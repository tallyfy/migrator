"""
Jotform API Client
Handles all interactions with Jotform API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)


class JotformClient:
    """Client for Jotform API operations"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize Jotform API client
        
        Args:
            api_key: Jotform API key
            base_url: Base URL for Jotform API (EU or US)
        """
        self.api_key = api_key or os.getenv('JOTFORM_API_KEY')
        
        # Determine region (EU or US)
        region = os.getenv('JOTFORM_REGION', 'US').upper()
        if region == 'EU':
            default_url = 'https://eu-api.jotform.com'
        else:
            default_url = 'https://api.jotform.com'
        
        self.base_url = base_url or os.getenv('JOTFORM_BASE_URL', default_url)
        
        if not self.api_key:
            raise ValueError("Jotform API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        logger.info(f"Jotform client initialized for {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request with retries"""
        url = f"{self.base_url}/{endpoint}"
        
        # Add API key to URL params for GET requests
        if method == 'GET':
            if 'params' not in kwargs:
                kwargs['params'] = {}
            kwargs['params']['apiKey'] = self.api_key
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 429:  # Rate limited
                    wait_time = 60
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                # Jotform returns data in 'content' field
                return data.get('content', data)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    
    def get_forms(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all forms"""
        logger.info("Fetching Jotform forms...")
        forms = []
        offset = 0
        
        while True:
            batch = self._make_request('GET', 'user/forms', params={
                'limit': min(limit, 100),
                'offset': offset,
                'orderby': 'created_at'
            })
            
            if isinstance(batch, list):
                forms.extend(batch)
                if len(batch) < 100 or len(forms) >= limit:
                    break
                offset += 100
            else:
                break
        
        logger.info(f"Found {len(forms)} forms")
        return forms[:limit]
    
    def get_form_details(self, form_id: str) -> Dict[str, Any]:
        """Get form details including all questions"""
        logger.debug(f"Fetching form {form_id}")
        return self._make_request('GET', f'form/{form_id}')
    
    def get_form_questions(self, form_id: str) -> Dict[str, Any]:
        """Get form questions/fields"""
        logger.debug(f"Fetching questions for form {form_id}")
        return self._make_request('GET', f'form/{form_id}/questions')
    
    def get_form_properties(self, form_id: str) -> Dict[str, Any]:
        """Get form properties"""
        logger.debug(f"Fetching properties for form {form_id}")
        return self._make_request('GET', f'form/{form_id}/properties')
    
    def get_form_submissions(self, form_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get form submissions"""
        logger.debug(f"Fetching submissions for form {form_id}")
        submissions = []
        offset = 0
        
        while True:
            batch = self._make_request('GET', f'form/{form_id}/submissions', params={
                'limit': min(limit, 100),
                'offset': offset,
                'orderby': 'created_at'
            })
            
            if isinstance(batch, list):
                submissions.extend(batch)
                if len(batch) < 100 or len(submissions) >= limit:
                    break
                offset += 100
            else:
                break
        
        return submissions[:limit]
    
    def get_submission_details(self, submission_id: str) -> Dict[str, Any]:
        """Get submission details"""
        logger.debug(f"Fetching submission {submission_id}")
        return self._make_request('GET', f'submission/{submission_id}')
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get user account information"""
        logger.info("Fetching user info...")
        return self._make_request('GET', 'user')
    
    def get_user_submissions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all user submissions"""
        logger.info("Fetching all submissions...")
        submissions = []
        offset = 0
        
        while True:
            batch = self._make_request('GET', 'user/submissions', params={
                'limit': min(limit, 100),
                'offset': offset
            })
            
            if isinstance(batch, list):
                submissions.extend(batch)
                if len(batch) < 100 or len(submissions) >= limit:
                    break
                offset += 100
            else:
                break
        
        logger.info(f"Found {len(submissions)} submissions")
        return submissions[:limit]
    
    def get_form_webhooks(self, form_id: str) -> List[Dict[str, Any]]:
        """Get webhooks for a form"""
        logger.debug(f"Fetching webhooks for form {form_id}")
        result = self._make_request('GET', f'form/{form_id}/webhooks')
        return result if isinstance(result, list) else []
    
    def get_form_reports(self, form_id: str) -> List[Dict[str, Any]]:
        """Get reports for a form"""
        logger.debug(f"Fetching reports for form {form_id}")
        result = self._make_request('GET', f'form/{form_id}/reports')
        return result if isinstance(result, list) else []
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get teams if available"""
        logger.info("Fetching teams...")
        try:
            result = self._make_request('GET', 'user/teams')
            teams = result if isinstance(result, list) else []
            logger.info(f"Found {len(teams)} teams")
            return teams
        except Exception as e:
            logger.warning(f"Could not fetch teams: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            logger.info("Testing Jotform connection...")
            user_info = self._make_request('GET', 'user')
            logger.info(f"✅ Jotform connection successful - Account: {user_info.get('username', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Jotform connection failed: {e}")
            return False