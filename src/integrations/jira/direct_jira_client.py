"""
Direct JIRA Client Implementation
Uses requests library instead of the JIRA library to avoid CloudFront 403 errors
"""

import os
import json
import base64
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DirectJIRAClient:
    """
    Direct JIRA client using HTTP requests instead of the jira library
    """
    
    def __init__(self):
        """Initialize direct JIRA client"""
        self.server_url = os.getenv('JIRA_SERVER_URL')
        self.username = os.getenv('JIRA_USERNAME') 
        self.api_token = os.getenv('JIRA_API_TOKEN')
        self.project_key = os.getenv('JIRA_PROJECT_KEY', 'SOC')
        
        if not all([self.server_url, self.username, self.api_token]):
            raise ValueError("JIRA credentials not found in environment variables")
        
        # Create auth header
        auth_string = f"{self.username}:{self.api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'SOC-LogClassification/1.0'
        }
        
        print(f"[OK] Direct JIRA client initialized for {self.server_url}")
        
        # Issue type mappings
        self.issue_types = {
            'incident': 'Story',  # Use Story as default since not all JIRA has Incident
            'security_incident': 'Bug', 
            'task': 'Task'
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
        
        # SLA thresholds (in hours)
        self.sla_thresholds = {
            'Highest': 1,    # 1 hour for critical
            'High': 4,       # 4 hours for high
            'Medium': 24,    # 24 hours for medium
            'Low': 72,       # 72 hours for low
            'Lowest': 168    # 1 week for lowest
        }

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> requests.Response:
        """Make HTTP request to JIRA API"""
        url = f"{self.server_url}/rest/api/2{endpoint}"
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=self.headers, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=self.headers, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response

    def test_connection(self) -> Dict[str, Any]:
        """Test JIRA connection and permissions"""
        try:
            # Test server info
            response = self._make_request('GET', '/serverInfo')
            if response.status_code != 200:
                return {
                    'status': 'error',
                    'error': f'Server info failed: {response.status_code} {response.text[:200]}'
                }
            
            server_info = response.json()
            
            # Test project access
            try:
                response = self._make_request('GET', f'/project/{self.project_key}')
                if response.status_code == 200:
                    project_info = response.json()
                    project_accessible = True
                    project_name = project_info.get('name', 'Unknown')
                else:
                    project_accessible = False
                    project_name = f"Access denied: {response.status_code}"
            except:
                project_accessible = False
                project_name = "Access denied or project not found"
            
            # Test permissions
            permissions = []
            try:
                # Check myself endpoint
                response = self._make_request('GET', '/myself')
                if response.status_code == 200:
                    permissions.append("Read user info")
                
                # Check if we can search issues
                response = self._make_request('GET', f'/search?jql=project={self.project_key}&maxResults=1')
                if response.status_code == 200:
                    permissions.append("Search issues")
                
            except Exception as perm_error:
                permissions.append(f"Permission check failed: {str(perm_error)}")
            
            return {
                'status': 'success',
                'server_info': {
                    'version': server_info.get('version', 'Unknown'),
                    'server_title': server_info.get('serverTitle', 'Unknown'),
                    'base_url': self.server_url
                },
                'project_info': {
                    'key': self.project_key,
                    'name': project_name,
                    'accessible': project_accessible
                },
                'permissions': permissions,
                'username': self.username
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Connection test failed: {str(e)}'
            }

    def create_issue(self, log_data: Dict[str, Any], incident_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a new JIRA issue"""
        try:
            severity_score = log_data.get('severity_score', 5)
            priority = self.priority_mapping.get(severity_score, 'Medium')
            classification = log_data.get('classification', 'Unknown')
            source = log_data.get('source', 'Unknown')
            
            # Create summary
            summary_parts = []
            if severity_score >= 8:
                summary_parts.append("[CRITICAL]")
            elif severity_score >= 6:
                summary_parts.append("[HIGH]")
            
            summary_parts.extend([
                classification,
                "-",
                source,
                f"(Severity {severity_score})"
            ])
            
            summary = " ".join(summary_parts)
            if len(summary) > 100:  # JIRA summary limit
                summary = summary[:97] + "..."
            
            # Create description
            description = self._format_description(log_data, incident_data)
            
            # Get available issue types first
            response = self._make_request('GET', f'/project/{self.project_key}')
            if response.status_code != 200:
                print(f"[ERROR] Cannot access project {self.project_key}: {response.status_code}")
                return None
                
            project_data = response.json()
            available_issue_types = [it['name'] for it in project_data.get('issueTypes', [])]
            
            # Choose best available issue type
            issue_type = 'Story'  # Default fallback
            if 'Bug' in available_issue_types and 'Security' in classification:
                issue_type = 'Bug'
            elif 'Story' in available_issue_types:
                issue_type = 'Story'
            elif available_issue_types:
                issue_type = available_issue_types[0]
            
            print(f"[DEBUG] Using issue type: {issue_type}")
            
            # Prepare issue data
            issue_data = {
                'fields': {
                    'project': {'key': self.project_key},
                    'summary': summary,
                    'description': description,
                    'issuetype': {'name': issue_type}
                }
            }
            
            # Add priority if available
            try:
                # Check if priority field exists
                response = self._make_request('GET', f'/priority')
                if response.status_code == 200:
                    priorities = response.json()
                    priority_names = [p['name'] for p in priorities]
                    if priority in priority_names:
                        issue_data['fields']['priority'] = {'name': priority}
            except:
                pass  # Priority field might not be available
            
            # Add labels
            labels = ['soc-automated', f'severity-{severity_score}', classification.lower().replace(' ', '-')]
            issue_data['fields']['labels'] = labels
            
            # Create the issue
            response = self._make_request('POST', '/issue', issue_data)
            
            if response.status_code == 201:
                new_issue = response.json()
                
                # Add SLA comment
                issue_key = new_issue['key']
                sla_hours = self.sla_thresholds.get(priority, 24)
                due_date = datetime.now() + timedelta(hours=sla_hours)
                sla_comment = f"SLA: {sla_hours} hours - Due by {due_date.strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.add_comment(issue_key, sla_comment)
                
                ticket_data = {
                    'ticket_id': issue_key,
                    'ticket_url': f"{self.server_url}/browse/{issue_key}",
                    'summary': summary,
                    'priority': priority,
                    'status': 'Open',
                    'created_date': datetime.now().isoformat(),
                    'sla_due_date': due_date.isoformat()
                }
                
                print(f"[OK] Created JIRA ticket: {issue_key}")
                return ticket_data
            else:
                print(f"[ERROR] Failed to create issue: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Error creating JIRA ticket: {str(e)}")
            return None

    def add_comment(self, issue_key: str, comment: str, author: str = None) -> bool:
        """Add comment to JIRA issue"""
        try:
            formatted_comment = comment
            if author:
                formatted_comment = f"*{author}:*\n{comment}"
            
            comment_data = {
                'body': formatted_comment
            }
            
            response = self._make_request('POST', f'/issue/{issue_key}/comment', comment_data)
            
            if response.status_code == 201:
                print(f"[OK] Added comment to {issue_key}")
                return True
            else:
                print(f"[ERROR] Failed to add comment: {response.status_code} {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error adding comment: {str(e)}")
            return False

    def search_issues(self, jql: str = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search JIRA issues with JQL"""
        try:
            if not jql:
                jql = f'project = {self.project_key} AND labels = "soc-automated" ORDER BY created DESC'
            
            response = self._make_request('GET', f'/search?jql={jql}&maxResults={max_results}')
            
            if response.status_code != 200:
                print(f"[ERROR] Search failed: {response.status_code} {response.text[:200]}")
                return []
            
            search_result = response.json()
            issues = search_result.get('issues', [])
            
            tickets = []
            for issue in issues:
                ticket_data = {
                    'ticket_id': issue['key'],
                    'summary': issue['fields']['summary'],
                    'status': issue['fields']['status']['name'],
                    'priority': issue['fields']['priority']['name'] if issue['fields'].get('priority') else 'None',
                    'assignee': issue['fields']['assignee']['displayName'] if issue['fields'].get('assignee') else 'Unassigned',
                    'created': issue['fields']['created'],
                    'updated': issue['fields']['updated'],
                    'ticket_url': f"{self.server_url}/browse/{issue['key']}"
                }
                tickets.append(ticket_data)
            
            return tickets
            
        except Exception as e:
            print(f"[ERROR] Error searching issues: {str(e)}")
            return []

    def _format_description(self, log_data: Dict[str, Any], incident_data: Optional[Dict[str, Any]] = None) -> str:
        """Format description for JIRA ticket"""
        
        lines = []
        
        # Header
        lines.append("h2. SOC Security Incident")
        lines.append("")
        
        # Log Information
        lines.append("h3. Log Details")
        lines.append(f"*Source System:* {log_data.get('source', 'Unknown')}")
        lines.append(f"*Classification:* {log_data.get('classification', 'Unknown')}")
        lines.append(f"*Severity Score:* {log_data.get('severity_score', 'N/A')}/10")
        
        confidence = log_data.get('confidence_score')
        if confidence is not None:
            lines.append(f"*Confidence:* {confidence:.2%}")
        
        lines.append(f"*Timestamp:* {log_data.get('timestamp', datetime.now().isoformat())}")
        lines.append("")
        
        # Log Message
        lines.append("h3. Log Message")
        log_message = log_data.get('message', log_data.get('log_message', 'No message available'))
        lines.append(f"{{code}}")
        lines.append(log_message)
        lines.append(f"{{code}}")
        lines.append("")
        
        # Additional Information
        lines.append("h3. Additional Information")
        lines.append(f"*SOC System Log ID:* {log_data.get('log_event_id', 'N/A')}")
        lines.append(f"*Created by:* SOC Automated System")
        lines.append(f"*Creation Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)

    def get_sla_violations(self) -> List[Dict[str, Any]]:
        """Get tickets that are violating SLA"""
        try:
            jql = f'project = {self.project_key} AND labels = "soc-automated" AND status != "Closed" AND status != "Resolved"'
            issues = self.search_issues(jql, 100)
            
            violations = []
            now = datetime.now()
            
            for issue in issues:
                try:
                    created_str = issue['created'][:19]  # Remove timezone part
                    created = datetime.strptime(created_str, '%Y-%m-%dT%H:%M:%S')
                    priority = issue['priority']
                    sla_hours = self.sla_thresholds.get(priority, 24)
                    due_time = created + timedelta(hours=sla_hours)
                    
                    if now > due_time:
                        overdue_hours = (now - due_time).total_seconds() / 3600
                        violations.append({
                            'ticket_id': issue['ticket_id'],
                            'summary': issue['summary'],
                            'priority': priority,
                            'created': issue['created'],
                            'due_time': due_time.isoformat(),
                            'overdue_hours': round(overdue_hours, 1),
                            'assignee': issue['assignee'],
                            'status': issue['status'],
                            'ticket_url': issue['ticket_url']
                        })
                except Exception as e:
                    print(f"[WARNING] Error processing issue {issue.get('ticket_id', 'unknown')}: {e}")
                    continue
            
            return sorted(violations, key=lambda x: x['overdue_hours'], reverse=True)
            
        except Exception as e:
            print(f"[ERROR] Error getting SLA violations: {str(e)}")
            return []

# Create singleton instance
_direct_jira_client = None

def get_direct_jira_client() -> Optional[DirectJIRAClient]:
    """Get or create direct JIRA client instance"""
    global _direct_jira_client
    
    if _direct_jira_client is None:
        try:
            _direct_jira_client = DirectJIRAClient()
        except Exception as e:
            print(f"[ERROR] Failed to initialize direct JIRA client: {e}")
            return None
    
    return _direct_jira_client