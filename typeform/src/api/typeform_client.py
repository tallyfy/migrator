"""
Typeform API Client
Handles interactions with Typeform API v2
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TypeformClient:
    """Client for Typeform API"""
    
    def __init__(self, api_key: str):
        """Initialize Typeform client"""
        self.api_key = api_key
        self.base_url = "https://api.typeform.com"
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info("Typeform client initialized")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    # Forms Management
    def get_forms(self, page: int = 1, page_size: int = 200) -> Dict[str, Any]:
        """Get all forms"""
        params = {
            'page': page,
            'page_size': page_size
        }
        return self._make_request('GET', '/forms', params=params)
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """Get form details including fields"""
        return self._make_request('GET', f'/forms/{form_id}')
    
    def get_responses(self, form_id: str, page_size: int = 1000) -> Dict[str, Any]:
        """Get form responses"""
        params = {
            'page_size': page_size,
            'completed': True
        }
        return self._make_request('GET', f'/forms/{form_id}/responses', params=params)
    
    # Workspaces
    def get_workspaces(self) -> Dict[str, Any]:
        """Get all workspaces"""
        return self._make_request('GET', '/workspaces')
    
    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace details"""
        return self._make_request('GET', f'/workspaces/{workspace_id}')
    
    def get_workspace_members(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get workspace members"""
        response = self._make_request('GET', f'/workspaces/{workspace_id}/members')
        return response.get('items', [])
    
    # Themes
    def get_themes(self) -> Dict[str, Any]:
        """Get available themes"""
        return self._make_request('GET', '/themes')
    
    # Images
    def get_images(self) -> Dict[str, Any]:
        """Get uploaded images"""
        return self._make_request('GET', '/images')
    
    # Webhooks
    def get_webhooks(self, form_id: str) -> Dict[str, Any]:
        """Get form webhooks"""
        return self._make_request('GET', f'/forms/{form_id}/webhooks')
    
    # Discovery
    def discover_workspace(self) -> Dict[str, Any]:
        """Discover complete workspace"""
        discovery = {
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {},
            'forms': []
        }
        
        # Get all forms
        forms_response = self.get_forms()
        forms = forms_response.get('items', [])
        discovery['statistics']['total_forms'] = forms_response.get('total_items', 0)
        
        # Get details for each form
        total_fields = 0
        total_responses = 0
        
        for form in forms[:20]:  # Limit for discovery
            form_details = self.get_form(form['id'])
            field_count = len(form_details.get('fields', []))
            
            # Get response count
            responses = self.get_responses(form['id'], page_size=1)
            response_count = responses.get('total_items', 0)
            
            total_fields += field_count
            total_responses += response_count
            
            discovery['forms'].append({
                'id': form['id'],
                'title': form.get('title'),
                'fields': field_count,
                'responses': response_count,
                'created_at': form.get('created_at'),
                'last_updated_at': form.get('last_updated_at')
            })
        
        discovery['statistics']['total_fields'] = total_fields
        discovery['statistics']['total_responses'] = total_responses
        
        # Get workspaces
        workspaces = self.get_workspaces()
        discovery['statistics']['workspaces'] = len(workspaces.get('items', []))
        
        return discovery
    
    def transform_field_to_tallyfy(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Typeform field to Tallyfy format"""
        field_type = field.get('type', 'short_text')
        
        # Map Typeform types to Tallyfy
        type_mapping = {
            'short_text': 'text',
            'long_text': 'textarea',
            'multiple_choice': 'radio',
            'picture_choice': 'radio',
            'dropdown': 'dropdown',
            'yes_no': 'radio',
            'email': 'email',
            'number': 'text',  # With numeric validation
            'rating': 'dropdown',
            'opinion_scale': 'dropdown',
            'date': 'date',
            'file_upload': 'file',
            'legal': 'radio',  # Accept/Decline
            'website': 'text',  # With URL validation
            'phone_number': 'text',  # With phone validation
            'payment': 'text',  # Note about payment
            'matrix': 'table',
            'ranking': 'multiselect'
        }
        
        tallyfy_type = type_mapping.get(field_type, 'text')
        
        tallyfy_field = {
            'type': tallyfy_type,
            'label': field.get('title', ''),
            'required': field.get('validations', {}).get('required', False),
            'help_text': field.get('properties', {}).get('description', ''),
            'metadata': {
                'typeform_id': field.get('id'),
                'typeform_type': field_type,
                'typeform_ref': field.get('ref')
            }
        }
        
        # Handle choices
        if field_type in ['multiple_choice', 'picture_choice', 'dropdown']:
            choices = field.get('properties', {}).get('choices', [])
            tallyfy_field['options'] = [
                {'value': c.get('ref', c.get('label')), 'label': c.get('label', '')}
                for c in choices
            ]
        
        # Handle yes/no
        if field_type == 'yes_no':
            tallyfy_field['options'] = [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]
        
        # Handle rating/scale
        if field_type in ['rating', 'opinion_scale']:
            steps = field.get('properties', {}).get('steps', 5)
            tallyfy_field['options'] = [
                {'value': str(i), 'label': str(i)}
                for i in range(1, steps + 1)
            ]
        
        # Add validation
        if field_type == 'email':
            tallyfy_field['validation'] = 'email'
        elif field_type == 'number':
            tallyfy_field['validation'] = 'numeric'
        elif field_type == 'website':
            tallyfy_field['validation'] = 'url'
        elif field_type == 'phone_number':
            tallyfy_field['validation'] = 'regex:^[\\d\\s\\-\\+\\(\\)]+$'
        
        return tallyfy_field
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self.get_forms(page_size=1)
            logger.info("Typeform API connection successful")
            return True
        except Exception as e:
            logger.error(f"Typeform API connection failed: {e}")
            return False