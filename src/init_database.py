#!/usr/bin/env python3
"""
Database initialization script for SOC Log Classification System
This script sets up the PostgreSQL database and creates all necessary tables.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from database.connection import Base, engine, DATABASE_URL
from database.models import LogEvent, Incident, AlertRule, AnalystFeedback, SystemMetric

def main():
    """Main function to initialize the database"""
    print("SOC Log Classification System - Database Initialization")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    print(f"Database URL: {DATABASE_URL}")
    print()
    
    try:
        # Test database connection
        print("1. Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✅ Connected to PostgreSQL: {version.split(',')[0]}")
        
        # Create all tables
        print("2. Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("   ✅ Tables created successfully!")
        
        # Verify tables were created
        print("3. Verifying table creation...")
        with engine.connect() as conn:
            # Check if tables exist
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            result = conn.execute(tables_query)
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['log_events', 'incidents', 'alert_rules', 'analyst_feedback', 'system_metrics']
            
            for table in expected_tables:
                if table in tables:
                    print(f"   ✅ Table '{table}' exists")
                else:
                    print(f"   ❌ Table '{table}' missing")
                    return False
        
        # Insert sample data for testing
        print("4. Inserting sample data...")
        insert_sample_data()
        
        print()
        print("🎉 Database initialization completed successfully!")
        print()
        print("Next steps:")
        print("1. Run 'streamlit run src/app.py' to start the web application")
        print("2. Use the enhanced log classification features")
        print("3. Check the Analytics Dashboard for insights")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print()
        print("Troubleshooting:")
        print("1. Ensure PostgreSQL is installed and running")
        print("2. Create database: createdb log_classification")
        print("3. Update DATABASE_URL in .env file")
        print("4. Check database permissions")
        return False

def insert_sample_data():
    """Insert sample data for testing"""
    from database.service import DatabaseService
    
    db_service = DatabaseService()
    
    try:
        # Sample log events
        sample_logs = [
            {
                'source': 'WebServer',
                'message': 'GET /api/users HTTP/1.1 - 404 Not Found',
                'classification': 'HTTP Status',
                'confidence_score': 0.95,
                'severity_score': 4
            },
            {
                'source': 'SecuritySystem',
                'message': 'Multiple failed login attempts from IP 192.168.1.100',
                'classification': 'Security Alert',
                'confidence_score': 0.98,
                'severity_score': 9
            },
            {
                'source': 'SystemMonitor',
                'message': 'Server memory usage at 95%',
                'classification': 'Resource Usage',
                'confidence_score': 0.92,
                'severity_score': 6
            }
        ]
        
        for log_data in sample_logs:
            db_service.create_log_event(**log_data)
        
        # Sample incident
        db_service.create_incident(
            title="High Memory Usage Alert",
            severity="Medium",
            description="Server memory usage exceeded threshold"
        )
        
        # Sample performance metrics
        db_service.record_metric("processing_latency", 45.2, "latency", "bert_classifier")
        db_service.record_metric("classification_confidence", 0.94, "accuracy", "bert_classifier")
        
        print("   ✅ Sample data inserted successfully!")
        
    except Exception as e:
        print(f"   ⚠️  Warning: Could not insert sample data: {e}")
    finally:
        db_service.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)