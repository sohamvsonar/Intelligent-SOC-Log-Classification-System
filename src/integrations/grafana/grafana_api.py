"""
Grafana Integration API for SOC Log Classification System
Provides REST API endpoints for Grafana to query log data and metrics
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, desc, func, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import pandas as pd
import uvicorn

# Load environment variables
load_dotenv()

# Import database models
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
from database.models import LogEvent, Incident, SystemMetric
from database.connection import SessionLocal

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

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SOC Grafana API", "timestamp": datetime.utcnow()}

@app.get("/search")
async def search_metrics():
    """
    Grafana search endpoint - returns available metrics/targets
    This is used by Grafana to discover what data sources are available
    """
    return [
        "log_events_by_severity",
        "log_events_by_classification", 
        "log_events_by_source",
        "log_events_timeline",
        "incidents_by_status",
        "incidents_by_severity",
        "system_metrics",
        "alert_volume",
        "top_sources",
        "severity_trend"
    ]

@app.post("/query")
async def query_data(request: Dict[str, Any]):
    """
    Main Grafana query endpoint
    Handles time series queries from Grafana
    """
    try:
        # Extract query parameters
        targets = request.get("targets", [])
        time_range = request.get("range", {})
        interval = request.get("interval", "1h")
        
        # Parse time range
        from_time = datetime.fromisoformat(time_range.get("from", "").replace("Z", "+00:00"))
        to_time = datetime.fromisoformat(time_range.get("to", "").replace("Z", "+00:00"))
        
        results = []
        
        for target in targets:
            target_name = target.get("target", "")
            
            if target_name == "log_events_timeline":
                data = await get_log_events_timeline(from_time, to_time, interval)
                results.append(data)
            elif target_name == "log_events_by_severity":
                data = await get_log_events_by_severity(from_time, to_time)
                results.append(data)
            elif target_name == "log_events_by_classification":
                data = await get_log_events_by_classification(from_time, to_time)
                results.append(data)
            elif target_name == "incidents_by_status":
                data = await get_incidents_by_status(from_time, to_time)
                results.append(data)
            elif target_name == "top_sources":
                data = await get_top_sources(from_time, to_time)
                results.append(data)
            elif target_name == "severity_trend":
                data = await get_severity_trend(from_time, to_time, interval)
                results.append(data)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

async def get_log_events_timeline(from_time: datetime, to_time: datetime, interval: str) -> Dict[str, Any]:
    """Get log events count over time for timeline visualization"""
    try:
        db = SessionLocal()
        
        # Convert interval to hours for PostgreSQL
        interval_hours = {
            "1m": 0.0167, "5m": 0.083, "15m": 0.25, "30m": 0.5,
            "1h": 1, "3h": 3, "6h": 6, "12h": 12, "1d": 24
        }.get(interval, 1)
        
        # Query log events grouped by time intervals
        query = text(f"""
            SELECT 
                date_trunc('hour', timestamp) + 
                (EXTRACT(HOUR FROM timestamp)::int / {int(interval_hours)}) * interval '{int(interval_hours)} hours' as time_bucket,
                COUNT(*) as count
            FROM log_events 
            WHERE timestamp BETWEEN :from_time AND :to_time
            GROUP BY time_bucket
            ORDER BY time_bucket
        """)
        
        result = db.execute(query, {"from_time": from_time, "to_time": to_time}).fetchall()
        
        datapoints = []
        for row in result:
            timestamp_ms = int(row[0].timestamp() * 1000)
            datapoints.append([row[1], timestamp_ms])
        
        return {
            "target": "Log Events Timeline",
            "datapoints": datapoints
        }
        
    except Exception as e:
        print(f"Error in get_log_events_timeline: {e}")
        return {"target": "Log Events Timeline", "datapoints": []}

async def get_log_events_by_severity(from_time: datetime, to_time: datetime) -> Dict[str, Any]:
    """Get log events grouped by severity for pie chart"""
    try:
        db = SessionLocal()
        
        result = db.query(
            LogEvent.severity_score,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.timestamp.between(from_time, to_time)
        ).group_by(LogEvent.severity_score).all()
        
        # Format for Grafana pie chart
        datapoints = []
        for row in result:
            severity_label = f"Severity {row[0] or 'Unknown'}"
            datapoints.append([row[1], severity_label])
        
        return {
            "target": "Log Events by Severity",
            "datapoints": datapoints,
            "type": "table"
        }
        
    except Exception as e:
        print(f"Error in get_log_events_by_severity: {e}")
        return {"target": "Log Events by Severity", "datapoints": []}

async def get_log_events_by_classification(from_time: datetime, to_time: datetime) -> Dict[str, Any]:
    """Get log events grouped by classification"""
    try:
        db = get_database_session()
        
        result = db.query(
            LogEvent.classification,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.timestamp.between(from_time, to_time)
        ).group_by(LogEvent.classification).order_by(
            func.count(LogEvent.id).desc()
        ).limit(10).all()
        
        datapoints = []
        for row in result:
            classification = row[0] or "Unknown"
            datapoints.append([row[1], classification])
        
        return {
            "target": "Log Events by Classification", 
            "datapoints": datapoints,
            "type": "table"
        }
        
    except Exception as e:
        print(f"Error in get_log_events_by_classification: {e}")
        return {"target": "Log Events by Classification", "datapoints": []}

async def get_incidents_by_status(from_time: datetime, to_time: datetime) -> Dict[str, Any]:
    """Get incidents grouped by status"""
    try:
        db = get_database_session()
        
        result = db.query(
            Incident.status,
            func.count(Incident.id).label('count')
        ).filter(
            Incident.created_at.between(from_time, to_time)
        ).group_by(Incident.status).all()
        
        datapoints = []
        for row in result:
            status = row[0] or "Unknown"
            datapoints.append([row[1], status.title()])
        
        return {
            "target": "Incidents by Status",
            "datapoints": datapoints,
            "type": "table"
        }
        
    except Exception as e:
        print(f"Error in get_incidents_by_status: {e}")
        return {"target": "Incidents by Status", "datapoints": []}

async def get_top_sources(from_time: datetime, to_time: datetime) -> Dict[str, Any]:
    """Get top log sources by volume"""
    try:
        db = get_database_session()
        
        result = db.query(
            LogEvent.source,
            func.count(LogEvent.id).label('count')
        ).filter(
            LogEvent.timestamp.between(from_time, to_time)
        ).group_by(LogEvent.source).order_by(
            func.count(LogEvent.id).desc()
        ).limit(10).all()
        
        datapoints = []
        for row in result:
            source = row[0] or "Unknown"
            datapoints.append([row[1], source])
        
        return {
            "target": "Top Log Sources",
            "datapoints": datapoints,
            "type": "table"
        }
        
    except Exception as e:
        print(f"Error in get_top_sources: {e}")
        return {"target": "Top Log Sources", "datapoints": []}

async def get_severity_trend(from_time: datetime, to_time: datetime, interval: str) -> Dict[str, Any]:
    """Get average severity trend over time"""
    try:
        db = get_database_session()
        
        interval_hours = {
            "1m": 0.0167, "5m": 0.083, "15m": 0.25, "30m": 0.5,
            "1h": 1, "3h": 3, "6h": 6, "12h": 12, "1d": 24
        }.get(interval, 1)
        
        query = text(f"""
            SELECT 
                date_trunc('hour', timestamp) + 
                (EXTRACT(HOUR FROM timestamp)::int / {int(interval_hours)}) * interval '{int(interval_hours)} hours' as time_bucket,
                AVG(severity_score::float) as avg_severity
            FROM log_events 
            WHERE timestamp BETWEEN :from_time AND :to_time
            AND severity_score IS NOT NULL
            GROUP BY time_bucket
            ORDER BY time_bucket
        """)
        
        result = db.execute(query, {"from_time": from_time, "to_time": to_time}).fetchall()
        
        datapoints = []
        for row in result:
            timestamp_ms = int(row[0].timestamp() * 1000)
            avg_severity = float(row[1]) if row[1] else 0
            datapoints.append([avg_severity, timestamp_ms])
        
        return {
            "target": "Average Severity Trend",
            "datapoints": datapoints
        }
        
    except Exception as e:
        print(f"Error in get_severity_trend: {e}")
        return {"target": "Average Severity Trend", "datapoints": []}

@app.get("/logs/recent")
async def get_recent_logs(limit: int = Query(100, description="Number of recent logs to return")):
    """Get recent log events for table display"""
    try:
        db = get_database_session()
        
        logs = db.query(LogEvent).order_by(desc(LogEvent.timestamp)).limit(limit).all()
        
        result = []
        for log in logs:
            result.append({
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "source": log.source,
                "classification": log.classification,
                "severity_score": log.severity_score,
                "confidence_score": log.confidence_score,
                "message": log.message[:200] + "..." if len(log.message or "") > 200 else log.message
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent logs: {str(e)}")

@app.get("/stats/summary")
async def get_stats_summary():
    """Get summary statistics for the dashboard"""
    try:
        db = get_database_session()
        
        # Get counts for last 24 hours
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        total_logs = db.query(func.count(LogEvent.id)).scalar()
        logs_24h = db.query(func.count(LogEvent.id)).filter(
            LogEvent.timestamp >= last_24h
        ).scalar()
        
        critical_logs_24h = db.query(func.count(LogEvent.id)).filter(
            LogEvent.timestamp >= last_24h,
            LogEvent.severity_score >= 8
        ).scalar()
        
        total_incidents = db.query(func.count(Incident.id)).scalar()
        open_incidents = db.query(func.count(Incident.id)).filter(
            Incident.status == 'open'
        ).scalar()
        
        return {
            "total_logs": total_logs or 0,
            "logs_last_24h": logs_24h or 0,
            "critical_logs_24h": critical_logs_24h or 0,
            "total_incidents": total_incidents or 0,
            "open_incidents": open_incidents or 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

if __name__ == "__main__":
    # Run the API server
    port = int(os.getenv("GRAFANA_API_PORT", 8002))
    
    print(f"Starting SOC Grafana API server on port {port}")
    print("Available endpoints:")
    print(f"  - Health: http://localhost:{port}/")
    print(f"  - Recent Logs: http://localhost:{port}/logs/recent")
    print(f"  - Stats: http://localhost:{port}/stats/summary")
    print(f"  - Grafana Query: http://localhost:{port}/query")
    
    uvicorn.run(
        "grafana_api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )