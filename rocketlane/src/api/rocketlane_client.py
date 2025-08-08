"""
RocketLane API Client
Handles all interactions with RocketLane's REST API
"""

import requests
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RocketLaneClient:
    """Client for RocketLane API interactions"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.rocketlane.com/api/1.0"):
        """Initialize RocketLane client with API key"""
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Configure retries with exponential backoff
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set authentication headers
        session.headers.update({
            'api-key': self.api_key,
            'Content-Type': 'application/json',
            
            'Accept': 'application/json'
        })
        
        return session
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and credentials"""
        try:
            response = self.session.get(f"{self.base_url}/users/me")
            response.raise_for_status()
            logger.info("Successfully connected to RocketLane API")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to RocketLane API: {e}")
            raise
    
    def get_customers(self, limit: int = 100, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Fetch all customers with pagination"""
        customers = []
        page_token = None
        
        while True:
            params = {
                'pageSize': min(limit, 100),
                'includeArchived': include_archived
            }
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/customers", params=params)
            response.raise_for_status()
            data = response.json()
            
            customers.extend(data.get('results', []))
            
            # Check for more pages
            page_token = data.get('pageToken')
            if not page_token or len(customers) >= limit:
                break
            
            # Rate limit respect
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(customers)} customers")
        return customers[:limit]
    
    def get_projects(self, limit: int = 100, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Fetch all projects with pagination"""
        projects = []
        page_token = None
        
        while True:
            params = {
                'pageSize': min(limit, 100),
                'includeArchived': include_archived
            }
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/projects", params=params)
            response.raise_for_status()
            data = response.json()
            
            projects.extend(data.get('results', []))
            
            page_token = data.get('pageToken')
            if not page_token or len(projects) >= limit:
                break
            
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(projects)} projects")
        return projects[:limit]
    
    def get_project_templates(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all project templates"""
        templates = []
        page_token = None
        
        while True:
            params = {'pageSize': min(limit, 100)}
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/projectTemplates", params=params)
            response.raise_for_status()
            data = response.json()
            
            templates.extend(data.get('results', []))
            
            page_token = data.get('pageToken')
            if not page_token or len(templates) >= limit:
                break
            
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(templates)} project templates")
        return templates[:limit]
    
    def get_tasks(self, project_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch tasks, optionally filtered by project"""
        tasks = []
        page_token = None
        
        while True:
            params = {'pageSize': min(limit, 100)}
            if project_id:
                params['projectId'] = project_id
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/tasks", params=params)
            response.raise_for_status()
            data = response.json()
            
            tasks.extend(data.get('results', []))
            
            page_token = data.get('pageToken')
            if not page_token or len(tasks) >= limit:
                break
            
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(tasks)} tasks")
        return tasks[:limit]
    
    def get_forms(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all forms"""
        forms = []
        page_token = None
        
        while True:
            params = {'pageSize': min(limit, 100)}
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/forms", params=params)
            response.raise_for_status()
            data = response.json()
            
            forms.extend(data.get('results', []))
            
            page_token = data.get('pageToken')
            if not page_token or len(forms) >= limit:
                break
            
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(forms)} forms")
        return forms[:limit]
    
    def get_form_responses(self, form_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch form responses for a specific form"""
        responses = []
        page_token = None
        
        while True:
            params = {'pageSize': min(limit, 100)}
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/forms/{form_id}/responses", params=params)
            response.raise_for_status()
            data = response.json()
            
            responses.extend(data.get('results', []))
            
            page_token = data.get('pageToken')
            if not page_token or len(responses) >= limit:
                break
            
            time.sleep(0.5)
        
        return responses[:limit]
    
    def get_users(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch all users"""
        users = []
        page_token = None
        
        while True:
            params = {'pageSize': min(limit, 100)}
            if page_token:
                params['pageToken'] = page_token
            
            response = self.session.get(f"{self.base_url}/users", params=params)
            response.raise_for_status()
            data = response.json()
            
            users.extend(data.get('results', []))
            
            page_token = data.get('pageToken')
            if not page_token or len(users) >= limit:
                break
            
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(users)} users")
        return users[:limit]
    
    def get_custom_fields(self, entity_type: str = 'project') -> List[Dict[str, Any]]:
        """Fetch custom field definitions for an entity type"""
        response = self.session.get(f"{self.base_url}/customFields/{entity_type}")
        response.raise_for_status()
        return response.json().get('results', [])
    
    def get_time_entries(self, project_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch time entries, optionally filtered by project"""
        entries = []
        page_token = None
        
        while True:
            params = {'pageSize': min(limit, 100)}
            if project_id:
                params['projectId'] = project_id
            if page_token:
                params['pageToken'] = page_token
            
            try:
                response = self.session.get(f"{self.base_url}/timeEntries", params=params)
                response.raise_for_status()
                data = response.json()
                
                entries.extend(data.get('results', []))
                
                page_token = data.get('pageToken')
                if not page_token or len(entries) >= limit:
                    break
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.warning("Time tracking endpoint not available")
                    return []
                raise
            
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(entries)} time entries")
        return entries[:limit]
    
    def get_project_details(self, project_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific project"""
        response = self.session.get(f"{self.base_url}/projects/{project_id}")
        response.raise_for_status()
        return response.json()
    
    def get_documents(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch documents/spaces for a project"""
        try:
            response = self.session.get(f"{self.base_url}/projects/{project_id}/documents")
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Documents endpoint not available for project {project_id}")
                return []
            raise
    
    def get_resource_allocations(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch resource allocations"""
        params = {}
        if project_id:
            params['projectId'] = project_id
        
        try:
            response = self.session.get(f"{self.base_url}/resourceAllocations", params=params)
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning("Resource allocation endpoint not available")
                return []
            raise
    
    def search_with_filter(self, resource: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search resources with advanced filtering"""
        # RocketLane's advanced filter format
        filter_params = []
        for key, value in filters.items():
            filter_params.append(f"{resource}.field.{key}.value:{value}")
        
        params = {
            'filter': ' AND '.join(filter_params),
            'pageSize': 100
        }
        
        response = self.session.get(f"{self.base_url}/{resource}", params=params)
        response.raise_for_status()
        return response.json().get('results', [])