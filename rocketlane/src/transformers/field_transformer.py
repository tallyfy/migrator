"""
Field Transformer for RocketLane to Tallyfy Migration
Maps RocketLane field types to correct Tallyfy field types
"""

import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform RocketLane fields to Tallyfy fields"""
    
    # RocketLane field types to Tallyfy field types mapping
    # Based on actual Tallyfy api-v2 implementation
    FIELD_TYPE_MAP = {
        # RocketLane -> Tallyfy
        'text': 'text',              # Short text (max 255)
        'longtext': 'textarea',       # Long text (max 6000)
        'number': 'text',            # No number type in Tallyfy, use text with validation
        'decimal': 'text',           # Use text with numeric validation
        'currency': 'text',          # Use text with numeric validation
        'percentage': 'text',        # Use text with numeric validation
        'email': 'email',            # Email field
        'phone': 'text',             # Use text with phone validation
        'url': 'text',               # Use text with URL validation
        'date': 'date',              # Date picker
        'datetime': 'date',          # Date with time
        'time': 'text',              # No time field, use text
        'boolean': 'radio',          # Yes/No radio buttons
        'checkbox': 'radio',         # Single checkbox -> radio
        'select': 'dropdown',        # Single select
        'multiselect': 'multiselect', # Multiple select
        'radio': 'radio',            # Radio buttons
        'file': 'file',              # File upload
        'image': 'file',             # Image upload
        'user': 'assignees_form',    # User picker
        'team': 'assignees_form',    # Team picker -> user groups
        'customer': 'dropdown',      # Customer reference
        'project': 'dropdown',       # Project reference
        'task': 'dropdown',          # Task reference
        'milestone': 'dropdown',     # Milestone reference
        'rating': 'dropdown',        # Rating scale
        'slider': 'text',            # Slider -> text with number
        'formula': 'text',           # Calculated field -> readonly text
        'lookup': 'dropdown',        # Lookup field
        'barcode': 'text',           # Barcode -> text
        'signature': 'file',         # Signature -> file upload
        'location': 'text',          # Location -> text
        'color': 'dropdown',         # Color picker -> dropdown
        'tags': 'multiselect',       # Tags field
        'json': 'textarea',          # JSON data
        'markdown': 'textarea',      # Markdown text
        'html': 'textarea',          # HTML content
        'table': 'table',            # Table/grid
        'matrix': 'table',           # Matrix -> table
        'kanban': 'dropdown',        # Kanban status
        'gantt': 'date',            # Gantt -> date range
        'calendar': 'date',         # Calendar event
        'timeline': 'date'          # Timeline -> date
    }
    
    # Validation rules for specific types
    VALIDATION_RULES = {
        'number': 'numeric',
        'decimal': 'numeric',
        'currency': 'numeric|min:0',
        'percentage': 'numeric|min:0|max:100',
        'email': 'email',
        'phone': 'regex:^[\\d\\s\\-\\+\\(\\)]+$',
        'url': 'url',
        'barcode': 'regex:^[A-Za-z0-9]+$'
    }
    
    def __init__(self, ai_client=None):
        """
        Initialize field transformer
        
        Args:
            ai_client: Optional AI client for complex mappings
        """
        self.ai_client = ai_client
        self.transformation_stats = {
            'total': 0,
            'successful': 0,
            'ai_assisted': 0,
            'fallback': 0
        }
    
    def transform_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a RocketLane field to Tallyfy format
        
        Args:
            field: RocketLane field definition
            
        Returns:
            Tallyfy field definition
        """
        self.transformation_stats['total'] += 1
        
        field_type = field.get('type', 'text').lower()
        field_name = field.get('name', 'field')
        field_label = field.get('label', field_name)
        
        # Try direct mapping first
        tallyfy_type = self.FIELD_TYPE_MAP.get(field_type)
        
        if not tallyfy_type:
            # Try AI mapping if available
            if self.ai_client and self.ai_client.enabled:
                tallyfy_type = self._ai_map_field(field)
                if tallyfy_type:
                    self.transformation_stats['ai_assisted'] += 1
            
            # Fallback to text
            if not tallyfy_type:
                logger.warning(f"Unknown field type '{field_type}', using text as fallback")
                tallyfy_type = 'text'
                self.transformation_stats['fallback'] += 1
        
        # Build Tallyfy field structure
        tallyfy_field = {
            'type': tallyfy_type,
            'label': field_label[:255],  # Max label length
            'name': self._sanitize_field_name(field_name),
            'required': field.get('required', False),
            'help_text': field.get('description', '')[:1000],
            'metadata': {
                'original_type': field_type,
                'original_id': field.get('id'),
                'rocketlane_config': field.get('config', {})
            }
        }
        
        # Add validation rules
        if field_type in self.VALIDATION_RULES:
            tallyfy_field['validation'] = self.VALIDATION_RULES[field_type]
        elif field.get('validation'):
            tallyfy_field['validation'] = self._transform_validation(field['validation'])
        
        # Handle specific field types
        if tallyfy_type in ['dropdown', 'radio', 'multiselect']:
            tallyfy_field['options'] = self._transform_options(field.get('options', []))
        
        elif tallyfy_type == 'date':
            tallyfy_field['include_time'] = field_type == 'datetime'
            
        elif tallyfy_type == 'table':
            tallyfy_field['columns'] = self._transform_table_columns(field.get('columns', []))
        
        elif field_type == 'boolean':
            # Boolean becomes Yes/No radio
            tallyfy_field['options'] = [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]
        
        elif field_type in ['formula', 'lookup']:
            tallyfy_field['readonly'] = True
            tallyfy_field['formula'] = field.get('formula', '')
        
        # Handle default values
        if 'default' in field:
            tallyfy_field['default_value'] = self._transform_default_value(
                field['default'], field_type, tallyfy_type
            )
        
        self.transformation_stats['successful'] += 1
        return tallyfy_field
    
    def _sanitize_field_name(self, name: str) -> str:
        """Sanitize field name for Tallyfy"""
        # Remove special characters, keep alphanumeric and underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'field_' + sanitized
        return sanitized[:50]  # Max field name length
    
    def _transform_options(self, options: List) -> List[Dict[str, str]]:
        """Transform field options to Tallyfy format"""
        transformed = []
        
        for option in options:
            if isinstance(option, dict):
                transformed.append({
                    'value': str(option.get('value', option.get('id', ''))),
                    'label': str(option.get('label', option.get('name', '')))
                })
            else:
                # Simple string option
                transformed.append({
                    'value': str(option),
                    'label': str(option)
                })
        
        return transformed
    
    def _transform_table_columns(self, columns: List) -> List[Dict]:
        """Transform table columns to Tallyfy format"""
        transformed = []
        
        for col in columns:
            if isinstance(col, dict):
                transformed.append({
                    'name': col.get('name', 'column'),
                    'type': 'text',  # Tables only support text columns
                    'width': col.get('width', 'auto')
                })
            else:
                transformed.append({
                    'name': str(col),
                    'type': 'text',
                    'width': 'auto'
                })
        
        return transformed
    
    def _transform_validation(self, validation: Any) -> str:
        """Transform RocketLane validation rules to Laravel format"""
        if isinstance(validation, dict):
            rules = []
            
            if validation.get('required'):
                rules.append('required')
            
            if validation.get('min_length'):
                rules.append(f"min:{validation['min_length']}")
            
            if validation.get('max_length'):
                rules.append(f"max:{validation['max_length']}")
            
            if validation.get('pattern'):
                rules.append(f"regex:{validation['pattern']}")
            
            if validation.get('min_value'):
                rules.append(f"min:{validation['min_value']}")
            
            if validation.get('max_value'):
                rules.append(f"max:{validation['max_value']}")
            
            return '|'.join(rules)
        
        return str(validation)
    
    def _transform_default_value(self, default: Any, 
                                original_type: str, tallyfy_type: str) -> Any:
        """Transform default value based on field types"""
        if default is None:
            return None
        
        # Handle boolean defaults
        if original_type == 'boolean':
            if default in [True, 'true', 'True', 1, '1']:
                return 'yes'
            else:
                return 'no'
        
        # Handle date defaults
        if tallyfy_type == 'date':
            if default == 'today':
                return '{{today}}'
            elif default == 'tomorrow':
                return '{{tomorrow}}'
        
        # Handle user defaults
        if tallyfy_type == 'assignees_form':
            if default == 'current_user':
                return '{{current_user}}'
        
        return str(default)
    
    def _ai_map_field(self, field: Dict[str, Any]) -> Optional[str]:
        """Use AI to map complex field types"""
        if not self.ai_client or not self.ai_client.enabled:
            return None
        
        try:
            result = self.ai_client.map_field(field)
            if result and result.get('confidence', 0) > 0.7:
                return result.get('tallyfy_type')
        except Exception as e:
            logger.warning(f"AI field mapping failed: {e}")
        
        return None
    
    def transform_fields_batch(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform multiple fields
        
        Args:
            fields: List of RocketLane fields
            
        Returns:
            List of Tallyfy fields
        """
        transformed = []
        
        for field in fields:
            try:
                transformed_field = self.transform_field(field)
                transformed.append(transformed_field)
            except Exception as e:
                logger.error(f"Failed to transform field {field.get('name', 'unknown')}: {e}")
        
        return transformed
    
    def get_stats(self) -> Dict[str, int]:
        """Get transformation statistics"""
        return self.transformation_stats.copy()