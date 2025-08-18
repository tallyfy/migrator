#!/usr/bin/env python3
"""
Production-Grade Google Forms API Client
Implements actual Google Forms API v1 with proper authentication, rate limiting, and error handling
"""

import os
import time
import json
import pickle
from typing import Dict, List, Any, Optional, Generator, Union
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from enum import Enum


class GoogleFormsRateLimitError(Exception):
    """Google Forms rate limit exceeded"""
    pass


class GoogleFormsAuthError(Exception):
    """Google Forms authentication failed"""
    pass


class GoogleFormsItemType(str, Enum):
    """Google Forms item types"""
    TEXT = "TEXT"
    PARAGRAPH_TEXT = "PARAGRAPH_TEXT"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    CHECKBOX = "CHECKBOX"
    DROPDOWN = "DROPDOWN"
    FILE_UPLOAD = "FILE_UPLOAD"
    SCALE = "SCALE"
    GRID = "GRID"
    CHECKBOX_GRID = "CHECKBOX_GRID"
    DATE = "DATE"
    TIME = "TIME"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    PAGE_BREAK = "PAGE_BREAK"
    SECTION_HEADER = "SECTION_HEADER"


class GoogleFormsProductionClient:
    """
    Production Google Forms API client with actual endpoints
    Implements Google Forms API v1
    """
    
    # Google API rate limits
    RATE_LIMITS = {
        'requests_per_minute': 300,
        'requests_per_second': 10
    }
    
    # OAuth2 scopes required
    SCOPES = [
        'https://www.googleapis.com/auth/forms.body',
        'https://www.googleapis.com/auth/forms.responses.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self):
        """Initialize Google Forms client with actual authentication"""
        self.creds = None
        self.forms_service = None
        self.drive_service = None
        
        # Check for service account or OAuth credentials
        self._authenticate()
        
        # Build services
        self.forms_service = build('forms', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        
        # Rate limiting tracking
        self.request_times = []
        self.minute_start = datetime.now()
        self.requests_this_minute = 0
        
        # Cache for frequently used data
        self.form_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _authenticate(self):
        """Authenticate with Google APIs"""
        # Try service account first
        service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        if service_account_file and os.path.exists(service_account_file):
            from google.oauth2 import service_account
            self.creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=self.SCOPES
            )
            return
        
        # Try OAuth2 credentials
        token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        
        # Load existing token
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    raise GoogleFormsAuthError(
                        "No authentication method available. "
                        "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_CREDENTIALS_FILE"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(self.creds, token)
    
    def _check_rate_limit(self):
        """Check and enforce Google API rate limits"""
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
    
    def _execute_request(self, request):
        """Execute Google API request with rate limiting and error handling"""
        self._check_rate_limit()
        
        try:
            return request.execute()
        except HttpError as error:
            if error.resp.status == 429:
                # Rate limited
                self.logger.warning("Rate limited by Google API. Waiting 60s")
                time.sleep(60)
                raise GoogleFormsRateLimitError("Rate limit exceeded")
            elif error.resp.status == 401:
                raise GoogleFormsAuthError(f"Authentication failed: {error}")
            else:
                self.logger.error(f"API error: {error}")
                raise
    
    # ============= ACTUAL GOOGLE FORMS API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            # List forms to test connection
            request = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.form'",
                pageSize=1,
                fields="files(id, name)"
            )
            result = self._execute_request(request)
            self.logger.info("Connected to Google Forms API")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_forms(self, page_size: int = 100, page_token: str = None) -> Dict[str, Any]:
        """Get all forms from Google Drive"""
        request = self.drive_service.files().list(
            q="mimeType='application/vnd.google-apps.form'",
            pageSize=page_size,
            pageToken=page_token,
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, owners, sharingUser, permissions)"
        )
        
        result = self._execute_request(request)
        
        # Cache form metadata
        for form in result.get('files', []):
            self.form_cache[form['id']] = form
        
        return result
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """Get detailed form information"""
        # Check cache for metadata
        if form_id not in self.form_cache:
            # Get metadata from Drive
            request = self.drive_service.files().get(
                fileId=form_id,
                fields="id, name, createdTime, modifiedTime, owners, sharingUser, permissions"
            )
            metadata = self._execute_request(request)
            self.form_cache[form_id] = metadata
        
        # Get form structure
        request = self.forms_service.forms().get(formId=form_id)
        form = self._execute_request(request)
        
        # Merge metadata
        form['metadata'] = self.form_cache.get(form_id, {})
        
        return form
    
    def get_form_responses(self, form_id: str, page_size: int = 100, 
                          page_token: str = None) -> Dict[str, Any]:
        """Get form responses"""
        request = self.forms_service.forms().responses().list(
            formId=form_id,
            pageSize=page_size,
            pageToken=page_token
        )
        
        return self._execute_request(request)
    
    def get_form_response(self, form_id: str, response_id: str) -> Dict[str, Any]:
        """Get specific form response"""
        request = self.forms_service.forms().responses().get(
            formId=form_id,
            responseId=response_id
        )
        
        return self._execute_request(request)
    
    def get_form_watches(self, form_id: str) -> List[Dict[str, Any]]:
        """Get watches (webhooks) for a form"""
        request = self.forms_service.forms().watches().list(formId=form_id)
        result = self._execute_request(request)
        return result.get('watches', [])
    
    # ============= FORM STRUCTURE ANALYSIS =============
    
    def analyze_form_complexity(self, form_id: str) -> Dict[str, Any]:
        """
        Analyze form complexity for transformation
        Google Forms has simpler structure than other form builders
        """
        form = self.get_form(form_id)
        
        analysis = {
            'item_count': len(form.get('items', [])),
            'has_sections': False,
            'has_page_breaks': False,
            'has_file_upload': False,
            'has_grid': False,
            'has_validation': False,
            'has_required_fields': False,
            'section_count': 1,
            'complexity_score': 0,
            'item_types': {}
        }
        
        # Analyze items
        for item in form.get('items', []):
            # Get question type
            if 'questionItem' in item:
                question = item['questionItem']['question']
                
                # Check if required
                if question.get('required'):
                    analysis['has_required_fields'] = True
                
                # Determine question type
                if 'textQuestion' in question:
                    item_type = GoogleFormsItemType.PARAGRAPH_TEXT.value if question['textQuestion'].get('paragraph') else GoogleFormsItemType.TEXT.value
                elif 'choiceQuestion' in question:
                    choice_type = question['choiceQuestion']['type']
                    if choice_type == 'RADIO':
                        item_type = GoogleFormsItemType.MULTIPLE_CHOICE.value
                    elif choice_type == 'CHECKBOX':
                        item_type = GoogleFormsItemType.CHECKBOX.value
                    elif choice_type == 'DROP_DOWN':
                        item_type = GoogleFormsItemType.DROPDOWN.value
                    else:
                        item_type = choice_type
                elif 'scaleQuestion' in question:
                    item_type = GoogleFormsItemType.SCALE.value
                elif 'dateQuestion' in question:
                    item_type = GoogleFormsItemType.DATE.value
                elif 'timeQuestion' in question:
                    item_type = GoogleFormsItemType.TIME.value
                elif 'fileUploadQuestion' in question:
                    item_type = GoogleFormsItemType.FILE_UPLOAD.value
                    analysis['has_file_upload'] = True
                    analysis['complexity_score'] += 5
                elif 'rowQuestion' in question:
                    item_type = GoogleFormsItemType.GRID.value
                    analysis['has_grid'] = True
                    analysis['complexity_score'] += 3
                else:
                    item_type = 'UNKNOWN'
                
                # Check for validation
                if 'textQuestion' in question and question['textQuestion'].get('validation'):
                    analysis['has_validation'] = True
                    analysis['complexity_score'] += 2
            
            elif 'pageBreakItem' in item:
                item_type = GoogleFormsItemType.PAGE_BREAK.value
                analysis['has_page_breaks'] = True
                analysis['section_count'] += 1
                analysis['complexity_score'] += 2
            
            elif 'textItem' in item or 'titleItem' in item:
                item_type = GoogleFormsItemType.SECTION_HEADER.value
                analysis['has_sections'] = True
            
            elif 'imageItem' in item:
                item_type = GoogleFormsItemType.IMAGE.value
            
            elif 'videoItem' in item:
                item_type = GoogleFormsItemType.VIDEO.value
            
            else:
                item_type = 'UNKNOWN'
            
            # Count item types
            if item_type not in analysis['item_types']:
                analysis['item_types'][item_type] = 0
            analysis['item_types'][item_type] += 1
        
        # Add base complexity
        analysis['complexity_score'] += analysis['item_count']
        analysis['complexity_score'] += (analysis['section_count'] - 1) * 5
        
        # Recommend transformation strategy
        if analysis['item_count'] <= 10 and not analysis['has_page_breaks']:
            analysis['recommended_strategy'] = 'simple_form'
        elif analysis['item_count'] <= 20 and not analysis['has_page_breaks']:
            analysis['recommended_strategy'] = 'kickoff_form'
        elif analysis['has_page_breaks']:
            analysis['recommended_strategy'] = 'multi_step_workflow'
        else:
            analysis['recommended_strategy'] = 'standard_workflow'
        
        return analysis
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_forms(self, batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get forms in batches"""
        page_token = None
        
        while True:
            result = self.get_forms(page_size=batch_size, page_token=page_token)
            forms = result.get('files', [])
            
            if not forms:
                break
            
            yield forms
            
            page_token = result.get('nextPageToken')
            if not page_token:
                break
            
            time.sleep(0.5)  # Rate limit pause
    
    def batch_get_responses(self, form_id: str, 
                           batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """Get form responses in batches"""
        page_token = None
        
        while True:
            result = self.get_form_responses(
                form_id=form_id,
                page_size=batch_size,
                page_token=page_token
            )
            
            responses = result.get('responses', [])
            
            if not responses:
                break
            
            yield responses
            
            page_token = result.get('nextPageToken')
            if not page_token:
                break
            
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Google Forms data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'forms': [],
            'total_forms': 0,
            'total_responses': 0,
            'total_items': 0
        }
        
        # Get all forms
        self.logger.info("Fetching forms...")
        
        for form_batch in self.batch_get_forms():
            for form_metadata in form_batch:
                self.logger.info(f"Processing form: {form_metadata['name']}")
                
                try:
                    # Get full form details
                    form_data = self.get_form(form_metadata['id'])
                    
                    # Analyze complexity
                    form_data['complexity_analysis'] = self.analyze_form_complexity(form_metadata['id'])
                    data['total_items'] += form_data['complexity_analysis']['item_count']
                    
                    # Get watches (webhooks)
                    form_data['watches'] = self.get_form_watches(form_metadata['id'])
                    
                    # Get responses
                    form_data['responses'] = []
                    response_count = 0
                    
                    for response_batch in self.batch_get_responses(form_metadata['id']):
                        form_data['responses'].extend(response_batch)
                        response_count += len(response_batch)
                        
                        # Limit responses to avoid huge exports
                        if response_count >= 5000:
                            self.logger.warning(f"  Limiting responses to 5000 for form {form_metadata['id']}")
                            break
                    
                    data['total_responses'] += response_count
                    
                    data['forms'].append(form_data)
                    data['total_forms'] += 1
                    
                    self.logger.info(f"  Processed {response_count} responses")
                    
                except Exception as e:
                    self.logger.error(f"  Error processing form {form_metadata['id']}: {e}")
                    continue
                
                # Rate limit pause
                time.sleep(1)
        
        self.logger.info(f"Export complete: {data['total_forms']} forms, {data['total_responses']} responses")
        
        return data
    
    # ============= RESPONSE PARSING =============
    
    def parse_response_answers(self, response: Dict[str, Any], form: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse response answers based on question types
        """
        parsed = {}
        
        # Create question map
        question_map = {}
        for item in form.get('items', []):
            if 'questionItem' in item:
                question_id = item['questionItem']['question']['questionId']
                question_map[question_id] = item['questionItem']['question']
        
        # Parse answers
        for answer in response.get('answers', {}).values():
            question_id = answer.get('questionId')
            
            if 'textAnswers' in answer:
                # Text response
                answers = answer['textAnswers'].get('answers', [])
                if len(answers) == 1:
                    parsed[question_id] = answers[0].get('value')
                else:
                    parsed[question_id] = [a.get('value') for a in answers]
            
            elif 'fileUploadAnswers' in answer:
                # File upload response
                answers = answer['fileUploadAnswers'].get('answers', [])
                parsed[question_id] = [a.get('fileId') for a in answers]
            
            elif 'grade' in answer:
                # Graded response
                parsed[question_id] = {
                    'score': answer['grade'].get('score'),
                    'correct': answer['grade'].get('correct'),
                    'feedback': answer['grade'].get('feedback')
                }
        
        # Add metadata
        parsed['_metadata'] = {
            'response_id': response.get('responseId'),
            'form_id': response.get('formId'),
            'created_time': response.get('createTime'),
            'last_submitted_time': response.get('lastSubmittedTime'),
            'respondent_email': response.get('respondentEmail')
        }
        
        return parsed
    
    # ============= CREATE OPERATIONS =============
    
    def create_form(self, title: str) -> Dict[str, Any]:
        """Create a new form"""
        form = {
            'info': {
                'title': title
            }
        }
        
        request = self.forms_service.forms().create(body=form)
        return self._execute_request(request)
    
    def create_watch(self, form_id: str, target_url: str, 
                    event_type: str = 'RESPONSES') -> Dict[str, Any]:
        """Create watch (webhook) for form"""
        watch = {
            'watch': {
                'target': {
                    'url': target_url
                },
                'eventType': event_type
            }
        }
        
        request = self.forms_service.forms().watches().create(
            formId=form_id,
            body=watch
        )
        return self._execute_request(request)
    
    def batch_update_form(self, form_id: str, requests: List[Dict]) -> Dict[str, Any]:
        """Batch update form structure"""
        body = {
            'requests': requests
        }
        
        request = self.forms_service.forms().batchUpdate(
            formId=form_id,
            body=body
        )
        return self._execute_request(request)


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = GoogleFormsProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Google Forms")
        
        # Get forms
        result = client.get_forms(page_size=5)
        forms = result.get('files', [])
        print(f"Found forms: {len(forms)}")
        
        if forms:
            form_metadata = forms[0]
            print(f"\nForm: {form_metadata['name']}")
            print(f"ID: {form_metadata['id']}")
            print(f"Created: {form_metadata.get('createdTime', 'Unknown')}")
            
            # Get full form details
            form = client.get_form(form_metadata['id'])
            print(f"Items: {len(form.get('items', []))}")
            
            # Analyze complexity
            analysis = client.analyze_form_complexity(form_metadata['id'])
            print(f"\nComplexity analysis:")
            print(f"  - Item count: {analysis['item_count']}")
            print(f"  - Has sections: {analysis['has_sections']}")
            print(f"  - Has file upload: {analysis['has_file_upload']}")
            print(f"  - Section count: {analysis['section_count']}")
            print(f"  - Complexity score: {analysis['complexity_score']}")
            print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
            
            # Get responses
            response_result = client.get_form_responses(form_metadata['id'], page_size=5)
            responses = response_result.get('responses', [])
            print(f"\nResponses: {len(responses)}")
            
            if responses:
                response = responses[0]
                parsed = client.parse_response_answers(response, form)
                print(f"  First response has {len(parsed)} answers")
    
    print("\n✅ Production Google Forms client ready!")