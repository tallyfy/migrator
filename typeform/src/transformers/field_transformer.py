"""
Typeform Field Transformer
Transforms Typeform fields to Tallyfy fields
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform Typeform fields to Tallyfy fields"""
    
    def __init__(self, ai_client: Optional[Any] = None):
        """Initialize field transformer"""
        self.ai_client = ai_client
        
        # Typeform to Tallyfy field type mappings
        self.type_map = {
            'short_text': 'text',
            'long_text': 'textarea',
            'multiple_choice': 'radio',
            'picture_choice': 'radio',
            'dropdown': 'dropdown',
            'yes_no': 'radio',
            'email': 'email',
            'number': 'text',
            'rating': 'dropdown',
            'opinion_scale': 'dropdown',
            'date': 'date',
            'file_upload': 'file',
            'legal': 'radio',
            'website': 'text',
            'phone_number': 'text',
            'payment': 'text',
            'matrix': 'table',
            'ranking': 'multiselect',
            'group': None,  # Skip group items
            'statement': None  # Skip statement items
        }
        
        logger.info("Typeform field transformer initialized")
    
    def transform(self, field: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform single Typeform field to Tallyfy field"""
        field_type = field.get('type', 'short_text')
        
        # Skip non-field items
        if field_type in ['group', 'statement', 'welcome_screen', 'thankyou_screen']:
            return None
        
        tallyfy_type = self.type_map.get(field_type, 'text')
        
        # Build base field
        tallyfy_field = {
            'type': tallyfy_type,
            'label': field.get('title', 'Untitled Field'),
            'name': f"field_{field.get('id', '')}",
            'required': field.get('validations', {}).get('required', False),
            'help_text': field.get('properties', {}).get('description', ''),
            'metadata': {
                'typeform_id': field.get('id'),
                'typeform_ref': field.get('ref'),
                'typeform_type': field_type
            }
        }
        
        # Handle choice fields
        if field_type in ['multiple_choice', 'picture_choice', 'dropdown']:
            choices = field.get('properties', {}).get('choices', [])
            tallyfy_field['options'] = self._transform_choices(choices)
            
            # Handle multiple selection
            if field.get('properties', {}).get('allow_multiple_selection'):
                tallyfy_field['type'] = 'multiselect'
        
        # Handle yes/no
        if field_type == 'yes_no':
            tallyfy_field['options'] = [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]
        
        # Handle legal (accept/decline)
        if field_type == 'legal':
            tallyfy_field['options'] = [
                {'value': 'accept', 'label': 'I Accept'},
                {'value': 'decline', 'label': 'I Decline'}
            ]
        
        # Handle rating/scale
        if field_type in ['rating', 'opinion_scale']:
            steps = field.get('properties', {}).get('steps', 5)
            start_at_one = field.get('properties', {}).get('start_at_one', True)
            start = 1 if start_at_one else 0
            
            tallyfy_field['options'] = [
                {'value': str(i), 'label': str(i)}
                for i in range(start, start + steps)
            ]
            
            # Add labels if provided
            labels = field.get('properties', {}).get('labels', {})
            if labels:
                left_label = labels.get('left')
                right_label = labels.get('right')
                if left_label or right_label:
                    tallyfy_field['help_text'] = f"{left_label} ← → {right_label}"
        
        # Handle matrix
        if field_type == 'matrix':
            tallyfy_field['type'] = 'table'
            rows = field.get('properties', {}).get('rows', [])
            columns = field.get('properties', {}).get('columns', [])
            
            tallyfy_field['table_config'] = {
                'rows': [r.get('label', '') for r in rows],
                'columns': [c.get('label', '') for c in columns]
            }
        
        # Handle ranking
        if field_type == 'ranking':
            choices = field.get('properties', {}).get('choices', [])
            tallyfy_field['options'] = self._transform_choices(choices)
            tallyfy_field['help_text'] = 'Rank items in order of preference'
        
        # Add validation rules
        tallyfy_field['validation'] = self._get_validation(field_type, field)
        
        # Add logic jump info if present
        if field.get('logic'):
            tallyfy_field['metadata']['has_logic'] = True
            tallyfy_field['metadata']['logic_count'] = len(field['logic'])
        
        return tallyfy_field
    
    def _transform_choices(self, choices: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Transform Typeform choices to Tallyfy options"""
        options = []
        
        for choice in choices:
            option = {
                'value': choice.get('ref', choice.get('id', '')),
                'label': choice.get('label', '')
            }
            
            # Note if choice has image
            if choice.get('attachment'):
                option['metadata'] = {'has_image': True}
            
            options.append(option)
        
        return options
    
    def _get_validation(self, field_type: str, field: Dict[str, Any]) -> Optional[str]:
        """Get validation rules for field"""
        validations = field.get('validations', {})
        rules = []
        
        # Type-specific validation
        if field_type == 'email':
            rules.append('email')
        elif field_type == 'number':
            rules.append('numeric')
            if validations.get('min_value') is not None:
                rules.append(f"min:{validations['min_value']}")
            if validations.get('max_value') is not None:
                rules.append(f"max:{validations['max_value']}")
        elif field_type == 'website':
            rules.append('url')
        elif field_type == 'phone_number':
            rules.append('regex:^[\\d\\s\\-\\+\\(\\)]+$')
        elif field_type in ['short_text', 'long_text']:
            max_length = validations.get('max_length')
            if max_length:
                rules.append(f"max:{max_length}")
            elif field_type == 'short_text':
                rules.append('max:255')
            else:
                rules.append('max:6000')
        
        # Required validation
        if validations.get('required'):
            rules.append('required')
        
        return '|'.join(rules) if rules else None
    
    def transform_batch(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple fields"""
        transformed = []
        
        for field in fields:
            result = self.transform(field)
            if result:
                transformed.append(result)
        
        logger.info(f"Transformed {len(transformed)} fields from {len(fields)} Typeform fields")
        return transformed
    
    def analyze_field_complexity(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze field transformation complexity"""
        field_type = field.get('type', 'unknown')
        
        complexity = {
            'field_id': field.get('id'),
            'field_type': field_type,
            'complexity': 'simple',
            'issues': []
        }
        
        # Check for complex features
        if field.get('logic'):
            complexity['complexity'] = 'complex'
            complexity['issues'].append('Has conditional logic')
        
        if field_type == 'payment':
            complexity['complexity'] = 'complex'
            complexity['issues'].append('Payment field requires manual setup')
        
        if field_type == 'matrix':
            complexity['complexity'] = 'medium'
            complexity['issues'].append('Matrix to table transformation')
        
        if field.get('properties', {}).get('randomize'):
            complexity['issues'].append('Choice randomization not supported')
        
        if field.get('attachment'):
            complexity['issues'].append('Field attachments need migration')
        
        return complexity