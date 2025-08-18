#!/usr/bin/env python3
"""
Production-Grade Wrike API Client
Implements actual Wrike API v4 with proper authentication, rate limiting, and error handling
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


class WrikeRateLimitError(Exception):
    """Wrike rate limit exceeded"""
    pass


class WrikeAuthError(Exception):
    """Wrike authentication failed"""
    pass


class WrikeCustomFieldType(str, Enum):
    """Wrike custom field types"""
    TEXT = "Text"
    DROPDOWN = "DropDown"
    NUMERIC = "Numeric"
    CURRENCY = "Currency"
    PERCENTAGE = "Percentage"
    DATE = "Date"
    DURATION = "Duration"
    CHECKBOX = "Checkbox"
    CONTACTS = "Contacts"
    MULTIPLE = "Multiple"


class WrikeTaskStatus(str, Enum):
    """Wrike task status"""
    ACTIVE = "Active"
    COMPLETED = "Completed"
    DEFERRED = "Deferred"
    CANCELLED = "Cancelled"


class WrikeProductionClient:
    """
    Production Wrike API client with actual endpoints
    Implements Wrike API v4
    """
    
    BASE_URL = "https://www.wrike.com/api/v4"
    
    # Wrike rate limits
    RATE_LIMITS = {
        'requests_per_minute': 100,
        'requests_per_second': 5,
        'burst_limit': 20
    }
    
    def __init__(self):
        """Initialize Wrike client with actual authentication"""
        self.access_token = os.getenv('WRIKE_ACCESS_TOKEN')
        
        if not self.access_token:
            # Try permanent token if OAuth token not available
            self.access_token = os.getenv('WRIKE_PERMANENT_TOKEN')
        
        if not self.access_token:
            raise WrikeAuthError("WRIKE_ACCESS_TOKEN or WRIKE_PERMANENT_TOKEN required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.request_times = []
        self.minute_start = datetime.now()
        self.requests_this_minute = 0
        
        # Cache for frequently used data
        self.folder_cache = {}
        self.space_cache = {}
        self.account_id = None
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce Wrike rate limits"""
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
        retry=retry_if_exception_type((requests.RequestException, WrikeRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to Wrike API"""
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
                raise WrikeRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                result = response.json()
                # Wrike wraps responses in 'data' key
                return result.get('data', result) if 'data' in result else result
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise WrikeAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL WRIKE API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            account = self._make_request('GET', '/account')
            if account:
                self.account_id = account[0]['id']
                self.logger.info(f"Connected to Wrike account: {account[0]['name']}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_account(self) -> Dict[str, Any]:
        """Get account details"""
        accounts = self._make_request('GET', '/account')
        if accounts:
            self.account_id = accounts[0]['id']
            return accounts[0]
        return {}
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        contacts = self._make_request('GET', '/contacts', {'me': True})
        return contacts[0] if contacts else {}
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users (contacts)"""
        return self._make_request('GET', '/contacts')
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups"""
        if not self.account_id:
            self.get_account()
        
        return self._make_request('GET', f'/accounts/{self.account_id}/groups')
    
    def get_spaces(self) -> List[Dict[str, Any]]:
        """Get all spaces"""
        spaces = self._make_request('GET', '/spaces')
        
        # Cache spaces
        for space in spaces:
            self.space_cache[space['id']] = space
        
        return spaces
    
    def get_folders(self, space_id: str = None, parent_id: str = None) -> List[Dict[str, Any]]:
        """Get folders, optionally filtered by space or parent"""
        if space_id:
            endpoint = f'/spaces/{space_id}/folders'
        elif parent_id:
            endpoint = f'/folders/{parent_id}/folders'
        else:
            endpoint = '/folders'
        
        params = {
            'descendants': False,  # Don't get all descendants at once
            'fields': '["customFields","project","metadata"]'
        }
        
        folders = self._make_request('GET', endpoint, params)
        
        # Cache folders
        for folder in folders:
            self.folder_cache[folder['id']] = folder
        
        return folders
    
    def get_folder(self, folder_id: str) -> Dict[str, Any]:
        """Get detailed folder information"""
        # Check cache first
        if folder_id in self.folder_cache:
            return self.folder_cache[folder_id]
        
        params = {
            'fields': '["customFields","project","metadata","hasAttachments","attachmentCount","description","briefDescription"]'
        }
        
        folders = self._make_request('GET', f'/folders/{folder_id}', params)
        
        if folders:
            folder = folders[0]
            self.folder_cache[folder_id] = folder
            return folder
        
        return None
    
    def get_tasks(self, folder_id: str = None, space_id: str = None, 
                 fields: List[str] = None) -> List[Dict[str, Any]]:
        """Get tasks from folder or space"""
        if folder_id:
            endpoint = f'/folders/{folder_id}/tasks'
        elif space_id:
            endpoint = f'/spaces/{space_id}/tasks'
        else:
            endpoint = '/tasks'
        
        params = {}
        if fields:
            params['fields'] = json.dumps(fields)
        else:
            params['fields'] = '["customFields","attachmentCount","description","briefDescription","recurrent","superTaskIds","subTaskIds","dependencyIds","metadata","responsibleIds"]'
        
        return self._make_request('GET', endpoint, params)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get detailed task information"""
        params = {
            'fields': '["customFields","attachmentCount","description","briefDescription","recurrent","superTaskIds","subTaskIds","dependencyIds","metadata","responsibleIds","attachments","comments"]'
        }
        
        tasks = self._make_request('GET', f'/tasks/{task_id}', params)
        return tasks[0] if tasks else None
    
    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """Get all custom fields"""
        if not self.account_id:
            self.get_account()
        
        return self._make_request('GET', f'/accounts/{self.account_id}/customfields')
    
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows (custom statuses)"""
        if not self.account_id:
            self.get_account()
        
        return self._make_request('GET', f'/accounts/{self.account_id}/workflows')
    
    def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get comments for a task"""
        return self._make_request('GET', f'/tasks/{task_id}/comments')
    
    def get_task_attachments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get attachments for a task"""
        return self._make_request('GET', f'/tasks/{task_id}/attachments')
    
    def get_timelogs(self, task_id: str = None, contact_id: str = None, 
                    start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Get time logs"""
        params = {}
        
        if task_id:
            endpoint = f'/tasks/{task_id}/timelogs'
        elif contact_id:
            endpoint = f'/contacts/{contact_id}/timelogs'
        else:
            endpoint = '/timelogs'
        
        if start_date:
            params['createdDate'] = {
                'start': start_date.isoformat()
            }
            if end_date:
                params['createdDate']['end'] = end_date.isoformat()
        
        return self._make_request('GET', endpoint, params)
    
    def get_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task dependencies"""
        return self._make_request('GET', f'/tasks/{task_id}/dependencies')
    
    def get_approvals(self, task_id: str = None, folder_id: str = None) -> List[Dict[str, Any]]:
        """Get approvals"""
        if task_id:
            endpoint = f'/tasks/{task_id}/approvals'
        elif folder_id:
            endpoint = f'/folders/{folder_id}/approvals'
        else:
            if not self.account_id:
                self.get_account()
            endpoint = f'/accounts/{self.account_id}/approvals'
        
        return self._make_request('GET', endpoint)
    
    # ============= FOLDER HIERARCHY =============
    
    def get_folder_tree(self, space_id: str = None) -> Dict[str, Any]:
        """Get complete folder hierarchy"""
        if space_id:
            endpoint = f'/spaces/{space_id}/folders'
        else:
            endpoint = '/folders'
        
        params = {
            'descendants': True,  # Get all descendants
            'fields': '["customFields","project","childIds","parentIds"]'
        }
        
        folders = self._make_request('GET', endpoint, params)
        
        # Build hierarchy tree
        tree = {
            'root': [],
            'folders': {}
        }
        
        for folder in folders:
            folder_id = folder['id']
            tree['folders'][folder_id] = folder
            
            if not folder.get('parentIds'):
                tree['root'].append(folder_id)
        
        return tree
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_tasks(self, folder_id: str = None, 
                       batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get tasks in batches"""
        # Wrike doesn't have traditional pagination
        # Get all tasks and yield in batches
        tasks = self.get_tasks(folder_id=folder_id)
        
        for i in range(0, len(tasks), batch_size):
            yield tasks[i:i + batch_size]
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Wrike data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'account': self.get_account(),
            'users': [],
            'groups': [],
            'spaces': [],
            'folders': [],
            'tasks': [],
            'custom_fields': [],
            'workflows': [],
            'total_folders': 0,
            'total_tasks': 0
        }
        
        # Get users
        self.logger.info("Fetching users...")
        data['users'] = self.get_users()
        
        # Get groups
        self.logger.info("Fetching groups...")
        data['groups'] = self.get_groups()
        
        # Get custom fields
        self.logger.info("Fetching custom fields...")
        data['custom_fields'] = self.get_custom_fields()
        
        # Get workflows
        self.logger.info("Fetching workflows...")
        data['workflows'] = self.get_workflows()
        
        # Get spaces
        self.logger.info("Fetching spaces...")
        spaces = self.get_spaces()
        
        for space in spaces:
            self.logger.info(f"Processing space: {space['title']}")
            
            space_data = space.copy()
            space_data['folders'] = []
            
            # Get folder tree for space
            tree = self.get_folder_tree(space['id'])
            
            # Process folders
            for folder_id, folder in tree['folders'].items():
                self.logger.info(f"  Processing folder: {folder['title']}")
                
                # Get full folder details
                folder_data = self.get_folder(folder_id)
                
                # Get tasks
                tasks = self.get_tasks(folder_id=folder_id)
                folder_data['tasks'] = []
                
                for task in tasks:
                    # Get full task details
                    task_data = self.get_task(task['id'])
                    
                    # Get comments
                    task_data['comments'] = self.get_task_comments(task['id'])
                    
                    # Get attachments
                    task_data['attachments'] = self.get_task_attachments(task['id'])
                    
                    # Get dependencies
                    task_data['dependencies'] = self.get_dependencies(task['id'])
                    
                    # Get timelogs
                    task_data['timelogs'] = self.get_timelogs(task_id=task['id'])
                    
                    folder_data['tasks'].append(task_data)
                    data['total_tasks'] += 1
                
                space_data['folders'].append(folder_data)
                data['total_folders'] += 1
                
                self.logger.info(f"    Processed {len(tasks)} tasks")
                
                # Rate limit pause
                time.sleep(1)
            
            data['spaces'].append(space_data)
        
        self.logger.info(f"Export complete: {data['total_folders']} folders, {data['total_tasks']} tasks")
        
        return data
    
    # ============= PARADIGM SHIFT HELPERS =============
    
    def analyze_folder_structure(self) -> Dict[str, Any]:
        """
        Analyze folder hierarchy depth and complexity
        Wrike has deep folder nesting
        """
        tree = self.get_folder_tree()
        
        analysis = {
            'total_folders': len(tree['folders']),
            'root_folders': len(tree['root']),
            'max_depth': 0,
            'average_depth': 0,
            'has_projects': False,
            'custom_fields_used': False
        }
        
        # Calculate folder depth
        def get_depth(folder_id, current_depth=0):
            folder = tree['folders'].get(folder_id, {})
            child_ids = folder.get('childIds', [])
            
            if not child_ids:
                return current_depth
            
            max_child_depth = current_depth
            for child_id in child_ids:
                if child_id in tree['folders']:
                    child_depth = get_depth(child_id, current_depth + 1)
                    max_child_depth = max(max_child_depth, child_depth)
            
            return max_child_depth
        
        depths = []
        for root_id in tree['root']:
            depth = get_depth(root_id)
            depths.append(depth)
            analysis['max_depth'] = max(analysis['max_depth'], depth)
        
        if depths:
            analysis['average_depth'] = sum(depths) / len(depths)
        
        # Check for projects
        for folder in tree['folders'].values():
            if folder.get('project'):
                analysis['has_projects'] = True
                break
        
        # Check custom fields
        custom_fields = self.get_custom_fields()
        if custom_fields:
            analysis['custom_fields_used'] = True
            analysis['custom_field_count'] = len(custom_fields)
        
        # Recommend transformation strategy
        if analysis['max_depth'] > 3:
            analysis['recommended_strategy'] = 'flatten_hierarchy'
        elif analysis['has_projects']:
            analysis['recommended_strategy'] = 'project_to_template'
        else:
            analysis['recommended_strategy'] = 'direct_folder_mapping'
        
        return analysis
    
    def parse_custom_field_value(self, field_type: str, value: Any) -> Any:
        """
        Parse custom field value based on Wrike field type
        """
        if not value:
            return None
        
        if field_type == WrikeCustomFieldType.DATE.value:
            # Date fields return ISO format
            return value
        
        elif field_type == WrikeCustomFieldType.DROPDOWN.value:
            # Dropdown returns selected option
            return value
        
        elif field_type == WrikeCustomFieldType.NUMERIC.value:
            # Numeric fields
            try:
                return float(value) if value else None
            except:
                return None
        
        elif field_type == WrikeCustomFieldType.CURRENCY.value:
            # Currency fields
            if isinstance(value, dict):
                return {
                    'amount': value.get('value'),
                    'currency': value.get('currency', 'USD')
                }
            return value
        
        elif field_type == WrikeCustomFieldType.PERCENTAGE.value:
            # Percentage fields
            try:
                return float(value) / 100 if value else None
            except:
                return None
        
        elif field_type == WrikeCustomFieldType.DURATION.value:
            # Duration in minutes
            return value
        
        elif field_type == WrikeCustomFieldType.CHECKBOX.value:
            # Boolean
            return bool(value)
        
        elif field_type == WrikeCustomFieldType.CONTACTS.value:
            # User IDs
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        elif field_type == WrikeCustomFieldType.MULTIPLE.value:
            # Multiple selection
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        else:
            # Default: return as-is
            return value
    
    # ============= CREATE OPERATIONS =============
    
    def create_folder(self, title: str, parent_id: str = None, 
                     space_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new folder"""
        if parent_id:
            endpoint = f'/folders/{parent_id}/folders'
        elif space_id:
            endpoint = f'/spaces/{space_id}/folders'
        else:
            endpoint = '/folders'
        
        data = {
            'title': title,
            **kwargs
        }
        
        result = self._make_request('POST', endpoint, data=data)
        return result[0] if result else None
    
    def create_task(self, folder_id: str, title: str, 
                   description: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new task"""
        data = {
            'title': title
        }
        
        if description:
            data['description'] = description
        
        data.update(kwargs)
        
        result = self._make_request('POST', f'/folders/{folder_id}/tasks', data=data)
        return result[0] if result else None
    
    def add_comment(self, task_id: str, text: str) -> Dict[str, Any]:
        """Add comment to task"""
        data = {
            'text': text
        }
        
        result = self._make_request('POST', f'/tasks/{task_id}/comments', data=data)
        return result[0] if result else None
    
    def create_webhook(self, folder_id: str, url: str) -> Dict[str, Any]:
        """Create webhook for folder"""
        data = {
            'hookUrl': url
        }
        
        if not self.account_id:
            self.get_account()
        
        result = self._make_request('POST', f'/accounts/{self.account_id}/webhooks', data=data)
        return result[0] if result else None


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = WrikeProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Wrike")
        
        # Get account
        account = client.get_account()
        print(f"Account: {account.get('name', 'Unknown')}")
        
        # Get current user
        user = client.get_current_user()
        print(f"User: {user.get('firstName', '')} {user.get('lastName', '')}")
        
        # Analyze folder structure
        analysis = client.analyze_folder_structure()
        print(f"\nFolder structure analysis:")
        print(f"  - Total folders: {analysis['total_folders']}")
        print(f"  - Max depth: {analysis['max_depth']}")
        print(f"  - Has projects: {analysis['has_projects']}")
        print(f"  - Custom fields: {analysis['custom_fields_used']}")
        print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
        
        # Get spaces
        spaces = client.get_spaces()
        print(f"\nFound {len(spaces)} spaces")
        
        if spaces:
            space = spaces[0]
            print(f"\nSpace: {space['title']}")
            
            # Get folders
            folders = client.get_folders(space_id=space['id'])
            print(f"Folders: {len(folders)}")
            
            if folders:
                folder = folders[0]
                print(f"\nFolder: {folder['title']}")
                
                # Get tasks
                tasks = client.get_tasks(folder_id=folder['id'])
                print(f"Tasks: {len(tasks)}")
                
                for task in tasks[:3]:
                    print(f"  - {task['title']} ({task.get('status', 'Unknown')})")
    
    print("\n✅ Production Wrike client ready!")