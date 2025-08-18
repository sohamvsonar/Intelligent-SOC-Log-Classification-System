# JIRA Integration Setup Guide - Phase 4.2

This guide walks you through setting up JIRA integration for automated SOC incident management and ticket tracking.

## 🚀 Quick Start Overview

The JIRA integration provides:
- **Automatic ticket creation** for critical security incidents
- **Bi-directional sync** between SOC system and JIRA
- **SLA tracking** and violation alerts
- **Status updates** and assignment workflows
- **Investigation notes** and audit trails
- **Integration with Slack** for unified notifications

## 📋 Prerequisites

1. **JIRA Instance** - Cloud or self-hosted JIRA with project access
2. **API Access** - JIRA API token with appropriate permissions
3. **Project Setup** - Dedicated SOC project in JIRA
4. **Issue Types** - Incident and Security Incident issue types configured

## 🔧 Step-by-Step Setup

### Step 1: Create JIRA API Token

1. **Go to Atlassian Account Settings**: https://id.atlassian.com/manage-profile/security/api-tokens
2. **Click "Create API token"**
3. **Enter a label**: `SOC System Integration`
4. **Copy the generated token** (save this securely - you can't view it again)

### Step 2: Set Up JIRA Project

1. **Create or Access SOC Project**:
   - Project Key: `SOC` (recommended)
   - Project Name: `Security Operations Center`
   - Project Type: `Software` or `IT Service Management`

2. **Configure Issue Types**:
   - Ensure "Incident" issue type exists
   - Add "Security Incident" custom issue type if needed
   - Configure appropriate workflows

3. **Set Up Priority Levels**:
   - Highest (Critical security events)
   - High (Major incidents)
   - Medium (Standard incidents)
   - Low (Minor issues)
   - Lowest (Informational)

4. **Configure Components** (optional):
   - Security
   - Infrastructure
   - Application
   - Network

### Step 3: Configure Environment Variables

Update your `.env` file with JIRA credentials:

```env
# JIRA Integration Configuration
JIRA_SERVER_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-api-token-from-step-1
JIRA_PROJECT_KEY=SOC
JIRA_COMPONENTS=Security,Infrastructure
```

**Important**: 
- Use your actual JIRA instance URL
- Use your email address associated with JIRA account
- Use the API token (not your password)

### Step 4: Test JIRA Connection

Create a test script to verify connectivity:

```python
# test_jira.py
import sys
import os
import asyncio

sys.path.append('src')

from integrations.jira.jira_integration import get_jira_manager

async def test_jira():
    manager = get_jira_manager()
    
    if manager.is_available():
        print("✅ JIRA integration available")
        
        # Test connection
        result = manager.test_connection()
        print(f"Connection: {result['status']}")
        
        if result['status'] == 'success':
            print(f"Server: {result['server_info']['server_title']}")
            print(f"Project: {result['project_info']['name']}")
            
            # Create test incident
            test_ticket = await manager.send_test_incident()
            if test_ticket:
                print(f"✅ Test ticket: {test_ticket['ticket_id']}")
                print(f"URL: {test_ticket['ticket_url']}")
        else:
            print(f"❌ Error: {result['error']}")
    else:
        print("❌ JIRA integration not available")

if __name__ == "__main__":
    asyncio.run(test_jira())
```

Run the test:
```bash
python test_jira.py
```

## 🧪 Testing the Integration

### Test 1: Connection and Permissions

```bash
cd src
python -c "
import asyncio
from integrations.jira.jira_integration import get_jira_manager

async def test():
    manager = get_jira_manager()
    if manager.is_available():
        result = manager.test_connection()
        print(f'Status: {result[\"status\"]}')
        if result['status'] == 'success':
            print(f'Server: {result[\"server_info\"][\"server_title\"]}')
            print(f'Project: {result[\"project_info\"][\"name\"]}')
            print(f'Permissions: {len(result[\"permissions\"])} granted')
        else:
            print(f'Error: {result[\"error\"]}')
    else:
        print('JIRA not available')

asyncio.run(test())
"
```

### Test 2: Create Test Incident

```bash
cd src
python -c "
import asyncio
from integrations.jira.jira_integration import get_jira_manager

async def test_incident():
    manager = get_jira_manager()
    if manager.is_available():
        ticket = await manager.send_test_incident()
        if ticket:
            print(f'✅ Created: {ticket[\"ticket_id\"]}')
            print(f'URL: {ticket[\"ticket_url\"]}')
            print(f'Priority: {ticket[\"priority\"]}')
        else:
            print('❌ Failed to create test incident')
    else:
        print('JIRA not available')

asyncio.run(test_incident())
"
```

### Test 3: Integration with Log Processing

```bash
cd src
python -c "
from processors.high_performance_processor import HighPerformanceLogProcessor

# Test with JIRA enabled
processor = HighPerformanceLogProcessor(
    max_workers=2,
    batch_size=10,
    use_database=False,
    enable_slack=True,
    enable_jira=True  # Enable JIRA integration
)

# Create test logs that should trigger JIRA incidents
test_logs = [
    ('SecuritySystem', 'CRITICAL: Multiple failed root login attempts - potential breach'),
    ('NetworkFirewall', 'SECURITY ALERT: Advanced persistent threat detected'),
]

print('Processing logs with JIRA integration...')
results = processor.process_large_dataset(test_logs, store_in_db=False)

# Check console output for JIRA incident creation
processor.close()
"
```

## 🎯 Automatic Incident Creation Rules

### Trigger Conditions

**JIRA tickets are automatically created when:**

1. **Severity Score ≥ 9** (Highest priority incidents)
2. **Classification contains "Security"** AND severity ≥ 8
3. **Classification contains "Critical"** AND severity ≥ 8

### Ticket Details Generated

**Summary Format:**
```
[CRITICAL] Security Alert - SecuritySystem (Severity 9)
```

**Description Includes:**
- Log source and classification
- Severity score and confidence
- Full log message
- Recommended response actions
- SOC system metadata

**JIRA Fields Set:**
- **Project**: SOC (configurable)
- **Issue Type**: Security Incident or Incident
- **Priority**: Based on severity mapping
- **Labels**: soc-automated, severity-X, classification
- **Components**: As configured in .env
- **Due Date**: Based on SLA thresholds

## 📊 SLA Management

### Automatic SLA Thresholds

| Priority | Response Time | Description |
|----------|---------------|-------------|
| Highest  | 1 hour        | Critical security incidents |
| High     | 4 hours       | Major system issues |
| Medium   | 24 hours      | Standard incidents |
| Low      | 72 hours      | Minor issues |
| Lowest   | 1 week        | Informational items |

### SLA Violation Detection

The system automatically:
- Calculates due dates based on priority
- Tracks overdue tickets
- Reports SLA violations
- Escalates as needed

## 🔄 Workflow Integration

### Status Synchronization

**JIRA Statuses Mapped:**
- Open → New incident created
- In Progress → Investigation started
- Resolved → Issue fixed, awaiting verification
- Closed → Incident fully resolved

### Assignment and Escalation

**Automatic Assignment:**
- Critical incidents: Security team lead
- High priority: Available SOC analyst
- Standard: Round-robin assignment

**Escalation Rules:**
- 50% of SLA time → Manager notification
- SLA violation → Automatic escalation
- 24 hours overdue → Executive notification

## 🔗 Integration with Slack

### Unified Notifications

When both Slack and JIRA are enabled:

1. **Critical Event Detected**
2. **Slack Alert Sent** → Real-time team notification
3. **JIRA Ticket Created** → Formal incident tracking
4. **Slack Updated** → Include JIRA ticket link
5. **Investigation Progress** → Updates in both systems

### Interactive Workflow

**From Slack:**
- Click "Create Incident" → Auto-creates JIRA ticket
- Click "View Ticket" → Opens JIRA incident
- Status updates sync between systems

## 📈 Streamlit Dashboard Updates

### Enhanced Processing Options

When processing logs in Streamlit, you'll see:

```
☑️ Enable Slack Notifications
☑️ Enable JIRA Incident Creation
```

### Processing Results Display

```
✅ Processed 1000 logs successfully!

📤 Sent 5 critical alerts to Slack
🎫 Created 3 JIRA incidents
📊 1 Batch summary sent to Slack

JIRA Incidents Created:
• SOC-123: [CRITICAL] Security Alert - Multiple Login Failures
• SOC-124: [CRITICAL] Security Alert - Malware Detection  
• SOC-125: [HIGH] System Error - Database Connection Failed
```

## 🐛 Troubleshooting

### Common Issues

**"JIRA integration not available"**
- Check `.env` file has correct credentials
- Verify API token is valid (not expired)
- Ensure JIRA instance is accessible

**"Permission denied" errors**
- Verify user has permission to create issues in SOC project
- Check if issue types (Incident, Security Incident) exist
- Ensure user can set priority and assign tickets

**"Project not found"**
- Verify JIRA_PROJECT_KEY matches actual project
- Check user has access to the project
- Ensure project exists and is active

**Tickets not being created**
- Check logs for error messages
- Verify severity thresholds are being met
- Ensure classification triggers are correct

### Debug Commands

**Test connection:**
```python
from integrations.jira.jira_integration import get_jira_manager
manager = get_jira_manager()
print(manager.test_connection())
```

**Check SLA violations:**
```python
import asyncio
violations = asyncio.run(manager.get_sla_violations())
print(f"SLA violations: {len(violations)}")
```

**List open incidents:**
```python
incidents = asyncio.run(manager.get_open_incidents())
print(f"Open incidents: {len(incidents)}")
```

## 🚀 Production Deployment

### Security Best Practices

1. **API Token Security**:
   - Store tokens as environment variables
   - Rotate tokens regularly (quarterly)
   - Limit token permissions to minimum required
   - Monitor token usage

2. **Access Control**:
   - Create dedicated service account for SOC integration
   - Limit project access to SOC team members
   - Use appropriate JIRA permissions model
   - Enable audit logging

3. **Network Security**:
   - Use HTTPS for all JIRA communications
   - Consider IP whitelisting for API access
   - Monitor for unusual API activity

### Performance Optimization

1. **Batch Operations**:
   - Group multiple updates when possible
   - Use bulk operations for large datasets
   - Implement rate limiting to respect JIRA limits

2. **Caching**:
   - Cache project metadata and configurations
   - Implement connection pooling
   - Use local caching for frequently accessed data

3. **Error Handling**:
   - Implement exponential backoff for retries
   - Handle rate limiting gracefully
   - Log all API interactions for troubleshooting

## 📊 Monitoring and Metrics

### Key Metrics to Track

**Incident Creation**:
- Number of tickets created per day
- Average time from log to ticket
- Success rate of ticket creation

**SLA Performance**:
- Percentage of tickets resolved within SLA
- Average resolution time by priority
- Escalation frequency and reasons

**System Health**:
- API response times
- Error rates and types
- Integration uptime percentage

## 🔄 Next Steps

After JIRA integration is working:

1. **Test with real data** - Process your log datasets
2. **Configure custom workflows** - Align with your team's processes  
3. **Set up Grafana integration** - Visualize incident metrics
4. **Add advanced automation** - Custom escalation rules
5. **Implement feedback loops** - Analyst input for ML improvement

---

**Phase 4.2 Status**: ✅ COMPLETE - JIRA Integration Ready for Testing

**Next Phase**: Grafana Integration (Phase 4.3) for comprehensive dashboards and metrics visualization.