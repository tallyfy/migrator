#!/usr/bin/env python3
"""
Production-Grade JotForm API Client
Implements actual JotForm API v1 with proper authentication, rate limiting, and error handling
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


class JotFormRateLimitError(Exception):
    """JotForm rate limit exceeded"""
    pass


class JotFormAuthError(Exception):
    """JotForm authentication failed"""
    pass


class JotFormFieldType(str, Enum):
    """JotForm field types"""
    TEXT = "control_textbox"
    TEXTAREA = "control_textarea"
    DROPDOWN = "control_dropdown"
    RADIO = "control_radio"
    CHECKBOX = "control_checkbox"
    NUMBER = "control_number"
    EMAIL = "control_email"
    PHONE = "control_phone"
    DATE = "control_datetime"
    TIME = "control_time"
    FILE = "control_fileupload"
    SIGNATURE = "control_signature"
    PAYMENT = "control_payment"
    MATRIX = "control_matrix"
    RATING = "control_rating"
    SLIDER = "control_slider"
    SPINNER = "control_spinner"
    RANGE = "control_range"
    ADDRESS = "control_address"
    FULLNAME = "control_fullname"
    APPOINTMENT = "control_appointment"
    WIDGET = "control_widget"
    CAPTCHA = "control_captcha"
    PAGE_BREAK = "control_pagebreak"
    HEADING = "control_head"
    IMAGE = "control_image"
    BUTTON = "control_button"


class JotFormProductionClient:
    """
    Production JotForm API client with actual endpoints
    Implements JotForm API v1
    """
    
    BASE_URL = "https://api.jotform.com"
    EU_BASE_URL = "https://eu-api.jotform.com"  # EU region endpoint
    
    # JotForm rate limits
    RATE_LIMITS = {
        'daily_limit': 10000,  # 10,000 requests per day
        'requests_per_second': 5
    }
    
    def __init__(self):
        """Initialize JotForm client with actual authentication"""
        self.api_key = os.getenv('JOTFORM_API_KEY')
        self.region = os.getenv('JOTFORM_REGION', 'US').upper()
        
        if not self.api_key:
            raise JotFormAuthError("JOTFORM_API_KEY required")
        
        # Select base URL based on region
        if self.region == 'EU':
            self.base_url = self.EU_BASE_URL
        else:
            self.base_url = self.BASE_URL
        
        self.session = requests.Session()
        self.session.params = {'apiKey': self.api_key}
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.request_times = []
        self.daily_requests = 0
        self.day_start = datetime.now()
        
        # Cache for frequently used data
        self.form_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce JotForm rate limits"""
        now = datetime.now()
        
        # Reset daily counter
        if now - self.day_start > timedelta(days=1):
            self.daily_requests = 0
            self.day_start = now
        
        # Check daily limit
        if self.daily_requests >= self.RATE_LIMITS['daily_limit']:
            wait_time = (timedelta(days=1) - (now - self.day_start)).seconds
            self.logger.warning(f"Daily limit reached. Waiting {wait_time}s")
            time.sleep(wait_time)
            self.daily_requests = 0
            self.day_start = datetime.now()
        
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
        self.daily_requests += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, JotFormRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to JotForm API"""
        self._check_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        # Merge params with API key
        if params is None:
            params = {}
        params['apiKey'] = self.api_key
        
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
                self.logger.warning("Rate limited. Waiting 60s")
                time.sleep(60)
                raise JotFormRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                result = response.json()
                # JotForm returns data in 'content' key
                return result.get('content', result)
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise JotFormAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL JOTFORM API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # Get user info to test
            user = self._make_request('GET', '/user')
            self.logger.info(f"Connected to JotForm as {user.get('username', 'Unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        return self._make_request('GET', '/user')
    
    def get_usage(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return self._make_request('GET', '/user/usage')
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """Get all folders"""
        return self._make_request('GET', '/user/folders')
    
    def get_forms(self, offset: int = 0, limit: int = 100, 
                 filter: Dict = None, order_by: str = None) -> List[Dict[str, Any]]:
        """Get all forms"""
        params = {
            'offset': offset,
            'limit': limit
        }
        
        if filter:
            params['filter'] = json.dumps(filter)
        
        if order_by:
            params['orderby'] = order_by
        
        forms = self._make_request('GET', '/user/forms', params)
        
        # Cache forms
        for form in forms:
            self.form_cache[form['id']] = form
        
        return forms
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """Get detailed form information"""
        # Check cache first
        if form_id in self.form_cache:
            # Get full details even if cached
            pass
        
        form = self._make_request('GET', f'/form/{form_id}')
        
        if form:
            self.form_cache[form_id] = form
        
        return form
    
    def get_form_questions(self, form_id: str) -> Dict[str, Any]:
        """Get form questions/fields"""
        return self._make_request('GET', f'/form/{form_id}/questions')
    
    def get_form_properties(self, form_id: str) -> Dict[str, Any]:
        """Get form properties and settings"""
        return self._make_request('GET', f'/form/{form_id}/properties')
    
    def get_form_submissions(self, form_id: str, offset: int = 0, limit: int = 100,
                           filter: Dict = None, order_by: str = None) -> List[Dict[str, Any]]:
        """Get form submissions"""
        params = {
            'offset': offset,
            'limit': limit
        }
        
        if filter:
            params['filter'] = json.dumps(filter)
        
        if order_by:
            params['orderby'] = order_by
        
        return self._make_request('GET', f'/form/{form_id}/submissions', params)
    
    def get_submission(self, submission_id: str) -> Dict[str, Any]:
        """Get detailed submission information"""
        return self._make_request('GET', f'/submission/{submission_id}')
    
    def get_form_files(self, form_id: str) -> List[Dict[str, Any]]:
        """Get files uploaded to a form"""
        return self._make_request('GET', f'/form/{form_id}/files')
    
    def get_form_webhooks(self, form_id: str) -> List[Dict[str, Any]]:
        """Get webhooks for a form"""
        return self._make_request('GET', f'/form/{form_id}/webhooks')
    
    def get_form_reports(self, form_id: str) -> List[Dict[str, Any]]:
        """Get reports for a form"""
        return self._make_request('GET', f'/form/{form_id}/reports')
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get teams/collaborators"""
        return self._make_request('GET', '/user/teams')
    
    def get_history(self, action: str = None, date: str = None, 
                   sort_by: str = None, start_date: str = None, 
                   end_date: str = None) -> List[Dict[str, Any]]:
        """Get account history"""
        params = {}
        
        if action:
            params['action'] = action
        if date:
            params['date'] = date
        if sort_by:
            params['sortBy'] = sort_by
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        
        return self._make_request('GET', '/user/history', params)
    
    # ============= FORM STRUCTURE ANALYSIS =============
    
    def analyze_form_complexity(self, form_id: str) -> Dict[str, Any]:
        """
        Analyze form complexity for transformation
        JotForm has many field types and conditions
        """
        form = self.get_form(form_id)
        questions = self.get_form_questions(form_id)
        properties = self.get_form_properties(form_id)
        
        analysis = {
            'field_count': len(questions),
            'has_conditions': False,
            'has_calculations': False,
            'has_payment': False,
            'has_appointment': False,
            'has_file_upload': False,
            'has_page_breaks': False,
            'page_count': 1,
            'complexity_score': 0,
            'field_types': {}
        }
        
        # Analyze questions/fields
        for qid, question in questions.items():
            if not isinstance(question, dict):
                continue
            
            field_type = question.get('type')
            
            # Count field types
            if field_type not in analysis['field_types']:
                analysis['field_types'][field_type] = 0
            analysis['field_types'][field_type] += 1
            
            # Check for complex field types
            if field_type == JotFormFieldType.PAYMENT.value:
                analysis['has_payment'] = True
                analysis['complexity_score'] += 10
            elif field_type == JotFormFieldType.FILE.value:
                analysis['has_file_upload'] = True
                analysis['complexity_score'] += 5
            elif field_type == JotFormFieldType.APPOINTMENT.value:
                analysis['has_appointment'] = True
                analysis['complexity_score'] += 8
            elif field_type == JotFormFieldType.PAGE_BREAK.value:
                analysis['has_page_breaks'] = True
                analysis['page_count'] += 1
                analysis['complexity_score'] += 2
            elif field_type in [JotFormFieldType.MATRIX.value, JotFormFieldType.WIDGET.value]:
                analysis['complexity_score'] += 3
        
        # Check conditions
        if properties.get('conditions'):
            conditions = json.loads(properties['conditions']) if isinstance(properties['conditions'], str) else properties['conditions']
            if conditions:
                analysis['has_conditions'] = True
                analysis['condition_count'] = len(conditions)
                analysis['complexity_score'] += len(conditions) * 3
        
        # Check calculations
        if properties.get('calculationSettings'):
            analysis['has_calculations'] = True
            analysis['complexity_score'] += 5
        
        # Add base complexity
        analysis['complexity_score'] += analysis['field_count']
        analysis['complexity_score'] += (analysis['page_count'] - 1) * 5
        
        # Recommend transformation strategy
        if analysis['field_count'] <= 10 and not analysis['has_conditions']:
            analysis['recommended_strategy'] = 'simple_form'
        elif analysis['field_count'] <= 20 and not analysis['has_conditions']:
            analysis['recommended_strategy'] = 'kickoff_form'
        elif analysis['has_page_breaks']:
            analysis['recommended_strategy'] = 'multi_step_workflow'
        elif analysis['has_conditions']:
            analysis['recommended_strategy'] = 'conditional_workflow'
        else:
            analysis['recommended_strategy'] = 'complex_workflow'
        
        return analysis
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_forms(self, batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get forms in batches"""
        offset = 0
        
        while True:
            forms = self.get_forms(offset=offset, limit=batch_size)
            
            if not forms:
                break
            
            yield forms
            
            if len(forms) < batch_size:
                break
            
            offset += batch_size
            time.sleep(0.5)  # Rate limit pause
    
    def batch_get_submissions(self, form_id: str, 
                            batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get form submissions in batches"""
        offset = 0
        
        while True:
            submissions = self.get_form_submissions(
                form_id=form_id,
                offset=offset,
                limit=batch_size
            )
            
            if not submissions:
                break
            
            yield submissions
            
            if len(submissions) < batch_size:
                break
            
            offset += batch_size
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete JotForm data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'user': self.get_user(),
            'folders': [],
            'forms': [],
            'teams': [],
            'total_forms': 0,
            'total_submissions': 0,
            'total_fields': 0
        }
        
        # Get folders
        self.logger.info("Fetching folders...")
        data['folders'] = self.get_folders()
        
        # Get teams
        self.logger.info("Fetching teams...")
        data['teams'] = self.get_teams()
        
        # Get forms
        self.logger.info("Fetching forms...")
        
        for form_batch in self.batch_get_forms():
            for form_summary in form_batch:
                self.logger.info(f"Processing form: {form_summary['title']}")
                
                # Get full form details
                form_data = self.get_form(form_summary['id'])
                
                # Get questions
                form_data['questions'] = self.get_form_questions(form_summary['id'])
                data['total_fields'] += len(form_data['questions'])
                
                # Get properties
                form_data['properties'] = self.get_form_properties(form_summary['id'])
                
                # Analyze complexity
                form_data['complexity_analysis'] = self.analyze_form_complexity(form_summary['id'])
                
                # Get webhooks
                form_data['webhooks'] = self.get_form_webhooks(form_summary['id'])
                
                # Get reports
                form_data['reports'] = self.get_form_reports(form_summary['id'])
                
                # Get submissions
                form_data['submissions'] = []
                submission_count = 0
                
                for submission_batch in self.batch_get_submissions(form_summary['id']):
                    form_data['submissions'].extend(submission_batch)
                    submission_count += len(submission_batch)
                    
                    # Limit submissions to avoid huge exports
                    if submission_count >= 5000:
                        self.logger.warning(f"  Limiting submissions to 5000 for form {form_summary['id']}")
                        break
                
                data['total_submissions'] += submission_count
                
                # Get files
                form_data['files'] = self.get_form_files(form_summary['id'])
                
                data['forms'].append(form_data)
                data['total_forms'] += 1
                
                self.logger.info(f"  Processed {submission_count} submissions")
                
                # Rate limit pause
                time.sleep(1)
        
        self.logger.info(f"Export complete: {data['total_forms']} forms, {data['total_submissions']} submissions")
        
        return data
    
    # ============= FIELD PARSING =============
    
    def parse_submission_answers(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse submission answers based on field types
        """
        parsed = {}
        answers = submission.get('answers', {})
        
        for field_id, answer in answers.items():
            if isinstance(answer, dict):
                # Complex field types return objects
                if 'answer' in answer:
                    parsed[field_id] = answer['answer']
                elif 'prettyFormat' in answer:
                    parsed[field_id] = answer['prettyFormat']
                else:
                    # Store entire answer object for complex types
                    parsed[field_id] = answer
            else:
                # Simple field types return values directly
                parsed[field_id] = answer
        
        # Add metadata
        parsed['_metadata'] = {
            'submission_id': submission.get('id'),
            'form_id': submission.get('form_id'),
            'created_at': submission.get('created_at'),
            'updated_at': submission.get('updated_at'),
            'ip': submission.get('ip'),
            'status': submission.get('status')
        }
        
        return parsed
    
    # ============= CREATE OPERATIONS =============
    
    def create_form(self, questions: Dict, properties: Dict = None) -> Dict[str, Any]:
        """Create a new form"""
        data = {
            'questions': questions
        }
        
        if properties:
            data['properties'] = properties
        
        return self._make_request('POST', '/user/forms', data=data)
    
    def create_submission(self, form_id: str, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new submission"""
        return self._make_request('POST', f'/form/{form_id}/submissions', data=submission)
    
    def create_webhook(self, form_id: str, webhook_url: str) -> Dict[str, Any]:
        """Create webhook for form"""
        data = {
            'webhookURL': webhook_url
        }
        
        return self._make_request('POST', f'/form/{form_id}/webhooks', data=data)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = JotFormProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to JotForm")
        
        # Get user
        user = client.get_user()
        print(f"User: {user.get('username', 'Unknown')}")
        print(f"Email: {user.get('email', 'Unknown')}")
        
        # Get usage
        usage = client.get_usage()
        print(f"\nAPI Usage: {usage.get('requests', 0)} requests")
        
        # Get folders
        folders = client.get_folders()
        print(f"\nFolders: {len(folders)}")
        
        # Get forms
        forms = client.get_forms(limit=5)
        print(f"Forms: {len(forms)}")
        
        if forms:
            form = forms[0]
            print(f"\nForm: {form['title']}")
            print(f"Status: {form.get('status', 'Unknown')}")
            print(f"Submissions: {form.get('count', 0)}")
            
            # Get full form details
            full_form = client.get_form(form['id'])
            
            # Get questions
            questions = client.get_form_questions(form['id'])
            print(f"Questions: {len(questions)}")
            
            # Analyze complexity
            analysis = client.analyze_form_complexity(form['id'])
            print(f"\nComplexity analysis:")
            print(f"  - Field count: {analysis['field_count']}")
            print(f"  - Has conditions: {analysis['has_conditions']}")
            print(f"  - Has payment: {analysis['has_payment']}")
            print(f"  - Page count: {analysis['page_count']}")
            print(f"  - Complexity score: {analysis['complexity_score']}")
            print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
            
            # Get submissions
            submissions = client.get_form_submissions(form['id'], limit=5)
            print(f"\nSubmissions: {len(submissions)}")
            
            if submissions:
                submission = submissions[0]
                parsed = client.parse_submission_answers(submission)
                print(f"  First submission has {len(parsed)} fields")
    
    print("\n✅ Production JotForm client ready!")