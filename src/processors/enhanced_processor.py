import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from processor_regex import regex_classify
from processor_bert import bert_classify
from processor_llm import llm_classify
from database.service import DatabaseService
from database.models import LogEvent

class EnhancedLogProcessor:
    """Enhanced log processor with database integration and metrics tracking"""
    
    def __init__(self):
        self.db_service = DatabaseService()
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
    
    def close(self):
        """Close database connection"""
        self.db_service.close()
    
    def calculate_severity(self, classification: str, confidence_score: float = None) -> int:
        """Calculate severity score based on classification and confidence"""
        base_severity = self.severity_mapping.get(classification, 1)
        
        # Adjust severity based on confidence if available
        if confidence_score is not None:
            if confidence_score > 0.9:
                base_severity = min(10, base_severity + 1)
            elif confidence_score < 0.6:
                base_severity = max(1, base_severity - 1)
        
        return base_severity
    
    def classify_and_store(self, source: str, log_message: str, 
                          store_in_db: bool = True) -> Dict[str, Any]:
        """Classify log message and optionally store in database"""
        start_time = time.time()
        
        # Perform classification using existing logic
        classification, confidence_score = self._classify_with_confidence(source, log_message)
        
        # Calculate severity
        severity_score = self.calculate_severity(classification, confidence_score)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create result dictionary
        result = {
            'source': source,
            'message': log_message,
            'classification': classification,
            'confidence_score': confidence_score,
            'severity_score': severity_score,
            'processing_time_ms': round(processing_time * 1000, 2),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in database if requested
        if store_in_db:
            try:
                log_event = self.db_service.create_log_event(
                    source=source,
                    message=log_message,
                    raw_data={
                        'processing_time_ms': result['processing_time_ms'],
                        'classifier_used': self._get_classifier_used(source)
                    },
                    classification=classification,
                    confidence_score=confidence_score,
                    severity_score=severity_score
                )
                result['log_event_id'] = str(log_event.id)
                
                # Record performance metrics
                self.db_service.record_metric(
                    metric_name='processing_latency',
                    value=processing_time * 1000,
                    metric_type='latency',
                    source_component=self._get_classifier_used(source)
                )
                
                self.db_service.record_metric(
                    metric_name='classification_confidence',
                    value=confidence_score or 0,
                    metric_type='accuracy',
                    source_component=self._get_classifier_used(source)
                )
                
            except Exception as e:
                result['db_error'] = str(e)
        
        return result
    
    def _classify_with_confidence(self, source: str, log_message: str) -> Tuple[str, Optional[float]]:
        """Perform classification and return classification with confidence score"""
        if source == "LegacyCRM":
            classification = llm_classify(log_message)
            confidence_score = None  # LLM doesn't provide confidence scores yet
        else:
            # Try regex first
            classification = regex_classify(log_message)
            confidence_score = None
            
            if classification is None:
                # Use BERT classifier
                classification = bert_classify(log_message)
                # Calculate confidence from BERT probabilities
                confidence_score = self._get_bert_confidence(log_message)
        
        return classification, confidence_score
    
    def _get_bert_confidence(self, log_message: str) -> float:
        """Get confidence score from BERT model"""
        try:
            from sentence_transformers import SentenceTransformer
            import joblib
            
            model_embedding = SentenceTransformer('all-MiniLM-L6-v2')
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                     "../models/log_classification_model.joblib")
            model_classification = joblib.load(model_path)
            
            embeddings = model_embedding.encode([log_message])
            probabilities = model_classification.predict_proba(embeddings)[0]
            return float(max(probabilities))
        except Exception:
            return 0.0
    
    def _get_classifier_used(self, source: str) -> str:
        """Get the name of the classifier used for this source"""
        if source == "LegacyCRM":
            return "llm_classifier"
        else:
            return "regex_bert_classifier"
    
    def process_batch(self, logs: list, store_in_db: bool = True) -> list:
        """Process a batch of logs"""
        results = []
        batch_start_time = time.time()
        
        for source, log_message in logs:
            result = self.classify_and_store(source, log_message, store_in_db)
            results.append(result)
        
        batch_time = time.time() - batch_start_time
        
        # Record batch metrics
        if store_in_db:
            try:
                self.db_service.record_metric(
                    metric_name='batch_processing_time',
                    value=batch_time * 1000,
                    metric_type='latency',
                    source_component='batch_processor'
                )
                
                self.db_service.record_metric(
                    metric_name='batch_size',
                    value=len(logs),
                    metric_type='throughput',
                    source_component='batch_processor'
                )
            except Exception as e:
                print(f"Error recording batch metrics: {e}")
        
        return results
    
    def get_recent_logs(self, limit: int = 100, source: str = None, 
                       classification: str = None):
        """Retrieve recent log events from database"""
        return self.db_service.get_log_events(limit=limit, source=source, 
                                            classification=classification)
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary of recent log processing"""
        try:
            classification_stats = self.db_service.get_classification_stats()
            severity_distribution = self.db_service.get_severity_distribution()
            volume_stats = self.db_service.get_log_volume_stats()
            
            return {
                'classification_distribution': classification_stats,
                'severity_distribution': severity_distribution,
                'volume_statistics': volume_stats,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}

# Backward compatibility functions
def classify(logs):
    """Backward compatible function for existing code"""
    processor = EnhancedLogProcessor()
    try:
        results = processor.process_batch(logs, store_in_db=False)
        return [result['classification'] for result in results]
    finally:
        processor.close()

def classify_log(source, log_message):
    """Backward compatible function for single log classification"""
    processor = EnhancedLogProcessor()
    try:
        result = processor.classify_and_store(source, log_message, store_in_db=False)
        return result['classification']
    finally:
        processor.close()

if __name__ == "__main__":
    # Test the enhanced processor
    processor = EnhancedLogProcessor()
    try:
        # Test logs
        test_logs = [
            ("WebServer", "alpha.osapi_compute.wsgi.server - 12.10.11.1 - API returned 404 not found error"),
            ("LegacyCRM", "Multiple login failures occurred on user 6454 account"),
            ("SystemMonitor", "Server A790 was restarted unexpectedly during the process of data transfer")
        ]
        
        print("Testing Enhanced Log Processor...")
        results = processor.process_batch(test_logs, store_in_db=True)
        
        for result in results:
            print(f"Source: {result['source']}")
            print(f"Classification: {result['classification']}")
            print(f"Severity: {result['severity_score']}")
            print(f"Processing Time: {result['processing_time_ms']}ms")
            print("-" * 50)
        
        # Show analytics
        analytics = processor.get_analytics_summary()
        print("\nAnalytics Summary:")
        print(analytics)
        
    finally:
        processor.close()