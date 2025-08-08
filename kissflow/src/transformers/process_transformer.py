"""Transform Kissflow processes to Tallyfy blueprints."""

import logging
from typing import Dict, Any, List, Optional
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class ProcessTransformer:
    """Transform Kissflow BPM processes to Tallyfy blueprints."""
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_process_to_blueprint(self, process: Dict[str, Any],
                                     fields: List[Dict[str, Any]],
                                     workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow process to Tallyfy blueprint.
        
        Args:
            process: Kissflow process object
            fields: Process form fields
            workflow: Process workflow definition
            
        Returns:
            Tallyfy blueprint object
        """
        logger.info(f"Transforming process '{process.get('Name')}' to blueprint")
        
        blueprint = {
            'name': process.get('Name', 'Untitled Process'),
            'description': self._format_description(process),
            'steps': self._transform_workflow_to_steps(workflow, fields),
            'kick_off_form': self._create_kickoff_form(process, fields),
            'tags': self._extract_tags(process),
            'metadata': {
                'source': 'kissflow',
                'original_id': process.get('Id'),
                'original_type': 'process',
                'created_at': process.get('CreatedAt'),
                'modified_at': process.get('ModifiedAt'),
                'version': process.get('Version'),
                'status': process.get('Status')
            }
        }
        
        # Add automation rules if present
        if workflow.get('Automations'):
            blueprint['rules'] = self._transform_automations(workflow['Automations'])
        
        # Add permissions/roles mapping
        if process.get('Permissions'):
            blueprint['permissions'] = self._transform_permissions(process['Permissions'])
        
        return blueprint
    
    def _format_description(self, process: Dict[str, Any]) -> str:
        """Format process description with metadata.
        
        Args:
            process: Kissflow process
            
        Returns:
            Formatted description
        """
        description = process.get('Description', '')
        
        # Add migration metadata
        migration_note = "\n\n---\n*Migrated from Kissflow Process*"
        
        if process.get('Category'):
            migration_note += f"\n*Category: {process['Category']}*"
        
        if process.get('SLA'):
            migration_note += f"\n*Original SLA: {process['SLA']} hours*"
        
        if process.get('Tags'):
            migration_note += f"\n*Tags: {', '.join(process['Tags'])}*"
        
        return description + migration_note
    
    def _transform_workflow_to_steps(self, workflow: Dict[str, Any],
                                    fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Kissflow workflow to Tallyfy steps.
        
        Args:
            workflow: Workflow definition
            fields: Process fields for form creation
            
        Returns:
            List of Tallyfy steps
        """
        steps = []
        step_order = 1
        
        # Process workflow steps
        for wf_step in workflow.get('Steps', []):
            step_type = wf_step.get('Type', 'task').lower()
            
            # Map Kissflow step types to Tallyfy
            if step_type == 'approval':
                tallyfy_type = 'approval'
            elif step_type == "text":
                tallyfy_type = "text"
            elif step_type == 'integration':
                tallyfy_type = 'task'  # Integration becomes task with webhook
            elif step_type == 'decision':
                # Decision points become multiple conditional steps
                steps.extend(self._create_decision_steps(wf_step, step_order, fields))
                step_order += len(steps)
                continue
            elif step_type == 'parallel':
                # Parallel branches become sequential with notes
                steps.extend(self._create_parallel_steps(wf_step, step_order, fields))
                step_order += len(steps)
                continue
            else:
                tallyfy_type = 'task'
            
            # Create basic step
            step = {
                'order': step_order,
                'name': wf_step.get('Name', f'Step {step_order}'),
                'type': tallyfy_type,
                'description': wf_step.get('Description', ''),
                "assignees_form": self._transform_assignee(wf_step.get('Assignee')),
                'duration': self._calculate_duration(wf_step),
                'form_fields': [],
                'metadata': {
                    'original_id': wf_step.get('Id'),
                    'original_type': step_type,
                    'conditions': wf_step.get('Conditions'),
                    'integrations': wf_step.get('Integrations')
                }
            }
            
            # Add form fields for this step
            step_fields = wf_step.get('Fields', [])
            if step_fields:
                for field_id in step_fields:
                    # Find field definition
                    field_def = next((f for f in fields if f.get('Id') == field_id), None)
                    if field_def:
                        transformed_field = self.field_transformer.transform_field_definition(field_def)
                        step['form_fields'].append(transformed_field)
            
            # Add deadline if specified
            if wf_step.get('SLA'):
                step['deadline'] = {
                    'type': 'relative',
                    'days': wf_step['SLA'] / 24  # Convert hours to days
                }
            
            # Handle short_text steps
            if tallyfy_type == "text":
                step['email_template'] = self._create_email_template(wf_step)
            
            # Handle integration steps
            if step_type == 'integration':
                step['webhook'] = self._create_webhook_config(wf_step)
            
            steps.append(step)
            step_order += 1
        
        logger.info(f"Transformed workflow with {len(steps)} steps")
        return steps
    
    def _create_decision_steps(self, decision: Dict[str, Any], 
                              start_order: int,
                              fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create steps for decision points.
        
        Args:
            decision: Decision step definition
            start_order: Starting order number
            fields: Available fields
            
        Returns:
            List of steps representing decision branches
        """
        steps = []
        
        # Create decision step
        decision_step = {
            'order': start_order,
            'name': f"Decision: {decision.get('Name', 'Choose Path')}",
            'type': 'approval',  # Use approval for decision
            'description': decision.get('Description', 'Select the appropriate path'),
            "assignees_form": self._transform_assignee(decision.get('Assignee')),
            'form_fields': [],
            'metadata': {
                'is_decision': True,
                'original_id': decision.get('Id')
            }
        }
        
        # Add decision criteria as form field
        decision_field = {
            'name': 'Decision',
            'type': 'dropdown',
            'required': True,
            'options': []
        }
        
        # Add each branch as an option
        for branch in decision.get('Branches', []):
            decision_field['options'].append({
                'value': branch.get('Id', ''),
                'label': branch.get('Name', 'Option')
            })
            
            # Document the condition
            if branch.get('Condition'):
                decision_step['description'] += f"\n\n**{branch['Name']}**: {branch['Condition']}"
        
        decision_step['form_fields'].append(decision_field)
        steps.append(decision_step)
        
        # Create placeholder steps for each branch
        for idx, branch in enumerate(decision.get('Branches', [])):
            branch_step = {
                'order': start_order + idx + 1,
                'name': f"Branch: {branch.get('Name', 'Path')}",
                'type': 'task',
                'description': f"Tasks for {branch.get('Name')} path\n\nCondition: {branch.get('Condition', 'N/A')}",
                "assignees_form": 'process_owner',
                'metadata': {
                    'is_branch': True,
                    'parent_decision': decision.get('Id'),
                    'branch_id': branch.get('Id')
                }
            }
            steps.append(branch_step)
        
        return steps
    
    def _create_parallel_steps(self, parallel: Dict[str, Any],
                              start_order: int,
                              fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create steps for parallel branches.
        
        Args:
            parallel: Parallel step definition
            start_order: Starting order number
            fields: Available fields
            
        Returns:
            List of sequential steps (Tallyfy doesn't support true parallel)
        """
        steps = []
        
        # Add notification about parallel execution
        parallel_start = {
            'order': start_order,
            'name': f"Parallel Tasks Start: {parallel.get('Name', 'Parallel Work')}",
            'type': 'task',
            'description': "The following tasks were originally parallel in Kissflow and can be worked on simultaneously",
            "assignees_form": 'process_owner',
            'duration': 0,
            'metadata': {
                'is_parallel_marker': True,
                'original_id': parallel.get('Id')
            }
        }
        steps.append(parallel_start)
        
        # Convert parallel branches to sequential steps
        order = start_order + 1
        for branch in parallel.get('Branches', []):
            for task in branch.get('Tasks', []):
                step = {
                    'order': order,
                    'name': f"[Parallel] {task.get('Name', 'Task')}",
                    'type': 'task',
                    'description': f"{task.get('Description', '')}\n\n*Originally parallel with other [Parallel] tasks*",
                    "assignees_form": self._transform_assignee(task.get('Assignee')),
                    'duration': self._calculate_duration(task),
                    'metadata': {
                        'was_parallel': True,
                        'parallel_group': parallel.get('Id'),
                        'branch': branch.get('Name')
                    }
                }
                steps.append(step)
                order += 1
        
        # Add parallel completion marker
        parallel_end = {
            'order': order,
            'name': f"Parallel Tasks Complete: {parallel.get('Name', 'Parallel Work')}",
            'type': 'approval',
            'description': "Confirm all parallel tasks have been completed",
            "assignees_form": 'process_owner',
            'metadata': {
                'is_parallel_marker': True,
                'parallel_group': parallel.get('Id')
            }
        }
        steps.append(parallel_end)
        
        return steps
    
    def _create_kickoff_form(self, process: Dict[str, Any],
                           fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create kick-off form from process initiation fields.
        
        Args:
            process: Kissflow process
            fields: Process fields
            
        Returns:
            List of form fields for kick-off
        """
        form_fields = []
        
        # Add process metadata fields
        form_fields.append({
            'name': 'Process Title',
            'type': 'text',
            'description': 'Title for this process instance',
            'required': True,
            'default_value': process.get('Name', '')
        })
        
        form_fields.append({
            'name': 'Priority',
            'type': 'dropdown',
            'description': 'Process priority level',
            'required': False,
            'options': [
                {'value': 'high', 'label': 'High'},
                {'value': 'normal', 'label': 'Normal'},
                {'value': 'low', 'label': 'Low'}
            ],
            'default_value': 'normal'
        })
        
        # Add initiation fields
        initiation_fields = process.get('InitiationFields', [])
        for field_id in initiation_fields:
            field_def = next((f for f in fields if f.get('Id') == field_id), None)
            if field_def:
                transformed_field = self.field_transformer.transform_field_definition(field_def)
                form_fields.append(transformed_field)
        
        # If no specific initiation fields, add all required fields
        if not initiation_fields:
            for field in fields:
                if field.get('Required') and field.get('ShowOnInitiation', True):
                    transformed_field = self.field_transformer.transform_field_definition(field)
                    form_fields.append(transformed_field)
        
        return form_fields
    
    def _transform_assignee(self, assignee: Any) -> str:
        """Transform Kissflow assignee to Tallyfy format.
        
        Args:
            assignee: Kissflow assignee definition
            
        Returns:
            Tallyfy assignee string
        """
        if not assignee:
            return 'process_owner'
        
        if isinstance(assignee, str):
            # Direct user ID or short_text
            return f"member:{assignee}"
        
        if isinstance(assignee, dict):
            assignee_type = assignee.get('Type', 'user')
            
            if assignee_type == 'role':
                # Role-based assignment
                role = assignee.get('Role', 'process_owner')
                return f"role:{role}"
            elif assignee_type == 'group':
                # Group assignment
                group = assignee.get('Group', '')
                return f"group:{group}"
            elif assignee_type == 'field':
                # Dynamic assignment from field
                field = assignee.get('Field', '')
                return f"field:{field}"
            elif assignee_type == 'initiator':
                return 'process_initiator'
            elif assignee_type == 'previous_step':
                return 'previous_assignee'
            else:
                # User assignment
                user = assignee.get('User') or assignee.get('Id')
                if user:
                    return f"member:{user}"
        
        return 'process_owner'
    
    def _calculate_duration(self, step: Dict[str, Any]) -> int:
        """Calculate step duration in days.
        
        Args:
            step: Workflow step
            
        Returns:
            Duration in days
        """
        if step.get('SLA'):
            # Convert hours to days
            hours = step['SLA']
            return max(1, int(hours / 24))
        
        # Default durations based on step type
        step_type = step.get('Type', 'task').lower()
        if step_type == 'approval':
            return 2
        elif step_type == "text":
            return 0
        elif step_type == 'integration':
            return 1
        else:
            return 1
    
    def _transform_automations(self, automations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Kissflow automations to Tallyfy rules.
        
        Args:
            automations: List of automation definitions
            
        Returns:
            List of Tallyfy rules
        """
        rules = []
        
        for automation in automations:
            trigger = automation.get('Trigger', {})
            actions = automation.get('Actions', [])
            
            rule = {
                'name': automation.get('Name', 'Automation'),
                'description': automation.get('Description', ''),
                'trigger': {
                    'type': trigger.get('Type', 'manual'),
                    'event': trigger.get('Event', ''),
                    'conditions': trigger.get('Conditions', [])
                },
                'actions': []
            }
            
            # Transform actions
            for action in actions:
                action_type = action.get('Type', '')
                
                if action_type == 'assign':
                    rule['actions'].append({
                        'type': 'assign_task',
                        "assignees_form": self._transform_assignee(action.get('Assignee'))
                    })
                elif action_type == "text":
                    rule['actions'].append({
                        'type': 'send_email',
                        'template': action.get('Template', ''),
                        'recipients': action.get('Recipients', [])
                    })
                elif action_type == 'update_field':
                    rule['actions'].append({
                        'type': 'update_field',
                        'field': action.get('Field', ''),
                        'value': action.get('Value', '')
                    })
                elif action_type == 'webhook':
                    rule['actions'].append({
                        'type': 'trigger_webhook',
                        "text": action.get('Url', ''),
                        'method': action.get('Method', 'POST')
                    })
            
            rules.append(rule)
        
        return rules
    
    def _transform_permissions(self, permissions: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow permissions to Tallyfy format.
        
        Args:
            permissions: Kissflow permission settings
            
        Returns:
            Tallyfy permission configuration
        """
        return {
            'admins': permissions.get('Admins', []),
            'developers': permissions.get('Developers', []),
            'members': permissions.get('Members', []),
            'viewers': permissions.get('Viewers', []),
            'initiators': permissions.get('Initiators', []),
            'visibility': permissions.get('Visibility', 'private')
        }
    
    def _extract_tags(self, process: Dict[str, Any]) -> List[str]:
        """Extract tags from process.
        
        Args:
            process: Kissflow process
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add existing tags
        if process.get('Tags'):
            tags.extend(process['Tags'])
        
        # Add category as tag
        if process.get('Category'):
            tags.append(f"category:{process['Category']}")
        
        # Add status as tag
        if process.get('Status'):
            tags.append(f"status:{process['Status']}")
        
        # Add type tag
        tags.append('type:process')
        tags.append('source:kissflow')
        
        return tags
    
    def _create_email_template(self, email_step: Dict[str, Any]) -> Dict[str, Any]:
        """Create email template from email step.
        
        Args:
            email_step: Email step definition
            
        Returns:
            Email template configuration
        """
        return {
            'subject': email_step.get('Subject', 'Process Notification'),
            'body': email_step.get('Body', ''),
            'recipients': email_step.get('Recipients', []),
            'cc': email_step.get('CC', []),
            'bcc': email_step.get('BCC', []),
            'attachments': email_step.get('Attachments', [])
        }
    
    def _create_webhook_config(self, integration_step: Dict[str, Any]) -> Dict[str, Any]:
        """Create webhook configuration from integration step.
        
        Args:
            integration_step: Integration step definition
            
        Returns:
            Webhook configuration
        """
        return {
            "text": integration_step.get('Url', ''),
            'method': integration_step.get('Method', 'POST'),
            'headers': integration_step.get('Headers', {}),
            'body_template': integration_step.get('BodyTemplate', ''),
            'retry_on_failure': integration_step.get('RetryOnFailure', True),
            'timeout': integration_step.get('Timeout', 30)
        }