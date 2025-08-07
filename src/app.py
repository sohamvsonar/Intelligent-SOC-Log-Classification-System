import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Import enhanced processor and database components
from processors.enhanced_processor import EnhancedLogProcessor
from database.connection import create_database, init_database
from database.service import DatabaseService

# Import legacy processors for backward compatibility
from processor_regex import regex_classify
from processor_bert import bert_classify
from processor_llm import llm_classify

def classify(logs):
    labels = []
    for source, log_msg in logs:
        label = classify_log(source, log_msg)
        labels.append(label)
    return labels

def classify_log(source, log_message):
    if source == "LegacyCRM":
        label = llm_classify(log_message)
    else:
        label = regex_classify(log_message)
        if label is None:
            label = bert_classify(log_message)
    return label

def classify_csv(input_file):
    df = pd.read_csv(input_file)

    # Perform classification
    df["target_label"] = classify(list(zip(df["source"], df["log_message"])))

    # Save the modified file
    output_file = os.path.join(os.path.dirname(__file__),"../resources/output.csv")
    df.to_csv(output_file, index=False)

    return output_file


def init_app():
    """Initialize the application and database"""
    if 'db_initialized' not in st.session_state:
        with st.spinner('Initializing database...'):
            if create_database():
                if init_database():
                    st.session_state.db_initialized = True
                    st.success("Database initialized successfully!")
                else:
                    st.error("Failed to initialize database tables")
                    return False
            else:
                st.error("Failed to connect to database. Using file-only mode.")
                st.session_state.db_initialized = False
    return st.session_state.get('db_initialized', False)

def main():
    st.set_page_config(
        page_title="SOC Log Analysis Platform",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔐 SOC Log Analysis Platform")
    st.markdown("*Phase 1: Enhanced Log Classification with Database Integration*")
    
    # Initialize database
    db_available = init_app()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Log Classification", "Analytics Dashboard", "Log History", "Single Log Test", "System Status"]
    )
    
    if page == "Log Classification":
        log_classification_page(db_available)
    elif page == "Analytics Dashboard":
        analytics_dashboard_page(db_available)
    elif page == "Log History":
        log_history_page(db_available)
    elif page == "Single Log Test":
        single_log_test_page(db_available)
    elif page == "System Status":
        system_status_page(db_available)

def log_classification_page(db_available):
    """Original log classification functionality with enhancements"""
    st.header("📊 Batch Log Classification")
    
    # Test dataset download
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("**Download Test Dataset:**")
        test_dataset_file = "test.csv"
        test_dataset_url = os.path.join(os.path.dirname(__file__), "../resources/test.csv")
        try:
            with open(test_dataset_url, "rb") as f:
                test_dataset_bytes = f.read()
            st.download_button(
                label="📥 Download Test Dataset",
                data=test_dataset_bytes,
                file_name=test_dataset_file,
                mime="text/csv"
            )
        except FileNotFoundError:
            st.warning("Test dataset not found")
    
    with col2:
        st.write("**Storage Options:**")
        store_in_db = st.checkbox(
            "Store results in database", 
            value=db_available,
            disabled=not db_available,
            help="Store classification results in PostgreSQL for analytics"
        )
    
    # File upload and processing
    st.write("**Upload CSV file to classify log messages:**")
    input_file = st.file_uploader("Upload CSV file", type="csv")
    
    if input_file is not None:
        try:
            df = pd.read_csv(input_file)
            st.write(f"Loaded {len(df)} log entries")
            
            # Show preview
            with st.expander("Preview data"):
                st.write(df.head())
            
            if st.button("🔍 Classify Logs", type="primary"):
                classify_and_display_results(df, store_in_db)
                
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

def classify_and_display_results(df, store_in_db):
    """Classify logs and display results with enhanced metrics"""
    if 'source' not in df.columns or 'log_message' not in df.columns:
        st.error("CSV must contain 'source' and 'log_message' columns")
        return
    
    processor = EnhancedLogProcessor()
    
    try:
        with st.spinner('Processing logs...'):
            progress_bar = st.progress(0)
            results = []
            
            logs = list(zip(df['source'], df['log_message']))
            total_logs = len(logs)
            
            for i, (source, log_message) in enumerate(logs):
                result = processor.classify_and_store(source, log_message, store_in_db)
                results.append(result)
                progress_bar.progress((i + 1) / total_logs)
            
        # Create results dataframe
        results_df = pd.DataFrame([
            {
                'source': r['source'],
                'log_message': r['message'],
                'classification': r['classification'],
                'confidence_score': r.get('confidence_score'),
                'severity_score': r['severity_score'],
                'processing_time_ms': r['processing_time_ms']
            }
            for r in results
        ])
        
        st.success(f"✅ Processed {len(results)} logs successfully!")
        
        # Display results
        st.subheader("Classification Results")
        st.dataframe(results_df, use_container_width=True)
        
        # Show statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Logs", len(results))
        with col2:
            avg_time = sum(r['processing_time_ms'] for r in results) / len(results)
            st.metric("Avg Processing Time", f"{avg_time:.1f}ms")
        with col3:
            classifications = [r['classification'] for r in results]
            unique_classes = len(set(classifications))
            st.metric("Unique Classifications", unique_classes)
        with col4:
            high_severity = sum(1 for r in results if r['severity_score'] >= 7)
            st.metric("High Severity Logs", high_severity)
        
        # Classification distribution chart
        if results:
            classification_counts = pd.Series([r['classification'] for r in results]).value_counts()
            fig = px.pie(
                values=classification_counts.values,
                names=classification_counts.index,
                title="Classification Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Download results
        csv_output = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv_output,
            file_name=f"classified_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error during classification: {str(e)}")
    finally:
        processor.close()

def analytics_dashboard_page(db_available):
    """Analytics dashboard showing classification trends and metrics"""
    st.header("📈 Analytics Dashboard")
    
    if not db_available:
        st.warning("Database not available. Analytics require database connection.")
        return
    
    processor = EnhancedLogProcessor()
    
    try:
        # Get analytics data
        analytics = processor.get_analytics_summary()
        
        if 'error' in analytics:
            st.error(f"Error loading analytics: {analytics['error']}")
            return
        
        # Key metrics
        col1, col2, col3 = st.columns(3)
        
        volume_stats = analytics.get('volume_statistics', {})
        with col1:
            st.metric(
                "Total Logs (24h)", 
                volume_stats.get('total_logs', 0)
            )
        with col2:
            st.metric(
                "Average Confidence", 
                f"{volume_stats.get('average_confidence', 0):.3f}"
            )
        with col3:
            classification_dist = analytics.get('classification_distribution', {})
            total_classifications = sum(classification_dist.values())
            st.metric("Total Classifications", total_classifications)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Classification distribution
            if classification_dist:
                fig = px.bar(
                    x=list(classification_dist.keys()),
                    y=list(classification_dist.values()),
                    title="Classification Distribution (7 days)",
                    labels={'x': 'Classification', 'y': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Severity distribution
            severity_dist = analytics.get('severity_distribution', {})
            if severity_dist:
                fig = px.pie(
                    values=list(severity_dist.values()),
                    names=list(severity_dist.keys()),
                    title="Severity Distribution (7 days)"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.rerun()
            
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
    finally:
        processor.close()

def log_history_page(db_available):
    """View historical log data from database"""
    st.header("📋 Log History")
    
    if not db_available:
        st.warning("Database not available. Cannot display log history.")
        return
    
    processor = EnhancedLogProcessor()
    
    try:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            limit = st.selectbox("Number of logs", [50, 100, 200, 500], index=1)
        with col2:
            source_filter = st.text_input("Filter by source (optional)")
        with col3:
            classification_filter = st.text_input("Filter by classification (optional)")
        
        # Get logs
        logs = processor.get_recent_logs(
            limit=limit,
            source=source_filter if source_filter else None,
            classification=classification_filter if classification_filter else None
        )
        
        if logs:
            # Convert to dataframe
            log_data = []
            for log in logs:
                log_data.append({
                    'Timestamp': log.timestamp,
                    'Source': log.source,
                    'Message': log.message[:100] + '...' if len(log.message) > 100 else log.message,
                    'Classification': log.classification,
                    'Confidence': log.confidence_score,
                    'Severity': log.severity_score
                })
            
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True)
            
            st.write(f"Showing {len(logs)} logs")
        else:
            st.info("No logs found matching the criteria")
            
    except Exception as e:
        st.error(f"Error loading log history: {str(e)}")
    finally:
        processor.close()

def single_log_test_page(db_available):
    """Test single log classification"""
    st.header("🔍 Single Log Test")
    
    # Input form
    with st.form("single_log_form"):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            source = st.selectbox(
                "Source System",
                ["WebServer", "LegacyCRM", "SystemMonitor", "DatabaseServer", "CustomApp"]
            )
        
        with col2:
            log_message = st.text_area(
                "Log Message",
                height=100,
                placeholder="Enter your log message here..."
            )
        
        store_result = st.checkbox(
            "Store in database", 
            value=db_available and True,
            disabled=not db_available
        )
        
        submitted = st.form_submit_button("🔍 Classify Log", type="primary")
    
    if submitted and log_message:
        processor = EnhancedLogProcessor()
        
        try:
            with st.spinner('Classifying log...'):
                result = processor.classify_and_store(
                    source, log_message, store_in_db=store_result
                )
            
            # Display results
            st.subheader("Classification Result")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Classification", result['classification'])
            with col2:
                confidence = result.get('confidence_score')
                if confidence is not None:
                    st.metric("Confidence", f"{confidence:.3f}")
                else:
                    st.metric("Confidence", "N/A")
            with col3:
                st.metric("Severity Score", result['severity_score'])
            
            # Additional info
            st.info(f"Processing time: {result['processing_time_ms']}ms")
            
            if 'log_event_id' in result:
                st.success(f"Stored in database with ID: {result['log_event_id']}")
            
        except Exception as e:
            st.error(f"Error classifying log: {str(e)}")
        finally:
            processor.close()

def system_status_page(db_available):
    """System status and health monitoring"""
    st.header("⚡ System Status")
    
    # Database status
    col1, col2 = st.columns(2)
    
    with col1:
        if db_available:
            st.success("✅ Database Connected")
        else:
            st.error("❌ Database Disconnected")
    
    with col2:
        st.info(f"🕒 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test database connection
    if st.button("🔄 Test Database Connection"):
        with st.spinner('Testing connection...'):
            db_status = create_database()
            if db_status:
                st.success("Database connection successful!")
            else:
                st.error("Database connection failed!")
    
    # Environment info
    st.subheader("Environment Information")
    env_info = {
        "Python Path": os.path.dirname(__file__),
        "Database URL": os.getenv('DATABASE_URL', 'Not configured'),
        "Timestamp": datetime.now().isoformat()
    }
    
    for key, value in env_info.items():
        st.text(f"{key}: {value}")


if __name__ == "__main__":
    main()