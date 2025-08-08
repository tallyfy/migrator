"""Transform Kissflow apps to Tallyfy blueprints."""

import logging
from typing import Dict, Any, List, Optional
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class AppTransformer:
    """Transform Kissflow low-code apps to Tallyfy blueprints.
    
    Kissflow Apps are custom applications with forms, views, and workflows.
    They need special handling as they combine features of processes and databases.
    """
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_app_to_blueprint(self, app: Dict[str, Any],
                                  forms: List[Dict[str, Any]],
                                  views: List[Dict[str, Any]],
                                  workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform Kissflow app to Tallyfy blueprint.
        
        Apps are complex - they have multiple forms, views, and workflows.
        We'll create a master blueprint with sub-processes.
        
        Args:
            app: Kissflow app definition
            forms: App forms
            views: App views (list, kanban, calendar, etc.)
            workflows: App workflows
            
        Returns:
            Tallyfy blueprint object
        """
        logger.info(f"Transforming app '{app.get('Name')}' to blueprint")
        
        # Create main blueprint for the app
        blueprint = {
            'name': app.get('Name', 'Untitled App'),
            'description': self._format_description(app, views),
            'steps': self._create_app_workflow(app, forms, workflows),
            'kick_off_form': self._create_master_form(app, forms),
            'tags': self._extract_tags(app),
            'metadata': {
                'source': 'kissflow',
                'original_id': app.get('Id'),
                'original_type': 'app',
                'app_type': app.get('Type', 'custom'),
                'created_at': app.get('CreatedAt'),
                'modified_at': app.get('ModifiedAt'),
                'forms_count': len(forms),
                'views_count': len(views),
                'workflows_count': len(workflows)
            }
        }
        
        # Add automation rules from workflows
        if workflows:
            blueprint['rules'] = self._transform_app_automations(workflows)
        
        # Add sub-blueprints for complex forms
        if len(forms) > 1:
            blueprint['sub_blueprints'] = self._create_sub_blueprints(forms)
        
        # Add view configurations as metadata
        blueprint['view_configs'] = self._transform_views(views)
        
        return blueprint
    
    def _format_description(self, app: Dict[str, Any], views: List[Dict[str, Any]]) -> str:
        """Format app description with migration notes.
        
        Args:
            app: Kissflow app
            views: App views
            
        Returns:
            Formatted description
        """
        description = app.get('Description', '')
        
        # Add app complexity warning
        app_warning = """

⚠️ **LOW-CODE APP MIGRATION** ⚠️
This workflow was migrated from a Kissflow App - a low-code application platform.

**Original App Structure:**
"""
        
        # List app components
        if app.get('Modules'):
            app_warning += "\n**Modules:**"
            for module in app['Modules']:
                app_warning += f"\n• {module.get('Name', 'Module')}: {module.get('Type', 'unknown')}"
        
        if views:
            app_warning += "\n\n**Original Views:**"
            for view in views:
                view_type = view.get('Type', 'list')
                app_warning += f"\n• {view.get('Name', 'View')} ({view_type} view)"
        
        app_warning += """

**Migration Limitations:**
1. Complex app logic may require manual configuration
2. Custom views (calendar, timeline) become list views
3. Inter-form relationships need manual setup
4. Advanced formulas may need reconfiguration
5. Custom permissions per view not supported

**Recommended Actions:**
- Review all form fields and validations
- Test workflow logic thoroughly
- Manually configure view filters
- Set up proper permissions
"""
        
        migration_note = f"\n\n---\n*Migrated from Kissflow App*"
        
        if app.get('Category'):
            migration_note += f"\n*Category: {app['Category']}*"
        
        if app.get('Version'):
            migration_note += f"\n*Version: {app['Version']}*"
        
        return description + app_warning + migration_note
    
    def _create_app_workflow(self, app: Dict[str, Any],
                           forms: List[Dict[str, Any]],
                           workflows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create workflow steps from app structure.
        
        Args:
            app: App definition
            forms: App forms
            workflows: App workflows
            
        Returns:
            List of workflow steps
        """
        steps = []
        step_order = 1
        
        # Create initial data entry step
        steps.append({
            'order': step_order,
            'name': 'Create Record',
            'type': 'task',
            'description': f"Create a new record in {app.get('Name', 'app')}",
            "assignees_form": 'process_initiator',
            'duration': 0,
            'form_fields': [],  # Will use kick-off form
            'metadata': {
                'is_app_entry': True
            }
        })
        step_order += 1
        
        # Process each workflow
        for workflow in workflows:
            workflow_name = workflow.get('Name', f'Workflow {step_order}')
            
            # Add workflow start marker
            steps.append({
                'order': step_order,
                'name': f"Start: {workflow_name}",
                'type': 'task',
                'description': workflow.get('Description', f"Begin {workflow_name} workflow"),
                "assignees_form": self._get_workflow_assignee(workflow),
                'duration': 0,
                'metadata': {
                    'workflow_id': workflow.get('Id'),
                    'workflow_trigger': workflow.get('Trigger')
                }
            })
            step_order += 1
            
            # Add workflow steps
            for wf_step in workflow.get('Steps', []):
                step = self._transform_workflow_step(wf_step, forms, step_order)
                steps.append(step)
                step_order += 1
            
            # Add workflow completion
            steps.append({
                'order': step_order,
                'name': f"Complete: {workflow_name}",
                'type': 'approval',
                'description': f"Confirm completion of {workflow_name}",
                "assignees_form": self._get_workflow_approver(workflow),
                'duration': 1,
                'form_fields': [
                    {
                        'name': 'Workflow Status',
                        'type': 'dropdown',
                        'required': True,
                        'options': [
                            {'value': 'completed', 'label': 'Completed'},
                            {'value': 'rejected', 'label': 'Rejected'},
                            {'value': 'cancelled', 'label': 'Cancelled'}
                        ]
                    },
                    {
                        'name': 'Comments',
                        'type': 'textarea',
                        'required': False
                    }
                ]
            })
            step_order += 1
        
        # If no workflows, create basic CRUD steps
        if not workflows:
            steps.extend(self._create_basic_crud_steps(app, forms, step_order))
        
        logger.info(f"Created {len(steps)} steps for app workflow")
        return steps
    
    def _create_master_form(self, app: Dict[str, Any],
                          forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create master kick-off form from app forms.
        
        Args:
            app: App definition
            forms: App forms
            
        Returns:
            List of form fields
        """
        form_fields = []
        
        # Add app-level metadata fields
        form_fields.append({
            'name': 'Record Type',
            'type': 'dropdown',
            'description': 'Select the type of record to create',
            'required': True,
            'options': [
                {'value': form.get('Id', ''), 'label': form.get('Name', 'Form')}
                for form in forms
            ] if len(forms) > 1 else [{'value': 'default', 'label': app.get('Name', 'Record')}]
        })
        
        # Merge fields from all forms (with prefixes to avoid conflicts)
        seen_fields = set()
        
        for form in forms:
            form_prefix = f"{form.get('Name', 'form')}_" if len(forms) > 1 else ""
            
            for field in form.get('Fields', []):
                field_name = field.get('Name', '')
                
                # Skip duplicate field names
                if field_name in seen_fields and len(forms) > 1:
                    continue
                seen_fields.add(field_name)
                
                # Transform field
                transformed_field = self.field_transformer.transform_field_definition(field)
                
                # Add prefix if multiple forms
                if form_prefix:
                    transformed_field['name'] = f"{form_prefix}{transformed_field['name']}"
                    transformed_field['description'] = f"[{form.get('Name')}] {transformed_field.get('description', '')}"
                    transformed_field['conditional'] = {
                        'field': 'Record Type',
                        'value': form.get('Id', '')
                    }
                
                form_fields.append(transformed_field)
        
        # Add common app fields
        form_fields.extend([
            {
                'name': 'Priority',
                'type': 'dropdown',
                'description': 'Record priority',
                'required': False,
                'options': [
                    {'value': 'critical', 'label': 'Critical'},
                    {'value': 'high', 'label': 'High'},
                    {'value': 'medium', 'label': 'Medium'},
                    {'value': 'low', 'label': 'Low'}
                ],
                'default_value': 'medium'
            },
            {
                'name': 'Tags',
                'type': 'text',
                'description': 'Comma-separated tags',
                'required': False
            }
        ])
        
        return form_fields
    
    def _transform_workflow_step(self, wf_step: Dict[str, Any],
                                forms: List[Dict[str, Any]],
                                order: int) -> Dict[str, Any]:
        """Transform app workflow step to Tallyfy step.
        
        Args:
            wf_step: Workflow step
            forms: Available forms
            order: Step order
            
        Returns:
            Tallyfy step
        """
        step_type = wf_step.get('Type', 'task').lower()
        
        # Map step types
        if step_type == 'form':
            tallyfy_type = 'task'
        elif step_type == 'approval':
            tallyfy_type = 'approval'
        elif step_type == 'notification':
            tallyfy_type = "text"
        elif step_type == 'integration':
            tallyfy_type = 'task'  # With webhook
        else:
            tallyfy_type = 'task'
        
        step = {
            'order': order,
            'name': wf_step.get('Name', f'Step {order}'),
            'type': tallyfy_type,
            'description': wf_step.get('Description', ''),
            "assignees_form": self._get_step_assignee(wf_step),
            'duration': self._calculate_duration(wf_step),
            'form_fields': [],
            'metadata': {
                'original_type': step_type,
                'original_id': wf_step.get('Id')
            }
        }
        
        # Add form fields if it's a form step
        if step_type == 'form' and wf_step.get('FormId'):
            form = next((f for f in forms if f.get('Id') == wf_step['FormId']), None)
            if form:
                for field in form.get('Fields', []):
                    transformed_field = self.field_transformer.transform_field_definition(field)
                    step['form_fields'].append(transformed_field)
        
        # Add approval fields
        if tallyfy_type == 'approval':
            step['form_fields'].extend([
                {
                    'name': 'Decision',
                    'type': 'radio',
                    'required': True,
                    'options': [
                        {'value': 'approved', 'label': 'Approve'},
                        {'value': 'rejected', 'label': 'Reject'},
                        {'value': 'needs_info', 'label': 'Request More Information'}
                    ]
                },
                {
                    'name': 'Comments',
                    'type': 'textarea',
                    'description': 'Approval comments',
                    'required': False
                }
            ])
        
        # Handle integrations
        if step_type == 'integration':
            step['webhook'] = {
                "text": wf_step.get('Url', ''),
                'method': wf_step.get('Method', 'POST'),
                'headers': wf_step.get('Headers', {}),
                'body_template': wf_step.get('BodyTemplate', '')
            }
        
        return step
    
    def _create_basic_crud_steps(self, app: Dict[str, Any],
                                forms: List[Dict[str, Any]],
                                start_order: int) -> List[Dict[str, Any]]:
        """Create basic CRUD operation steps for apps without workflows.
        
        Args:
            app: App definition
            forms: App forms
            start_order: Starting order number
            
        Returns:
            List of CRUD steps
        """
        steps = []
        order = start_order
        
        # Review step
        steps.append({
            'order': order,
            'name': 'Review Record',
            'type': 'task',
            'description': 'Review the created record for completeness',
            "assignees_form": 'process_owner',
            'duration': 1,
            'form_fields': [
                {
                    'name': 'Review Notes',
                    'type': 'textarea',
                    'description': 'Add any review comments',
                    'required': False
                },
                {
                    'name': 'Data Quality',
                    'type': 'radio',
                    'description': 'Rate the data quality',
                    'required': True,
                    'options': [
                        {'value': 'excellent', 'label': 'Excellent'},
                        {'value': 'good', 'label': 'Good'},
                        {'value': 'needs_improvement', 'label': 'Needs Improvement'}
                    ]
                }
            ]
        })
        order += 1
        
        # Update step
        steps.append({
            'order': order,
            'name': 'Update Record',
            'type': 'task',
            'description': 'Make any necessary updates to the record',
            "assignees_form": 'process_owner',
            'duration': 1,
            'form_fields': [
                {
                    'name': 'Updates Made',
                    'type': 'textarea',
                    'description': 'Describe the updates made',
                    'required': False
                }
            ]
        })
        order += 1
        
        # Approval step
        steps.append({
            'order': order,
            'name': 'Approve Record',
            'type': 'approval',
            'description': 'Final approval of the record',
            "assignees_form": 'process_owner',
            'duration': 1,
            'form_fields': [
                {
                    'name': 'Approval Status',
                    'type': 'radio',
                    'required': True,
                    'options': [
                        {'value': 'approved', 'label': 'Approved'},
                        {'value': 'rejected', 'label': 'Rejected'}
                    ]
                },
                {
                    'name': 'Approval Comments',
                    'type': 'textarea',
                    'required': False
                }
            ]
        })
        
        return steps
    
    def _create_sub_blueprints(self, forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create sub-blueprints for complex forms.
        
        Args:
            forms: App forms
            
        Returns:
            List of sub-blueprint references
        """
        sub_blueprints = []
        
        for form in forms:
            sub_blueprint = {
                'name': f"Form: {form.get('Name', 'Form')}",
                'description': form.get('Description', ''),
                'type': 'form_process',
                'metadata': {
                    'form_id': form.get('Id'),
                    'field_count': len(form.get('Fields', [])),
                    'has_validation': bool(form.get('Validations')),
                    'has_calculations': bool(form.get('Calculations'))
                }
            }
            sub_blueprints.append(sub_blueprint)
        
        return sub_blueprints
    
    def _transform_views(self, views: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform app views to view configurations.
        
        Args:
            views: App views
            
        Returns:
            List of view configurations
        """
        view_configs = []
        
        for view in views:
            view_type = view.get('Type', 'list').lower()
            
            config = {
                'name': view.get('Name', 'View'),
                'type': 'list',  # Tallyfy mainly supports list views
                'description': f"Originally a {view_type} view in Kissflow",
                'filters': self._transform_view_filters(view.get('Filters', [])),
                'columns': self._transform_view_columns(view.get('Columns', [])),
                'sort': view.get('Sort', []),
                'metadata': {
                    'original_type': view_type,
                    'original_id': view.get('Id'),
                    'is_default': view.get('IsDefault', False)
                }
            }
            
            # Add view-specific notes
            if view_type == 'kanban':
                config['note'] = "Kanban board view - consider using Tallyfy's status-based filtering"
            elif view_type == 'calendar':
                config['note'] = "Calendar view - use date field filtering in Tallyfy"
            elif view_type == 'timeline':
                config['note'] = "Timeline view - use Tallyfy's timeline feature if available"
            elif view_type == 'chart':
                config['note'] = "Chart view - use Tallyfy's reporting features"
            
            view_configs.append(config)
        
        return view_configs
    
    def _transform_view_filters(self, filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform view filters.
        
        Args:
            filters: View filters
            
        Returns:
            Transformed filters
        """
        transformed_filters = []
        
        for filter_def in filters:
            transformed_filter = {
                'field': filter_def.get('Field', ''),
                'operator': filter_def.get('Operator', 'equals'),
                'value': filter_def.get('Value', ''),
                'type': filter_def.get('Type', 'static')
            }
            
            # Map operators
            operator_map = {
                'eq': 'equals',
                'ne': 'not_equals',
                'gt': 'greater_than',
                'lt': 'less_than',
                'gte': 'greater_or_equal',
                'lte': 'less_or_equal',
                'contains': 'contains',
                'not_contains': 'not_contains',
                'in': 'in_list',
                'not_in': 'not_in_list'
            }
            
            if filter_def.get('Operator') in operator_map:
                transformed_filter['operator'] = operator_map[filter_def['Operator']]
            
            transformed_filters.append(transformed_filter)
        
        return transformed_filters
    
    def _transform_view_columns(self, columns: List[Dict[str, Any]]) -> List[str]:
        """Transform view columns.
        
        Args:
            columns: View columns
            
        Returns:
            List of column names
        """
        return [col.get('Name', col.get('Field', '')) for col in columns]
    
    def _transform_app_automations(self, workflows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform app automations to Tallyfy rules.
        
        Args:
            workflows: App workflows with automations
            
        Returns:
            List of Tallyfy rules
        """
        rules = []
        
        for workflow in workflows:
            # Create rule from workflow trigger
            if workflow.get('Trigger'):
                trigger = workflow['Trigger']
                rule = {
                    'name': f"Auto: {workflow.get('Name', 'Workflow')}",
                    'description': workflow.get('Description', ''),
                    'trigger': {
                        'type': trigger.get('Type', 'manual'),
                        'event': trigger.get('Event', ''),
                        'conditions': trigger.get('Conditions', [])
                    },
                    'actions': []
                }
                
                # Add workflow execution as action
                rule['actions'].append({
                    'type': 'start_workflow',
                    'workflow_name': workflow.get('Name', ''),
                    'note': 'Automatically triggered from app event'
                })
                
                rules.append(rule)
            
            # Add step-level automations
            for step in workflow.get('Steps', []):
                if step.get('Automations'):
                    for automation in step['Automations']:
                        rule = {
                            'name': f"Step Auto: {step.get('Name', 'Step')}",
                            'description': automation.get('Description', ''),
                            'trigger': automation.get('Trigger', {}),
                            'actions': automation.get('Actions', [])
                        }
                        rules.append(rule)
        
        return rules
    
    def _get_workflow_assignee(self, workflow: Dict[str, Any]) -> str:
        """Get workflow assignee.
        
        Args:
            workflow: Workflow definition
            
        Returns:
            Assignee string
        """
        if workflow.get('DefaultAssignee'):
            return f"member:{workflow['DefaultAssignee']}"
        return 'process_initiator'
    
    def _get_workflow_approver(self, workflow: Dict[str, Any]) -> str:
        """Get workflow approver.
        
        Args:
            workflow: Workflow definition
            
        Returns:
            Approver string
        """
        if workflow.get('Approver'):
            return f"member:{workflow['Approver']}"
        return 'process_owner'
    
    def _get_step_assignee(self, step: Dict[str, Any]) -> str:
        """Get step assignee.
        
        Args:
            step: Step definition
            
        Returns:
            Assignee string
        """
        if step.get('Assignee'):
            if isinstance(step['Assignee'], dict):
                return f"member:{step['Assignee'].get('Id', '')}"
            return f"member:{step['Assignee']}"
        return 'process_owner'
    
    def _calculate_duration(self, step: Dict[str, Any]) -> int:
        """Calculate step duration.
        
        Args:
            step: Step definition
            
        Returns:
            Duration in days
        """
        if step.get('SLA'):
            # Convert hours to days
            return max(1, int(step['SLA'] / 24))
        
        # Default based on step type
        step_type = step.get('Type', 'task').lower()
        if step_type == 'approval':
            return 2
        elif step_type == 'notification':
            return 0
        else:
            return 1
    
    def _extract_tags(self, app: Dict[str, Any]) -> List[str]:
        """Extract tags from app.
        
        Args:
            app: Kissflow app
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add existing tags
        if app.get('Tags'):
            tags.extend(app['Tags'])
        
        # Add metadata tags
        tags.append('type:app')
        tags.append('source:kissflow')
        tags.append('complexity:high')
        
        if app.get('Category'):
            tags.append(f"category:{app['Category']}")
        
        if app.get('Type'):
            tags.append(f"app-type:{app['Type']}")
        
        return tags