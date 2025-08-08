"""
Basecamp API Client
Handles all interactions with Basecamp API (v3)
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class BasecampClient:
    """Client for Basecamp API operations"""
    
    def __init__(self, account_id: str = None, access_token: str = None, client_id: str = None):
        """
        Initialize Basecamp API client
        
        Args:
            account_id: Basecamp account ID
            access_token: OAuth access token
            client_id: Client ID for User-Agent
        """
        self.account_id = account_id or os.getenv('BASECAMP_ACCOUNT_ID')
        self.access_token = access_token or os.getenv('BASECAMP_ACCESS_TOKEN')
        self.client_id = client_id or os.getenv('BASECAMP_CLIENT_ID', 'Tallyfy Migration Tool')
        
        if not self.account_id or not self.access_token:
            raise ValueError("Basecamp account ID and access token are required")
        
        self.base_url = f'https://3.basecampapi.com/{self.account_id}'
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': f'{self.client_id} (migration@tallyfy.com)',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"Basecamp client initialized for account {self.account_id}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with retries"""
        url = f"{self.base_url}/{endpoint}.json"
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 429:  # Rate limited
                    wait_time = 60
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json() if response.content else None
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects"""
        logger.info("Fetching Basecamp projects...")
        projects = self._make_request('GET', 'projects')
        logger.info(f"Found {len(projects)} projects")
        return projects
    
    def get_project_details(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        logger.debug(f"Fetching project {project_id}")
        return self._make_request('GET', f'projects/{project_id}')
    
    def get_project_tools(self, project_id: str) -> List[Dict[str, Any]]:
        """Get tools enabled for a project"""
        logger.debug(f"Fetching tools for project {project_id}")
        project = self.get_project_details(project_id)
        return project.get('dock', [])
    
    def get_todosets(self, project_id: str) -> Dict[str, Any]:
        """Get todoset for a project"""
        logger.debug(f"Fetching todosets for project {project_id}")
        tools = self.get_project_tools(project_id)
        
        for tool in tools:
            if tool.get('name') == 'todoset':
                return self._make_request('GET', f'buckets/{project_id}/todosets/{tool["id"]}')
        
        return {}
    
    def get_todolists(self, project_id: str, todoset_id: str) -> List[Dict[str, Any]]:
        """Get todo lists in a todoset"""
        logger.debug(f"Fetching todo lists for project {project_id}")
        result = self._make_request('GET', f'buckets/{project_id}/todosets/{todoset_id}/todolists')
        return result if isinstance(result, list) else []
    
    def get_todos(self, project_id: str, todolist_id: str) -> List[Dict[str, Any]]:
        """Get todos in a list"""
        logger.debug(f"Fetching todos for list {todolist_id}")
        result = self._make_request('GET', f'buckets/{project_id}/todolists/{todolist_id}/todos')
        return result if isinstance(result, list) else []
    
    def get_todo_details(self, project_id: str, todo_id: str) -> Dict[str, Any]:
        """Get todo details"""
        logger.debug(f"Fetching todo {todo_id}")
        return self._make_request('GET', f'buckets/{project_id}/todos/{todo_id}')
    
    def get_people(self) -> List[Dict[str, Any]]:
        """Get all people in the account"""
        logger.info("Fetching people...")
        people = self._make_request('GET', 'people')
        logger.info(f"Found {len(people)} people")
        return people
    
    def get_person_details(self, person_id: str) -> Dict[str, Any]:
        """Get person details"""
        logger.debug(f"Fetching person {person_id}")
        return self._make_request('GET', f'people/{person_id}')
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get project templates"""
        logger.info("Fetching templates...")
        templates = self._make_request('GET', 'templates')
        logger.info(f"Found {len(templates)} templates")
        return templates
    
    def get_template_details(self, template_id: str) -> Dict[str, Any]:
        """Get template details"""
        logger.debug(f"Fetching template {template_id}")
        return self._make_request('GET', f'templates/{template_id}')
    
    def get_comments(self, project_id: str, recording_id: str) -> List[Dict[str, Any]]:
        """Get comments for a recording (todo, message, etc)"""
        logger.debug(f"Fetching comments for recording {recording_id}")
        result = self._make_request('GET', f'buckets/{project_id}/recordings/{recording_id}/comments')
        return result if isinstance(result, list) else []
    
    def get_attachments(self, project_id: str) -> List[Dict[str, Any]]:
        """Get attachments/uploads for a project"""
        logger.debug(f"Fetching attachments for project {project_id}")
        tools = self.get_project_tools(project_id)
        
        for tool in tools:
            if tool.get('name') == 'vault':
                result = self._make_request('GET', f'buckets/{project_id}/vaults/{tool["id"]}/uploads')
                return result if isinstance(result, list) else []
        
        return []
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            logger.info("Testing Basecamp connection...")
            self._make_request('GET', 'projects')
            logger.info("✅ Basecamp connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Basecamp connection failed: {e}")
            return False