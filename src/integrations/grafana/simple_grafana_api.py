"""
Simple Grafana Integration API for SOC Log Classification System
Provides REST API endpoints for Grafana to query log data and metrics
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Import database models
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))

from database.connection import SessionLocal
from database.models import LogEvent, Incident

app = FastAPI(
    title="SOC Grafana Data API",
    description="REST API for serving SOC log data to Grafana dashboards",
    version="1.0.0"
)

# Enable CORS for Grafana
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Grafana's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_session():
    """Get database session with proper cleanup"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SOC Grafana API", "timestamp": datetime.utcnow()}

@app.get("/search")
async def search_metrics():
    """
    Grafana search endpoint - returns available metrics/targets
    """
    return [
        "log_events_timeline",
        "log_events_by_severity", 
        "log_events_by_classification",
        "incidents_by_status",
        "top_sources"
    ]

@app.get("/logs/recent")
async def get_recent_logs(limit: int = Query(100, description="Number of recent logs to return")):
    """Get recent log events for table display"""
    db = None
    try:
        db = get_db_session()
        
        logs = db.query(LogEvent).order_by(LogEvent.timestamp.desc()).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "source": log.source or "Unknown",
                "classification": log.classification or "Unknown",
                "severity_score": log.severity_score or 0,
                "confidence_score": round(log.confidence_score, 2) if log.confidence_score else 0,
                "message": (log.message[:200] + "...") if log.message and len(log.message) > 200 else (log.message or "")
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent logs: {str(e)}")
    finally:
        if db:
            db.close()

@app.get("/stats/summary")
async def get_stats_summary():
    """Get summary statistics for the dashboard"""
    db = None
    try:
        db = get_db_session()
        
        # Get counts for last 24 hours
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Total logs
        total_logs = db.query(LogEvent).count()
        
        # Logs in last 24h
        logs_24h = db.query(LogEvent).filter(LogEvent.timestamp >= last_24h).count()
        
        # Critical logs in last 24h
        critical_logs_24h = db.query(LogEvent).filter(
            LogEvent.timestamp >= last_24h,
            LogEvent.severity_score >= 8
        ).count()
        
        # Total incidents
        total_incidents = db.query(Incident).count()
        
        # Open incidents
        open_incidents = db.query(Incident).filter(Incident.status == 'open').count()
        
        # Get severity distribution
        severity_dist = {}
        logs_with_severity = db.query(LogEvent.severity_score).filter(LogEvent.severity_score.isnot(None)).all()
        for (severity,) in logs_with_severity:
            if severity >= 8:
                key = "Critical (8+)"
            elif severity >= 6:
                key = "High (6-7)"
            elif severity >= 4:
                key = "Medium (4-5)"
            else:
                key = "Low (0-3)"
            severity_dist[key] = severity_dist.get(key, 0) + 1
        
        # Get top classifications
        from sqlalchemy import func
        top_classifications = db.query(
            LogEvent.classification,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.classification.isnot(None)
        ).group_by(LogEvent.classification).order_by(
            func.count(LogEvent.id).desc()
        ).limit(5).all()
        
        classifications = {cls: count for cls, count in top_classifications}
        
        return {
            "total_logs": total_logs,
            "logs_last_24h": logs_24h,
            "critical_logs_24h": critical_logs_24h,
            "total_incidents": total_incidents,
            "open_incidents": open_incidents,
            "severity_distribution": severity_dist,
            "top_classifications": classifications,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    finally:
        if db:
            db.close()

@app.get("/logs/by_severity")
async def get_logs_by_severity():
    """Get log count by severity for pie charts"""
    db = None
    try:
        db = get_db_session()
        
        from sqlalchemy import func
        result = db.query(
            LogEvent.severity_score,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.severity_score.isnot(None)
        ).group_by(LogEvent.severity_score).all()
        
        severity_data = {}
        for severity, count in result:
            if severity >= 8:
                key = "Critical (8+)"
            elif severity >= 6:
                key = "High (6-7)"
            elif severity >= 4:
                key = "Medium (4-5)"
            else:
                key = "Low (0-3)"
            severity_data[key] = severity_data.get(key, 0) + count
        
        return severity_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get severity data: {str(e)}")
    finally:
        if db:
            db.close()

@app.get("/logs/by_classification")
async def get_logs_by_classification():
    """Get log count by classification"""
    db = None
    try:
        db = get_db_session()
        
        from sqlalchemy import func
        result = db.query(
            LogEvent.classification,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.classification.isnot(None)
        ).group_by(LogEvent.classification).order_by(
            func.count(LogEvent.id).desc()
        ).limit(10).all()
        
        return {classification: count for classification, count in result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get classification data: {str(e)}")
    finally:
        if db:
            db.close()

@app.get("/logs/by_source")
async def get_logs_by_source():
    """Get log count by source"""
    db = None
    try:
        db = get_db_session()
        
        from sqlalchemy import func
        result = db.query(
            LogEvent.source,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.source.isnot(None)
        ).group_by(LogEvent.source).order_by(
            func.count(LogEvent.id).desc()
        ).limit(10).all()
        
        return {source: count for source, count in result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get source data: {str(e)}")
    finally:
        if db:
            db.close()

@app.get("/test")
async def test_database():
    """Test database connection and return sample data"""
    db = None
    try:
        db = get_db_session()
        
        # Test basic query
        count = db.query(LogEvent).count()
        
        # Get a sample log
        sample_log = db.query(LogEvent).first()
        sample_data = None
        if sample_log:
            sample_data = {
                "id": str(sample_log.id),
                "timestamp": sample_log.timestamp.isoformat() if sample_log.timestamp else None,
                "source": sample_log.source,
                "classification": sample_log.classification,
                "severity_score": sample_log.severity_score
            }
        
        return {
            "status": "success",
            "total_logs": count,
            "sample_log": sample_data,
            "message": f"Database connection working. Found {count} logs."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database test failed: {str(e)}")
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    # Run the API server
    port = int(os.getenv("GRAFANA_API_PORT", 8002))
    
    print(f"Starting SOC Grafana API server on port {port}")
    print("Available endpoints:")
    print(f"  - Health: http://localhost:{port}/")
    print(f"  - Recent Logs: http://localhost:{port}/logs/recent")
    print(f"  - Stats: http://localhost:{port}/stats/summary")
    print(f"  - Test DB: http://localhost:{port}/test")
    print(f"  - Severity Data: http://localhost:{port}/logs/by_severity")
    print(f"  - Classification Data: http://localhost:{port}/logs/by_classification")
    print(f"  - Source Data: http://localhost:{port}/logs/by_source")
    
    uvicorn.run(
        "simple_grafana_api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )