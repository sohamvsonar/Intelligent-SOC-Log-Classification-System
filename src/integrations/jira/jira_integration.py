"""
JIRA Integration Helper for SOC Log Classification System
Integrates JIRA incident management with the log processing pipeline
"""

import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))

from integrations.jira.jira_mcp_server import get_jira_server, create_incident_ticket, update_ticket_status, add_ticket_comment

class JIRAIntegrationManager:
    """Manages JIRA integration for the SOC system"""
    
    def __init__(self, enabled: bool = True):
        """Initialize JIRA integration manager"""
        self.enabled = enabled
        self.jira_server = None
        
        if self.enabled:
            try:
                self.jira_server = get_jira_server()
                if self.jira_server:
                    print("[OK] JIRA integration initialized")
                else:
                    print("[WARNING] JIRA integration failed to initialize - running without ticket management")
                    self.enabled = False
            except Exception as e:
                print(f"[WARNING] JIRA integration disabled due to error: {e}")
                self.enabled = False
    
    def is_available(self) -> bool:
        """Check if JIRA integration is available"""
        return self.enabled and self.jira_server is not None
    
    async def create_incident_from_log(self, log_data: Dict[str, Any], 
                                     auto_create: bool = True) -> Optional[Dict[str, Any]]:
        """Create JIRA incident from log event"""
        if not self.is_available():
            return None
        
        try:
            severity_score = log_data.get('severity_score', 1)
            classification = log_data.get('classification', '')
            
            # Determine if incident should be auto-created
            should_create = auto_create and (
                severity_score >= 8 or  # Critical severity
                'Security' in classification or  # Security-related
                'Critical' in classification  # Critical classification
            )
            
            if not should_create:
                return None
            
            print(f"[TICKET] Creating JIRA incident for {classification} (severity {severity_score})")
            
            # Create incident ticket
            ticket_data = await create_incident_ticket(log_data)
            
            if ticket_data:
                print(f"[OK] JIRA ticket created: {ticket_data['ticket_id']}")
                
                # Store ticket reference in our database (if available)
                await self._store_ticket_reference(log_data, ticket_data)
                
                return ticket_data
            else:
                print(f"[ERROR] Failed to create JIRA ticket")
                return None
                
        except Exception as e:
            print(f"[ERROR] Error creating JIRA incident: {e}")
            return None
    
    async def create_incident_from_multiple_logs(self, logs: List[Dict[str, Any]], 
                                               correlation_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create JIRA incident from correlated multiple log events"""
        if not self.is_available() or not logs:
            return None
        
        try:
            # Use the most severe log as primary
            primary_log = max(logs, key=lambda x: x.get('severity_score', 0))
            
            # Enhanced incident data with correlation info
            incident_data = {
                'title': f"Correlated Security Incident - {correlation_info.get('pattern_type', 'Multiple Events')}",
                'description': self._format_correlation_description(logs, correlation_info),
                'severity': 'High',  # Correlated incidents are always high priority
                'assigned_to': correlation_info.get('assigned_to')
            }
            
            # Modify primary log data for enhanced ticket
            enhanced_log_data = primary_log.copy()
            enhanced_log_data.update({
                'severity_score': max(8, primary_log.get('severity_score', 8)),  # Ensure critical
                'classification': f"Correlated {primary_log.get('classification', 'Incident')}",
                'correlation_count': len(logs),
                'time_span': correlation_info.get('time_span', 'Unknown'),
                'affected_systems': list(set(log['source'] for log in logs))
            })
            
            ticket_data = await create_incident_ticket(enhanced_log_data, incident_data)
            
            if ticket_data:
                print(f"[OK] Correlated incident ticket created: {ticket_data['ticket_id']} ({len(logs)} events)")
                
                # Add individual logs as comments
                await self._add_correlated_logs_as_comments(ticket_data['ticket_id'], logs)
                
                return ticket_data
            
        except Exception as e:
            print(f"[ERROR] Error creating correlated JIRA incident: {e}")
            return None
    
    async def update_incident_status(self, ticket_id: str, status: str, 
                                   comment: str = None, analyst: str = None) -> bool:
        """Update JIRA incident status with optional analyst comment"""
        if not self.is_available():
            return False
        
        try:
            # Format comment with analyst attribution
            formatted_comment = comment
            if comment and analyst:
                formatted_comment = f"Updated by {analyst}: {comment}"
            
            success = await update_ticket_status(ticket_id, status, formatted_comment)
            
            if success:
                print(f"[OK] Updated JIRA {ticket_id} status to {status}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] Error updating JIRA incident status: {e}")
            return False
    
    async def add_investigation_notes(self, ticket_id: str, notes: str, 
                                    analyst: str = None) -> bool:
        """Add investigation notes to JIRA ticket"""
        if not self.is_available():
            return False
        
        try:
            success = await add_ticket_comment(ticket_id, notes, analyst)
            
            if success:
                print(f"[OK] Added investigation notes to JIRA {ticket_id}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] Error adding investigation notes: {e}")
            return False
    
    async def get_open_incidents(self, assignee: str = None) -> List[Dict[str, Any]]:
        """Get list of open SOC incidents"""
        if not self.is_available():
            return []
        
        try:
            # Build JQL query
            jql_parts = [
                f'project = {self.jira_server.project_key}',
                'labels = "soc-automated"',
                'status != "Closed"',
                'status != "Resolved"'
            ]
            
            if assignee:
                jql_parts.append(f'assignee = "{assignee}"')
            
            jql = ' AND '.join(jql_parts) + ' ORDER BY priority DESC, created DESC'
            
            tickets = await self.jira_server.search_tickets(jql)
            
            print(f"[LIST] Retrieved {len(tickets)} open incidents")
            return tickets
            
        except Exception as e:
            print(f"[ERROR] Error getting open incidents: {e}")
            return []
    
    async def get_sla_violations(self) -> List[Dict[str, Any]]:
        """Get incidents violating SLA"""
        if not self.is_available():
            return []
        
        try:
            violations = await self.jira_server.get_sla_violations()
            
            if violations:
                print(f"[WARNING] Found {len(violations)} SLA violations")
            
            return violations
            
        except Exception as e:
            print(f"[ERROR] Error getting SLA violations: {e}")
            return []
    
    async def assign_incident(self, ticket_id: str, assignee: str) -> bool:
        """Assign incident to analyst"""
        if not self.is_available():
            return False
        
        try:
            success = await self.jira_server.assign_ticket(ticket_id, assignee)
            
            if success:
                print(f"[OK] Assigned {ticket_id} to {assignee}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] Error assigning incident: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test JIRA connection and return status"""
        if not self.jira_server:
            return {
                'status': 'disabled',
                'message': 'JIRA integration not initialized'
            }
        
        try:
            test_result = self.jira_server.test_connection()
            return test_result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection test failed: {str(e)}'
            }
    
    async def send_test_incident(self) -> Optional[Dict[str, Any]]:
        """Create a test incident to verify JIRA integration"""
        if not self.is_available():
            return None
        
        test_log = {
            'source': 'SOC_Test_System',
            'message': 'This is a test incident to verify JIRA integration is working correctly.',
            'classification': 'Security Alert',
            'severity_score': 8,
            'confidence_score': 1.0,
            'log_event_id': f'test_jira_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            ticket_data = await self.create_incident_from_log(test_log, auto_create=True)
            return ticket_data
            
        except Exception as e:
            print(f"[ERROR] Test incident creation failed: {e}")
            return None
    
    def _format_correlation_description(self, logs: List[Dict[str, Any]], 
                                      correlation_info: Dict[str, Any]) -> str:
        """Format description for correlated incident"""
        lines = [
            "h3. Correlated Security Incident",
            "",
            f"*Pattern Type:* {correlation_info.get('pattern_type', 'Multiple Events')}",
            f"*Event Count:* {len(logs)}",
            f"*Time Span:* {correlation_info.get('time_span', 'Unknown')}",
            f"*Correlation Confidence:* {correlation_info.get('confidence', 'High')}",
            ""
        ]
        
        # Add affected systems
        systems = list(set(log['source'] for log in logs))
        lines.extend([
            "*Affected Systems:*",
            ", ".join(systems),
            ""
        ])
        
        # Add top classifications
        classifications = {}
        for log in logs:
            classification = log.get('classification', 'Unknown')
            classifications[classification] = classifications.get(classification, 0) + 1
        
        top_classifications = sorted(classifications.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.extend([
            "*Primary Classifications:*"
        ])
        
        for classification, count in top_classifications:
            lines.append(f"• {classification}: {count} events")
        
        lines.extend([
            "",
            "*Correlation Details:*",
            correlation_info.get('description', 'Multiple related security events detected within a short time window.')
        ])
        
        return "\n".join(lines)
    
    async def _add_correlated_logs_as_comments(self, ticket_id: str, logs: List[Dict[str, Any]]) -> None:
        """Add individual correlated logs as comments to the ticket"""
        try:
            comment_lines = [
                "h4. Related Log Events",
                ""
            ]
            
            for i, log in enumerate(logs[:10], 1):  # Limit to first 10 logs
                comment_lines.extend([
                    f"*Event {i}:* {log.get('classification', 'Unknown')} (Severity {log.get('severity_score', 'N/A')})",
                    f"*Source:* {log.get('source', 'Unknown')}",
                    f"*Time:* {log.get('timestamp', 'Unknown')}",
                    f"*Message:* {log.get('message', 'No message')[:200]}{'...' if len(log.get('message', '')) > 200 else ''}",
                    ""
                ])
            
            if len(logs) > 10:
                comment_lines.append(f"... and {len(logs) - 10} more related events")
            
            comment = "\n".join(comment_lines)
            await add_ticket_comment(ticket_id, comment, "SOC Correlation Engine")
            
        except Exception as e:
            print(f"[WARNING] Could not add correlated logs as comments: {e}")
    
    async def _store_ticket_reference(self, log_data: Dict[str, Any], 
                                    ticket_data: Dict[str, Any]) -> None:
        """Store ticket reference in database (if available)"""
        try:
            # Try to update incident record with JIRA ticket ID
            log_event_id = log_data.get('log_event_id')
            if log_event_id:
                # This would update the incident record in database
                # Implementation depends on having database service available
                pass
        except Exception as e:
            print(f"[WARNING] Could not store ticket reference: {e}")

# Global instance
_jira_manager = None

def get_jira_manager(enabled: bool = True) -> JIRAIntegrationManager:
    """Get or create JIRA integration manager instance"""
    global _jira_manager
    
    if _jira_manager is None:
        _jira_manager = JIRAIntegrationManager(enabled=enabled)
    
    return _jira_manager

def is_jira_available() -> bool:
    """Check if JIRA integration is available"""
    manager = get_jira_manager()
    return manager.is_available()

# Convenience functions for async operations
async def create_incident(log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convenience function to create incident"""
    manager = get_jira_manager()
    return await manager.create_incident_from_log(log_data)

async def update_incident(ticket_id: str, status: str, comment: str = None, 
                        analyst: str = None) -> bool:
    """Convenience function to update incident"""
    manager = get_jira_manager()
    return await manager.update_incident_status(ticket_id, status, comment, analyst)

async def add_investigation_notes(ticket_id: str, notes: str, analyst: str = None) -> bool:
    """Convenience function to add investigation notes"""
    manager = get_jira_manager()
    return await manager.add_investigation_notes(ticket_id, notes, analyst)

# Synchronous wrapper for integration with existing code
def create_incident_sync(log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for creating JIRA incidents"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new loop
            import threading
            result = [None]
            
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result[0] = new_loop.run_until_complete(create_incident(log_data))
                finally:
                    new_loop.close()
            
            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()
            return result[0]
        else:
            return loop.run_until_complete(create_incident(log_data))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(create_incident(log_data))
    except Exception as e:
        print(f"Error in synchronous JIRA incident creation: {e}")
        return None

if __name__ == "__main__":
    # Test the JIRA integration
    async def test_integration():
        print("[TEST] Testing JIRA Integration...")
        
        # Initialize manager
        manager = get_jira_manager()
        
        if not manager.is_available():
            print("[ERROR] JIRA integration not available")
            return
        
        # Test connection
        print("\n1. Testing connection...")
        connection_test = manager.test_connection()
        print(f"Connection test result: {connection_test.get('status', 'unknown')}")
        
        if connection_test.get('status') == 'success':
            print("   [OK] Connection successful")
            
            # Test incident creation
            print("\n2. Creating test incident...")
            test_ticket = await manager.send_test_incident()
            if test_ticket:
                print(f"   [OK] Test incident created: {test_ticket['ticket_id']}")
                print(f"   URL: {test_ticket['ticket_url']}")
                
                # Test adding comment
                print("\n3. Adding test comment...")
                comment_success = await manager.add_investigation_notes(
                    test_ticket['ticket_id'], 
                    "This is a test comment from the SOC system integration.",
                    "SOC_Test_Analyst"
                )
                if comment_success:
                    print("   [OK] Test comment added successfully")
            
            # Test searching incidents
            print("\n4. Getting open incidents...")
            open_incidents = await manager.get_open_incidents()
            print(f"   Found {len(open_incidents)} open incidents")
            
            # Test SLA violations
            print("\n5. Checking SLA violations...")
            violations = await manager.get_sla_violations()
            print(f"   Found {len(violations)} SLA violations")
            
        else:
            print(f"   [ERROR] Connection failed: {connection_test.get('message', 'Unknown error')}")
    
    # Run the test
    asyncio.run(test_integration())