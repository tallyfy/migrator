"""
Tallyfy API Client
Handles all interactions with Tallyfy API for data import
"""

import requests
import time
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin
from datetime import datetime, timedelta
import backoff

logger = logging.getLogger(__name__)


class TallyfyClient:
    """Client for interacting with Tallyfy API"""
    
    # CORRECT Tallyfy field types from api-v2
    FIELD_TYPES = {
        'text',          # Short text (max 255 chars)
        'textarea',      # Long text (max 6000 chars)
        'radio',         # Radio buttons
        'dropdown',      # Single select dropdown
        'multiselect',   # Multiple select
        'date',          # Date picker
        'email',         # Email field
        'file',          # File upload
        'table',         # Table/grid
        'assignees_form' # User/guest assignment
    }
    
    def __init__(self, api_url: str, client_id: str, client_secret: str, 
                 organization_id: str, organization_slug: str):
        """
        Initialize Tallyfy API client
        
        Args:
            api_url: Tallyfy API base URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            organization_id: Tallyfy organization ID
            organization_slug: Organization slug for URL routing
        """
        self.api_url = api_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.organization_id = organization_id
        self.organization_slug = organization_slug
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            
            'Accept': 'application/json'
        })
        
        # OAuth2 token management
        self.access_token = None
        self.token_expires_at = None
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.6  # 100 requests per minute
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'rate_limits_hit': 0,
            'errors': 0,
            'data_imported': {}
        }
        
        # Authenticate on initialization
        self._authenticate()
    
    def _generate_hash_id(self, prefix: str = '') -> str:
        """
        Generate a Tallyfy-style 32-character hash ID
        
        Args:
            prefix: Optional prefix for the ID
            
        Returns:
            32-character hash ID
        """
        timestamp = str(time.time())
        random_str = hashlib.md5(timestamp.encode()).hexdigest()
        
        if prefix:
            # Ensure total length is 32
            prefix_len = min(len(prefix), 8)
            return prefix[:prefix_len] + random_str[:32-prefix_len]
        
        return random_str[:32]
    
    def _authenticate(self) -> None:
        """
        Authenticate with Tallyfy OAuth2
        """
        logger.info("Authenticating with Tallyfy API...")
        
        auth_url = urljoin(self.api_url, '/oauth/token')
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'read write'
        }
        
        try:
            response = requests.post(auth_url, json=auth_data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Update session headers with token
            self.session.headers['Authorization'] = f'Bearer {self.access_token}'
            logger.info("Authentication successful")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def _ensure_authenticated(self) -> None:
        """
        Ensure we have a valid authentication token
        """
        if not self.access_token or datetime.utcnow() >= self.token_expires_at:
            self._authenticate()
    
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request with authentication and error handling
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional request parameters
            
        Returns:
            API response as dictionary
        """
        self._ensure_authenticated()
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        # Build URL with organization path
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        # Add organization context to path if needed - MUST include /api prefix
        if '/organizations/' not in endpoint and '/oauth/' not in endpoint:
            endpoint = f'/api/organizations/{self.organization_id}{endpoint}'
        
        url = urljoin(self.api_url, endpoint)
        
        logger.debug(f"Making {method} request to {url}")
        self.stats['api_calls'] += 1
        
        try:
            response = self.session.request(method, url, **kwargs)
            self.last_request_time = time.time()
            
            if response.status_code == 429:
                self.stats['rate_limits_hit'] += 1
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, **kwargs)
            
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204:
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.stats['errors'] += 1
            logger.error(f"API request failed: {e}")
            raise
    
    # Organization Methods
    def get_organization(self) -> Dict[str, Any]:
        """Get current organization details"""
        return self._make_request('GET', f'/api/organizations/{self.organization_id}')
    
    def update_organization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update organization settings"""
        return self._make_request('PATCH', f'/api/organizations/{self.organization_id}', json=data)
    
    # User Methods
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user in the organization
        
        Args:
            user_data: User information including email, first_name, last_name, role
            
        Returns:
            Created user object
        """
        # Generate Tallyfy user ID if not provided
        if 'id' not in user_data:
            user_data['id'] = self._generate_hash_id('usr')
        
        # Set default role if not specified
        if 'role' not in user_data:
            user_data['role'] = 'member'
        
        # Add organization context
        user_data['organization_id'] = self.organization_id
        
        result = self._make_request('POST', '/users', json=user_data)
        
        self.stats['data_imported'].setdefault('users', 0)
        self.stats['data_imported']['users'] += 1
        
        logger.info(f"Created user: {user_data.get('email', user_data.get('first_name', 'Unknown'))}")
        return result
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID"""
        return self._make_request('GET', f'/users/{user_id}')
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users in the organization"""
        return self._make_request('GET', '/users')
    
    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email address"""
        users = self.list_users()
        for user in users:
            if user.get("email") == email:
                return user
        return None
    
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        return self._make_request('PATCH', f'/users/{user_id}', json=user_data)
    
    # Group Methods
    def create_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new group
        
        Args:
            group_data: Group information including name, description
            
        Returns:
            Created group object
        """
        if 'id' not in group_data:
            group_data['id'] = self._generate_hash_id('grp')
        
        group_data['organization_id'] = self.organization_id
        
        result = self._make_request('POST', '/groups', json=group_data)
        
        self.stats['data_imported'].setdefault('groups', 0)
        self.stats['data_imported']['groups'] += 1
        
        logger.info(f"Created group: {group_data['name']}")
        return result
    
    def add_user_to_group(self, group_id: str, user_id: str) -> Dict[str, Any]:
        """Add user to a group"""
        return self._make_request('POST', f'/groups/{group_id}/members', 
                                 json={'user_id': user_id})
    
    # Checklist (Template) Methods
    def create_checklist(self, checklist_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new checklist template
        
        Args:
            checklist_data: Checklist template data
            
        Returns:
            Created checklist object
        """
        if 'id' not in checklist_data:
            checklist_data['id'] = self._generate_hash_id('chk')
        
        checklist_data['organization_id'] = self.organization_id
        
        # Ensure required fields
        if 'status' not in checklist_data:
            checklist_data['status'] = 'active'
        if 'is_template' not in checklist_data:
            checklist_data['is_template'] = True
        
        result = self._make_request('POST', f'/api/organizations/{self.organization_id}/checklists', json=checklist_data)
        
        self.stats['data_imported'].setdefault('checklists', 0)
        self.stats['data_imported']['checklists'] += 1
        
        logger.info(f"Created checklist: {checklist_data.get('title', 'Untitled')}")
        return result
    
    def get_checklist(self, checklist_id: str) -> Dict[str, Any]:
        """Get checklist by ID"""
        return self._make_request('GET', f'/api/organizations/{self.organization_id}/checklists/{checklist_id}')
    
    def list_checklists(self) -> List[Dict[str, Any]]:
        """List all checklists in the organization"""
        return self._make_request('GET', f'/api/organizations/{self.organization_id}/checklists')
    
    # Step Methods
    def create_step(self, checklist_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a step in a checklist
        
        Args:
            checklist_id: Parent checklist ID
            step_data: Step information
            
        Returns:
            Created step object
        """
        if 'id' not in step_data:
            step_data['id'] = self._generate_hash_id('stp')
        
        step_data['checklist_id'] = checklist_id
        
        # Set defaults
        if 'task_type' not in step_data:
            step_data['task_type'] = 'normal'
        if 'position' not in step_data:
            step_data['position'] = 0
        
        result = self._make_request('POST', f'/api/organizations/{self.organization_id}/checklists/{checklist_id}/steps', json=step_data)
        
        self.stats['data_imported'].setdefault('steps', 0)
        self.stats['data_imported']['steps'] += 1
        
        logger.info(f"Created step: {step_data.get('title', 'Untitled')}")
        return result
    
    def create_steps_batch(self, checklist_id: str, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple steps in batch
        
        Args:
            checklist_id: Parent checklist ID
            steps: List of step data
            
        Returns:
            List of created steps
        """
        created_steps = []
        
        for i, step_data in enumerate(steps):
            if 'position' not in step_data:
                step_data['position'] = i
            
            created_step = self.create_step(checklist_id, step_data)
            created_steps.append(created_step)
            
            # Small delay between requests
            time.sleep(0.1)
        
        return created_steps
    
    # Process (Instance) Methods
    def create_process(self, process_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new process (checklist instance)
        
        Args:
            process_data: Process information including checklist_id
            
        Returns:
            Created process object
        """
        if 'id' not in process_data:
            process_data['id'] = self._generate_hash_id('prc')
        
        process_data['organization_id'] = self.organization_id
        
        # Set defaults
        if 'status' not in process_data:
            process_data['status'] = 'active'
        
        # Handle prerun_data if present - MUST be object format, not array
        if 'prerun_data' in process_data and isinstance(process_data['prerun_data'], list):
            # Convert array to object format
            prerun_obj = {}
            for item in process_data['prerun_data']:
                if isinstance(item, dict) and 'field_id' in item and 'value' in item:
                    prerun_obj[item['field_id']] = item['value']
            process_data['prerun_data'] = prerun_obj
        
        result = self._make_request('POST', f'/api/organizations/{self.organization_id}/runs', json=process_data)
        
        self.stats['data_imported'].setdefault('processes', 0)
        self.stats['data_imported']['processes'] += 1
        
        logger.info(f"Created process: {process_data.get('title', 'Untitled')}")
        return result
    
    def get_process(self, run_id: str) -> Dict[str, Any]:
        """Get process by ID"""
        return self._make_request('GET', f'/api/organizations/{self.organization_id}/runs/{run_id}')
    
    def update_process(self, run_id: str, process_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update process information"""
        return self._make_request('PATCH', f'/api/organizations/{self.organization_id}/runs/{run_id}', json=process_data)
    
    # Step Instance Methods
    def update_step_instance(self, run_id: str, step_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a step instance in a process
        
        Args:
            run_id: Process ID
            step_id: Step ID
            data: Update data (status, completed_at, etc.)
            
        Returns:
            Updated step instance
        """
        return self._make_request('PATCH', f'/api/organizations/{self.organization_id}/runs/{run_id}/tasks/{step_id}', json=data)
    
    def complete_step(self, run_id: str, step_id: str, completed_by: str) -> Dict[str, Any]:
        """
        Mark a step as completed
        
        Args:
            run_id: Process ID
            step_id: Step ID
            completed_by: User ID who completed the step
            
        Returns:
            Updated step instance
        """
        data = {
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat(),
            'completed_by': completed_by
        }
        return self.update_step_instance(run_id, step_id, data)
    
    # Form/field Methods
    def create_capture(self, entity_type: str, entity_id: str, capture_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a capture (form field) for an entity
        
        Args:
            entity_type: Type of entity (checklist, step, process)
            entity_id: Entity ID
            capture_data: Capture field configuration
            
        Returns:
            Created capture object
        """
        if 'id' not in capture_data:
            capture_data['id'] = self._generate_hash_id('cap')
        
        # Validate field type
        if 'field_type' in capture_data:
            if capture_data['field_type'] not in self.FIELD_TYPES:
                logger.warning(f"Invalid field type: {capture_data['field_type']}, defaulting to 'text'")
                capture_data['field_type'] = 'text'
        
        endpoint = f'/api/organizations/{self.organization_id}/{entity_type}s/{entity_id}/captures'
        result = self._make_request('POST', endpoint, json=capture_data)
        
        self.stats['data_imported'].setdefault('captures', 0)
        self.stats['data_imported']['captures'] += 1
        
        return result
    
    def set_capture_value(self, run_id: str, capture_id: str, value: Any) -> Dict[str, Any]:
        """
        Set a capture field value in a process
        
        Args:
            run_id: Process ID
            capture_id: field field ID
            value: Field value
            
        Returns:
            Updated field value
        """
        data = {'value': value}
        return self._make_request('PUT', f'/api/organizations/{self.organization_id}/runs/{run_id}/captures/{capture_id}/value', 
                                 json=data)
    
    # Comment Methods
    def create_comment(self, entity_type: str, entity_id: str, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a comment on an entity
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            comment_data: Comment content and metadata
            
        Returns:
            Created comment object
        """
        if 'id' not in comment_data:
            comment_data['id'] = self._generate_hash_id('cmt')
        
        endpoint = f'/{entity_type}s/{entity_id}/comments'
        result = self._make_request('POST', endpoint, json=comment_data)
        
        self.stats['data_imported'].setdefault('comments', 0)
        self.stats['data_imported']['comments'] += 1
        
        return result
    
    # File Methods
    def upload_file(self, file_path: str, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """
        Upload a file and attach to an entity
        
        Args:
            file_path: Local file path
            entity_type: Type of entity to attach to
            entity_id: Entity ID
            
        Returns:
            File metadata
        """
        with open(file_path, 'rb') as f:
            files = {"file": f}
            endpoint = f'/{entity_type}s/{entity_id}/attachments'
            
            # Temporarily remove JSON content type for file_upload upload
            original_content_type = self.session.headers.get('Content-Type')
            del self.session.headers['Content-Type']
            
            try:
                result = self._make_request('POST', endpoint, files=files)
                
                self.stats['data_imported'].setdefault('files', 0)
                self.stats['data_imported']['files'] += 1
                
                logger.info(f"Uploaded file: {file_path}")
                return result
                
            finally:
                # Restore content type
                if original_content_type:
                    self.session.headers['Content-Type'] = original_content_type
    
    # Webhook Methods
    def create_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a webhook
        
        Args:
            webhook_data: Webhook configuration
            
        Returns:
            Created webhook object
        """
        if 'id' not in webhook_data:
            webhook_data['id'] = self._generate_hash_id('whk')
        
        webhook_data['organization_id'] = self.organization_id
        
        result = self._make_request('POST', '/webhooks', json=webhook_data)
        
        self.stats['data_imported'].setdefault('webhooks', 0)
        self.stats['data_imported']['webhooks'] += 1
        
        logger.info(f"Created webhook: {webhook_data.get("text", 'Unknown')}")
        return result
    
    # Batch Operations
    def batch_create_users(self, users: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """
        Create multiple users in batch
        
        Args:
            users: List of user data
            
        Returns:
            Tuple of (successful_users, failed_users)
        """
        successful = []
        failed = []
        
        for user_data in users:
            try:
                # Check if user already exists
                existing = self.find_user_by_email(user_data["text"])
                if existing:
                    logger.info(f"User already exists: {user_data["text"]}")
                    successful.append(existing)
                else:
                    created = self.create_user(user_data)
                    successful.append(created)
                
            except Exception as e:
                logger.error(f"Failed to create user {user_data.get("text", 'Unknown')}: {e}")
                failed.append({'user': user_data, 'error': str(e)})
            
            # Rate limiting between requests
            time.sleep(0.1)
        
        return successful, failed
    
    # Validation Methods
    def validate_import(self, entity_type: str, entity_id: str) -> bool:
        """
        Validate that an entity was successfully imported
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            True if entity exists and is valid
        """
        try:
            endpoint = f'/{entity_type}s/{entity_id}'
            result = self._make_request('GET', endpoint)
            return result is not None
        except Exception:
            return False
    
    def get_import_statistics(self) -> Dict[str, Any]:
        """Get import statistics"""
        return {
            'summary': self.stats['data_imported'].copy(),
            'total_imported': sum(self.stats['data_imported'].values()),
            'api_calls': self.stats['api_calls'],
            'errors': self.stats['errors'],
            'rate_limits_hit': self.stats['rate_limits_hit']
        }