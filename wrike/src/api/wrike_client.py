"""
Wrike API Client
Handles all interactions with Wrike API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class WrikeClient:
    """Client for Wrike API operations"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize Wrike API client
        
        Args:
            api_key: Wrike API key
            base_url: Base URL for Wrike API
        """
        self.api_key = api_key or os.getenv('WRIKE_API_KEY')
        self.base_url = base_url or os.getenv('WRIKE_BASE_URL', 'https://www.wrike.com/api/v4')
        
        if not self.api_key:
            raise ValueError("Wrike API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"Wrike client initialized for {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with retries"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 429:  # Rate limited
                    wait_time = int(response.headers.get('Retry-After', 60))
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
    
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows"""
        logger.info("Fetching Wrike workflows...")
        result = self._make_request('GET', 'workflows')
        workflows = result.get('data', [])
        logger.info(f"Found {len(workflows)} workflows")
        return workflows
    
    def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed workflow information"""
        logger.debug(f"Fetching workflow {workflow_id}")
        result = self._make_request('GET', f'workflows/{workflow_id}')
        return result.get('data', [{}])[0]
    
    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """Get all custom fields"""
        logger.info("Fetching custom fields...")
        result = self._make_request('GET', 'customfields')
        fields = result.get('data', [])
        logger.info(f"Found {len(fields)} custom fields")
        return fields
    
    def get_folders(self, space_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get folders (projects)"""
        logger.info("Fetching folders...")
        endpoint = f'spaces/{space_id}/folders' if space_id else 'folders'
        result = self._make_request('GET', endpoint)
        folders = result.get('data', [])
        logger.info(f"Found {len(folders)} folders")
        return folders
    
    def get_folder_tasks(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get tasks in a folder"""
        logger.debug(f"Fetching tasks for folder {folder_id}")
        result = self._make_request('GET', f'folders/{folder_id}/tasks')
        return result.get('data', [])
    
    def get_task_details(self, task_id: str) -> Dict[str, Any]:
        """Get detailed task information"""
        logger.debug(f"Fetching task {task_id}")
        result = self._make_request('GET', f'tasks/{task_id}')
        return result.get('data', [{}])[0]
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        logger.info("Fetching users...")
        result = self._make_request('GET', 'contacts')
        users = result.get('data', [])
        logger.info(f"Found {len(users)} users")
        return users
    
    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        logger.debug(f"Fetching user {user_id}")
        result = self._make_request('GET', f'contacts/{user_id}')
        return result.get('data', [{}])[0]
    
    def get_spaces(self) -> List[Dict[str, Any]]:
        """Get all spaces"""
        logger.info("Fetching spaces...")
        result = self._make_request('GET', 'spaces')
        spaces = result.get('data', [])
        logger.info(f"Found {len(spaces)} spaces")
        return spaces
    
    def get_task_comments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get comments for a task"""
        logger.debug(f"Fetching comments for task {task_id}")
        result = self._make_request('GET', f'tasks/{task_id}/comments')
        return result.get('data', [])
    
    def get_attachments(self, task_id: str) -> List[Dict[str, Any]]:
        """Get attachments for a task"""
        logger.debug(f"Fetching attachments for task {task_id}")
        result = self._make_request('GET', f'tasks/{task_id}/attachments')
        return result.get('data', [])
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            logger.info("Testing Wrike connection...")
            self._make_request('GET', 'account')
            logger.info("✅ Wrike connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Wrike connection failed: {e}")
            return False