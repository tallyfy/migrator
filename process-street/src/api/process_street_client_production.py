#!/usr/bin/env python3
"""
Production-Grade Process Street API Client
Implements actual Process Street API v1 with proper authentication, rate limiting, and error handling
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Generator, Union
from datetime import datetime, timedelta
from urllib.parse import urlencode
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from enum import Enum


class ProcessStreetRateLimitError(Exception):
    """Process Street rate limit exceeded"""
    pass


class ProcessStreetAuthError(Exception):
    """Process Street authentication failed"""
    pass


class ProcessStreetFieldType(str, Enum):
    """Process Street field types"""
    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    URL = "url"
    DATE = "date"
    DROPDOWN = "dropdown"
    MULTICHOICE = "multichoice"
    MEMBER = "member"
    FILE = "file"
    EMBED = "embed"
    HEADER = "header"
    CONDITIONAL = "conditional"
    APPROVALS = "approvals"
    VARIABLES = "variables"


class ProcessStreetTaskType(str, Enum):
    """Process Street task types"""
    STANDARD = "standard"
    APPROVAL = "approval"
    STOP = "stop"
    EMAIL = "email"


class ProcessStreetProductionClient:
    """
    Production Process Street API client with actual endpoints
    Implements Process Street API v1
    """
    
    BASE_URL = "https://api.process.st/api/v1"
    
    # Process Street rate limits
    RATE_LIMITS = {
        'requests_per_minute': 60,
        'requests_per_second': 2,
        'burst_limit': 10
    }
    
    def __init__(self):
        """Initialize Process Street client with actual authentication"""
        self.api_key = os.getenv('PROCESS_STREET_API_KEY')
        
        if not self.api_key:
            raise ProcessStreetAuthError("PROCESS_STREET_API_KEY required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-KEY': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.request_times = []
        self.minute_start = datetime.now()
        self.requests_this_minute = 0
        
        # Cache for frequently used data
        self.workflow_cache = {}
        self.user_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce Process Street rate limits"""
        now = datetime.now()
        
        # Reset minute counter
        if now - self.minute_start > timedelta(minutes=1):
            self.requests_this_minute = 0
            self.minute_start = now
        
        # Check requests per minute
        if self.requests_this_minute >= self.RATE_LIMITS['requests_per_minute']:
            wait_time = 60 - (now - self.minute_start).seconds
            self.logger.warning(f"Rate limit reached. Waiting {wait_time}s")
            time.sleep(wait_time)
            self.requests_this_minute = 0
            self.minute_start = datetime.now()
        
        # Check requests per second
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(seconds=1)
        ]
        
        if len(self.request_times) >= self.RATE_LIMITS['requests_per_second']:
            wait_time = 1 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                time.sleep(wait_time)
                self.request_times = []
        
        self.request_times.append(now)
        self.requests_this_minute += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, ProcessStreetRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to Process Street API"""
        self._check_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # Check for rate limit response
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise ProcessStreetRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                return response.json()
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ProcessStreetAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL PROCESS STREET API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Use workflows endpoint to test
            response = self._make_request('GET', '/workflows', {'limit': 1})
            self.logger.info("Connected to Process Street")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        # Process Street doesn't have a direct /me endpoint
        # Get from first workflow or organization data
        workflows = self.get_workflows(limit=1)
        if workflows and workflows[0].get('organizationId'):
            org = self.get_organization(workflows[0]['organizationId'])
            return org.get('owner', {})
        return {}
    
    def get_organization(self, org_id: str) -> Dict[str, Any]:
        """Get organization details"""
        return self._make_request('GET', f'/organizations/{org_id}')
    
    def get_workflows(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all workflow templates"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = self._make_request('GET', '/workflows', params)
        workflows = response.get('workflows', []) if isinstance(response, dict) else response
        
        # Cache workflows
        for workflow in workflows:
            self.workflow_cache[workflow['id']] = workflow
        
        return workflows
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed workflow information"""
        # Check cache first
        if workflow_id in self.workflow_cache:
            return self.workflow_cache[workflow_id]
        
        workflow = self._make_request('GET', f'/workflows/{workflow_id}')
        
        if workflow:
            self.workflow_cache[workflow_id] = workflow
        
        return workflow
    
    def get_workflow_runs(self, workflow_id: str = None, limit: int = 100, 
                         offset: int = 0, status: str = None) -> List[Dict[str, Any]]:
        """Get workflow runs (instances)"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        if workflow_id:
            params['workflowId'] = workflow_id
        
        if status:
            params['status'] = status  # active, completed, stopped
        
        response = self._make_request('GET', '/workflow-runs', params)
        return response.get('workflowRuns', []) if isinstance(response, dict) else response
    
    def get_workflow_run(self, run_id: str) -> Dict[str, Any]:
        """Get detailed workflow run information"""
        return self._make_request('GET', f'/workflow-runs/{run_id}')
    
    def get_tasks(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get tasks for a workflow"""
        workflow = self.get_workflow(workflow_id)
        return workflow.get('tasks', [])
    
    def get_task_instances(self, run_id: str) -> List[Dict[str, Any]]:
        """Get task instances for a workflow run"""
        run = self.get_workflow_run(run_id)
        return run.get('tasks', [])
    
    def get_form_fields(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get form fields for a workflow"""
        workflow = self.get_workflow(workflow_id)
        form_fields = []
        
        # Extract form fields from tasks
        for task in workflow.get('tasks', []):
            if task.get('formFields'):
                form_fields.extend(task['formFields'])
        
        return form_fields
    
    def get_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all users in organization"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = self._make_request('GET', '/users', params)
        users = response.get('users', []) if isinstance(response, dict) else response
        
        # Cache users
        for user in users:
            self.user_cache[user['id']] = user
        
        return users
    
    def get_groups(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all groups in organization"""
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = self._make_request('GET', '/groups', params)
        return response.get('groups', []) if isinstance(response, dict) else response
    
    def get_integrations(self, workflow_id: str = None) -> List[Dict[str, Any]]:
        """Get integrations for workflow or all"""
        if workflow_id:
            workflow = self.get_workflow(workflow_id)
            return workflow.get('integrations', [])
        
        # Get all integrations
        params = {'limit': 100}
        response = self._make_request('GET', '/integrations', params)
        return response.get('integrations', []) if isinstance(response, dict) else response
    
    def get_webhooks(self, workflow_id: str = None) -> List[Dict[str, Any]]:
        """Get webhooks for workflow or all"""
        params = {'limit': 100}
        
        if workflow_id:
            params['workflowId'] = workflow_id
        
        response = self._make_request('GET', '/webhooks', params)
        return response.get('webhooks', []) if isinstance(response, dict) else response
    
    # ============= CONDITIONAL LOGIC & VARIABLES =============
    
    def get_workflow_variables(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get variables defined in workflow"""
        workflow = self.get_workflow(workflow_id)
        return workflow.get('variables', [])
    
    def get_conditional_logic(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get conditional logic rules in workflow"""
        workflow = self.get_workflow(workflow_id)
        conditions = []
        
        # Extract conditions from tasks
        for task in workflow.get('tasks', []):
            if task.get('conditions'):
                conditions.append({
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'conditions': task['conditions']
                })
        
        return conditions
    
    def get_approvals(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get approval tasks in workflow"""
        workflow = self.get_workflow(workflow_id)
        approvals = []
        
        for task in workflow.get('tasks', []):
            if task.get('type') == ProcessStreetTaskType.APPROVAL.value:
                approvals.append({
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'approvers': task.get('approvers', []),
                    'approval_type': task.get('approvalType', 'any')  # any, all, specific
                })
        
        return approvals
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_workflow_runs(self, workflow_id: str = None, 
                               batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """
        Get workflow runs in batches
        
        Args:
            workflow_id: Optional workflow ID filter
            batch_size: Number of runs per batch
            
        Yields:
            Batches of workflow runs
        """
        offset = 0
        
        while True:
            runs = self.get_workflow_runs(
                workflow_id=workflow_id,
                limit=batch_size,
                offset=offset
            )
            
            if not runs:
                break
            
            yield runs
            
            if len(runs) < batch_size:
                break
            
            offset += batch_size
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Process Street data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'workflows': [],
            'workflow_runs': [],
            'users': [],
            'groups': [],
            'integrations': [],
            'total_workflows': 0,
            'total_runs': 0,
            'total_tasks': 0
        }
        
        # Get users
        self.logger.info("Fetching users...")
        data['users'] = self.get_users()
        
        # Get groups
        self.logger.info("Fetching groups...")
        data['groups'] = self.get_groups()
        
        # Get workflows
        self.logger.info("Fetching workflows...")
        workflows = self.get_workflows()
        
        for workflow in workflows:
            self.logger.info(f"Processing workflow: {workflow['name']}")
            
            # Get full workflow details
            workflow_data = self.get_workflow(workflow['id'])
            
            # Get form fields
            workflow_data['form_fields'] = self.get_form_fields(workflow['id'])
            
            # Get variables
            workflow_data['variables'] = self.get_workflow_variables(workflow['id'])
            
            # Get conditional logic
            workflow_data['conditional_logic'] = self.get_conditional_logic(workflow['id'])
            
            # Get approvals
            workflow_data['approvals'] = self.get_approvals(workflow['id'])
            
            # Get integrations
            workflow_data['integrations'] = self.get_integrations(workflow['id'])
            
            # Get webhooks
            workflow_data['webhooks'] = self.get_webhooks(workflow['id'])
            
            # Count tasks
            data['total_tasks'] += len(workflow_data.get('tasks', []))
            
            data['workflows'].append(workflow_data)
            data['total_workflows'] += 1
            
            # Get workflow runs
            self.logger.info(f"  Fetching runs for workflow...")
            run_count = 0
            
            for run_batch in self.batch_get_workflow_runs(workflow['id']):
                for run in run_batch:
                    # Get detailed run data
                    run_data = self.get_workflow_run(run['id'])
                    data['workflow_runs'].append(run_data)
                    run_count += 1
                
                # Rate limit pause
                time.sleep(1)
            
            data['total_runs'] += run_count
            self.logger.info(f"  Processed {run_count} runs")
        
        # Get all integrations
        self.logger.info("Fetching integrations...")
        data['integrations'] = self.get_integrations()
        
        self.logger.info(f"Export complete: {data['total_workflows']} workflows, {data['total_runs']} runs")
        
        return data
    
    # ============= PARADIGM SHIFT HELPERS =============
    
    def analyze_workflow_complexity(self, workflow_id: str) -> Dict[str, Any]:
        """
        Analyze workflow complexity for transformation
        Process Street has complex conditional logic
        """
        workflow = self.get_workflow(workflow_id)
        
        analysis = {
            'task_count': len(workflow.get('tasks', [])),
            'form_field_count': len(self.get_form_fields(workflow_id)),
            'has_conditionals': False,
            'has_approvals': False,
            'has_variables': False,
            'has_integrations': False,
            'parallel_branches': 0,
            'complexity_score': 0
        }
        
        # Check for complex features
        conditions = self.get_conditional_logic(workflow_id)
        if conditions:
            analysis['has_conditionals'] = True
            analysis['parallel_branches'] = len(conditions)
            analysis['complexity_score'] += len(conditions) * 10
        
        approvals = self.get_approvals(workflow_id)
        if approvals:
            analysis['has_approvals'] = True
            analysis['complexity_score'] += len(approvals) * 5
        
        variables = self.get_workflow_variables(workflow_id)
        if variables:
            analysis['has_variables'] = True
            analysis['complexity_score'] += len(variables) * 2
        
        integrations = self.get_integrations(workflow_id)
        if integrations:
            analysis['has_integrations'] = True
            analysis['complexity_score'] += len(integrations) * 3
        
        # Add base complexity
        analysis['complexity_score'] += analysis['task_count']
        analysis['complexity_score'] += analysis['form_field_count'] // 5
        
        # Recommend transformation strategy
        if analysis['complexity_score'] < 20:
            analysis['recommended_strategy'] = 'simple_workflow'
        elif analysis['has_conditionals']:
            analysis['recommended_strategy'] = 'conditional_to_rules'
        else:
            analysis['recommended_strategy'] = 'direct_task_mapping'
        
        return analysis
    
    def parse_form_field_value(self, field_type: str, value: Any) -> Any:
        """
        Parse form field value based on Process Street field type
        """
        if not value:
            return None
        
        if field_type == ProcessStreetFieldType.DATE.value:
            # Date fields return ISO format
            return value
        
        elif field_type == ProcessStreetFieldType.DROPDOWN.value:
            # Dropdown returns selected option
            return value
        
        elif field_type == ProcessStreetFieldType.MULTICHOICE.value:
            # Multi-choice returns array
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        elif field_type == ProcessStreetFieldType.MEMBER.value:
            # Member fields return user IDs
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        elif field_type == ProcessStreetFieldType.FILE.value:
            # File fields return URLs
            if isinstance(value, dict):
                return {
                    'url': value.get('url'),
                    'name': value.get('name'),
                    'size': value.get('size')
                }
            return value
        
        elif field_type == ProcessStreetFieldType.APPROVALS.value:
            # Approval fields return approval status
            if isinstance(value, dict):
                return {
                    'approved': value.get('approved', False),
                    'approver': value.get('approver'),
                    'approved_at': value.get('approvedAt')
                }
            return value
        
        else:
            # Default: return as-is
            return value
    
    # ============= CREATE OPERATIONS =============
    
    def create_workflow(self, name: str, description: str = None, 
                       tasks: List[Dict] = None) -> Dict[str, Any]:
        """Create a new workflow template"""
        data = {
            'name': name,
            'description': description or '',
            'tasks': tasks or []
        }
        
        return self._make_request('POST', '/workflows', data=data)
    
    def create_workflow_run(self, workflow_id: str, name: str = None, 
                          assigned_to: str = None) -> Dict[str, Any]:
        """Create a new workflow run (instance)"""
        data = {
            'workflowId': workflow_id
        }
        
        if name:
            data['name'] = name
        
        if assigned_to:
            data['assignedTo'] = assigned_to
        
        return self._make_request('POST', '/workflow-runs', data=data)
    
    def update_task_instance(self, run_id: str, task_id: str, 
                            completed: bool = None, data: Dict = None) -> Dict[str, Any]:
        """Update a task instance in a workflow run"""
        update_data = {}
        
        if completed is not None:
            update_data['completed'] = completed
        
        if data:
            update_data['data'] = data
        
        return self._make_request('PUT', f'/workflow-runs/{run_id}/tasks/{task_id}', data=update_data)
    
    def create_webhook(self, workflow_id: str, url: str, 
                      events: List[str] = None) -> Dict[str, Any]:
        """Create webhook for workflow"""
        data = {
            'workflowId': workflow_id,
            'url': url,
            'events': events or ['workflowRun.created', 'workflowRun.completed']
        }
        
        return self._make_request('POST', '/webhooks', data=data)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = ProcessStreetProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Process Street")
        
        # Get workflows
        workflows = client.get_workflows(limit=10)
        print(f"Found {len(workflows)} workflows")
        
        if workflows:
            workflow = workflows[0]
            print(f"\nWorkflow: {workflow['name']}")
            
            # Get full details
            full_workflow = client.get_workflow(workflow['id'])
            print(f"Tasks: {len(full_workflow.get('tasks', []))}")
            
            # Analyze complexity
            analysis = client.analyze_workflow_complexity(workflow['id'])
            print(f"\nComplexity analysis:")
            print(f"  - Tasks: {analysis['task_count']}")
            print(f"  - Form fields: {analysis['form_field_count']}")
            print(f"  - Has conditionals: {analysis['has_conditionals']}")
            print(f"  - Has approvals: {analysis['has_approvals']}")
            print(f"  - Complexity score: {analysis['complexity_score']}")
            print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
            
            # Get workflow runs
            runs = client.get_workflow_runs(workflow_id=workflow['id'], limit=5)
            print(f"\nFound {len(runs)} runs")
            
            for run in runs[:3]:
                print(f"  - {run.get('name', 'Unnamed')} ({run.get('status', 'unknown')})")
    
    print("\n✅ Production Process Street client ready!")