"""
High-Performance Log Processor
Optimized for large-scale log processing with parallel execution and batch operations
"""

import time
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, Any, Optional, Tuple, List, Callable
from datetime import datetime
import sys
import os
import threading
from queue import Queue
import numpy as np
import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from processor_regex import regex_classify
from processor_bert import bert_classify
from processor_llm import llm_classify
from database.batch_service import BatchDatabaseService
from database.service import DatabaseService

# Import Slack integration
try:
    from integrations.slack.slack_integration import get_slack_manager, notify_log_alert, notify_batch_complete
    SLACK_AVAILABLE = True
except ImportError as e:
    print(f"Slack integration not available: {e}")
    SLACK_AVAILABLE = False

# Import JIRA integration
try:
    from integrations.jira.jira_integration import get_jira_manager, create_incident
    JIRA_AVAILABLE = True
except ImportError as e:
    print(f"JIRA integration not available: {e}")
    JIRA_AVAILABLE = False

class ModelCache:
    """Thread-safe model cache for sharing models across workers"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.initialized = False
        return cls._instance
    
    def initialize_models(self):
        """Initialize models once for the entire application"""
        if not self.initialized:
            with self._lock:
                if not self.initialized:
                    try:
                        # Pre-load BERT model and SVM classifier
                        from sentence_transformers import SentenceTransformer
                        import joblib
                        
                        print("Loading BERT embedding model...")
                        self.bert_model = SentenceTransformer('all-MiniLM-L6-v2')
                        
                        print("Loading SVM classification model...")
                        model_path = os.path.join(os.path.dirname(__file__), 
                                                 "../../models/log_classification_model.joblib")
                        self.svm_model = joblib.load(model_path)
                        
                        self.initialized = True
                        print("Models loaded successfully!")
                        
                    except Exception as e:
                        print(f"Error loading models: {e}")
                        self.initialized = False

# Global model cache instance
model_cache = ModelCache()

def classify_log_batch(log_batch: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    """
    Classify a batch of logs using optimized batch processing
    This function is designed to be called by worker processes
    """
    results = []
    
    # Ensure models are loaded in this worker
    if not model_cache.initialized:
        model_cache.initialize_models()
    
    if not model_cache.initialized:
        # Fallback to individual classification
        for source, log_message in log_batch:
            result = classify_single_log_fallback(source, log_message)
            results.append(result)
        return results
    
    # Separate logs by processing type
    bert_logs = []
    llm_logs = []
    regex_logs = []
    
    for i, (source, log_message) in enumerate(log_batch):
        if source == "LegacyCRM":
            llm_logs.append((i, source, log_message))
        else:
            # Try regex first, then BERT if needed
            regex_result = regex_classify(log_message)
            if regex_result is not None:
                results.append({
                    'index': i,
                    'source': source,
                    'message': log_message,
                    'classification': regex_result,
                    'confidence_score': None,
                    'method': 'regex'
                })
            else:
                bert_logs.append((i, source, log_message))
    
    # Process BERT logs in batch for efficiency
    if bert_logs and model_cache.initialized:
        try:
            # Extract messages for batch embedding
            messages = [log[2] for log in bert_logs]
            
            # Get embeddings for all messages at once
            embeddings = model_cache.bert_model.encode(messages)
            
            # Get predictions for all embeddings at once
            probabilities = model_cache.svm_model.predict_proba(embeddings)
            predictions = model_cache.svm_model.predict(embeddings)
            
            # Process results
            for j, (i, source, log_message) in enumerate(bert_logs):
                max_prob = max(probabilities[j])
                classification = "Unclassified" if max_prob < 0.55 else predictions[j]
                
                results.append({
                    'index': i,
                    'source': source,
                    'message': log_message,
                    'classification': classification,
                    'confidence_score': float(max_prob),
                    'method': 'bert'
                })
                
        except Exception as e:
            print(f"Batch BERT processing error: {e}")
            # Fallback to individual processing
            for i, source, log_message in bert_logs:
                result = classify_single_log_fallback(source, log_message)
                result['index'] = i
                results.append(result)
    
    # Process LLM logs (these need to be done individually due to API nature)
    for i, source, log_message in llm_logs:
        try:
            classification = llm_classify(log_message)
            results.append({
                'index': i,
                'source': source,
                'message': log_message,
                'classification': classification,
                'confidence_score': None,
                'method': 'llm'
            })
        except Exception as e:
            print(f"LLM classification error: {e}")
            results.append({
                'index': i,
                'source': source,
                'message': log_message,
                'classification': 'Unclassified',
                'confidence_score': None,
                'method': 'llm_error'
            })
    
    # Sort results by original index
    results.sort(key=lambda x: x['index'])
    
    return results

def classify_single_log_fallback(source: str, log_message: str) -> Dict[str, Any]:
    """Fallback single log classification"""
    try:
        start_time = time.time()
        
        if source == "LegacyCRM":
            classification = llm_classify(log_message)
            confidence_score = None
        else:
            regex_result = regex_classify(log_message)
            if regex_result is not None:
                classification = regex_result
                confidence_score = None
            else:
                classification = bert_classify(log_message)
                confidence_score = 0.8  # Approximate confidence
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            'source': source,
            'message': log_message,
            'classification': classification,
            'confidence_score': confidence_score,
            'processing_time_ms': processing_time,
            'method': 'fallback'
        }
        
    except Exception as e:
        return {
            'source': source,
            'message': log_message,
            'classification': 'Unclassified',
            'confidence_score': None,
            'processing_time_ms': 0,
            'method': 'error',
            'error': str(e)
        }

class HighPerformanceLogProcessor:
    """High-performance log processor with parallel processing and batch operations"""
    
    def __init__(self, max_workers: int = None, batch_size: int = 100, 
                 use_database: bool = True, enable_slack: bool = True, enable_jira: bool = True):
        """
        Initialize the high-performance processor
        
        Args:
            max_workers: Number of parallel workers (default: CPU count)
            batch_size: Number of logs to process in each batch
            use_database: Whether to use database storage
            enable_slack: Whether to enable Slack notifications
            enable_jira: Whether to enable JIRA incident creation
        """
        self.max_workers = max_workers or min(mp.cpu_count(), 8)  # Cap at 8 to avoid overwhelming
        self.batch_size = batch_size
        self.use_database = use_database
        self.enable_slack = enable_slack and SLACK_AVAILABLE
        self.enable_jira = enable_jira and JIRA_AVAILABLE
        
        # Initialize Slack integration
        if self.enable_slack:
            try:
                self.slack_manager = get_slack_manager()
                if self.slack_manager.is_available():
                    print("✅ Slack notifications enabled")
                else:
                    self.enable_slack = False
                    print("⚠️ Slack notifications disabled - connection failed")
            except Exception as e:
                self.enable_slack = False
                print(f"⚠️ Slack notifications disabled due to error: {e}")
        
        # Initialize JIRA integration
        if self.enable_jira:
            try:
                self.jira_manager = get_jira_manager()
                if self.jira_manager.is_available():
                    print("✅ JIRA incident management enabled")
                else:
                    self.enable_jira = False
                    print("⚠️ JIRA integration disabled - connection failed")
            except Exception as e:
                self.enable_jira = False
                print(f"⚠️ JIRA integration disabled due to error: {e}")
        
        # Initialize model cache
        model_cache.initialize_models()
        
        # Database services
        if self.use_database:
            try:
                self.batch_db_service = BatchDatabaseService(batch_size=1000)
                self.db_service = DatabaseService()
            except Exception as e:
                print(f"Warning: Database not available: {e}")
                self.use_database = False
        
        # Severity mapping
        self.severity_mapping = {
            'Security Alert': 9,
            'Critical Error': 8,
            'Workflow Error': 7,
            'System Notification': 6,
            'HTTP Status': 4,
            'Resource Usage': 3,
            'User Action': 2,
            'Deprecation Warning': 2,
            'Unclassified': 1
        }
    
    def calculate_severity(self, classification: str, confidence_score: float = None) -> int:
        """Calculate severity score"""
        base_severity = self.severity_mapping.get(classification, 1)
        
        if confidence_score is not None:
            if confidence_score > 0.9:
                base_severity = min(10, base_severity + 1)
            elif confidence_score < 0.6:
                base_severity = max(1, base_severity - 1)
        
        return base_severity
    
    def process_batch_parallel(self, logs: List[Tuple[str, str]], 
                             progress_callback: Callable[[int, int], None] = None) -> List[Dict[str, Any]]:
        """
        Process logs in parallel batches for maximum performance
        
        Args:
            logs: List of (source, log_message) tuples
            progress_callback: Function to call with (completed, total) progress updates
            
        Returns:
            List of classification results
        """
        if not logs:
            return []
        
        start_time = time.time()
        total_logs = len(logs)
        results = []
        
        print(f"Processing {total_logs} logs with {self.max_workers} workers...")
        
        # Split logs into batches
        batches = []
        for i in range(0, len(logs), self.batch_size):
            batch = logs[i:i + self.batch_size]
            batches.append(batch)
        
        completed_logs = 0
        
        # Use ThreadPoolExecutor for I/O bound operations (better for our use case)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(classify_log_batch, batch): batch 
                for batch in batches
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                try:
                    batch_results = future.result()
                    
                    # Process each result in the batch
                    for result in batch_results:
                        # Add severity calculation
                        severity_score = self.calculate_severity(
                            result['classification'], 
                            result.get('confidence_score')
                        )
                        result['severity_score'] = severity_score
                        results.append(result)
                    
                    # Update progress
                    completed_logs += len(batch_results)
                    if progress_callback:
                        progress_callback(completed_logs, total_logs)
                    
                    print(f"Completed {completed_logs}/{total_logs} logs...")
                    
                except Exception as e:
                    print(f"Batch processing error: {e}")
                    # Add error results for failed batch
                    batch = future_to_batch[future]
                    for source, log_message in batch:
                        results.append({
                            'source': source,
                            'message': log_message,
                            'classification': 'Unclassified',
                            'confidence_score': None,
                            'severity_score': 1,
                            'error': str(e)
                        })
        
        processing_time = time.time() - start_time
        
        # Sort results to maintain original order
        results.sort(key=lambda x: x.get('index', 0))
        
        print(f"Parallel processing completed in {processing_time:.2f}s")
        print(f"Average: {(processing_time * 1000) / total_logs:.1f}ms per log")
        
        return results
    
    def store_results_batch(self, results: List[Dict[str, Any]]) -> None:
        """Store results in database using batch operations"""
        if not self.use_database or not results:
            return
        
        try:
            # Prepare data for batch insert
            log_data = []
            metrics_data = []
            
            for result in results:
                # Prepare log event data
                log_item = {
                    'source': result['source'],
                    'message': result['message'],
                    'classification': result['classification'],
                    'confidence_score': result.get('confidence_score'),
                    'severity_score': result['severity_score'],
                    'raw_data': {
                        'method': result.get('method', 'unknown'),
                        'error': result.get('error') if 'error' in result else None
                    }
                }
                log_data.append(log_item)
                
                # Prepare metrics data
                if 'processing_time_ms' in result:
                    metrics_data.append({
                        'metric_name': 'processing_latency',
                        'metric_value': result['processing_time_ms'],
                        'metric_type': 'latency',
                        'source_component': result.get('method', 'unknown')
                    })
                
                if result.get('confidence_score') is not None:
                    metrics_data.append({
                        'metric_name': 'classification_confidence',
                        'metric_value': result['confidence_score'],
                        'metric_type': 'accuracy',
                        'source_component': result.get('method', 'unknown')
                    })
            
            # Perform batch inserts
            print("Storing results in database...")
            start_time = time.time()
            
            self.batch_db_service.bulk_insert_log_events(log_data)
            self.batch_db_service.bulk_insert_metrics(metrics_data)
            
            storage_time = time.time() - start_time
            print(f"Database storage completed in {storage_time:.2f}s")
            
        except Exception as e:
            print(f"Error storing results: {e}")
    
    def process_large_dataset(self, logs: List[Tuple[str, str]], 
                            store_in_db: bool = True,
                            progress_callback: Callable[[int, int], None] = None) -> List[Dict[str, Any]]:
        """
        Process a large dataset with optimal performance
        
        Args:
            logs: List of (source, log_message) tuples
            store_in_db: Whether to store results in database
            progress_callback: Progress update callback
            
        Returns:
            List of classification results
        """
        total_start_time = time.time()
        
        # Process logs in parallel
        results = self.process_batch_parallel(logs, progress_callback)
        
        # Store results if requested
        if store_in_db and self.use_database:
            self.store_results_batch(results)
        
        total_time = time.time() - total_start_time
        
        # Performance summary
        processing_stats = {}
        if results:
            print(f"\n=== Performance Summary ===")
            print(f"Total logs processed: {len(results)}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Average per log: {(total_time * 1000) / len(results):.1f}ms")
            print(f"Throughput: {len(results) / total_time:.1f} logs/second")
            
            # Prepare stats for Slack notification
            processing_stats = {
                'total_logs': len(results),
                'total_time': total_time,
                'avg_time_per_log': (total_time * 1000) / len(results),
                'throughput': len(results) / total_time
            }
            
            # Classification distribution
            classifications = {}
            high_severity_count = 0
            critical_count = 0
            
            for result in results:
                classification = result['classification']
                classifications[classification] = classifications.get(classification, 0) + 1
                
                severity = result.get('severity_score', 0)
                if severity >= 8:
                    critical_count += 1
                elif severity >= 6:
                    high_severity_count += 1
            
            print(f"\nClassification Distribution:")
            for classification, count in classifications.items():
                percentage = (count / len(results)) * 100
                print(f"  {classification}: {count} ({percentage:.1f}%)")
            
            print(f"\nSeverity Summary:")
            print(f"  Critical (8+): {critical_count}")
            print(f"  High (6-7): {high_severity_count}")
            
            processing_stats.update({
                'critical_count': critical_count,
                'high_severity_count': high_severity_count,
                'classifications': classifications
            })
            
            # Send notifications and create incidents asynchronously if enabled
            notifications_sent = {
                'slack_alerts': 0,
                'jira_incidents': 0
            }
            
            if self.enable_slack or self.enable_jira:
                try:
                    # Process critical events for notifications and incidents
                    for result in results:
                        severity_score = result.get('severity_score', 0)
                        
                        if severity_score >= 8:  # Critical events
                            # Send Slack alert
                            if self.enable_slack:
                                try:
                                    def send_alert_bg():
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        try:
                                            loop.run_until_complete(notify_log_alert(result))
                                        finally:
                                            loop.close()
                                    
                                    import threading
                                    alert_thread = threading.Thread(target=send_alert_bg)
                                    alert_thread.daemon = True
                                    alert_thread.start()
                                    notifications_sent['slack_alerts'] += 1
                                    
                                except Exception as e:
                                    print(f"⚠️ Failed to send Slack alert: {e}")
                            
                            # Create JIRA incident for security/critical events
                            if self.enable_jira:
                                classification = result.get('classification', '')
                                if ('Security' in classification or 'Critical' in classification or 
                                    severity_score >= 9):  # Very critical or security-related
                                    try:
                                        def create_incident_bg():
                                            loop = asyncio.new_event_loop()
                                            asyncio.set_event_loop(loop)
                                            try:
                                                loop.run_until_complete(create_incident(result))
                                            finally:
                                                loop.close()
                                        
                                        incident_thread = threading.Thread(target=create_incident_bg)
                                        incident_thread.daemon = True
                                        incident_thread.start()
                                        notifications_sent['jira_incidents'] += 1
                                        
                                    except Exception as e:
                                        print(f"⚠️ Failed to create JIRA incident: {e}")
                    
                    # Report notification activity
                    if notifications_sent['slack_alerts'] > 0:
                        print(f"📤 Sent {notifications_sent['slack_alerts']} critical alerts to Slack")
                    
                    if notifications_sent['jira_incidents'] > 0:
                        print(f"🎫 Created {notifications_sent['jira_incidents']} JIRA incidents")
                    
                    # Send batch summary for significant batches
                    if len(results) >= 100 or high_severity_count >= 5:
                        try:
                            def send_batch_summary_bg():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(notify_batch_complete(results, processing_stats))
                                finally:
                                    loop.close()
                            
                            summary_thread = threading.Thread(target=send_batch_summary_bg)
                            summary_thread.daemon = True
                            summary_thread.start()
                            print("📤 Batch summary sent to Slack")
                            
                        except Exception as e:
                            print(f"⚠️ Failed to send batch summary: {e}")
                    
                except Exception as e:
                    print(f"⚠️ Slack notification error: {e}")
        
        return results
    
    def close(self):
        """Clean up resources"""
        if self.use_database:
            if hasattr(self, 'batch_db_service'):
                self.batch_db_service.close()
            if hasattr(self, 'db_service'):
                self.db_service.close()

# Convenience function for backward compatibility
def process_logs_high_performance(logs: List[Tuple[str, str]], 
                                max_workers: int = None,
                                batch_size: int = 100,
                                store_in_db: bool = True,
                                progress_callback: Callable[[int, int], None] = None) -> List[Dict[str, Any]]:
    """
    High-performance log processing function
    
    Usage:
        results = process_logs_high_performance([(source, message), ...])
    """
    processor = HighPerformanceLogProcessor(
        max_workers=max_workers,
        batch_size=batch_size,
        use_database=store_in_db
    )
    
    try:
        return processor.process_large_dataset(
            logs, 
            store_in_db=store_in_db,
            progress_callback=progress_callback
        )
    finally:
        processor.close()

if __name__ == "__main__":
    # Test the high-performance processor
    test_logs = [
        ("WebServer", f"GET /api/test/{i} HTTP/1.1 - 200 OK")
        for i in range(100)
    ]
    
    print("Testing high-performance processor...")
    results = process_logs_high_performance(test_logs, store_in_db=False)
    print(f"Processed {len(results)} logs successfully!")