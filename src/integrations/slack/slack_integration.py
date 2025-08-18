"""
Slack Integration Helper for SOC Log Classification System
Integrates Slack notifications with the log processing pipeline
"""

import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))

from integrations.slack.slack_mcp_server import get_slack_server, send_alert, send_batch_summary, send_incident_notification

class SlackIntegrationManager:
    """Manages Slack integration for the SOC system"""
    
    def __init__(self, enabled: bool = True):
        """Initialize Slack integration manager"""
        self.enabled = enabled
        self.slack_server = None
        
        if self.enabled:
            try:
                self.slack_server = get_slack_server()
                if self.slack_server:
                    print("✅ Slack integration initialized")
                else:
                    print("⚠️ Slack integration failed to initialize - running without notifications")
                    self.enabled = False
            except Exception as e:
                print(f"⚠️ Slack integration disabled due to error: {e}")
                self.enabled = False
    
    def is_available(self) -> bool:
        """Check if Slack integration is available"""
        return self.enabled and self.slack_server is not None
    
    async def notify_high_severity_log(self, log_data: Dict[str, Any]) -> bool:
        """Send notification for high-severity log events"""
        if not self.is_available():
            return False
        
        try:
            severity = log_data.get('severity_score', 1)
            
            # Only notify for high-severity events (6+)
            if severity >= 6:
                result = await send_alert(log_data)
                if result:
                    print(f"📤 Slack alert sent for {log_data.get('classification', 'Unknown')} (severity {severity})")
                return result
            
            return False
            
        except Exception as e:
            print(f"❌ Error sending Slack alert: {e}")
            return False
    
    async def notify_batch_processing(self, results: List[Dict[str, Any]], 
                                    processing_stats: Dict[str, Any] = None) -> bool:
        """Send batch processing summary notification"""
        if not self.is_available() or not results:
            return False
        
        try:
            # Add processing statistics to the summary if available
            if processing_stats:
                # Find high-severity events
                high_severity_results = [r for r in results if r.get('severity_score', 0) >= 6]
                
                # Only send batch summary if there are significant events
                if len(high_severity_results) >= 5:  # 5+ high-severity events
                    # Enhance results with processing stats
                    enhanced_results = results.copy()
                    for result in enhanced_results:
                        result.update({
                            'batch_processing_time': processing_stats.get('total_time', 0),
                            'batch_throughput': processing_stats.get('throughput', 0)
                        })
                    
                    success = await send_batch_summary(enhanced_results)
                    if success:
                        print(f"📤 Batch summary sent to Slack ({len(results)} logs, {len(high_severity_results)} high-severity)")
                    return success
            
            return False
            
        except Exception as e:
            print(f"❌ Error sending batch summary: {e}")
            return False
    
    async def notify_incident_created(self, incident_data: Dict[str, Any]) -> bool:
        """Send notification when a new incident is created"""
        if not self.is_available():
            return False
        
        try:
            success = await send_incident_notification(incident_data)
            if success:
                print(f"📤 Incident notification sent: {incident_data.get('title', 'Unknown')}")
            return success
            
        except Exception as e:
            print(f"❌ Error sending incident notification: {e}")
            return False
    
    async def notify_system_status(self, status_data: Dict[str, Any]) -> bool:
        """Send system status notification"""
        if not self.is_available():
            return False
        
        try:
            if self.slack_server:
                success = await self.slack_server.send_system_status(status_data)
                if success:
                    print("📤 System status sent to Slack")
                return success
            return False
            
        except Exception as e:
            print(f"❌ Error sending system status: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Slack connection and return status"""
        if not self.slack_server:
            return {
                'status': 'disabled',
                'message': 'Slack integration not initialized'
            }
        
        try:
            test_result = self.slack_server.test_connection()
            return test_result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection test failed: {str(e)}'
            }
    
    async def send_test_alert(self) -> bool:
        """Send a test alert to verify Slack integration"""
        if not self.is_available():
            return False
        
        test_log = {
            'source': 'SOC_Test_System',
            'message': 'This is a test alert to verify Slack integration is working correctly.',
            'classification': 'System Notification',
            'severity_score': 6,
            'confidence_score': 1.0,
            'log_event_id': f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            success = await self.notify_high_severity_log(test_log)
            return success
            
        except Exception as e:
            print(f"❌ Test alert failed: {e}")
            return False

# Global instance
_slack_manager = None

def get_slack_manager(enabled: bool = True) -> SlackIntegrationManager:
    """Get or create Slack integration manager instance"""
    global _slack_manager
    
    if _slack_manager is None:
        _slack_manager = SlackIntegrationManager(enabled=enabled)
    
    return _slack_manager

def is_slack_available() -> bool:
    """Check if Slack integration is available"""
    manager = get_slack_manager()
    return manager.is_available()

# Convenience functions for async operations
async def notify_log_alert(log_data: Dict[str, Any]) -> bool:
    """Convenience function to send log alert"""
    manager = get_slack_manager()
    return await manager.notify_high_severity_log(log_data)

async def notify_batch_complete(results: List[Dict[str, Any]], 
                              stats: Dict[str, Any] = None) -> bool:
    """Convenience function to send batch completion notification"""
    manager = get_slack_manager()
    return await manager.notify_batch_processing(results, stats)

async def notify_incident(incident_data: Dict[str, Any]) -> bool:
    """Convenience function to send incident notification"""
    manager = get_slack_manager()
    return await manager.notify_incident_created(incident_data)

# Synchronous wrapper for integration with existing code
def send_slack_alert_sync(log_data: Dict[str, Any]) -> bool:
    """Synchronous wrapper for sending Slack alerts"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new loop
            import threading
            result = [False]
            
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result[0] = new_loop.run_until_complete(notify_log_alert(log_data))
                finally:
                    new_loop.close()
            
            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()
            return result[0]
        else:
            return loop.run_until_complete(notify_log_alert(log_data))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(notify_log_alert(log_data))
    except Exception as e:
        print(f"Error in synchronous Slack alert: {e}")
        return False

if __name__ == "__main__":
    # Test the Slack integration
    async def test_integration():
        print("🧪 Testing Slack Integration...")
        
        # Initialize manager
        manager = get_slack_manager()
        
        if not manager.is_available():
            print("❌ Slack integration not available")
            return
        
        # Test connection
        print("\n1. Testing connection...")
        connection_test = manager.test_connection()
        print(f"Connection test result: {connection_test.get('status', 'unknown')}")
        
        if connection_test.get('status') == 'success':
            print("   ✅ Connection successful")
            
            # Test alert
            print("\n2. Sending test alert...")
            alert_success = await manager.send_test_alert()
            if alert_success:
                print("   ✅ Test alert sent successfully")
            else:
                print("   ❌ Failed to send test alert")
            
            # Test system status
            print("\n3. Sending system status...")
            status_data = {
                'uptime': '2 days, 3 hours',
                'logs_processed_today': 15432,
                'active_incidents': 2,
                'avg_processing_time': 45.2
            }
            
            status_success = await manager.notify_system_status(status_data)
            if status_success:
                print("   ✅ System status sent successfully")
            else:
                print("   ❌ Failed to send system status")
        
        else:
            print(f"   ❌ Connection failed: {connection_test.get('message', 'Unknown error')}")
    
    # Run the test
    asyncio.run(test_integration())