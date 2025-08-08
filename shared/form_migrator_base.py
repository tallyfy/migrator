"""
Base Form Migrator
Shared functionality for form-based migration tools (Typeform, Jotform, Google Forms, Cognito Forms)
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class FormMigratorBase(ABC):
    """Base class for form-based migrators"""
    
    def __init__(self, vendor_name: str):
        """Initialize base form migrator"""
        self.vendor_name = vendor_name
        self.migration_id = f"{vendor_name}_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Common field type mappings
        self.field_type_map = {
            # Text types
            'text': 'text',
            'short_text': 'text',
            'long_text': 'textarea',
            'paragraph': 'textarea',
            'essay': 'textarea',
            
            # Choice types
            'radio': 'radio',
            'checkbox': 'multiselect',
            'dropdown': 'dropdown',
            'select': 'dropdown',
            'multiple_choice': 'radio',
            'single_choice': 'radio',
            'multi_choice': 'multiselect',
            
            # Special types
            'email': 'email',
            'number': 'text',  # With validation
            'phone': 'text',   # With validation
            'url': 'text',     # With validation
            'date': 'date',
            'time': 'text',    # With time format
            'datetime': 'date',
            'file': 'file',
            'upload': 'file',
            'signature': 'file',
            'payment': 'text',  # Note field
            
            # Scale/Rating
            'rating': 'dropdown',
            'scale': 'dropdown',
            'nps': 'dropdown',
            'likert': 'dropdown',
            
            # Boolean
            'yes_no': 'radio',
            'true_false': 'radio',
            'boolean': 'radio',
            
            # Complex
            'matrix': 'table',
            'grid': 'table',
            'ranking': 'multiselect',
            'address': 'textarea',
            'name': 'text'
        }
        
        logger.info(f"Initialized {vendor_name} form migrator")
    
    @abstractmethod
    def get_forms(self) -> List[Dict[str, Any]]:
        """Get all forms from vendor - must be implemented by subclass"""
        pass
    
    @abstractmethod
    def get_form_details(self, form_id: str) -> Dict[str, Any]:
        """Get form details including fields - must be implemented by subclass"""
        pass
    
    @abstractmethod
    def get_form_responses(self, form_id: str) -> List[Dict[str, Any]]:
        """Get form responses/submissions - must be implemented by subclass"""
        pass
    
    def transform_form_to_blueprint(self, form: Dict[str, Any], 
                                  ai_client: Optional[Any] = None) -> Dict[str, Any]:
        """Transform vendor form to Tallyfy blueprint"""
        
        # Assess form complexity
        field_count = len(form.get('fields', []))
        has_logic = self._has_conditional_logic(form)
        has_payments = self._has_payment_fields(form)
        
        complexity = self._assess_complexity(field_count, has_logic, has_payments, ai_client)
        
        if complexity == 'simple':
            # Single kickoff form
            return self._create_simple_blueprint(form)
        elif complexity == 'medium':
            # Multi-section workflow
            return self._create_sectioned_blueprint(form)
        else:
            # Complex multi-step workflow
            return self._create_complex_blueprint(form)
    
    def _assess_complexity(self, field_count: int, has_logic: bool, 
                          has_payments: bool, ai_client: Optional[Any] = None) -> str:
        """Assess form complexity for transformation strategy"""
        
        if ai_client and ai_client.enabled:
            # Use AI for assessment
            context = {
                'field_count': field_count,
                'has_logic': has_logic,
                'has_payments': has_payments,
                'vendor': self.vendor_name
            }
            result = ai_client.assess_form_complexity(context)
            if result and result.get('confidence', 0) > 0.7:
                return result.get('complexity', 'medium')
        
        # Fallback heuristics
        if field_count <= 10 and not has_logic and not has_payments:
            return 'simple'
        elif field_count <= 25 or has_logic:
            return 'medium'
        else:
            return 'complex'
    
    def _create_simple_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple blueprint with kickoff form"""
        fields = self._transform_fields(form.get('fields', []))
        
        return {
            'name': form.get('title', 'Untitled Form'),
            'description': form.get('description', ''),
            'metadata': {
                'source': self.vendor_name,
                'original_id': form.get('id'),
                'created_at': form.get('created_at'),
                'response_count': form.get('response_count', 0)
            },
            'kickoff_form': {
                'fields': fields
            },
            'steps': [
                {
                    'name': 'Review Submission',
                    'type': 'task',
                    'description': 'Review and process the form submission'
                },
                {
                    'name': 'Send Confirmation',
                    'type': 'task',
                    'description': 'Send confirmation to submitter'
                }
            ]
        }
    
    def _create_sectioned_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Create blueprint with sections as steps"""
        sections = self._group_fields_into_sections(form.get('fields', []))
        
        blueprint = {
            'name': form.get('title', 'Untitled Form'),
            'description': form.get('description', ''),
            'metadata': {
                'source': self.vendor_name,
                'original_id': form.get('id'),
                'complexity': 'medium'
            },
            'steps': []
        }
        
        # Create step for each section
        for idx, section in enumerate(sections):
            step = {
                'name': section.get('name', f'Section {idx + 1}'),
                'type': 'form',
                'form_fields': self._transform_fields(section.get('fields', []))
            }
            blueprint['steps'].append(step)
        
        # Add processing steps
        blueprint['steps'].extend([
            {
                'name': 'Validate Submission',
                'type': 'approval',
                'description': 'Validate all form data'
            },
            {
                'name': 'Process Data',
                'type': 'task',
                'description': 'Process the submitted information'
            }
        ])
        
        return blueprint
    
    def _create_complex_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Create complex multi-step workflow"""
        # Group fields logically
        field_groups = self._intelligent_field_grouping(form.get('fields', []))
        
        blueprint = {
            'name': form.get('title', 'Untitled Form'),
            'description': form.get('description', ''),
            'metadata': {
                'source': self.vendor_name,
                'original_id': form.get('id'),
                'complexity': 'complex',
                'original_field_count': len(form.get('fields', []))
            },
            'steps': []
        }
        
        # Create steps for each field group
        for group in field_groups:
            step = {
                'name': group['name'],
                'type': 'form',
                'description': group.get('description', ''),
                'form_fields': self._transform_fields(group['fields'])
            }
            
            # Add validation if needed
            if group.get('requires_validation'):
                blueprint['steps'].append(step)
                blueprint['steps'].append({
                    'name': f'Validate {group["name"]}',
                    'type': 'approval',
                    'description': f'Validate {group["name"]} data'
                })
            else:
                blueprint['steps'].append(step)
        
        # Add final processing
        blueprint['steps'].append({
            'name': 'Final Review',
            'type': 'approval',
            'description': 'Final review of all submitted data'
        })
        
        return blueprint
    
    def _transform_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform vendor fields to Tallyfy format"""
        transformed = []
        
        for field in fields:
            field_type = field.get('type', 'text')
            tallyfy_type = self.field_type_map.get(field_type, 'text')
            
            tallyfy_field = {
                'type': tallyfy_type,
                'label': field.get('label', field.get('title', '')),
                'name': field.get('name', field.get('id', '')),
                'required': field.get('required', False),
                'help_text': field.get('description', field.get('help_text', '')),
                'metadata': {
                    'original_type': field_type,
                    'original_id': field.get('id'),
                    f'{self.vendor_name}_properties': field.get('properties', {})
                }
            }
            
            # Handle options for choice fields
            if tallyfy_type in ['radio', 'dropdown', 'multiselect']:
                options = field.get('options', field.get('choices', []))
                tallyfy_field['options'] = self._transform_options(options)
            
            # Add validation
            validation = self._get_field_validation(field_type, field)
            if validation:
                tallyfy_field['validation'] = validation
            
            # Handle default values
            if field.get('default_value'):
                tallyfy_field['default_value'] = str(field['default_value'])
            
            transformed.append(tallyfy_field)
        
        return transformed
    
    def _transform_options(self, options: List[Any]) -> List[Dict[str, str]]:
        """Transform field options to Tallyfy format"""
        transformed = []
        
        for option in options:
            if isinstance(option, dict):
                transformed.append({
                    'value': str(option.get('value', option.get('id', ''))),
                    'label': str(option.get('label', option.get('text', '')))
                })
            else:
                # Simple string option
                transformed.append({
                    'value': str(option),
                    'label': str(option)
                })
        
        return transformed
    
    def _get_field_validation(self, field_type: str, field: Dict[str, Any]) -> Optional[str]:
        """Get validation rules for field"""
        if field_type in ['email']:
            return 'email'
        elif field_type in ['number', 'numeric']:
            min_val = field.get('min')
            max_val = field.get('max')
            rules = ['numeric']
            if min_val is not None:
                rules.append(f'min:{min_val}')
            if max_val is not None:
                rules.append(f'max:{max_val}')
            return '|'.join(rules)
        elif field_type in ['url', 'website']:
            return 'url'
        elif field_type in ['phone', 'phone_number']:
            return 'regex:^[\\d\\s\\-\\+\\(\\)]+$'
        
        return None
    
    def _has_conditional_logic(self, form: Dict[str, Any]) -> bool:
        """Check if form has conditional logic"""
        # Check for logic in fields
        for field in form.get('fields', []):
            if field.get('logic') or field.get('conditions') or field.get('rules'):
                return True
        
        # Check for form-level logic
        if form.get('logic') or form.get('conditional_logic'):
            return True
        
        return False
    
    def _has_payment_fields(self, form: Dict[str, Any]) -> bool:
        """Check if form has payment fields"""
        payment_types = ['payment', 'stripe', 'paypal', 'credit_card', 'billing']
        
        for field in form.get('fields', []):
            if field.get('type', '').lower() in payment_types:
                return True
            if any(p in field.get('label', '').lower() for p in ['payment', 'pay', 'price']):
                return True
        
        return False
    
    def _group_fields_into_sections(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group fields into logical sections"""
        sections = []
        current_section = {'name': 'Section 1', 'fields': []}
        
        for field in fields:
            # Check if field marks a new section
            if field.get('type') in ['section', 'page_break', 'heading']:
                if current_section['fields']:
                    sections.append(current_section)
                current_section = {
                    'name': field.get('label', f'Section {len(sections) + 1}'),
                    'fields': []
                }
            else:
                current_section['fields'].append(field)
                
                # Start new section every 10 fields
                if len(current_section['fields']) >= 10:
                    sections.append(current_section)
                    current_section = {
                        'name': f'Section {len(sections) + 1}',
                        'fields': []
                    }
        
        # Add remaining fields
        if current_section['fields']:
            sections.append(current_section)
        
        return sections
    
    def _intelligent_field_grouping(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Intelligently group fields for complex forms"""
        groups = []
        
        # Group by field categories
        personal_fields = []
        contact_fields = []
        preference_fields = []
        other_fields = []
        
        for field in fields:
            field_label = field.get('label', '').lower()
            field_type = field.get('type', '').lower()
            
            if any(keyword in field_label for keyword in ['name', 'age', 'birth', 'gender']):
                personal_fields.append(field)
            elif any(keyword in field_label for keyword in ['email', 'phone', 'address', 'contact']):
                contact_fields.append(field)
            elif any(keyword in field_label for keyword in ['prefer', 'interest', 'option', 'choice']):
                preference_fields.append(field)
            else:
                other_fields.append(field)
        
        # Create groups
        if personal_fields:
            groups.append({
                'name': 'Personal Information',
                'fields': personal_fields,
                'requires_validation': True
            })
        
        if contact_fields:
            groups.append({
                'name': 'Contact Information',
                'fields': contact_fields,
                'requires_validation': True
            })
        
        if preference_fields:
            groups.append({
                'name': 'Preferences',
                'fields': preference_fields,
                'requires_validation': False
            })
        
        # Split other fields into chunks
        if other_fields:
            for i in range(0, len(other_fields), 8):
                chunk = other_fields[i:i+8]
                groups.append({
                    'name': f'Additional Information {(i//8) + 1}' if i > 0 else 'Additional Information',
                    'fields': chunk,
                    'requires_validation': False
                })
        
        return groups
    
    def transform_responses_to_processes(self, form_id: str, blueprint_id: str,
                                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Transform form responses to Tallyfy processes"""
        responses = self.get_form_responses(form_id)
        
        if limit:
            responses = responses[:limit]
        
        processes = []
        for response in responses:
            process = {
                'checklist_id': blueprint_id,
                'name': f"Submission from {response.get('submitter', 'Anonymous')}",
                'prerun_data': self._extract_response_data(response),
                'metadata': {
                    'source': self.vendor_name,
                    'original_response_id': response.get('id'),
                    'submitted_at': response.get('submitted_at'),
                    'submitter': response.get('submitter')
                }
            }
            processes.append(process)
        
        return processes
    
    def _extract_response_data(self, response: Dict[str, Any]) -> Dict[str, str]:
        """Extract response data for prerun"""
        data = {}
        
        answers = response.get('answers', response.get('data', {}))
        
        for field_id, value in answers.items():
            if value is not None:
                if isinstance(value, (list, dict)):
                    data[field_id] = json.dumps(value)
                else:
                    data[field_id] = str(value)
        
        return data