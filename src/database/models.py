import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .connection import Base

class LogEvent(Base):
    """Log events table for storing processed logs"""
    __tablename__ = "log_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    source = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    raw_data = Column(JSONB)
    classification = Column(String(50))
    confidence_score = Column(Float)
    severity_score = Column(Integer)
    processed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    feedback = relationship("AnalystFeedback", back_populates="log_event")

class Incident(Base):
    """Incidents table for tracking security incidents"""
    __tablename__ = "incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default='open')
    assigned_to = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    escalated_at = Column(DateTime(timezone=True))
    jira_ticket_id = Column(String(50))

class AlertRule(Base):
    """Alert rules for defining escalation conditions"""
    __tablename__ = "alert_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    conditions = Column(JSONB, nullable=False)
    severity = Column(String(20), nullable=False)
    escalation_policy = Column(JSONB)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class AnalystFeedback(Base):
    """Analyst feedback for ML model improvement"""
    __tablename__ = "analyst_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_event_id = Column(UUID(as_uuid=True), ForeignKey('log_events.id'), nullable=False)
    analyst_id = Column(String(100), nullable=False)
    correct_classification = Column(String(50))
    feedback_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    log_event = relationship("LogEvent", back_populates="feedback")

# Additional model for system metrics and monitoring
class SystemMetric(Base):
    """System metrics for monitoring performance"""
    __tablename__ = "system_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50))  # latency, throughput, accuracy, etc.
    source_component = Column(String(100))  # bert_classifier, llm_classifier, etc.
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)