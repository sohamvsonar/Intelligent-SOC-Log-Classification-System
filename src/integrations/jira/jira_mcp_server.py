"""
JIRA MCP Server Integration for SOC Log Classification System
Provides automated incident management, ticket creation, and workflow tracking via JIRA
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .direct_jira_client import get_direct_jira_client

# Load environment variables
load_dotenv()

class JIRAMCPServer:
    """
    JIRA MCP Server for SOC incident management
    Handles automatic ticket creation, status tracking, and workflow management
    """
    
    def __init__(self):
        """Initialize JIRA client and configuration"""
        self.project_key = os.getenv('JIRA_PROJECT_KEY', 'SOC')
        
        # Initialize direct JIRA client (avoids library CloudFront issues)
        try:
            self.jira_client = get_direct_jira_client()
            if not self.jira_client:
                raise ValueError("Failed to initialize direct JIRA client")
            
            print(f"[OK] Connected to JIRA using direct client")
        except Exception as e:
            print(f"[DEBUG] Full error: {repr(e)}")
            raise ValueError(f"Failed to connect to JIRA: {str(e)}")
        
        # Issue type mappings
        self.issue_types = {
            'incident': 'Incident',
            'security_incident': 'Security Incident', 
            'task': 'Task',
            'subtask': 'Sub-task'
        }
        
        # Priority mappings based on severity scores
        self.priority_mapping = {
            10: 'Highest',
            9: 'Highest', 
            8: 'High',
            7: 'High',
            6: 'Medium',
            5: 'Medium',
            4: 'Low',
            3: 'Low',
            2: 'Lowest',
            1: 'Lowest'
        }
        
        # Status mappings
        self.status_mapping = {
            'open': 'Open',
            'in_progress': 'In Progress',
            'resolved': 'Resolved',
            'closed': 'Closed',
            'reopened': 'Reopened'
        }
        
        # SLA thresholds (in hours)
        self.sla_thresholds = {
            'Highest': 1,    # 1 hour for critical
            'High': 4,       # 4 hours for high
            'Medium': 24,    # 24 hours for medium
            'Low': 72,       # 72 hours for low
            'Lowest': 168    # 1 week for lowest
        }
    
    def get_priority_from_severity(self, severity_score: int) -> str:
        """Get JIRA priority based on severity score"""
        return self.priority_mapping.get(severity_score, 'Medium')
    
    def format_incident_description(self, log_data: Dict[str, Any], 
                                  incident_data: Optional[Dict[str, Any]] = None) -> str:
        """Format detailed description for JIRA ticket"""
        
        description = []
        
        # Header
        description.append("h2. SOC Security Incident")
        description.append("")
        
        # Log Information
        description.append("h3. Log Details")
        description.append(f"*Source System:* {log_data.get('source', 'Unknown')}")
        description.append(f"*Classification:* {log_data.get('classification', 'Unknown')}")
        description.append(f"*Severity Score:* {log_data.get('severity_score', 'N/A')}/10")
        
        confidence = log_data.get('confidence_score')
        if confidence is not None:
            description.append(f"*Confidence:* {confidence:.2%}")
        
        description.append(f"*Timestamp:* {log_data.get('timestamp', datetime.now().isoformat())}")
        description.append("")
        
        # Log Message
        description.append("h3. Log Message")
        log_message = log_data.get('message', log_data.get('log_message', 'No message available'))
        description.append(f"{{code}}")
        description.append(log_message)
        description.append(f"{{code}}")
        description.append("")
        
        # Incident Details (if provided)
        if incident_data:
            description.append("h3. Incident Information")
            if incident_data.get('description'):
                description.append(incident_data['description'])
            
            if incident_data.get('assigned_to'):
                description.append(f"*Initially Assigned To:* {incident_data['assigned_to']}")
            description.append("")
        
        # Recommended Actions
        description.append("h3. Recommended Actions")
        severity = log_data.get('severity_score', 1)
        classification = log_data.get('classification', '')
        
        if severity >= 8 and 'Security' in classification:
            description.extend([
                "# Immediately isolate affected system",
                "# Review access logs for the past 24 hours", 
                "# Notify security team and management",
                "# Document all findings and actions taken",
                "# Consider forensic analysis if data breach suspected"
            ])
        elif severity >= 6:
            description.extend([
                "# Investigate the root cause",
                "# Check system health and performance",
                "# Review recent changes or deployments",
                "# Monitor for additional related events", 
                "# Update stakeholders on progress"
            ])
        else:
            description.extend([
                "# Monitor system for recurring issues",
                "# Review and update monitoring thresholds",
                "# Document resolution for future reference"
            ])
        
        description.append("")
        
        # Additional Information
        description.append("h3. Additional Information")
        description.append(f"*SOC System Log ID:* {log_data.get('log_event_id', 'N/A')}")
        description.append(f"*Created by:* SOC Automated System")
        description.append(f"*Creation Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(description)
    
    async def create_incident_ticket(self, log_data: Dict[str, Any], 
                                   incident_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a new JIRA ticket for a security incident"""
        try:
            return self.jira_client.create_issue(log_data, incident_data)
        except Exception as e:
            print(f"[ERROR] Error creating JIRA ticket: {str(e)}")
            return None
    
    async def update_ticket_status(self, ticket_id: str, new_status: str, 
                                 comment: str = None) -> bool:
        """Update JIRA ticket status"""
        try:
            issue = self.jira_client.issue(ticket_id)
            
            # Get available transitions
            transitions = self.jira_client.transitions(issue)
            transition_id = None
            
            # Find transition that leads to desired status
            for transition in transitions:
                if transition['to']['name'].lower() == new_status.lower():
                    transition_id = transition['id']
                    break
            
            if transition_id:
                # Perform transition
                self.jira_client.transition_issue(issue, transition_id)
                
                # Add comment if provided
                if comment:
                    self.jira_client.add_comment(issue, f"Status updated to {new_status}: {comment}")
                
                print(f"[OK] Updated JIRA {ticket_id} status to {new_status}")
                return True
            else:
                print(f"[WARNING] No transition available to status '{new_status}' for {ticket_id}")
                return False
                
        except JIRAError as e:
            print(f"[ERROR] JIRA error updating status: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Error updating JIRA ticket status: {str(e)}")
            return False
    
    async def add_comment_to_ticket(self, ticket_id: str, comment: str, 
                                  author: str = None) -> bool:
        """Add comment to JIRA ticket"""
        try:
            return self.jira_client.add_comment(ticket_id, comment, author)
        except Exception as e:
            print(f"[ERROR] Error adding comment to JIRA: {str(e)}")
            return False
    
    async def get_ticket_info(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a JIRA ticket"""
        try:
            issue = self.jira_client.issue(ticket_id)
            
            ticket_info = {
                'ticket_id': issue.key,
                'summary': issue.fields.summary,
                'description': issue.fields.description,
                'status': issue.fields.status.name,
                'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                'assignee': issue.fields.assignee.name if issue.fields.assignee else None,
                'reporter': issue.fields.reporter.name if issue.fields.reporter else None,
                'created': issue.fields.created,
                'updated': issue.fields.updated,
                'resolution': issue.fields.resolution.name if issue.fields.resolution else None,
                'labels': issue.fields.labels,
                'ticket_url': f"{self.server_url}/browse/{issue.key}"
            }
            
            return ticket_info
            
        except JIRAError as e:
            print(f"[ERROR] JIRA error getting ticket info: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Error getting JIRA ticket info: {str(e)}")
            return None
    
    async def search_tickets(self, jql: str = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search JIRA tickets with JQL query"""
        try:
            return self.jira_client.search_issues(jql, max_results)
        except Exception as e:
            print(f"[ERROR] Error searching JIRA tickets: {str(e)}")
            return []
    
    async def assign_ticket(self, ticket_id: str, assignee: str) -> bool:
        """Assign ticket to a user"""
        try:
            issue = self.jira_client.issue(ticket_id)
            
            # Try to assign
            try:
                issue.update(fields={'assignee': {'name': assignee}})
                print(f"[OK] Assigned JIRA {ticket_id} to {assignee}")
                return True
            except:
                # If assignment fails, add comment instead
                comment = f"Attempted to assign to {assignee}, but user may not exist or lack permissions."
                self.jira_client.add_comment(issue, comment)
                print(f"[WARNING] Could not assign {ticket_id} to {assignee}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error assigning JIRA ticket: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test JIRA connection and permissions"""
        try:
            return self.jira_client.test_connection()
        except Exception as e:
            return {
                'status': 'error', 
                'error': f"Connection test failed: {str(e)}"
            }
    
    async def get_sla_violations(self) -> List[Dict[str, Any]]:
        """Get tickets that are violating SLA"""
        try:
            return self.jira_client.get_sla_violations()
        except Exception as e:
            print(f"[ERROR] Error getting SLA violations: {str(e)}")
            return []

# Singleton instance for global access
jira_server = None

def get_jira_server() -> Optional[JIRAMCPServer]:
    """Get or create JIRA MCP server instance"""
    global jira_server
    
    if jira_server is None:
        try:
            jira_server = JIRAMCPServer()
            print("[OK] JIRA MCP server initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize JIRA MCP server: {e}")
            return None
    
    return jira_server

# Async wrapper functions for easy integration
async def create_incident_ticket(log_data: Dict[str, Any], 
                               incident_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Create incident ticket in JIRA"""
    server = get_jira_server()
    if server:
        return await server.create_incident_ticket(log_data, incident_data)
    return None

async def update_ticket_status(ticket_id: str, status: str, comment: str = None) -> bool:
    """Update JIRA ticket status"""
    server = get_jira_server()
    if server:
        return await server.update_ticket_status(ticket_id, status, comment)
    return False

async def add_ticket_comment(ticket_id: str, comment: str, author: str = None) -> bool:
    """Add comment to JIRA ticket"""
    server = get_jira_server()
    if server:
        return await server.add_comment_to_ticket(ticket_id, comment, author)
    return False

if __name__ == "__main__":
    # Test the JIRA integration
    print("Testing JIRA MCP Server...")
    
    # Test connection
    server = get_jira_server()
    if server:
        test_result = server.test_connection()
        print("Connection test result:", json.dumps(test_result, indent=2, default=str))
        
        # Test creating a sample incident
        sample_log = {
            'source': 'TestSystem',
            'message': 'Test security incident from SOC system',
            'classification': 'Security Alert',
            'severity_score': 8,
            'confidence_score': 0.95,
            'log_event_id': 'test-jira-123',
            'timestamp': datetime.now().isoformat()
        }
        
        async def test_ticket_creation():
            ticket_data = await create_incident_ticket(sample_log)
            if ticket_data:
                print(f"[OK] Test ticket created: {ticket_data['ticket_id']}")
                print(f"URL: {ticket_data['ticket_url']}")
            else:
                print("[ERROR] Failed to create test ticket")
        
        asyncio.run(test_ticket_creation())
    else:
        print("[ERROR] Failed to initialize JIRA server")