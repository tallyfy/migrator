"""
Process Street API Client v2
Enhanced client with correct API endpoints and response handling
Based on Process Street API v1.1 documentation
"""

import requests
import time
import json
import logging
from typing import Dict, List, Optional, Any, Generator, Tuple
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
import backoff
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessStreetEndpoints:
    """Process Street API endpoints"""
    # Core endpoints from API v1.1
    WORKFLOWS = '/workflows'  # Templates
    CHECKLISTS = '/checklists'  # Workflow runs
    TASKS = '/tasks'
    FORM_FIELDS = '/form-fields'
    USERS = '/users'
    GROUPS = '/groups'
    APPROVALS = '/approvals'
    ASSIGNMENTS = '/assignments'
    ORGANIZATIONS = '/organizations'
    WEBHOOKS = '/webhooks'
    DATA_SETS = '/data-sets'


class ProcessStreetClient:
    """Enhanced client for Process Street API v1.1"""
    
    def __init__(self, api_key: str, base_url: str = "https://public-api.process.st/api/v1.1", 
                 organization_id: Optional[str] = None):
        """
        Initialize Process Street API client
        
        Args:
            api_key: Process Street API key (Enterprise plan required)
            base_url: API base URL with version
            organization_id: Optional organization ID to scope requests
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.organization_id = organization_id
        
        # Create session with authentication
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-KEY': api_key,
            'Content-Type': 'application/json',
            
            'Accept': 'application/json',
            'User-Agent': 'ProcessStreet-Tallyfy-Migrator/2.0'
        })
        
        # Rate limiting configuration
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 2 requests per second max
        self.rate_limit_backoff = 60  # Default backoff for rate limits
        
        # Statistics tracking
        self.stats = {
            'api_calls': 0,
            'rate_limits_hit': 0,
            'errors': 0,
            'retries': 0,
            'data_fetched': {},
            'last_error': None,
            'start_time': datetime.utcnow()
        }
        
        # Validate API key on initialization
        self._validate_api_key()
    
    def _validate_api_key(self):
        """Validate API key by making a test request"""
        try:
            # Try to get current user
            response = self._make_request('GET', '/users/me')
            logger.info(f"API key validated. User: {response.get('data', {}).get('attributes', {}).get("text", 'Unknown')}")
        except Exception as e:
            logger.error(f"Invalid API key or connection error: {e}")
            raise ValueError(f"Failed to validate Process Street API key: {e}")
    
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.Timeout),
        max_tries=3,
        max_time=30
    )
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request with proper error handling and rate limiting
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/workflows')
            **kwargs: Additional request parameters
            
        Returns:
            API response as dictionary
        """
        # Apply rate limiting
        self._rate_limit()
        
        # Build full URL
        if endpoint.startswith('http'):
            url = endpoint  # Full URL provided (for pagination)
        else:
            url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        # Add organization filter if specified
        if self.organization_id and 'params' in kwargs:
            if 'organizationId' not in kwargs['params']:
                kwargs['params']['organizationId'] = self.organization_id
        
        logger.debug(f"Making {method} request to {url}")
        self.stats['api_calls'] += 1
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                self.stats['rate_limits_hit'] += 1
                retry_after = int(response.headers.get('Retry-After', self.rate_limit_backoff))
                logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                time.sleep(retry_after)
                self.stats['retries'] += 1
                return self._make_request(method, endpoint, **kwargs)
            
            # Handle other HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.stats['errors'] += 1
                self.stats['last_error'] = error_msg
                logger.error(error_msg)
                response.raise_for_status()
            
            # Parse JSON response
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                # Non-JSON response (shouldn't happen with this API)
                return {'data': response.text}
                
        except requests.exceptions.RequestException as e:
            self.stats['errors'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"API request failed: {e}")
            raise
    
    def _get_paginated(self, endpoint: str, params: Optional[Dict] = None) -> Generator[Dict, None, None]:
        """
        Get paginated results using Process Street's link-based pagination
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Yields:
            Individual items from paginated responses
        """
        if params is None:
            params = {}
        
        # Process Street uses 20 items per page by default
        if 'limit' not in params:
            params['limit'] = 20
        
        next_url = None
        first_request = True
        
        while first_request or next_url:
            if first_request:
                response = self._make_request('GET', endpoint, params=params)
                first_request = False
            else:
                # Use the next URL directly
                response = self._make_request('GET', next_url)
            
            # Extract data array
            data = response.get('data', [])
            
            # Yield individual items
            for item in data:
                yield item
            
            # Check for next page using links
            links = response.get('links', {})
            next_url = links.get('next')
            
            # Stop if no more pages
            if not next_url or len(data) == 0:
                break
            
            # Small delay between pages to be respectful
            time.sleep(0.2)
    
    # ==================== Organization Methods ====================
    
    def get_organization(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """Get organization details"""
        org_id = org_id or self.organization_id
        if not org_id:
            # Try to get from current user
            user = self._make_request('GET', '/users/me')
            org_id = user.get('data', {}).get('relationships', {}).get('organization', {}).get('data', {}).get('id')
            
        if not org_id:
            raise ValueError("Organization ID required")
        
        response = self._make_request('GET', f'/organizations/{org_id}')
        return response.get('data', {})
    
    def list_organizations(self) -> List[Dict[str, Any]]:
        """List all accessible organizations"""
        return list(self._get_paginated('/organizations'))
    
    # ==================== Workflow (Template) Methods ====================
    
    def list_workflows(self, active_only: bool = True, **filters) -> List[Dict[str, Any]]:
        """
        List all workflows (templates)
        
        Args:
            active_only: Only return active workflows
            **filters: Additional filters
            
        Returns:
            List of workflow objects
        """
        params = filters.copy()
        if active_only:
            params['active'] = 'true'
        
        workflows = list(self._get_paginated(ProcessStreetEndpoints.WORKFLOWS, params=params))
        self.stats['data_fetched']['workflows'] = len(workflows)
        logger.info(f"Fetched {len(workflows)} workflows")
        return workflows
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get detailed workflow information including tasks and form fields
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Complete workflow object
        """
        response = self._make_request('GET', f'{ProcessStreetEndpoints.WORKFLOWS}/{workflow_id}')
        workflow = response.get('data', {})
        
        # Fetch related data
        workflow['tasks'] = self.get_workflow_tasks(workflow_id)
        workflow['form_fields'] = self.get_workflow_form_fields(workflow_id)
        
        return workflow
    
    def get_workflow_tasks(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get all task templates for a workflow"""
        params = {'workflowId': workflow_id}
        tasks = list(self._get_paginated(f'{ProcessStreetEndpoints.WORKFLOWS}/{workflow_id}/tasks', params=params))
        logger.debug(f"Fetched {len(tasks)} tasks for workflow {workflow_id}")
        return tasks
    
    def get_workflow_form_fields(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get all form field definitions for a workflow"""
        params = {'workflowId': workflow_id}
        fields = list(self._get_paginated(f'{ProcessStreetEndpoints.WORKFLOWS}/{workflow_id}/form-fields', params=params))
        logger.debug(f"Fetched {len(fields)} form fields for workflow {workflow_id}")
        return fields
    
    # ==================== Checklist (Workflow Run) Methods ====================
    
    def list_checklists(self, workflow_id: Optional[str] = None, status: Optional[str] = None, **filters) -> List[Dict[str, Any]]:
        """
        List checklists (workflow runs)
        
        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status (active, completed, stopped)
            **filters: Additional filters
            
        Returns:
            List of checklist objects
        """
        params = filters.copy()
        if workflow_id:
            params['workflowId'] = workflow_id
        if status:
            params['status'] = status
        
        checklists = list(self._get_paginated(ProcessStreetEndpoints.CHECKLISTS, params=params))
        self.stats['data_fetched']['checklists'] = len(checklists)
        logger.info(f"Fetched {len(checklists)} checklists")
        return checklists
    
    def get_checklist(self, checklist_id: str, include_tasks: bool = True) -> Dict[str, Any]:
        """
        Get detailed checklist information
        
        Args:
            checklist_id: Checklist ID
            include_tasks: Include task completion status
            
        Returns:
            Complete checklist object
        """
        response = self._make_request('GET', f'{ProcessStreetEndpoints.CHECKLISTS}/{checklist_id}')
        checklist = response.get('data', {})
        
        if include_tasks:
            # Get task completion status
            checklist['tasks'] = self.get_checklist_tasks(checklist_id)
            
        # Get form field values
        checklist['form_values'] = self.get_checklist_form_values(checklist_id)
        
        return checklist
    
    def get_checklist_tasks(self, checklist_id: str) -> List[Dict[str, Any]]:
        """Get task instances for a checklist with completion status"""
        tasks = list(self._get_paginated(f'{ProcessStreetEndpoints.CHECKLISTS}/{checklist_id}/tasks'))
        logger.debug(f"Fetched {len(tasks)} task instances for checklist {checklist_id}")
        return tasks
    
    def get_checklist_form_values(self, checklist_id: str) -> Dict[str, Any]:
        """Get form field values for a checklist"""
        response = self._make_request('GET', f'{ProcessStreetEndpoints.CHECKLISTS}/{checklist_id}/form-field-values')
        return response.get('data', {})
    
    def create_checklist(self, workflow_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new checklist from a workflow
        
        Args:
            workflow_id: Source workflow ID
            name: Checklist name
            **kwargs: Additional checklist properties
            
        Returns:
            Created checklist object
        """
        data = {
            'workflowId': workflow_id,
            'name': name,
            **kwargs
        }
        
        response = self._make_request('POST', ProcessStreetEndpoints.CHECKLISTS, json=data)
        return response.get('data', {})
    
    # ==================== User Methods ====================
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users in the organization"""
        users = list(self._get_paginated(ProcessStreetEndpoints.USERS))
        self.stats['data_fetched']['users'] = len(users)
        logger.info(f"Fetched {len(users)} users")
        return users
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        response = self._make_request('GET', f'{ProcessStreetEndpoints.USERS}/{user_id}')
        return response.get('data', {})
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get current authenticated user"""
        response = self._make_request('GET', '/users/me')
        return response.get('data', {})
    
    # ==================== Group Methods ====================
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all groups in the organization"""
        groups = list(self._get_paginated(ProcessStreetEndpoints.GROUPS))
        self.stats['data_fetched']['groups'] = len(groups)
        logger.info(f"Fetched {len(groups)} groups")
        return groups
    
    def get_group(self, group_id: str) -> Dict[str, Any]:
        """Get group details with members"""
        response = self._make_request('GET', f'{ProcessStreetEndpoints.GROUPS}/{group_id}')
        group = response.get('data', {})
        
        # Get group members
        group['members'] = self.get_group_members(group_id)
        
        return group
    
    def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Get members of a group"""
        members = list(self._get_paginated(f'{ProcessStreetEndpoints.GROUPS}/{group_id}/members'))
        return members
    
    # ==================== Task Methods ====================
    
    def complete_task(self, task_id: str, completed_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Mark a task as complete
        
        Args:
            task_id: Task instance ID
            completed_by: User ID who completed the task
            
        Returns:
            Updated task object
        """
        data = {
            'completed': True,
            'completedAt': datetime.utcnow().isoformat(),
        }
        if completed_by:
            data['completedBy'] = completed_by
        
        response = self._make_request('PUT', f'{ProcessStreetEndpoints.TASKS}/{task_id}', json=data)
        return response.get('data', {})
    
    def uncomplete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as incomplete"""
        data = {'completed': False}
        response = self._make_request('PUT', f'{ProcessStreetEndpoints.TASKS}/{task_id}', json=data)
        return response.get('data', {})
    
    # ==================== Form Field Methods ====================
    
    def update_form_field_value(self, checklist_id: str, field_id: str, value: Any) -> Dict[str, Any]:
        """
        Update a form field value in a checklist
        
        Args:
            checklist_id: Checklist ID
            field_id: Form field ID
            value: New value (string, array, or object depending on field type)
            
        Returns:
            Updated field value object
        """
        data = {'value': value}
        endpoint = f'{ProcessStreetEndpoints.CHECKLISTS}/{checklist_id}/form-fields/{field_id}/value'
        response = self._make_request('PUT', endpoint, json=data)
        return response.get('data', {})
    
    def batch_update_form_fields(self, checklist_id: str, field_values: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Update multiple form field values at once
        
        Args:
            checklist_id: Checklist ID
            field_values: Dictionary of field_id: value pairs
            
        Returns:
            List of updated field value objects
        """
        data = {'fields': field_values}
        endpoint = f'{ProcessStreetEndpoints.CHECKLISTS}/{checklist_id}/form-fields/batch'
        response = self._make_request('PUT', endpoint, json=data)
        return response.get('data', [])
    
    # ==================== Assignment Methods ====================
    
    def list_assignments(self, checklist_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List assignments, optionally filtered by checklist"""
        params = {}
        if checklist_id:
            params['checklistId'] = checklist_id
        
        assignments = list(self._get_paginated(ProcessStreetEndpoints.ASSIGNMENTS, params=params))
        return assignments
    
    def assign_user_to_checklist(self, checklist_id: str, user_id: str, role: str = 'member') -> Dict[str, Any]:
        """Assign a user to a checklist"""
        data = {
            'checklistId': checklist_id,
            'userId': user_id,
            'role': role
        }
        response = self._make_request('POST', ProcessStreetEndpoints.ASSIGNMENTS, json=data)
        return response.get('data', {})
    
    def unassign_user_from_checklist(self, assignment_id: str) -> bool:
        """Remove a user assignment"""
        self._make_request('DELETE', f'{ProcessStreetEndpoints.ASSIGNMENTS}/{assignment_id}')
        return True
    
    # ==================== Approval Methods ====================
    
    def list_approvals(self, checklist_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List approval tasks, optionally filtered by checklist"""
        params = {}
        if checklist_id:
            params['checklistId'] = checklist_id
        
        approvals = list(self._get_paginated(ProcessStreetEndpoints.APPROVALS, params=params))
        return approvals
    
    def approve_task(self, approval_id: str, approver_id: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Approve an approval task"""
        data = {
            'status': 'approved',
            'approverId': approver_id,
            'approvedAt': datetime.utcnow().isoformat()
        }
        if comments:
            data['comments'] = comments
        
        response = self._make_request('PUT', f'{ProcessStreetEndpoints.APPROVALS}/{approval_id}', json=data)
        return response.get('data', {})
    
    def reject_task(self, approval_id: str, rejector_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject an approval task"""
        data = {
            'status': 'rejected',
            'rejectorId': rejector_id,
            'rejectedAt': datetime.utcnow().isoformat()
        }
        if reason:
            data['reason'] = reason
        
        response = self._make_request('PUT', f'{ProcessStreetEndpoints.APPROVALS}/{approval_id}', json=data)
        return response.get('data', {})
    
    # ==================== Comment Methods ====================
    
    def list_comments(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """
        List comments for an entity
        
        Args:
            entity_type: Type of entity (checklist, task)
            entity_id: Entity ID
            
        Returns:
            List of comments
        """
        endpoint = f'/{entity_type}s/{entity_id}/comments'
        comments = list(self._get_paginated(endpoint))
        return comments
    
    def add_comment(self, entity_type: str, entity_id: str, text: str, author_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a comment to an entity"""
        data = {
            "text": text,
            'createdAt': datetime.utcnow().isoformat()
        }
        if author_id:
            data['authorId'] = author_id
        
        endpoint = f'/{entity_type}s/{entity_id}/comments'
        response = self._make_request('POST', endpoint, json=data)
        return response.get('data', {})
    
    # ==================== File Attachment Methods ====================
    
    def list_attachments(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """List file attachments for an entity"""
        endpoint = f'/{entity_type}s/{entity_id}/attachments'
        attachments = list(self._get_paginated(endpoint))
        return attachments
    
    def download_attachment(self, attachment_url: str, destination: str) -> bool:
        """
        Download a file attachment
        
        Args:
            attachment_url: Attachment URL
            destination: Local file path
            
        Returns:
            Success status
        """
        try:
            # Attachments may require authentication
            headers = {'X-API-KEY': self.api_key}
            response = requests.get(attachment_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Downloaded attachment to {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            return False
    
    # ==================== Webhook Methods ====================
    
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all webhooks in the organization"""
        webhooks = list(self._get_paginated(ProcessStreetEndpoints.WEBHOOKS))
        self.stats['data_fetched']['webhooks'] = len(webhooks)
        logger.info(f"Fetched {len(webhooks)} webhooks")
        return webhooks
    
    def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Get webhook details"""
        response = self._make_request('GET', f'{ProcessStreetEndpoints.WEBHOOKS}/{webhook_id}')
        return response.get('data', {})
    
    def create_webhook(self, url: str, events: List[str], name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new webhook
        
        Args:
            url: Webhook URL
            events: List of events to subscribe to
            name: Optional webhook name
            
        Returns:
            Created webhook object
        """
        data = {
            "text": url,
            'events': events,
            'active': True
        }
        if name:
            data['name'] = name
        
        response = self._make_request('POST', ProcessStreetEndpoints.WEBHOOKS, json=data)
        return response.get('data', {})
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        self._make_request('DELETE', f'{ProcessStreetEndpoints.WEBHOOKS}/{webhook_id}')
        return True
    
    # ==================== Data Set Methods ====================
    
    def list_data_sets(self) -> List[Dict[str, Any]]:
        """List all data sets in the organization"""
        data_sets = list(self._get_paginated(ProcessStreetEndpoints.DATA_SETS))
        self.stats['data_fetched']['data_sets'] = len(data_sets)
        logger.info(f"Fetched {len(data_sets)} data sets")
        return data_sets
    
    def get_data_set(self, dataset_id: str) -> Dict[str, Any]:
        """Get data set details"""
        response = self._make_request('GET', f'{ProcessStreetEndpoints.DATA_SETS}/{dataset_id}')
        return response.get('data', {})
    
    def get_data_set_records(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get all records from a data set"""
        records = list(self._get_paginated(f'{ProcessStreetEndpoints.DATA_SETS}/{dataset_id}/records'))
        logger.debug(f"Fetched {len(records)} records from data set {dataset_id}")
        return records
    
    # ==================== Export Methods ====================
    
    def export_workflow_data(self, workflow_id: str, format: str = 'json') -> Any:
        """
        Export workflow data
        
        Args:
            workflow_id: Workflow ID
            format: Export format (json, csv)
            
        Returns:
            Exported data
        """
        params = {'format': format}
        response = self._make_request('GET', f'{ProcessStreetEndpoints.WORKFLOWS}/{workflow_id}/export', params=params)
        
        if format == 'json':
            return response
        else:
            return response.get('data', '')
    
    def export_checklist_data(self, checklist_id: str, format: str = 'json') -> Any:
        """
        Export checklist data
        
        Args:
            checklist_id: Checklist ID
            format: Export format (json, csv)
            
        Returns:
            Exported data
        """
        params = {'format': format}
        response = self._make_request('GET', f'{ProcessStreetEndpoints.CHECKLISTS}/{checklist_id}/export', params=params)
        
        if format == 'json':
            return response
        else:
            return response.get('data', '')
    
    # ==================== Discovery Methods ====================
    
    def discover_all_data(self) -> Dict[str, Any]:
        """
        Discover all data in the organization for migration
        
        Returns:
            Comprehensive data discovery report
        """
        logger.info("Starting comprehensive data discovery...")
        
        discovery = {
            'organization': None,
            'counts': {},
            'samples': {},
            'relationships': {},
            'timestamp': datetime.utcnow().isoformat(),
            'api_version': 'v1.1',
            'limitations': []
        }
        
        # Get organization details
        try:
            discovery['organization'] = self.get_organization()
        except Exception as e:
            logger.warning(f"Could not fetch organization: {e}")
            discovery['limitations'].append("Organization details unavailable")
        
        # Discover each data type
        discovery_tasks = [
            ('users', self.list_users),
            ('groups', self.list_groups),
            ('workflows', self.list_workflows),
            ('checklists', lambda: self.list_checklists(status='active')),
            ('completed_checklists', lambda: self.list_checklists(status='completed')),
            ('webhooks', self.list_webhooks),
            ('data_sets', self.list_data_sets)
        ]
        
        for data_type, fetch_func in discovery_tasks:
            try:
                logger.info(f"Discovering {data_type}...")
                items = fetch_func()
                discovery['counts'][data_type] = len(items)
                
                # Store samples (first 3 items)
                discovery['samples'][data_type] = items[:3] if items else []
                
                # Analyze relationships
                if data_type == 'workflows' and items:
                    # Count tasks and form fields per workflow
                    total_tasks = 0
                    total_fields = 0
                    for workflow in items[:5]:  # Sample first 5 workflows
                        try:
                            wf_id = workflow.get('id')
                            tasks = self.get_workflow_tasks(wf_id)
                            fields = self.get_workflow_form_fields(wf_id)
                            total_tasks += len(tasks)
                            total_fields += len(fields)
                        except:
                            pass
                    
                    discovery['relationships']['avg_tasks_per_workflow'] = total_tasks / min(5, len(items))
                    discovery['relationships']['avg_fields_per_workflow'] = total_fields / min(5, len(items))
                
                logger.info(f"Discovered {len(items)} {data_type}")
                
            except Exception as e:
                logger.error(f"Failed to discover {data_type}: {e}")
                discovery['counts'][data_type] = 0
                discovery['samples'][data_type] = []
                discovery['limitations'].append(f"Could not fetch {data_type}: {str(e)}")
        
        # Calculate totals
        discovery['totals'] = {
            'total_objects': sum(discovery['counts'].values()),
            'active_processes': discovery['counts'].get('checklists', 0),
            'completed_processes': discovery['counts'].get('completed_checklists', 0),
            'total_workflows': discovery['counts'].get('workflows', 0),
            'total_users': discovery['counts'].get('users', 0),
            'api_calls_made': self.stats['api_calls'],
            'rate_limits_hit': self.stats['rate_limits_hit'],
            'errors': self.stats['errors']
        }
        
        # Add migration complexity assessment
        complexity_score = (
            discovery['totals']['total_workflows'] * 10 +
            discovery['totals']['active_processes'] * 5 +
            discovery['totals']['completed_processes'] * 2 +
            discovery['totals']['total_users'] * 1
        )
        
        if complexity_score < 100:
            discovery['migration_complexity'] = 'Low'
        elif complexity_score < 500:
            discovery['migration_complexity'] = 'Medium'
        elif complexity_score < 2000:
            discovery['migration_complexity'] = 'High'
        else:
            discovery['migration_complexity'] = 'Very High'
        
        logger.info(f"Discovery complete: {discovery['totals']['total_objects']} total objects")
        logger.info(f"Migration complexity: {discovery['migration_complexity']}")
        
        return discovery
    
    def validate_migration_readiness(self) -> Dict[str, Any]:
        """
        Validate if the organization is ready for migration
        
        Returns:
            Readiness assessment report
        """
        logger.info("Validating migration readiness...")
        
        readiness = {
            'ready': True,
            'checks': [],
            'warnings': [],
            'blockers': []
        }
        
        # Check API access
        try:
            user = self.get_current_user()
            readiness['checks'].append({
                'name': 'API Access',
                'status': 'passed',
                'details': f"Authenticated as {user.get('attributes', {}).get("text", 'Unknown')}"
            })
        except Exception as e:
            readiness['ready'] = False
            readiness['blockers'].append(f"API access failed: {e}")
            readiness['checks'].append({
                'name': 'API Access',
                'status': 'failed',
                'details': str(e)
            })
        
        # Check organization access
        try:
            org = self.get_organization()
            readiness['checks'].append({
                'name': 'Organization Access',
                'status': 'passed',
                'details': f"Organization: {org.get('attributes', {}).get('name', 'Unknown')}"
            })
        except Exception as e:
            readiness['warnings'].append(f"Could not verify organization: {e}")
            readiness['checks'].append({
                'name': 'Organization Access',
                'status': 'warning',
                'details': str(e)
            })
        
        # Check data accessibility
        try:
            # Try to fetch a small sample of each data type
            workflows = self.list_workflows()[:1]
            checklists = self.list_checklists()[:1]
            users = self.list_users()[:1]
            
            readiness['checks'].append({
                'name': 'Data Access',
                'status': 'passed',
                'details': 'Can access workflows, checklists, and users'
            })
        except Exception as e:
            readiness['ready'] = False
            readiness['blockers'].append(f"Cannot access required data: {e}")
            readiness['checks'].append({
                'name': 'Data Access',
                'status': 'failed',
                'details': str(e)
            })
        
        # Check for active processes
        try:
            active_checklists = self.list_checklists(status='active')
            if len(active_checklists) > 100:
                readiness['warnings'].append(f"High number of active processes ({len(active_checklists)}). Consider completing or archiving before migration.")
        except:
            pass
        
        # Summary
        readiness['summary'] = {
            'total_checks': len(readiness['checks']),
            'passed_checks': len([c for c in readiness['checks'] if c['status'] == 'passed']),
            'warning_count': len(readiness['warnings']),
            'blocker_count': len(readiness['blockers'])
        }
        
        logger.info(f"Readiness check complete: {'Ready' if readiness['ready'] else 'Not Ready'}")
        
        return readiness
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed client statistics"""
        elapsed = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'elapsed_time': elapsed,
            'avg_requests_per_minute': (self.stats['api_calls'] / elapsed * 60) if elapsed > 0 else 0,
            'error_rate': (self.stats['errors'] / self.stats['api_calls'] * 100) if self.stats['api_calls'] > 0 else 0,
            'retry_rate': (self.stats['retries'] / self.stats['api_calls'] * 100) if self.stats['api_calls'] > 0 else 0
        }