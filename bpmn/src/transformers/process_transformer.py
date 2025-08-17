"""
BPMN Process Transformer
Transforms BPMN processes into Tallyfy templates
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProcessTransformer:
    """Transform BPMN processes to Tallyfy templates"""
    
    def __init__(self, ai_client=None, id_mapper=None):
        """
        Initialize process transformer
        
        Args:
            ai_client: AI client for complex transformations
            id_mapper: ID mapping utility
        """
        self.ai_client = ai_client
        self.id_mapper = id_mapper
        
        # Track transformations
        self.stats = {
            'processes_transformed': 0,
            'tasks_created': 0,
            'gateways_transformed': 0,
            'events_mapped': 0,
            'rules_created': 0
        }
    
    def transform_process(self, bpmn_process: Dict[str, Any], 
                         collaboration: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transform a BPMN process into a Tallyfy template
        
        Args:
            bpmn_process: BPMN process data
            collaboration: Optional collaboration context (pools/lanes)
            
        Returns:
            Tallyfy template structure
        """
        logger.info(f"Transforming BPMN process: {bpmn_process.get('name', bpmn_process['id'])}")
        
        # Generate Tallyfy template ID
        template_id = self._generate_tallyfy_id('tpl', bpmn_process['id'])
        
        # Initialize template structure
        tallyfy_template = {
            'id': template_id,
            'title': bpmn_process.get('name', 'Untitled Process'),
            'description': f"Migrated from BPMN process: {bpmn_process['id']}",
            'status': 'active',
            'is_template': True,
            'is_public': False,
            'version': 1,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            
            # Process configuration
            'config': {
                'allow_comments': True,
                'allow_attachments': True,
                'require_approval': False,
                'auto_assign': True,
                'sequential': True,  # Will be adjusted based on gateways
                'notify_on_complete': True,
                'is_executable': bpmn_process.get('is_executable', False)
            },
            
            # Elements to be populated
            'steps': [],
            'field': [],  # Kick-off form fields
            'rules': [],  # Conditional logic
            'groups': [],  # User groups from lanes
            'webhooks': [],  # External integrations
            
            # Metadata
            'bpmn_source': {
                'process_id': bpmn_process['id'],
                'file_name': bpmn_process.get('file_name', 'unknown'),
                'lanes': len(bpmn_process.get('lanes', [])),
                'complexity': self._calculate_complexity(bpmn_process)
            }
        }
        
        # Transform lanes to groups
        if bpmn_process.get('lanes'):
            tallyfy_template['groups'] = self._transform_lanes(bpmn_process['lanes'])
        
        # Build flow graph for sequence analysis
        flow_graph = self._build_flow_graph(bpmn_process)
        
        # Find start events
        start_events = [e for e in bpmn_process.get('events', []) if e['position'] == 'start']
        
        # Transform elements in logical order
        if start_events:
            # Start from start events and follow flow
            transformed_elements = self._transform_from_start(
                bpmn_process, start_events, flow_graph
            )
        else:
            # No explicit start events, transform all elements
            transformed_elements = self._transform_all_elements(bpmn_process)
        
        # Add transformed elements to template
        tallyfy_template['steps'] = transformed_elements['steps']
        tallyfy_template['rules'] = transformed_elements['rules']
        tallyfy_template['webhooks'] = transformed_elements['webhooks']
        
        # Extract form fields from data objects
        if bpmn_process.get('data_objects'):
            tallyfy_template['field'] = self._transform_data_objects(bpmn_process['data_objects'])
        
        # Handle subprocesses
        if bpmn_process.get('subprocesses'):
            self._handle_subprocesses(bpmn_process['subprocesses'], tallyfy_template)
        
        # Optimize template structure
        tallyfy_template = self._optimize_template(tallyfy_template)
        
        # Update statistics
        self.stats['processes_transformed'] += 1
        self.stats['tasks_created'] += len(tallyfy_template['steps'])
        self.stats['rules_created'] += len(tallyfy_template['rules'])
        
        # Store ID mapping
        if self.id_mapper:
            self.id_mapper.map_id(bpmn_process['id'], template_id, 'template')
        
        logger.info(f"Successfully transformed process with {len(tallyfy_template['steps'])} steps")
        
        return tallyfy_template
    
    def _transform_from_start(self, process: Dict[str, Any], 
                            start_events: List[Dict[str, Any]], 
                            flow_graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """Transform elements following the flow from start events"""
        
        steps = []
        rules = []
        webhooks = []
        visited = set()
        position_counter = 0
        
        # Queue for BFS traversal
        queue = []
        
        # Add all start events to queue
        for start_event in start_events:
            queue.append((start_event['id'], position_counter))
        
        # Process queue
        while queue:
            element_id, position = queue.pop(0)
            
            if element_id in visited:
                continue
            
            visited.add(element_id)
            
            # Find element in process
            element = self._find_element(process, element_id)
            if not element:
                continue
            
            element_type = element.get('element_type')
            
            # Transform based on element type
            if element_type == 'task':
                step = self._transform_task(element, position)
                steps.append(step)
                position_counter += 1
                
            elif element_type == 'gateway':
                gateway_result = self._transform_gateway(element, position, flow_graph)
                if gateway_result.get('steps'):
                    steps.extend(gateway_result['steps'])
                if gateway_result.get('rules'):
                    rules.extend(gateway_result['rules'])
                position_counter += len(gateway_result.get('steps', []))
                
            elif element_type == 'event':
                event_result = self._transform_event(element, position)
                if event_result.get('step'):
                    steps.append(event_result['step'])
                    position_counter += 1
                if event_result.get('webhook'):
                    webhooks.append(event_result['webhook'])
            
            # Add outgoing elements to queue
            if element_id in flow_graph:
                for target_id in flow_graph[element_id]:
                    if target_id not in visited:
                        queue.append((target_id, position_counter))
        
        return {
            'steps': steps,
            'rules': rules,
            'webhooks': webhooks
        }
    
    def _transform_all_elements(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """Transform all elements when no clear flow is defined"""
        
        steps = []
        rules = []
        webhooks = []
        position_counter = 0
        
        # Transform all tasks
        for task in process.get('tasks', []):
            task['element_type'] = 'task'
            step = self._transform_task(task, position_counter)
            steps.append(step)
            position_counter += 1
        
        # Transform gateways
        flow_graph = self._build_flow_graph(process)
        for gateway in process.get('gateways', []):
            gateway['element_type'] = 'gateway'
            gateway_result = self._transform_gateway(gateway, position_counter, flow_graph)
            if gateway_result.get('steps'):
                steps.extend(gateway_result['steps'])
                position_counter += len(gateway_result['steps'])
            if gateway_result.get('rules'):
                rules.extend(gateway_result['rules'])
        
        # Transform relevant events
        for event in process.get('events', []):
            event['element_type'] = 'event'
            if event['position'] not in ['start', 'end'] or event['type'] != 'none':
                event_result = self._transform_event(event, position_counter)
                if event_result.get('step'):
                    steps.append(event_result['step'])
                    position_counter += 1
                if event_result.get('webhook'):
                    webhooks.append(event_result['webhook'])
        
        return {
            'steps': steps,
            'rules': rules,
            'webhooks': webhooks
        }
    
    def _transform_task(self, task: Dict[str, Any], position: int) -> Dict[str, Any]:
        """Transform a BPMN task to a Tallyfy step"""
        
        step_id = self._generate_tallyfy_id('stp', task['id'])
        
        # Determine task type mapping
        task_type_mapping = {
            'userTask': 'task',
            'serviceTask': 'webhook',
            'scriptTask': 'webhook',
            'businessRuleTask': 'task',
            'sendTask': 'email',
            'receiveTask': 'approval',
            'manualTask': 'task',
            'task': 'task',
            'callActivity': 'template_ref'
        }
        
        tallyfy_task_type = task_type_mapping.get(task['type'], 'task')
        
        step = {
            'id': step_id,
            'title': task.get('name', f"Task {position + 1}"),
            'description': task.get('documentation', ''),
            'task_type': tallyfy_task_type,
            'position': position,
            'is_required': True,
            'is_blocking': task['type'] == 'receiveTask',
            
            # Assignment
            'assignment_type': 'any',  # Will be updated based on lanes
            'assigned_to': None,
            
            # Timing
            'estimated_duration': 0,
            'deadline_config': None,
            
            # Dependencies
            'dependencies': [],
            
            # Task configuration
            'config': {},
            
            # BPMN reference
            'bpmn_ref': {
                'id': task['id'],
                'type': task['type']
            }
        }
        
        # Handle user task specifics
        if task['type'] == 'userTask':
            if task.get('assignee'):
                step['assignment_type'] = 'specific'
                step['assigned_to'] = task['assignee']
            elif task.get('candidate_groups'):
                step['assignment_type'] = 'group'
                step['assigned_to'] = task['candidate_groups']
            
            # Add form fields if present
            if task.get('form_fields'):
                step['field'] = self._transform_form_fields(task['form_fields'])
        
        # Handle service/script tasks
        elif task['type'] in ['serviceTask', 'scriptTask']:
            step['config']['webhook_url'] = task.get('implementation', '')
            step['config']['script'] = task.get('script', '')
        
        # Handle call activity
        elif task['type'] == 'callActivity':
            step['config']['called_template'] = task.get('called_element', '')
        
        # Handle boundary events
        if task.get('boundary_events'):
            for boundary_event in task['boundary_events']:
                if boundary_event['type'] == 'timer':
                    step['deadline_config'] = {
                        'duration': boundary_event.get('timer', {}).get('value', 'P1D'),
                        'escalate': True
                    }
        
        # Store ID mapping
        if self.id_mapper:
            self.id_mapper.map_id(task['id'], step_id, 'step')
        
        self.stats['tasks_created'] += 1
        
        return step
    
    def _transform_gateway(self, gateway: Dict[str, Any], position: int, 
                          flow_graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """Transform a BPMN gateway to Tallyfy rules and steps"""
        
        result = {'steps': [], 'rules': []}
        
        # Get AI assistance for complex gateways if available
        if self.ai_client:
            outgoing_flows = self._get_outgoing_flows(gateway['id'], flow_graph)
            strategy = self.ai_client.analyze_gateway_complexity(gateway, outgoing_flows)
        else:
            strategy = self._get_gateway_strategy(gateway)
        
        gateway_id = gateway['id']
        
        if gateway['type'] == 'exclusiveGateway':
            # XOR Gateway - Create conditional rules
            rules = self._create_xor_rules(gateway, flow_graph, position)
            result['rules'].extend(rules)
            
        elif gateway['type'] == 'parallelGateway':
            # AND Gateway - Create parallel steps
            if gateway['gateway_direction'] == 'Diverging':
                # Create parallel branches
                parallel_steps = self._create_parallel_steps(gateway, flow_graph, position)
                result['steps'].extend(parallel_steps)
            else:
                # Converging - Create sync point
                sync_step = self._create_sync_step(gateway, position)
                result['steps'].append(sync_step)
                
        elif gateway['type'] == 'inclusiveGateway':
            # OR Gateway - Multiple non-exclusive conditions
            rules = self._create_inclusive_rules(gateway, flow_graph, position)
            result['rules'].extend(rules)
            
        elif gateway['type'] == 'eventBasedGateway':
            # Event-based - Create waiting step with event handlers
            wait_step = self._create_event_wait_step(gateway, flow_graph, position)
            result['steps'].append(wait_step)
            
        elif gateway['type'] == 'complexGateway':
            # Complex - Requires manual configuration
            logger.warning(f"Complex gateway '{gateway.get('name', gateway_id)}' requires manual configuration")
            comment_step = {
                'id': self._generate_tallyfy_id('stp', gateway_id),
                'title': f"Complex Gateway: {gateway.get('name', 'Review Required')}",
                'description': "This complex gateway requires manual configuration in Tallyfy",
                'task_type': 'task',
                'position': position
            }
            result['steps'].append(comment_step)
        
        self.stats['gateways_transformed'] += 1
        
        return result
    
    def _transform_event(self, event: Dict[str, Any], position: int) -> Dict[str, Any]:
        """Transform a BPMN event to Tallyfy step or webhook"""
        
        result = {}
        
        # Get AI assistance for complex events if available
        if self.ai_client and event['type'] not in ['none', 'message', 'timer']:
            mapping = self.ai_client.map_complex_event(event)
        else:
            mapping = self._get_event_mapping(event)
        
        event_id = event['id']
        
        if event['position'] == 'start':
            if event['type'] == 'timer':
                # Timer start - Add to template configuration
                result['config'] = {
                    'scheduled_start': event.get('timer', {}).get('value')
                }
            elif event['type'] == 'message':
                # Message start - Create webhook trigger
                result['webhook'] = {
                    'id': self._generate_tallyfy_id('whk', event_id),
                    'name': f"Start trigger: {event.get('name', 'Message')}",
                    'type': 'incoming',
                    'trigger_template': True
                }
                
        elif event['position'] == 'intermediate_catch':
            # Intermediate catching event - Create waiting step
            step = {
                'id': self._generate_tallyfy_id('stp', event_id),
                'title': f"Wait for: {event.get('name', event['type'])}",
                'description': f"Waiting for {event['type']} event",
                'task_type': 'approval',
                'position': position,
                'is_blocking': True
            }
            
            if event['type'] == 'timer':
                step['deadline_config'] = {
                    'duration': event.get('timer', {}).get('value', 'P1D')
                }
            elif event['type'] == 'message':
                step['task_type'] = 'webhook'
                step['config'] = {'wait_for_webhook': True}
            
            result['step'] = step
            
        elif event['position'] == 'intermediate_throw':
            # Intermediate throwing event - Create action step
            if event['type'] == 'message':
                step = {
                    'id': self._generate_tallyfy_id('stp', event_id),
                    'title': f"Send: {event.get('name', 'Message')}",
                    'description': "Send message/notification",
                    'task_type': 'email',
                    'position': position
                }
                result['step'] = step
            elif event['type'] == 'signal':
                result['webhook'] = {
                    'id': self._generate_tallyfy_id('whk', event_id),
                    'name': f"Signal: {event.get('name', 'Signal')}",
                    'type': 'outgoing',
                    'trigger_on_step': position
                }
                
        elif event['position'] == 'end':
            # End events typically don't need transformation
            if event['type'] == 'error':
                # Error end - Mark template as failed
                result['config'] = {'mark_as_failed': True}
            elif event['type'] == 'terminate':
                # Terminate - Force complete all branches
                result['config'] = {'force_complete': True}
        
        self.stats['events_mapped'] += 1
        
        return result
    
    def _transform_lanes(self, lanes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform BPMN lanes to Tallyfy groups"""
        
        groups = []
        
        # Get AI assistance for optimization if available
        if self.ai_client and len(lanes) > 1:
            # For complex lane structures, get AI recommendations
            mapping = self.ai_client.optimize_lane_to_role_mapping(lanes, [])
            lane_mappings = mapping.get('mappings', [])
        else:
            lane_mappings = []
        
        for lane in lanes:
            group_id = self._generate_tallyfy_id('grp', lane['id'])
            
            # Find AI mapping if available
            ai_mapping = next((m for m in lane_mappings if m['lane_id'] == lane['id']), None)
            
            group = {
                'id': group_id,
                'name': ai_mapping['tallyfy_group'] if ai_mapping else lane.get('name', f"Group_{group_id[:8]}"),
                'description': f"Migrated from BPMN lane: {lane.get('name', lane['id'])}",
                'members': [],  # Will be populated during user migration
                'bpmn_lane_id': lane['id'],
                'flow_node_refs': lane.get('flow_node_refs', [])
            }
            
            groups.append(group)
            
            # Store ID mapping
            if self.id_mapper:
                self.id_mapper.map_id(lane['id'], group_id, 'group')
        
        return groups
    
    def _transform_data_objects(self, data_objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform BPMN data objects to Tallyfy form fields"""
        
        fields = []
        
        for data_obj in data_objects:
            field_id = self._generate_tallyfy_id('fld', data_obj['id'])
            
            field = {
                'id': field_id,
                'name': data_obj.get('name', f"Field_{field_id[:8]}"),
                'type': 'text',  # Default to text, can be refined based on item_subject_ref
                'required': False,
                'description': f"Data from BPMN: {data_obj.get('name', data_obj['id'])}",
                'bpmn_ref': data_obj['id']
            }
            
            fields.append(field)
            
            # Store ID mapping
            if self.id_mapper:
                self.id_mapper.map_id(data_obj['id'], field_id, 'field')
        
        return fields
    
    def _transform_form_fields(self, form_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform BPMN form fields (e.g., Camunda) to Tallyfy fields"""
        
        fields = []
        
        field_type_mapping = {
            'string': 'text',
            'long': 'textarea',
            'boolean': 'radio',
            'date': 'date',
            'enum': 'dropdown',
            'email': 'email'
        }
        
        for bpmn_field in form_fields:
            field = {
                'id': self._generate_tallyfy_id('fld', bpmn_field['id']),
                'name': bpmn_field.get('label', bpmn_field['id']),
                'type': field_type_mapping.get(bpmn_field.get('type', 'string'), 'text'),
                'required': bpmn_field.get('required', False),
                'default_value': bpmn_field.get('default_value')
            }
            
            # Handle enum values
            if bpmn_field.get('values'):
                field['options'] = [v['name'] for v in bpmn_field['values']]
            
            # Handle validation
            if bpmn_field.get('validation'):
                field['validation'] = bpmn_field['validation']
            
            fields.append(field)
        
        return fields
    
    def _handle_subprocesses(self, subprocesses: List[Dict[str, Any]], 
                           template: Dict[str, Any]) -> None:
        """Handle BPMN subprocesses"""
        
        for subprocess in subprocesses:
            if subprocess.get('triggered_by_event'):
                # Event subprocess - Create separate template
                logger.info(f"Event subprocess '{subprocess.get('name', subprocess['id'])}' should be created as separate template")
                # This would trigger creation of a linked template
            else:
                # Embedded subprocess - Inline the steps
                subprocess_result = self._transform_all_elements(subprocess)
                
                # Add subprocess steps to main template
                base_position = len(template['steps'])
                for step in subprocess_result['steps']:
                    step['position'] += base_position
                    step['group_name'] = subprocess.get('name', 'Subprocess')
                    template['steps'].append(step)
                
                template['rules'].extend(subprocess_result.get('rules', []))
                template['webhooks'].extend(subprocess_result.get('webhooks', []))
    
    # Helper methods
    
    def _build_flow_graph(self, process: Dict[str, Any]) -> Dict[str, List[str]]:
        """Build adjacency list from sequence flows"""
        
        graph = {}
        
        for flow in process.get('sequence_flows', []):
            source = flow['source_ref']
            target = flow['target_ref']
            
            if source not in graph:
                graph[source] = []
            
            graph[source].append(target)
        
        return graph
    
    def _find_element(self, process: Dict[str, Any], element_id: str) -> Optional[Dict[str, Any]]:
        """Find element by ID in process"""
        
        # Check tasks
        for task in process.get('tasks', []):
            if task['id'] == element_id:
                task['element_type'] = 'task'
                return task
        
        # Check gateways
        for gateway in process.get('gateways', []):
            if gateway['id'] == element_id:
                gateway['element_type'] = 'gateway'
                return gateway
        
        # Check events
        for event in process.get('events', []):
            if event['id'] == element_id:
                event['element_type'] = 'event'
                return event
        
        return None
    
    def _get_outgoing_flows(self, element_id: str, flow_graph: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Get outgoing sequence flows for an element"""
        
        # This would need access to the actual flow objects with conditions
        # For now, return basic structure
        return [{'target_ref': target} for target in flow_graph.get(element_id, [])]
    
    def _create_xor_rules(self, gateway: Dict[str, Any], flow_graph: Dict[str, List[str]], 
                         position: int) -> List[Dict[str, Any]]:
        """Create conditional rules for XOR gateway"""
        
        rules = []
        targets = flow_graph.get(gateway['id'], [])
        
        for i, target_id in enumerate(targets):
            rule = {
                'id': self._generate_tallyfy_id('rul', f"{gateway['id']}_{i}"),
                'name': f"Path {i+1} from {gateway.get('name', 'gateway')}",
                'condition': {
                    'type': 'field_value',
                    'field': 'decision_field',  # Would need to be mapped properly
                    'operator': 'equals',
                    'value': f"option_{i+1}"
                },
                'action': {
                    'type': 'show_step',
                    'step_id': target_id  # Will be mapped to Tallyfy step ID
                }
            }
            rules.append(rule)
        
        return rules
    
    def _create_parallel_steps(self, gateway: Dict[str, Any], flow_graph: Dict[str, List[str]], 
                              position: int) -> List[Dict[str, Any]]:
        """Create parallel steps for AND gateway divergence"""
        
        steps = []
        targets = flow_graph.get(gateway['id'], [])
        
        # All targets get the same position to run in parallel
        for target_id in targets:
            # This is a placeholder - actual implementation would follow the flow
            # to find the next actual tasks
            step = {
                'id': self._generate_tallyfy_id('stp', f"{gateway['id']}_{target_id}"),
                'title': f"Parallel branch to {target_id}",
                'description': "Parallel execution branch",
                'task_type': 'task',
                'position': position,
                'parallel': True
            }
            steps.append(step)
        
        return steps
    
    def _create_sync_step(self, gateway: Dict[str, Any], position: int) -> Dict[str, Any]:
        """Create synchronization step for converging parallel gateway"""
        
        return {
            'id': self._generate_tallyfy_id('stp', gateway['id']),
            'title': f"Sync: {gateway.get('name', 'Wait for parallel branches')}",
            'description': "Wait for all parallel branches to complete",
            'task_type': 'approval',
            'position': position,
            'is_blocking': True,
            'wait_for_all': True
        }
    
    def _create_inclusive_rules(self, gateway: Dict[str, Any], flow_graph: Dict[str, List[str]], 
                               position: int) -> List[Dict[str, Any]]:
        """Create non-exclusive rules for inclusive gateway"""
        
        rules = []
        targets = flow_graph.get(gateway['id'], [])
        
        for i, target_id in enumerate(targets):
            rule = {
                'id': self._generate_tallyfy_id('rul', f"{gateway['id']}_{i}"),
                'name': f"Inclusive path {i+1}",
                'condition': {
                    'type': 'field_value',
                    'field': f"include_path_{i+1}",
                    'operator': 'equals',
                    'value': 'yes'
                },
                'action': {
                    'type': 'show_step',
                    'step_id': target_id
                },
                'exclusive': False  # Multiple rules can be true
            }
            rules.append(rule)
        
        return rules
    
    def _create_event_wait_step(self, gateway: Dict[str, Any], flow_graph: Dict[str, List[str]], 
                               position: int) -> Dict[str, Any]:
        """Create waiting step for event-based gateway"""
        
        return {
            'id': self._generate_tallyfy_id('stp', gateway['id']),
            'title': f"Wait for event: {gateway.get('name', 'Event')}",
            'description': "Waiting for one of multiple events to occur",
            'task_type': 'approval',
            'position': position,
            'is_blocking': True,
            'config': {
                'event_based': True,
                'timeout': 'P7D'  # Default 7 day timeout
            }
        }
    
    def _get_gateway_strategy(self, gateway: Dict[str, Any]) -> Dict[str, Any]:
        """Get transformation strategy for gateway without AI"""
        
        strategies = {
            'exclusiveGateway': {'transformation': 'conditional_rules'},
            'parallelGateway': {'transformation': 'parallel_steps'},
            'inclusiveGateway': {'transformation': 'multiple_conditions'},
            'eventBasedGateway': {'transformation': 'approval_with_timeout'},
            'complexGateway': {'transformation': 'manual_review'}
        }
        
        return strategies.get(gateway['type'], {'transformation': 'manual_review'})
    
    def _get_event_mapping(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get event mapping without AI"""
        
        if event['type'] == 'none':
            return {'type': 'none', 'implementation': 'No action needed'}
        elif event['type'] == 'message':
            return {'type': 'webhook', 'implementation': 'Message via webhook'}
        elif event['type'] == 'timer':
            return {'type': 'deadline', 'implementation': 'Timer as deadline'}
        elif event['type'] == 'signal':
            return {'type': 'webhook', 'implementation': 'Signal via webhook'}
        else:
            return {'type': 'manual', 'implementation': 'Requires manual configuration'}
    
    def _calculate_complexity(self, process: Dict[str, Any]) -> str:
        """Calculate process complexity"""
        
        score = (
            len(process.get('tasks', [])) * 1 +
            len(process.get('gateways', [])) * 3 +
            len(process.get('events', [])) * 2 +
            len(process.get('subprocesses', [])) * 5
        )
        
        if score < 10:
            return 'simple'
        elif score < 30:
            return 'medium'
        else:
            return 'complex'
    
    def _optimize_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize template structure for better execution"""
        
        # Sort steps by position
        template['steps'].sort(key=lambda x: x['position'])
        
        # Renumber positions to be sequential
        for i, step in enumerate(template['steps']):
            step['position'] = i
        
        # Detect if template should be sequential or parallel
        has_parallel = any(step.get('parallel', False) for step in template['steps'])
        template['config']['sequential'] = not has_parallel
        
        # Remove empty lists
        if not template['rules']:
            del template['rules']
        if not template['webhooks']:
            del template['webhooks']
        if not template['field']:
            del template['field']
        if not template['groups']:
            del template['groups']
        
        return template
    
    def _generate_tallyfy_id(self, prefix: str, source_id: str) -> str:
        """Generate Tallyfy-compatible ID"""
        
        # Create hash from source ID
        hash_obj = hashlib.md5(source_id.encode())
        hash_str = hash_obj.hexdigest()
        
        # Format: prefix_hash[:24]
        return f"{prefix}_{hash_str[:24]}"
    
    def get_stats(self) -> Dict[str, int]:
        """Get transformation statistics"""
        return self.stats.copy()