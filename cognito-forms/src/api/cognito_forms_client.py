"""
Cognito Forms API Client
Handles all interactions with Cognito Forms API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time
import base64

logger = logging.getLogger(__name__)


class CognitoFormsClient:
    """Client for Cognito Forms API operations"""
    
    def __init__(self, api_key: str = None, organization: str = None, base_url: str = None):
        """
        Initialize Cognito Forms API client
        
        Args:
            api_key: Cognito Forms API key
            organization: Organization name
            base_url: Base URL for Cognito Forms API
        """
        self.api_key = api_key or os.getenv('COGNITO_FORMS_API_KEY')
        self.organization = organization or os.getenv('COGNITO_FORMS_ORGANIZATION')
        self.base_url = base_url or os.getenv('COGNITO_FORMS_BASE_URL', 'https://www.cognitoforms.com/api/1')
        
        if not self.api_key:
            raise ValueError("Cognito Forms API key is required")
        
        if not self.organization:
            raise ValueError("Cognito Forms organization is required")
        
        self.session = requests.Session()
        
        # Cognito Forms uses Basic Auth with API key as password
        auth_string = f"{self.api_key}:"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        self.session.headers.update({
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        logger.info(f"Cognito Forms client initialized for {self.organization}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with retries"""
        url = f"{self.base_url}/organizations/{self.organization}/{endpoint}"
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 429:  # Rate limited
                    wait_time = 60
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
    
    def get_forms(self) -> List[Dict[str, Any]]:
        """Get all forms"""
        logger.info("Fetching Cognito Forms...")
        forms = []
        skip = 0
        limit = 100
        
        while True:
            result = self._make_request('GET', 'forms', params={
                '$skip': skip,
                '$top': limit,
                '$orderby': 'Name'
            })
            
            if isinstance(result, list):
                forms.extend(result)
                if len(result) < limit:
                    break
                skip += limit
            else:
                break
        
        logger.info(f"Found {len(forms)} forms")
        return forms
    
    def get_form_details(self, form_id: str) -> Dict[str, Any]:
        """Get form details"""
        logger.debug(f"Fetching form {form_id}")
        return self._make_request('GET', f'forms/{form_id}')
    
    def get_form_fields(self, form_id: str) -> List[Dict[str, Any]]:
        """Get form fields"""
        logger.debug(f"Fetching fields for form {form_id}")
        form = self.get_form_details(form_id)
        
        # Extract fields from form structure
        fields = []
        if 'Fields' in form:
            fields = form['Fields']
        elif 'Definition' in form and 'Fields' in form['Definition']:
            fields = form['Definition']['Fields']
        
        return fields
    
    def get_form_entries(self, form_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get form entries (submissions)"""
        logger.debug(f"Fetching entries for form {form_id}")
        entries = []
        skip = 0
        batch_size = 100
        
        while len(entries) < limit:
            result = self._make_request('GET', f'forms/{form_id}/entries', params={
                '$skip': skip,
                '$top': min(batch_size, limit - len(entries)),
                '$orderby': 'DateCreated desc'
            })
            
            if isinstance(result, list):
                entries.extend(result)
                if len(result) < batch_size:
                    break
                skip += batch_size
            else:
                break
        
        return entries[:limit]
    
    def get_entry_details(self, form_id: str, entry_id: str) -> Dict[str, Any]:
        """Get entry details"""
        logger.debug(f"Fetching entry {entry_id} from form {form_id}")
        return self._make_request('GET', f'forms/{form_id}/entries/{entry_id}')
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get organization users"""
        logger.info("Fetching users...")
        users = []
        skip = 0
        limit = 100
        
        while True:
            result = self._make_request('GET', 'users', params={
                '$skip': skip,
                '$top': limit
            })
            
            if isinstance(result, list):
                users.extend(result)
                if len(result) < limit:
                    break
                skip += limit
            else:
                break
        
        logger.info(f"Found {len(users)} users")
        return users
    
    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        logger.debug(f"Fetching user {user_id}")
        return self._make_request('GET', f'users/{user_id}')
    
    def get_workflows(self, form_id: str) -> List[Dict[str, Any]]:
        """Get workflows for a form"""
        logger.debug(f"Fetching workflows for form {form_id}")
        try:
            result = self._make_request('GET', f'forms/{form_id}/workflows')
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch workflows: {e}")
            return []
    
    def get_form_views(self, form_id: str) -> List[Dict[str, Any]]:
        """Get views for a form"""
        logger.debug(f"Fetching views for form {form_id}")
        try:
            result = self._make_request('GET', f'forms/{form_id}/views')
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch views: {e}")
            return []
    
    def get_form_notifications(self, form_id: str) -> List[Dict[str, Any]]:
        """Get notifications for a form"""
        logger.debug(f"Fetching notifications for form {form_id}")
        try:
            result = self._make_request('GET', f'forms/{form_id}/notifications')
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Could not fetch notifications: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            logger.info("Testing Cognito Forms connection...")
            # Try to get forms with limit 1 to test connection
            self._make_request('GET', 'forms', params={'$top': 1})
            logger.info(f"✅ Cognito Forms connection successful for {self.organization}")
            return True
        except Exception as e:
            logger.error(f"❌ Cognito Forms connection failed: {e}")
            return False