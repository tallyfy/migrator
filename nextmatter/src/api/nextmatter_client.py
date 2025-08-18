"""
NextMatter API Client
Handles all interactions with NextMatter API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class NextMatterClient:
    """Client for NextMatter API operations"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize NextMatter API client
        
        Args:
            api_key: NextMatter API key
            base_url: Base URL for NextMatter API
        """
        self.api_key = api_key or os.getenv('NEXTMATTER_API_KEY')
        self.base_url = base_url or os.getenv('NEXTMATTER_BASE_URL', 'https://core.nextmatter.com/api')
        
        if not self.api_key:
            raise ValueError("NextMatter API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Api-Key {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info(f"NextMatter client initialized for {self.base_url}")
    
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
        """Get all workflows (processes)"""
        logger.info("Fetching NextMatter workflows...")
        workflows = []
        next_url = 'processes/'
        
        while next_url:
            result = self._make_request('GET', next_url.replace(self.base_url + '/', ''))
            batch = result.get('results', [])
            workflows.extend(batch)
            next_url = result.get('next')
            
        logger.info(f"Found {len(workflows)} workflows")
        return workflows
    
    def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed workflow information"""
        logger.debug(f"Fetching workflow {workflow_id}")
        return self._make_request('GET', f'workflows/{workflow_id}')
    
    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get workflow steps"""
        logger.debug(f"Fetching steps for workflow {workflow_id}")
        result = self._make_request('GET', f'workflows/{workflow_id}/steps')
        return result.get('steps', [])
    
    def get_instances(self) -> List[Dict[str, Any]]:
        """Get all instances (workflow runs)"""
        logger.info("Fetching instances...")
        instances = []
        next_url = 'instances/'
        
        while next_url:
            result = self._make_request('GET', next_url.replace(self.base_url + '/', ''))
            batch = result.get('results', [])
            instances.extend(batch)
            next_url = result.get('next')
            
        logger.info(f"Found {len(instances)} instances")
        return instances
    
    def get_process_details(self, process_id: str) -> Dict[str, Any]:
        """Get process details"""
        logger.debug(f"Fetching process {process_id}")
        return self._make_request('GET', f'processes/{process_id}')
    
    def get_process_tasks(self, process_id: str) -> List[Dict[str, Any]]:
        """Get tasks in a process"""
        logger.debug(f"Fetching tasks for process {process_id}")
        result = self._make_request('GET', f'processes/{process_id}/tasks')
        return result.get('tasks', [])
    
    def get_forms(self) -> List[Dict[str, Any]]:
        """Get all forms"""
        logger.info("Fetching forms...")
        result = self._make_request('GET', 'forms')
        forms = result.get('forms', [])
        logger.info(f"Found {len(forms)} forms")
        return forms
    
    def get_form_fields(self, form_id: str) -> List[Dict[str, Any]]:
        """Get form fields"""
        logger.debug(f"Fetching fields for form {form_id}")
        result = self._make_request('GET', f'forms/{form_id}/fields')
        return result.get('fields', [])
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        logger.info("Fetching users...")
        users = []
        page = 1
        
        while True:
            result = self._make_request('GET', 'users', params={'page': page, 'per_page': 100})
            batch = result.get('users', [])
            users.extend(batch)
            
            if len(batch) < 100:
                break
            page += 1
        
        logger.info(f"Found {len(users)} users")
        return users
    
    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        logger.debug(f"Fetching user {user_id}")
        return self._make_request('GET', f'users/{user_id}')
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams"""
        logger.info("Fetching teams...")
        result = self._make_request('GET', 'teams')
        teams = result.get('teams', [])
        logger.info(f"Found {len(teams)} teams")
        return teams
    
    def get_comments(self, process_id: str) -> List[Dict[str, Any]]:
        """Get comments for a process"""
        logger.debug(f"Fetching comments for process {process_id}")
        result = self._make_request('GET', f'processes/{process_id}/comments')
        return result.get('comments', [])
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            logger.info("Testing NextMatter connection...")
            self._make_request('GET', 'processes/?limit=1')
            logger.info("✅ NextMatter connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ NextMatter connection failed: {e}")
            return False
    
    def create_instance(self, process_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new instance of a workflow"""
        logger.info(f"Creating instance for process {process_id}")
        payload = {
            'process': process_id,
            'name': data.get('name', ''),
            'deadline': data.get('deadline'),
            'priority': data.get('priority', 'M'),  # V=Very High, H=High, M=Medium, L=Low, N=None
            'tags': data.get('tags', []),
            'step_assignments': data.get('step_assignments', [])
        }
        return self._make_request('POST', 'instances/', json=payload)