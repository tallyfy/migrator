"""
Typeform Template Transformer
Transforms Typeform forms to Tallyfy blueprints
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateTransformer:
    """Transform Typeform forms to Tallyfy blueprints"""
    
    def __init__(self, field_transformer, ai_client: Optional[Any] = None):
        """Initialize template transformer"""
        self.field_transformer = field_transformer
        self.ai_client = ai_client
        logger.info("Typeform template transformer initialized")
    
    def transform(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Typeform form to Tallyfy blueprint"""
        
        # Extract form metadata
        form_id = form.get('id', '')
        title = form.get('title', 'Untitled Form')
        fields = form.get('fields', [])
        
        # Assess form complexity
        complexity = self._assess_complexity(form)
        
        logger.info(f"Transforming Typeform '{title}' with {len(fields)} fields, complexity: {complexity}")
        
        if complexity == 'simple':
            return self._create_simple_blueprint(form)
        elif complexity == 'medium':
            return self._create_sectioned_blueprint(form)
        else:
            return self._create_complex_blueprint(form)
    
    def _assess_complexity(self, form: Dict[str, Any]) -> str:
        """Assess form complexity for transformation strategy"""
        fields = form.get('fields', [])
        field_count = len(fields)
        
        # Check for complex features
        has_logic = self._has_logic_jumps(form)
        has_payment = self._has_payment_fields(fields)
        has_calculations = self._has_calculations(form)
        
        # Use AI if available
        if self.ai_client and self.ai_client.enabled:
            context = {
                'field_count': field_count,
                'has_logic': has_logic,
                'has_payment': has_payment,
                'has_calculations': has_calculations,
                'form_title': form.get('title', ''),
                'vendor': 'typeform'
            }
            
            result = self.ai_client.assess_form_complexity(context)
            if result and result.get('confidence', 0) > 0.7:
                return result.get('complexity', 'medium')
        
        # Fallback heuristics
        if field_count <= 15 and not has_logic and not has_payment:
            return 'simple'
        elif field_count <= 30 or has_logic:
            return 'medium'
        else:
            return 'complex'
    
    def _create_simple_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple blueprint with kickoff form"""
        fields = form.get('fields', [])
        
        # Transform all fields
        tallyfy_fields = self.field_transformer.transform_batch(fields)
        
        blueprint = {
            'name': form.get('title', 'Untitled Form'),
            'description': self._get_form_description(form),
            'metadata': {
                'source': 'typeform',
                'typeform_id': form.get('id'),
                'typeform_type': form.get('type', 'form'),
                'created_at': form.get('created_at'),
                'last_updated_at': form.get('last_updated_at'),
                'response_count': form.get('_count', {}).get('responses', 0),
                'complexity': 'simple'
            },
            'kickoff_form': {
                'fields': tallyfy_fields
            },
            'steps': [
                {
                    'name': 'Review Submission',
                    'type': 'task',
                    'description': 'Review the form submission and verify all data',
                    'assigned_to': 'process_owner'
                },
                {
                    'name': 'Process Response',
                    'type': 'task',
                    'description': 'Process the submission according to business rules',
                    'assigned_to': 'process_owner'
                }
            ]
        }
        
        # Add thank you message as final step if exists
        if form.get('thankyou_screens'):
            blueprint['steps'].append({
                'name': 'Send Confirmation',
                'type': 'task',
                'description': self._extract_thank_you_message(form),
                'assigned_to': 'process_owner'
            })
        
        return blueprint
    
    def _create_sectioned_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Create blueprint with sections as steps"""
        fields = form.get('fields', [])
        sections = self._group_fields_into_sections(fields)
        
        blueprint = {
            'name': form.get('title', 'Untitled Form'),
            'description': self._get_form_description(form),
            'metadata': {
                'source': 'typeform',
                'typeform_id': form.get('id'),
                'field_count': len(fields),
                'section_count': len(sections),
                'complexity': 'medium'
            },
            'steps': []
        }
        
        # Create form step for each section
        for idx, section in enumerate(sections):
            section_fields = self.field_transformer.transform_batch(section['fields'])
            
            step = {
                'name': section.get('name', f'Section {idx + 1}'),
                'type': 'form',
                'description': section.get('description', ''),
                'form_fields': section_fields,
                'assigned_to': 'process_owner'
            }
            blueprint['steps'].append(step)
        
        # Add processing steps
        blueprint['steps'].extend([
            {
                'name': 'Validate Submission',
                'type': 'approval',
                'description': 'Validate all submitted data for completeness and accuracy',
                'assigned_to': 'manager'
            },
            {
                'name': 'Process Data',
                'type': 'task',
                'description': 'Process the validated submission',
                'assigned_to': 'process_owner'
            }
        ])
        
        return blueprint
    
    def _create_complex_blueprint(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Create complex multi-step workflow"""
        fields = form.get('fields', [])
        
        # Use AI to determine optimal grouping if available
        if self.ai_client and self.ai_client.enabled:
            field_groups = self.ai_client.determine_workflow_steps({
                'fields': fields,
                'form_title': form.get('title'),
                'field_count': len(fields)
            })
            
            if field_groups and field_groups.get('confidence', 0) > 0.7:
                groups = field_groups.get('groups', [])
            else:
                groups = self._intelligent_field_grouping(fields)
        else:
            groups = self._intelligent_field_grouping(fields)
        
        blueprint = {
            'name': form.get('title', 'Untitled Form'),
            'description': self._get_form_description(form),
            'metadata': {
                'source': 'typeform',
                'typeform_id': form.get('id'),
                'field_count': len(fields),
                'step_count': len(groups),
                'complexity': 'complex',
                'has_logic': self._has_logic_jumps(form),
                'has_calculations': self._has_calculations(form)
            },
            'steps': []
        }
        
        # Create steps for each field group
        for group in groups:
            group_fields = self.field_transformer.transform_batch(group['fields'])
            
            step = {
                'name': group['name'],
                'type': 'form',
                'description': group.get('description', ''),
                'form_fields': group_fields,
                'assigned_to': 'process_owner'
            }
            blueprint['steps'].append(step)
            
            # Add validation step if needed
            if group.get('requires_validation'):
                blueprint['steps'].append({
                    'name': f"Validate {group['name']}",
                    'type': 'approval',
                    'description': f"Validate {group['name']} data before proceeding",
                    'assigned_to': 'manager'
                })
        
        # Add final processing
        blueprint['steps'].extend([
            {
                'name': 'Final Review',
                'type': 'approval',
                'description': 'Final review of all submitted data',
                'assigned_to': 'manager'
            },
            {
                'name': 'Complete Processing',
                'type': 'task',
                'description': 'Complete final processing and archival',
                'assigned_to': 'process_owner'
            }
        ])
        
        return blueprint
    
    def _group_fields_into_sections(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group fields into logical sections"""
        sections = []
        current_section = {'name': 'Section 1', 'fields': []}
        
        for field in fields:
            # Check if field is a group/section marker
            if field.get('type') == 'group':
                # Save current section if it has fields
                if current_section['fields']:
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    'name': field.get('title', f'Section {len(sections) + 1}'),
                    'description': field.get('properties', {}).get('description', ''),
                    'fields': []
                }
            else:
                current_section['fields'].append(field)
                
                # Create new section every 10 fields
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
        
        # Categorize fields
        personal_fields = []
        contact_fields = []
        preference_fields = []
        payment_fields = []
        other_fields = []
        
        for field in fields:
            field_type = field.get('type', '')
            field_title = field.get('title', '').lower()
            
            if field_type == 'payment':
                payment_fields.append(field)
            elif any(keyword in field_title for keyword in ['name', 'age', 'birth', 'gender', 'title']):
                personal_fields.append(field)
            elif field_type in ['email', 'phone_number'] or \
                 any(keyword in field_title for keyword in ['email', 'phone', 'address', 'contact']):
                contact_fields.append(field)
            elif any(keyword in field_title for keyword in ['prefer', 'interest', 'option', 'choice', 'select']):
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
                'name': 'Preferences & Options',
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
        
        # Add payment fields last
        if payment_fields:
            groups.append({
                'name': 'Payment Information',
                'fields': payment_fields,
                'requires_validation': True,
                'description': 'Payment processing requires manual setup in Tallyfy'
            })
        
        return groups
    
    def _has_logic_jumps(self, form: Dict[str, Any]) -> bool:
        """Check if form has logic jumps"""
        for field in form.get('fields', []):
            if field.get('logic'):
                return True
        
        # Check for form-level logic
        if form.get('logic'):
            return True
        
        return False
    
    def _has_payment_fields(self, fields: List[Dict[str, Any]]) -> bool:
        """Check if form has payment fields"""
        for field in fields:
            if field.get('type') == 'payment':
                return True
        return False
    
    def _has_calculations(self, form: Dict[str, Any]) -> bool:
        """Check if form has calculated fields"""
        for field in form.get('fields', []):
            if field.get('properties', {}).get('calculation'):
                return True
        
        # Check for variables/calculations
        if form.get('variables'):
            return True
        
        return False
    
    def _get_form_description(self, form: Dict[str, Any]) -> str:
        """Extract form description"""
        # Try welcome screen first
        welcome_screens = form.get('welcome_screens', [])
        if welcome_screens:
            welcome = welcome_screens[0]
            title = welcome.get('title', '')
            description = welcome.get('properties', {}).get('description', '')
            return f"{title}\n{description}".strip()
        
        # Fallback to settings description
        settings = form.get('settings', {})
        return settings.get('meta', {}).get('description', '')
    
    def _extract_thank_you_message(self, form: Dict[str, Any]) -> str:
        """Extract thank you message for confirmation step"""
        thankyou_screens = form.get('thankyou_screens', [])
        if thankyou_screens:
            thankyou = thankyou_screens[0]
            title = thankyou.get('title', 'Thank you!')
            msg = thankyou.get('properties', {}).get('description', '')
            return f"Send confirmation: {title} - {msg}"
        
        return 'Send standard confirmation to submitter'
    
    def transform_batch(self, forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple forms"""
        blueprints = []
        
        for form in forms:
            try:
                blueprint = self.transform(form)
                blueprints.append(blueprint)
                logger.info(f"Successfully transformed form '{form.get('title')}'")
            except Exception as e:
                logger.error(f"Failed to transform form '{form.get('title')}': {e}")
        
        return blueprints