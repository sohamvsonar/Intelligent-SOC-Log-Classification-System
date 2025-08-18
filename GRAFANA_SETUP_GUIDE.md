# Grafana Integration Setup Guide

This guide will help you set up Grafana dashboard integration with your SOC Log Classification System to visualize past 100 logs and analytics.

## 🏗️ Architecture Overview

```
SOC System → PostgreSQL Database → FastAPI → Grafana Dashboard
```

- **PostgreSQL**: Stores processed log data
- **FastAPI**: Serves data to Grafana via REST API
- **Grafana**: Visualizes data with advanced charts and dashboards

## 📋 Prerequisites

- Python 3.10+ with your existing venv
- Docker (for Grafana)
- PostgreSQL database with processed logs
- Existing SOC system running

## 🚀 Quick Setup (Recommended)

### Step 1: Install Dependencies

```bash
# Activate your venv
.venv/Scripts/activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Install additional requirements
pip install fastapi==0.104.1 uvicorn==0.24.0
```

### Step 2: Start Grafana with Docker

```bash
# Option A: Use our pre-configured Docker Compose
docker-compose -f docker-compose-grafana.yml up -d

# Option B: Manual Docker run
docker run -d \
  --name soc-grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=socsystem" \
  -e "GF_INSTALL_PLUGINS=grafana-simple-json-datasource" \
  grafana/grafana:latest
```

### Step 3: Start SOC API Server

```bash
# From your project root
cd src/integrations/grafana
python grafana_api.py
```

You should see:
```
Starting SOC Grafana API server on port 8002
Available endpoints:
  - Health: http://localhost:8002/
  - Recent Logs: http://localhost:8002/logs/recent
  - Stats: http://localhost:8002/stats/summary
  - Grafana Query: http://localhost:8002/query
```

### Step 4: Auto-Setup Grafana

```bash
# From the grafana directory
python grafana_setup.py
```

This will:
- ✅ Configure Grafana data source
- ✅ Import SOC dashboard
- ✅ Set up all connections

### Step 5: Access Your Dashboard

1. **Open Grafana**: http://localhost:3000
2. **Login**: admin / socsystem
3. **Navigate**: Home → Dashboards → SOC Log Classification Dashboard
4. **Configure time range**: Last 7 days (or as needed)

## 📊 Dashboard Features

### Overview Panels:
- **Log Events Over Time**: Timeline visualization
- **Critical Events Alert**: Real-time critical log count
- **Log Events by Severity**: Pie chart breakdown
- **Average Severity Trend**: Trend line over time

### Analysis Panels:
- **Top Log Classifications**: Bar chart of most common types
- **Top Log Sources**: Systems generating most logs
- **Incident Status Overview**: Donut chart of incident statuses
- **Recent Log Events**: Detailed table with severity color coding

### Key Metrics:
- Total logs processed
- Critical events (severity ≥ 8)
- Classification distribution
- Source system analysis

## 🔧 Manual Setup (Advanced)

### 1. Install Grafana Manually

**Windows:**
```bash
# Download and install from https://grafana.com/grafana/download
# Or use Chocolatey
choco install grafana
```

**Linux:**
```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana
```

### 2. Configure Grafana

Edit `/etc/grafana/grafana.ini` or create custom config:
```ini
[server]
http_port = 3000

[security]
admin_password = socsystem

[plugins]
enable_alpha = false
```

### 3. Install Simple JSON Plugin

```bash
grafana-cli plugins install grafana-simple-json-datasource
```

### 4. Manual Data Source Setup

1. **Go to**: Configuration → Data Sources
2. **Add**: Simple JSON
3. **Configure**:
   - Name: `SOC_API`
   - URL: `http://localhost:8002`
   - Access: Server (default)

### 5. Import Dashboard

1. **Go to**: Create → Import
2. **Upload**: `src/integrations/grafana/soc_dashboard.json`
3. **Select**: SOC_API data source
4. **Import**

## 🧪 Testing Your Setup

### 1. Test API Endpoints

```bash
# Health check
curl http://localhost:8002/

# Recent logs
curl http://localhost:8002/logs/recent?limit=10

# Stats summary
curl http://localhost:8002/stats/summary
```

### 2. Test Grafana Connection

```bash
# Test Grafana health
curl http://localhost:3000/api/health

# Test data source (after setup)
curl -u admin:socsystem http://localhost:3000/api/datasources
```

### 3. Test Dashboard Data

1. Open Grafana dashboard
2. Check each panel loads data
3. Verify time range filtering works
4. Test refresh functionality

## 🎯 Using Your Dashboard

### Daily Operations:
1. **Monitor** critical events in real-time
2. **Analyze** trends and patterns
3. **Track** incident resolution
4. **Review** source system health

### Time Range Options:
- **Last 1 hour**: Real-time monitoring
- **Last 24 hours**: Daily analysis
- **Last 7 days**: Weekly trends (recommended)
- **Custom range**: Historical analysis

### Alert Setup:
- Configure alerts for critical event thresholds
- Set up notifications via Slack/email
- Create SLA monitoring rules

## 🔄 Integration with SOC Workflow

### In Streamlit Dashboard:
1. Go to **"Grafana Dashboard"** page
2. Check service status
3. Use quick actions to start services
4. View data preview
5. Click **"Open Grafana"** for full analytics

### Regular Updates:
- Dashboard refreshes every 5 minutes
- Real-time updates when processing new logs
- Historical data preserved in database

## 🐛 Troubleshooting

### Common Issues:

**API Not Starting:**
```bash
# Check if port 8002 is in use
netstat -an | grep 8002

# Check database connection
python -c "from database.connection import get_database_session; print('DB OK')"
```

**Grafana Connection Issues:**
```bash
# Check Grafana is running
docker ps | grep grafana

# Check Grafana logs
docker logs soc-grafana
```

**No Data in Dashboard:**
```bash
# Verify you have logs in database
python -c "from database.service import DatabaseService; print(DatabaseService().get_log_count())"

# Test API data
curl http://localhost:8002/logs/recent
```

**Dashboard Panels Empty:**
1. Check time range (try "Last 7 days")
2. Verify data source connection
3. Check browser console for errors
4. Refresh dashboard

### Environment Variables:

Add to your `.env` file:
```env
# Grafana Configuration
GRAFANA_URL=http://localhost:3000
GRAFANA_USER=admin
GRAFANA_PASSWORD=socsystem
SOC_API_URL=http://localhost:8002
GRAFANA_API_PORT=8002
```

## 📈 Next Steps

1. **Customize Dashboard**: Add your own panels and metrics
2. **Set up Alerts**: Configure thresholds and notifications
3. **Create Additional Dashboards**: For specific use cases
4. **Integrate with Slack**: Dashboard links in Slack notifications
5. **Schedule Reports**: Export dashboard data periodically

## 💡 Tips for Best Experience

- **Process logs regularly** to keep dashboard updated
- **Use appropriate time ranges** (7 days for trends)
- **Monitor critical events** daily
- **Customize dashboard** for your specific needs
- **Set up alerts** for proactive monitoring

Your Grafana dashboard is now ready to provide powerful analytics and visualizations for your SOC operations! 🎉