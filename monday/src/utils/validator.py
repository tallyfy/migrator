"""Validation utilities for Monday.com migration."""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Validator:
    """Validate migration data and transformations."""
    
    # Email regex pattern
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # URL regex pattern  
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    # Phone regex pattern
    PHONE_PATTERN = re.compile(r'^[\d\s\-\+\(\)]+$')
    
    # Required blueprint fields
    REQUIRED_BLUEPRINT_FIELDS = ['name', 'steps']
    
    # Required step fields
    REQUIRED_STEP_FIELDS = ['name', 'type', 'order']
    
    # Valid step types
    VALID_STEP_TYPES = ['task', 'approval', 'form', "text", 'conditional']
    
    # Required user fields
    REQUIRED_USER_FIELDS = ["text", 'firstname']
    
    # Valid user roles
    VALID_USER_ROLES = ['admin', 'member', 'light']
    
    def validate_blueprint(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Tallyfy blueprint structure.
        
        Args:
            blueprint: Blueprint data
            
        Returns:
            Validation result with 'valid' and 'errors' keys
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_BLUEPRINT_FIELDS:
            if field not in blueprint or not blueprint[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate name
        if 'name' in blueprint:
            if len(blueprint['name']) > 255:
                errors.append("Blueprint name exceeds 255 characters")
            if len(blueprint['name']) < 3:
                errors.append("Blueprint name must be at least 3 characters")
        
        # Validate steps
        if 'steps' in blueprint:
            if not isinstance(blueprint['steps'], list):
                errors.append("Steps must be a list")
            elif len(blueprint['steps']) == 0:
                errors.append("Blueprint must have at least one step")
            else:
                # Validate each step
                step_orders = set()
                for i, step in enumerate(blueprint['steps']):
                    step_errors = self._validate_step(step, i)
                    errors.extend(step_errors)
                    
                    # Check for duplicate orders
                    if 'order' in step:
                        if step['order'] in step_orders:
                            errors.append(f"Duplicate step order: {step['order']}")
                        step_orders.add(step['order'])
        
        # Validate kick-off form if present
        if 'kick_off_form' in blueprint:
            form_errors = self._validate_form_fields(blueprint['kick_off_form'])
            errors.extend(form_errors)
        
        # Validate permissions
        if 'permissions' in blueprint:
            perm_errors = self._validate_permissions(blueprint['permissions'])
            errors.extend(perm_errors)
        
        # Check for migration notes (warning, not error)
        if 'migration_notes' in blueprint:
            warnings.append("Blueprint contains migration notes for manual review")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_step(self, step: Dict[str, Any], index: int) -> List[str]:
        """Validate a single step.
        
        Args:
            step: Step data
            index: Step index
            
        Returns:
            List of error messages
        """
        errors = []
        step_ref = f"Step {index + 1}"
        
        # Check required fields
        for field in self.REQUIRED_STEP_FIELDS:
            if field not in step or not step[field]:
                errors.append(f"{step_ref}: Missing required field '{field}'")
        
        # Validate step type
        if 'type' in step:
            if step['type'] not in self.VALID_STEP_TYPES:
                errors.append(f"{step_ref}: Invalid step type '{step['type']}'")
        
        # Validate step name
        if 'name' in step:
            if len(step['name']) > 255:
                errors.append(f"{step_ref}: Step name exceeds 255 characters")
            if len(step['name']) < 1:
                errors.append(f"{step_ref}: Step name cannot be empty")
        
        # Validate order
        if 'order' in step:
            if not isinstance(step['order'], (int, float)):
                errors.append(f"{step_ref}: Step order must be a number")
            elif step['order'] < 1:
                errors.append(f"{step_ref}: Step order must be positive")
        
        # Validate form fields if present
        if 'form_fields' in step:
            form_errors = self._validate_form_fields(step['form_fields'])
            for error in form_errors:
                errors.append(f"{step_ref}: {error}")
        
        # Validate duration
        if 'duration' in step:
            if not isinstance(step['duration'], (int, float)):
                errors.append(f"{step_ref}: Duration must be a number")
            elif step['duration'] < 0:
                errors.append(f"{step_ref}: Duration cannot be negative")
        
        return errors
    
    def _validate_form_fields(self, fields: List[Dict[str, Any]]) -> List[str]:
        """Validate form fields.
        
        Args:
            fields: List of form fields
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not isinstance(fields, list):
            errors.append("Form fields must be a list")
            return errors
        
        field_names = set()
        for i, field in enumerate(fields):
            field_ref = f"Field {i + 1}"
            
            # Check required attributes
            if 'name' not in field:
                errors.append(f"{field_ref}: Missing field name")
            else:
                # Check for duplicate names
                if field['name'] in field_names:
                    errors.append(f"{field_ref}: Duplicate field name '{field['name']}'")
                field_names.add(field['name'])
            
            if 'type' not in field:
                errors.append(f"{field_ref}: Missing field type")
            
            # Validate specific field types
            if field.get('type') == 'dropdown' or field.get('type') == 'radio':
                if 'options' not in field or not field['options']:
                    errors.append(f"{field_ref}: {field['type']} field must have options")
            
            # Validate validation rules if present
            if 'validation' in field:
                val_errors = self._validate_field_validation(field['validation'], field_ref)
                errors.extend(val_errors)
        
        return errors
    
    def _validate_field_validation(self, validation: Dict[str, Any], field_ref: str) -> List[str]:
        """Validate field validation rules.
        
        Args:
            validation: Validation rules
            field_ref: Field reference for error messages
            
        Returns:
            List of error messages
        """
        errors = []
        
        if 'min' in validation and 'max' in validation:
            if validation['min'] > validation['max']:
                errors.append(f"{field_ref}: Min value cannot be greater than max value")
        
        if 'pattern' in validation:
            try:
                re.compile(validation['pattern'])
            except re.error:
                errors.append(f"{field_ref}: Invalid regex pattern")
        
        return errors
    
    def _validate_permissions(self, permissions: Dict[str, Any]) -> List[str]:
        """Validate permissions configuration.
        
        Args:
            permissions: Permissions data
            
        Returns:
            List of error messages
        """
        errors = []
        
        if 'visibility' in permissions:
            valid_visibility = ['private', 'organization', 'public']
            if permissions['visibility'] not in valid_visibility:
                errors.append(f"Invalid visibility: {permissions['visibility']}")
        
        # Check for valid user lists
        for role in ['admins', 'members', 'viewers']:
            if role in permissions:
                if not isinstance(permissions[role], list):
                    errors.append(f"{role} must be a list")
        
        return errors
    
    def validate_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Tallyfy user data.
        
        Args:
            user: User data
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_USER_FIELDS:
            if field not in user or not user[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate short_text
        if "text" in user:
            if not self.EMAIL_PATTERN.match(user["text"]):
                errors.append(f"Invalid email format: {user["text"]}")
        
        # Validate role
        if 'role' in user:
            if user['role'] not in self.VALID_USER_ROLES:
                errors.append(f"Invalid user role: {user['role']}")
        
        # Validate short_text if present
        if "text" in user and user["text"]:
            if not self.PHONE_PATTERN.match(user["text"]):
                warnings.append(f"Phone number may be invalid: {user["text"]}")
        
        # Check name length
        if 'firstname' in user:
            if len(user['firstname']) > 100:
                errors.append("First name exceeds 100 characters")
        
        if 'lastname' in user:
            if len(user['lastname']) > 100:
                errors.append("Last name exceeds 100 characters")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_process(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Tallyfy process data.
        
        Args:
            process: Process data
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Check required fields
        if 'checklist_id' not in process or not process['checklist_id']:
            errors.append("Missing required field: checklist_id")
        
        if 'name' not in process or not process['name']:
            errors.append("Missing required field: name")
        
        # Validate status
        if 'status' in process:
            valid_statuses = ['active', 'completed', 'cancelled', 'archived', 'on_hold']
            if process['status'] not in valid_statuses:
                errors.append(f"Invalid process status: {process['status']}")
        
        # Validate dates
        if 'due_date' in process and process['due_date']:
            try:
                datetime.fromisoformat(process['due_date'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append(f"Invalid due date format: {process['due_date']}")
        
        # Validate priority
        if 'priority' in process:
            valid_priorities = ['critical', 'high', 'medium', 'low']
            if process['priority'] not in valid_priorities:
                errors.append(f"Invalid priority: {process['priority']}")
        
        # Validate data fields
        if 'data' in process:
            if not isinstance(process['data'], dict):
                errors.append("Process data must be a dictionary")
        
        # Check for migration metadata
        if 'metadata' in process:
            if 'source' in process['metadata'] and process['metadata']['source'] != 'monday':
                warnings.append(f"Unexpected source: {process['metadata']['source']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_id_mapping(self, monday_id: str, tallyfy_id: str) -> bool:
        """Validate ID mapping.
        
        Args:
            monday_id: Monday.com ID
            tallyfy_id: Tallyfy ID
            
        Returns:
            True if valid
        """
        if not monday_id or not tallyfy_id:
            return False
        
        # Monday.com IDs are usually numeric strings
        # Tallyfy IDs are usually UUIDs or alphanumeric
        
        if not isinstance(monday_id, str) or not isinstance(tallyfy_id, str):
            return False
        
        return len(monday_id) > 0 and len(tallyfy_id) > 0
    
    def validate_batch(self, items: List[Dict[str, Any]], 
                      item_type: str) -> Dict[str, Any]:
        """Validate a batch of items.
        
        Args:
            items: List of items to validate
            item_type: Type of items (blueprint, user, process)
            
        Returns:
            Batch validation result
        """
        results = {
            'total': len(items),
            'valid': 0,
            'invalid': 0,
            'errors': [],
            'warnings': []
        }
        
        for i, item in enumerate(items):
            # Validate based on type
            if item_type == 'blueprint':
                result = self.validate_blueprint(item)
            elif item_type == 'user':
                result = self.validate_user(item)
            elif item_type == 'process':
                result = self.validate_process(item)
            else:
                result = {'valid': False, 'errors': [f"Unknown item type: {item_type}"]}
            
            if result['valid']:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                for error in result['errors']:
                    results['errors'].append(f"Item {i + 1}: {error}")
            
            if 'warnings' in result:
                for warning in result['warnings']:
                    results['warnings'].append(f"Item {i + 1}: {warning}")
        
        return results
    
    def get_validation_summary(self, validation_results: List[Dict[str, Any]]) -> str:
        """Get formatted validation summary.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Formatted summary string
        """
        total_valid = sum(1 for r in validation_results if r.get('valid', False))
        total_invalid = len(validation_results) - total_valid
        
        all_errors = []
        all_warnings = []
        
        for result in validation_results:
            all_errors.extend(result.get('errors', []))
            all_warnings.extend(result.get('warnings', []))
        
        lines = [
            "Validation Summary",
            "=" * 40,
            f"Total Items: {len(validation_results)}",
            f"Valid: {total_valid}",
            f"Invalid: {total_invalid}"
        ]
        
        if all_errors:
            lines.append(f"\nErrors ({len(all_errors)}):")
            for error in all_errors[:10]:  # Show first 10 errors
                lines.append(f"  - {error}")
            if len(all_errors) > 10:
                lines.append(f"  ... and {len(all_errors) - 10} more errors")
        
        if all_warnings:
            lines.append(f"\nWarnings ({len(all_warnings)}):")
            for warning in all_warnings[:5]:  # Show first 5 warnings
                lines.append(f"  - {warning}")
            if len(all_warnings) > 5:
                lines.append(f"  ... and {len(all_warnings) - 5} more warnings")
        
        return "\n".join(lines)