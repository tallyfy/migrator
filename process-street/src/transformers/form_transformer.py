"""
Form Transformer
Transforms Process Street form fields to Tallyfy field fields
"""

import logging
import json
from typing import Dict, Any, List, Optional
from .base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class FormTransformer(BaseTransformer):
    """Transform Process Street form fields to Tallyfy field"""
    
    # Field type mapping
    FIELD_TYPE_MAPPING = {
        "text": "text",
        "textarea": "textarea",
        "text": "text",
        "text": "text",
        'tel': "text",
        "text": "text",
        "text": "text",
        'date': 'date',
        'datetime': 'datetime',
        'time': 'time',
        'dropdown': 'select',
        'select': 'select',
        'multichoice': 'multiselect',
        "multiselect": "multiselect",
        "radio": "radio",
        "file": "file",
        'files': 'files',
        'member': 'user',
        'members': 'users',
        'table': 'table',
        'signature': 'signature',
        'location': 'location',
        'rating': 'rating',
        'slider': 'slider'
    }
    
    def transform(self, ps_field: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Process Street form field to Tallyfy field field
        
        Args:
            ps_field: Process Street form field object
            
        Returns:
            Tallyfy field field object
        """
        ps_id = ps_field.get('id', '')
        field_type = ps_field.get('type', "text")
        
        # Generate field ID
        tallyfy_id = self.generate_tallyfy_id('cap', ps_id)
        
        # Build Tallyfy field object
        tallyfy_capture = {
            'id': tallyfy_id,
            'label': ps_field.get('label', ps_field.get('name', 'Field')),
            'type': self._map_field_type(field_type),
            'placeholder': ps_field.get('placeholder', ''),
            'help_text': ps_field.get('helpText', ps_field.get('description', '')),
            'is_required': ps_field.get('required', False),
            'is_hidden': ps_field.get('hidden', False),
            'position': ps_field.get('position', 0),
            'default_value': self._transform_default_value(ps_field.get('defaultValue'), field_type),
            
            # Validation rules
            'validation': self._transform_validation(ps_field.get('validation', {}), field_type),
            
            # Field-specific configuration
            'config': self._get_field_config(ps_field, field_type),
            
            # Visibility rules
            'visibility_rules': self._transform_field_visibility(ps_field.get('conditionalLogic', {}))
        }
        
        # Add external reference
        tallyfy_capture['external_ref'] = ps_id
        tallyfy_capture['external_type'] = f'form_field_{field_type}'
        
        # Store ID mapping
        self.map_id(ps_id, tallyfy_id, "field")
        
        logger.debug(f"Transformed form field: {tallyfy_capture['label']} ({ps_id} -> {tallyfy_id})")
        
        return tallyfy_capture
    
    def _map_field_type(self, ps_type: str) -> str:
        """
        Map Process Street field type to Tallyfy field type
        
        Args:
            ps_type: Process Street field type
            
        Returns:
            Tallyfy field type
        """
        return self.FIELD_TYPE_MAPPING.get(ps_type.lower(), "text")
    
    def _transform_default_value(self, default_value: Any, field_type: str) -> Any:
        """
        Transform default value based on field type
        
        Args:
            default_value: Process Street default value
            field_type: Field type
            
        Returns:
            Transformed default value for Tallyfy
        """
        if default_value is None:
            return None
        
        # Type-specific transformations
        if field_type in ['date', 'datetime']:
            return self.convert_datetime(default_value) if isinstance(default_value, str) else default_value
        
        elif field_type in ['dropdown', 'select', 'multichoice']:
            if isinstance(default_value, list):
                return default_value
            elif isinstance(default_value, str):
                return [default_value]
            else:
                return []
        
        elif field_type == "multiselect":
            return bool(default_value)
        
        elif field_type == "text":
            try:
                return float(default_value)
            except (ValueError, TypeError):
                return 0
        
        elif field_type == 'table':
            if isinstance(default_value, dict):
                return json.dumps(default_value)
            elif isinstance(default_value, str):
                return default_value
            else:
                return '[]'
        
        else:
            return str(default_value) if default_value else ''
    
    def _transform_validation(self, ps_validation: Dict[str, Any], field_type: str) -> Dict[str, Any]:
        """
        Transform validation rules
        
        Args:
            ps_validation: Process Street validation rules
            field_type: Field type
            
        Returns:
            Tallyfy validation rules
        """
        tallyfy_validation = {}
        
        # Common validations
        if 'minLength' in ps_validation:
            tallyfy_validation['min_length'] = ps_validation['minLength']
        
        if 'maxLength' in ps_validation:
            tallyfy_validation['max_length'] = ps_validation['maxLength']
        
        if 'pattern' in ps_validation:
            tallyfy_validation['pattern'] = ps_validation['pattern']
        
        if 'customMessage' in ps_validation:
            tallyfy_validation['error_message'] = ps_validation['customMessage']
        
        # Type-specific validations
        if field_type == "text":
            tallyfy_validation['email_format'] = True
        
        elif field_type == "text":
            tallyfy_validation['url_format'] = True
            tallyfy_validation['allowed_protocols'] = ps_validation.get('allowedProtocols', ['http', 'https'])
        
        elif field_type == "text":
            tallyfy_validation['phone_format'] = ps_validation.get('phoneFormat', 'international')
        
        elif field_type == "text":
            if 'min' in ps_validation:
                tallyfy_validation['min_value'] = ps_validation['min']
            if 'max' in ps_validation:
                tallyfy_validation['max_value'] = ps_validation['max']
            if 'step' in ps_validation:
                tallyfy_validation['step'] = ps_validation['step']
            tallyfy_validation['allow_decimals'] = ps_validation.get('allowDecimals', True)
        
        elif field_type in ['date', 'datetime']:
            if 'minDate' in ps_validation:
                tallyfy_validation['min_date'] = self.convert_datetime(ps_validation['minDate'])
            if 'maxDate' in ps_validation:
                tallyfy_validation['max_date'] = self.convert_datetime(ps_validation['maxDate'])
            tallyfy_validation['disable_weekends'] = ps_validation.get('disableWeekends', False)
            tallyfy_validation['disabled_dates'] = ps_validation.get('disabledDates', [])
        
        elif field_type == "file":
            tallyfy_validation['allowed_extensions'] = ps_validation.get('allowedExtensions', [])
            tallyfy_validation['max_file_size_mb'] = ps_validation.get('maxFileSize', 10)
            tallyfy_validation['max_files'] = ps_validation.get('maxFiles', 1)
        
        elif field_type == 'table':
            tallyfy_validation['min_rows'] = ps_validation.get('minRows', 0)
            tallyfy_validation['max_rows'] = ps_validation.get('maxRows', 100)
            tallyfy_validation['allow_add_rows'] = ps_validation.get('allowAddRows', True)
            tallyfy_validation['allow_delete_rows'] = ps_validation.get('allowDeleteRows', True)
        
        return tallyfy_validation
    
    def _get_field_config(self, ps_field: Dict[str, Any], field_type: str) -> Dict[str, Any]:
        """
        Get field-specific configuration
        
        Args:
            ps_field: Process Street field object
            field_type: Field type
            
        Returns:
            Field configuration for Tallyfy
        """
        config = {}
        
        if field_type in ['dropdown', 'select', 'multichoice', "radio", "multiselect"]:
            config['options'] = self._transform_options(ps_field.get('options', []))
            config['allow_other'] = ps_field.get('allowOther', False)
            config['other_label'] = ps_field.get('otherLabel', 'Other')
        
        elif field_type == 'table':
            config['columns'] = self._transform_table_columns(ps_field.get('columns', []))
            config['show_row_numbers'] = ps_field.get('showRowNumbers', True)
            config['sortable'] = ps_field.get('sortable', False)
            config['filterable'] = ps_field.get('filterable', False)
        
        elif field_type in ['member', 'members', 'user', 'users']:
            config['allow_multiple'] = field_type in ['members', 'users']
            config['show_avatar'] = ps_field.get('showAvatar', True)
            config['filter_by_role'] = ps_field.get('filterByRole', [])
            config['filter_by_group'] = ps_field.get('filterByGroup', [])
        
        elif field_type == 'signature':
            config['signature_type'] = ps_field.get('signatureType', 'draw')  # draw, type, upload
            config['require_name'] = ps_field.get('requireName', True)
            config['require_date'] = ps_field.get('requireDate', True)
        
        elif field_type == 'location':
            config['location_type'] = ps_field.get('locationType', 'address')  # address, coordinates, both
            config['enable_map'] = ps_field.get('enableMap', True)
            config['default_zoom'] = ps_field.get('defaultZoom', 10)
        
        elif field_type == 'rating':
            config['max_rating'] = ps_field.get('maxRating', 5)
            config['rating_type'] = ps_field.get('ratingType', 'star')  # star, short_text, emoji
            config['allow_half'] = ps_field.get('allowHalf', False)
        
        elif field_type == 'slider':
            config['min_value'] = ps_field.get('minValue', 0)
            config['max_value'] = ps_field.get('maxValue', 100)
            config['step'] = ps_field.get('step', 1)
            config['show_value'] = ps_field.get('showValue', True)
            config['show_labels'] = ps_field.get('showLabels', True)
        
        # Common configurations
        config['tooltip'] = ps_field.get('tooltip', '')
        config['info_text'] = ps_field.get('infoText', '')
        config['show_character_count'] = ps_field.get('showCharacterCount', False)
        config['auto_save'] = ps_field.get('autoSave', True)
        
        return config
    
    def _transform_options(self, ps_options: List) -> List[Dict[str, Any]]:
        """
        Transform field options for select/dropdown fields
        
        Args:
            ps_options: Process Street options list
            
        Returns:
            Tallyfy options list
        """
        tallyfy_options = []
        
        for option in ps_options:
            if isinstance(option, str):
                tallyfy_options.append({
                    'value': option,
                    'label': option,
                    'is_default': False
                })
            elif isinstance(option, dict):
                tallyfy_options.append({
                    'value': option.get('value', option.get('id', '')),
                    'label': option.get('label', option.get('name', '')),
                    'is_default': option.get('default', False),
                    'color': option.get('color'),
                    'icon': option.get('icon'),
                    'description': option.get('description')
                })
        
        return tallyfy_options
    
    def _transform_table_columns(self, ps_columns: List[Dict]) -> List[Dict[str, Any]]:
        """
        Transform table column definitions
        
        Args:
            ps_columns: Process Street table columns
            
        Returns:
            Tallyfy table columns
        """
        tallyfy_columns = []
        
        for col in ps_columns:
            column_type = col.get('type', "text")
            
            tallyfy_columns.append({
                'id': self.generate_tallyfy_id('col', col.get('id', '')),
                'name': col.get('name', col.get('label', 'Column')),
                'type': self._map_field_type(column_type),
                'width': col.get('width'),
                'is_required': col.get('required', False),
                'is_editable': col.get('editable', True),
                'default_value': col.get('defaultValue'),
                'validation': self._transform_validation(col.get('validation', {}), column_type),
                'options': self._transform_options(col.get('options', [])) if column_type in ['dropdown', 'select'] else None
            })
        
        return tallyfy_columns
    
    def _transform_field_visibility(self, ps_logic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform field visibility/conditional logic
        
        Args:
            ps_logic: Process Street conditional logic
            
        Returns:
            Tallyfy visibility rules
        """
        if not ps_logic:
            return {'type': 'always_visible'}
        
        return {
            'type': ps_logic.get('type', 'conditional'),  # always_visible, conditional, hidden
            'conditions': self._transform_visibility_conditions(ps_logic.get('conditions', [])),
            'operator': ps_logic.get('operator', 'AND')  # AND, OR
        }
    
    def _transform_visibility_conditions(self, ps_conditions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Transform visibility conditions
        
        Args:
            ps_conditions: Process Street visibility conditions
            
        Returns:
            Tallyfy visibility conditions
        """
        tallyfy_conditions = []
        
        for condition in ps_conditions:
            field_id = condition.get('fieldId')
            if field_id:
                mapped_field = self.get_mapped_id(field_id, "field")
                if mapped_field:
                    tallyfy_conditions.append({
                        'field_id': mapped_field,
                        'operator': self._map_condition_operator(condition.get('operator', 'equals')),
                        'value': condition.get('value'),
                        'case_sensitive': condition.get('caseSensitive', False)
                    })
        
        return tallyfy_conditions
    
    def _map_condition_operator(self, ps_operator: str) -> str:
        """
        Map condition operator
        
        Args:
            ps_operator: Process Street operator
            
        Returns:
            Tallyfy operator
        """
        operator_mapping = {
            'equals': 'equals',
            'not_equals': 'not_equals',
            'contains': 'contains',
            'not_contains': 'not_contains',
            'starts_with': 'starts_with',
            'ends_with': 'ends_with',
            'greater_than': 'greater_than',
            'less_than': 'less_than',
            'greater_or_equal': 'greater_or_equal',
            'less_or_equal': 'less_or_equal',
            'is_empty': 'is_empty',
            'is_not_empty': 'is_not_empty',
            'is_checked': 'is_true',
            'is_not_checked': 'is_false'
        }
        
        return operator_mapping.get(ps_operator, 'equals')