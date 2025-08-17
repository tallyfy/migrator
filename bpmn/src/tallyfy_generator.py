#!/usr/bin/env python3
"""
Tallyfy Template JSON Generator
Generates complete, valid Tallyfy template JSON from BPMN migration results
Addresses all gaps identified in MIGRATION_GAPS_AND_ISSUES.md
"""

import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import re


class TallyfyTemplateGenerator:
    """
    Generates complete Tallyfy template JSON with all required fields
    Based on actual Tallyfy API v2 schema from Laravel codebase
    """
    
    def __init__(self):
        """Initialize generator with Tallyfy constants"""
        # Task types from constants.php
        self.TASK_TYPES = {
            'task': 'task',
            'approval': 'approval',
            'expiring': 'expiring',
            'email': 'email',
            'expiring_email': 'expiring_email'
        }
        
        # Field types from ALLOWED_CAPTURE_TYPES
        self.FIELD_TYPES = {
            'text': {'max_length': 200},
            'textarea': {'max_length': 30000},
            'radio': {'requires_options': True},
            'dropdown': {'requires_options': True},
            'multiselect': {'requires_options': True},
            'date': {'format': 'YYYY-MM-DD'},
            'email': {'validation': 'email'},
            'file': {'max_size': '10MB'},
            'table': {'columns': []},
            'assignees_form': {'type': 'user_picker'}
        }
        
        # Condition operators
        self.OPERATORS = [
            'equals', 'not_equals', 'equals_any', 'contains', 
            'not_contains', 'greater_than', 'less_than', 
            'is_empty', 'is_not_empty'
        ]
        
        # Action types
        self.ACTION_TYPES = [
            'show', 'hide', 'deadline', 'reopen', 
            'assign', 'unassign', 'assign_only', 'clear_assignees'
        ]
    
    def generate_template(self, 
                         bpmn_process: Dict[str, Any],
                         migration_results: Dict[str, Any],
                         config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate complete Tallyfy template from BPMN process
        
        Args:
            bpmn_process: Parsed BPMN process data
            migration_results: Results from rule engine migration
            config: Optional configuration overrides
            
        Returns:
            Complete Tallyfy template JSON
        """
        config = config or {}
        
        template = {
            # Basic Information
            'title': bpmn_process.get('name', 'Migrated Process'),
            'type': 'template',
            'summary': f"Migrated from BPMN: {bpmn_process.get('id', 'unknown')}",
            'tags': config.get('tags', ['bpmn-migration']),
            
            # Settings
            'is_public': config.get('is_public', False),
            'is_publishable': True,
            'allow_guests': config.get('allow_guests', False),
            'auto_archive_days': config.get('auto_archive_days', 30),
            
            # Ownership
            'owners': config.get('owners', []),
            'visibility': {
                'type': config.get('visibility_type', 'organization'),
                'user_ids': config.get('visible_to_users', [])
            },
            
            # Structure
            'prerun': self._generate_kickoff_form(bpmn_process),
            'steps': [],
            'automated_actions': [],
            
            # Metadata
            'version': 1,
            'source': 'bpmn_migration',
            'migration_metadata': {
                'bpmn_file': bpmn_process.get('source_file'),
                'migration_date': datetime.now(timezone.utc).isoformat(),
                'migration_version': '2.0',
                'original_process_id': bpmn_process.get('id')
            }
        }
        
        # Generate steps from tasks
        step_mapping = {}
        position = 0
        
        for element in bpmn_process.get('elements', {}).get('tasks', []):
            step = self._generate_step(element, position)
            template['steps'].append(step)
            step_mapping[element['id']] = step['id']
            position += 1
        
        # Generate automation rules from gateways
        for gateway in bpmn_process.get('elements', {}).get('gateways', []):
            automations = self._generate_gateway_automations(gateway, step_mapping, bpmn_process)
            template['automated_actions'].extend(automations)
        
        # Add form fields to appropriate steps
        self._attach_form_fields(template, bpmn_process)
        
        # Generate rules from sequence flow conditions
        self._generate_flow_conditions(template, bpmn_process, step_mapping)
        
        # Handle lanes as groups
        self._generate_groups_from_lanes(template, bpmn_process)
        
        # Process timer events as deadlines
        self._process_timer_events(template, bpmn_process)
        
        # Validate and clean template
        self._validate_template(template)
        
        return template
    
    def _generate_kickoff_form(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """Generate kick-off form from start event and initial data"""
        kickoff = {
            'enabled': False,
            'fields': []
        }
        
        # Check for start event with forms
        start_events = [e for e in process.get('elements', {}).get('events', []) 
                       if e.get('category') == 'start']
        
        if start_events:
            start_event = start_events[0]
            
            # If there are data objects referenced at start
            if process.get('elements', {}).get('dataObjects'):
                kickoff['enabled'] = True
                
                for data_obj in process['elements']['dataObjects'][:5]:  # Limit to 5 fields
                    field = {
                        'id': self._generate_id(data_obj.get('id', '')),
                        'name': self._sanitize_alias(data_obj.get('name', 'field')),
                        'label': data_obj.get('name', 'Data Field'),
                        'type': 'text',
                        'required': False,
                        'help_text': f"Data from BPMN: {data_obj.get('id', '')}"
                    }
                    kickoff['fields'].append(field)
        
        # Add decision fields for gateways
        gateways = process.get('elements', {}).get('gateways', [])
        for gateway in gateways:
            if gateway.get('type') == 'exclusiveGateway':
                field = self._create_gateway_decision_field(gateway)
                if field:
                    kickoff['enabled'] = True
                    kickoff['fields'].append(field)
        
        return kickoff
    
    def _generate_step(self, task: Dict[str, Any], position: int) -> Dict[str, Any]:
        """Generate Tallyfy step from BPMN task"""
        
        # Determine task type
        task_type = self._map_task_type(task.get('type', 'task'))
        
        step = {
            'id': self._generate_id(task.get('id', '')),
            'title': task.get('name', 'Unnamed Task'),
            'description': task.get('documentation', ''),
            'position': position,
            'task_type': task_type,
            'required': True,
            'hidden': False,
            
            # Timing
            'deadline': None,
            'start_date': None,
            
            # Assignment
            'assignees': [],
            'assign_to_step_completer': False,
            
            # Form fields
            'captures': [],
            
            # Integration
            'webhook': None,
            
            # Metadata
            'bpmn_element_id': task.get('id'),
            'bpmn_element_type': task.get('type')
        }
        
        # Add webhook for service tasks
        if task.get('type') == 'serviceTask':
            step['webhook'] = self._generate_webhook_config(task)
        
        # Handle multi-instance
        if task.get('properties', {}).get('multiInstance'):
            step['note'] = 'Multi-instance task - create multiple copies as needed'
        
        # Handle loop
        if task.get('properties', {}).get('loop'):
            step['note'] = 'Loop task - requires external scheduling for repetition'
        
        return step
    
    def _generate_gateway_automations(self, 
                                     gateway: Dict[str, Any], 
                                     step_mapping: Dict[str, str],
                                     process: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate automation rules from gateway"""
        automations = []
        
        if gateway['type'] == 'exclusiveGateway':
            # Create decision field
            decision_field_id = f"gateway_{gateway['id']}_decision"
            
            # Find outgoing flows
            flows = [f for f in process.get('elements', {}).get('flows', [])
                    if f.get('sourceRef') == gateway['id']]
            
            for i, flow in enumerate(flows):
                target = flow.get('targetRef')
                if target in step_mapping:
                    automation = {
                        'id': self._generate_id(f"rule_{gateway['id']}_{i}"),
                        'name': f"{gateway.get('name', 'Gateway')} - Path {i+1}",
                        'description': f"Route to {flow.get('name', 'next step')}",
                        'rules': [{
                            'id': self._generate_id(f"condition_{flow['id']}"),
                            'field_alias': decision_field_id,
                            'operator': 'equals',
                            'value': f"path_{i+1}"
                        }],
                        'actions': [{
                            'id': self._generate_id(f"action_{flow['id']}"),
                            'type': 'show',
                            'step_id': step_mapping[target]
                        }]
                    }
                    
                    # Parse condition if exists
                    if flow.get('condition'):
                        condition = self._parse_condition_expression(flow['condition'])
                        if condition:
                            automation['rules'][0].update(condition)
                    
                    automations.append(automation)
        
        elif gateway['type'] == 'parallelGateway':
            # For parallel gateway, show all outgoing paths
            flows = [f for f in process.get('elements', {}).get('flows', [])
                    if f.get('sourceRef') == gateway['id']]
            
            if flows:
                automation = {
                    'id': self._generate_id(f"parallel_{gateway['id']}"),
                    'name': f"{gateway.get('name', 'Parallel Gateway')}",
                    'description': "Execute parallel paths (visual only)",
                    'rules': [],  # No conditions for parallel
                    'actions': []
                }
                
                for flow in flows:
                    target = flow.get('targetRef')
                    if target in step_mapping:
                        automation['actions'].append({
                            'id': self._generate_id(f"parallel_action_{flow['id']}"),
                            'type': 'show',
                            'step_id': step_mapping[target]
                        })
                
                if automation['actions']:
                    automations.append(automation)
        
        return automations
    
    def _create_gateway_decision_field(self, gateway: Dict[str, Any]) -> Dict[str, Any]:
        """Create form field for gateway decision"""
        
        # Count outgoing paths
        outgoing_count = len(gateway.get('outgoing', []))
        
        field = {
            'id': self._generate_id(f"field_{gateway['id']}"),
            'name': f"gateway_{gateway['id']}_decision",
            'label': gateway.get('name', 'Decision'),
            'type': 'radio' if outgoing_count <= 4 else 'dropdown',
            'required': True,
            'options': [],
            'help_text': f"Decision point from BPMN gateway: {gateway['id']}"
        }
        
        # Generate options for each path
        for i in range(outgoing_count):
            field['options'].append({
                'value': f"path_{i+1}",
                'label': f"Option {i+1}"
            })
        
        return field
    
    def _attach_form_fields(self, template: Dict[str, Any], process: Dict[str, Any]):
        """Attach form fields to appropriate steps"""
        
        # Process any forms defined in tasks
        for task in process.get('elements', {}).get('tasks', []):
            if task.get('forms'):
                # Find corresponding step
                step = next((s for s in template['steps'] 
                           if s['bpmn_element_id'] == task['id']), None)
                
                if step:
                    for form in task['forms']:
                        capture = self._convert_form_field(form)
                        step['captures'].append(capture)
    
    def _convert_form_field(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BPMN form field to Tallyfy capture"""
        
        field_type = form.get('type', 'string')
        tallyfy_type = self._map_field_type(field_type)
        
        capture = {
            'id': self._generate_id(form.get('id', '')),
            'name': self._sanitize_alias(form.get('id', 'field')),
            'label': form.get('label', form.get('id', 'Field')),
            'type': tallyfy_type,
            'required': form.get('required', 'false') == 'true',
            'hidden': False,
            'read_only': False,
            'placeholder': '',
            'help_text': '',
            'default_value': form.get('defaultValue', '')
        }
        
        # Add validation if present
        if form.get('validation'):
            capture['validation'] = self._convert_validation(form['validation'])
        
        # Add options for select fields
        if tallyfy_type in ['radio', 'dropdown', 'multiselect'] and form.get('options'):
            capture['options'] = [
                {'value': opt.get('id', ''), 'label': opt.get('name', '')}
                for opt in form['options']
            ]
        
        return capture
    
    def _convert_validation(self, validation: Any) -> Dict[str, Any]:
        """Convert BPMN validation to Tallyfy validation"""
        
        result = {}
        
        # Handle different validation types
        if isinstance(validation, dict):
            if validation.get('min'):
                result['min'] = validation['min']
            if validation.get('max'):
                result['max'] = validation['max']
            if validation.get('pattern'):
                result['pattern'] = validation['pattern']
            if validation.get('minLength'):
                result['min_length'] = validation['minLength']
            if validation.get('maxLength'):
                result['max_length'] = validation['maxLength']
        elif isinstance(validation, list):
            # Handle constraint-based validation
            for constraint in validation:
                if constraint.get('name') == 'min':
                    result['min'] = constraint.get('config', 0)
                elif constraint.get('name') == 'max':
                    result['max'] = constraint.get('config', 999999)
                elif constraint.get('name') == 'required':
                    # Handled at field level
                    pass
        
        return result
    
    def _generate_flow_conditions(self, 
                                 template: Dict[str, Any], 
                                 process: Dict[str, Any],
                                 step_mapping: Dict[str, str]):
        """Generate conditional rules from sequence flows"""
        
        flows_with_conditions = [
            f for f in process.get('elements', {}).get('flows', [])
            if f.get('condition')
        ]
        
        for flow in flows_with_conditions:
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            
            if target in step_mapping:
                condition = self._parse_condition_expression(flow['condition'])
                
                if condition:
                    automation = {
                        'id': self._generate_id(f"flow_rule_{flow['id']}"),
                        'name': f"Condition: {flow.get('name', 'Flow condition')}",
                        'description': f"From {source} to {target}",
                        'rules': [condition],
                        'actions': [{
                            'id': self._generate_id(f"flow_action_{flow['id']}"),
                            'type': 'show',
                            'step_id': step_mapping[target]
                        }]
                    }
                    template['automated_actions'].append(automation)
    
    def _parse_condition_expression(self, expression: str) -> Optional[Dict[str, Any]]:
        """Parse BPMN condition expression to Tallyfy rule"""
        
        if not expression:
            return None
        
        # Remove CDATA wrapper if present
        expression = expression.replace('<![CDATA[', '').replace(']]>', '').strip()
        
        # Try to parse common patterns
        patterns = [
            # ${variable == value}
            r'\$\{(\w+)\s*==\s*["\']?(\w+)["\']?\}',
            # ${variable > value}
            r'\$\{(\w+)\s*>\s*(\d+)\}',
            # ${variable < value}
            r'\$\{(\w+)\s*<\s*(\d+)\}',
            # ${variable != value}
            r'\$\{(\w+)\s*!=\s*["\']?(\w+)["\']?\}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, expression)
            if match:
                field = match.group(1)
                value = match.group(2)
                
                # Determine operator
                if '==' in expression:
                    operator = 'equals'
                elif '!=' in expression:
                    operator = 'not_equals'
                elif '>' in expression:
                    operator = 'greater_than'
                elif '<' in expression:
                    operator = 'less_than'
                else:
                    operator = 'equals'
                
                return {
                    'field_alias': self._sanitize_alias(field),
                    'operator': operator,
                    'value': value
                }
        
        # Fallback: create a text note about the condition
        return {
            'field_alias': 'manual_check',
            'operator': 'equals',
            'value': 'true',
            'note': f"Original condition: {expression}"
        }
    
    def _generate_groups_from_lanes(self, template: Dict[str, Any], process: Dict[str, Any]):
        """Generate groups from BPMN lanes"""
        
        template['groups'] = []
        
        for lane in process.get('elements', {}).get('lanes', []):
            group = {
                'id': self._generate_id(lane['id']),
                'name': lane.get('name', 'Lane'),
                'description': f"From BPMN lane: {lane['id']}",
                'members': []  # To be populated manually
            }
            template['groups'].append(group)
            
            # Assign steps to groups based on lane references
            for ref in lane.get('flowNodeRefs', []):
                step = next((s for s in template['steps'] 
                           if s['bpmn_element_id'] == ref), None)
                if step:
                    step['assignees'].append({
                        'type': 'group',
                        'group_id': group['id']
                    })
    
    def _process_timer_events(self, template: Dict[str, Any], process: Dict[str, Any]):
        """Process timer events and add deadlines to steps"""
        
        timer_events = [
            e for e in process.get('elements', {}).get('events', [])
            if e.get('eventType') == 'timer'
        ]
        
        for event in timer_events:
            # Parse timer duration if available
            deadline = self._parse_timer_duration(event)
            
            if deadline and event.get('attachedTo'):
                # Find the task this timer is attached to
                step = next((s for s in template['steps']
                           if s['bpmn_element_id'] == event['attachedTo']), None)
                if step:
                    step['deadline'] = deadline
    
    def _parse_timer_duration(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ISO 8601 duration to Tallyfy deadline"""
        
        # This is simplified - full ISO 8601 parsing would be more complex
        # P1DT12H30M = 1 day, 12 hours, 30 minutes
        
        duration_str = event.get('duration', '')
        
        # Simple pattern matching
        if 'PT' in duration_str:
            # Time-based duration
            hours = re.search(r'(\d+)H', duration_str)
            if hours:
                return {
                    'step': 'start_run',
                    'unit': 'hour',
                    'value': int(hours.group(1))
                }
        elif 'P' in duration_str:
            # Date-based duration
            days = re.search(r'P(\d+)D', duration_str)
            if days:
                return {
                    'step': 'start_run',
                    'unit': 'day',
                    'value': int(days.group(1))
                }
        
        return None
    
    def _generate_webhook_config(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate webhook configuration for service task"""
        
        return {
            'url': '{{WEBHOOK_URL}}',  # To be configured
            'method': 'POST',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': {
                'task_id': task.get('id'),
                'task_name': task.get('name'),
                'process_id': '{{process_id}}',
                'data': '{{step_data}}'
            },
            'auth': {
                'type': 'none'  # To be configured
            }
        }
    
    def _map_task_type(self, bpmn_type: str) -> str:
        """Map BPMN task type to Tallyfy task type"""
        
        mapping = {
            'userTask': 'task',
            'manualTask': 'task',
            'serviceTask': 'task',
            'scriptTask': 'task',
            'businessRuleTask': 'task',
            'sendTask': 'email',
            'receiveTask': 'approval',
            'task': 'task'
        }
        
        return mapping.get(bpmn_type, 'task')
    
    def _map_field_type(self, bpmn_type: str) -> str:
        """Map BPMN field type to Tallyfy field type"""
        
        mapping = {
            'string': 'text',
            'long': 'text',
            'boolean': 'radio',
            'date': 'date',
            'enum': 'dropdown',
            'text': 'textarea'
        }
        
        return mapping.get(bpmn_type, 'text')
    
    def _sanitize_alias(self, name: str) -> str:
        """Sanitize field name for alias"""
        
        # Remove special characters, convert to lowercase
        alias = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        alias = alias.lower()
        
        # Ensure it starts with a letter
        if alias and not alias[0].isalpha():
            alias = 'field_' + alias
        
        return alias or 'field'
    
    def _generate_id(self, base: str = '') -> str:
        """Generate unique ID"""
        
        if not base:
            base = 'generated'
        
        # Create hash for uniqueness
        hash_input = f"{base}_{datetime.now(timezone.utc).isoformat()}"
        hash_digest = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        return f"{base}_{hash_digest}"
    
    def _validate_template(self, template: Dict[str, Any]):
        """Validate and clean template"""
        
        # Ensure required fields
        if not template.get('title'):
            template['title'] = 'Untitled Process'
        
        # Ensure at least one step
        if not template.get('steps'):
            template['steps'].append({
                'id': self._generate_id('default_step'),
                'title': 'Process Step',
                'description': 'Add process steps here',
                'position': 0,
                'task_type': 'task',
                'required': True,
                'hidden': False,
                'captures': [],
                'assignees': []
            })
        
        # Clean up empty arrays
        if not template.get('automated_actions'):
            template.pop('automated_actions', None)
        
        if not template.get('groups'):
            template.pop('groups', None)
        
        # Ensure kickoff form structure
        if not template.get('prerun', {}).get('enabled'):
            template['prerun'] = {'enabled': False, 'fields': []}


def generate_complete_tallyfy_template(bpmn_file: str, output_file: str = None) -> Dict[str, Any]:
    """
    Helper function to generate complete Tallyfy template from BPMN
    
    Args:
        bpmn_file: Path to BPMN file
        output_file: Optional output JSON file
        
    Returns:
        Complete Tallyfy template
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from migrator import BPMNToTallyfyMigrator
    
    # Parse BPMN
    migrator = BPMNToTallyfyMigrator()
    results = migrator.migrate_file(bpmn_file)
    
    # Generate Tallyfy template
    generator = TallyfyTemplateGenerator()
    
    templates = []
    for process in results.get('processes', []):
        template = generator.generate_template(
            process,
            results.get('migration_report', {}),
            config={
                'tags': ['bpmn-import', 'automated'],
                'auto_archive_days': 90
            }
        )
        templates.append(template)
    
    # Save if requested
    if output_file and templates:
        with open(output_file, 'w') as f:
            json.dump(templates[0] if len(templates) == 1 else templates, f, indent=2)
        print(f"Template saved to: {output_file}")
    
    return templates[0] if templates else {}


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Tallyfy template from BPMN')
    parser.add_argument('bpmn_file', help='BPMN file to convert')
    parser.add_argument('-o', '--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    template = generate_complete_tallyfy_template(args.bpmn_file, args.output)
    
    print(f"\nGenerated Tallyfy template:")
    print(f"  Title: {template.get('title')}")
    print(f"  Steps: {len(template.get('steps', []))}")
    print(f"  Automations: {len(template.get('automated_actions', []))}")
    print(f"  Form Fields: {sum(len(s.get('captures', [])) for s in template.get('steps', []))}")