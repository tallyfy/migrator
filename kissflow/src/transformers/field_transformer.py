"""Transform Kissflow fields to Tallyfy form fields."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform Kissflow's 20+ field types to Tallyfy field."""
    
    # Kissflow field types to Tallyfy field types mapping
    FIELD_TYPE_MAP = {
        # Basic Fields
        "text": 'text',
        "textarea": 'textarea',
        'rich_text': 'textarea',
        "text": 'text',  # With short_text validation
        "text": "text",
        'currency': "text",
        'rating': "text",
        'slider': "text",
        'date': 'date',
        'datetime': 'date',  # Tallyfy date can include time
        'yes_no': 'radio',
        
        # Selection Fields
        'dropdown': 'dropdown',
        'multi_dropdown': 'multiselect',
        "radio": 'radio',
        "multiselect": 'radio',  # Single checklist becomes yes/no radio_buttons
        'multiselect': 'multiselect',
        
        # Advanced Fields
        'user': 'assignees_form',
        'attachment': 'file',
        "file": 'file',
        'geolocation': 'text',  # Store as coordinates string
        'scanner': 'text',  # Store scanned value as short_text
        'sequence_number': 'text',  # Auto-increment as readonly short_text
        'formula': 'text',  # Calculated field as readonly short_text
        
        # Kissflow-specific
        'child_table': 'table',  # Complex - needs special handling
        'lookup': 'dropdown',  # Lookup becomes dropdown with options
        'remote_lookup': 'dropdown',  # External data as dropdown
        'signature': 'file',  # Signature as image file_upload
        'image': 'file',
        "text": 'text',  # URL with validation
        "text": 'text',  # Phone with validation
    }
    
    # Field validations to apply
    FIELD_VALIDATIONS = {
        "text": {'type': "text"},
        "text": {'type': "text"},
        "text": {'type': "text"},
        "text": {'type': "text"},
        'currency': {'type': "text", 'format': 'currency'},
    }
    
    def transform_field_definition(self, kissflow_field: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow field definition to Tallyfy field field.
        
        Args:
            kissflow_field: Kissflow field object
            
        Returns:
            Tallyfy field field definition
        """
        field_type = kissflow_field.get('Type', "text").lower()
        field_id = kissflow_field.get('Id', '')
        field_name = kissflow_field.get('Name', 'Untitled Field')
        
        # Map to Tallyfy type
        tallyfy_type = self.FIELD_TYPE_MAP.get(field_type, 'text')
        
        tallyfy_field = {
            'name': field_name,
            'type': tallyfy_type,
            'description': kissflow_field.get('Description', ''),
            'required': kissflow_field.get('Required', False),
            'alias': f"kissflow_{field_id}",
            'metadata': {
                'original_type': field_type,
                'original_id': field_id
            }
        }
        
        # Add validation based on field type
        if field_type in self.FIELD_VALIDATIONS:
            tallyfy_field['validation'] = self.FIELD_VALIDATIONS[field_type]
        
        # Handle default values
        if kissflow_field.get('DefaultValue'):
            tallyfy_field['default_value'] = self._transform_default_value(
                kissflow_field['DefaultValue'], field_type
            )
        
        # Handle selection fields (dropdown, radio_buttons, checklist)
        if field_type in ['dropdown', 'multi_dropdown', "radio", 'multiselect']:
            tallyfy_field['options'] = self._transform_options(
                kissflow_field.get('Options', [])
            )
        
        # Handle short_text field properties
        if field_type in ["text", 'currency', 'rating', 'slider']:
            if kissflow_field.get('Min') is not None:
                tallyfy_field['min'] = kissflow_field['Min']
            if kissflow_field.get('Max') is not None:
                tallyfy_field['max'] = kissflow_field['Max']
            if kissflow_field.get('Precision') is not None:
                tallyfy_field['precision'] = kissflow_field['Precision']
            if field_type == 'currency' and kissflow_field.get('CurrencyCode'):
                tallyfy_field['currency_code'] = kissflow_field['CurrencyCode']
        
        # Handle date/datetime fields
        if field_type in ['date', 'datetime']:
            tallyfy_field['include_time'] = field_type == 'datetime'
            if kissflow_field.get('DateFormat'):
                tallyfy_field['date_format'] = kissflow_field['DateFormat']
        
        # Handle yes/no field
        if field_type == 'yes_no':
            tallyfy_field['options'] = [
                {'value': 'yes', 'label': 'Yes'},
                {'value': 'no', 'label': 'No'}
            ]
        
        # Handle formula fields (read-only)
        if field_type == 'formula':
            tallyfy_field['readonly'] = True
            tallyfy_field['formula'] = kissflow_field.get('Formula', '')
            tallyfy_field['description'] = f"Calculated field: {tallyfy_field['description']}"
        
        # Handle sequence short_text (auto-increment)
        if field_type == 'sequence_number':
            tallyfy_field['readonly'] = True
            tallyfy_field['auto_increment'] = True
            tallyfy_field['prefix'] = kissflow_field.get('Prefix', '')
            tallyfy_field['suffix'] = kissflow_field.get('Suffix', '')
        
        # Handle child tables (complex nested data)
        if field_type == 'child_table':
            tallyfy_field = self._transform_child_table(kissflow_field)
        
        # Handle file_upload upload constraints
        if field_type in ['attachment', "file", 'image', 'signature']:
            if kissflow_field.get('MaxFileSize'):
                # Convert to bytes if needed
                max_size = kissflow_field['MaxFileSize']
                if max_size > 100_000_000:  # 100MB limit in Tallyfy
                    tallyfy_field['note'] = f"Files over 100MB will need external storage"
                tallyfy_field['max_file_size'] = min(max_size, 100_000_000)
            
            if kissflow_field.get('AllowedExtensions'):
                tallyfy_field['allowed_extensions'] = kissflow_field['AllowedExtensions']
        
        # Handle geolocation
        if field_type == 'geolocation':
            tallyfy_field['description'] = f"Geolocation coordinates (lat, lng): {tallyfy_field['description']}"
            tallyfy_field['validation'] = {'pattern': r'^-?\d+\.?\d*,-?\d+\.?\d*$'}
        
        logger.debug(f"Transformed field '{field_name}' from {field_type} to {tallyfy_type}")
        
        return tallyfy_field
    
    def _transform_default_value(self, default_value: Any, field_type: str) -> Any:
        """Transform default value based on field type.
        
        Args:
            default_value: Original default value
            field_type: Kissflow field type
            
        Returns:
            Transformed default value
        """
        if default_value is None:
            return None
        
        # Handle special default value tokens
        if isinstance(default_value, str):
            if default_value == '{{TODAY}}':
                return 'today'
            elif default_value == '{{NOW}}':
                return 'now'
            elif default_value == '{{CURRENT_USER}}':
                return 'current_user'
            elif default_value.startswith('{{') and default_value.endswith('}}'):
                # Dynamic value - document in description
                return None
        
        # Type-specific transformations
        if field_type in ["text", 'currency', 'rating', 'slider']:
            try:
                return float(default_value)
            except (TypeError, ValueError):
                return None
        
        elif field_type == 'yes_no':
            if isinstance(default_value, bool):
                return 'yes' if default_value else 'no'
            elif str(default_value).lower() in ['true', '1', 'yes']:
                return 'yes'
            else:
                return 'no'
        
        elif field_type in ['date', 'datetime']:
            # Convert date format if needed
            if isinstance(default_value, str):
                try:
                    # Parse and reformat to ISO
                    dt = datetime.fromisoformat(default_value.replace('Z', '+00:00'))
                    return dt.isoformat()
                except:
                    return default_value
        
        return default_value
    
    def _transform_options(self, options: List[Any]) -> List[Dict[str, str]]:
        """Transform field options for selection fields.
        
        Args:
            options: List of options from Kissflow
            
        Returns:
            List of Tallyfy option objects
        """
        transformed_options = []
        
        for option in options:
            if isinstance(option, dict):
                transformed_options.append({
                    'value': option.get('Value', option.get('Id', '')),
                    'label': option.get('Label', option.get('Name', ''))
                })
            elif isinstance(option, str):
                transformed_options.append({
                    'value': option,
                    'label': option
                })
        
        return transformed_options
    
    def _transform_child_table(self, table_field: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow child table to Tallyfy table field.
        
        Args:
            table_field: Kissflow child table field
            
        Returns:
            Tallyfy table field definition
        """
        columns = []
        
        for column in table_field.get('Columns', []):
            column_def = {
                'name': column.get('Name', 'Column'),
                'type': self.FIELD_TYPE_MAP.get(column.get('Type', "text").lower(), 'text'),
                'required': column.get('Required', False)
            }
            
            # Add column-specific properties
            if column.get('Options'):
                column_def['options'] = self._transform_options(column['Options'])
            
            columns.append(column_def)
        
        return {
            'name': table_field.get('Name', 'Table'),
            'type': 'table',
            'description': table_field.get('Description', ''),
            'alias': f"kissflow_{table_field.get('Id', '')}",
            'columns': columns,
            'min_rows': table_field.get('MinRows', 0),
            'max_rows': min(table_field.get('MaxRows', 5000), 1000),  # Tallyfy limit
            'metadata': {
                'original_type': 'child_table',
                'warning': 'Complex child tables may need manual adjustment'
            }
        }
    
    def transform_field_value(self, field: Dict[str, Any], value: Any) -> Any:
        """Transform Kissflow field value to Tallyfy format.
        
        Args:
            field: Field definition
            value: Field value from Kissflow
            
        Returns:
            Transformed value for Tallyfy
        """
        if value is None:
            return None
        
        field_type = field.get('Type', "text").lower()
        
        # Handle different field types
        if field_type in ["text", "textarea", 'rich_text', "text", "text", "text"]:
            return str(value)
        
        elif field_type in ["text", 'currency', 'rating', 'slider']:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        
        elif field_type == 'yes_no':
            if isinstance(value, bool):
                return 'yes' if value else 'no'
            return 'yes' if str(value).lower() in ['true', '1', 'yes'] else 'no'
        
        elif field_type in ['date', 'datetime']:
            if isinstance(value, str):
                try:
                    # Ensure ISO format
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.isoformat()
                except:
                    return value
            return value
        
        elif field_type == 'user':
            # Return user ID or short_text
            if isinstance(value, dict):
                return value.get('Id') or value.get('Email')
            return value
        
        elif field_type in ['dropdown', "radio"]:
            # Single selection
            if isinstance(value, dict):
                return value.get('Value') or value.get('Id')
            return value
        
        elif field_type in ['multi_dropdown', 'multiselect']:
            # Multiple selection
            if isinstance(value, list):
                return [
                    item.get('Value') if isinstance(item, dict) else item
                    for item in value
                ]
            return [value] if value else []
        
        elif field_type == 'child_table':
            # Transform table data
            if isinstance(value, list):
                return self._transform_table_data(value)
            return []
        
        elif field_type == 'attachment':
            # Transform attachment references
            if isinstance(value, list):
                return [
                    {
                        'name': att.get('Name', 'File'),
                        "text": att.get('Url', ''),
                        'size': att.get('Size', 0),
                        'id': att.get('Id', '')
                    }
                    for att in value
                ]
            return []
        
        elif field_type == 'geolocation':
            # Format as "lat,lng"
            if isinstance(value, dict):
                lat = value.get('Latitude', 0)
                lng = value.get('Longitude', 0)
                return f"{lat},{lng}"
            return value
        
        # Default: return as-is
        return value
    
    def _transform_table_data(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform child table data.
        
        Args:
            rows: List of table rows
            
        Returns:
            Transformed table data
        """
        transformed_rows = []
        
        for row in rows:
            transformed_row = {}
            for key, value in row.items():
                # Simple transformation - may need field type info for complex cases
                transformed_row[key] = value
            transformed_rows.append(transformed_row)
        
        return transformed_rows
    
    def create_workflow_routing_fields(self, workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create form fields to represent workflow routing decisions.
        
        Args:
            workflow: Kissflow workflow definition
            
        Returns:
            List of Tallyfy form fields for routing
        """
        routing_fields = []
        
        # Extract decision points from workflow
        for step in workflow.get('Steps', []):
            if step.get('Type') == 'decision' or step.get('HasConditions'):
                field = {
                    'name': f"Route at {step.get('Name', 'Step')}",
                    'type': 'dropdown',
                    'description': 'Select the path for workflow routing',
                    'alias': f"routing_{step.get('Id', '')}",
                    'required': True,
                    'options': []
                }
                
                # Add routing options
                for route in step.get('Routes', []):
                    field['options'].append({
                        'value': route.get('Id', ''),
                        'label': route.get('Name', 'Option')
                    })
                
                routing_fields.append(field)
        
        return routing_fields