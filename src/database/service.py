from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from .models import LogEvent, Incident, AlertRule, AnalystFeedback, SystemMetric
from .connection import get_db, SessionLocal
import uuid

class DatabaseService:
    """Service layer for database operations"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def close(self):
        """Close database session"""
        self.db.close()
    
    # Log Event operations
    def create_log_event(self, source: str, message: str, raw_data: Dict = None,
                        classification: str = None, confidence_score: float = None,
                        severity_score: int = None) -> LogEvent:
        """Create a new log event"""
        log_event = LogEvent(
            source=source,
            message=message,
            raw_data=raw_data or {},
            classification=classification,
            confidence_score=confidence_score,
            severity_score=severity_score
        )
        self.db.add(log_event)
        self.db.commit()
        self.db.refresh(log_event)
        return log_event
    
    def get_log_events(self, limit: int = 100, offset: int = 0, 
                      source: str = None, classification: str = None) -> List[LogEvent]:
        """Retrieve log events with optional filtering"""
        query = self.db.query(LogEvent)
        
        if source:
            query = query.filter(LogEvent.source == source)
        if classification:
            query = query.filter(LogEvent.classification == classification)
        
        return query.order_by(desc(LogEvent.timestamp)).offset(offset).limit(limit).all()
    
    def get_log_event_by_id(self, event_id: uuid.UUID) -> Optional[LogEvent]:
        """Get specific log event by ID"""
        return self.db.query(LogEvent).filter(LogEvent.id == event_id).first()
    
    # Incident operations
    def create_incident(self, title: str, severity: str, description: str = None,
                       assigned_to: str = None) -> Incident:
        """Create a new incident"""
        incident = Incident(
            title=title,
            description=description,
            severity=severity,
            assigned_to=assigned_to
        )
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident
    
    def get_incidents(self, status: str = None, severity: str = None,
                     limit: int = 50) -> List[Incident]:
        """Retrieve incidents with optional filtering"""
        query = self.db.query(Incident)
        
        if status:
            query = query.filter(Incident.status == status)
        if severity:
            query = query.filter(Incident.severity == severity)
        
        return query.order_by(desc(Incident.created_at)).limit(limit).all()
    
    def update_incident_status(self, incident_id: uuid.UUID, status: str,
                              assigned_to: str = None) -> Optional[Incident]:
        """Update incident status"""
        incident = self.db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            incident.status = status
            if assigned_to:
                incident.assigned_to = assigned_to
            self.db.commit()
            self.db.refresh(incident)
        return incident
    
    # Analytics and reporting
    def get_classification_stats(self, days: int = 7) -> Dict[str, int]:
        """Get classification statistics for the past N days"""
        from_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from_date = from_date.replace(day=from_date.day - days)
        
        stats = self.db.query(
            LogEvent.classification,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.timestamp >= from_date
        ).group_by(LogEvent.classification).all()
        
        return {stat.classification or 'Unclassified': stat.count for stat in stats}
    
    def get_severity_distribution(self, days: int = 7) -> Dict[str, int]:
        """Get severity score distribution"""
        from_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from_date = from_date.replace(day=from_date.day - days)
        
        stats = self.db.query(
            func.case(
                (LogEvent.severity_score >= 8, 'Critical'),
                (LogEvent.severity_score >= 6, 'High'),
                (LogEvent.severity_score >= 4, 'Medium'),
                (LogEvent.severity_score >= 2, 'Low'),
                else_='Info'
            ).label('severity_level'),
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.timestamp >= from_date,
            LogEvent.severity_score.isnot(None)
        ).group_by('severity_level').all()
        
        return {stat.severity_level: stat.count for stat in stats}
    
    def get_log_volume_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get log volume statistics"""
        from_date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        from_date = from_date.replace(hour=from_date.hour - hours)
        
        total_logs = self.db.query(func.count(LogEvent.id)).filter(
            LogEvent.timestamp >= from_date
        ).scalar()
        
        avg_confidence = self.db.query(func.avg(LogEvent.confidence_score)).filter(
            LogEvent.timestamp >= from_date,
            LogEvent.confidence_score.isnot(None)
        ).scalar()
        
        return {
            'total_logs': total_logs or 0,
            'average_confidence': round(float(avg_confidence or 0), 3),
            'time_period_hours': hours
        }
    
    # Analyst feedback operations
    def add_feedback(self, log_event_id: uuid.UUID, analyst_id: str,
                    correct_classification: str, notes: str = None) -> AnalystFeedback:
        """Add analyst feedback for a log event"""
        feedback = AnalystFeedback(
            log_event_id=log_event_id,
            analyst_id=analyst_id,
            correct_classification=correct_classification,
            feedback_notes=notes
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def record_metric(self, metric_name: str, value: float, metric_type: str = None,
                     source_component: str = None) -> SystemMetric:
        """Record system performance metric"""
        metric = SystemMetric(
            metric_name=metric_name,
            metric_value=value,
            metric_type=metric_type,
            source_component=source_component
        )
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric