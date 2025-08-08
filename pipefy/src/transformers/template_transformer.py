"""
Template Transformer for RocketLane to Tallyfy Migration
Handles project template to blueprint conversion with paradigm shifts
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class TemplateTransformer:
    """Transform RocketLane project templates to Tallyfy blueprints"""
    
    def __init__(self, ai_client=None):
        """
        Initialize template transformer
        
        Args:
            ai_client: Optional AI client for complex mappings
        """
        self.ai_client = ai_client
        self.field_transformer = FieldTransformer(ai_client)
        self.transformation_stats = {
            'total': 0,
            'successful': 0,
            'phases_converted': 0,
            'tasks_converted': 0,
            'forms_converted': 0,
            'ai_assisted': 0
        }
    
    def transform_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a RocketLane project template to Tallyfy blueprint
        
        Args:
            template: RocketLane project template
            
        Returns:
            Tallyfy blueprint structure
        """
        self.transformation_stats['total'] += 1
        
        template_name = template.get('name', 'Untitled Template')
        logger.info(f"Transforming template: {template_name}")
        
        # Basic blueprint structure
        blueprint = {
            'name': template_name[:250],
            'description': self._build_description(template),
            'summary': template.get('description', '')[:2000],
            'metadata': {
                'source': 'rocketlane',
                'original_id': template.get('id'),
                'created_at': template.get('created_at'),
                'customer_type': template.get('customer_type', 'general'),
                'industry': template.get('industry'),
                'complexity': self._assess_complexity(template)
            },
            'steps': [],
            'kickoff_form': None
        }
        
        # Transform phases to sequential steps
        if template.get('phases'):
            blueprint['steps'] = self._transform_phases(template['phases'])
            self.transformation_stats['phases_converted'] += len(template['phases'])
        
        # Transform tasks within phases
        if template.get('tasks'):
            self._integrate_tasks_into_steps(blueprint['steps'], template['tasks'])
            self.transformation_stats['tasks_converted'] += len(template['tasks'])
        
        # Transform forms to kickoff form or step forms
        if template.get('forms'):
            kickoff_form, step_forms = self._transform_forms(template['forms'])
            if kickoff_form:
                blueprint['kickoff_form'] = kickoff_form
                self.transformation_stats['forms_converted'] += 1
            
            # Integrate step forms into appropriate steps
            if step_forms:
                self._integrate_step_forms(blueprint['steps'], step_forms)
                self.transformation_stats['forms_converted'] += len(step_forms)
        
        # Handle customer portal paradigm shift
        if template.get('customer_visible', False):
            blueprint = self._apply_customer_paradigm_shift(blueprint, template)
            if self.ai_client and self.ai_client.enabled:
                self.transformation_stats['ai_assisted'] += 1
        
        # Add automation rules
        if template.get('automations'):
            blueprint['automations'] = self._transform_automations(template['automations'])
        
        # Add SLAs and deadlines
        if template.get('sla_config'):
            blueprint['sla'] = self._transform_sla(template['sla_config'])
        
        self.transformation_stats['successful'] += 1
        return blueprint
    
    def _build_description(self, template: Dict[str, Any]) -> str:
        """Build comprehensive description for blueprint"""
        parts = []
        
        if template.get('description'):
            parts.append(template['description'])
        
        if template.get('customer_type'):
            parts.append(f"Customer Type: {template['customer_type']}")
        
        if template.get('estimated_duration'):
            parts.append(f"Estimated Duration: {template['estimated_duration']} days")
        
        if template.get('team_size'):
            parts.append(f"Team Size: {template['team_size']}")
        
        if template.get('deliverables'):
            parts.append(f"Deliverables: {', '.join(template['deliverables'])}")
        
        return ' | '.join(parts)[:2000]
    
    def _assess_complexity(self, template: Dict[str, Any]) -> str:
        """Assess template complexity for appropriate transformation"""
        score = 0
        
        # Count elements
        phases = len(template.get('phases', []))
        tasks = len(template.get('tasks', []))
        forms = len(template.get('forms', []))
        automations = len(template.get('automations', []))
        
        # Calculate complexity score
        score += phases * 2
        score += tasks
        score += forms * 3
        score += automations * 2
        
        # Add complexity for customer visibility
        if template.get('customer_visible'):
            score += 10
        
        # Add complexity for dependencies
        for task in template.get('tasks', []):
            if task.get('dependencies'):
                score += len(task['dependencies'])
        
        # Determine complexity level
        if score < 20:
            return 'simple'
        elif score < 50:
            return 'medium'
        else:
            return 'complex'
    
    def _transform_phases(self, phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform RocketLane phases to Tallyfy step groups"""
        transformed_steps = []
        
        # Sort phases by order/dependencies
        sorted_phases = sorted(phases, key=lambda p: (
            p.get('order', 999),
            p.get('start_after_days', 0)
        ))
        
        for phase in sorted_phases:
            # Create step group for phase
            step_group = {
                'name': phase.get('name', 'Phase')[:600],
                'description': phase.get('description', ''),
                'type': 'group',
                'metadata': {
                    'original_phase_id': phase.get('id'),
                    'duration_days': phase.get('duration_days'),
                    'milestone': phase.get('is_milestone', False)
                },
                'steps': []  # Will be populated with tasks
            }
            
            # Handle phase-level requirements
            if phase.get('entry_criteria'):
                step_group['entry_conditions'] = self._transform_criteria(
                    phase['entry_criteria']
                )
            
            if phase.get('exit_criteria'):
                step_group['completion_conditions'] = self._transform_criteria(
                    phase['exit_criteria']
                )
            
            # Handle phase owner/assignee
            if phase.get('default_owner'):
                step_group['default_assignee'] = phase['default_owner']
            
            transformed_steps.append(step_group)
        
        return transformed_steps
    
    def _integrate_tasks_into_steps(self, steps: List[Dict], tasks: List[Dict]):
        """Integrate tasks into appropriate phase steps"""
        # Create phase lookup
        phase_map = {}
        for step in steps:
            if step.get('metadata', {}).get('original_phase_id'):
                phase_id = step['metadata']['original_phase_id']
                phase_map[phase_id] = step
        
        # Group tasks by phase
        for task in tasks:
            phase_id = task.get('phase_id')
            
            if phase_id and phase_id in phase_map:
                # Add task to phase
                task_step = self._transform_task(task)
                phase_map[phase_id]['steps'].append(task_step)
            else:
                # Standalone task - add as top-level step
                task_step = self._transform_task(task)
                steps.append(task_step)
    
    def _transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Transform RocketLane task to Tallyfy step"""
        step = {
            'name': task.get('title', 'Task')[:600],
            'description': task.get('description', ''),
            'type': self._determine_task_type(task),
            'metadata': {
                'original_task_id': task.get('id'),
                'task_type': task.get('type'),
                'estimated_hours': task.get('estimated_hours'),
                'skills_required': task.get('skills', [])
            }
        }
        
        # Handle task assignment
        if task.get('assigned_role'):
            step['assignee_type'] = 'role'
            step['assignee_value'] = task['assigned_role']
        elif task.get('assigned_to'):
            step['assignee_type'] = 'user'
            step['assignee_value'] = task['assigned_to']
        
        # Handle due dates
        if task.get('due_after_days'):
            step['deadline_days'] = task['due_after_days']
        
        # Handle dependencies
        if task.get('dependencies'):
            step['dependencies'] = [
                {'task_id': dep, 'type': 'finish_to_start'}
                for dep in task['dependencies']
            ]
        
        # Handle task fields/form
        if task.get('custom_fields'):
            step['form_fields'] = self.field_transformer.transform_fields_batch(
                task['custom_fields']
            )
        
        # Handle customer visibility
        if task.get('customer_visible'):
            step['guest_can_complete'] = True
            step['send_guest_notification'] = True
        
        # Handle approval requirements
        if task.get('requires_approval'):
            step['type'] = 'approval'
            step['approval_type'] = task.get('approval_type', 'any')
        
        return step
    
    def _determine_task_type(self, task: Dict[str, Any]) -> str:
        """Determine appropriate Tallyfy task type"""
        task_type = task.get('type', '').lower()
        
        if 'approval' in task_type or task.get('requires_approval'):
            return 'approval'
        elif 'milestone' in task_type or task.get('is_milestone'):
            return 'milestone'
        elif 'review' in task_type:
            return 'approval'
        elif 'form' in task_type or task.get('custom_fields'):
            return 'form'
        elif task.get('due_date') and task.get('strict_deadline'):
            return 'expiring'
        else:
            return 'task'
    
    def _transform_forms(self, forms: List[Dict[str, Any]]) -> tuple:
        """Transform forms to kickoff and step forms"""
        kickoff_form = None
        step_forms = []
        
        for form in forms:
            form_type = form.get('type', 'general')
            field_count = len(form.get('fields', []))
            
            # Determine form placement based on type and complexity
            if form_type in ['onboarding', 'kickoff', 'initial'] or form.get('is_kickoff'):
                # Merge into single kickoff form if simple
                if field_count <= 20:
                    if not kickoff_form:
                        kickoff_form = {
                            'name': 'Process Kickoff Form',
                            'fields': []
                        }
                    kickoff_form['fields'].extend(
                        self.field_transformer.transform_fields_batch(form['fields'])
                    )
                else:
                    # Complex form becomes multi-step workflow
                    step_forms.extend(self._split_complex_form(form))
            
            elif form_type in ['feedback', 'survey', 'assessment']:
                # Becomes approval step with form
                step_forms.append({
                    'name': form.get('name', 'Feedback Form'),
                    'type': 'approval',
                    'position': form.get('position', 999),
                    'fields': self.field_transformer.transform_fields_batch(form['fields'])
                })
            
            else:
                # General form becomes step form
                step_forms.append({
                    'name': form.get('name', 'Form'),
                    'type': 'form',
                    'position': form.get('position', 999),
                    'fields': self.field_transformer.transform_fields_batch(form['fields'])
                })
        
        return kickoff_form, step_forms
    
    def _split_complex_form(self, form: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split complex form into multiple steps"""
        fields = form.get('fields', [])
        step_forms = []
        
        # Group fields by section or type
        sections = {}
        for field in fields:
            section = field.get('section', 'General')
            if section not in sections:
                sections[section] = []
            sections[section].append(field)
        
        # Create step for each section
        for section_name, section_fields in sections.items():
            step_forms.append({
                'name': f"{form.get('name', 'Form')} - {section_name}",
                'type': 'form',
                'fields': self.field_transformer.transform_fields_batch(section_fields)
            })
        
        return step_forms
    
    def _integrate_step_forms(self, steps: List[Dict], step_forms: List[Dict]):
        """Integrate step forms into workflow steps"""
        for form in step_forms:
            # Try to find matching step by position or name
            inserted = False
            
            for step in steps:
                if step.get('type') == 'group':
                    # Check if form belongs to this phase
                    if form.get('phase_id') == step['metadata'].get('original_phase_id'):
                        step['steps'].insert(0, form)  # Add form at beginning of phase
                        inserted = True
                        break
            
            if not inserted:
                # Add as standalone step
                steps.append(form)
    
    def _apply_customer_paradigm_shift(self, blueprint: Dict, template: Dict) -> Dict:
        """Apply paradigm shift for customer-facing templates"""
        portal_handling = os.getenv('CUSTOMER_PORTAL_HANDLING', 'guest_users')
        
        if self.ai_client and self.ai_client.enabled:
            # Use AI to determine optimal transformation
            try:
                decision = self.ai_client.transform_customer_template(template)
                if decision and decision.get('confidence', 0) > 0.7:
                    portal_handling = decision.get('strategy', portal_handling)
                    blueprint['metadata']['ai_paradigm_shift'] = decision
            except Exception as e:
                logger.warning(f"AI paradigm shift failed, using fallback: {e}")
        
        # Apply transformation based on strategy
        if portal_handling == 'guest_users':
            # Transform to guest-accessible workflow
            blueprint['guest_access'] = True
            blueprint['guest_can_view_progress'] = True
            
            # Mark customer-visible steps
            for step in blueprint['steps']:
                if isinstance(step, dict):
                    if step.get('type') == 'group':
                        for substep in step.get('steps', []):
                            if template.get('customer_tasks', {}).get(
                                substep.get('metadata', {}).get('original_task_id')
                            ):
                                substep['guest_can_complete'] = True
                    elif template.get('customer_tasks', {}).get(
                        step.get('metadata', {}).get('original_task_id')
                    ):
                        step['guest_can_complete'] = True
        
        elif portal_handling == 'organizations':
            # Create separate organization for customer
            blueprint['create_customer_org'] = True
            blueprint['org_type'] = 'customer'
            blueprint['shared_with_parent'] = True
        
        return blueprint
    
    def _transform_criteria(self, criteria: List[str]) -> List[Dict[str, Any]]:
        """Transform entry/exit criteria to conditions"""
        conditions = []
        
        for criterion in criteria:
            conditions.append({
                'type': 'manual_check',
                'description': criterion,
                'required': True
            })
        
        return conditions
    
    def _transform_automations(self, automations: List[Dict]) -> List[Dict]:
        """Transform RocketLane automations to Tallyfy rules"""
        rules = []
        
        for automation in automations:
            rule = {
                'name': automation.get('name', 'Automation'),
                'trigger': self._map_trigger(automation.get('trigger')),
                'conditions': self._map_conditions(automation.get('conditions', [])),
                'actions': self._map_actions(automation.get('actions', [])),
                'metadata': {
                    'original_id': automation.get('id'),
                    'original_type': automation.get('type')
                }
            }
            rules.append(rule)
        
        return rules
    
    def _map_trigger(self, trigger: Dict) -> Dict:
        """Map RocketLane trigger to Tallyfy trigger"""
        trigger_type = trigger.get('type', 'unknown')
        
        mapping = {
            'task_completed': 'step_completed',
            'phase_started': 'step_started',
            'form_submitted': 'form_submitted',
            'due_date_approaching': 'deadline_approaching',
            'project_started': 'process_started'
        }
        
        return {
            'type': mapping.get(trigger_type, 'manual'),
            'config': trigger.get('config', {})
        }
    
    def _map_conditions(self, conditions: List) -> List[Dict]:
        """Map automation conditions"""
        mapped = []
        
        for condition in conditions:
            mapped.append({
                'field': condition.get('field'),
                'operator': condition.get('operator', 'equals'),
                'value': condition.get('value')
            })
        
        return mapped
    
    def _map_actions(self, actions: List) -> List[Dict]:
        """Map automation actions"""
        mapped = []
        
        for action in actions:
            action_type = action.get('type')
            
            if action_type == 'send_email':
                mapped.append({
                    'type': 'send_notification',
                    'recipient': action.get('to'),
                    'template': action.get('template')
                })
            elif action_type == 'create_task':
                mapped.append({
                    'type': 'create_step',
                    'step_template': action.get('task_template')
                })
            elif action_type == 'update_field':
                mapped.append({
                    'type': 'set_field_value',
                    'field': action.get('field'),
                    'value': action.get('value')
                })
            else:
                # Generic action
                mapped.append({
                    'type': action_type,
                    'config': action.get('config', {})
                })
        
        return mapped
    
    def _transform_sla(self, sla_config: Dict) -> Dict:
        """Transform SLA configuration"""
        return {
            'response_time': sla_config.get('response_hours', 24),
            'resolution_time': sla_config.get('resolution_days', 7),
            'escalation_rules': sla_config.get('escalation', []),
            'business_hours': sla_config.get('business_hours', {
                'monday': '09:00-17:00',
                'tuesday': '09:00-17:00',
                'wednesday': '09:00-17:00',
                'thursday': '09:00-17:00',
                'friday': '09:00-17:00'
            })
        }
    
    def transform_templates_batch(self, templates: List[Dict]) -> List[Dict]:
        """Transform multiple templates"""
        transformed = []
        
        for template in templates:
            try:
                blueprint = self.transform_template(template)
                transformed.append(blueprint)
            except Exception as e:
                logger.error(f"Failed to transform template {template.get('name')}: {e}")
        
        return transformed
    
    def get_stats(self) -> Dict[str, int]:
        """Get transformation statistics"""
        return self.transformation_stats.copy()


# Import os for environment variables
import os