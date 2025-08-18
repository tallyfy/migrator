#!/usr/bin/env python3
"""
Production-Grade Typeform API Client
Implements actual Typeform API with proper authentication, rate limiting, and error handling
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


class TypeformRateLimitError(Exception):
    """Typeform rate limit exceeded"""
    pass


class TypeformAuthError(Exception):
    """Typeform authentication failed"""
    pass


class TypeformFieldType(str, Enum):
    """Typeform field types"""
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    MULTIPLE_CHOICE = "multiple_choice"
    PICTURE_CHOICE = "picture_choice"
    DROPDOWN = "dropdown"
    YES_NO = "yes_no"
    LEGAL = "legal"
    EMAIL = "email"
    WEBSITE = "website"
    NUMBER = "number"
    DATE = "date"
    PHONE_NUMBER = "phone_number"
    FILE_UPLOAD = "file_upload"
    PAYMENT = "payment"
    RATING = "rating"
    OPINION_SCALE = "opinion_scale"
    NPS = "nps"
    STATEMENT = "statement"
    GROUP = "group"
    MATRIX = "matrix"
    RANKING = "ranking"


class TypeformLogicType(str, Enum):
    """Typeform logic jump types"""
    FIELD = "field"
    HIDDEN = "hidden"
    VARIABLE = "variable"
    CONSTANT = "constant"
    END = "end"
    ALWAYS = "always"


class TypeformProductionClient:
    """
    Production Typeform API client with actual endpoints
    Implements Typeform API
    """
    
    BASE_URL = "https://api.typeform.com"
    
    # Typeform rate limits
    RATE_LIMITS = {
        'requests_per_minute': 120,  # 2 requests per second average
        'burst_limit': 10
    }
    
    def __init__(self):
        """Initialize Typeform client with actual authentication"""
        self.access_token = os.getenv('TYPEFORM_ACCESS_TOKEN')
        
        if not self.access_token:
            raise TypeformAuthError("TYPEFORM_ACCESS_TOKEN required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.minute_start = datetime.now()
        self.requests_this_minute = 0
        
        # Cache for frequently used data
        self.form_cache = {}
        self.workspace_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce Typeform rate limits"""
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
        
        self.requests_this_minute += 1
        
        # Small delay to avoid bursts
        time.sleep(0.5)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, TypeformRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to Typeform API"""
        self._check_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
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
                retry_after = int(response.headers.get('X-Rate-Limit-Reset', 60))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise TypeformRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                return response.json()
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise TypeformAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL TYPEFORM API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Get user info to test
            user = self._make_request('GET', '/me')
            self.logger.info(f"Connected to Typeform as {user.get('alias', 'Unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        return self._make_request('GET', '/me')
    
    def get_workspaces(self, page: int = 1, page_size: int = 200) -> Dict[str, Any]:
        """Get all workspaces"""
        params = {
            'page': page,
            'page_size': page_size
        }
        
        response = self._make_request('GET', '/workspaces', params)
        
        # Cache workspaces
        if response and 'items' in response:
            for workspace in response['items']:
                self.workspace_cache[workspace['id']] = workspace
        
        return response
    
    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Get detailed workspace information"""
        # Check cache first
        if workspace_id in self.workspace_cache:
            return self.workspace_cache[workspace_id]
        
        workspace = self._make_request('GET', f'/workspaces/{workspace_id}')
        
        if workspace:
            self.workspace_cache[workspace_id] = workspace
        
        return workspace
    
    def get_forms(self, workspace_id: str = None, page: int = 1, 
                 page_size: int = 200) -> Dict[str, Any]:
        """Get all forms"""
        params = {
            'page': page,
            'page_size': page_size
        }
        
        if workspace_id:
            params['workspace_id'] = workspace_id
        
        response = self._make_request('GET', '/forms', params)
        
        # Cache forms
        if response and 'items' in response:
            for form in response['items']:
                self.form_cache[form['id']] = form
        
        return response
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """Get detailed form information"""
        # Check cache first
        if form_id in self.form_cache:
            # Get full details even if cached (cache has limited info)
            pass
        
        form = self._make_request('GET', f'/forms/{form_id}')
        
        if form:
            self.form_cache[form_id] = form
        
        return form
    
    def get_form_responses(self, form_id: str, page_size: int = 1000, 
                          since: datetime = None, until: datetime = None,
                          after: str = None) -> Dict[str, Any]:
        """Get form responses"""
        params = {
            'page_size': page_size
        }
        
        if since:
            params['since'] = since.isoformat()
        
        if until:
            params['until'] = until.isoformat()
        
        if after:
            params['after'] = after  # Token for pagination
        
        return self._make_request('GET', f'/forms/{form_id}/responses', params)
    
    def get_themes(self, page: int = 1, page_size: int = 200) -> Dict[str, Any]:
        """Get all themes"""
        params = {
            'page': page,
            'page_size': page_size
        }
        
        return self._make_request('GET', '/themes', params)
    
    def get_theme(self, theme_id: str) -> Dict[str, Any]:
        """Get detailed theme information"""
        return self._make_request('GET', f'/themes/{theme_id}')
    
    def get_images(self, page: int = 1, page_size: int = 200) -> Dict[str, Any]:
        """Get all images in account"""
        params = {
            'page': page,
            'page_size': page_size
        }
        
        return self._make_request('GET', '/images', params)
    
    def get_webhooks(self, form_id: str) -> Dict[str, Any]:
        """Get webhooks for a form"""
        return self._make_request('GET', f'/forms/{form_id}/webhooks')
    
    # ============= FORM STRUCTURE ANALYSIS =============
    
    def analyze_form_complexity(self, form_id: str) -> Dict[str, Any]:
        """
        Analyze form complexity for transformation
        Typeform has complex logic and multiple question types
        """
        form = self.get_form(form_id)
        
        analysis = {
            'field_count': len(form.get('fields', [])),
            'has_logic': False,
            'has_variables': False,
            'has_hidden_fields': False,
            'has_calculator': False,
            'has_payment': False,
            'has_file_upload': False,
            'logic_jumps': 0,
            'complexity_score': 0,
            'field_types': {}
        }
        
        # Analyze fields
        for field in form.get('fields', []):
            field_type = field.get('type')
            
            # Count field types
            if field_type not in analysis['field_types']:
                analysis['field_types'][field_type] = 0
            analysis['field_types'][field_type] += 1
            
            # Check for complex field types
            if field_type == TypeformFieldType.PAYMENT.value:
                analysis['has_payment'] = True
                analysis['complexity_score'] += 10
            elif field_type == TypeformFieldType.FILE_UPLOAD.value:
                analysis['has_file_upload'] = True
                analysis['complexity_score'] += 5
            elif field_type in [TypeformFieldType.MATRIX.value, TypeformFieldType.RANKING.value]:
                analysis['complexity_score'] += 3
        
        # Check logic
        if form.get('logic'):
            analysis['has_logic'] = True
            
            # Count logic jumps
            for logic_item in form.get('logic', []):
                if logic_item.get('actions'):
                    analysis['logic_jumps'] += len(logic_item['actions'])
            
            analysis['complexity_score'] += analysis['logic_jumps'] * 2
        
        # Check variables
        if form.get('variables'):
            analysis['has_variables'] = True
            analysis['variable_count'] = len(form['variables'])
            analysis['complexity_score'] += analysis['variable_count'] * 2
        
        # Check hidden fields
        if form.get('hidden'):
            analysis['has_hidden_fields'] = True
            analysis['hidden_field_count'] = len(form['hidden'])
            analysis['complexity_score'] += analysis['hidden_field_count']
        
        # Check calculator
        if form.get('settings', {}).get('is_calculator'):
            analysis['has_calculator'] = True
            analysis['complexity_score'] += 10
        
        # Add base complexity
        analysis['complexity_score'] += analysis['field_count']
        
        # Recommend transformation strategy
        if analysis['field_count'] <= 10 and not analysis['has_logic']:
            analysis['recommended_strategy'] = 'simple_form'
        elif analysis['field_count'] <= 20 and not analysis['has_logic']:
            analysis['recommended_strategy'] = 'kickoff_form'
        elif analysis['has_logic']:
            analysis['recommended_strategy'] = 'conditional_workflow'
        else:
            analysis['recommended_strategy'] = 'multi_step_workflow'
        
        return analysis
    
    def get_form_logic(self, form_id: str) -> List[Dict[str, Any]]:
        """Get logic jumps for a form"""
        form = self.get_form(form_id)
        return form.get('logic', [])
    
    def get_form_variables(self, form_id: str) -> Dict[str, Any]:
        """Get variables and calculations for a form"""
        form = self.get_form(form_id)
        return form.get('variables', {})
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_forms(self, workspace_id: str = None, 
                       batch_size: int = 200) -> Generator[List[Dict], None, None]:
        """Get forms in batches"""
        page = 1
        
        while True:
            response = self.get_forms(
                workspace_id=workspace_id,
                page=page,
                page_size=batch_size
            )
            
            if not response or 'items' not in response:
                break
            
            forms = response['items']
            if not forms:
                break
            
            yield forms
            
            # Check if more pages
            if response.get('page_count', 0) <= page:
                break
            
            page += 1
            time.sleep(1)  # Rate limit pause
    
    def batch_get_responses(self, form_id: str, 
                           batch_size: int = 1000) -> Generator[List[Dict], None, None]:
        """Get form responses in batches"""
        after = None
        
        while True:
            response = self.get_form_responses(
                form_id=form_id,
                page_size=batch_size,
                after=after
            )
            
            if not response or 'items' not in response:
                break
            
            responses = response['items']
            if not responses:
                break
            
            yield responses
            
            # Get pagination token
            after = response.get('after')
            if not after:
                break
            
            time.sleep(1)  # Rate limit pause
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Typeform data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'user': self.get_current_user(),
            'workspaces': [],
            'forms': [],
            'themes': [],
            'total_forms': 0,
            'total_responses': 0,
            'total_fields': 0
        }
        
        # Get workspaces
        self.logger.info("Fetching workspaces...")
        workspace_response = self.get_workspaces()
        workspaces = workspace_response.get('items', [])
        data['workspaces'] = workspaces
        
        # Get themes
        self.logger.info("Fetching themes...")
        theme_response = self.get_themes()
        data['themes'] = theme_response.get('items', [])
        
        # Process each workspace
        for workspace in workspaces:
            self.logger.info(f"Processing workspace: {workspace['name']}")
            
            # Get forms for workspace
            for form_batch in self.batch_get_forms(workspace_id=workspace['id']):
                for form_summary in form_batch:
                    self.logger.info(f"  Processing form: {form_summary['title']}")
                    
                    # Get full form details
                    form_data = self.get_form(form_summary['id'])
                    
                    # Analyze complexity
                    form_data['complexity_analysis'] = self.analyze_form_complexity(form_summary['id'])
                    
                    # Get logic
                    form_data['logic'] = self.get_form_logic(form_summary['id'])
                    
                    # Get variables
                    form_data['variables'] = self.get_form_variables(form_summary['id'])
                    
                    # Get webhooks
                    form_data['webhooks'] = self.get_webhooks(form_summary['id'])
                    
                    # Get responses
                    form_data['responses'] = []
                    response_count = 0
                    
                    for response_batch in self.batch_get_responses(form_summary['id']):
                        form_data['responses'].extend(response_batch)
                        response_count += len(response_batch)
                        
                        # Limit responses to avoid huge exports
                        if response_count >= 5000:
                            self.logger.warning(f"    Limiting responses to 5000 for form {form_summary['id']}")
                            break
                    
                    data['total_responses'] += response_count
                    data['total_fields'] += len(form_data.get('fields', []))
                    
                    data['forms'].append(form_data)
                    data['total_forms'] += 1
                    
                    self.logger.info(f"    Processed {response_count} responses")
                    
                    # Rate limit pause
                    time.sleep(2)
        
        self.logger.info(f"Export complete: {data['total_forms']} forms, {data['total_responses']} responses")
        
        return data
    
    # ============= FIELD PARSING =============
    
    def parse_response_answers(self, response: Dict[str, Any], form: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse response answers based on field types
        """
        parsed = {}
        field_map = {field['id']: field for field in form.get('fields', [])}
        
        for answer in response.get('answers', []):
            field_id = answer.get('field', {}).get('id')
            field = field_map.get(field_id, {})
            field_type = field.get('type')
            
            if field_type == TypeformFieldType.MULTIPLE_CHOICE.value:
                # Multiple choice can be single or multi-select
                if answer.get('choice'):
                    parsed[field_id] = answer['choice'].get('label')
                elif answer.get('choices'):
                    parsed[field_id] = [c.get('label') for c in answer['choices'].get('labels', [])]
            
            elif field_type == TypeformFieldType.PICTURE_CHOICE.value:
                # Picture choice
                if answer.get('choice'):
                    parsed[field_id] = answer['choice'].get('label')
                elif answer.get('choices'):
                    parsed[field_id] = [c.get('label') for c in answer['choices'].get('labels', [])]
            
            elif field_type in [TypeformFieldType.SHORT_TEXT.value, TypeformFieldType.LONG_TEXT.value]:
                parsed[field_id] = answer.get('text')
            
            elif field_type == TypeformFieldType.EMAIL.value:
                parsed[field_id] = answer.get('email')
            
            elif field_type == TypeformFieldType.NUMBER.value:
                parsed[field_id] = answer.get('number')
            
            elif field_type == TypeformFieldType.DATE.value:
                parsed[field_id] = answer.get('date')
            
            elif field_type == TypeformFieldType.PHONE_NUMBER.value:
                parsed[field_id] = answer.get('phone_number')
            
            elif field_type == TypeformFieldType.YES_NO.value:
                parsed[field_id] = answer.get('boolean')
            
            elif field_type == TypeformFieldType.FILE_UPLOAD.value:
                parsed[field_id] = answer.get('file_url')
            
            elif field_type == TypeformFieldType.PAYMENT.value:
                payment = answer.get('payment', {})
                parsed[field_id] = {
                    'amount': payment.get('amount'),
                    'status': payment.get('status')
                }
            
            elif field_type == TypeformFieldType.RATING.value:
                parsed[field_id] = answer.get('number')
            
            elif field_type == TypeformFieldType.OPINION_SCALE.value:
                parsed[field_id] = answer.get('number')
            
            elif field_type == TypeformFieldType.NPS.value:
                parsed[field_id] = answer.get('number')
            
            else:
                # Default: store raw answer
                parsed[field_id] = answer
        
        # Add calculated variables if present
        if response.get('variables'):
            parsed['_variables'] = response['variables']
        
        # Add hidden fields if present
        if response.get('hidden'):
            parsed['_hidden'] = response['hidden']
        
        return parsed
    
    # ============= CREATE OPERATIONS =============
    
    def create_form(self, title: str, workspace_id: str = None, 
                   fields: List[Dict] = None) -> Dict[str, Any]:
        """Create a new form"""
        data = {
            'title': title,
            'type': 'form'
        }
        
        if workspace_id:
            data['workspace'] = {'href': f'https://api.typeform.com/workspaces/{workspace_id}'}
        
        if fields:
            data['fields'] = fields
        
        return self._make_request('POST', '/forms', data=data)
    
    def create_webhook(self, form_id: str, url: str, enabled: bool = True) -> Dict[str, Any]:
        """Create webhook for form"""
        data = {
            'url': url,
            'enabled': enabled
        }
        
        return self._make_request('PUT', f'/forms/{form_id}/webhooks/{form_id}', data=data)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = TypeformProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Typeform")
        
        # Get current user
        user = client.get_current_user()
        print(f"User: {user.get('alias', 'Unknown')}")
        print(f"Email: {user.get('email', 'Unknown')}")
        
        # Get workspaces
        workspace_response = client.get_workspaces()
        workspaces = workspace_response.get('items', [])
        print(f"\nFound {workspace_response.get('total_items', 0)} workspaces")
        
        if workspaces:
            workspace = workspaces[0]
            print(f"\nWorkspace: {workspace['name']}")
            
            # Get forms
            form_response = client.get_forms(workspace_id=workspace['id'], page_size=5)
            forms = form_response.get('items', [])
            print(f"Forms: {form_response.get('total_items', 0)}")
            
            if forms:
                form_summary = forms[0]
                print(f"\nForm: {form_summary['title']}")
                
                # Get full form details
                form = client.get_form(form_summary['id'])
                print(f"Fields: {len(form.get('fields', []))}")
                
                # Analyze complexity
                analysis = client.analyze_form_complexity(form_summary['id'])
                print(f"\nComplexity analysis:")
                print(f"  - Field count: {analysis['field_count']}")
                print(f"  - Has logic: {analysis['has_logic']}")
                print(f"  - Has variables: {analysis['has_variables']}")
                print(f"  - Complexity score: {analysis['complexity_score']}")
                print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
                
                # Get responses
                response_data = client.get_form_responses(form_summary['id'], page_size=5)
                responses = response_data.get('items', [])
                print(f"\nResponses: {response_data.get('total_items', 0)}")
                
                if responses:
                    response = responses[0]
                    parsed = client.parse_response_answers(response, form)
                    print(f"  First response has {len(parsed)} answers")
    
    print("\n✅ Production Typeform client ready!")