# Slack Integration Setup Guide - Phase 4

This guide walks you through setting up Slack integration for real-time SOC alerts and notifications.

## 🚀 Quick Start Overview

The Slack integration provides:
- **Real-time alerts** for critical security events
- **Batch processing summaries** with key metrics
- **Interactive buttons** for incident management
- **Multi-channel routing** based on severity levels
- **Rate limiting** to prevent spam

## 📋 Prerequisites

1. **Slack Workspace** - You need admin access to create a bot
2. **Slack App** - Create a new Slack app for your workspace
3. **Bot Token** - Generate bot token with necessary permissions

## 🔧 Step-by-Step Setup

### Step 1: Create Slack App

1. **Go to Slack API**: https://api.slack.com/apps
2. **Click "Create New App"**
3. **Select "From scratch"**
4. **Enter App Details**:
   - App Name: `SOC Alert Bot`
   - Workspace: Select your workspace
   - Click "Create App"

### Step 2: Configure Bot Permissions

1. **In your app dashboard, go to "OAuth & Permissions"**
2. **Add the following Bot Token Scopes**:
   ```
   channels:read        # Read channel information
   chat:write          # Send messages
   chat:write.customize # Send messages with custom username/icon
   groups:read         # Access private channels (if needed)
   im:write            # Send direct messages
   users:read          # Read user information
   ```

3. **Scroll up and click "Install to Workspace"**
4. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`)
### Step 3: Create Slack Channels

Create the following channels in your Slack workspace:

1. `#security-alerts` - For critical security events (severity 8+)
2. `#system-notifications` - For high-priority system events (severity 6-7)
3. `#incidents` - For incident management updates
4. `#soc-general` - For general SOC system notifications

**Invite your bot to these channels**:
- Type `/invite @SOC Alert Bot` in each channel

### Step 4: Configure Environment Variables

Update your `.env` file with your Slack credentials:

```env
# Slack Integration Configuration
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-from-slack-app
SLACK_SECURITY_CHANNEL=#security-alerts
SLACK_SYSTEM_CHANNEL=#system-notifications  
SLACK_INCIDENT_CHANNEL=#incidents
SLACK_GENERAL_CHANNEL=#soc-general
```

**To get your Signing Secret**:
1. Go to your Slack app dashboard
2. Navigate to "Basic Information"
3. Find "Signing Secret" and click "Show"
4. Copy the secret

## 🧪 Testing the Integration

### Test 1: Connection Test

```bash
cd src
python -c "
import sys
import os
sys.path.append('.')

from integrations.slack.slack_integration import get_slack_manager
import asyncio

async def test():
    manager = get_slack_manager()
    if manager.is_available():
        print('✅ Slack connection successful')
        # Test connection details
        result = manager.test_connection()
        print(f'Bot ID: {result.get(\"bot_info\", {}).get(\"bot_id\", \"Unknown\")}')
        print(f'Team: {result.get(\"bot_info\", {}).get(\"team\", \"Unknown\")}')
        
        # Test channels
        channels = result.get('channel_tests', {})
        for channel_type, info in channels.items():
            if info.get('accessible'):
                print(f'✅ {channel_type}: {info.get(\"channel_name\")}')
            else:
                print(f'❌ {channel_type}: {info.get(\"error\")}')
    else:
        print('❌ Slack connection failed')

asyncio.run(test())
"
```

### Test 2: Send Test Alert

```bash
cd src
python -c "
import sys
import os
import asyncio
sys.path.append('.')

from integrations.slack.slack_integration import get_slack_manager

async def test_alert():
    manager = get_slack_manager()
    if manager.is_available():
        success = await manager.send_test_alert()
        if success:
            print('✅ Test alert sent successfully!')
            print('Check your #system-notifications channel')
        else:
            print('❌ Failed to send test alert')
    else:
        print('❌ Slack not available')

asyncio.run(test_alert())
"
```

### Test 3: Integration with Log Processing

```bash
cd src
python -c "
import sys
import os
sys.path.append('.')

from processors.high_performance_processor import HighPerformanceLogProcessor

# Test with Slack enabled
processor = HighPerformanceLogProcessor(
    max_workers=2,
    batch_size=10,
    use_database=False,
    enable_slack=True
)

# Create test logs with different severity levels
test_logs = [
    ('SecuritySystem', 'CRITICAL: Multiple failed root login attempts detected from 192.168.1.100'),
    ('WebServer', 'HTTP 500 Internal Server Error - Database connection failed'),
    ('SystemMonitor', 'Normal system operation - all services running'),
]

print('Processing test logs with Slack notifications...')
results = processor.process_large_dataset(test_logs, store_in_db=False)
print(f'Processed {len(results)} logs')

processor.close()
"
```

## 📊 Message Types and Channels

### Security Alerts Channel (`#security-alerts`)
- **Critical events** (severity 8-10)
- **Security-related classifications**: Security Alert, Critical Error
- **Features**: Interactive buttons (Create Incident, Acknowledge, Investigate)

### System Notifications Channel (`#system-notifications`)
- **High-priority events** (severity 6-7)
- **System-related classifications**: Workflow Error, Resource Usage
- **Features**: Batch processing summaries, performance metrics

### Incidents Channel (`#incidents`)
- **Incident creation/updates**
- **Assignment notifications**
- **Status changes**
- **Features**: Incident management buttons (Assign, Add Note, Resolve)

### General Channel (`#soc-general`)
- **Low-priority events** (severity 1-5)
- **System status reports**
- **General SOC updates**

## 🎛️ Alert Configuration

### Severity Thresholds
```python
alert_thresholds = {
    'critical_severity': 8,     # Send immediate alerts
    'high_severity': 6,         # Include in batch summaries
    'batch_size_threshold': 10  # Send batch alert if 10+ high-severity
}
```

### Rate Limiting
- **5-minute minimum** between similar alerts
- Prevents spam from repeated similar events
- Based on classification + source combination

### Batch Summary Triggers
- **100+ logs processed** in a batch
- **5+ high-severity events** in a batch
- **Any critical events** in a batch

## 🔧 Customization Options

### Custom Channels
Update channel mappings in `.env`:
```env
SLACK_SECURITY_CHANNEL=#custom-security
SLACK_SYSTEM_CHANNEL=#custom-system
SLACK_INCIDENT_CHANNEL=#custom-incidents
SLACK_GENERAL_CHANNEL=#custom-general
```

### Alert Thresholds
Modify in `slack_mcp_server.py`:
```python
self.alert_thresholds = {
    'critical_severity': 9,    # Only most critical
    'high_severity': 7,        # Fewer high-priority alerts
    'batch_size_threshold': 15 # Require more events for batch alert
}
```

### Rate Limiting
Adjust rate limit duration:
```python
self.rate_limit_minutes = 10  # 10 minutes between similar alerts
```

## 🐛 Troubleshooting

### Common Issues

**"Slack integration not available"**
- Check that `slack-sdk` is installed: `pip install slack-sdk==3.23.0`
- Verify `.env` file has correct token format

**"Connection test failed"**
- Verify `SLACK_BOT_TOKEN` starts with `xoxb-`
- Check bot has been installed to workspace
- Ensure bot token hasn't expired

**"Cannot access channel"**
- Invite bot to the channel: `/invite @SOC Alert Bot`
- Check channel names match exactly (with #)
- Verify bot has permission to post in channel

**"Failed to send alert"**
- Check internet connection
- Verify Slack API is accessible
- Look for rate limiting messages from Slack

### Debug Mode

Enable debug logging by adding to your test scripts:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Production Deployment

### Security Best Practices
1. **Store tokens securely** - Use environment variables, not hardcoded values
2. **Rotate tokens regularly** - Generate new bot tokens periodically
3. **Limit bot permissions** - Only grant necessary scopes
4. **Monitor usage** - Check Slack API usage limits

### Performance Considerations
1. **Rate limiting** - Slack has API rate limits (1+ request per second)
2. **Message size** - Keep log messages under 4000 characters
3. **Channel organization** - Use appropriate channels to avoid noise
4. **Background processing** - Slack notifications run in separate threads

### Monitoring
- Check Slack app dashboard for usage statistics
- Monitor console logs for failed notifications
- Test alerts regularly to ensure connectivity

## 📈 Next Steps

After Slack integration is working:
1. **Test with real log data** - Process your 5000-entry dataset
2. **Configure JIRA integration** - Create incidents automatically
3. **Set up Grafana dashboards** - Visualize alerts and metrics
4. **Add more interactive commands** - Slack slash commands for SOC operations

---

**Status**: Phase 4.1 Complete ✅  
**Next**: JIRA Integration (Phase 4.2)