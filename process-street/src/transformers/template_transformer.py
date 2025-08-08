"""
Template Transformer
Transforms Process Street workflows/checklists to Tallyfy checklists
"""

import logging
import json
from typing import Dict, Any, List, Optional
from .base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class TemplateTransformer(BaseTransformer):
    """Transform Process Street workflows to Tallyfy checklists"""
    
    def transform(self, ps_workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Process Street workflow to Tallyfy checklist
        
        Args:
            ps_workflow: Process Street workflow object
            
        Returns:
            Tallyfy checklist object with steps
        """
        ps_id = ps_workflow.get('id', '')
        title = ps_workflow.get('name', ps_workflow.get('title', 'Untitled'))
        
        # Check if already mapped
        tallyfy_id = self.get_mapped_id(ps_id, 'multiselect')
        if not tallyfy_id:
            tallyfy_id = self.generate_tallyfy_id('chk', ps_id)
        
        # Build Tallyfy checklist object
        tallyfy_checklist = {
            'id': tallyfy_id,
            'title': title,
            'description': self.clean_html(ps_workflow.get('description', '')),
            'status': 'active' if ps_workflow.get('active', True) else 'inactive',
            'is_template': True,
            'is_public': ps_workflow.get('public', False),
            'version': ps_workflow.get('version', 1),
            'category': self._map_category(ps_workflow.get('folder', '')),
            'tags': ps_workflow.get('tags', []),
            'icon': ps_workflow.get('icon', 'clipboard'),
            'color': ps_workflow.get('color', '#4A90E2'),
            'created_at': self.convert_datetime(ps_workflow.get('created_at')),
            'updated_at': self.convert_datetime(ps_workflow.get('updated_at')),
            'created_by': self.get_mapped_id(ps_workflow.get('owner_id'), 'user'),
            
            # Configuration
            'config': {
                'allow_comments': ps_workflow.get('allowComments', True),
                'allow_attachments': ps_workflow.get('allowAttachments', True),
                'require_approval': ps_workflow.get('requireApproval', False),
                'auto_assign': ps_workflow.get('autoAssign', False),
                'sequential': ps_workflow.get('sequential', True),
                'notify_on_complete': ps_workflow.get('notifyOnComplete', True),
                'archive_on_complete': ps_workflow.get('archiveOnComplete', False),
                'recurring': ps_workflow.get('recurring', False),
                'recurring_config': self._transform_recurring_config(ps_workflow.get('recurringConfig', {}))
            },
            
            # Steps will be added separately
            'steps': [],
            
            # Form fields at template level
            'field': []
        }
        
        # Add external reference
        tallyfy_checklist = self.add_external_reference(tallyfy_checklist, ps_id, 'workflow')
        
        # Transform tasks to steps
        if 'tasks' in ps_workflow:
            tallyfy_checklist['steps'] = self._transform_tasks(ps_workflow['tasks'])
        
        # Transform form fields to field
        if 'formFields' in ps_workflow:
            tallyfy_checklist['field'] = self._transform_form_fields(ps_workflow['formFields'])
        
        # Handle webhooks
        if 'webhooks' in ps_workflow:
            tallyfy_checklist['webhooks'] = self._transform_webhooks(ps_workflow['webhooks'])
        
        # Handle conditional logic / rules
        if 'conditionalLogic' in ps_workflow:
            tallyfy_checklist['rules'] = self._transform_conditional_logic(ps_workflow['conditionalLogic'])
        
        # Handle permissions
        if 'permissions' in ps_workflow:
            tallyfy_checklist['permissions'] = self._transform_permissions(ps_workflow['permissions'])
        
        # Store ID mapping
        self.map_id(ps_id, tallyfy_id, 'multiselect')
        
        logger.debug(f"Transformed workflow: {title} ({ps_id} -> {tallyfy_id})")
        
        return tallyfy_checklist
    
    def _map_category(self, folder: str) -> str:
        """
        Map Process Street folder to Tallyfy category
        
        Args:
            folder: Process Street folder name
            
        Returns:
            Tallyfy category name
        """
        if not folder:
            return 'General'
        
        # Clean up folder name
        category = folder.strip().replace('/', ' - ')
        
        return category
    
    def _transform_recurring_config(self, ps_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform recurring configuration
        
        Args:
            ps_config: Process Street recurring config
            
        Returns:
            Tallyfy recurring configuration
        """
        if not ps_config:
            return {}
        
        return {
            'frequency': ps_config.get('frequency', 'daily'),
            'interval': ps_config.get('interval', 1),
            'days_of_week': ps_config.get('daysOfWeek', []),
            'day_of_month': ps_config.get('dayOfMonth'),
            'time': ps_config.get('time', '09:00'),
            'timezone': ps_config.get('timezone', 'UTC'),
            'end_date': self.convert_datetime(ps_config.get('endDate'))
        }
    
    def _transform_tasks(self, ps_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform Process Street tasks to Tallyfy steps
        
        Args:
            ps_tasks: List of Process Street tasks
            
        Returns:
            List of Tallyfy steps
        """
        tallyfy_steps = []
        
        for i, task in enumerate(ps_tasks):
            ps_task_id = task.get('id', '')
            
            # Generate step ID
            tallyfy_step_id = self.generate_tallyfy_id('stp', ps_task_id)
            
            # Determine task type
            task_type = self._determine_task_type(task)
            
            tallyfy_step = {
                'id': tallyfy_step_id,
                'title': task.get('title', task.get('name', f'Step {i+1}')),
                'description': self.clean_html(task.get('description', '')),
                'task_type': task_type,
                'position': task.get('position', i),
                'is_required': task.get('required', True),
                'is_blocking': task.get('stopTask', False),
                
                # Assignment
                'assignment_type': self._map_assignment_type(task.get('assigneeType', 'any')),
                'assigned_to': self._map_assignee(task.get("assignees_form")),
                'role_assignment': task.get('roleAssignment'),
                
                # Timing
                'estimated_duration': task.get('estimatedDuration', 0),
                'deadline_config': self._transform_deadline_config(task.get('dueDateConfig')),
                
                # Dependencies
                'dependencies': self._map_dependencies(task.get('dependencies', [])),
                
                # Visibility rules
                'visibility_rules': self._transform_visibility_rules(task.get('conditionalShow', {})),
                
                # Task-specific configuration
                'config': self._get_task_config(task, task_type)
            }
            
            # Add external reference
            tallyfy_step['external_ref'] = ps_task_id
            
            # Handle form fields within task
            if 'formFields' in task:
                tallyfy_step['field'] = self._transform_form_fields(task['formFields'])
            
            # Store ID mapping
            self.map_id(ps_task_id, tallyfy_step_id, 'step')
            
            tallyfy_steps.append(tallyfy_step)
        
        return tallyfy_steps
    
    def _determine_task_type(self, task: Dict[str, Any]) -> str:
        """
        Determine Tallyfy task type from Process Street task
        
        Args:
            task: Process Street task object
            
        Returns:
            Tallyfy task type
        """
        if task.get('approvalRequired') or task.get('type') == 'approval':
            return 'approval'
        elif task.get('formFields') or task.get('type') == 'form':
            return 'form'
        elif task.get('type') == 'decision':
            return 'decision'
        elif task.get('type') == "text":
            return "text"
        else:
            return 'normal'
    
    def _map_assignment_type(self, ps_type: str) -> str:
        """
        Map Process Street assignment type to Tallyfy
        
        Args:
            ps_type: Process Street assignment type
            
        Returns:
            Tallyfy assignment type
        """
        mapping = {
            'specific': 'specific',
            'role': 'role',
            'any': 'any',
            'dynamic': 'dynamic',
            'group': 'group',
            'self': 'self'
        }
        
        return mapping.get(ps_type, 'any')
    
    def _map_assignee(self, ps_assignee: Any) -> Optional[str]:
        """
        Map Process Street assignee to Tallyfy user/role ID
        
        Args:
            ps_assignee: Process Street assignee (ID, email, or object)
            
        Returns:
            Tallyfy user or role ID
        """
        if not ps_assignee:
            return None
        
        if isinstance(ps_assignee, str):
            # Try to map as user ID
            mapped_user = self.get_mapped_id(ps_assignee, 'user')
            if mapped_user:
                return mapped_user
            
            # Could be short_text or role name
            return ps_assignee
        
        elif isinstance(ps_assignee, dict):
            assignee_id = ps_assignee.get('id')
            if assignee_id:
                return self.get_mapped_id(assignee_id, 'user')
        
        elif isinstance(ps_assignee, list):
            # Multiple assignees - return first one
            if ps_assignee:
                return self._map_assignee(ps_assignee[0])
        
        return None
    
    def _transform_deadline_config(self, ps_config: Optional[Dict]) -> Dict[str, Any]:
        """
        Transform deadline/due date configuration
        
        Args:
            ps_config: Process Street due date config
            
        Returns:
            Tallyfy deadline configuration
        """
        if not ps_config:
            return {}
        
        return {
            'type': ps_config.get('type', 'none'),  # none, fixed, relative
            'fixed_date': self.convert_datetime(ps_config.get('fixedDate')),
            'relative_days': ps_config.get('relativeDays', 0),
            'relative_to': ps_config.get('relativeTo', 'process_start'),  # process_start, step_complete
            'business_days_only': ps_config.get('businessDaysOnly', False),
            'reminder_before': ps_config.get('reminderBefore', 0)
        }
    
    def _map_dependencies(self, ps_dependencies: List) -> List[str]:
        """
        Map task dependencies
        
        Args:
            ps_dependencies: List of Process Street task dependencies
            
        Returns:
            List of Tallyfy step IDs
        """
        tallyfy_deps = []
        
        for dep in ps_dependencies:
            if isinstance(dep, str):
                mapped_step = self.get_mapped_id(dep, 'step')
                if mapped_step:
                    tallyfy_deps.append(mapped_step)
            elif isinstance(dep, dict):
                dep_id = dep.get('id')
                if dep_id:
                    mapped_step = self.get_mapped_id(dep_id, 'step')
                    if mapped_step:
                        tallyfy_deps.append(mapped_step)
        
        return tallyfy_deps
    
    def _transform_visibility_rules(self, ps_rules: Dict) -> Dict[str, Any]:
        """
        Transform conditional visibility rules
        
        Args:
            ps_rules: Process Street conditional show rules
            
        Returns:
            Tallyfy visibility rules
        """
        if not ps_rules:
            return {}
        
        return {
            'condition_type': ps_rules.get('type', 'always'),  # always, field_value, step_complete
            'field_conditions': self._transform_field_conditions(ps_rules.get('fieldConditions', [])),
            'step_conditions': self._transform_step_conditions(ps_rules.get('stepConditions', [])),
            'logic_operator': ps_rules.get('operator', 'AND')  # AND, OR
        }
    
    def _transform_field_conditions(self, conditions: List[Dict]) -> List[Dict]:
        """Transform field-based conditions"""
        transformed = []
        
        for condition in conditions:
            field_id = condition.get('fieldId')
            if field_id:
                mapped_field = self.get_mapped_id(field_id, "field")
                if mapped_field:
                    transformed.append({
                        'field_id': mapped_field,
                        'operator': condition.get('operator', 'equals'),
                        'value': condition.get('value')
                    })
        
        return transformed
    
    def _transform_step_conditions(self, conditions: List[Dict]) -> List[Dict]:
        """Transform step-based conditions"""
        transformed = []
        
        for condition in conditions:
            step_id = condition.get('stepId')
            if step_id:
                mapped_step = self.get_mapped_id(step_id, 'step')
                if mapped_step:
                    transformed.append({
                        'step_id': mapped_step,
                        'status': condition.get('status', 'completed')
                    })
        
        return transformed
    
    def _get_task_config(self, task: Dict, task_type: str) -> Dict[str, Any]:
        """
        Get task-specific configuration based on type
        
        Args:
            task: Process Street task
            task_type: Determined task type
            
        Returns:
            Task configuration for Tallyfy
        """
        config = {
            'allow_comments': task.get('allowComments', True),
            'allow_attachments': task.get('allowAttachments', True),
            'require_evidence': task.get('requireEvidence', False),
            'show_in_summary': task.get('showInSummary', True)
        }
        
        if task_type == 'approval':
            config['approval'] = {
                'approvers': self._map_approvers(task.get('approvers', [])),
                'approval_type': task.get('approvalType', 'any'),  # any, all, specific
                'rejection_action': task.get('rejectionAction', 'block')  # block, continue
            }
        
        elif task_type == 'form':
            config['form'] = {
                'submit_button_text': task.get('submitButtonText', 'Submit'),
                'save_draft': task.get('saveDraft', True),
                'validation_on_submit': task.get('validationOnSubmit', True)
            }
        
        elif task_type == "text":
            config["text"] = {
                'checklist_id': task.get('emailTemplateId'),
                'recipients': task.get('emailRecipients', []),
                'subject': task.get('emailSubject', ''),
                'send_automatically': task.get('sendAutomatically', False)
            }
        
        return config
    
    def _map_approvers(self, ps_approvers: List) -> List[str]:
        """Map approvers to Tallyfy user IDs"""
        tallyfy_approvers = []
        
        for approver in ps_approvers:
            if isinstance(approver, str):
                mapped = self.get_mapped_id(approver, 'user')
                if mapped:
                    tallyfy_approvers.append(mapped)
            elif isinstance(approver, dict):
                approver_id = approver.get('id')
                if approver_id:
                    mapped = self.get_mapped_id(approver_id, 'user')
                    if mapped:
                        tallyfy_approvers.append(mapped)
        
        return tallyfy_approvers
    
    def _transform_form_fields(self, ps_fields: List[Dict]) -> List[Dict[str, Any]]:
        """
        Transform Process Street form fields to Tallyfy field
        
        Args:
            ps_fields: List of Process Street form fields
            
        Returns:
            List of Tallyfy field fields
        """
        from .form_transformer import FormTransformer
        
        form_transformer = FormTransformer(self.id_mapper)
        tallyfy_captures = []
        
        for field in ps_fields:
            try:
                transformed = form_transformer.transform(field)
                tallyfy_captures.append(transformed)
            except Exception as e:
                logger.warning(f"Failed to transform form field: {e}")
        
        return tallyfy_captures
    
    def _transform_webhooks(self, ps_webhooks: List[Dict]) -> List[Dict[str, Any]]:
        """Transform webhooks"""
        tallyfy_webhooks = []
        
        for webhook in ps_webhooks:
            tallyfy_webhooks.append({
                "text": webhook.get("text"),
                'events': webhook.get('events', ['all']),
                'is_active': webhook.get('active', True),
                'headers': webhook.get('headers', {}),
                'secret': webhook.get('secret')
            })
        
        return tallyfy_webhooks
    
    def _transform_permissions(self, ps_permissions: Dict) -> Dict[str, Any]:
        """Transform template permissions"""
        return {
            'visibility': ps_permissions.get('visibility', 'organization'),  # organization, public, specific
            'can_edit': self._map_permission_users(ps_permissions.get('canEdit', [])),
            'can_run': self._map_permission_users(ps_permissions.get('canRun', [])),
            'can_view': self._map_permission_users(ps_permissions.get('canView', [])),
            'can_delete': self._map_permission_users(ps_permissions.get('canDelete', []))
        }
    
    def _map_permission_users(self, ps_users: List) -> List[str]:
        """Map users in permissions"""
        tallyfy_users = []
        
        for user in ps_users:
            if isinstance(user, str):
                mapped = self.get_mapped_id(user, 'user')
                if mapped:
                    tallyfy_users.append(mapped)
            elif isinstance(user, dict):
                user_id = user.get('id')
                if user_id:
                    mapped = self.get_mapped_id(user_id, 'user')
                    if mapped:
                        tallyfy_users.append(mapped)
        
        return tallyfy_users