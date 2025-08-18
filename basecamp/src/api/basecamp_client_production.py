#!/usr/bin/env python3
"""
Production-Grade Basecamp API Client
Implements actual Basecamp API v3 with proper authentication, rate limiting, and error handling
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


class BasecampRateLimitError(Exception):
    """Basecamp rate limit exceeded"""
    pass


class BasecampAuthError(Exception):
    """Basecamp authentication failed"""
    pass


class BasecampResourceType(str, Enum):
    """Basecamp resource types"""
    PROJECT = "project"
    MESSAGE = "message"
    TODO_LIST = "todolist"
    TODO = "todo"
    COMMENT = "comment"
    DOCUMENT = "document"
    UPLOAD = "upload"
    CAMPFIRE = "campfire"
    SCHEDULE = "schedule"
    QUESTIONNAIRE = "questionnaire"
    VAULT = "vault"


class BasecampProductionClient:
    """
    Production Basecamp API client with actual endpoints
    Implements Basecamp API v3
    """
    
    BASE_URL = "https://3.basecampapi.com"
    
    # Basecamp rate limits
    RATE_LIMITS = {
        'requests_per_10_seconds': 50,
        'burst_limit': 10
    }
    
    def __init__(self):
        """Initialize Basecamp client with actual authentication"""
        self.access_token = os.getenv('BASECAMP_ACCESS_TOKEN')
        self.account_id = os.getenv('BASECAMP_ACCOUNT_ID')
        self.client_id = os.getenv('BASECAMP_CLIENT_ID')
        self.client_secret = os.getenv('BASECAMP_CLIENT_SECRET')
        self.refresh_token = os.getenv('BASECAMP_REFRESH_TOKEN')
        
        if not self.access_token or not self.account_id:
            raise BasecampAuthError("BASECAMP_ACCESS_TOKEN and BASECAMP_ACCOUNT_ID required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Tallyfy Migrator (support@tallyfy.com)'
        })
        
        # Rate limiting tracking
        self.request_times = []
        
        # Cache for frequently used data
        self.project_cache = {}
        self.people_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce Basecamp rate limits"""
        now = datetime.now()
        
        # Remove requests older than 10 seconds
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(seconds=10)
        ]
        
        # Check 50 requests per 10 seconds limit
        if len(self.request_times) >= self.RATE_LIMITS['requests_per_10_seconds']:
            wait_time = 10 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached. Waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                self.request_times = []
        
        self.request_times.append(now)
    
    def _refresh_access_token(self):
        """Refresh OAuth access token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise BasecampAuthError("Cannot refresh token - missing OAuth credentials")
        
        url = "https://launchpad.37signals.com/authorization/token"
        data = {
            'type': 'refresh',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.session.headers['Authorization'] = f'Bearer {self.access_token}'
            self.logger.info("Access token refreshed successfully")
            return True
        else:
            self.logger.error(f"Failed to refresh token: {response.text}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, BasecampRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to Basecamp API"""
        self._check_rate_limit()
        
        # Build URL with account ID
        if endpoint.startswith('/'):
            url = f"{self.BASE_URL}/{self.account_id}{endpoint}.json"
        else:
            url = endpoint  # Full URL provided (for pagination)
        
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
                retry_after = int(response.headers.get('Retry-After', 10))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise BasecampRateLimitError("Rate limit exceeded")
            
            # Try refreshing token if unauthorized
            if response.status_code == 401:
                if self._refresh_access_token():
                    # Retry request with new token
                    response = self.session.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data,
                        timeout=30
                    )
                else:
                    raise BasecampAuthError("Authentication failed and couldn't refresh token")
            
            response.raise_for_status()
            
            # Parse response
            if response.text:
                result = response.json()
                
                # Handle pagination info
                if 'Link' in response.headers:
                    next_link = self._parse_link_header(response.headers['Link'])
                    if next_link:
                        result = {'data': result, 'next': next_link}
                
                return result
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    def _parse_link_header(self, link_header: str) -> Optional[str]:
        """Parse Link header for next page URL"""
        if not link_header:
            return None
        
        for link in link_header.split(','):
            if 'rel="next"' in link:
                # Extract URL from <URL>; rel="next"
                url = link.split(';')[0].strip('<> ')
                return url
        
        return None
    
    # ============= ACTUAL BASECAMP API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Get authorization info
            auth = self._make_request('GET', '/authorization')
            self.logger.info(f"Connected to Basecamp as {auth['identity']['email_address']}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_authorization(self) -> Dict[str, Any]:
        """Get authorization and account info"""
        return self._make_request('GET', '/authorization')
    
    def get_people(self) -> List[Dict[str, Any]]:
        """Get all people in account"""
        people = self._make_request('GET', '/people')
        
        # Cache people
        for person in people:
            self.people_cache[person['id']] = person
        
        return people
    
    def get_person(self, person_id: int) -> Dict[str, Any]:
        """Get detailed person information"""
        # Check cache first
        if person_id in self.people_cache:
            return self.people_cache[person_id]
        
        person = self._make_request('GET', f'/people/{person_id}')
        
        if person:
            self.people_cache[person_id] = person
        
        return person
    
    def get_projects(self, status: str = 'active') -> List[Dict[str, Any]]:
        """Get all projects"""
        # Status can be: active, archived, trashed
        params = {'status': status}
        
        projects = self._make_request('GET', '/projects', params)
        
        # Cache projects
        for project in projects:
            self.project_cache[project['id']] = project
        
        return projects
    
    def get_project(self, project_id: int) -> Dict[str, Any]:
        """Get detailed project information"""
        # Check cache first
        if project_id in self.project_cache:
            return self.project_cache[project_id]
        
        project = self._make_request('GET', f'/projects/{project_id}')
        
        if project:
            self.project_cache[project_id] = project
        
        return project
    
    def get_project_tools(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all tools (apps) enabled for a project"""
        # This returns the dock - list of enabled tools
        project = self.get_project(project_id)
        return project.get('dock', [])
    
    def get_todo_lists(self, project_id: int, status: str = 'active') -> List[Dict[str, Any]]:
        """Get todo lists for a project"""
        todoset = self._get_todoset(project_id)
        if not todoset:
            return []
        
        params = {'status': status}
        return self._make_request('GET', f'/buckets/{project_id}/todosets/{todoset["id"]}/todolists', params)
    
    def get_todos(self, project_id: int, todolist_id: int) -> List[Dict[str, Any]]:
        """Get todos in a todo list"""
        return self._make_request('GET', f'/buckets/{project_id}/todolists/{todolist_id}/todos')
    
    def get_todo(self, project_id: int, todo_id: int) -> Dict[str, Any]:
        """Get detailed todo information"""
        return self._make_request('GET', f'/buckets/{project_id}/todos/{todo_id}')
    
    def get_messages(self, project_id: int) -> List[Dict[str, Any]]:
        """Get messages (posts) in a project"""
        message_board = self._get_message_board(project_id)
        if not message_board:
            return []
        
        return self._make_request('GET', f'/buckets/{project_id}/message_boards/{message_board["id"]}/messages')
    
    def get_message(self, project_id: int, message_id: int) -> Dict[str, Any]:
        """Get detailed message information"""
        return self._make_request('GET', f'/buckets/{project_id}/messages/{message_id}')
    
    def get_documents(self, project_id: int) -> List[Dict[str, Any]]:
        """Get documents in a project"""
        vault = self._get_vault(project_id)
        if not vault:
            return []
        
        return self._make_request('GET', f'/buckets/{project_id}/vaults/{vault["id"]}/documents')
    
    def get_uploads(self, project_id: int) -> List[Dict[str, Any]]:
        """Get uploads (files) in a project"""
        vault = self._get_vault(project_id)
        if not vault:
            return []
        
        return self._make_request('GET', f'/buckets/{project_id}/vaults/{vault["id"]}/uploads')
    
    def get_campfires(self, project_id: int) -> List[Dict[str, Any]]:
        """Get campfire chats in a project"""
        chat = self._get_chat(project_id)
        if not chat:
            return []
        
        return self._make_request('GET', f'/buckets/{project_id}/chats/{chat["id"]}/lines')
    
    def get_schedule_entries(self, project_id: int) -> List[Dict[str, Any]]:
        """Get schedule entries in a project"""
        schedule = self._get_schedule(project_id)
        if not schedule:
            return []
        
        return self._make_request('GET', f'/buckets/{project_id}/schedules/{schedule["id"]}/entries')
    
    def get_questionnaires(self, project_id: int) -> List[Dict[str, Any]]:
        """Get questionnaires (check-in questions) in a project"""
        questionnaire = self._get_questionnaire(project_id)
        if not questionnaire:
            return []
        
        return self._make_request('GET', f'/buckets/{project_id}/questionnaires/{questionnaire["id"]}/questions')
    
    def get_comments(self, project_id: int, recording_id: int) -> List[Dict[str, Any]]:
        """Get comments on any recording (todo, message, etc.)"""
        return self._make_request('GET', f'/buckets/{project_id}/recordings/{recording_id}/comments')
    
    def get_events(self, project_id: int = None, since: datetime = None) -> List[Dict[str, Any]]:
        """Get events (activity feed)"""
        params = {}
        
        if since:
            params['since'] = since.isoformat()
        
        if project_id:
            endpoint = f'/buckets/{project_id}/recordings/events'
        else:
            endpoint = '/events'
        
        return self._make_request('GET', endpoint, params)
    
    # ============= HELPER METHODS FOR TOOLS =============
    
    def _get_tool(self, project_id: int, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool from project dock"""
        tools = self.get_project_tools(project_id)
        for tool in tools:
            if tool['name'].lower() == tool_name.lower():
                return tool
        return None
    
    def _get_todoset(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get todoset tool for project"""
        return self._get_tool(project_id, 'todoset')
    
    def _get_message_board(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get message board tool for project"""
        return self._get_tool(project_id, 'message_board')
    
    def _get_vault(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get vault (docs & files) tool for project"""
        return self._get_tool(project_id, 'vault')
    
    def _get_chat(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get campfire chat tool for project"""
        return self._get_tool(project_id, 'chat')
    
    def _get_schedule(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get schedule tool for project"""
        return self._get_tool(project_id, 'schedule')
    
    def _get_questionnaire(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get questionnaire tool for project"""
        return self._get_tool(project_id, 'questionnaire')
    
    # ============= BATCH OPERATIONS =============
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Basecamp data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'authorization': self.get_authorization(),
            'people': [],
            'projects': [],
            'total_projects': 0,
            'total_todos': 0,
            'total_messages': 0,
            'total_documents': 0
        }
        
        # Get people
        self.logger.info("Fetching people...")
        data['people'] = self.get_people()
        
        # Get projects
        self.logger.info("Fetching projects...")
        projects = self.get_projects(status='active')
        
        for project in projects:
            self.logger.info(f"Processing project: {project['name']}")
            
            # Get full project details
            project_data = self.get_project(project['id'])
            
            # Get todo lists
            project_data['todo_lists'] = []
            todo_lists = self.get_todo_lists(project['id'])
            
            for todolist in todo_lists:
                self.logger.info(f"  Processing todo list: {todolist['title']}")
                
                todolist_data = todolist.copy()
                
                # Get todos
                todos = self.get_todos(project['id'], todolist['id'])
                todolist_data['todos'] = todos
                data['total_todos'] += len(todos)
                
                # Get comments for each todo
                for todo in todos:
                    todo['comments'] = self.get_comments(project['id'], todo['id'])
                
                project_data['todo_lists'].append(todolist_data)
            
            # Get messages
            self.logger.info(f"  Fetching messages...")
            messages = self.get_messages(project['id'])
            project_data['messages'] = messages
            data['total_messages'] += len(messages)
            
            # Get comments for each message
            for message in messages:
                message['comments'] = self.get_comments(project['id'], message['id'])
            
            # Get documents
            self.logger.info(f"  Fetching documents...")
            documents = self.get_documents(project['id'])
            project_data['documents'] = documents
            data['total_documents'] += len(documents)
            
            # Get uploads
            self.logger.info(f"  Fetching uploads...")
            project_data['uploads'] = self.get_uploads(project['id'])
            
            # Get schedule entries
            self.logger.info(f"  Fetching schedule...")
            project_data['schedule_entries'] = self.get_schedule_entries(project['id'])
            
            # Get questionnaires
            self.logger.info(f"  Fetching questionnaires...")
            project_data['questionnaires'] = self.get_questionnaires(project['id'])
            
            # Get recent events
            self.logger.info(f"  Fetching events...")
            project_data['events'] = self.get_events(project_id=project['id'])
            
            data['projects'].append(project_data)
            data['total_projects'] += 1
            
            # Rate limit pause between projects
            time.sleep(1)
        
        self.logger.info(f"Export complete: {data['total_projects']} projects, {data['total_todos']} todos")
        
        return data
    
    # ============= PARADIGM SHIFT HELPERS =============
    
    def analyze_project_structure(self, project_id: int) -> Dict[str, Any]:
        """
        Analyze project structure and tools usage
        Basecamp is project-centric with multiple tools
        """
        project = self.get_project(project_id)
        tools = self.get_project_tools(project_id)
        
        analysis = {
            'project_name': project['name'],
            'tools_enabled': len(tools),
            'has_todos': False,
            'has_messages': False,
            'has_documents': False,
            'has_schedule': False,
            'has_chat': False,
            'complexity': 'simple'
        }
        
        # Check which tools are enabled
        for tool in tools:
            tool_name = tool['name'].lower()
            if 'todo' in tool_name:
                analysis['has_todos'] = True
            elif 'message' in tool_name:
                analysis['has_messages'] = True
            elif 'vault' in tool_name or 'doc' in tool_name:
                analysis['has_documents'] = True
            elif 'schedule' in tool_name:
                analysis['has_schedule'] = True
            elif 'chat' in tool_name or 'campfire' in tool_name:
                analysis['has_chat'] = True
        
        # Count todo lists
        if analysis['has_todos']:
            todo_lists = self.get_todo_lists(project_id)
            analysis['todo_list_count'] = len(todo_lists)
            
            # Count total todos
            total_todos = 0
            for todolist in todo_lists[:5]:  # Sample first 5
                todos = self.get_todos(project_id, todolist['id'])
                total_todos += len(todos)
            
            analysis['estimated_todos'] = total_todos * (len(todo_lists) / min(5, len(todo_lists)))
        
        # Determine complexity
        if analysis['tools_enabled'] <= 2:
            analysis['complexity'] = 'simple'
        elif analysis['tools_enabled'] <= 4:
            analysis['complexity'] = 'moderate'
        else:
            analysis['complexity'] = 'complex'
        
        # Recommend transformation strategy
        if analysis['has_todos'] and not analysis['has_messages']:
            analysis['recommended_strategy'] = 'todos_to_workflow'
        elif analysis['has_messages'] and not analysis['has_todos']:
            analysis['recommended_strategy'] = 'messages_to_comments'
        else:
            analysis['recommended_strategy'] = 'multi_tool_to_comprehensive'
        
        return analysis
    
    # ============= CREATE OPERATIONS =============
    
    def create_project(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new project"""
        data = {
            'name': name
        }
        
        if description:
            data['description'] = description
        
        return self._make_request('POST', '/projects', data=data)
    
    def create_todo_list(self, project_id: int, name: str, 
                        description: str = None) -> Dict[str, Any]:
        """Create a new todo list"""
        todoset = self._get_todoset(project_id)
        if not todoset:
            raise ValueError(f"Todoset not enabled for project {project_id}")
        
        data = {
            'name': name
        }
        
        if description:
            data['description'] = description
        
        return self._make_request('POST', f'/buckets/{project_id}/todosets/{todoset["id"]}/todolists', data=data)
    
    def create_todo(self, project_id: int, todolist_id: int, 
                   content: str, **kwargs) -> Dict[str, Any]:
        """Create a new todo"""
        data = {
            'content': content,
            **kwargs
        }
        
        return self._make_request('POST', f'/buckets/{project_id}/todolists/{todolist_id}/todos', data=data)
    
    def create_message(self, project_id: int, subject: str, 
                      content: str, **kwargs) -> Dict[str, Any]:
        """Create a new message"""
        message_board = self._get_message_board(project_id)
        if not message_board:
            raise ValueError(f"Message board not enabled for project {project_id}")
        
        data = {
            'subject': subject,
            'content': content,
            **kwargs
        }
        
        return self._make_request('POST', f'/buckets/{project_id}/message_boards/{message_board["id"]}/messages', data=data)
    
    def create_comment(self, project_id: int, recording_id: int, 
                      content: str) -> Dict[str, Any]:
        """Create a comment on any recording"""
        data = {
            'content': content
        }
        
        return self._make_request('POST', f'/buckets/{project_id}/recordings/{recording_id}/comments', data=data)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = BasecampProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Basecamp")
        
        # Get authorization
        auth = client.get_authorization()
        print(f"Account: {auth['accounts'][0]['name']}")
        print(f"User: {auth['identity']['email_address']}")
        
        # Get people
        people = client.get_people()
        print(f"\nFound {len(people)} people")
        
        # Get projects
        projects = client.get_projects()
        print(f"Found {len(projects)} active projects")
        
        if projects:
            project = projects[0]
            print(f"\nProject: {project['name']}")
            
            # Analyze project structure
            analysis = client.analyze_project_structure(project['id'])
            print(f"\nProject analysis:")
            print(f"  - Tools enabled: {analysis['tools_enabled']}")
            print(f"  - Has todos: {analysis['has_todos']}")
            print(f"  - Has messages: {analysis['has_messages']}")
            print(f"  - Complexity: {analysis['complexity']}")
            print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
            
            # Get todo lists
            if analysis['has_todos']:
                todo_lists = client.get_todo_lists(project['id'])
                print(f"\nTodo lists: {len(todo_lists)}")
                
                if todo_lists:
                    todolist = todo_lists[0]
                    print(f"  - {todolist['title']}")
                    
                    # Get todos
                    todos = client.get_todos(project['id'], todolist['id'])
                    print(f"    Todos: {len(todos)}")
    
    print("\n✅ Production Basecamp client ready!")