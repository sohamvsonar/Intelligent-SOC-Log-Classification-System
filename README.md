# Log Classification System

An intelligent log classification system that uses hybrid AI approaches (BERT + LLM) to categorize log messages into actionable categories for better operational insights and automated SOC (Security Operations Center) workflows.

## 🎯 Overview

Traditional log monitoring approaches rely on basic keyword matching and log levels, missing critical operational patterns. This system provides intelligent classification into meaningful categories like Security Alerts, Resource Usage, and Workflow Errors, enabling proactive incident response and system monitoring.

### Key Features

- **Hybrid AI Classification**: Combines BERT and LLM models for optimal performance and cost
- **Actionable Categories**: Security Alert, Resource Usage, Workflow Error classifications
- **Real-time Processing**: Fast processing with confidence scoring and severity assessment
- **PostgreSQL Integration**: Persistent storage with analytics and trend analysis
- **Web Interface**: Streamlit-based dashboard with analytics and monitoring
- **JIRA & Slack Integration**: Automated incident creation and notifications
- **Performance Analytics**: Real-time metrics and system monitoring

## 🏗️ Architecture

The system uses a hybrid classification pipeline:

```
Log Input → Regex Filter → BERT Classification → LLM Fallback → Database Storage
                     ↓
              Analytics Dashboard ← PostgreSQL ← Confidence & Severity Scoring
```

### Classification Categories

1. **Security Alert**: Multiple login failures, abnormal system behavior, security breaches
2. **Resource Usage**: Memory/CPU exceeded, resource exhaustion, performance issues  
3. **Workflow Error**: Escalation failures, task assignment errors, process breakdowns

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- GROQ API key for LLM classification

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Log-Classification-System
   ```

2. **Set up PostgreSQL database**
   ```bash
   # Create database
   sudo -u postgres psql
   CREATE DATABASE log_classification;
   CREATE USER log_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE log_classification TO log_user;
   \q
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and GROQ API key
   ```

4. **Install dependencies**
   ```bash
   cd src
   pip install -r requirements.txt
   ```

5. **Initialize database**
   ```bash
   python init_database.py
   ```

6. **Launch application**
   ```bash
   streamlit run app.py
   ```

Access the application at `http://localhost:8501`

## 📊 Usage

### Web Interface

The Streamlit interface provides multiple pages:

- **Log Classification**: Upload CSV files for batch processing
- **Analytics Dashboard**: Real-time classification trends and metrics
- **Log History**: Browse and filter historical log data
- **Single Log Test**: Test individual log messages
- **System Status**: Database health and performance monitoring

## 🔧 Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://log_user:password@localhost:5432/log_classification

# API Keys
GROQ_API_KEY=your_groq_api_key_here

# Optional: JIRA Integration
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your_api_token

# Optional: Slack Integration  
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL=#security-alerts
```

## 📈 Performance Benchmarks

- **BERT Classification**: ~100ms per log
- **LLM Classification**: ~2s per log  
- **Database Storage**: ~50ms per log entry
- **Batch Processing**: 1000+ logs/minute
- **Classification Accuracy**: >85% confidence average

## 🔌 Integrations

### JIRA Integration
Automatic incident creation for high-severity security alerts:

```python
from integrations.jira.jira_integration import JiraIntegration

jira = JiraIntegration()
jira.create_security_incident(log_data, severity_level=8)
```

### Slack Integration
Real-time notifications for critical events:

```python
from integrations.slack.slack_integration import SlackIntegration

slack = SlackIntegration()
slack.send_alert(channel="#security", message="Critical security event detected")
```

## 🧪 Testing

Run the benchmark tool to test performance:

```bash
python benchmark_performance.py
```

Test with sample data:

```bash
python test.py
```

## 📁 Project Structure

```
Log-Classification-System/
├── src/
│   ├── app.py                    # Streamlit web interface
│   ├── processors/               # Classification processors
│   │   ├── enhanced_processor.py
│   │   └── high_performance_processor.py
│   ├── database/                 # Database services
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── service.py
│   ├── integrations/             # External integrations
│   │   ├── jira/
│   │   └── slack/
│   └── requirements.txt
├── docs/                         # Documentation
├── resources/                    # Sample data and datasets
├── models/                       # Trained models
└── training/                     # Training notebooks and data
```

## 🛡️ Security Considerations

- Database credentials stored in environment variables
- API keys properly secured and not committed to repository
- Input validation for all log processing endpoints
- Sanitized database queries to prevent SQL injection
- Rate limiting for API endpoints

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is part of academic research at IIT. Please contact the maintainers for usage permissions.

## 🆘 Support

For issues and questions:

1. Check the [troubleshooting guide](PHASE1_SETUP.md#-troubleshooting)
2. Review existing documentation in `/docs`
3. Create an issue with detailed error information

## 🔄 Roadmap

### Phase 2 (In Progress)
- Real-time log streaming with Kafka
- REST API endpoints
- Advanced threat severity scoring
- Model versioning and A/B testing

### Phase 3 (Planned)
- Machine learning model improvements
- Cross-system correlation analysis
- Automated remediation workflows
- Enterprise scalability enhancements

---

**Status**: Phase 1 Complete ✅ | Phase 2 In Development 🚧

Built with ❤️ for intelligent log analysis and automated SOC operations.