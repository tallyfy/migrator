#!/usr/bin/env python3
"""
Production-Grade ClickUp API Client
Implements actual ClickUp API v2 with proper authentication, rate limiting, and error handling
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


class ClickUpRateLimitError(Exception):
    """ClickUp rate limit exceeded"""
    pass


class ClickUpAuthError(Exception):
    """ClickUp authentication failed"""
    pass


class ClickUpViewType(str, Enum):
    """ClickUp view types"""
    LIST = "list"
    BOARD = "board"
    BOX = "box"
    CALENDAR = "calendar"
    GANTT = "gantt"
    TIMELINE = "timeline"
    WORKLOAD = "workload"
    ACTIVITY = "activity"
    MAP = "map"
    TABLE = "table"
    DOC = "doc"
    EMBED = "embed"
    FORM = "form"
    CHAT = "chat"


class ClickUpFieldType(str, Enum):
    """ClickUp custom field types"""
    TEXT = "text"
    NUMBER = "number"
    MONEY = "money"
    DATE = "date"
    CHECKBOX = "checkbox"
    DROP_DOWN = "drop_down"
    LABELS = "labels"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    LOCATION = "location"
    USERS = "users"
    EMOJI = "emoji"
    AUTOMATIC_PROGRESS = "automatic_progress"
    MANUAL_PROGRESS = "manual_progress"
    SHORT_TEXT = "short_text"
    FORMULA = "formula"
    RELATIONSHIP = "relationship"
    RATING = "rating"


class ClickUpProductionClient:
    """
    Production ClickUp API client with actual endpoints
    Implements ClickUp API v2
    """
    
    BASE_URL = "https://api.clickup.com/api/v2"
    
    # ClickUp rate limits
    RATE_LIMITS = {
        'requests_per_minute': 100,
        'requests_per_second': 10,
        'burst_limit': 20
    }
    
    def __init__(self):
        """Initialize ClickUp client with actual authentication"""
        self.api_key = os.getenv('CLICKUP_API_KEY')
        
        if not self.api_key:
            raise ClickUpAuthError("CLICKUP_API_KEY required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.request_times = []
        self.minute_start = datetime.now()
        self.requests_this_minute = 0
        
        # Cache for workspace/team data
        self.workspace_cache = {}
        self.team_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce ClickUp rate limits"""
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
        
        # Check requests per second (sliding window)
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
        retry=retry_if_exception_type((requests.RequestException, ClickUpRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None, files: Dict = None) -> Any:
        """Make authenticated request to ClickUp API"""
        self._check_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                files=files,
                timeout=30
            )
            
            # Check for rate limit response
            if response.status_code == 429:
                retry_after = int(response.headers.get('X-RateLimit-Reset', 60))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise ClickUpRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                return response.json()
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ClickUpAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                if e.response.text:
                    self.logger.error(f"Response: {e.response.text}")
                raise
    
    # ============= ACTUAL CLICKUP API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            user = self._make_request('GET', '/user')
            self.logger.info(f"Connected to ClickUp as {user['user']['username']}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_authorized_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        return self._make_request('GET', '/user')
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams (workspaces) accessible to the user"""
        response = self._make_request('GET', '/team')
        teams = response.get('teams', [])
        
        # Cache teams for later use
        for team in teams:
            self.team_cache[team['id']] = team
        
        return teams
    
    def get_team(self, team_id: str) -> Dict[str, Any]:
        """Get detailed team information"""
        # Check cache first
        if team_id in self.team_cache:
            return self.team_cache[team_id]
        
        team = self._make_request('GET', f'/team/{team_id}')
        self.team_cache[team_id] = team
        return team
    
    def get_spaces(self, team_id: str, archived: bool = False) -> List[Dict[str, Any]]:
        """Get all spaces in a team"""
        params = {'archived': archived}
        response = self._make_request('GET', f'/team/{team_id}/space', params)
        return response.get('spaces', [])
    
    def get_space(self, space_id: str) -> Dict[str, Any]:
        """Get detailed space information"""
        return self._make_request('GET', f'/space/{space_id}')
    
    def get_folders(self, space_id: str, archived: bool = False) -> List[Dict[str, Any]]:
        """Get all folders in a space"""
        params = {'archived': archived}
        response = self._make_request('GET', f'/space/{space_id}/folder', params)
        return response.get('folders', [])
    
    def get_folder(self, folder_id: str) -> Dict[str, Any]:
        """Get detailed folder information"""
        return self._make_request('GET', f'/folder/{folder_id}')
    
    def get_lists(self, folder_id: str = None, space_id: str = None, 
                 archived: bool = False) -> List[Dict[str, Any]]:
        """
        Get lists from folder or space (folderless lists)
        
        Args:
            folder_id: Folder to get lists from
            space_id: Space to get folderless lists from
            archived: Include archived lists
        """
        params = {'archived': archived}
        
        if folder_id:
            endpoint = f'/folder/{folder_id}/list'
        elif space_id:
            endpoint = f'/space/{space_id}/list'
        else:
            raise ValueError("Either folder_id or space_id required")
        
        response = self._make_request('GET', endpoint, params)
        return response.get('lists', [])
    
    def get_list(self, list_id: str) -> Dict[str, Any]:
        """Get detailed list information"""
        return self._make_request('GET', f'/list/{list_id}')
    
    def get_tasks(self, list_id: str = None, team_id: str = None, 
                 include_closed: bool = False, include_subtasks: bool = True,
                 page: int = 0) -> Dict[str, Any]:
        """
        Get tasks from list or entire workspace
        
        Args:
            list_id: List to get tasks from
            team_id: Team to get all tasks from
            include_closed: Include closed/archived tasks
            include_subtasks: Include subtasks in response
            page: Page number for pagination
        """
        params = {
            'archived': include_closed,
            'include_closed': include_closed,
            'subtasks': include_subtasks,
            'page': page
        }
        
        if list_id:
            endpoint = f'/list/{list_id}/task'
        elif team_id:
            params['team_id'] = team_id
            endpoint = '/team/{team_id}/task'
        else:
            raise ValueError("Either list_id or team_id required")
        
        response = self._make_request('GET', endpoint, params)
        return response
    
    def get_task(self, task_id: str, include_subtasks: bool = True) -> Dict[str, Any]:
        """Get detailed task information"""
        params = {
            'include_subtasks': include_subtasks,
            'include_markdown_description': True
        }
        return self._make_request('GET', f'/task/{task_id}', params)
    
    def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all comments on a task"""
        response = self._make_request('GET', f'/task/{task_id}/comment')
        return response.get('comments', [])
    
    def get_task_time_entries(self, task_id: str) -> List[Dict[str, Any]]:
        """Get time tracking entries for a task"""
        response = self._make_request('GET', f'/task/{task_id}/time')
        return response.get('data', [])
    
    def get_custom_fields(self, list_id: str) -> List[Dict[str, Any]]:
        """Get custom fields for a list"""
        response = self._make_request('GET', f'/list/{list_id}/field')
        return response.get('fields', [])
    
    def get_tags(self, space_id: str) -> List[Dict[str, Any]]:
        """Get all tags in a space"""
        response = self._make_request('GET', f'/space/{space_id}/tag')
        return response.get('tags', [])
    
    def get_members(self, list_id: str = None, task_id: str = None) -> List[Dict[str, Any]]:
        """Get members of a list or task"""
        if list_id:
            response = self._make_request('GET', f'/list/{list_id}/member')
        elif task_id:
            response = self._make_request('GET', f'/task/{task_id}/member')
        else:
            raise ValueError("Either list_id or task_id required")
        
        return response.get('members', [])
    
    def get_views(self, list_id: str = None, space_id: str = None, 
                 team_id: str = None) -> List[Dict[str, Any]]:
        """Get views for list, space, or team"""
        if list_id:
            endpoint = f'/list/{list_id}/view'
        elif space_id:
            endpoint = f'/space/{space_id}/view'
        elif team_id:
            endpoint = f'/team/{team_id}/view'
        else:
            raise ValueError("list_id, space_id, or team_id required")
        
        response = self._make_request('GET', endpoint)
        return response.get('views', [])
    
    def get_goals(self, team_id: str) -> List[Dict[str, Any]]:
        """Get goals for a team"""
        response = self._make_request('GET', f'/team/{team_id}/goal')
        return response.get('goals', [])
    
    def get_webhooks(self, team_id: str) -> List[Dict[str, Any]]:
        """Get webhooks for a team"""
        response = self._make_request('GET', f'/team/{team_id}/webhook')
        return response.get('webhooks', [])
    
    def get_time_entries(self, team_id: str, start_date: datetime = None, 
                        end_date: datetime = None) -> List[Dict[str, Any]]:
        """Get time entries for a team"""
        params = {}
        if start_date:
            params['start_date'] = int(start_date.timestamp() * 1000)
        if end_date:
            params['end_date'] = int(end_date.timestamp() * 1000)
        
        response = self._make_request('GET', f'/team/{team_id}/time_entries', params)
        return response.get('data', [])
    
    def get_task_templates(self, team_id: str) -> List[Dict[str, Any]]:
        """Get task templates for a team"""
        params = {'page': 0}
        response = self._make_request('GET', f'/team/{team_id}/task_template', params)
        return response.get('templates', [])
    
    def get_automations(self, list_id: str) -> List[Dict[str, Any]]:
        """Get automations for a list"""
        response = self._make_request('GET', f'/list/{list_id}/automation')
        return response.get('automations', [])
    
    def get_dependencies(self, task_id: str) -> Dict[str, Any]:
        """Get task dependencies"""
        response = self._make_request('GET', f'/task/{task_id}/dependency')
        return {
            'depends_on': response.get('depends_on', []),
            'dependency_of': response.get('dependency_of', []),
            'links_to': response.get('links_to', []),
            'linked_to': response.get('linked_to', [])
        }
    
    # ============= SEARCH OPERATIONS =============
    
    def search_tasks(self, team_id: str, query: str = None, 
                    filters: Dict = None) -> List[Dict[str, Any]]:
        """
        Search tasks in team
        
        Args:
            team_id: Team to search in
            query: Search query string
            filters: Additional filters (assignees, tags, etc.)
        """
        params = {
            'team_id': team_id,
            'include_closed': True
        }
        
        if query:
            params['query'] = query
        
        if filters:
            # ClickUp uses specific filter format
            if 'assignees' in filters:
                params['assignees[]'] = filters['assignees']
            if 'tags' in filters:
                params['tags[]'] = filters['tags']
            if 'statuses' in filters:
                params['statuses[]'] = filters['statuses']
            if 'due_date_gt' in filters:
                params['due_date_gt'] = filters['due_date_gt']
            if 'due_date_lt' in filters:
                params['due_date_lt'] = filters['due_date_lt']
        
        response = self._make_request('GET', f'/team/{team_id}/task', params)
        return response.get('tasks', [])
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_tasks(self, list_id: str, batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """
        Get tasks in batches to handle large lists
        
        Args:
            list_id: List ID
            batch_size: Number of tasks per batch
            
        Yields:
            Batches of tasks
        """
        page = 0
        
        while True:
            response = self.get_tasks(list_id=list_id, page=page)
            tasks = response.get('tasks', [])
            
            if not tasks:
                break
            
            # Yield in batches
            for i in range(0, len(tasks), batch_size):
                yield tasks[i:i + batch_size]
            
            # Check if there are more pages
            if not response.get('last_page', True):
                page += 1
                time.sleep(0.5)  # Rate limit pause
            else:
                break
    
    def get_all_data(self, team_id: str, include_archived: bool = False) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Args:
            team_id: Team (workspace) to export
            include_archived: Include archived items
            
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete ClickUp data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'team': self.get_team(team_id),
            'spaces': [],
            'members': [],
            'goals': [],
            'tags': [],
            'total_lists': 0,
            'total_tasks': 0,
            'total_folders': 0
        }
        
        # Get team members
        self.logger.info("Fetching team members...")
        team_data = self._make_request('GET', f'/team/{team_id}')
        data['members'] = team_data.get('team', {}).get('members', [])
        
        # Get goals
        self.logger.info("Fetching goals...")
        data['goals'] = self.get_goals(team_id)
        
        # Get spaces
        self.logger.info("Fetching spaces...")
        spaces = self.get_spaces(team_id, archived=include_archived)
        
        for space in spaces:
            if not include_archived and space.get('archived'):
                continue
            
            self.logger.info(f"Processing space: {space['name']}")
            
            space_data = self.get_space(space['id'])
            space_data['tags'] = self.get_tags(space['id'])
            space_data['folders'] = []
            space_data['lists'] = []  # For folderless lists
            
            # Get folders
            folders = self.get_folders(space['id'], archived=include_archived)
            
            for folder in folders:
                if not include_archived and folder.get('archived'):
                    continue
                
                self.logger.info(f"  Processing folder: {folder['name']}")
                
                folder_data = self.get_folder(folder['id'])
                folder_data['lists'] = []
                
                # Get lists in folder
                lists = self.get_lists(folder_id=folder['id'], archived=include_archived)
                
                for list_item in lists:
                    if not include_archived and list_item.get('archived'):
                        continue
                    
                    self.logger.info(f"    Processing list: {list_item['name']}")
                    
                    list_data = self.get_list(list_item['id'])
                    
                    # Get custom fields
                    list_data['custom_fields'] = self.get_custom_fields(list_item['id'])
                    
                    # Get views
                    list_data['views'] = self.get_views(list_id=list_item['id'])
                    
                    # Get automations
                    list_data['automations'] = self.get_automations(list_item['id'])
                    
                    # Get tasks
                    list_data['tasks'] = []
                    task_count = 0
                    
                    for task_batch in self.batch_get_tasks(list_item['id']):
                        for task in task_batch:
                            # Get additional task details
                            task_detail = self.get_task(task['id'])
                            
                            # Get comments
                            task_detail['comments'] = self.get_task_comments(task['id'])
                            
                            # Get time entries
                            task_detail['time_entries'] = self.get_task_time_entries(task['id'])
                            
                            # Get dependencies
                            task_detail['dependencies'] = self.get_dependencies(task['id'])
                            
                            list_data['tasks'].append(task_detail)
                            task_count += 1
                        
                        # Rate limit pause
                        time.sleep(1)
                    
                    data['total_tasks'] += task_count
                    folder_data['lists'].append(list_data)
                    data['total_lists'] += 1
                    
                    self.logger.info(f"      Processed {task_count} tasks")
                
                space_data['folders'].append(folder_data)
                data['total_folders'] += 1
            
            # Get folderless lists
            folderless_lists = self.get_lists(space_id=space['id'], archived=include_archived)
            
            for list_item in folderless_lists:
                if not include_archived and list_item.get('archived'):
                    continue
                
                self.logger.info(f"  Processing folderless list: {list_item['name']}")
                
                list_data = self.get_list(list_item['id'])
                list_data['custom_fields'] = self.get_custom_fields(list_item['id'])
                list_data['views'] = self.get_views(list_id=list_item['id'])
                list_data['automations'] = self.get_automations(list_item['id'])
                list_data['tasks'] = []
                
                # Get tasks (simplified for folderless lists)
                response = self.get_tasks(list_id=list_item['id'])
                for task in response.get('tasks', []):
                    list_data['tasks'].append(task)
                    data['total_tasks'] += 1
                
                space_data['lists'].append(list_data)
                data['total_lists'] += 1
            
            data['spaces'].append(space_data)
        
        self.logger.info(f"Export complete: {data['total_lists']} lists, {data['total_tasks']} tasks")
        
        return data
    
    # ============= CREATE OPERATIONS =============
    
    def create_list(self, name: str, folder_id: str = None, space_id: str = None, 
                   **kwargs) -> Dict[str, Any]:
        """Create a new list"""
        if folder_id:
            endpoint = f'/folder/{folder_id}/list'
        elif space_id:
            endpoint = f'/space/{space_id}/list'
        else:
            raise ValueError("Either folder_id or space_id required")
        
        data = {
            'name': name,
            **kwargs
        }
        return self._make_request('POST', endpoint, data=data)
    
    def create_task(self, list_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new task"""
        data = {
            'name': name,
            **kwargs
        }
        return self._make_request('POST', f'/list/{list_id}/task', data=data)
    
    def add_comment(self, task_id: str, comment_text: str, 
                   notify_all: bool = False) -> Dict[str, Any]:
        """Add comment to task"""
        data = {
            'comment_text': comment_text,
            'notify_all': notify_all
        }
        return self._make_request('POST', f'/task/{task_id}/comment', data=data)
    
    def add_attachment(self, task_id: str, file_path: str) -> Dict[str, Any]:
        """Add attachment to task"""
        with open(file_path, 'rb') as f:
            files = {'attachment': f}
            return self._make_request('POST', f'/task/{task_id}/attachment', files=files)
    
    def create_webhook(self, team_id: str, endpoint: str, events: List[str]) -> Dict[str, Any]:
        """Create webhook for team"""
        data = {
            'endpoint': endpoint,
            'events': events
        }
        return self._make_request('POST', f'/team/{team_id}/webhook', data=data)
    
    # ============= PARADIGM SHIFT HELPERS =============
    
    def detect_primary_view(self, list_id: str) -> str:
        """
        Detect the primary view type for a list
        Important for paradigm shift handling
        """
        views = self.get_views(list_id=list_id)
        
        if not views:
            return ClickUpViewType.LIST.value
        
        # Find the view with highest usage or set as default
        primary = views[0]
        for view in views:
            if view.get('favorite') or view.get('is_default'):
                primary = view
                break
        
        return primary.get('type', ClickUpViewType.LIST.value)
    
    def analyze_hierarchy(self, team_id: str) -> Dict[str, Any]:
        """
        Analyze the workspace hierarchy structure
        Useful for understanding organization patterns
        """
        spaces = self.get_spaces(team_id)
        
        hierarchy = {
            'depth': 0,
            'has_folders': False,
            'has_folderless_lists': False,
            'space_count': len(spaces),
            'structure': []
        }
        
        for space in spaces:
            folders = self.get_folders(space['id'])
            folderless = self.get_lists(space_id=space['id'])
            
            if folders:
                hierarchy['has_folders'] = True
                hierarchy['depth'] = max(hierarchy['depth'], 3)  # Team > Space > Folder > List
            
            if folderless:
                hierarchy['has_folderless_lists'] = True
                hierarchy['depth'] = max(hierarchy['depth'], 2)  # Team > Space > List
            
            hierarchy['structure'].append({
                'space': space['name'],
                'folders': len(folders),
                'folderless_lists': len(folderless)
            })
        
        return hierarchy


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = ClickUpProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to ClickUp")
        
        # Get teams (workspaces)
        teams = client.get_teams()
        print(f"Found {len(teams)} teams")
        
        if teams:
            team = teams[0]
            print(f"Using team: {team['name']}")
            
            # Analyze hierarchy
            hierarchy = client.analyze_hierarchy(team['id'])
            print(f"Hierarchy depth: {hierarchy['depth']}")
            print(f"Has folders: {hierarchy['has_folders']}")
            
            # Get spaces
            spaces = client.get_spaces(team['id'])
            print(f"Found {len(spaces)} spaces")
            
            if spaces:
                space = spaces[0]
                
                # Get lists
                lists = client.get_lists(space_id=space['id'])
                print(f"Found {len(lists)} lists in {space['name']}")
                
                if lists:
                    list_item = lists[0]
                    
                    # Detect primary view
                    primary_view = client.detect_primary_view(list_item['id'])
                    print(f"Primary view for {list_item['name']}: {primary_view}")
                    
                    # Get tasks
                    response = client.get_tasks(list_id=list_item['id'])
                    tasks = response.get('tasks', [])
                    print(f"Found {len(tasks)} tasks")
    
    print("\n✅ Production ClickUp client ready!")