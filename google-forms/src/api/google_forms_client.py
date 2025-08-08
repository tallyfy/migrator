"""
Google Forms API Client
Handles interactions with Google Forms API v1
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GoogleFormsClient:
    """Client for Google Forms API"""
    
    def __init__(self, credentials_path: str):
        """
        Initialize Google Forms client
        
        Args:
            credentials_path: Path to service account JSON file
        """
        self.credentials_path = credentials_path
        
        # Initialize Google API client
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/forms.body.readonly',
                'https://www.googleapis.com/auth/forms.responses.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
        )
        
        self.forms_service = build('forms', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)
        
        logger.info("Google Forms client initialized")
    
    def get_forms(self) -> List[Dict[str, Any]]:
        """Get all forms accessible to service account"""
        try:
            # Search for Google Forms in Drive
            results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.form'",
                pageSize=100,
                fields="files(id, name, createdTime, modifiedTime)"
            ).execute()
            
            forms = results.get('files', [])
            return forms
            
        except Exception as e:
            logger.error(f"Failed to get forms: {e}")
            raise
    
    def get_form(self, form_id: str) -> Dict[str, Any]:
        """Get form details including questions"""
        try:
            form = self.forms_service.forms().get(formId=form_id).execute()
            return form
        except Exception as e:
            logger.error(f"Failed to get form {form_id}: {e}")
            raise
    
    def get_responses(self, form_id: str) -> List[Dict[str, Any]]:
        """Get form responses"""
        try:
            responses = self.forms_service.forms().responses().list(
                formId=form_id
            ).execute()
            
            return responses.get('responses', [])
            
        except Exception as e:
            logger.error(f"Failed to get responses for {form_id}: {e}")
            raise
    
    def transform_to_tallyfy_field(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Forms question to Tallyfy field"""
        question = item.get('question', {})
        question_id = item.get('questionId', {}).get('value', '')
        
        # Get question type
        if 'textQuestion' in question:
            field_type = 'textarea' if question['textQuestion'].get('paragraph') else 'text'
        elif 'choiceQuestion' in question:
            choice_type = question['choiceQuestion']['type']
            if choice_type == 'RADIO':
                field_type = 'radio'
            elif choice_type == 'CHECKBOX':
                field_type = 'multiselect'
            elif choice_type == 'DROP_DOWN':
                field_type = 'dropdown'
            else:
                field_type = 'radio'
        elif 'scaleQuestion' in question:
            field_type = 'dropdown'  # Scale as dropdown
        elif 'dateQuestion' in question:
            field_type = 'date'
        elif 'timeQuestion' in question:
            field_type = 'text'  # Time as text with validation
        elif 'fileUploadQuestion' in question:
            field_type = 'file'
        elif 'gridQuestion' in question:
            field_type = 'table'
        else:
            field_type = 'text'
        
        # Build Tallyfy field
        tallyfy_field = {
            'type': field_type,
            'label': item.get('title', 'Untitled Question'),
            'name': f'field_{question_id}',
            'required': question.get('required', False),
            'help_text': item.get('description', ''),
            'metadata': {
                'google_forms_id': question_id,
                'google_forms_type': list(question.keys())[0] if question else 'unknown'
            }
        }
        
        # Handle choice options
        if 'choiceQuestion' in question:
            options = question['choiceQuestion'].get('options', [])
            tallyfy_field['options'] = [
                {'value': opt.get('value', ''), 'label': opt.get('value', '')}
                for opt in options
            ]
        
        # Handle scale options
        if 'scaleQuestion' in question:
            scale = question['scaleQuestion']
            low = scale.get('low', 1)
            high = scale.get('high', 5)
            tallyfy_field['options'] = [
                {'value': str(i), 'label': f'{i}'}
                for i in range(low, high + 1)
            ]
        
        # Add validation for specific types
        if 'textQuestion' in question:
            text_q = question['textQuestion']
            if text_q.get('paragraph'):
                tallyfy_field['validation'] = 'max:6000'
            else:
                tallyfy_field['validation'] = 'max:255'
        
        return tallyfy_field
    
    def transform_form_to_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Google Form to Tallyfy blueprint"""
        info = form.get('info', {})
        items = form.get('items', [])
        
        # Extract questions (skip non-question items)
        questions = [
            item for item in items 
            if 'question' in item.get('questionItem', {})
        ]
        
        # Transform questions to fields
        fields = []
        for item in questions:
            question_item = item.get('questionItem', {})
            field = self.transform_to_tallyfy_field(question_item)
            fields.append(field)
        
        # Determine complexity
        field_count = len(fields)
        
        if field_count <= 15:
            # Simple form - single kickoff
            return {
                'name': info.get('title', 'Untitled Form'),
                'description': info.get('description', ''),
                'metadata': {
                    'source': 'google_forms',
                    'form_id': form.get('formId'),
                    'revision_id': form.get('revisionId'),
                    'responder_uri': form.get('responderUri')
                },
                'kickoff_form': {
                    'fields': fields
                },
                'steps': [
                    {
                        'name': 'Process Response',
                        'type': 'task',
                        'description': 'Process the form submission'
                    },
                    {
                        'name': 'Send Confirmation',
                        'type': 'task',
                        'description': 'Send confirmation email if needed'
                    }
                ]
            }
        else:
            # Complex form - multi-step
            blueprint = {
                'name': info.get('title', 'Untitled Form'),
                'description': info.get('description', ''),
                'metadata': {
                    'source': 'google_forms',
                    'form_id': form.get('formId'),
                    'field_count': field_count
                },
                'steps': []
            }
            
            # Split fields into steps (10 fields per step)
            for i in range(0, field_count, 10):
                chunk = fields[i:i+10]
                step = {
                    'name': f'Part {(i//10) + 1}',
                    'type': 'form',
                    'form_fields': chunk
                }
                blueprint['steps'].append(step)
            
            # Add processing steps
            blueprint['steps'].extend([
                {
                    'name': 'Review Submission',
                    'type': 'approval',
                    'description': 'Review all submitted data'
                },
                {
                    'name': 'Process & File',
                    'type': 'task',
                    'description': 'Process and file the submission'
                }
            ])
            
            return blueprint
    
    def transform_response_to_process(self, response: Dict[str, Any], 
                                     blueprint_id: str) -> Dict[str, Any]:
        """Transform form response to Tallyfy process"""
        answers = response.get('answers', {})
        
        # Extract response data
        prerun_data = {}
        for question_id, answer_data in answers.items():
            answer = answer_data.get('textAnswers', {}).get('answers', [])
            if answer:
                # Get first answer value
                value = answer[0].get('value', '')
                prerun_data[f'field_{question_id}'] = value
        
        return {
            'checklist_id': blueprint_id,
            'name': f"Response {response.get('responseId', 'Unknown')}",
            'prerun_data': prerun_data,
            'metadata': {
                'source': 'google_forms',
                'response_id': response.get('responseId'),
                'submitted_at': response.get('createTime'),
                'last_modified': response.get('lastSubmittedTime'),
                'respondent_email': response.get('respondentEmail')
            }
        }
    
    def discover_workspace(self) -> Dict[str, Any]:
        """Discover all forms and statistics"""
        discovery = {
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {},
            'forms': []
        }
        
        # Get all forms
        forms = self.get_forms()
        discovery['statistics']['total_forms'] = len(forms)
        
        total_questions = 0
        total_responses = 0
        
        for form_meta in forms[:10]:  # Limit for discovery
            try:
                # Get form details
                form = self.get_form(form_meta['id'])
                question_count = len(form.get('items', []))
                
                # Get responses
                responses = self.get_responses(form_meta['id'])
                response_count = len(responses)
                
                total_questions += question_count
                total_responses += response_count
                
                discovery['forms'].append({
                    'id': form_meta['id'],
                    'name': form_meta['name'],
                    'questions': question_count,
                    'responses': response_count,
                    'created': form_meta.get('createdTime'),
                    'modified': form_meta.get('modifiedTime')
                })
                
            except Exception as e:
                logger.warning(f"Could not process form {form_meta['id']}: {e}")
        
        discovery['statistics']['total_questions'] = total_questions
        discovery['statistics']['total_responses'] = total_responses
        
        return discovery
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            # Try to list forms
            self.get_forms()
            logger.info("Google Forms API connection successful")
            return True
        except Exception as e:
            logger.error(f"Google Forms API connection failed: {e}")
            return False