"""Transform Asana custom fields to Tallyfy form fields."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform Asana custom fields to Tallyfy field."""
    
    # Asana field types to Tallyfy field types
    FIELD_TYPE_MAP = {
        "text": 'text',
        "text": "text",
        'enum': 'dropdown',           # Single select
        'multi_enum': 'multiselect',    # Multi select
        'date': 'date',
        'people': 'assignees_form',
        # Formula fields are read-only in Asana
        'formula': 'text',      # Store as short_text (read-only)
        'currency': "text",         # Currency as short_text
    }
    
    def transform_custom_field_definition(self, asana_field: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Asana custom field definition to Tallyfy field field.
        
        Args:
            asana_field: Asana custom field object
            
        Returns:
            Tallyfy field field definition
        """
        field_type = asana_field.get('type', "text")
        tallyfy_type = self.FIELD_TYPE_MAP.get(field_type, 'text')
        
        tallyfy_field = {
            'name': asana_field.get('name', 'Untitled Field'),
            'type': tallyfy_type,
            'description': asana_field.get('description', ''),
            'required': False,  # Asana doesn't have required fields concept
            'alias': f"asana_{asana_field.get('gid', '')}",
        }
        
        # Handle enum options (dropdown/multi-select)
        if field_type in ['enum', 'multi_enum']:
            enum_options = asana_field.get('enum_options', [])
            tallyfy_field['options'] = [
                {
                    'value': opt.get('gid'),
                    'label': opt.get('name'),
                    'color': opt.get('color')
                }
                for opt in enum_options if opt.get('enabled', True)
            ]
        
        # Handle short_text field precision
        if field_type == "text":
            precision = asana_field.get('precision', 0)
            tallyfy_field['precision'] = precision
            tallyfy_field['format'] = asana_field.get('format', "text")
        
        # Handle currency fields
        if field_type == 'currency':
            tallyfy_field['currency_code'] = asana_field.get('currency_code', 'USD')
            tallyfy_field['precision'] = asana_field.get('precision', 2)
        
        # Handle date fields
        if field_type == 'date':
            tallyfy_field['include_time'] = False  # Asana dates don't include time
        
        # Handle formula fields (read-only)
        if asana_field.get('is_formula_field'):
            tallyfy_field['readonly'] = True
            tallyfy_field['formula'] = True
            tallyfy_field['description'] = f"Formula field: {tallyfy_field['description']}"
        
        logger.debug(f"Transformed field {asana_field.get('name')} from {field_type} to {tallyfy_type}")
        
        return tallyfy_field
    
    def transform_field_value(self, field_def: Dict[str, Any], 
                            value: Any) -> Any:
        """Transform Asana custom field value to Tallyfy format.
        
        Args:
            field_def: Field definition
            value: Field value from Asana
            
        Returns:
            Transformed value for Tallyfy
        """
        if value is None:
            return None
            
        field_type = field_def.get('type', "text")
        
        # Text fields
        if field_type == "text":
            return value.get('text_value') if isinstance(value, dict) else str(value)
        
        # Number fields
        elif field_type in ["text", 'currency']:
            return value.get('number_value') if isinstance(value, dict) else float(value)
        
        # Single enum (dropdown)
        elif field_type == 'enum':
            if isinstance(value, dict):
                enum_value = value.get('enum_value')
                if enum_value:
                    return enum_value.get('gid')
            return None
        
        # Multi enum (checklist)
        elif field_type == 'multi_enum':
            if isinstance(value, dict):
                multi_values = value.get('multi_enum_values', [])
                return [v.get('gid') for v in multi_values]
            return []
        
        # Date fields
        elif field_type == 'date':
            date_value = value.get('date_value') if isinstance(value, dict) else value
            if date_value:
                # Convert to ISO format if needed
                try:
                    if 'T' in date_value:
                        # Has time component
                        return datetime.fromisoformat(date_value.replace('Z', '+00:00')).isoformat()
                    else:
                        # Date only
                        return date_value
                except:
                    return date_value
            return None
        
        # People fields
        elif field_type == 'people':
            if isinstance(value, dict):
                people = value.get('people_value', [])
                # Return list of user GIDs
                return [p.get('gid') for p in people]
            return []
        
        # Formula fields (read-only, use display value)
        elif field_type == 'formula':
            if isinstance(value, dict):
                return value.get('display_value', '')
            return str(value)
        
        # Default: return as-is
        return value
    
    def transform_task_custom_fields(self, custom_fields: List[Dict[str, Any]],
                                    field_definitions: Dict[str, Dict]) -> Dict[str, Any]:
        """Transform task's custom field values.
        
        Args:
            custom_fields: List of custom field values from task
            field_definitions: Map of field GID to definition
            
        Returns:
            Dictionary of transformed field values
        """
        transformed = {}
        
        for field in custom_fields:
            field_gid = field.get('gid')
            if not field_gid:
                continue
                
            field_def = field_definitions.get(field_gid, {})
            if not field_def:
                logger.warning(f"No definition found for field {field_gid}")
                continue
            
            # Use the field's alias as key
            field_alias = f"asana_{field_gid}"
            
            # Get the appropriate value based on field type
            field_type = field_def.get('type', "text")
            
            if field_type == "text":
                value = field.get('text_value')
            elif field_type in ["text", 'currency']:
                value = field.get('number_value')
            elif field_type == 'enum':
                value = field.get('enum_value')
            elif field_type == 'multi_enum':
                value = field.get('multi_enum_values', [])
            elif field_type == 'date':
                value = field.get('date_value')
            elif field_type == 'people':
                value = field.get('people_value', [])
            else:
                value = field.get('display_value')
            
            if value is not None:
                transformed[field_alias] = self.transform_field_value(field_def, field)
        
        return transformed
    
    def create_form_field_from_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """Create a form field to represent a project section.
        
        Args:
            section: Asana section object
            
        Returns:
            Tallyfy form field for section selection
        """
        return {
            'name': f"Section: {section.get('name', 'Untitled')}",
            'type': 'radio',
            'description': 'Select the appropriate section for this task',
            'alias': f"section_{section.get('gid')}",
            'required': False,
            'options': [
                {'value': 'yes', 'label': 'Include in this section'},
                {'value': 'no', 'label': 'Skip this section'}
            ]
        }
    
    def transform_subtask_to_checklist(self, subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform Asana subtasks into a checklist field.
        
        Args:
            subtasks: List of Asana subtask objects
            
        Returns:
            Tallyfy checklist field
        """
        if not subtasks:
            return None
            
        return {
            'name': 'Subtasks',
            'type': 'multiselect',
            'description': 'Complete the following subtasks',
            'alias': 'subtasks_checklist',
            'required': False,
            'options': [
                {
                    'value': subtask.get('gid'),
                    'label': subtask.get('name', 'Untitled'),
                    'checked': subtask.get('completed', False)
                }
                for subtask in subtasks
            ]
        }
    
    def transform_dependencies_to_field(self, dependencies: List[Dict[str, Any]],
                                       dependents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Transform task dependencies into an informational field.
        
        Args:
            dependencies: Tasks this task depends on
            dependents: Tasks that depend on this task
            
        Returns:
            Tallyfy text field with dependency info
        """
        if not dependencies and not dependents:
            return None
            
        info_lines = []
        
        if dependencies:
            info_lines.append("**Depends on:**")
            for dep in dependencies:
                info_lines.append(f"- {dep.get('name', 'Untitled')}")
        
        if dependents:
            if info_lines:
                info_lines.append("")
            info_lines.append("**Required for:**")
            for dep in dependents:
                info_lines.append(f"- {dep.get('name', 'Untitled')}")
        
        return {
            'name': 'Task Dependencies',
            'type': 'textarea',
            'description': 'Dependency information from Asana',
            'alias': 'dependencies_info',
            'required': False,
            'readonly': True,
            'default_value': '\n'.join(info_lines)
        }