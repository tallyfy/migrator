"""
Google Forms Field Transformer
Transforms Google Forms fields to Tallyfy fields
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional

# Add shared components
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))
from shared.form_migrator_base import FormMigratorBase

logger = logging.getLogger(__name__)


class FieldTransformer(FormMigratorBase):
    """Transform Google Forms fields to Tallyfy fields"""
    
    def __init__(self, ai_client: Optional[Any] = None):
        """Initialize field transformer"""
        super().__init__('google_forms')
        self.ai_client = ai_client
        logger.info("Google Forms field transformer initialized")
    
    def transform(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Google Forms question to Tallyfy field"""
        question = item.get('question', {})
        question_id = item.get('questionId', {}).get('value', '')
        
        # Determine field type
        field_type = self._get_field_type(question)
        if not field_type:
            return None
        
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
            tallyfy_field['options'] = self._transform_choice_options(question['choiceQuestion'])
        
        # Handle scale options
        if 'scaleQuestion' in question:
            tallyfy_field['options'] = self._transform_scale_options(question['scaleQuestion'])
        
        # Handle grid questions
        if 'gridQuestion' in question:
            tallyfy_field['table_config'] = self._transform_grid_config(question['gridQuestion'])
        
        # Add validation
        tallyfy_field['validation'] = self._get_validation(question, field_type)
        
        return tallyfy_field
    
    def _get_field_type(self, question: Dict[str, Any]) -> Optional[str]:
        """Determine Tallyfy field type from Google Forms question"""
        if 'textQuestion' in question:
            return 'textarea' if question['textQuestion'].get('paragraph') else 'text'
        elif 'choiceQuestion' in question:
            choice_type = question['choiceQuestion']['type']
            if choice_type == 'RADIO':
                return 'radio'
            elif choice_type == 'CHECKBOX':
                return 'multiselect'
            elif choice_type == 'DROP_DOWN':
                return 'dropdown'
            else:
                return 'radio'
        elif 'scaleQuestion' in question:
            return 'dropdown'
        elif 'dateQuestion' in question:
            return 'date'
        elif 'timeQuestion' in question:
            return 'text'
        elif 'fileUploadQuestion' in question:
            return 'file'
        elif 'gridQuestion' in question:
            return 'table'
        else:
            # Use AI for unknown types if available
            if self.ai_client and self.ai_client.enabled:
                result = self.ai_client.map_field({
                    'question_type': list(question.keys())[0] if question else 'unknown',
                    'vendor': 'google_forms'
                })
                if result and result.get('confidence', 0) > 0.7:
                    return result.get('tallyfy_type', 'text')
            return 'text'
    
    def _transform_choice_options(self, choice_question: Dict[str, Any]) -> List[Dict[str, str]]:
        """Transform choice options"""
        options = choice_question.get('options', [])
        return [
            {'value': opt.get('value', ''), 'label': opt.get('value', '')}
            for opt in options
        ]
    
    def _transform_scale_options(self, scale_question: Dict[str, Any]) -> List[Dict[str, str]]:
        """Transform scale options"""
        low = scale_question.get('low', 1)
        high = scale_question.get('high', 5)
        low_label = scale_question.get('lowLabel', '')
        high_label = scale_question.get('highLabel', '')
        
        options = []
        for i in range(low, high + 1):
            label = str(i)
            if i == low and low_label:
                label = f"{i} - {low_label}"
            elif i == high and high_label:
                label = f"{i} - {high_label}"
            options.append({'value': str(i), 'label': label})
        
        return options
    
    def _transform_grid_config(self, grid_question: Dict[str, Any]) -> Dict[str, Any]:
        """Transform grid configuration"""
        return {
            'rows': grid_question.get('rows', []),
            'columns': [col.get('label', '') for col in grid_question.get('columns', [])]
        }
    
    def _get_validation(self, question: Dict[str, Any], field_type: str) -> Optional[str]:
        """Get validation rules"""
        rules = []
        
        if question.get('required'):
            rules.append('required')
        
        if 'textQuestion' in question:
            text_q = question['textQuestion']
            if text_q.get('paragraph'):
                rules.append('max:6000')
            else:
                rules.append('max:255')
        
        return '|'.join(rules) if rules else None
    
    def transform_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple items"""
        transformed = []
        
        for item in items:
            # Skip non-question items
            if 'questionItem' not in item:
                continue
            
            question_item = item['questionItem']
            if 'question' in question_item:
                result = self.transform(question_item)
                if result:
                    transformed.append(result)
        
        logger.info(f"Transformed {len(transformed)} fields from {len(items)} items")
        return transformed