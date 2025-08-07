"""
High-Performance Batch Database Service
Optimized for bulk operations and high-volume log processing
"""

from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
import uuid
import time
from .models import LogEvent, SystemMetric
from .connection import DATABASE_URL, Base

class BatchDatabaseService:
    """High-performance batch database operations"""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.engine = create_engine(
            DATABASE_URL, 
            echo=False,
            pool_size=20,  # Increase connection pool
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def close(self):
        """Close database session"""
        self.session.close()
        self.engine.dispose()
    
    def bulk_insert_log_events(self, log_data: List[Dict[str, Any]]) -> List[uuid.UUID]:
        """
        Bulk insert log events using PostgreSQL's efficient bulk insert
        
        Args:
            log_data: List of dictionaries containing log event data
            
        Returns:
            List of UUIDs for inserted records
        """
        if not log_data:
            return []
        
        try:
            # Prepare data for bulk insert
            insert_data = []
            inserted_ids = []
            
            for item in log_data:
                log_id = uuid.uuid4()
                inserted_ids.append(log_id)
                
                insert_item = {
                    'id': log_id,
                    'timestamp': datetime.utcnow(),
                    'source': item['source'],
                    'message': item['message'],
                    'raw_data': item.get('raw_data', {}),
                    'classification': item.get('classification'),
                    'confidence_score': item.get('confidence_score'),
                    'severity_score': item.get('severity_score'),
                    'processed_at': datetime.utcnow()
                }
                insert_data.append(insert_item)
            
            # Use PostgreSQL's bulk insert for maximum performance
            if len(insert_data) > 0:
                # Process in batches to avoid memory issues
                for i in range(0, len(insert_data), self.batch_size):
                    batch = insert_data[i:i + self.batch_size]
                    self.session.bulk_insert_mappings(LogEvent, batch)
                
                self.session.commit()
            
            return inserted_ids
            
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Bulk insert failed: {str(e)}")
    
    def bulk_insert_metrics(self, metrics_data: List[Dict[str, Any]]) -> None:
        """Bulk insert system metrics"""
        if not metrics_data:
            return
        
        try:
            # Prepare metrics data
            insert_data = []
            for item in metrics_data:
                insert_item = {
                    'id': uuid.uuid4(),
                    'metric_name': item['metric_name'],
                    'metric_value': item['metric_value'],
                    'metric_type': item.get('metric_type'),
                    'source_component': item.get('source_component'),
                    'timestamp': datetime.utcnow()
                }
                insert_data.append(insert_item)
            
            # Bulk insert metrics
            self.session.bulk_insert_mappings(SystemMetric, insert_data)
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Metrics bulk insert failed: {str(e)}")
    
    def upsert_log_events(self, log_data: List[Dict[str, Any]]) -> List[uuid.UUID]:
        """
        Upsert log events (insert or update if exists) - PostgreSQL specific
        Useful for reprocessing logs without duplicates
        """
        if not log_data:
            return []
        
        try:
            inserted_ids = []
            
            # Prepare data for upsert
            for item in log_data:
                log_id = uuid.uuid4()
                inserted_ids.append(log_id)
                
                stmt = insert(LogEvent).values(
                    id=log_id,
                    timestamp=datetime.utcnow(),
                    source=item['source'],
                    message=item['message'],
                    raw_data=item.get('raw_data', {}),
                    classification=item.get('classification'),
                    confidence_score=item.get('confidence_score'),
                    severity_score=item.get('severity_score'),
                    processed_at=datetime.utcnow()
                )
                
                # On conflict (duplicate message + source + timestamp), update classification
                do_update_stmt = stmt.on_conflict_do_update(
                    index_elements=['source', 'message', 'timestamp'],
                    set_=dict(
                        classification=stmt.excluded.classification,
                        confidence_score=stmt.excluded.confidence_score,
                        severity_score=stmt.excluded.severity_score,
                        processed_at=stmt.excluded.processed_at
                    )
                )
                
                self.session.execute(do_update_stmt)
            
            self.session.commit()
            return inserted_ids
            
        except Exception as e:
            self.session.rollback()
            # Fallback to regular bulk insert if upsert fails
            return self.bulk_insert_log_events(log_data)
    
    def create_indexes_for_performance(self):
        """Create database indexes for better query performance"""
        try:
            # Create indexes on commonly queried columns
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_log_events_timestamp ON log_events(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_log_events_source ON log_events(source)",
                "CREATE INDEX IF NOT EXISTS idx_log_events_classification ON log_events(classification)",
                "CREATE INDEX IF NOT EXISTS idx_log_events_severity ON log_events(severity_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_log_events_processed_at ON log_events(processed_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_system_metrics_component ON system_metrics(source_component)"
            ]
            
            for index_sql in indexes:
                self.session.execute(index_sql)
            
            self.session.commit()
            print("Performance indexes created successfully")
            
        except Exception as e:
            print(f"Warning: Could not create performance indexes: {e}")
            self.session.rollback()
    
    def get_table_statistics(self) -> Dict[str, Any]:
        """Get database table statistics for performance monitoring"""
        try:
            stats = {}
            
            # Get row counts
            log_count = self.session.query(LogEvent).count()
            stats['total_log_events'] = log_count
            
            # Get recent processing stats
            recent_query = """
            SELECT 
                COUNT(*) as recent_count,
                AVG(EXTRACT(EPOCH FROM (processed_at - timestamp)) * 1000) as avg_processing_delay_ms
            FROM log_events 
            WHERE processed_at >= NOW() - INTERVAL '1 hour'
            """
            
            result = self.session.execute(recent_query).fetchone()
            stats['recent_logs_count'] = result[0] if result else 0
            stats['avg_processing_delay_ms'] = round(result[1], 2) if result and result[1] else 0
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    def vacuum_and_analyze(self):
        """Run PostgreSQL VACUUM and ANALYZE for performance optimization"""
        try:
            # These operations help PostgreSQL optimize query performance
            self.session.execute("VACUUM ANALYZE log_events")
            self.session.execute("VACUUM ANALYZE system_metrics")
            self.session.commit()
            print("Database optimization completed (VACUUM ANALYZE)")
            
        except Exception as e:
            print(f"Warning: Database optimization failed: {e}")
            self.session.rollback()