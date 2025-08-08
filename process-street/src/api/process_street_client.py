"""
Process Street API Client
Handles all interactions with Process Street API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class ProcessStreetClient:
    """Client for Process Street API operations"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize Process Street API client
        
        Args:
            api_key: Process Street API key
            base_url: Base URL for Process Street API
        """
        self.api_key = api_key or os.getenv('PROCESS_STREET_API_KEY')
        self.base_url = base_url or os.getenv('PROCESS_STREET_BASE_URL', 'https://api.process.st/api/v1')
        
        if not self.api_key:
            raise ValueError("Process Street API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info(f"Process Street client initialized for {self.base_url}")
    
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
        """Get all workflows (templates)"""
        logger.info("Fetching Process Street workflows...")
        workflows = []
        page = 1
        
        while True:
            result = self._make_request('GET', 'workflows', params={'page': page, 'limit': 100})
            batch = result.get('workflows', result.get('data', []))
            workflows.extend(batch)
            
            if len(batch) < 100:
                break
            page += 1
        
        logger.info(f"Found {len(workflows)} workflows")
        return workflows
    
    def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow details"""
        logger.debug(f"Fetching workflow {workflow_id}")
        return self._make_request('GET', f'workflows/{workflow_id}')
    
    def get_workflow_runs(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get workflow runs (instances)"""
        logger.debug(f"Fetching runs for workflow {workflow_id}")
        result = self._make_request('GET', f'workflows/{workflow_id}/workflow-runs')
        return result.get('workflow-runs', result.get('data', []))
    
    def get_run_details(self, run_id: str) -> Dict[str, Any]:
        """Get workflow run details"""
        logger.debug(f"Fetching run {run_id}")
        return self._make_request('GET', f'workflow-runs/{run_id}')
    
    def get_tasks(self, run_id: str) -> List[Dict[str, Any]]:
        """Get tasks in a workflow run"""
        logger.debug(f"Fetching tasks for run {run_id}")
        result = self._make_request('GET', f'workflow-runs/{run_id}/tasks')
        return result.get('tasks', result.get('data', []))
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        logger.info("Fetching users...")
        users = []
        page = 1
        
        while True:
            result = self._make_request('GET', 'users', params={'page': page, 'limit': 100})
            batch = result.get('users', result.get('data', []))
            users.extend(batch)
            
            if len(batch) < 100:
                break
            page += 1
        
        logger.info(f"Found {len(users)} users")
        return users
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            logger.info("Testing Process Street connection...")
            self._make_request('GET', 'workflows', params={'limit': 1})
            logger.info("✅ Process Street connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Process Street connection failed: {e}")
            return False
