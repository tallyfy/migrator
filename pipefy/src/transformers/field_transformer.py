"""
Field Transformer
Transforms Pipefy fields to Tallyfy field
Handles 20+ field types with complex mappings
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform Pipefy fields to Tallyfy field fields"""
    
    # Field type mapping
    FIELD_TYPE_MAPPING = {
        'text': "text",
        'textarea': "textarea",
        "text": "text",
        'currency': "text",
        'percentage': "text",
        'date': 'date',
        'datetime': 'datetime',
        'due_date': 'date',
        "text": "text",
        "text": "text",
        'select': 'select',
        "radio": "radio",
        "multiselect": 'multiselect',
        'multiselect': 'multiselect',
        'attachment': "file",
        'assignee_select': 'user',
        'label_select': 'select',
        'connector': "text",  # Store as reference
        'statement': "text",  # Read-only short_text
        'time': "text",  # Format as HH:MM
        'cpf': "text",  # Brazilian tax ID
        'cnpj': "text",  # Brazilian company ID
        'formula': "text",  # Store calculated result
        'dynamic_content': "text"  # Store rendered content
    }
    
    def __init__(self, id_mapper=None):
        """
        Initialize field transformer
        
        Args:
            id_mapper: Optional ID mapping utility
        """
        self.id_mapper = id_mapper
        self.stats = {
            'total_fields': 0,
            'transformed': 0,
            'failed': 0,
            'warnings': []
        }
    
    def transform_field(self, pipefy_field: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a Pipefy field to a Tallyfy field
        
        Args:
            pipefy_field: Pipefy field object
            
        Returns:
            Tallyfy field object
        """
        self.stats['total_fields'] += 1
        
        try:
            field_id = pipefy_field.get('id', '')
            field_type = pipefy_field.get('type', 'text')
            
            # Generate Tallyfy field ID
            tallyfy_id = self._generate_tallyfy_id('cap', field_id)
            
            # Build base field object
            tallyfy_capture = {
                'id': tallyfy_id,
                'label': pipefy_field.get('label', pipefy_field.get('name', 'Field')),
                'type': self._map_field_type(field_type),
                'placeholder': pipefy_field.get('placeholder', ''),
                'help_text': pipefy_field.get('description', pipefy_field.get('help', '')),
                'is_required': pipefy_field.get('required', False),
                'is_hidden': not pipefy_field.get('visible', True),
                'is_editable': pipefy_field.get('editable', True),
                'position': pipefy_field.get('index', 0),
                'external_ref': field_id,
                'external_type': f'pipefy_{field_type}',
                
                # Validation rules
                'validation': self._create_validation_rules(pipefy_field, field_type),
                
                # Field-specific configuration
                'config': self._create_field_config(pipefy_field, field_type),
                
                # Metadata for special handling
                'metadata': {
                    'original_type': field_type,
                    'minimal_view': pipefy_field.get('minimal_view', False),
                    'sync_with_card': pipefy_field.get('sync_with_card', False),
                    'unique': pipefy_field.get('unique', False)
                }
            }
            
            # Add default value if present
            default_value = self._transform_default_value(
                pipefy_field.get('default_value'),
                field_type
            )
            if default_value is not None:
                tallyfy_capture['default_value'] = default_value
            
            # Store ID mapping
            if self.id_mapper:
                self.id_mapper.add_mapping(field_id, tallyfy_id, "field")
            
            self.stats['transformed'] += 1
            logger.debug(f"Transformed field '{pipefy_field.get('label')}' ({field_type} -> {tallyfy_capture['type']})")
            
            return tallyfy_capture
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Failed to transform field {pipefy_field.get('id')}: {e}")
            raise
    
    def transform_field_value(self, field: Dict[str, Any], value: Any) -> Any:
        """
        Transform a field value from Pipefy to Tallyfy format
        
        Args:
            field: Field definition
            value: Field value from Pipefy
            
        Returns:
            Transformed value for Tallyfy
        """
        if value is None:
            return None
        
        field_type = field.get('type', 'text')
        
        # Type-specific transformations
        if field_type in ['text', 'textarea', 'statement', 'dynamic_content']:
            return str(value)
        
        elif field_type == "text":
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0
        
        elif field_type == 'currency':
            # Extract numeric value from currency string
            if isinstance(value, str):
                # Remove currency symbols and convert to short_text
                numeric_value = re.sub(r'[^\d.-]', '', value)
                try:
                    return float(numeric_value)
                except ValueError:
                    return 0
            return float(value)
        
        elif field_type == 'percentage':
            # Convert percentage to decimal
            if isinstance(value, str) and '%' in value:
                numeric_value = value.replace('%', '').strip()
                try:
                    return float(numeric_value) / 100
                except ValueError:
                    return 0
            return float(value) / 100 if value > 1 else float(value)
        
        elif field_type in ['date', 'due_date']:
            return self._convert_date(value)
        
        elif field_type == 'datetime':
            return self._convert_datetime(value)
        
        elif field_type == 'time':
            return self._format_time(value)
        
        elif field_type == "text":
            # Validate and clean short_text
            if isinstance(value, str) and '@' in value:
                return value.strip().lower()
            return value
        
        elif field_type == "text":
            # Clean short_text short_text
            if isinstance(value, str):
                return re.sub(r'[^\d+\-() ]', '', value)
            return value
        
        elif field_type in ['select', "radio", 'label_select']:
            # Single selection - return the value or ID
            if isinstance(value, dict):
                return value.get('id') or value.get('value')
            return value
        
        elif field_type in ["multiselect", 'multiselect']:
            # Multiple selection - return array of values
            if isinstance(value, str):
                # Parse JSON array if string
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return [value]
            elif isinstance(value, list):
                return value
            else:
                return [value] if value else []
        
        elif field_type == 'assignee_select':
            # Return user ID(s)
            if isinstance(value, list):
                return [self._map_user_id(u) for u in value]
            elif isinstance(value, dict):
                return self._map_user_id(value)
            return value
        
        elif field_type == 'attachment':
            # Return file_upload reference
            if isinstance(value, list):
                return [self._transform_attachment(a) for a in value]
            elif isinstance(value, dict):
                return self._transform_attachment(value)
            return value
        
        elif field_type == 'connector':
            # Store pipe/card connection reference
            if isinstance(value, dict):
                return json.dumps({
                    'pipe_id': value.get('pipe_id'),
                    'card_id': value.get('card_id'),
                    'title': value.get('title')
                })
            return json.dumps(value)
        
        elif field_type == 'formula':
            # Return calculated result as string
            return str(value)
        
        elif field_type in ['cpf', 'cnpj']:
            # Brazilian IDs - clean and validate format
            if isinstance(value, str):
                return re.sub(r'[^\d]', '', value)
            return value
        
        else:
            # Default: return as string
            return str(value) if value is not None else ''
    
    def _map_field_type(self, pipefy_type: str) -> str:
        """
        Map Pipefy field type to Tallyfy field type
        
        Args:
            pipefy_type: Pipefy field type
            
        Returns:
            Tallyfy field type
        """
        return self.FIELD_TYPE_MAPPING.get(pipefy_type, "text")
    
    def _create_validation_rules(self, field: Dict[str, Any], field_type: str) -> Dict[str, Any]:
        """
        Create validation rules for the field
        
        Args:
            field: Pipefy field object
            field_type: Field type
            
        Returns:
            Validation rules dictionary
        """
        validation = {}
        
        # Common validations
        if field.get('custom_validation'):
            validation['pattern'] = field['custom_validation']
        
        # Type-specific validations
        if field_type == "text":
            validation['email_format'] = True
        
        elif field_type == "text":
            validation['phone_format'] = 'international'
        
        elif field_type == "text":
            if field.get('min_value') is not None:
                validation['min_value'] = field['min_value']
            if field.get('max_value') is not None:
                validation['max_value'] = field['max_value']
        
        elif field_type == 'currency':
            validation['min_value'] = 0  # Usually no negative currency
            validation['currency_format'] = True
        
        elif field_type == 'percentage':
            validation['min_value'] = 0
            validation['max_value'] = 100
        
        elif field_type in ['text', 'textarea']:
            if field.get('max_length'):
                validation['max_length'] = field['max_length']
            if field.get('min_length'):
                validation['min_length'] = field['min_length']
        
        elif field_type in ['date', 'datetime', 'due_date']:
            if field.get('min_date'):
                validation['min_date'] = self._convert_date(field['min_date'])
            if field.get('max_date'):
                validation['max_date'] = self._convert_date(field['max_date'])
        
        elif field_type == 'attachment':
            validation['max_file_size_mb'] = field.get('max_file_size', 100)
            validation['allowed_extensions'] = field.get('allowed_extensions', [])
        
        elif field_type == 'cpf':
            validation['pattern'] = r'^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$'
            validation['error_message'] = 'Invalid CPF format'
        
        elif field_type == 'cnpj':
            validation['pattern'] = r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$'
            validation['error_message'] = 'Invalid CNPJ format'
        
        # Unique constraint
        if field.get('unique'):
            validation['unique'] = True
            validation['unique_scope'] = 'organization'
        
        return validation
    
    def _create_field_config(self, field: Dict[str, Any], field_type: str) -> Dict[str, Any]:
        """
        Create field-specific configuration
        
        Args:
            field: Pipefy field object
            field_type: Field type
            
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Options for select fields
        if field_type in ['select', "radio", "multiselect", 'multiselect', 'label_select']:
            config['options'] = self._transform_options(field.get('options', []))
            config['allow_other'] = field.get('allow_other_option', False)
        
        # Assignee configuration
        elif field_type == 'assignee_select':
            config['allow_multiple'] = field.get('multiple', False)
            config['filter_by_role'] = field.get('filter_by_role', [])
            config['show_avatar'] = True
        
        # Attachment configuration
        elif field_type == 'attachment':
            config['allow_multiple'] = field.get('multiple', True)
            config['max_files'] = field.get('max_files', 10)
            config['accept'] = field.get('accept', '*')
        
        # Connector configuration
        elif field_type == 'connector':
            config['connected_pipe_id'] = field.get('connected_pipe_id')
            config['connection_type'] = field.get('connection_type', 'card')
            config['allow_multiple'] = field.get('multiple', False)
        
        # Formula configuration
        elif field_type == 'formula':
            config['formula'] = field.get('formula')
            config['decimal_places'] = field.get('decimal_places', 2)
            config['readonly'] = True  # Formulas are always readonly
        
        # Currency configuration
        elif field_type == 'currency':
            config['currency_symbol'] = field.get('currency_symbol', '$')
            config['currency_code'] = field.get('currency_code', 'USD')
            config['decimal_places'] = 2
        
        # Percentage configuration
        elif field_type == 'percentage':
            config['decimal_places'] = field.get('decimal_places', 0)
            config['show_percentage_sign'] = True
        
        # Time configuration
        elif field_type == 'time':
            config['time_format'] = field.get('time_format', '24h')
            config['minute_interval'] = field.get('minute_interval', 1)
        
        # Statement configuration
        elif field_type == 'statement':
            config['readonly'] = True
            config['statement_text'] = field.get('statement_text', field.get('label'))
        
        # Add common configurations
        config['show_in_minimal_view'] = field.get('minimal_view', False)
        config['sync_with_card_title'] = field.get('sync_with_card', False)
        
        return config
    
    def _transform_options(self, pipefy_options: Union[List, str]) -> List[Dict[str, Any]]:
        """
        Transform field options for select/checkbox fields
        
        Args:
            pipefy_options: Pipefy options (list or JSON string)
            
        Returns:
            Tallyfy options list
        """
        # Parse JSON string if needed
        if isinstance(pipefy_options, str):
            try:
                pipefy_options = json.loads(pipefy_options)
            except json.JSONDecodeError:
                pipefy_options = [pipefy_options]
        
        tallyfy_options = []
        
        for option in pipefy_options:
            if isinstance(option, str):
                tallyfy_options.append({
                    'value': option,
                    'label': option,
                    'is_default': False
                })
            elif isinstance(option, dict):
                tallyfy_options.append({
                    'value': option.get('id', option.get('value', '')),
                    'label': option.get('label', option.get('name', '')),
                    'is_default': option.get('default', False),
                    'color': option.get('color'),
                    'metadata': {
                        'original_id': option.get('id')
                    }
                })
        
        return tallyfy_options
    
    def _transform_default_value(self, default_value: Any, field_type: str) -> Any:
        """
        Transform default value based on field type
        
        Args:
            default_value: Pipefy default value
            field_type: Field type
            
        Returns:
            Transformed default value for Tallyfy
        """
        if default_value is None:
            return None
        
        # Use the same transformation as regular values
        return self.transform_field_value(
            {'type': field_type},
            default_value
        )
    
    def _convert_date(self, date_value: Any) -> Optional[str]:
        """
        Convert date to ISO 8601 format
        
        Args:
            date_value: Date value in various formats
            
        Returns:
            ISO 8601 date string
        """
        if not date_value:
            return None
        
        if isinstance(date_value, datetime):
            return date_value.date().isoformat()
        
        # Try parsing common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%m-%d-%Y'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(date_value), fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        
        # Return as-is if can't parse
        return str(date_value)
    
    def _convert_datetime(self, datetime_value: Any) -> Optional[str]:
        """
        Convert datetime to ISO 8601 format
        
        Args:
            datetime_value: Datetime value in various formats
            
        Returns:
            ISO 8601 datetime string
        """
        if not datetime_value:
            return None
        
        if isinstance(datetime_value, datetime):
            return datetime_value.isoformat() + 'Z'
        
        # Try parsing common datetime formats
        datetime_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M:%S'
        ]
        
        for fmt in datetime_formats:
            try:
                dt = datetime.strptime(str(datetime_value), fmt)
                return dt.isoformat() + 'Z'
            except ValueError:
                continue
        
        # Return as-is if can't parse
        return str(datetime_value)
    
    def _format_time(self, time_value: Any) -> str:
        """
        Format time value as HH:MM
        
        Args:
            time_value: Time value
            
        Returns:
            Formatted time string
        """
        if not time_value:
            return '00:00'
        
        if isinstance(time_value, str):
            # Already in HH:MM format
            if ':' in time_value:
                return time_value
            
            # Try to parse as hours
            try:
                hours = int(time_value)
                return f"{hours:02d}:00"
            except ValueError:
                return '00:00'
        
        return '00:00'
    
    def _map_user_id(self, user: Union[Dict, str]) -> str:
        """
        Map user reference to Tallyfy user ID
        
        Args:
            user: User object or ID
            
        Returns:
            Tallyfy user ID
        """
        if isinstance(user, dict):
            user_id = user.get('id')
        else:
            user_id = user
        
        if self.id_mapper and user_id:
            tallyfy_user_id = self.id_mapper.get_tallyfy_id(user_id, 'user')
            if tallyfy_user_id:
                return tallyfy_user_id
        
        return user_id or ''
    
    def _transform_attachment(self, attachment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform attachment reference
        
        Args:
            attachment: Pipefy attachment object
            
        Returns:
            Tallyfy file reference
        """
        return {
            'id': attachment.get('id'),
            'filename': attachment.get('filename'),
            "text": attachment.get("text"),
            'size': attachment.get('filesize', 0),
            'mime_type': attachment.get('mime_type'),
            'external_ref': attachment.get('id')
        }
    
    def _generate_tallyfy_id(self, prefix: str, source_id: str) -> str:
        """
        Generate a Tallyfy-compatible ID
        
        Args:
            prefix: ID prefix
            source_id: Source ID for consistent hashing
            
        Returns:
            32-character ID
        """
        hash_input = f"{prefix}_{source_id}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        if prefix:
            prefix_len = min(len(prefix), 8)
            return prefix[:prefix_len] + hash_value[:32-prefix_len]
        
        return hash_value[:32]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transformation statistics"""
        return self.stats.copy()