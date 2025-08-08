#!/bin/bash

# Create transformers for all migrators that need them

MIGRATORS=(
    "wrike"
    "nextmatter"
    "basecamp"
    "jotform"
    "cognito-forms"
    "clickup"
    "trello"
    "google-forms"
)

for MIGRATOR in "${MIGRATORS[@]}"; do
    echo "Creating transformers for $MIGRATOR..."
    
    TRANSFORM_DIR="/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/transformers"
    mkdir -p "$TRANSFORM_DIR"
    
    # Create field transformer if it doesn't exist
    if [ ! -f "$TRANSFORM_DIR/field_transformer.py" ]; then
        cat > "$TRANSFORM_DIR/field_transformer.py" << 'EOF'
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
EOF
        echo "  Created field_transformer.py"
    fi
    
    # Create template transformer if it doesn't exist
    if [ ! -f "$TRANSFORM_DIR/template_transformer.py" ]; then
        cat > "$TRANSFORM_DIR/template_transformer.py" << 'EOF'
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
EOF
        echo "  Created template_transformer.py"
    fi
    
    # Create instance transformer if it doesn't exist
    if [ ! -f "$TRANSFORM_DIR/instance_transformer.py" ]; then
        cat > "$TRANSFORM_DIR/instance_transformer.py" << 'EOF'
"""
Instance Transformer
Transforms vendor instances/runs to Tallyfy runs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform vendor instances to Tallyfy format"""
    
    def __init__(self, ai_client=None):
        """Initialize instance transformer"""
        self.ai_client = ai_client
    
    def transform_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a vendor instance to Tallyfy format"""
        try:
            tallyfy_instance = {
                'name': instance.get('name', 'Untitled Instance'),
                'template_id': instance.get('template_id', ''),
                'status': self._transform_status(instance),
                'created_at': instance.get('created_at', ''),
                'updated_at': instance.get('updated_at', ''),
                'completed_at': instance.get('completed_at'),
                'data': self._transform_instance_data(instance),
                'steps': self._transform_instance_steps(instance),
                'vendor_metadata': {
                    'original_id': instance.get('id', ''),
                    'original_status': instance.get('status', ''),
                    'original_data': instance
                }
            }
            
            return tallyfy_instance
            
        except Exception as e:
            logger.error(f"Error transforming instance: {e}")
            return self._create_fallback_instance(instance)
    
    def _transform_status(self, instance: Dict[str, Any]) -> str:
        """Transform instance status"""
        status = instance.get('status', '').lower()
        
        status_map = {
            'active': 'in_progress',
            'running': 'in_progress',
            'in_progress': 'in_progress',
            'completed': 'completed',
            'done': 'completed',
            'finished': 'completed',
            'cancelled': 'cancelled',
            'canceled': 'cancelled',
            'paused': 'paused',
            'pending': 'pending',
            'draft': 'draft'
        }
        
        return status_map.get(status, 'in_progress')
    
    def _transform_instance_data(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Transform instance data/responses"""
        # Override in vendor-specific implementation
        return instance.get('data', instance.get('responses', {}))
    
    def _transform_instance_steps(self, instance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform instance steps"""
        steps = []
        vendor_steps = instance.get('steps', instance.get('tasks', []))
        
        for step in vendor_steps:
            steps.append({
                'name': step.get('name', ''),
                'status': self._transform_status(step),
                'completed_at': step.get('completed_at'),
                'completed_by': step.get('completed_by'),
                'data': step.get('data', {})
            })
        
        return steps
    
    def _create_fallback_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback instance when transformation fails"""
        return {
            'name': str(instance.get('name', 'Untitled Instance')),
            'status': 'pending',
            'vendor_metadata': {'original_data': instance}
        }
EOF
        echo "  Created instance_transformer.py"
    fi
    
    # Create user transformer if it doesn't exist
    if [ ! -f "$TRANSFORM_DIR/user_transformer.py" ]; then
        cat > "$TRANSFORM_DIR/user_transformer.py" << 'EOF'
"""
User Transformer
Transforms vendor users to Tallyfy users
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform vendor users to Tallyfy format"""
    
    def __init__(self, ai_client=None):
        """Initialize user transformer"""
        self.ai_client = ai_client
    
    def transform_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a vendor user to Tallyfy format"""
        try:
            tallyfy_user = {
                'email': self._extract_email(user),
                'first_name': user.get('first_name', user.get('firstName', '')),
                'last_name': user.get('last_name', user.get('lastName', '')),
                'full_name': self._extract_full_name(user),
                'role': self._transform_role(user),
                'active': user.get('active', user.get('is_active', True)),
                'vendor_metadata': {
                    'original_id': user.get('id', ''),
                    'original_role': user.get('role', ''),
                    'original_data': user
                }
            }
            
            # Add optional fields if present
            if 'phone' in user:
                tallyfy_user['phone'] = user['phone']
            if 'avatar' in user or 'avatar_url' in user:
                tallyfy_user['avatar_url'] = user.get('avatar', user.get('avatar_url'))
            
            return tallyfy_user
            
        except Exception as e:
            logger.error(f"Error transforming user: {e}")
            return self._create_fallback_user(user)
    
    def _extract_email(self, user: Dict[str, Any]) -> str:
        """Extract email from user data"""
        return user.get('email', user.get('email_address', ''))
    
    def _extract_full_name(self, user: Dict[str, Any]) -> str:
        """Extract or construct full name"""
        if 'full_name' in user:
            return user['full_name']
        if 'name' in user:
            return user['name']
        
        first = user.get('first_name', user.get('firstName', ''))
        last = user.get('last_name', user.get('lastName', ''))
        return f"{first} {last}".strip()
    
    def _transform_role(self, user: Dict[str, Any]) -> str:
        """Transform user role"""
        role = user.get('role', user.get('type', '')).lower()
        
        role_map = {
            'admin': 'admin',
            'administrator': 'admin',
            'owner': 'admin',
            'manager': 'manager',
            'member': 'member',
            'user': 'member',
            'guest': 'guest',
            'viewer': 'guest',
            'read_only': 'guest'
        }
        
        return role_map.get(role, 'member')
    
    def _create_fallback_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback user when transformation fails"""
        return {
            'email': str(user.get('email', user.get('id', 'unknown@example.com'))),
            'full_name': 'Unknown User',
            'role': 'member',
            'vendor_metadata': {'original_data': user}
        }
EOF
        echo "  Created user_transformer.py"
    fi
done

echo "Done creating transformers!"