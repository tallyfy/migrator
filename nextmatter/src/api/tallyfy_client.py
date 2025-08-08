"""
Tallyfy API Client for RocketLane Migration
Handles all interactions with Tallyfy API using CORRECT field types and endpoints
"""

import requests
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TallyfyClient:
    """Client for interacting with Tallyfy API v2"""
    
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
    
    def __init__(self, api_key: str, organization: str, base_url: str = "https://api.tallyfy.com"):
        """
        Initialize Tallyfy client
        
        Args:
            api_key: Tallyfy API key
            organization: Organization subdomain
            base_url: API base URL
        """
        self.api_key = api_key
        self.organization = organization
        self.organization_id = self._generate_org_id(organization)
        self.base_url = base_url.rstrip('/')
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            # Note: X-Tallyfy-Client header is NOT required
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 2 requests per second
        
    def _generate_org_id(self, org_name: str) -> str:
        """Generate a 32-character organization ID"""
        return hashlib.md5(org_name.encode()).hexdigest()
    
    def _generate_id(self, prefix: str = '') -> str:
        """Generate a 32-character hash ID for entities"""
        timestamp = str(time.time()).encode()
        return hashlib.md5(timestamp).hexdigest()
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        self._rate_limit()
        
        # Ensure endpoint includes organization ID
        if not endpoint.startswith('/api/organizations/'):
            if endpoint.startswith('/'):
                endpoint = f'/api/organizations/{self.organization_id}{endpoint}'
            else:
                endpoint = f'/api/organizations/{self.organization_id}/{endpoint}'
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    # User Management
    def create_user(self, email: str, first_name: str, last_name: str,
                   role: str = 'member') -> Dict[str, Any]:
        """Create a new user"""
        data = {
            'email': email,
            'firstname': first_name,
            'lastname': last_name,
            'role': role
        }
        
        # Users are global, not org-specific
        response = self.session.post(f"{self.base_url}/api/users", json=data)
        response.raise_for_status()
        return response.json()
    
    def create_guest(self, email: str, name: str) -> Dict[str, Any]:
        """Create a guest user"""
        data = {
            'email': email,
            'name': name,
            'organization_id': self.organization_id
        }
        return self._make_request('POST', '/guests', json=data)
    
    # Template/Checklist Management
    def create_checklist(self, name: str, description: str = '',
                        steps: List[Dict] = None) -> Dict[str, Any]:
        """
        Create a checklist (template)
        
        Args:
            name: Checklist name
            description: Checklist description
            steps: List of steps
            
        Returns:
            Created checklist
        """
        data = {
            'id': self._generate_id('chk'),
            'title': name[:250],  # Max 250 chars
            'summary': description[:2000],  # Max 2000 chars
            'organization_id': self.organization_id,
            'status': 'active',
            'is_template': True
        }
        
        checklist = self._make_request('POST', '/checklists', json=data)
        
        # Add steps if provided
        if steps:
            for idx, step in enumerate(steps):
                self.add_step_to_checklist(checklist['id'], step, position=idx)
        
        return checklist
    
    def add_step_to_checklist(self, checklist_id: str, step_data: Dict,
                             position: int = 0) -> Dict[str, Any]:
        """Add a step to a checklist"""
        data = {
            'id': self._generate_id('stp'),
            'title': step_data.get('name', 'Untitled Step')[:600],  # Max 600 chars
            'description': step_data.get('description', ''),
            'task_type': step_data.get('type', 'task'),  # task, approval, expiring
            'position': position,
            'checklist_id': checklist_id
        }
        
        # Add form fields if present
        if 'fields' in step_data:
            data['captures'] = self._transform_fields(step_data['fields'])
        
        return self._make_request('POST', f'/checklists/{checklist_id}/steps', json=data)
    
    def _transform_fields(self, fields: List[Dict]) -> List[Dict]:
        """Transform field definitions to Tallyfy format"""
        captures = []
        
        for field in fields:
            field_type = field.get('type', 'text')
            
            # Map to correct Tallyfy field type
            if field_type not in self.FIELD_TYPES:
                # Map common incorrect types
                mappings = {
                    'short_text': 'text',
                    'long_text': 'textarea',
                    'radio_buttons': 'radio',
                    'checklist': 'multiselect',
                    'file_upload': 'file',
                    'assignee_picker': 'assignees_form',
                    'number': 'text'  # No number type, use text with validation
                }
                field_type = mappings.get(field_type, 'text')
            
            capture = {
                'id': self._generate_id('cap'),
                'field_type': field_type,
                'label': field.get('label', 'Field'),
                'required': field.get('required', False),
                'guidance': field.get('help_text', '')
            }
            
            # Add validation for number fields
            if field.get('type') == 'number':
                capture['field_validation'] = 'numeric'
            elif field_type == 'email':
                capture['field_validation'] = 'email'
            elif field.get('validation'):
                capture['field_validation'] = field['validation']
            
            # Add options for select fields
            if field_type in ['dropdown', 'radio', 'multiselect']:
                capture['options'] = field.get('options', [])
            
            captures.append(capture)
        
        return captures
    
    def add_kickoff_form(self, checklist_id: str, fields: List[Dict]) -> Dict[str, Any]:
        """Add kick-off form fields to a checklist"""
        prerun_fields = self._transform_fields(fields)
        
        for field in prerun_fields:
            field['class_id'] = checklist_id  # Link to checklist, not step
            self._make_request('POST', f'/checklists/{checklist_id}/preruns', json=field)
        
        return {'success': True, 'fields_added': len(prerun_fields)}
    
    # Process/Run Management
    def create_run(self, checklist_id: str, name: str,
                  prerun_data: Dict = None) -> Dict[str, Any]:
        """
        Create a run (process instance)
        
        Args:
            checklist_id: Template ID
            name: Process name
            prerun_data: Kick-off form data (as object, not array!)
            
        Returns:
            Created run
        """
        data = {
            'id': self._generate_id('run'),
            'checklist_id': checklist_id,
            'name': name,
            'organization_id': self.organization_id,
            'status': 'active'
        }
        
        # Add prerun data if provided (MUST be object, not array)
        if prerun_data:
            data['prerun_data'] = prerun_data  # Object format: {"field_id": "value"}
        
        return self._make_request('POST', '/runs', json=data)
    
    def update_run_task(self, run_id: str, task_id: str,
                       data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task in a run"""
        return self._make_request('PUT', f'/runs/{run_id}/tasks/{task_id}', json=data)
    
    def complete_task(self, run_id: str, task_id: str,
                     completed_by: Optional[str] = None) -> Dict[str, Any]:
        """Mark a task as completed"""
        data = {
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat()
        }
        
        if completed_by:
            data['completed_by'] = completed_by
        
        return self.update_run_task(run_id, task_id, data)
    
    def add_comment(self, run_id: str, task_id: str, 
                   comment: str, author: Optional[str] = None) -> Dict[str, Any]:
        """Add a comment to a task"""
        data = {
            'id': self._generate_id('cmt'),
            'text': comment,
            'task_id': task_id,
            'run_id': run_id
        }
        
        if author:
            data['author_id'] = author
        
        return self._make_request('POST', f'/runs/{run_id}/tasks/{task_id}/comments', json=data)
    
    def upload_file(self, run_id: str, task_id: str,
                   file_path: str, file_name: str) -> Dict[str, Any]:
        """Upload a file to a task"""
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f)}
            
            # Temporarily remove JSON content type for file upload
            headers = self.session.headers.copy()
            del headers['Content-Type']
            
            response = requests.post(
                f"{self.base_url}/api/organizations/{self.organization_id}/runs/{run_id}/tasks/{task_id}/files",
                headers=headers,
                files=files
            )
            response.raise_for_status()
            return response.json()
    
    def set_field_value(self, run_id: str, field_id: str, value: Any) -> Dict[str, Any]:
        """Set a form field value in a run"""
        data = {'value': value}
        return self._make_request('PUT', f'/runs/{run_id}/fields/{field_id}/value', json=data)
    
    # Groups
    def create_group(self, name: str, member_ids: List[str] = None) -> Dict[str, Any]:
        """Create a group"""
        data = {
            'id': self._generate_id('grp'),
            'name': name,
            'organization_id': self.organization_id,
            'members': member_ids or []
        }
        return self._make_request('POST', '/groups', json=data)
    
    # Validation
    def validate_checklist(self, checklist_id: str) -> bool:
        """Validate that a checklist was created successfully"""
        try:
            checklist = self._make_request('GET', f'/checklists/{checklist_id}')
            return checklist is not None
        except:
            return False
    
    def validate_run(self, run_id: str) -> bool:
        """Validate that a run was created successfully"""
        try:
            run = self._make_request('GET', f'/runs/{run_id}')
            return run is not None
        except:
            return False
    
    def get_statistics(self) -> Dict[str, int]:
        """Get migration statistics"""
        stats = {}
        
        try:
            # Get counts
            checklists = self._make_request('GET', '/checklists')
            stats['templates'] = len(checklists.get('data', []))
            
            runs = self._make_request('GET', '/runs')
            stats['processes'] = len(runs.get('data', []))
            
        except Exception as e:
            logger.warning(f"Could not fetch statistics: {e}")
        
        return stats