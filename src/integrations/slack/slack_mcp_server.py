"""
Slack MCP Server Integration for SOC Log Classification System
Provides real-time alerting, incident management, and collaborative features via Slack
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SlackMCPServer:
    """
    Slack MCP Server for SOC operations
    Handles alerts, notifications, and interactive commands
    """
    
    def __init__(self):
        """Initialize Slack client and configuration"""
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        
        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment variables")
        
        self.client = WebClient(token=self.bot_token)
        
        # Default channels for different alert types
        self.channels = {
            'security_alerts': os.getenv('SLACK_SECURITY_CHANNEL', '#security-alerts'),
            'system_notifications': os.getenv('SLACK_SYSTEM_CHANNEL', '#system-notifications'),
            'incident_updates': os.getenv('SLACK_INCIDENT_CHANNEL', '#incidents'),
            'general': os.getenv('SLACK_GENERAL_CHANNEL', '#soc-general')
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'critical_severity': 8,
            'high_severity': 6,
            'batch_size_threshold': 10,  # Alert if more than 10 high-severity logs in batch
        }
        
        # Rate limiting
        self.last_alert_time = {}
        self.rate_limit_minutes = 5  # Minimum 5 minutes between similar alerts
    
    def get_channel_for_severity(self, severity_score: int) -> str:
        """Determine appropriate Slack channel based on severity"""
        if severity_score >= self.alert_thresholds['critical_severity']:
            return self.channels['security_alerts']
        elif severity_score >= self.alert_thresholds['high_severity']:
            return self.channels['system_notifications']
        else:
            return self.channels['general']
    
    def should_send_alert(self, alert_key: str) -> bool:
        """Check if enough time has passed since last similar alert (rate limiting)"""
        now = datetime.now()
        if alert_key in self.last_alert_time:
            time_diff = now - self.last_alert_time[alert_key]
            if time_diff.total_seconds() < (self.rate_limit_minutes * 60):
                return False
        
        self.last_alert_time[alert_key] = now
        return True
    
    def format_log_alert(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format log data into Slack message blocks"""
        
        severity = log_data.get('severity_score', 1)
        classification = log_data.get('classification', 'Unknown')
        source = log_data.get('source', 'Unknown')
        message = log_data.get('message', '')
        confidence = log_data.get('confidence_score', 0)
        
        # Determine severity color and emoji
        if severity >= 8:
            color = "danger"
            severity_emoji = "🚨"
            severity_text = "CRITICAL"
        elif severity >= 6:
            color = "warning"
            severity_emoji = "⚠️"
            severity_text = "HIGH"
        elif severity >= 4:
            color = "#439FE0"  # Blue
            severity_emoji = "ℹ️"
            severity_text = "MEDIUM"
        else:
            color = "good"
            severity_emoji = "✅"
            severity_text = "LOW"
        
        # Create Slack message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} SOC Alert - {severity_text} Severity"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Classification:*\n{classification}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Source System:*\n{source}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity Score:*\n{severity}/10"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{confidence:.2f}" if confidence else "*Confidence:*\nN/A"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Log Message:*\n```{message[:500]}{'...' if len(message) > 500 else ''}```"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Log ID: {log_data.get('log_event_id', 'N/A')}"
                    }
                ]
            }
        ]
        
        # Add action buttons for high-severity alerts
        if severity >= 6:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🎯 Create Incident"
                        },
                        "style": "danger",
                        "value": f"create_incident_{log_data.get('log_event_id', '')}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Acknowledge"
                        },
                        "value": f"acknowledge_{log_data.get('log_event_id', '')}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔍 Investigate"
                        },
                        "value": f"investigate_{log_data.get('log_event_id', '')}"
                    }
                ]
            })
        
        return {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "fallback": f"SOC Alert: {classification} - Severity {severity}"
                }
            ]
        }
    
    async def send_single_alert(self, log_data: Dict[str, Any]) -> bool:
        """Send alert for a single high-severity log event"""
        try:
            severity = log_data.get('severity_score', 1)
            
            # Only send alerts for high-severity events
            if severity < self.alert_thresholds['high_severity']:
                return False
            
            # Rate limiting
            alert_key = f"{log_data.get('classification', 'unknown')}_{log_data.get('source', 'unknown')}"
            if not self.should_send_alert(alert_key):
                print(f"Rate limited: Skipping alert for {alert_key}")
                return False
            
            channel = self.get_channel_for_severity(severity)
            message_content = self.format_log_alert(log_data)
            
            response = self.client.chat_postMessage(
                channel=channel,
                **message_content,
                username="SOC Alert Bot",
                icon_emoji=":warning:"
            )
            
            print(f"Alert sent to {channel}: {response['ts']}")
            return True
            
        except SlackApiError as e:
            print(f"Slack API error sending alert: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Error sending Slack alert: {str(e)}")
            return False
    
    async def send_batch_summary(self, batch_results: List[Dict[str, Any]]) -> bool:
        """Send summary alert for batch processing results"""
        try:
            if not batch_results:
                return False
            
            # Calculate batch statistics
            total_logs = len(batch_results)
            critical_count = sum(1 for log in batch_results if log.get('severity_score', 0) >= 8)
            high_count = sum(1 for log in batch_results if log.get('severity_score', 0) >= 6)
            
            # Classification distribution
            classifications = {}
            for log in batch_results:
                classification = log.get('classification', 'Unknown')
                classifications[classification] = classifications.get(classification, 0) + 1
            
            # Only send batch summary if there are significant events
            if critical_count == 0 and high_count < self.alert_thresholds['batch_size_threshold']:
                return False
            
            # Format batch summary message
            classification_text = "\n".join([
                f"• {classification}: {count}" 
                for classification, count in sorted(classifications.items(), key=lambda x: x[1], reverse=True)[:5]
            ])
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 SOC Batch Processing Summary"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Logs Processed:*\n{total_logs}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Critical Alerts:*\n🚨 {critical_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*High Severity:*\n⚠️ {high_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Processing Time:*\n{datetime.now().strftime('%H:%M:%S')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Classifications:*\n{classification_text}"
                    }
                }
            ]
            
            # Add action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📈 View Dashboard"
                        },
                        "url": "http://localhost:8501",  # Link to Streamlit dashboard
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔍 View Details"
                        },
                        "value": "view_batch_details"
                    }
                ]
            })
            
            channel = self.channels['system_notifications']
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                username="SOC Batch Bot",
                icon_emoji=":bar_chart:"
            )
            
            print(f"Batch summary sent to {channel}: {response['ts']}")
            return True
            
        except SlackApiError as e:
            print(f"Slack API error sending batch summary: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Error sending Slack batch summary: {str(e)}")
            return False
    
    async def send_incident_alert(self, incident_data: Dict[str, Any]) -> bool:
        """Send incident creation/update alert"""
        try:
            incident_id = incident_data.get('id', 'Unknown')
            title = incident_data.get('title', 'Unknown Incident')
            severity = incident_data.get('severity', 'Medium')
            status = incident_data.get('status', 'open')
            assigned_to = incident_data.get('assigned_to', 'Unassigned')
            
            # Severity emoji mapping
            severity_emojis = {
                'Critical': '🚨',
                'High': '⚠️',
                'Medium': 'ℹ️',
                'Low': '✅'
            }
            
            # Status emoji mapping
            status_emojis = {
                'open': '🔓',
                'in_progress': '⚙️',
                'resolved': '✅',
                'closed': '🔒'
            }
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{severity_emojis.get(severity, '🔔')} New SOC Incident Created"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n{incident_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{severity}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:*\n{status_emojis.get(status, '❓')} {status.title()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Assigned To:*\n{assigned_to}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Title:*\n{title}"
                    }
                }
            ]
            
            # Add description if available
            if incident_data.get('description'):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{incident_data['description'][:300]}{'...' if len(incident_data.get('description', '')) > 300 else ''}"
                    }
                })
            
            # Add action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🎯 Assign to Me"
                        },
                        "value": f"assign_incident_{incident_id}",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📝 Add Note"
                        },
                        "value": f"add_note_{incident_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Mark Resolved"
                        },
                        "value": f"resolve_incident_{incident_id}",
                        "style": "danger"
                    }
                ]
            })
            
            channel = self.channels['incident_updates']
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                username="SOC Incident Bot",
                icon_emoji=":exclamation:"
            )
            
            print(f"Incident alert sent to {channel}: {response['ts']}")
            return True
            
        except SlackApiError as e:
            print(f"Slack API error sending incident alert: {e.response['error']}")
            return False
        except Exception as e:
            print(f"Error sending incident alert: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Slack connection and bot permissions"""
        try:
            # Test authentication
            auth_test = self.client.auth_test()
            bot_info = {
                'connected': True,
                'bot_id': auth_test['bot_id'],
                'user_id': auth_test['user_id'],
                'team': auth_test['team'],
                'url': auth_test['url']
            }
            
            # Test channel access
            channel_tests = {}
            for channel_type, channel_name in self.channels.items():
                try:
                    # Try to get channel info
                    channel_info = self.client.conversations_info(channel=channel_name)
                    channel_tests[channel_type] = {
                        'accessible': True,
                        'channel_id': channel_info['channel']['id'],
                        'channel_name': channel_info['channel']['name']
                    }
                except SlackApiError:
                    channel_tests[channel_type] = {
                        'accessible': False,
                        'error': f"Cannot access channel {channel_name}"
                    }
            
            return {
                'status': 'success',
                'bot_info': bot_info,
                'channel_tests': channel_tests
            }
            
        except SlackApiError as e:
            return {
                'status': 'error',
                'error': f"Slack API error: {e.response['error']}"
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Connection test failed: {str(e)}"
            }
    
    async def send_system_status(self, status_data: Dict[str, Any]) -> bool:
        """Send system status update"""
        try:
            uptime = status_data.get('uptime', 'Unknown')
            logs_processed = status_data.get('logs_processed_today', 0)
            active_incidents = status_data.get('active_incidents', 0)
            avg_processing_time = status_data.get('avg_processing_time', 0)
            
            status_emoji = "✅" if active_incidents == 0 else "⚠️"
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} SOC System Status Report"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*System Uptime:*\n{uptime}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Logs Processed Today:*\n{logs_processed:,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Active Incidents:*\n{active_incidents}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg Processing Time:*\n{avg_processing_time:.1f}ms"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
            
            channel = self.channels['general']
            response = self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                username="SOC System Bot",
                icon_emoji=":desktop_computer:"
            )
            
            print(f"System status sent to {channel}: {response['ts']}")
            return True
            
        except Exception as e:
            print(f"Error sending system status: {str(e)}")
            return False

# Singleton instance for global access
slack_server = None

def get_slack_server() -> Optional[SlackMCPServer]:
    """Get or create Slack MCP server instance"""
    global slack_server
    
    if slack_server is None:
        try:
            slack_server = SlackMCPServer()
            print("Slack MCP server initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Slack MCP server: {e}")
            return None
    
    return slack_server

# Async wrapper functions for easy integration
async def send_alert(log_data: Dict[str, Any]) -> bool:
    """Send single log alert to Slack"""
    server = get_slack_server()
    if server:
        return await server.send_single_alert(log_data)
    return False

async def send_batch_summary(batch_results: List[Dict[str, Any]]) -> bool:
    """Send batch processing summary to Slack"""
    server = get_slack_server()
    if server:
        return await server.send_batch_summary(batch_results)
    return False

async def send_incident_notification(incident_data: Dict[str, Any]) -> bool:
    """Send incident notification to Slack"""
    server = get_slack_server()
    if server:
        return await server.send_incident_alert(incident_data)
    return False

if __name__ == "__main__":
    # Test the Slack integration
    print("Testing Slack MCP Server...")
    
    # Test connection
    server = get_slack_server()
    if server:
        test_result = server.test_connection()
        print("Connection test result:", json.dumps(test_result, indent=2))
        
        # Test sending a sample alert
        sample_log = {
            'source': 'TestSystem',
            'message': 'Test security alert from SOC system',
            'classification': 'Security Alert',
            'severity_score': 8,
            'confidence_score': 0.95,
            'log_event_id': 'test-123'
        }
        
        async def test_alert():
            result = await send_alert(sample_log)
            print(f"Test alert sent: {result}")
        
        asyncio.run(test_alert())
    else:
        print("Failed to initialize Slack server")