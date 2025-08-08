"""Tallyfy API client for Kissflow migration."""

import requests
import logging
from typing import Dict, List, Optional, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TallyfyClient:
    """Client for interacting with Tallyfy API."""
    
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
    
    def __init__(self, api_token: str, organization_id: str,
                 base_url: str = "https://go.tallyfy.com/api"):
        """Initialize Tallyfy client.
        
        Args:
            api_token: Tallyfy API token
            organization_id: Organization ID
            base_url: API base URL
        """
        self.api_token = api_token
        self.organization_id = organization_id
        self.base_url = base_url.rstrip('/')
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
                    })
        
        return session
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity.
        
        Returns:
            Organization info if successful
        """
        response = self.session.get(f"{self.base_url}/organizations/{self.organization_id}")
        response.raise_for_status()
        return response.json()
    
    def create_member(self, email: str, first_name: str, last_name: str,
                     role: str = 'member') -> Dict[str, Any]:
        """Create a new member.
        
        Args:
            email: User email
            first_name: First name
            last_name: Last name
            role: Member role (admin, member, light)
            
        Returns:
            Created member object
        """
        data = {
            "email": email,
            'firstname': first_name,
            'lastname': last_name,
            'role': role,
            'organization_id': self.organization_id
        }
        response = self.session.post(f"{self.base_url}/members", json=data)
        
        if response.status_code == 409:
            # User already exists
            logger.info(f"Member {email} already exists")
            return self.get_member_by_email(email)
            
        response.raise_for_status()
        return response.json()
    
    def get_member_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get member by email.
        
        Args:
            email: User email
            
        Returns:
            Member object or None
        """
        response = self.session.get(f"{self.base_url}/members", 
                                   params={'organization_id': self.organization_id})
        response.raise_for_status()
        
        members = response.json().get('data', [])
        for member in members:
            if member.get("email") == email:
                return member
        return None
    
    def create_group(self, name: str, member_ids: List[str]) -> Dict[str, Any]:
        """Create a group.
        
        Args:
            name: Group name
            member_ids: List of member IDs
            
        Returns:
            Created group object
        """
        data = {
            'name': name,
            'members': member_ids,
            'organization_id': self.organization_id
        }
        response = self.session.post(f"{self.base_url}/groups", json=data)
        response.raise_for_status()
        return response.json()
    
    def create_blueprint(self, name: str, description: str = '',
                        steps: List[Dict] = None) -> Dict[str, Any]:
        """Create a blueprint (template).
        
        Args:
            name: Blueprint name
            description: Blueprint description
            steps: List of step definitions
            
        Returns:
            Created blueprint object
        """
        data = {
            'name': name,
            'description': description,
            'organization_id': self.organization_id,
            'steps': steps or []
        }
        response = self.session.post(f"{self.base_url}/api/organizations/{self.organization_id}/checklists", json=data)
        response.raise_for_status()
        return response.json()
    
    def create_process(self, checklist_id: str, name: str,
                      data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a process (running instance).
        
        Args:
            checklist_id: Blueprint ID to instantiate
            name: Process name
            data: Kick-off form data
            
        Returns:
            Created process object
        """
        payload = {
            'checklist_id': checklist_id,
            'name': name,
            'organization_id': self.organization_id
        }
        if data:
            # Handle prerun_data - MUST be object format, not array
            if isinstance(data, list):
                # Convert array to object format
                prerun_obj = {}
                for item in data:
                    if isinstance(item, dict) and 'field_id' in item and 'value' in item:
                        prerun_obj[item['field_id']] = item['value']
                payload['prerun_data'] = prerun_obj
            else:
                payload['prerun_data'] = data
            
        response = self.session.post(f"{self.base_url}/api/organizations/{self.organization_id}/runs", json=payload)
        response.raise_for_status()
        return response.json()
    
    def update_task(self, task_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task.
        
        Args:
            task_id: Task ID
            data: Update data
            
        Returns:
            Updated task object
        """
        response = self.session.put(f"{self.base_url}/tasks/{task_id}", json=data)
        response.raise_for_status()
        return response.json()
    
    def add_comment(self, task_id: str, text: str) -> Dict[str, Any]:
        """Add comment to task.
        
        Args:
            task_id: Task ID
            text: Comment text
            
        Returns:
            Created comment object
        """
        data = {
            'task_id': task_id,
            "text": text
        }
        response = self.session.post(f"{self.base_url}/comments", json=data)
        response.raise_for_status()
        return response.json()
    
    def upload_file(self, task_id: str, file_path: str) -> Dict[str, Any]:
        """Upload file to task.
        
        Args:
            task_id: Task ID
            file_path: Path to file
            
        Returns:
            Upload result
        """
        with open(file_path, 'rb') as f:
            files = {"file": f}
            data = {'task_id': task_id}
            response = self.session.post(f"{self.base_url}/files", 
                                        files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    def create_tag(self, name: str) -> Dict[str, Any]:
        """Create a tag.
        
        Args:
            name: Tag name
            
        Returns:
            Created tag object
        """
        data = {
            'name': name,
            'organization_id': self.organization_id
        }
        response = self.session.post(f"{self.base_url}/tags", json=data)
        response.raise_for_status()
        return response.json()
    
    def create_webhook(self, checklist_id: str, url: str, 
                      events: List[str]) -> Dict[str, Any]:
        """Create a webhook for automation.
        
        Args:
            checklist_id: Blueprint ID
            url: Webhook URL
            events: List of events to trigger on
            
        Returns:
            Created webhook object
        """
        data = {
            'checklist_id': checklist_id,
            "url": url,
            'events': events,
            'organization_id': self.organization_id
        }
        response = self.session.post(f"{self.base_url}/webhooks", json=data)
        response.raise_for_status()
        return response.json()