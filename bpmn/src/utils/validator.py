"""Validation utilities for BPMN to Tallyfy migration"""

from typing import Dict, List, Any, Optional, Tuple
import re


class Validator:
    """Validates BPMN and Tallyfy data structures"""
    
    def __init__(self):
        """Initialize validator with rules"""
        self.errors = []
        self.warnings = []
    
    def validate_bpmn(self, bpmn_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate BPMN data structure
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Check for required elements
        if not bpmn_data:
            self.errors.append("BPMN data is empty")
            return False, self.errors
        
        # Check for process
        if 'processes' not in bpmn_data or not bpmn_data['processes']:
            self.errors.append("No processes found in BPMN")
        
        # Validate each process
        for process in bpmn_data.get('processes', []):
            self._validate_bpmn_process(process)
        
        is_valid = len(self.errors) == 0
        all_issues = self.errors + self.warnings
        
        return is_valid, all_issues
    
    def _validate_bpmn_process(self, process: Dict[str, Any]):
        """Validate a single BPMN process"""
        
        # Check for process ID
        if not process.get('id'):
            self.errors.append("Process missing ID")
        
        # Check for at least one task
        elements = process.get('elements', {})
        tasks = elements.get('tasks', [])
        
        if not tasks:
            self.warnings.append(f"Process {process.get('id', 'unknown')} has no tasks")
        
        # Check for start and end events
        events = elements.get('events', [])
        start_events = [e for e in events if e.get('category') == 'start']
        end_events = [e for e in events if e.get('category') == 'end']
        
        if not start_events:
            self.warnings.append(f"Process {process.get('id', 'unknown')} has no start event")
        
        if not end_events:
            self.warnings.append(f"Process {process.get('id', 'unknown')} has no end event")
        
        # Check for disconnected elements
        flows = elements.get('flows', [])
        self._check_connectivity(tasks, flows, process.get('id', 'unknown'))
    
    def _check_connectivity(self, tasks: List[Dict], flows: List[Dict], process_id: str):
        """Check if all tasks are connected"""
        
        connected_elements = set()
        
        for flow in flows:
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            
            if source:
                connected_elements.add(source)
            if target:
                connected_elements.add(target)
        
        for task in tasks:
            task_id = task.get('id')
            if task_id and task_id not in connected_elements:
                self.warnings.append(
                    f"Task '{task.get('name', task_id)}' in process {process_id} is not connected"
                )
    
    def validate_tallyfy_template(self, template: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate Tallyfy template structure
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Required fields
        if not template.get('title'):
            self.errors.append("Template missing title")
        
        # Validate steps
        steps = template.get('steps', [])
        if not steps:
            self.errors.append("Template has no steps")
        else:
            for i, step in enumerate(steps):
                self._validate_tallyfy_step(step, i)
        
        # Validate automation rules
        automations = template.get('automated_actions', [])
        for automation in automations:
            self._validate_automation_rule(automation)
        
        # Validate kickoff form
        if template.get('prerun', {}).get('enabled'):
            self._validate_kickoff_form(template['prerun'])
        
        is_valid = len(self.errors) == 0
        all_issues = self.errors + self.warnings
        
        return is_valid, all_issues
    
    def _validate_tallyfy_step(self, step: Dict[str, Any], index: int):
        """Validate a Tallyfy step"""
        
        # Required fields
        if not step.get('id'):
            self.errors.append(f"Step {index} missing ID")
        
        if not step.get('title'):
            self.errors.append(f"Step {index} missing title")
        
        # Validate task type
        valid_task_types = ['task', 'approval', 'expiring', 'email', 'expiring_email']
        if step.get('task_type') not in valid_task_types:
            self.warnings.append(
                f"Step '{step.get('title', index)}' has invalid task type: {step.get('task_type')}"
            )
        
        # Validate captures (form fields)
        for capture in step.get('captures', []):
            self._validate_capture(capture, step.get('title', f'Step {index}'))
        
        # Validate webhook if present
        if step.get('webhook'):
            self._validate_webhook(step['webhook'], step.get('title', f'Step {index}'))
    
    def _validate_capture(self, capture: Dict[str, Any], step_title: str):
        """Validate a form field"""
        
        if not capture.get('id'):
            self.errors.append(f"Capture in step '{step_title}' missing ID")
        
        if not capture.get('name'):
            self.errors.append(f"Capture in step '{step_title}' missing name")
        
        # Validate field name (alias)
        name = capture.get('name', '')
        if name and not re.match(r'^[a-z][a-z0-9_]*$', name):
            self.warnings.append(
                f"Capture name '{name}' in step '{step_title}' should be lowercase alphanumeric with underscores"
            )
        
        # Validate field type
        valid_types = ['text', 'textarea', 'radio', 'dropdown', 'multiselect', 
                      'date', 'email', 'file', 'table', 'assignees_form']
        if capture.get('type') not in valid_types:
            self.errors.append(
                f"Capture in step '{step_title}' has invalid type: {capture.get('type')}"
            )
        
        # Validate options for select fields
        if capture.get('type') in ['radio', 'dropdown', 'multiselect']:
            if not capture.get('options'):
                self.errors.append(
                    f"Capture '{capture.get('name', 'unknown')}' in step '{step_title}' requires options"
                )
    
    def _validate_webhook(self, webhook: Dict[str, Any], step_title: str):
        """Validate webhook configuration"""
        
        if not webhook.get('url'):
            self.warnings.append(f"Webhook in step '{step_title}' missing URL")
        
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        if webhook.get('method') not in valid_methods:
            self.warnings.append(
                f"Webhook in step '{step_title}' has invalid method: {webhook.get('method')}"
            )
    
    def _validate_automation_rule(self, automation: Dict[str, Any]):
        """Validate an automation rule"""
        
        if not automation.get('id'):
            self.errors.append("Automation rule missing ID")
        
        if not automation.get('name'):
            self.warnings.append("Automation rule missing name")
        
        # Validate rules (conditions)
        for rule in automation.get('rules', []):
            if not rule.get('field_alias'):
                self.warnings.append(
                    f"Rule in automation '{automation.get('name', 'unknown')}' missing field_alias"
                )
            
            valid_operators = ['equals', 'not_equals', 'contains', 'not_contains',
                             'greater_than', 'less_than', 'is_empty', 'is_not_empty']
            if rule.get('operator') not in valid_operators:
                self.warnings.append(
                    f"Rule in automation '{automation.get('name', 'unknown')}' has invalid operator"
                )
        
        # Validate actions
        if not automation.get('actions'):
            self.warnings.append(
                f"Automation '{automation.get('name', 'unknown')}' has no actions"
            )
        
        for action in automation.get('actions', []):
            valid_action_types = ['show', 'hide', 'assign', 'unassign', 'deadline']
            if action.get('type') not in valid_action_types:
                self.warnings.append(
                    f"Action in automation '{automation.get('name', 'unknown')}' has invalid type"
                )
    
    def _validate_kickoff_form(self, kickoff: Dict[str, Any]):
        """Validate kickoff form"""
        
        fields = kickoff.get('fields', [])
        if not fields:
            self.warnings.append("Kickoff form enabled but has no fields")
        
        for field in fields:
            self._validate_capture(field, 'Kickoff form')
    
    def get_validation_report(self) -> str:
        """Get a formatted validation report"""
        
        report = []
        
        if self.errors:
            report.append("❌ ERRORS:")
            for error in self.errors:
                report.append(f"  - {error}")
        
        if self.warnings:
            if report:
                report.append("")
            report.append("⚠️ WARNINGS:")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            report.append("✅ Validation passed with no issues")
        
        return "\n".join(report)