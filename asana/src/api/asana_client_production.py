#!/usr/bin/env python3
"""
Production-Grade Asana API Client
Implements actual Asana API with proper authentication, rate limiting, and error handling
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Generator, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from dataclasses import dataclass
from enum import Enum


class AsanaRateLimitError(Exception):
    """Asana rate limit exceeded"""
    pass


class AsanaAuthError(Exception):
    """Asana authentication failed"""
    pass


class AsanaResourceType(str, Enum):
    """Asana resource types"""
    WORKSPACE = "workspace"
    PROJECT = "project"
    TASK = "task"
    SUBTASK = "subtask"
    SECTION = "section"
    TAG = "tag"
    USER = "user"
    TEAM = "team"
    PORTFOLIO = "portfolio"
    CUSTOM_FIELD = "custom_field"
    ATTACHMENT = "attachment"
    STORY = "story"


@dataclass
class AsanaRateLimit:
    """Rate limit tracking for Asana API"""
    minute_limit: int = 150  # 150 requests per minute
    hour_limit: int = 1500   # 1500 requests per hour
    minute_requests: List[datetime] = None
    hour_start: datetime = None
    hour_requests: int = 0
    
    def __post_init__(self):
        if self.minute_requests is None:
            self.minute_requests = []
        if self.hour_start is None:
            self.hour_start = datetime.now()


class AsanaProductionClient:
    """
    Production Asana API client with actual endpoints
    Implements Asana REST API
    """
    
    BASE_URL = "https://app.asana.com/api/1.0"
    
    def __init__(self):
        """Initialize Asana client with actual authentication"""
        # Try Personal Access Token first
        self.access_token = os.getenv('ASANA_ACCESS_TOKEN')
        
        # Fall back to OAuth if no PAT
        if not self.access_token:
            self.access_token = os.getenv('ASANA_OAUTH_TOKEN')
        
        if not self.access_token:
            raise AsanaAuthError("ASANA_ACCESS_TOKEN or ASANA_OAUTH_TOKEN required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Asana-Enable': 'new_user_task_lists,new_project_templates,new_memberships'  # Enable new features
        })
        
        # Rate limiting
        self.rate_limit = AsanaRateLimit()
        
        # Workspace cache
        self.default_workspace = None
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce Asana rate limits"""
        now = datetime.now()
        
        # Check hourly limit
        if now - self.rate_limit.hour_start > timedelta(hours=1):
            self.rate_limit.hour_requests = 0
            self.rate_limit.hour_start = now
        
        if self.rate_limit.hour_requests >= self.rate_limit.hour_limit:
            wait_time = 3600 - (now - self.rate_limit.hour_start).seconds
            self.logger.warning(f"Hourly rate limit reached. Waiting {wait_time}s")
            time.sleep(wait_time)
            self.rate_limit.hour_requests = 0
            self.rate_limit.hour_start = datetime.now()
        
        # Check minute limit (sliding window)
        self.rate_limit.minute_requests = [
            ts for ts in self.rate_limit.minute_requests 
            if now - ts < timedelta(minutes=1)
        ]
        
        if len(self.rate_limit.minute_requests) >= self.rate_limit.minute_limit:
            wait_time = 60 - (now - self.rate_limit.minute_requests[0]).seconds
            if wait_time > 0:
                self.logger.info(f"Minute rate limit throttling: waiting {wait_time}s")
                time.sleep(wait_time)
                self.rate_limit.minute_requests = []
        
        self.rate_limit.minute_requests.append(now)
        self.rate_limit.hour_requests += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, AsanaRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None, files: Dict = None) -> Any:
        """Make authenticated request to Asana API"""
        self._check_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if files:
                # For file uploads, don't send Content-Type header
                headers = self.session.headers.copy()
                del headers['Content-Type']
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,  # Use data instead of json for multipart
                    files=files,
                    headers=headers,
                    timeout=30
                )
            else:
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
                raise AsanaRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                result = response.json()
                # Asana wraps responses in 'data' key
                return result.get('data', result) if 'data' in result else result
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AsanaAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                if e.response.text:
                    self.logger.error(f"Response: {e.response.text}")
                raise
    
    # ============= ACTUAL ASANA API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            user = self._make_request('GET', '/users/me')
            self.logger.info(f"Connected to Asana as {user.get('name')}")
            
            # Cache default workspace
            if user.get('workspaces'):
                self.default_workspace = user['workspaces'][0]['gid']
            
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        params = {
            'opt_fields': 'name,email,photo,workspaces,workspaces.name'
        }
        return self._make_request('GET', '/users/me', params)
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces accessible to the user"""
        params = {
            'opt_fields': 'name,is_organization,email_domains'
        }
        return self._make_request('GET', '/workspaces', params)
    
    def get_workspace(self, workspace_gid: str) -> Dict[str, Any]:
        """Get detailed workspace information"""
        params = {
            'opt_fields': 'name,is_organization,email_domains,members,teams'
        }
        return self._make_request('GET', f'/workspaces/{workspace_gid}', params)
    
    def get_projects(self, workspace_gid: str = None, team_gid: str = None, 
                    archived: bool = False) -> List[Dict[str, Any]]:
        """
        Get all projects
        
        Args:
            workspace_gid: Workspace to get projects from
            team_gid: Team to get projects from
            archived: Include archived projects
        """
        params = {
            'opt_fields': 'name,notes,color,archived,created_at,modified_at,owner,team,workspace,custom_fields,members',
            'archived': archived
        }
        
        if team_gid:
            endpoint = f'/teams/{team_gid}/projects'
        elif workspace_gid:
            params['workspace'] = workspace_gid
            endpoint = '/projects'
        else:
            params['workspace'] = self.default_workspace
            endpoint = '/projects'
        
        return self._make_request('GET', endpoint, params)
    
    def get_project(self, project_gid: str) -> Dict[str, Any]:
        """Get detailed project information"""
        params = {
            'opt_fields': ('name,notes,html_notes,color,archived,created_at,modified_at,'
                          'start_on,due_on,current_status,owner,team,workspace,custom_fields,'
                          'members,followers,custom_field_settings,layout')
        }
        return self._make_request('GET', f'/projects/{project_gid}', params)
    
    def get_tasks(self, project_gid: str = None, assignee: str = None, 
                 completed_since: datetime = None) -> List[Dict[str, Any]]:
        """
        Get tasks from project or assigned to user
        
        Args:
            project_gid: Project to get tasks from
            assignee: User GID or 'me' for current user
            completed_since: Include tasks completed after this date
        """
        params = {
            'opt_fields': ('name,notes,html_notes,completed,completed_at,due_on,due_at,'
                          'assignee,assignee_status,projects,tags,custom_fields,followers,'
                          'created_at,modified_at,memberships,dependencies,dependents')
        }
        
        if completed_since:
            params['completed_since'] = completed_since.isoformat()
        
        if project_gid:
            endpoint = f'/projects/{project_gid}/tasks'
        elif assignee:
            params['assignee'] = assignee
            params['workspace'] = self.default_workspace
            endpoint = '/tasks'
        else:
            raise ValueError("Either project_gid or assignee required")
        
        return self._make_request('GET', endpoint, params)
    
    def get_task(self, task_gid: str) -> Dict[str, Any]:
        """Get detailed task information"""
        params = {
            'opt_fields': ('name,notes,html_notes,completed,completed_at,due_on,due_at,'
                          'assignee,assignee_status,projects,tags,custom_fields,followers,'
                          'created_at,modified_at,parent,hearts,num_hearts,liked,likes,'
                          'memberships,dependencies,dependents,attachments,subtasks')
        }
        return self._make_request('GET', f'/tasks/{task_gid}', params)
    
    def get_subtasks(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get subtasks of a task"""
        params = {
            'opt_fields': 'name,notes,completed,assignee,due_on,due_at'
        }
        return self._make_request('GET', f'/tasks/{task_gid}/subtasks', params)
    
    def get_sections(self, project_gid: str) -> List[Dict[str, Any]]:
        """Get sections in a project"""
        params = {
            'opt_fields': 'name,created_at,project,projects'
        }
        return self._make_request('GET', f'/projects/{project_gid}/sections', params)
    
    def get_tags(self, workspace_gid: str = None) -> List[Dict[str, Any]]:
        """Get all tags in workspace"""
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        params = {
            'workspace': workspace_gid,
            'opt_fields': 'name,color,notes,created_at,followers'
        }
        return self._make_request('GET', '/tags', params)
    
    def get_teams(self, workspace_gid: str = None) -> List[Dict[str, Any]]:
        """Get all teams in workspace"""
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        params = {
            'opt_fields': 'name,description,html_description,organization'
        }
        
        # Use organization endpoint if available
        endpoint = f'/organizations/{workspace_gid}/teams'
        try:
            return self._make_request('GET', endpoint, params)
        except:
            # Fall back to workspace endpoint
            return self._make_request('GET', f'/workspaces/{workspace_gid}/teams', params)
    
    def get_users(self, workspace_gid: str = None, team_gid: str = None) -> List[Dict[str, Any]]:
        """Get users in workspace or team"""
        params = {
            'opt_fields': 'name,email,photo'
        }
        
        if team_gid:
            endpoint = f'/teams/{team_gid}/users'
        elif workspace_gid:
            endpoint = f'/workspaces/{workspace_gid}/users'
        else:
            endpoint = f'/workspaces/{self.default_workspace}/users'
        
        return self._make_request('GET', endpoint, params)
    
    def get_custom_fields(self, workspace_gid: str = None) -> List[Dict[str, Any]]:
        """Get custom field definitions for workspace"""
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        params = {
            'workspace': workspace_gid,
            'opt_fields': 'name,description,type,enum_options,precision,format,currency_code'
        }
        return self._make_request('GET', '/custom_fields', params)
    
    def get_portfolios(self, workspace_gid: str = None) -> List[Dict[str, Any]]:
        """Get portfolios in workspace"""
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        params = {
            'workspace': workspace_gid,
            'opt_fields': 'name,color,created_at,members,owner,custom_fields'
        }
        return self._make_request('GET', '/portfolios', params)
    
    def get_attachments(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get attachments on a task"""
        params = {
            'opt_fields': 'name,download_url,view_url,host,created_at,size'
        }
        return self._make_request('GET', f'/tasks/{task_gid}/attachments', params)
    
    def get_stories(self, task_gid: str) -> List[Dict[str, Any]]:
        """Get stories (comments/activity) on a task"""
        params = {
            'opt_fields': 'text,html_text,type,created_at,created_by,resource_subtype'
        }
        return self._make_request('GET', f'/tasks/{task_gid}/stories', params)
    
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhooks for the authenticated user"""
        return self._make_request('GET', '/webhooks', {'workspace': self.default_workspace})
    
    # ============= SEARCH OPERATIONS =============
    
    def search_tasks(self, workspace_gid: str = None, text: str = None, 
                    resource_subtype: str = 'default_task', **filters) -> List[Dict[str, Any]]:
        """
        Search tasks in workspace
        
        Args:
            workspace_gid: Workspace to search in
            text: Text to search for
            resource_subtype: 'default_task' or 'milestone'
            **filters: Additional filters (assignee.any, projects.any, etc.)
        """
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        params = {
            'workspace': workspace_gid,
            'resource_subtype': resource_subtype,
            'opt_fields': 'name,notes,completed,assignee,projects,due_on'
        }
        
        if text:
            params['text'] = text
        
        # Add additional filters
        params.update(filters)
        
        return self._make_request('GET', '/workspaces/{workspace_gid}/tasks/search', params)
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_tasks(self, project_gid: str, batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """
        Get tasks in batches to handle large projects
        
        Args:
            project_gid: Project GID
            batch_size: Number of tasks per batch
            
        Yields:
            Batches of tasks
        """
        offset = None
        
        while True:
            params = {
                'opt_fields': 'name,notes,completed,assignee,due_on,custom_fields',
                'limit': batch_size
            }
            
            if offset:
                params['offset'] = offset
            
            response = self._make_request('GET', f'/projects/{project_gid}/tasks', params)
            
            if not response:
                break
            
            # Handle both list and paginated responses
            if isinstance(response, list):
                yield response
                if len(response) < batch_size:
                    break
            else:
                # Paginated response with next_page
                yield response.get('data', [])
                if not response.get('next_page'):
                    break
                offset = response['next_page'].get('offset')
            
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self, workspace_gid: str = None, include_archived: bool = False) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Args:
            workspace_gid: Workspace to export
            include_archived: Include archived projects
            
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Asana data export")
        
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'workspace': self.get_workspace(workspace_gid),
            'users': [],
            'teams': [],
            'projects': [],
            'tags': [],
            'custom_fields': [],
            'portfolios': [],
            'total_tasks': 0,
            'total_projects': 0
        }
        
        # Get users
        self.logger.info("Fetching users...")
        data['users'] = self.get_users(workspace_gid)
        
        # Get teams
        self.logger.info("Fetching teams...")
        data['teams'] = self.get_teams(workspace_gid)
        
        # Get tags
        self.logger.info("Fetching tags...")
        data['tags'] = self.get_tags(workspace_gid)
        
        # Get custom fields
        self.logger.info("Fetching custom fields...")
        data['custom_fields'] = self.get_custom_fields(workspace_gid)
        
        # Get portfolios
        self.logger.info("Fetching portfolios...")
        data['portfolios'] = self.get_portfolios(workspace_gid)
        
        # Get projects and their tasks
        self.logger.info("Fetching projects...")
        projects = self.get_projects(workspace_gid, archived=include_archived)
        
        for project in projects:
            if not include_archived and project.get('archived'):
                continue
            
            self.logger.info(f"  Processing project: {project['name']}")
            
            # Get full project details
            project_data = self.get_project(project['gid'])
            
            # Get sections
            project_data['sections'] = self.get_sections(project['gid'])
            
            # Get tasks
            project_data['tasks'] = []
            task_count = 0
            
            for task_batch in self.batch_get_tasks(project['gid']):
                for task in task_batch:
                    # Get subtasks if any
                    if task.get('num_subtasks', 0) > 0:
                        task['subtasks'] = self.get_subtasks(task['gid'])
                    
                    # Get attachments if any
                    if task.get('num_attachments', 0) > 0:
                        task['attachments'] = self.get_attachments(task['gid'])
                    
                    # Get stories (comments)
                    task['stories'] = self.get_stories(task['gid'])
                    
                    project_data['tasks'].append(task)
                    task_count += 1
                
                # Rate limit pause
                time.sleep(1)
            
            data['total_tasks'] += task_count
            data['projects'].append(project_data)
            data['total_projects'] += 1
            
            self.logger.info(f"    Processed {task_count} tasks")
        
        self.logger.info(f"Export complete: {data['total_projects']} projects, {data['total_tasks']} tasks")
        
        return data
    
    # ============= PAGINATION SUPPORT =============
    
    def paginate_resource(self, resource_type: AsanaResourceType, 
                         parent_gid: str = None, **params) -> Generator[Dict, None, None]:
        """
        Generic pagination for any Asana resource
        
        Args:
            resource_type: Type of resource to paginate
            parent_gid: Parent resource GID
            **params: Additional parameters
            
        Yields:
            Individual resources
        """
        # Determine endpoint based on resource type
        endpoints = {
            AsanaResourceType.PROJECT: f'/workspaces/{parent_gid or self.default_workspace}/projects',
            AsanaResourceType.TASK: f'/projects/{parent_gid}/tasks' if parent_gid else '/tasks',
            AsanaResourceType.USER: f'/workspaces/{parent_gid or self.default_workspace}/users',
            AsanaResourceType.TEAM: f'/workspaces/{parent_gid or self.default_workspace}/teams',
            AsanaResourceType.TAG: '/tags',
            AsanaResourceType.PORTFOLIO: '/portfolios'
        }
        
        endpoint = endpoints.get(resource_type)
        if not endpoint:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        
        offset = None
        params['limit'] = params.get('limit', 100)
        
        while True:
            if offset:
                params['offset'] = offset
            
            response = self._make_request('GET', endpoint, params)
            
            if not response:
                break
            
            # Handle both list and paginated responses
            if isinstance(response, list):
                for item in response:
                    yield item
                if len(response) < params['limit']:
                    break
            else:
                # Paginated response
                for item in response.get('data', []):
                    yield item
                if not response.get('next_page'):
                    break
                offset = response['next_page'].get('offset')
            
            time.sleep(0.1)  # Small delay between pages
    
    # ============= BULK CREATE OPERATIONS =============
    
    def create_project(self, name: str, workspace_gid: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new project"""
        if not workspace_gid:
            workspace_gid = self.default_workspace
        
        data = {
            'data': {
                'name': name,
                'workspace': workspace_gid,
                **kwargs
            }
        }
        return self._make_request('POST', '/projects', data=data)
    
    def create_task(self, name: str, project_gid: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new task"""
        data = {
            'data': {
                'name': name,
                **kwargs
            }
        }
        
        if project_gid:
            data['data']['projects'] = [project_gid]
        
        return self._make_request('POST', '/tasks', data=data)
    
    def add_attachment(self, task_gid: str, file_path: str, file_name: str = None) -> Dict[str, Any]:
        """Add attachment to task"""
        if not file_name:
            file_name = os.path.basename(file_path)
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_name, f, 'application/octet-stream')
            }
            data = {
                'parent': task_gid
            }
            return self._make_request('POST', '/attachments', data=data, files=files)
    
    def create_webhook(self, resource_gid: str, target_url: str) -> Dict[str, Any]:
        """Create webhook for resource"""
        data = {
            'data': {
                'resource': resource_gid,
                'target': target_url
            }
        }
        return self._make_request('POST', '/webhooks', data=data)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = AsanaProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Asana")
        
        # Get workspaces
        workspaces = client.get_workspaces()
        print(f"Found {len(workspaces)} workspaces")
        
        if workspaces:
            workspace = workspaces[0]
            print(f"Using workspace: {workspace['name']}")
            
            # Get projects
            projects = client.get_projects(workspace['gid'])
            print(f"Found {len(projects)} projects")
            
            if projects:
                # Get tasks from first project
                project = projects[0]
                tasks = client.get_tasks(project['gid'])
                print(f"Found {len(tasks)} tasks in {project['name']}")
    
    print("\n✅ Production Asana client ready!")