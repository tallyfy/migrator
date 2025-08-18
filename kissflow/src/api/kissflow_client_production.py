#!/usr/bin/env python3
"""
Production-Grade Kissflow API Client
Implements actual Kissflow API v1 with proper authentication, rate limiting, and error handling
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


class KissflowRateLimitError(Exception):
    """Kissflow rate limit exceeded"""
    pass


class KissflowAuthError(Exception):
    """Kissflow authentication failed"""
    pass


class KissflowModuleType(str, Enum):
    """Kissflow module types"""
    PROCESS = "process"
    CASE = "case"
    DATASET = "dataset"
    BOARD = "board"
    METRIC = "metric"
    FORM = "form"


class KissflowFieldType(str, Enum):
    """Kissflow field types"""
    TEXT = "Text"
    MULTILINE = "Multiline"
    NUMBER = "Number"
    CURRENCY = "Currency"
    DATE = "Date"
    DATETIME = "DateTime"
    TIME = "Time"
    YES_NO = "Yes_No"
    DROPDOWN = "Dropdown"
    CHECKBOX = "Checkbox"
    RADIO = "Radio"
    USER = "User"
    ATTACHMENT = "Attachment"
    RICH_TEXT = "Rich_Text"
    EMAIL = "Email"
    PHONE = "Phone"
    URL = "URL"
    RATING = "Rating"
    SLIDER = "Slider"
    SIGNATURE = "Signature"
    IMAGE = "Image"
    FORMULA = "Formula"
    LOOKUP = "Lookup"
    REMOTE_LOOKUP = "Remote_Lookup"


class KissflowProductionClient:
    """
    Production Kissflow API client with actual endpoints
    Implements Kissflow API v1
    """
    
    BASE_URL = "https://api.kissflow.com/api/v1"
    
    # Kissflow rate limits
    RATE_LIMITS = {
        'requests_per_minute': 120,
        'requests_per_second': 3,
        'burst_limit': 10
    }
    
    def __init__(self):
        """Initialize Kissflow client with actual authentication"""
        self.api_key = os.getenv('KISSFLOW_API_KEY')
        self.account_id = os.getenv('KISSFLOW_ACCOUNT_ID')
        
        if not self.api_key or not self.account_id:
            raise KissflowAuthError("KISSFLOW_API_KEY and KISSFLOW_ACCOUNT_ID required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'api-key': self.api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.request_times = []
        self.minute_start = datetime.now()
        self.requests_this_minute = 0
        
        # Cache for frequently used data
        self.process_cache = {}
        self.form_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _get_account_url(self, endpoint: str) -> str:
        """Build URL with account ID"""
        return f"{self.BASE_URL}/accounts/{self.account_id}{endpoint}"
    
    def _check_rate_limit(self):
        """Check and enforce Kissflow rate limits"""
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
        retry=retry_if_exception_type((requests.RequestException, KissflowRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to Kissflow API"""
        self._check_rate_limit()
        
        url = self._get_account_url(endpoint)
        
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
                raise KissflowRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                return response.json()
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise KissflowAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL KISSFLOW API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Get account details to test
            account = self._make_request('GET', '')
            self.logger.info(f"Connected to Kissflow account: {account.get('Name', 'Unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_account(self) -> Dict[str, Any]:
        """Get account details"""
        return self._make_request('GET', '')
    
    def get_users(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get users with pagination"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', '/users', params)
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get detailed user information"""
        return self._make_request('GET', f'/users/{user_id}')
    
    def get_groups(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get groups with pagination"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', '/groups', params)
    
    def get_processes(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get all processes (workflows)"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        response = self._make_request('GET', '/processes', params)
        processes = response.get('Data', [])
        
        # Cache processes
        for process in processes:
            self.process_cache[process['Id']] = process
        
        return response
    
    def get_process(self, process_id: str) -> Dict[str, Any]:
        """Get detailed process information"""
        # Check cache first
        if process_id in self.process_cache:
            return self.process_cache[process_id]
        
        process = self._make_request('GET', f'/processes/{process_id}')
        
        if process:
            self.process_cache[process_id] = process
        
        return process
    
    def get_process_instances(self, process_id: str, page_size: int = 100, 
                            page_number: int = 1, status: str = None) -> Dict[str, Any]:
        """Get process instances (running workflows)"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        if status:
            params['status'] = status  # Active, Completed, Aborted
        
        return self._make_request('GET', f'/processes/{process_id}/instances', params)
    
    def get_process_instance(self, process_id: str, instance_id: str) -> Dict[str, Any]:
        """Get detailed process instance"""
        return self._make_request('GET', f'/processes/{process_id}/instances/{instance_id}')
    
    def get_forms(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get all forms"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        response = self._make_request('GET', '/forms', params)
        forms = response.get('Data', [])
        
        # Cache forms
        for form in forms:
            self.form_cache[form['Id']] = form
        
        return response
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """Get detailed form information"""
        # Check cache first
        if form_id in self.form_cache:
            return self.form_cache[form_id]
        
        form = self._make_request('GET', f'/forms/{form_id}')
        
        if form:
            self.form_cache[form_id] = form
        
        return form
    
    def get_form_submissions(self, form_id: str, page_size: int = 100, 
                           page_number: int = 1) -> Dict[str, Any]:
        """Get form submissions"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', f'/forms/{form_id}/submissions', params)
    
    def get_cases(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get all cases"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', '/cases', params)
    
    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Get detailed case information"""
        return self._make_request('GET', f'/cases/{case_id}')
    
    def get_boards(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get all boards (Kanban boards)"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', '/boards', params)
    
    def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get detailed board information"""
        return self._make_request('GET', f'/boards/{board_id}')
    
    def get_board_items(self, board_id: str, page_size: int = 100, 
                       page_number: int = 1) -> Dict[str, Any]:
        """Get items in a board"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', f'/boards/{board_id}/items', params)
    
    def get_datasets(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get all datasets (databases)"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', '/datasets', params)
    
    def get_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Get detailed dataset information"""
        return self._make_request('GET', f'/datasets/{dataset_id}')
    
    def get_dataset_records(self, dataset_id: str, page_size: int = 100, 
                          page_number: int = 1) -> Dict[str, Any]:
        """Get records in a dataset"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', f'/datasets/{dataset_id}/records', params)
    
    def get_reports(self, page_size: int = 100, page_number: int = 1) -> Dict[str, Any]:
        """Get all reports/metrics"""
        params = {
            'page_size': page_size,
            'page_number': page_number
        }
        
        return self._make_request('GET', '/reports', params)
    
    def get_integrations(self) -> List[Dict[str, Any]]:
        """Get all integrations"""
        return self._make_request('GET', '/integrations')
    
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhooks"""
        return self._make_request('GET', '/webhooks')
    
    # ============= FIELD MAPPING =============
    
    def get_process_fields(self, process_id: str) -> List[Dict[str, Any]]:
        """Get fields for a process"""
        process = self.get_process(process_id)
        return process.get('Fields', [])
    
    def get_form_fields(self, form_id: str) -> List[Dict[str, Any]]:
        """Get fields for a form"""
        form = self.get_form(form_id)
        return form.get('Fields', [])
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_users(self, batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get users in batches"""
        page_number = 1
        
        while True:
            response = self.get_users(page_size=batch_size, page_number=page_number)
            users = response.get('Data', [])
            
            if not users:
                break
            
            yield users
            
            # Check if more pages
            if not response.get('HasNext', False):
                break
            
            page_number += 1
            time.sleep(0.5)  # Rate limit pause
    
    def batch_get_process_instances(self, process_id: str, 
                                   batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get process instances in batches"""
        page_number = 1
        
        while True:
            response = self.get_process_instances(
                process_id=process_id,
                page_size=batch_size,
                page_number=page_number
            )
            instances = response.get('Data', [])
            
            if not instances:
                break
            
            yield instances
            
            # Check if more pages
            if not response.get('HasNext', False):
                break
            
            page_number += 1
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Kissflow data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'account': self.get_account(),
            'users': [],
            'groups': [],
            'processes': [],
            'forms': [],
            'cases': [],
            'boards': [],
            'datasets': [],
            'total_processes': 0,
            'total_instances': 0,
            'total_forms': 0,
            'total_submissions': 0
        }
        
        # Get users
        self.logger.info("Fetching users...")
        for user_batch in self.batch_get_users():
            data['users'].extend(user_batch)
        
        # Get groups
        self.logger.info("Fetching groups...")
        response = self.get_groups()
        data['groups'] = response.get('Data', [])
        
        # Get processes
        self.logger.info("Fetching processes...")
        process_response = self.get_processes()
        processes = process_response.get('Data', [])
        
        for process in processes:
            self.logger.info(f"Processing process: {process['Name']}")
            
            # Get full process details
            process_data = self.get_process(process['Id'])
            
            # Get fields
            process_data['Fields'] = self.get_process_fields(process['Id'])
            
            # Get instances
            process_data['instances'] = []
            instance_count = 0
            
            for instance_batch in self.batch_get_process_instances(process['Id']):
                for instance in instance_batch:
                    # Get detailed instance
                    instance_data = self.get_process_instance(process['Id'], instance['Id'])
                    process_data['instances'].append(instance_data)
                    instance_count += 1
                
                # Rate limit pause
                time.sleep(1)
            
            data['total_instances'] += instance_count
            data['processes'].append(process_data)
            data['total_processes'] += 1
            
            self.logger.info(f"  Processed {instance_count} instances")
        
        # Get forms
        self.logger.info("Fetching forms...")
        form_response = self.get_forms()
        forms = form_response.get('Data', [])
        
        for form in forms:
            self.logger.info(f"Processing form: {form['Name']}")
            
            # Get full form details
            form_data = self.get_form(form['Id'])
            
            # Get submissions
            submission_response = self.get_form_submissions(form['Id'])
            form_data['submissions'] = submission_response.get('Data', [])
            data['total_submissions'] += len(form_data['submissions'])
            
            data['forms'].append(form_data)
            data['total_forms'] += 1
        
        # Get cases
        self.logger.info("Fetching cases...")
        case_response = self.get_cases()
        data['cases'] = case_response.get('Data', [])
        
        # Get boards
        self.logger.info("Fetching boards...")
        board_response = self.get_boards()
        boards = board_response.get('Data', [])
        
        for board in boards:
            board_data = self.get_board(board['Id'])
            
            # Get board items
            items_response = self.get_board_items(board['Id'])
            board_data['items'] = items_response.get('Data', [])
            
            data['boards'].append(board_data)
        
        # Get datasets
        self.logger.info("Fetching datasets...")
        dataset_response = self.get_datasets()
        datasets = dataset_response.get('Data', [])
        
        for dataset in datasets:
            dataset_data = self.get_dataset(dataset['Id'])
            
            # Get records
            records_response = self.get_dataset_records(dataset['Id'])
            dataset_data['records'] = records_response.get('Data', [])
            
            data['datasets'].append(dataset_data)
        
        self.logger.info(f"Export complete: {data['total_processes']} processes, {data['total_forms']} forms")
        
        return data
    
    # ============= PARADIGM SHIFT HELPERS =============
    
    def analyze_module_distribution(self) -> Dict[str, Any]:
        """
        Analyze distribution of different Kissflow modules
        Kissflow has multiple paradigms in one platform
        """
        analysis = {
            'modules_used': [],
            'primary_module': None,
            'complexity': 'simple'
        }
        
        # Check processes
        process_response = self.get_processes(page_size=1)
        if process_response.get('TotalCount', 0) > 0:
            analysis['modules_used'].append('process')
            analysis['process_count'] = process_response['TotalCount']
        
        # Check forms
        form_response = self.get_forms(page_size=1)
        if form_response.get('TotalCount', 0) > 0:
            analysis['modules_used'].append('form')
            analysis['form_count'] = form_response['TotalCount']
        
        # Check cases
        case_response = self.get_cases(page_size=1)
        if case_response.get('TotalCount', 0) > 0:
            analysis['modules_used'].append('case')
            analysis['case_count'] = case_response['TotalCount']
        
        # Check boards
        board_response = self.get_boards(page_size=1)
        if board_response.get('TotalCount', 0) > 0:
            analysis['modules_used'].append('board')
            analysis['board_count'] = board_response['TotalCount']
        
        # Check datasets
        dataset_response = self.get_datasets(page_size=1)
        if dataset_response.get('TotalCount', 0) > 0:
            analysis['modules_used'].append('dataset')
            analysis['dataset_count'] = dataset_response['TotalCount']
        
        # Determine primary module
        if len(analysis['modules_used']) == 1:
            analysis['primary_module'] = analysis['modules_used'][0]
            analysis['complexity'] = 'simple'
        elif len(analysis['modules_used']) > 3:
            analysis['complexity'] = 'complex'
            # Find module with most items
            max_count = 0
            for module in analysis['modules_used']:
                count = analysis.get(f'{module}_count', 0)
                if count > max_count:
                    max_count = count
                    analysis['primary_module'] = module
        else:
            analysis['complexity'] = 'moderate'
        
        return analysis
    
    def parse_field_value(self, field_type: str, value: Any) -> Any:
        """
        Parse field value based on Kissflow field type
        """
        if not value:
            return None
        
        if field_type == KissflowFieldType.DATE.value:
            # Date fields return ISO format
            return value
        
        elif field_type == KissflowFieldType.DATETIME.value:
            # DateTime fields return ISO format with time
            return value
        
        elif field_type == KissflowFieldType.NUMBER.value:
            # Number fields
            try:
                return float(value) if value else None
            except:
                return None
        
        elif field_type == KissflowFieldType.CURRENCY.value:
            # Currency fields
            if isinstance(value, dict):
                return {
                    'amount': value.get('Amount'),
                    'currency': value.get('Currency', 'USD')
                }
            return value
        
        elif field_type == KissflowFieldType.YES_NO.value:
            # Boolean fields
            if isinstance(value, str):
                return value.lower() == 'yes'
            return bool(value)
        
        elif field_type == KissflowFieldType.DROPDOWN.value:
            # Dropdown returns selected option
            return value
        
        elif field_type == KissflowFieldType.CHECKBOX.value:
            # Checkbox returns array of selected options
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        elif field_type == KissflowFieldType.USER.value:
            # User fields return user IDs
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        elif field_type == KissflowFieldType.ATTACHMENT.value:
            # Attachment fields return file info
            if isinstance(value, list):
                return value
            return []
        
        elif field_type == KissflowFieldType.FORMULA.value:
            # Formula fields are computed
            return value
        
        elif field_type == KissflowFieldType.LOOKUP.value:
            # Lookup fields reference other data
            return value
        
        else:
            # Default: return as-is
            return value
    
    # ============= CREATE OPERATIONS =============
    
    def create_process_instance(self, process_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new process instance"""
        return self._make_request('POST', f'/processes/{process_id}/instances', data=data)
    
    def create_form_submission(self, form_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new form submission"""
        return self._make_request('POST', f'/forms/{form_id}/submissions', data=data)
    
    def create_case(self, case_type_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new case"""
        return self._make_request('POST', f'/cases/{case_type_id}', data=data)
    
    def create_board_item(self, board_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new board item"""
        return self._make_request('POST', f'/boards/{board_id}/items', data=data)
    
    def create_webhook(self, module: str, module_id: str, url: str, 
                      events: List[str]) -> Dict[str, Any]:
        """Create webhook for module"""
        data = {
            'Module': module,
            'ModuleId': module_id,
            'Url': url,
            'Events': events
        }
        
        return self._make_request('POST', '/webhooks', data=data)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = KissflowProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Kissflow")
        
        # Get account
        account = client.get_account()
        print(f"Account: {account.get('Name', 'Unknown')}")
        
        # Analyze module distribution
        analysis = client.analyze_module_distribution()
        print(f"\nModule analysis:")
        print(f"  - Modules used: {', '.join(analysis['modules_used'])}")
        print(f"  - Primary module: {analysis['primary_module']}")
        print(f"  - Complexity: {analysis['complexity']}")
        
        # Get processes
        process_response = client.get_processes(page_size=5)
        processes = process_response.get('Data', [])
        print(f"\nFound {process_response.get('TotalCount', 0)} processes")
        
        if processes:
            process = processes[0]
            print(f"\nProcess: {process['Name']}")
            
            # Get process details
            full_process = client.get_process(process['Id'])
            fields = full_process.get('Fields', [])
            print(f"Fields: {len(fields)}")
            
            # Get instances
            instance_response = client.get_process_instances(process['Id'], page_size=5)
            instances = instance_response.get('Data', [])
            print(f"Instances: {len(instances)}")
        
        # Get forms
        form_response = client.get_forms(page_size=5)
        forms = form_response.get('Data', [])
        print(f"\nFound {form_response.get('TotalCount', 0)} forms")
        
        if forms:
            form = forms[0]
            print(f"Form: {form['Name']}")
    
    print("\n✅ Production Kissflow client ready!")