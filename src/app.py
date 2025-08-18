import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Import legacy processors for log classification
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
    """Initialize the application"""
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        st.success("Application initialized successfully!")
    return True

def main():
    st.set_page_config(
        page_title="SOC Log Analysis Platform",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔐 SOC Log Analysis Platform")
    st.markdown("*Streamlit Demo Version - Log Classification System*")
    
    # Initialize app
    app_available = init_app()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Log Classification", "Single Log Test"]
    )
    
    if page == "Log Classification":
        log_classification_page()
    elif page == "Single Log Test":
        single_log_test_page()

def log_classification_page():
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
        st.write("**Processing Mode:**")
        st.info("📁 File-only mode (no database storage)")
    
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
                classify_and_display_results(df)
                
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

def classify_and_display_results(df):
    """Classify logs and display results - simplified for Streamlit demo"""
    if 'source' not in df.columns or 'log_message' not in df.columns:
        st.error("CSV must contain 'source' and 'log_message' columns")
        return
    
    total_logs = len(df)
    st.info(f"📋 Processing {total_logs} logs...")
    
    # Simple classification without database or integrations
    results = []
    logs = list(zip(df['source'], df['log_message']))
    
    start_time = time.time()
    
    with st.spinner('Processing logs...'):
        progress_bar = st.progress(0)
        
        for i, (source, log_message) in enumerate(logs):
            # Use the same classification logic from classify_log function
            classification = classify_log(source, log_message)
            
            # Simple severity scoring based on classification
            severity_map = {
                'ERROR': 8,
                'CRITICAL': 9,
                'WARNING': 6,
                'INFO': 3,
                'DEBUG': 1
            }
            severity_score = severity_map.get(classification, 5)
            
            result = {
                'source': source,
                'log_message': log_message,
                'classification': classification,
                'confidence_score': 0.85,  # Static confidence for demo
                'severity_score': severity_score,
                'processing_time_ms': 10  # Static processing time for demo
            }
            results.append(result)
            
            progress_bar.progress((i + 1) / total_logs)
    
    end_time = time.time()
    
    # Create results dataframe
    results_df = pd.DataFrame(results)
    
    # Calculate performance metrics
    total_time = end_time - start_time
    avg_time_per_log = (total_time * 1000) / len(results)  # Convert to ms
    throughput = len(results) / total_time  # logs per second
    
    st.success(f"✅ Processed {len(results)} logs successfully!")
    
    # Performance summary
    performance_col1, performance_col2, performance_col3 = st.columns(3)
    with performance_col1:
        st.metric("Total Time", f"{total_time:.2f}s")
    with performance_col2:
        st.metric("Avg Time/Log", f"{avg_time_per_log:.1f}ms")
    with performance_col3:
        st.metric("Throughput", f"{throughput:.1f} logs/sec")
    
    # Display results
    st.subheader("Classification Results")
    st.dataframe(results_df, use_container_width=True)
    
    # Show statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Logs", len(results))
    with col2:
        st.metric("Processing Method", "Standard")
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

def single_log_test_page():
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
        
        st.info("📝 Demo mode - results not stored")
        
        submitted = st.form_submit_button("🔍 Classify Log", type="primary")
    
    if submitted and log_message:
        try:
            with st.spinner('Classifying log...'):
                start_time = time.time()
                classification = classify_log(source, log_message)
                end_time = time.time()
                
                # Simple severity scoring based on classification
                severity_map = {
                    'ERROR': 8,
                    'CRITICAL': 9,
                    'WARNING': 6,
                    'INFO': 3,
                    'DEBUG': 1
                }
                severity_score = severity_map.get(classification, 5)
                processing_time_ms = (end_time - start_time) * 1000
            
            # Display results
            st.subheader("Classification Result")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Classification", classification)
            with col2:
                st.metric("Confidence", "0.85")  # Static confidence for demo
            with col3:
                st.metric("Severity Score", severity_score)
            
            # Additional info
            st.info(f"Processing time: {processing_time_ms:.1f}ms")
            st.success("✅ Classification completed (demo mode)")
            
        except Exception as e:
            st.error(f"Error classifying log: {str(e)}")


if __name__ == "__main__":
    main()