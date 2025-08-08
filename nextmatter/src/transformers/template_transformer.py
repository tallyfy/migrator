"""
Template Transformer
Transforms vendor templates/workflows to Tallyfy templates
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateTransformer:
    """Transform vendor templates to Tallyfy format"""
    
    def __init__(self, ai_client=None):
        """Initialize template transformer"""
        self.ai_client = ai_client
        self.field_transformer = None  # Set by orchestrator
    
    def transform_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a vendor template to Tallyfy format"""
        try:
            tallyfy_template = {
                'name': template.get('name', 'Untitled Template'),
                'description': template.get('description', ''),
                'steps': self._transform_steps(template),
                'settings': self._transform_settings(template),
                'vendor_metadata': {
                    'original_id': template.get('id', ''),
                    'original_type': template.get('type', ''),
                    'original_data': template
                }
            }
            
            return tallyfy_template
            
        except Exception as e:
            logger.error(f"Error transforming template: {e}")
            return self._create_fallback_template(template)
    
    def _transform_steps(self, template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform template steps"""
        # Override in vendor-specific implementation
        steps = []
        
        # Extract steps/tasks from vendor format
        vendor_steps = template.get('steps', template.get('tasks', []))
        
        for idx, step in enumerate(vendor_steps):
            steps.append({
                'name': step.get('name', f'Step {idx + 1}'),
                'description': step.get('description', ''),
                'type': 'task',
                'fields': self._transform_step_fields(step),
                'assignee': self._transform_assignee(step),
                'due_date': self._transform_due_date(step)
            })
        
        return steps
    
    def _transform_step_fields(self, step: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform fields in a step"""
        if not self.field_transformer:
            return []
        
        fields = []
        vendor_fields = step.get('fields', step.get('questions', []))
        
        for field in vendor_fields:
            transformed = self.field_transformer.transform_field(field)
            if transformed:
                fields.append(transformed)
        
        return fields
    
    def _transform_assignee(self, step: Dict[str, Any]) -> Optional[str]:
        """Transform assignee information"""
        # Override in vendor-specific implementation
        return step.get('assignee', step.get('assigned_to'))
    
    def _transform_due_date(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform due date information"""
        # Override in vendor-specific implementation
        if 'due_date' in step:
            return {'type': 'fixed', 'value': step['due_date']}
        return None
    
    def _transform_settings(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Transform template settings"""
        return {
            'visibility': 'private',
            'allow_comments': True,
            'allow_attachments': True
        }
    
    def _create_fallback_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback template when transformation fails"""
        return {
            'name': str(template.get('name', 'Untitled Template')),
            'description': 'Imported template',
            'steps': [],
            'vendor_metadata': {'original_data': template}
        }
