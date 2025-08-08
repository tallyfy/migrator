"""
ClickUp API Client
Handles all interactions with ClickUp API v2
"""

import requests
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ClickUpClient:
    """Client for interacting with ClickUp API v2"""
    
    def __init__(self, api_key: str, workspace_id: Optional[str] = None):
        """
        Initialize ClickUp client
        
        Args:
            api_key: ClickUp personal API token
            workspace_id: Optional workspace ID (will fetch first if not provided)
        """
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base_url = "https://api.clickup.com/api/v2"
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': api_key,
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.6  # ~100 requests per minute
        
        # Auto-fetch workspace if not provided
        if not self.workspace_id:
            self._fetch_workspace()
        
        logger.info(f"ClickUp client initialized for workspace: {self.workspace_id}")
    
    def _fetch_workspace(self):
        """Fetch first available workspace"""
        try:
            workspaces = self.get_workspaces()
            if workspaces:
                self.workspace_id = workspaces[0]['id']
                logger.info(f"Auto-selected workspace: {workspaces[0]['name']}")
            else:
                raise Exception("No workspaces found")
        except Exception as e:
            logger.error(f"Failed to fetch workspace: {e}")
            raise
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an API request"""
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('X-RateLimit-Reset', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, **kwargs)
            
            response.raise_for_status()
            
            if response.status_code == 204:
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    # Workspace & Team Management
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces (teams)"""
        response = self._make_request('GET', '/team')
        return response.get('teams', [])
    
    def get_spaces(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get all spaces in workspace"""
        params = {'archived': include_archived}
        response = self._make_request('GET', f'/team/{self.workspace_id}/space', params=params)
        return response.get('spaces', [])
    
    def get_space(self, space_id: str) -> Dict[str, Any]:
        """Get specific space details"""
        return self._make_request('GET', f'/space/{space_id}')
    
    # Folder Management
    def get_folders(self, space_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get folders in a space"""
        params = {'archived': include_archived}
        response = self._make_request('GET', f'/space/{space_id}/folder', params=params)
        return response.get('folders', [])
    
    def get_folderless_lists(self, space_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get lists without folders in a space"""
        params = {'archived': include_archived}
        response = self._make_request('GET', f'/space/{space_id}/list', params=params)
        return response.get('lists', [])
    
    # List Management
    def get_lists(self, folder_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get lists in a folder"""
        params = {'archived': include_archived}
        response = self._make_request('GET', f'/folder/{folder_id}/list', params=params)
        return response.get('lists', [])
    
    def get_list(self, list_id: str) -> Dict[str, Any]:
        """Get specific list details"""
        return self._make_request('GET', f'/list/{list_id}')
    
    def get_list_views(self, list_id: str) -> List[Dict[str, Any]]:
        """Get views for a list"""
        response = self._make_request('GET', f'/list/{list_id}/view')
        return response.get('views', [])
    
    # Task Management
    def get_tasks(self, list_id: str, include_archived: bool = False, 
                 include_subtasks: bool = True, page: int = 0) -> List[Dict[str, Any]]:
        """Get tasks in a list"""
        params = {
            'archived': include_archived,
            'include_subtasks': include_subtasks,
            'page': page,
            'order_by': 'created',
            'reverse': False
        }
        response = self._make_request('GET', f'/list/{list_id}/task', params=params)
        return response.get('tasks', [])
    
    def get_task(self, task_id: str, include_subtasks: bool = True) -> Dict[str, Any]:
        """Get specific task details"""
        params = {'include_subtasks': include_subtasks}
        return self._make_request('GET', f'/task/{task_id}', params=params)
    
    def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task comments"""
        response = self._make_request('GET', f'/task/{task_id}/comment')
        return response.get('comments', [])
    
    def get_task_time_entries(self, task_id: str) -> List[Dict[str, Any]]:
        """Get time tracking entries for a task"""
        response = self._make_request('GET', f'/task/{task_id}/time')
        return response.get('data', [])
    
    # Custom Fields
    def get_custom_fields(self, list_id: str) -> List[Dict[str, Any]]:
        """Get custom fields for a list"""
        list_data = self.get_list(list_id)
        return list_data.get('custom_fields', [])
    
    def get_accessible_custom_fields(self) -> List[Dict[str, Any]]:
        """Get all accessible custom fields in workspace"""
        response = self._make_request('GET', f'/team/{self.workspace_id}/field')
        return response.get('fields', [])
    
    # User Management  
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users in workspace"""
        response = self._make_request('GET', f'/team/{self.workspace_id}/user')
        return response.get('members', [])
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get specific user details"""
        return self._make_request('GET', f'/user/{user_id}')
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get teams/user groups in workspace"""
        response = self._make_request('GET', f'/group')
        teams = response.get('groups', [])
        # Filter to workspace teams
        return [t for t in teams if t.get('team_id') == self.workspace_id]
    
    # Automations
    def get_automations(self) -> List[Dict[str, Any]]:
        """Get workspace automations"""
        response = self._make_request('GET', f'/team/{self.workspace_id}/automation')
        return response.get('automations', [])
    
    # Goals
    def get_goals(self) -> List[Dict[str, Any]]:
        """Get workspace goals"""
        response = self._make_request('GET', f'/team/{self.workspace_id}/goal')
        return response.get('goals', [])
    
    # Webhooks
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get workspace webhooks"""
        response = self._make_request('GET', f'/team/{self.workspace_id}/webhook')
        return response.get('webhooks', [])
    
    # Tags
    def get_tags(self, space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tags for workspace or space"""
        if space_id:
            response = self._make_request('GET', f'/space/{space_id}/tag')
        else:
            # Get workspace tags
            spaces = self.get_spaces()
            all_tags = []
            for space in spaces:
                space_tags = self.get_tags(space['id'])
                all_tags.extend(space_tags)
            return all_tags
        
        return response.get('tags', [])
    
    # Time Tracking
    def get_time_entries(self, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get time entries for workspace"""
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
            
        response = self._make_request('GET', f'/team/{self.workspace_id}/time_entries', 
                                     params=params)
        return response.get('data', [])
    
    # Discovery
    def discover_workspace(self) -> Dict[str, Any]:
        """Discover complete workspace structure"""
        discovery = {
            'workspace_id': self.workspace_id,
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {},
            'structure': {}
        }
        
        # Get spaces
        spaces = self.get_spaces()
        discovery['statistics']['spaces'] = len(spaces)
        discovery['structure']['spaces'] = []
        
        total_lists = 0
        total_tasks = 0
        
        for space in spaces:
            space_data = {
                'id': space['id'],
                'name': space['name'],
                'folders': [],
                'lists': []
            }
            
            # Get folders
            folders = self.get_folders(space['id'])
            for folder in folders:
                folder_data = {
                    'id': folder['id'],
                    'name': folder['name'],
                    'lists': []
                }
                
                # Get lists in folder
                lists = self.get_lists(folder['id'])
                total_lists += len(lists)
                
                for list_item in lists:
                    # Get task count
                    tasks = self.get_tasks(list_item['id'])
                    total_tasks += len(tasks)
                    
                    folder_data['lists'].append({
                        'id': list_item['id'],
                        'name': list_item['name'],
                        'task_count': len(tasks)
                    })
                
                space_data['folders'].append(folder_data)
            
            # Get folderless lists
            folderless = self.get_folderless_lists(space['id'])
            total_lists += len(folderless)
            
            for list_item in folderless:
                tasks = self.get_tasks(list_item['id'])
                total_tasks += len(tasks)
                
                space_data['lists'].append({
                    'id': list_item['id'],
                    'name': list_item['name'],
                    'task_count': len(tasks)
                })
            
            discovery['structure']['spaces'].append(space_data)
        
        # Get users
        users = self.get_users()
        discovery['statistics']['users'] = len(users)
        
        # Get custom fields
        custom_fields = self.get_accessible_custom_fields()
        discovery['statistics']['custom_fields'] = len(custom_fields)
        
        # Get automations
        automations = self.get_automations()
        discovery['statistics']['automations'] = len(automations)
        
        discovery['statistics']['folders'] = sum(
            len(s.get('folders', [])) for s in discovery['structure']['spaces']
        )
        discovery['statistics']['lists'] = total_lists
        discovery['statistics']['tasks'] = total_tasks
        
        return discovery
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self.get_workspaces()
            logger.info("ClickUp API connection successful")
            return True
        except Exception as e:
            logger.error(f"ClickUp API connection failed: {e}")
            return False