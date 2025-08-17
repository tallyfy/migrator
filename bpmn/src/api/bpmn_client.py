"""
BPMN 2.0 XML Parser and Client
Handles reading and parsing BPMN diagram files
"""

import xml.etree.ElementTree as ET
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BPMNClient:
    """Client for parsing and extracting data from BPMN 2.0 XML files"""
    
    # BPMN 2.0 Namespaces
    NAMESPACES = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'dc': 'http://www.omg.org/spec/DD/20100524/DC',
        'di': 'http://www.omg.org/spec/DD/20100524/DI',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'camunda': 'http://camunda.org/schema/1.0/bpmn',
        'zeebe': 'http://camunda.org/schema/zeebe/1.0'
    }
    
    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize BPMN parser
        
        Args:
            file_path: Path to BPMN XML file (optional, can load later)
        """
        self.file_path = file_path
        self.tree = None
        self.root = None
        self.processes = []
        self.collaborations = []
        self.messages = []
        self.data_stores = []
        
        # Element caches for quick lookup
        self.elements_by_id = {}
        self.sequence_flows = []
        self.message_flows = []
        
        # Statistics
        self.stats = {
            'processes': 0,
            'pools': 0,
            'lanes': 0,
            'tasks': 0,
            'gateways': 0,
            'events': 0,
            'sequence_flows': 0,
            'message_flows': 0,
            'data_objects': 0
        }
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str) -> None:
        """
        Load and parse BPMN XML file
        
        Args:
            file_path: Path to BPMN XML file
        """
        logger.info(f"Loading BPMN file: {file_path}")
        
        try:
            self.file_path = file_path
            self.tree = ET.parse(file_path)
            self.root = self.tree.getroot()
            
            # Register namespaces for XPath queries
            for prefix, uri in self.NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
            # Parse the BPMN structure
            self._parse_bpmn()
            
            logger.info(f"Successfully loaded BPMN with {self.stats['processes']} process(es)")
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse BPMN XML: {e}")
            raise
        except FileNotFoundError as e:
            logger.error(f"BPMN file not found: {e}")
            raise
    
    def load_string(self, xml_string: str) -> None:
        """
        Load and parse BPMN from XML string
        
        Args:
            xml_string: BPMN XML content as string
        """
        try:
            self.root = ET.fromstring(xml_string)
            self.tree = ET.ElementTree(self.root)
            
            # Register namespaces
            for prefix, uri in self.NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
            # Parse the BPMN structure
            self._parse_bpmn()
            
            logger.info(f"Successfully parsed BPMN from string")
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse BPMN XML string: {e}")
            raise
    
    def _parse_bpmn(self) -> None:
        """Parse all BPMN elements from the loaded XML"""
        
        # Parse collaborations (pools and message flows)
        self._parse_collaborations()
        
        # Parse processes
        self._parse_processes()
        
        # Parse global elements
        self._parse_messages()
        self._parse_data_stores()
        
        # Build element index
        self._build_element_index()
        
        # Calculate statistics
        self._calculate_stats()
    
    def _parse_collaborations(self) -> None:
        """Parse collaboration elements (pools, lanes, message flows)"""
        
        for collab in self.root.findall('.//bpmn:collaboration', self.NAMESPACES):
            collaboration = {
                'id': collab.get('id'),
                'name': collab.get('name'),
                'participants': [],
                'message_flows': []
            }
            
            # Parse participants (pools)
            for participant in collab.findall('bpmn:participant', self.NAMESPACES):
                pool = {
                    'id': participant.get('id'),
                    'name': participant.get('name'),
                    'process_ref': participant.get('processRef'),
                    'lanes': []
                }
                collaboration['participants'].append(pool)
            
            # Parse message flows
            for msg_flow in collab.findall('bpmn:messageFlow', self.NAMESPACES):
                flow = {
                    'id': msg_flow.get('id'),
                    'name': msg_flow.get('name'),
                    'source_ref': msg_flow.get('sourceRef'),
                    'target_ref': msg_flow.get('targetRef')
                }
                collaboration['message_flows'].append(flow)
                self.message_flows.append(flow)
            
            self.collaborations.append(collaboration)
    
    def _parse_processes(self) -> None:
        """Parse process elements"""
        
        for process in self.root.findall('.//bpmn:process', self.NAMESPACES):
            process_data = {
                'id': process.get('id'),
                'name': process.get('name'),
                'is_executable': process.get('isExecutable', 'false').lower() == 'true',
                'lanes': [],
                'tasks': [],
                'gateways': [],
                'events': [],
                'sequence_flows': [],
                'data_objects': [],
                'subprocesses': []
            }
            
            # Parse lane sets
            for lane_set in process.findall('bpmn:laneSet', self.NAMESPACES):
                for lane in lane_set.findall('bpmn:lane', self.NAMESPACES):
                    lane_data = {
                        'id': lane.get('id'),
                        'name': lane.get('name'),
                        'flow_node_refs': [ref.text for ref in lane.findall('bpmn:flowNodeRef', self.NAMESPACES)]
                    }
                    process_data['lanes'].append(lane_data)
            
            # Parse tasks
            process_data['tasks'].extend(self._parse_tasks(process))
            
            # Parse gateways
            process_data['gateways'].extend(self._parse_gateways(process))
            
            # Parse events
            process_data['events'].extend(self._parse_events(process))
            
            # Parse sequence flows
            for seq_flow in process.findall('bpmn:sequenceFlow', self.NAMESPACES):
                flow = {
                    'id': seq_flow.get('id'),
                    'name': seq_flow.get('name'),
                    'source_ref': seq_flow.get('sourceRef'),
                    'target_ref': seq_flow.get('targetRef'),
                    'condition': self._parse_condition(seq_flow)
                }
                process_data['sequence_flows'].append(flow)
                self.sequence_flows.append(flow)
            
            # Parse data objects
            for data_obj in process.findall('bpmn:dataObject', self.NAMESPACES):
                data = {
                    'id': data_obj.get('id'),
                    'name': data_obj.get('name'),
                    'item_subject_ref': data_obj.get('itemSubjectRef')
                }
                process_data['data_objects'].append(data)
            
            # Parse subprocesses
            process_data['subprocesses'].extend(self._parse_subprocesses(process))
            
            self.processes.append(process_data)
    
    def _parse_tasks(self, parent_element) -> List[Dict[str, Any]]:
        """Parse all task types from a parent element"""
        
        tasks = []
        task_types = [
            'userTask', 'serviceTask', 'scriptTask', 'businessRuleTask',
            'sendTask', 'receiveTask', 'manualTask', 'task', 'callActivity'
        ]
        
        for task_type in task_types:
            for task in parent_element.findall(f'bpmn:{task_type}', self.NAMESPACES):
                task_data = {
                    'id': task.get('id'),
                    'name': task.get('name'),
                    'type': task_type,
                    'documentation': self._get_documentation(task),
                    'incoming': [ref.text for ref in task.findall('bpmn:incoming', self.NAMESPACES)],
                    'outgoing': [ref.text for ref in task.findall('bpmn:outgoing', self.NAMESPACES)],
                    'properties': self._parse_extension_elements(task),
                    'boundary_events': self._parse_boundary_events(task.get('id'), parent_element)
                }
                
                # Parse specific task attributes
                if task_type == 'userTask':
                    task_data['assignee'] = task.get('{http://camunda.org/schema/1.0/bpmn}assignee')
                    task_data['candidate_groups'] = task.get('{http://camunda.org/schema/1.0/bpmn}candidateGroups')
                    task_data['form_key'] = task.get('{http://camunda.org/schema/1.0/bpmn}formKey')
                    task_data['form_fields'] = self._parse_form_fields(task)
                
                elif task_type == 'serviceTask':
                    task_data['implementation'] = task.get('implementation')
                    task_data['operation_ref'] = task.get('operationRef')
                
                elif task_type == 'scriptTask':
                    task_data['script_format'] = task.get('scriptFormat')
                    script_elem = task.find('bpmn:script', self.NAMESPACES)
                    task_data['script'] = script_elem.text if script_elem is not None else None
                
                elif task_type == 'callActivity':
                    task_data['called_element'] = task.get('calledElement')
                
                tasks.append(task_data)
        
        return tasks
    
    def _parse_gateways(self, parent_element) -> List[Dict[str, Any]]:
        """Parse all gateway types from a parent element"""
        
        gateways = []
        gateway_types = [
            'exclusiveGateway', 'parallelGateway', 'inclusiveGateway',
            'eventBasedGateway', 'complexGateway'
        ]
        
        for gateway_type in gateway_types:
            for gateway in parent_element.findall(f'bpmn:{gateway_type}', self.NAMESPACES):
                gateway_data = {
                    'id': gateway.get('id'),
                    'name': gateway.get('name'),
                    'type': gateway_type,
                    'incoming': [ref.text for ref in gateway.findall('bpmn:incoming', self.NAMESPACES)],
                    'outgoing': [ref.text for ref in gateway.findall('bpmn:outgoing', self.NAMESPACES)],
                    'default': gateway.get('default'),
                    'gateway_direction': gateway.get('gatewayDirection', 'Diverging')
                }
                gateways.append(gateway_data)
        
        return gateways
    
    def _parse_events(self, parent_element) -> List[Dict[str, Any]]:
        """Parse all event types from a parent element"""
        
        events = []
        
        # Start events
        for event in parent_element.findall('bpmn:startEvent', self.NAMESPACES):
            events.append(self._parse_event(event, 'start'))
        
        # End events
        for event in parent_element.findall('bpmn:endEvent', self.NAMESPACES):
            events.append(self._parse_event(event, 'end'))
        
        # Intermediate events
        for event in parent_element.findall('bpmn:intermediateCatchEvent', self.NAMESPACES):
            events.append(self._parse_event(event, 'intermediate_catch'))
        
        for event in parent_element.findall('bpmn:intermediateThrowEvent', self.NAMESPACES):
            events.append(self._parse_event(event, 'intermediate_throw'))
        
        # Boundary events are parsed separately with their attached tasks
        
        return events
    
    def _parse_event(self, event_elem, event_position: str) -> Dict[str, Any]:
        """Parse a single event element"""
        
        event_data = {
            'id': event_elem.get('id'),
            'name': event_elem.get('name'),
            'position': event_position,
            'type': self._determine_event_type(event_elem),
            'incoming': [ref.text for ref in event_elem.findall('bpmn:incoming', self.NAMESPACES)],
            'outgoing': [ref.text for ref in event_elem.findall('bpmn:outgoing', self.NAMESPACES)],
            'properties': self._parse_extension_elements(event_elem)
        }
        
        # Parse event definitions
        if event_data['type'] == 'timer':
            timer_def = event_elem.find('bpmn:timerEventDefinition', self.NAMESPACES)
            if timer_def is not None:
                event_data['timer'] = self._parse_timer_definition(timer_def)
        
        elif event_data['type'] == 'message':
            msg_def = event_elem.find('bpmn:messageEventDefinition', self.NAMESPACES)
            if msg_def is not None:
                event_data['message_ref'] = msg_def.get('messageRef')
        
        elif event_data['type'] == 'signal':
            signal_def = event_elem.find('bpmn:signalEventDefinition', self.NAMESPACES)
            if signal_def is not None:
                event_data['signal_ref'] = signal_def.get('signalRef')
        
        elif event_data['type'] == 'error':
            error_def = event_elem.find('bpmn:errorEventDefinition', self.NAMESPACES)
            if error_def is not None:
                event_data['error_ref'] = error_def.get('errorRef')
        
        return event_data
    
    def _parse_boundary_events(self, task_id: str, parent_element) -> List[Dict[str, Any]]:
        """Parse boundary events attached to a task"""
        
        boundary_events = []
        
        for event in parent_element.findall('bpmn:boundaryEvent', self.NAMESPACES):
            if event.get('attachedToRef') == task_id:
                event_data = self._parse_event(event, 'boundary')
                event_data['attached_to'] = task_id
                event_data['cancel_activity'] = event.get('cancelActivity', 'true').lower() == 'true'
                boundary_events.append(event_data)
        
        return boundary_events
    
    def _parse_subprocesses(self, parent_element) -> List[Dict[str, Any]]:
        """Parse subprocess elements"""
        
        subprocesses = []
        
        for subprocess in parent_element.findall('bpmn:subProcess', self.NAMESPACES):
            subprocess_data = {
                'id': subprocess.get('id'),
                'name': subprocess.get('name'),
                'triggered_by_event': subprocess.get('triggeredByEvent', 'false').lower() == 'true',
                'tasks': self._parse_tasks(subprocess),
                'gateways': self._parse_gateways(subprocess),
                'events': self._parse_events(subprocess),
                'sequence_flows': []
            }
            
            # Parse sequence flows within subprocess
            for seq_flow in subprocess.findall('bpmn:sequenceFlow', self.NAMESPACES):
                flow = {
                    'id': seq_flow.get('id'),
                    'source_ref': seq_flow.get('sourceRef'),
                    'target_ref': seq_flow.get('targetRef'),
                    'condition': self._parse_condition(seq_flow)
                }
                subprocess_data['sequence_flows'].append(flow)
            
            subprocesses.append(subprocess_data)
        
        return subprocesses
    
    def _determine_event_type(self, event_elem) -> str:
        """Determine the type of event based on its definitions"""
        
        if event_elem.find('bpmn:timerEventDefinition', self.NAMESPACES) is not None:
            return 'timer'
        elif event_elem.find('bpmn:messageEventDefinition', self.NAMESPACES) is not None:
            return 'message'
        elif event_elem.find('bpmn:signalEventDefinition', self.NAMESPACES) is not None:
            return 'signal'
        elif event_elem.find('bpmn:errorEventDefinition', self.NAMESPACES) is not None:
            return 'error'
        elif event_elem.find('bpmn:escalationEventDefinition', self.NAMESPACES) is not None:
            return 'escalation'
        elif event_elem.find('bpmn:compensateEventDefinition', self.NAMESPACES) is not None:
            return 'compensate'
        elif event_elem.find('bpmn:conditionalEventDefinition', self.NAMESPACES) is not None:
            return 'conditional'
        elif event_elem.find('bpmn:linkEventDefinition', self.NAMESPACES) is not None:
            return 'link'
        elif event_elem.find('bpmn:terminateEventDefinition', self.NAMESPACES) is not None:
            return 'terminate'
        else:
            return 'none'
    
    def _parse_timer_definition(self, timer_def) -> Dict[str, Any]:
        """Parse timer event definition"""
        
        timer_data = {}
        
        time_date = timer_def.find('bpmn:timeDate', self.NAMESPACES)
        if time_date is not None:
            timer_data['type'] = 'date'
            timer_data['value'] = time_date.text
        
        time_duration = timer_def.find('bpmn:timeDuration', self.NAMESPACES)
        if time_duration is not None:
            timer_data['type'] = 'duration'
            timer_data['value'] = time_duration.text
        
        time_cycle = timer_def.find('bpmn:timeCycle', self.NAMESPACES)
        if time_cycle is not None:
            timer_data['type'] = 'cycle'
            timer_data['value'] = time_cycle.text
        
        return timer_data
    
    def _parse_condition(self, seq_flow_elem) -> Optional[str]:
        """Parse condition expression from sequence flow"""
        
        condition_elem = seq_flow_elem.find('bpmn:conditionExpression', self.NAMESPACES)
        if condition_elem is not None:
            return condition_elem.text
        return None
    
    def _parse_form_fields(self, task_elem) -> List[Dict[str, Any]]:
        """Parse form fields from user task (Camunda extension)"""
        
        form_fields = []
        
        ext_elem = task_elem.find('bpmn:extensionElements', self.NAMESPACES)
        if ext_elem is not None:
            form_data = ext_elem.find('camunda:formData', {'camunda': 'http://camunda.org/schema/1.0/bpmn'})
            if form_data is not None:
                for field in form_data.findall('camunda:formField', {'camunda': 'http://camunda.org/schema/1.0/bpmn'}):
                    field_data = {
                        'id': field.get('id'),
                        'label': field.get('label'),
                        'type': field.get('type'),
                        'default_value': field.get('defaultValue'),
                        'required': field.get('required', 'false').lower() == 'true'
                    }
                    
                    # Parse validation
                    validation = field.find('camunda:validation', {'camunda': 'http://camunda.org/schema/1.0/bpmn'})
                    if validation is not None:
                        constraints = []
                        for constraint in validation.findall('camunda:constraint', {'camunda': 'http://camunda.org/schema/1.0/bpmn'}):
                            constraints.append({
                                'name': constraint.get('name'),
                                'config': constraint.get('config')
                            })
                        field_data['validation'] = constraints
                    
                    # Parse enum values
                    values = []
                    for value in field.findall('camunda:value', {'camunda': 'http://camunda.org/schema/1.0/bpmn'}):
                        values.append({
                            'id': value.get('id'),
                            'name': value.get('name')
                        })
                    if values:
                        field_data['values'] = values
                    
                    form_fields.append(field_data)
        
        return form_fields
    
    def _parse_extension_elements(self, element) -> Dict[str, Any]:
        """Parse extension elements for custom properties"""
        
        properties = {}
        
        ext_elem = element.find('bpmn:extensionElements', self.NAMESPACES)
        if ext_elem is not None:
            # Parse Camunda properties
            props_elem = ext_elem.find('camunda:properties', {'camunda': 'http://camunda.org/schema/1.0/bpmn'})
            if props_elem is not None:
                for prop in props_elem.findall('camunda:property', {'camunda': 'http://camunda.org/schema/1.0/bpmn'}):
                    properties[prop.get('name')] = prop.get('value')
        
        return properties
    
    def _get_documentation(self, element) -> Optional[str]:
        """Extract documentation from an element"""
        
        doc_elem = element.find('bpmn:documentation', self.NAMESPACES)
        if doc_elem is not None:
            return doc_elem.text
        return None
    
    def _parse_messages(self) -> None:
        """Parse message definitions"""
        
        for message in self.root.findall('.//bpmn:message', self.NAMESPACES):
            msg_data = {
                'id': message.get('id'),
                'name': message.get('name'),
                'item_ref': message.get('itemRef')
            }
            self.messages.append(msg_data)
    
    def _parse_data_stores(self) -> None:
        """Parse data store definitions"""
        
        for data_store in self.root.findall('.//bpmn:dataStore', self.NAMESPACES):
            store_data = {
                'id': data_store.get('id'),
                'name': data_store.get('name'),
                'capacity': data_store.get('capacity'),
                'is_unlimited': data_store.get('isUnlimited', 'false').lower() == 'true'
            }
            self.data_stores.append(store_data)
    
    def _build_element_index(self) -> None:
        """Build index of all elements by ID for quick lookup"""
        
        self.elements_by_id = {}
        
        # Index all elements from processes
        for process in self.processes:
            self.elements_by_id[process['id']] = {'type': 'process', 'data': process}
            
            for task in process['tasks']:
                self.elements_by_id[task['id']] = {'type': 'task', 'data': task}
            
            for gateway in process['gateways']:
                self.elements_by_id[gateway['id']] = {'type': 'gateway', 'data': gateway}
            
            for event in process['events']:
                self.elements_by_id[event['id']] = {'type': 'event', 'data': event}
            
            for lane in process['lanes']:
                self.elements_by_id[lane['id']] = {'type': 'lane', 'data': lane}
    
    def _calculate_stats(self) -> None:
        """Calculate statistics about the BPMN diagram"""
        
        self.stats['processes'] = len(self.processes)
        self.stats['sequence_flows'] = len(self.sequence_flows)
        self.stats['message_flows'] = len(self.message_flows)
        
        for process in self.processes:
            self.stats['lanes'] += len(process['lanes'])
            self.stats['tasks'] += len(process['tasks'])
            self.stats['gateways'] += len(process['gateways'])
            self.stats['events'] += len(process['events'])
            self.stats['data_objects'] += len(process['data_objects'])
        
        for collab in self.collaborations:
            self.stats['pools'] += len(collab['participants'])
    
    def get_element_by_id(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element by its ID"""
        return self.elements_by_id.get(element_id)
    
    def get_process_flow(self, process_id: str) -> List[Dict[str, Any]]:
        """Get the execution flow for a process"""
        
        process = None
        for p in self.processes:
            if p['id'] == process_id:
                process = p
                break
        
        if not process:
            return []
        
        # Build flow graph
        flow_graph = {}
        for seq_flow in process['sequence_flows']:
            source = seq_flow['source_ref']
            if source not in flow_graph:
                flow_graph[source] = []
            flow_graph[source].append(seq_flow)
        
        # Find start events
        start_events = [e for e in process['events'] if e['position'] == 'start']
        
        # Build execution flow
        flow = []
        visited = set()
        
        def traverse(element_id):
            if element_id in visited:
                return
            visited.add(element_id)
            
            element = self.get_element_by_id(element_id)
            if element:
                flow.append(element['data'])
                
                # Follow outgoing flows
                if element_id in flow_graph:
                    for seq_flow in flow_graph[element_id]:
                        traverse(seq_flow['target_ref'])
        
        # Start traversal from start events
        for start_event in start_events:
            traverse(start_event['id'])
        
        return flow
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the BPMN diagram structure
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for at least one process
        if not self.processes:
            issues.append("No processes found in BPMN diagram")
        
        for process in self.processes:
            # Check for start events
            start_events = [e for e in process['events'] if e['position'] == 'start']
            if not start_events:
                issues.append(f"Process '{process['name'] or process['id']}' has no start event")
            
            # Check for end events
            end_events = [e for e in process['events'] if e['position'] == 'end']
            if not end_events:
                issues.append(f"Process '{process['name'] or process['id']}' has no end event")
            
            # Check for unreachable elements
            reachable = set()
            for seq_flow in process['sequence_flows']:
                reachable.add(seq_flow['target_ref'])
            
            for task in process['tasks']:
                if task['id'] not in reachable and not task['incoming']:
                    # Check if it's a start task
                    has_start_event_flow = False
                    for event in start_events:
                        if task['id'] in [f['target_ref'] for f in process['sequence_flows'] if f['source_ref'] == event['id']]:
                            has_start_event_flow = True
                            break
                    
                    if not has_start_event_flow:
                        issues.append(f"Task '{task['name'] or task['id']}' is unreachable")
            
            # Check for unconnected gateways
            for gateway in process['gateways']:
                if not gateway['incoming']:
                    issues.append(f"Gateway '{gateway['name'] or gateway['id']}' has no incoming flows")
                if not gateway['outgoing']:
                    issues.append(f"Gateway '{gateway['name'] or gateway['id']}' has no outgoing flows")
                
                # Check gateway specific rules
                if gateway['type'] == 'exclusiveGateway' and gateway['gateway_direction'] == 'Diverging':
                    if len(gateway['outgoing']) < 2:
                        issues.append(f"Exclusive gateway '{gateway['name'] or gateway['id']}' should have at least 2 outgoing flows")
                
                elif gateway['type'] == 'parallelGateway' and gateway['gateway_direction'] == 'Diverging':
                    if len(gateway['outgoing']) < 2:
                        issues.append(f"Parallel gateway '{gateway['name'] or gateway['id']}' should have at least 2 outgoing flows")
        
        return len(issues) == 0, issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Export parsed BPMN data as dictionary"""
        
        return {
            'file_path': self.file_path,
            'processes': self.processes,
            'collaborations': self.collaborations,
            'messages': self.messages,
            'data_stores': self.data_stores,
            'statistics': self.stats
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export parsed BPMN data as JSON string"""
        
        return json.dumps(self.to_dict(), indent=indent, default=str)