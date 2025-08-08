"""
Field Transformer
Transforms vendor fields to Tallyfy fields
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform vendor fields to Tallyfy format"""
    
    def __init__(self, ai_client=None):
        """Initialize field transformer"""
        self.ai_client = ai_client
        
        # Map vendor field types to Tallyfy types
        self.field_type_map = {
            'text': 'text',
            'textarea': 'textarea',
            'number': 'text',
            'email': 'email',
            'phone': 'text',
            'date': 'date',
            'checkbox': 'multiselect',
            'radio': 'radio',
            'select': 'dropdown',
            'dropdown': 'dropdown',
            'file': 'file',
            'url': 'text',
            'boolean': 'yesno',
            'multiselect': 'multiselect',
            'rating': 'rating',
            'signature': 'signature'
        }
    
    def transform_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single field"""
        try:
            # Get field type
            field_type = self._get_field_type(field)
            tallyfy_type = self.field_type_map.get(field_type, 'text')
            
            # Build Tallyfy field
            tallyfy_field = {
                'name': field.get('name', field.get('label', '')),
                'type': tallyfy_type,
                'required': field.get('required', False),
                'description': field.get('description', ''),
                'help_text': field.get('help_text', ''),
                'placeholder': field.get('placeholder', ''),
                'vendor_metadata': {
                    'original_type': field_type,
                    'original_id': field.get('id', ''),
                    'original_data': field
                }
            }
            
            # Handle choice fields
            if tallyfy_type in ['dropdown', 'radio', 'multiselect']:
                tallyfy_field['options'] = self._extract_options(field)
            
            # Handle validation
            if 'validation' in field:
                tallyfy_field['validation'] = self._transform_validation(field['validation'])
            
            return tallyfy_field
            
        except Exception as e:
            logger.error(f"Error transforming field: {e}")
            return self._create_fallback_field(field)
    
    def _get_field_type(self, field: Dict[str, Any]) -> str:
        """Extract field type from vendor format"""
        # Override in vendor-specific implementation
        return field.get('type', 'text').lower()
    
    def _extract_options(self, field: Dict[str, Any]) -> List[str]:
        """Extract options for choice fields"""
        # Override in vendor-specific implementation
        options = field.get('options', field.get('choices', []))
        if isinstance(options, list):
            return [str(opt) for opt in options]
        return []
    
    def _transform_validation(self, validation: Any) -> Dict[str, Any]:
        """Transform validation rules"""
        # Override in vendor-specific implementation
        return {}
    
    def _create_fallback_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback field when transformation fails"""
        return {
            'name': str(field.get('name', field.get('label', 'Untitled Field'))),
            'type': 'text',
            'required': False,
            'vendor_metadata': {'original_data': field}
        }
