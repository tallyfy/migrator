"""Kissflow API client implementation."""

import requests
import time
import logging
import json
from typing import Dict, List, Optional, Any, Generator
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class KissflowClient:
    """Client for interacting with Kissflow API."""
    
    def __init__(self, subdomain: str, account_id: str, 
                 access_key_id: str, access_key_secret: str):
        """Initialize Kissflow client.
        
        Args:
            subdomain: Your Kissflow subdomain (e.g., 'demo' from demo.kissflow.com)
            account_id: Unique alphanumeric account identifier
            access_key_id: Access Key ID from API Authentication settings
            access_key_secret: Access Key Secret for authentication
        """
        self.subdomain = subdomain
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.base_url = f"https://{subdomain}.kissflow.com"
        self.session = self._create_session()
        self.api_version = "2"  # Current API version
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retries with exponential backoff
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set authentication headers
        session.headers.update({
            'X-Access-Key-Id': self.access_key_id,
            'X-Access-Key-Secret': self.access_key_secret,
            'Content-Type': 'application/json',
            
            'Accept': 'application/json'
        })
        
        # Set timeout for all requests (10 seconds as per Kissflow docs)
        session.timeout = 10
        
        return session
    
    def _make_request(self, method: str, endpoint: str, 
                     data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Kissflow API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON data
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=10
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                # Retry the request
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=10
                )
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and credentials.
        
        Returns:
            Account information if successful
        """
        try:
            # Try to get current user info
            endpoint = f"/user/{self.api_version}/{self.account_id}/me"
            result = self._make_request("GET", endpoint)
            logger.info(f"Successfully connected to Kissflow account: {self.account_id}")
            return result
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    def get_users(self, page_size: int = 50) -> List[Dict[str, Any]]:
        """Get all users in the account.
        
        Args:
            page_size: Number of users per page
            
        Returns:
            List of user objects
        """
        users = []
        page_number = 1
        
        while True:
            endpoint = f"/user/{self.api_version}/{self.account_id}/list/p{page_number}/{page_size}"
            response = self._make_request("GET", endpoint)
            
            if not response or 'users' not in response:
                break
                
            page_users = response.get('users', [])
            if not page_users:
                break
                
            users.extend(page_users)
            
            # Check if there are more pages
            if len(page_users) < page_size:
                break
                
            page_number += 1
        
        logger.info(f"Found {len(users)} users")
        return users
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups in the account.
        
        Returns:
            List of group objects
        """
        endpoint = f"/group/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        groups = response.get('groups', [])
        logger.info(f"Found {len(groups)} groups")
        return groups
    
    def get_processes(self) -> List[Dict[str, Any]]:
        """Get all processes (workflow templates).
        
        Returns:
            List of process objects
        """
        endpoint = f"/process/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        processes = response.get('processes', [])
        logger.info(f"Found {len(processes)} processes")
        return processes
    
    def get_process_details(self, run_id: str) -> Dict[str, Any]:
        """Get detailed process information.
        
        Args:
            run_id: Process identifier
            
        Returns:
            Process object with full details
        """
        endpoint = f"/process/{self.api_version}/{self.account_id}/{run_id}"
        return self._make_request("GET", endpoint)
    
    def get_process_fields(self, run_id: str) -> List[Dict[str, Any]]:
        """Get form fields for a process.
        
        Args:
            run_id: Process identifier
            
        Returns:
            List of field definitions
        """
        endpoint = f"/process/{self.api_version}/{self.account_id}/{run_id}/fields"
        response = self._make_request("GET", endpoint)
        return response.get('fields', [])
    
    def get_process_workflow(self, run_id: str) -> Dict[str, Any]:
        """Get workflow definition for a process.
        
        Args:
            run_id: Process identifier
            
        Returns:
            Workflow structure with steps and routing
        """
        endpoint = f"/process/{self.api_version}/{self.account_id}/{run_id}/workflow"
        return self._make_request("GET", endpoint)
    
    def get_process_instances(self, run_id: str, status: str = "active",
                            page_size: int = 50) -> List[Dict[str, Any]]:
        """Get process instances (running processes).
        
        Args:
            run_id: Process identifier
            status: Instance status (active, completed, all)
            page_size: Items per page
            
        Returns:
            List of process instances
        """
        instances = []
        page_number = 1
        
        while True:
            endpoint = f"/process/{self.api_version}/{self.account_id}/{run_id}/instances/{status}/p{page_number}/{page_size}"
            response = self._make_request("GET", endpoint)
            
            if not response or 'instances' not in response:
                break
                
            page_instances = response.get('instances', [])
            if not page_instances:
                break
                
            instances.extend(page_instances)
            
            if len(page_instances) < page_size:
                break
                
            page_number += 1
        
        logger.info(f"Found {len(instances)} instances for process {run_id}")
        return instances
    
    def get_boards(self) -> List[Dict[str, Any]]:
        """Get all boards (Kanban project management).
        
        Returns:
            List of board objects
        """
        endpoint = f"/board/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        boards = response.get('boards', [])
        logger.info(f"Found {len(boards)} boards")
        return boards
    
    def get_board_details(self, board_id: str) -> Dict[str, Any]:
        """Get detailed board information.
        
        Args:
            board_id: Board identifier
            
        Returns:
            Board object with full details
        """
        endpoint = f"/board/{self.api_version}/{self.account_id}/{board_id}"
        return self._make_request("GET", endpoint)
    
    def get_board_items(self, board_id: str, status: str = "active",
                       page_size: int = 50) -> List[Dict[str, Any]]:
        """Get items in a board.
        
        Args:
            board_id: Board identifier
            status: Item status filter
            page_size: Items per page
            
        Returns:
            List of board items
        """
        items = []
        page_number = 1
        
        while True:
            endpoint = f"/board/{self.api_version}/{self.account_id}/{board_id}/items/{status}/p{page_number}/{page_size}"
            response = self._make_request("GET", endpoint)
            
            if not response or 'items' not in response:
                break
                
            page_items = response.get('items', [])
            if not page_items:
                break
                
            items.extend(page_items)
            
            if len(page_items) < page_size:
                break
                
            page_number += 1
        
        logger.info(f"Found {len(items)} items in board {board_id}")
        return items
    
    def get_apps(self) -> List[Dict[str, Any]]:
        """Get all apps (low-code applications).
        
        Returns:
            List of app objects
        """
        endpoint = f"/app/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        apps = response.get('apps', [])
        logger.info(f"Found {len(apps)} apps")
        return apps
    
    def get_app_details(self, app_id: str) -> Dict[str, Any]:
        """Get detailed app information.
        
        Args:
            app_id: App identifier
            
        Returns:
            App object with full details
        """
        endpoint = f"/app/{self.api_version}/{self.account_id}/{app_id}"
        return self._make_request("GET", endpoint)
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get all datasets (data tables).
        
        Returns:
            List of dataset objects
        """
        endpoint = f"/dataset/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        datasets = response.get('datasets', [])
        logger.info(f"Found {len(datasets)} datasets")
        return datasets
    
    def get_dataset_details(self, dataset_id: str) -> Dict[str, Any]:
        """Get detailed dataset information.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dataset object with schema
        """
        endpoint = f"/dataset/{self.api_version}/{self.account_id}/{dataset_id}"
        return self._make_request("GET", endpoint)
    
    def get_dataset_rows(self, dataset_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """Get rows from a dataset.
        
        Args:
            dataset_id: Dataset identifier
            page_size: Rows per page
            
        Returns:
            List of dataset rows
        """
        rows = []
        page_number = 1
        
        while True:
            endpoint = f"/dataset/{self.api_version}/{self.account_id}/{dataset_id}/rows/p{page_number}/{page_size}"
            response = self._make_request("GET", endpoint)
            
            if not response or 'rows' not in response:
                break
                
            page_rows = response.get('rows', [])
            if not page_rows:
                break
                
            rows.extend(page_rows)
            
            if len(page_rows) < page_size:
                break
                
            page_number += 1
        
        logger.info(f"Found {len(rows)} rows in dataset {dataset_id}")
        return rows
    
    def get_forms(self) -> List[Dict[str, Any]]:
        """Get all data forms.
        
        Returns:
            List of form objects
        """
        endpoint = f"/form/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        forms = response.get('forms', [])
        logger.info(f"Found {len(forms)} forms")
        return forms
    
    def get_form_details(self, form_id: str) -> Dict[str, Any]:
        """Get detailed form information.
        
        Args:
            form_id: Form identifier
            
        Returns:
            Form object with field definitions
        """
        endpoint = f"/form/{self.api_version}/{self.account_id}/{form_id}"
        return self._make_request("GET", endpoint)
    
    def get_reports(self) -> List[Dict[str, Any]]:
        """Get all reports.
        
        Returns:
            List of report objects
        """
        endpoint = f"/report/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        reports = response.get('reports', [])
        logger.info(f"Found {len(reports)} reports")
        return reports
    
    def get_integrations(self) -> List[Dict[str, Any]]:
        """Get configured integrations.
        
        Returns:
            List of integration configurations
        """
        endpoint = f"/integration/{self.api_version}/{self.account_id}/list"
        response = self._make_request("GET", endpoint)
        integrations = response.get('integrations', [])
        logger.info(f"Found {len(integrations)} integrations")
        return integrations
    
    def get_my_items(self, status: str = "active", page_size: int = 50) -> List[Dict[str, Any]]:
        """Get items assigned to current user.
        
        Args:
            status: Item status filter (active, completed, all)
            page_size: Items per page
            
        Returns:
            List of assigned items across all processes and boards
        """
        items = []
        page_number = 1
        
        while True:
            endpoint = f"/search/1/{self.account_id}/global/myitems/{status}/p{page_number}/{page_size}"
            response = self._make_request("GET", endpoint)
            
            if not response or 'items' not in response:
                break
                
            page_items = response.get('items', [])
            if not page_items:
                break
                
            items.extend(page_items)
            
            if len(page_items) < page_size:
                break
                
            page_number += 1
        
        logger.info(f"Found {len(items)} items assigned to current user")
        return items
    
    def get_attachment(self, run_id: str, instance_id: str, 
                      activity_id: str, field_id: str, 
                      attachment_id: str) -> Dict[str, Any]:
        """Get attachment details.
        
        Args:
            run_id: Process identifier
            instance_id: Instance identifier
            activity_id: Activity instance identifier
            field_id: Field identifier
            attachment_id: Attachment identifier
            
        Returns:
            Attachment metadata and download URL
        """
        endpoint = f"/process/{self.api_version}/{self.account_id}/{run_id}/{instance_id}/{activity_id}/{field_id}/attachment/{attachment_id}"
        return self._make_request("GET", endpoint)
    
    def search_global(self, query: str, page_size: int = 50) -> List[Dict[str, Any]]:
        """Global search across all objects.
        
        Args:
            query: Search query
            page_size: Results per page
            
        Returns:
            List of search results
        """
        results = []
        page_number = 1
        
        while True:
            endpoint = f"/search/1/{self.account_id}/global/p{page_number}/{page_size}"
            params = {"q": query}
            response = self._make_request("GET", endpoint, params=params)
            
            if not response or 'results' not in response:
                break
                
            page_results = response.get('results', [])
            if not page_results:
                break
                
            results.extend(page_results)
            
            if len(page_results) < page_size:
                break
                
            page_number += 1
        
        logger.info(f"Found {len(results)} results for query: {query}")
        return results