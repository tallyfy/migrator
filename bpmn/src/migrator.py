#!/usr/bin/env python3
"""
BPMN to Tallyfy Migrator - Self-Contained Version
All mapping rules and transformation logic embedded directly
No external AI required - deterministic rule-based migration
"""

import os
import sys
import json
import logging
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our rule engine
from rule_engine import BPMNToTallyfyRuleEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BPMNToTallyfyMigrator:
    """
    Complete BPMN to Tallyfy migrator with embedded rules
    No external dependencies - all logic self-contained
    """
    
    def __init__(self):
        """Initialize migrator with rule engine"""
        self.rule_engine = BPMNToTallyfyRuleEngine()
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI',
            'camunda': 'http://camunda.org/schema/1.0/bpmn',
            'signavio': 'http://www.signavio.com'
        }
        
        self.results = {
            'source_file': None,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {},
            'processes': [],
            'tallyfy_templates': [],
            'migration_report': {},
            'warnings': [],
            'errors': []
        }
    
    def migrate_file(self, bpmn_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Main migration method
        
        Args:
            bpmn_file: Path to BPMN 2.0 XML file
            output_file: Optional output JSON file path
            
        Returns:
            Complete migration results
        """
        logger.info(f"Starting migration of {bpmn_file}")
        self.results['source_file'] = bpmn_file
        
        try:
            # Parse BPMN file
            tree = ET.parse(bpmn_file)
            root = tree.getroot()
            
            # Extract and analyze all processes
            processes = self._extract_processes(root)
            self.results['processes'] = processes
            
            # Generate summary statistics
            self.results['summary'] = self._generate_summary(processes)
            
            # Migrate each process to Tallyfy template
            for process in processes:
                template = self._migrate_process(process)
                self.results['tallyfy_templates'].append(template)
            
            # Generate migration report
            self.results['migration_report'] = self._generate_report()
            
            # Save output if requested
            if output_file:
                self._save_output(output_file)
            
            return self.results
            
        except ET.ParseError as e:
            error_msg = f"Failed to parse BPMN file: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return self.results
            
        except Exception as e:
            error_msg = f"Migration failed: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)
            return self.results
    
    def _extract_processes(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract all processes from BPMN XML"""
        processes = []
        
        # Find all process elements
        for process_elem in root.findall('.//bpmn:process', self.namespaces):
            process = {
                'id': process_elem.get('id'),
                'name': process_elem.get('name', 'Unnamed Process'),
                'isExecutable': process_elem.get('isExecutable', 'true'),
                'elements': {
                    'tasks': [],
                    'gateways': [],
                    'events': [],
                    'flows': [],
                    'dataObjects': [],
                    'lanes': [],
                    'subprocesses': []
                },
                'statistics': {}
            }
            
            # Extract all elements
            self._extract_tasks(process_elem, process)
            self._extract_gateways(process_elem, process)
            self._extract_events(process_elem, process)
            self._extract_flows(process_elem, process)
            self._extract_data_objects(process_elem, process)
            self._extract_lanes(root, process)
            self._extract_subprocesses(process_elem, process)
            
            # Calculate statistics
            process['statistics'] = self._calculate_process_stats(process)
            
            processes.append(process)
        
        # Handle collaboration if present
        for collaboration in root.findall('.//bpmn:collaboration', self.namespaces):
            self._extract_collaboration(collaboration, processes)
        
        return processes
    
    def _extract_tasks(self, process_elem: ET.Element, process: Dict[str, Any]):
        """Extract all task types from process"""
        task_types = [
            'task', 'userTask', 'manualTask', 'serviceTask', 
            'scriptTask', 'businessRuleTask', 'sendTask', 
            'receiveTask', 'callActivity'
        ]
        
        for task_type in task_types:
            for task in process_elem.findall(f'.//bpmn:{task_type}', self.namespaces):
                task_data = {
                    'type': task_type,
                    'id': task.get('id'),
                    'name': task.get('name', f'Unnamed {task_type}'),
                    'documentation': self._extract_documentation(task),
                    'incoming': [],
                    'outgoing': [],
                    'properties': {},
                    'forms': []
                }
                
                # Extract flow references
                for incoming in task.findall('.//bpmn:incoming', self.namespaces):
                    if incoming.text:
                        task_data['incoming'].append(incoming.text)
                
                for outgoing in task.findall('.//bpmn:outgoing', self.namespaces):
                    if outgoing.text:
                        task_data['outgoing'].append(outgoing.text)
                
                # Extract loop characteristics
                if task.find('.//bpmn:multiInstanceLoopCharacteristics', self.namespaces) is not None:
                    task_data['properties']['multiInstance'] = True
                    
                if task.find('.//bpmn:standardLoopCharacteristics', self.namespaces) is not None:
                    task_data['properties']['loop'] = True
                
                # Extract forms if present
                self._extract_forms(task, task_data)
                
                # Extract Camunda/vendor extensions
                self._extract_vendor_extensions(task, task_data)
                
                process['elements']['tasks'].append(task_data)
    
    def _extract_gateways(self, process_elem: ET.Element, process: Dict[str, Any]):
        """Extract all gateway types"""
        gateway_types = [
            'exclusiveGateway', 'parallelGateway', 'inclusiveGateway',
            'eventBasedGateway', 'complexGateway'
        ]
        
        for gateway_type in gateway_types:
            for gateway in process_elem.findall(f'.//bpmn:{gateway_type}', self.namespaces):
                gateway_data = {
                    'type': gateway_type,
                    'id': gateway.get('id'),
                    'name': gateway.get('name', f'{gateway_type}'),
                    'incoming': [],
                    'outgoing': [],
                    'default': gateway.get('default')
                }
                
                # Extract flow references
                for incoming in gateway.findall('.//bpmn:incoming', self.namespaces):
                    if incoming.text:
                        gateway_data['incoming'].append(incoming.text)
                
                for outgoing in gateway.findall('.//bpmn:outgoing', self.namespaces):
                    if outgoing.text:
                        gateway_data['outgoing'].append(outgoing.text)
                
                process['elements']['gateways'].append(gateway_data)
    
    def _extract_events(self, process_elem: ET.Element, process: Dict[str, Any]):
        """Extract all event types"""
        event_categories = [
            ('startEvent', 'start'),
            ('endEvent', 'end'),
            ('intermediateCatchEvent', 'intermediate_catch'),
            ('intermediateThrowEvent', 'intermediate_throw'),
            ('boundaryEvent', 'boundary')
        ]
        
        for event_type, category in event_categories:
            for event in process_elem.findall(f'.//bpmn:{event_type}', self.namespaces):
                event_data = {
                    'type': event_type,
                    'category': category,
                    'id': event.get('id'),
                    'name': event.get('name', event_type),
                    'eventType': self._determine_event_type(event),
                    'incoming': [],
                    'outgoing': [],
                    'attachedTo': event.get('attachedToRef'),
                    'cancelActivity': event.get('cancelActivity', 'true')
                }
                
                # Extract flow references
                for incoming in event.findall('.//bpmn:incoming', self.namespaces):
                    if incoming.text:
                        event_data['incoming'].append(incoming.text)
                
                for outgoing in event.findall('.//bpmn:outgoing', self.namespaces):
                    if outgoing.text:
                        event_data['outgoing'].append(outgoing.text)
                
                process['elements']['events'].append(event_data)
    
    def _extract_flows(self, process_elem: ET.Element, process: Dict[str, Any]):
        """Extract sequence flows"""
        for flow in process_elem.findall('.//bpmn:sequenceFlow', self.namespaces):
            flow_data = {
                'type': 'sequenceFlow',
                'id': flow.get('id'),
                'name': flow.get('name', ''),
                'sourceRef': flow.get('sourceRef'),
                'targetRef': flow.get('targetRef'),
                'condition': None
            }
            
            # Extract condition expression
            condition = flow.find('.//bpmn:conditionExpression', self.namespaces)
            if condition is not None:
                flow_data['condition'] = condition.text
            
            process['elements']['flows'].append(flow_data)
    
    def _extract_data_objects(self, process_elem: ET.Element, process: Dict[str, Any]):
        """Extract data objects and references"""
        for data_obj in process_elem.findall('.//bpmn:dataObject', self.namespaces):
            data = {
                'type': 'dataObject',
                'id': data_obj.get('id'),
                'name': data_obj.get('name', 'Data Object'),
                'isCollection': data_obj.get('isCollection', 'false')
            }
            process['elements']['dataObjects'].append(data)
        
        for data_ref in process_elem.findall('.//bpmn:dataObjectReference', self.namespaces):
            data = {
                'type': 'dataObjectReference',
                'id': data_ref.get('id'),
                'name': data_ref.get('name', 'Data Reference'),
                'dataObjectRef': data_ref.get('dataObjectRef')
            }
            process['elements']['dataObjects'].append(data)
    
    def _extract_lanes(self, root: ET.Element, process: Dict[str, Any]):
        """Extract lanes and pools"""
        # Find lanes within this process
        for lane_set in root.findall('.//bpmn:laneSet', self.namespaces):
            for lane in lane_set.findall('.//bpmn:lane', self.namespaces):
                lane_data = {
                    'type': 'lane',
                    'id': lane.get('id'),
                    'name': lane.get('name', 'Lane'),
                    'flowNodeRefs': []
                }
                
                # Get flow node references
                for flow_ref in lane.findall('.//bpmn:flowNodeRef', self.namespaces):
                    if flow_ref.text:
                        lane_data['flowNodeRefs'].append(flow_ref.text)
                
                process['elements']['lanes'].append(lane_data)
    
    def _extract_subprocesses(self, process_elem: ET.Element, process: Dict[str, Any]):
        """Extract embedded subprocesses"""
        for subprocess in process_elem.findall('.//bpmn:subProcess', self.namespaces):
            subprocess_data = {
                'type': 'subProcess',
                'id': subprocess.get('id'),
                'name': subprocess.get('name', 'Subprocess'),
                'triggeredByEvent': subprocess.get('triggeredByEvent', 'false'),
                'elements': {
                    'tasks': [],
                    'gateways': [],
                    'events': []
                }
            }
            
            # Recursively extract subprocess elements
            self._extract_tasks(subprocess, subprocess_data)
            self._extract_gateways(subprocess, subprocess_data)
            self._extract_events(subprocess, subprocess_data)
            
            process['elements']['subprocesses'].append(subprocess_data)
    
    def _extract_collaboration(self, collaboration: ET.Element, processes: List[Dict[str, Any]]):
        """Extract collaboration elements"""
        # Extract participants (pools)
        for participant in collaboration.findall('.//bpmn:participant', self.namespaces):
            pool_data = {
                'type': 'pool',
                'id': participant.get('id'),
                'name': participant.get('name', 'Pool'),
                'processRef': participant.get('processRef')
            }
            
            # Find the corresponding process and add pool info
            for process in processes:
                if process['id'] == pool_data['processRef']:
                    process['pool'] = pool_data
                    break
        
        # Extract message flows
        for msg_flow in collaboration.findall('.//bpmn:messageFlow', self.namespaces):
            flow_data = {
                'type': 'messageFlow',
                'id': msg_flow.get('id'),
                'name': msg_flow.get('name', ''),
                'sourceRef': msg_flow.get('sourceRef'),
                'targetRef': msg_flow.get('targetRef')
            }
            # Add to appropriate process
            if processes:
                processes[0].setdefault('messageFlows', []).append(flow_data)
    
    def _extract_forms(self, element: ET.Element, element_data: Dict[str, Any]):
        """Extract form fields from task"""
        # Check for Camunda forms
        for form_field in element.findall('.//camunda:formField', self.namespaces):
            field = {
                'id': form_field.get('id'),
                'label': form_field.get('label'),
                'type': form_field.get('type', 'string'),
                'defaultValue': form_field.get('defaultValue'),
                'required': form_field.get('required', 'false')
            }
            
            # Extract validation
            for validation in form_field.findall('.//camunda:validation', self.namespaces):
                for constraint in validation.findall('.//camunda:constraint', self.namespaces):
                    field.setdefault('validation', {})[constraint.get('name')] = constraint.get('config')
            
            # Extract options for enums
            for value in form_field.findall('.//camunda:value', self.namespaces):
                field.setdefault('options', []).append({
                    'id': value.get('id'),
                    'name': value.get('name')
                })
            
            element_data['forms'].append(field)
    
    def _extract_vendor_extensions(self, element: ET.Element, element_data: Dict[str, Any]):
        """Extract vendor-specific extensions"""
        # Camunda properties
        for prop in element.findall('.//camunda:property', self.namespaces):
            element_data['properties'][prop.get('name')] = prop.get('value')
        
        # Camunda input/output parameters
        for input_param in element.findall('.//camunda:inputParameter', self.namespaces):
            element_data.setdefault('inputs', {})[input_param.get('name')] = input_param.text
        
        for output_param in element.findall('.//camunda:outputParameter', self.namespaces):
            element_data.setdefault('outputs', {})[output_param.get('name')] = output_param.text
    
    def _extract_documentation(self, element: ET.Element) -> Optional[str]:
        """Extract documentation from element"""
        doc = element.find('.//bpmn:documentation', self.namespaces)
        return doc.text if doc is not None else None
    
    def _determine_event_type(self, event: ET.Element) -> str:
        """Determine the specific event type"""
        event_definitions = [
            ('messageEventDefinition', 'message'),
            ('timerEventDefinition', 'timer'),
            ('errorEventDefinition', 'error'),
            ('signalEventDefinition', 'signal'),
            ('compensateEventDefinition', 'compensation'),
            ('conditionalEventDefinition', 'conditional'),
            ('linkEventDefinition', 'link'),
            ('escalationEventDefinition', 'escalation'),
            ('terminateEventDefinition', 'terminate'),
            ('cancelEventDefinition', 'cancel')
        ]
        
        for def_name, event_type in event_definitions:
            if event.find(f'.//bpmn:{def_name}', self.namespaces) is not None:
                return event_type
        
        return 'none'
    
    def _calculate_process_stats(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate process statistics"""
        stats = {
            'total_elements': 0,
            'tasks': len(process['elements']['tasks']),
            'gateways': len(process['elements']['gateways']),
            'events': len(process['elements']['events']),
            'flows': len(process['elements']['flows']),
            'data_objects': len(process['elements']['dataObjects']),
            'lanes': len(process['elements']['lanes']),
            'subprocesses': len(process['elements']['subprocesses']),
            'complexity_score': 0
        }
        
        stats['total_elements'] = sum([
            stats['tasks'], stats['gateways'], stats['events'],
            stats['flows'], stats['data_objects'], stats['lanes'],
            stats['subprocesses']
        ])
        
        # Calculate complexity score
        stats['complexity_score'] = (
            stats['tasks'] * 1 +
            stats['gateways'] * 3 +
            stats['events'] * 2 +
            stats['subprocesses'] * 5 +
            len([t for t in process['elements']['tasks'] if t['properties'].get('multiInstance')]) * 4 +
            len([t for t in process['elements']['tasks'] if t['properties'].get('loop')]) * 5
        )
        
        return stats
    
    def _generate_summary(self, processes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall summary statistics"""
        summary = {
            'total_processes': len(processes),
            'total_elements': 0,
            'total_tasks': 0,
            'total_gateways': 0,
            'total_events': 0,
            'complexity': 'Simple',
            'estimated_migration_time': '1-2 hours'
        }
        
        for process in processes:
            stats = process['statistics']
            summary['total_elements'] += stats['total_elements']
            summary['total_tasks'] += stats['tasks']
            summary['total_gateways'] += stats['gateways']
            summary['total_events'] += stats['events']
        
        # Determine overall complexity
        total_complexity = sum(p['statistics']['complexity_score'] for p in processes)
        
        if total_complexity < 20:
            summary['complexity'] = 'Simple'
            summary['estimated_migration_time'] = '1-2 hours'
        elif total_complexity < 50:
            summary['complexity'] = 'Moderate'
            summary['estimated_migration_time'] = '2-4 hours'
        elif total_complexity < 100:
            summary['complexity'] = 'Complex'
            summary['estimated_migration_time'] = '4-8 hours'
        else:
            summary['complexity'] = 'Very Complex'
            summary['estimated_migration_time'] = '8+ hours'
        
        return summary
    
    def _migrate_process(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a BPMN process to Tallyfy template"""
        template = {
            'title': process['name'],
            'description': f"Migrated from BPMN process: {process['id']}",
            'steps': [],
            'rules': [],
            'captures': [],
            'groups': [],
            'metadata': {
                'bpmn_process_id': process['id'],
                'migration_timestamp': datetime.now(timezone.utc).isoformat(),
                'migration_version': '1.0'
            },
            'migration_details': {
                'successful': [],
                'partial': [],
                'failed': []
            }
        }
        
        # Create lane-to-group mapping
        lane_mapping = {}
        for lane in process['elements']['lanes']:
            group = {
                'name': lane['name'],
                'bpmn_lane_id': lane['id'],
                'members': []  # To be populated manually
            }
            template['groups'].append(group)
            lane_mapping[lane['id']] = group['name']
        
        # Process tasks
        step_position = 0
        element_to_step = {}
        
        for task in process['elements']['tasks']:
            migration_result = self._migrate_task(task, lane_mapping, step_position)
            
            if migration_result['status'] == 'success':
                template['steps'].append(migration_result['step'])
                element_to_step[task['id']] = migration_result['step']
                template['migration_details']['successful'].append({
                    'bpmn_element': task['id'],
                    'tallyfy_step': migration_result['step']['title']
                })
                step_position += 1
            elif migration_result['status'] == 'partial':
                template['steps'].append(migration_result['step'])
                element_to_step[task['id']] = migration_result['step']
                template['migration_details']['partial'].append({
                    'bpmn_element': task['id'],
                    'tallyfy_step': migration_result['step']['title'],
                    'warnings': migration_result['warnings']
                })
                step_position += 1
            else:
                template['migration_details']['failed'].append({
                    'bpmn_element': task['id'],
                    'reason': migration_result['reason']
                })
        
        # Process gateways
        for gateway in process['elements']['gateways']:
            gateway_result = self._migrate_gateway(gateway, element_to_step)
            
            if gateway_result['status'] == 'success':
                template['rules'].extend(gateway_result['rules'])
                template['migration_details']['successful'].append({
                    'bpmn_element': gateway['id'],
                    'tallyfy_rules': len(gateway_result['rules'])
                })
            elif gateway_result['status'] == 'partial':
                template['rules'].extend(gateway_result['rules'])
                template['migration_details']['partial'].append({
                    'bpmn_element': gateway['id'],
                    'warnings': gateway_result['warnings']
                })
            else:
                template['migration_details']['failed'].append({
                    'bpmn_element': gateway['id'],
                    'reason': gateway_result['reason']
                })
        
        # Process events
        for event in process['elements']['events']:
            event_result = self._migrate_event(event, element_to_step, step_position)
            
            if event_result['status'] == 'success' and event_result.get('step'):
                template['steps'].append(event_result['step'])
                template['migration_details']['successful'].append({
                    'bpmn_element': event['id'],
                    'tallyfy_element': event_result.get('type', 'event')
                })
                step_position += 1
            elif event_result['status'] == 'partial':
                if event_result.get('step'):
                    template['steps'].append(event_result['step'])
                    step_position += 1
                template['migration_details']['partial'].append({
                    'bpmn_element': event['id'],
                    'warnings': event_result['warnings']
                })
            else:
                template['migration_details']['failed'].append({
                    'bpmn_element': event['id'],
                    'reason': event_result.get('reason', 'Event type not supported')
                })
        
        # Process forms
        for task in process['elements']['tasks']:
            if task['forms']:
                captures = self._migrate_forms(task['forms'])
                template['captures'].extend(captures)
        
        return template
    
    def _migrate_task(self, task: Dict[str, Any], lane_mapping: Dict[str, str], position: int) -> Dict[str, Any]:
        """Migrate a BPMN task to Tallyfy step"""
        # Use rule engine to get migration decision
        decision = self.rule_engine.analyze_element(task)
        
        if decision['strategy'] == 'unsupported':
            return {
                'status': 'failed',
                'reason': decision['reasoning']
            }
        
        # Build Tallyfy step
        step = {
            'position': position,
            'title': task['name'],
            'description': task.get('documentation', ''),
            'task_type': decision['tallyfy_mapping'].get('task_type', 'task'),
            'bpmn_task_id': task['id'],
            'bpmn_task_type': task['type']
        }
        
        # Add webhook if service task
        if task['type'] == 'serviceTask':
            step['webhook'] = {
                'url': '{{CONFIGURE_WEBHOOK_URL}}',
                'method': 'POST',
                'headers': {},
                'body': {}
            }
        
        # Add deadline if specified
        if task.get('properties', {}).get('dueDate'):
            step['deadline'] = {
                'unit': 'day',
                'value': 1,
                'note': 'Configure based on BPMN due date'
            }
        
        # Determine assignment based on lane
        for lane_id, group_name in lane_mapping.items():
            lane = next((l for l in task.get('lanes', []) if l['id'] == lane_id), None)
            if lane and task['id'] in lane.get('flowNodeRefs', []):
                step['assignee'] = {
                    'type': 'group',
                    'group': group_name
                }
                break
        
        result = {
            'status': 'partial' if decision['warnings'] else 'success',
            'step': step,
            'warnings': decision['warnings']
        }
        
        return result
    
    def _migrate_gateway(self, gateway: Dict[str, Any], element_to_step: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a BPMN gateway to Tallyfy rules"""
        # Use rule engine for gateway analysis
        context = {
            'incoming': len(gateway['incoming']),
            'outgoing': len(gateway['outgoing'])
        }
        decision = self.rule_engine.analyze_element(gateway, context)
        
        if decision['strategy'] == 'unsupported':
            return {
                'status': 'failed',
                'reason': decision['reasoning']
            }
        
        rules = []
        
        if gateway['type'] == 'exclusiveGateway' and len(gateway['outgoing']) > 1:
            # Create IF-THEN rules for each outgoing path
            for i, flow_id in enumerate(gateway['outgoing']):
                rule = {
                    'type': 'conditional',
                    'condition': {
                        'field': f'gateway_{gateway["id"]}_decision',
                        'operator': 'equals',
                        'value': f'path_{i+1}'
                    },
                    'action': {
                        'type': 'show',
                        'target': f'branch_{i+1}_steps'
                    },
                    'bpmn_gateway_id': gateway['id']
                }
                rules.append(rule)
        
        elif gateway['type'] == 'parallelGateway':
            # Note about parallel execution
            rule = {
                'type': 'note',
                'description': 'Parallel gateway - create steps at same position for visual parallelism',
                'bpmn_gateway_id': gateway['id']
            }
            rules.append(rule)
        
        result = {
            'status': 'partial' if decision['warnings'] else 'success',
            'rules': rules,
            'warnings': decision['warnings']
        }
        
        return result
    
    def _migrate_event(self, event: Dict[str, Any], element_to_step: Dict[str, Any], position: int) -> Dict[str, Any]:
        """Migrate a BPMN event"""
        decision = self.rule_engine.analyze_element(event)
        
        if decision['strategy'] == 'unsupported':
            return {
                'status': 'failed',
                'reason': decision['reasoning']
            }
        
        result = {'status': 'success'}
        
        # Start events
        if event['category'] == 'start':
            if event['eventType'] == 'none':
                result['type'] = 'manual_start'
            elif event['eventType'] == 'message':
                result['type'] = 'webhook_trigger'
                result['webhook_url'] = '{{CONFIGURE_WEBHOOK}}'
                result['status'] = 'partial'
                result['warnings'] = ['Configure webhook for message start']
            elif event['eventType'] == 'timer':
                result['type'] = 'scheduled_start'
                result['status'] = 'partial'
                result['warnings'] = ['Use external scheduler for timer start']
        
        # End events
        elif event['category'] == 'end':
            if event['eventType'] == 'none':
                result['type'] = 'process_complete'
            elif event['eventType'] == 'message':
                result['step'] = {
                    'position': position,
                    'title': f'Send {event["name"]}',
                    'task_type': 'email',
                    'bpmn_event_id': event['id']
                }
            elif event['eventType'] == 'error':
                result['type'] = 'mark_as_problem'
                result['status'] = 'partial'
                result['warnings'] = ['Error end simplified to problem flag']
        
        # Intermediate events
        elif 'intermediate' in event['category']:
            if event['eventType'] == 'timer':
                result['step'] = {
                    'position': position,
                    'title': f'Wait: {event["name"]}',
                    'task_type': 'task',
                    'deadline': {
                        'unit': 'hour',
                        'value': 1
                    },
                    'bpmn_event_id': event['id']
                }
            elif event['eventType'] == 'message':
                if 'throw' in event['category']:
                    result['step'] = {
                        'position': position,
                        'title': f'Send: {event["name"]}',
                        'task_type': 'email',
                        'bpmn_event_id': event['id']
                    }
                else:
                    result['step'] = {
                        'position': position,
                        'title': f'Wait for: {event["name"]}',
                        'task_type': 'approval',
                        'bpmn_event_id': event['id']
                    }
        
        # Boundary events
        elif event['category'] == 'boundary':
            result['status'] = 'failed'
            result['reason'] = 'Boundary events cannot be migrated to Tallyfy'
        
        return result
    
    def _migrate_forms(self, forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Migrate BPMN form fields to Tallyfy captures"""
        captures = []
        
        for form in forms:
            # Use rule engine for field mapping
            capture = self.rule_engine.map_form_field(form['type'], form)
            
            capture['bpmn_field_id'] = form['id']
            captures.append(capture)
        
        return captures
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate migration report"""
        report = {
            'summary': {
                'total_processes': len(self.results['processes']),
                'total_templates': len(self.results['tallyfy_templates']),
                'migration_rate': 0,
                'manual_work_required': False
            },
            'statistics': {},
            'recommendations': []
        }
        
        # Calculate migration statistics
        total_elements = 0
        successful = 0
        partial = 0
        failed = 0
        
        for template in self.results['tallyfy_templates']:
            details = template['migration_details']
            successful += len(details['successful'])
            partial += len(details['partial'])
            failed += len(details['failed'])
        
        total_elements = successful + partial + failed
        
        if total_elements > 0:
            report['summary']['migration_rate'] = (successful / total_elements) * 100
            report['summary']['manual_work_required'] = partial > 0 or failed > 0
        
        report['statistics'] = {
            'elements_processed': total_elements,
            'successful_migrations': successful,
            'partial_migrations': partial,
            'failed_migrations': failed
        }
        
        # Get optimization suggestions from rule engine
        process_stats = {
            'task_count': sum(p['statistics']['tasks'] for p in self.results['processes']),
            'gateway_count': sum(p['statistics']['gateways'] for p in self.results['processes']),
            'unsupported_count': failed,
            'has_loops': any(
                any(t['properties'].get('loop') for t in p['elements']['tasks'])
                for p in self.results['processes']
            ),
            'parallel_gateways': sum(
                len([g for g in p['elements']['gateways'] if g['type'] == 'parallelGateway'])
                for p in self.results['processes']
            )
        }
        
        optimization = self.rule_engine.suggest_optimization(process_stats)
        report['recommendations'] = optimization['recommendations']
        report['complexity'] = optimization['difficulty']
        report['estimated_work'] = optimization['estimated_manual_work']
        
        return report
    
    def _save_output(self, output_file: str):
        """Save migration results to JSON file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"Results saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save output: {e}")
            self.results['errors'].append(f"Failed to save output: {e}")
    
    def print_report(self):
        """Print human-readable migration report"""
        print("\n" + "="*60)
        print("BPMN TO TALLYFY MIGRATION REPORT")
        print("="*60)
        
        print(f"\nSource: {self.results['source_file']}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        summary = self.results['summary']
        print(f"\n📊 Summary:")
        print(f"  Processes: {summary['total_processes']}")
        print(f"  Total Elements: {summary['total_elements']}")
        print(f"  Complexity: {summary['complexity']}")
        print(f"  Estimated Time: {summary['estimated_migration_time']}")
        
        report = self.results['migration_report']
        if report:
            stats = report['statistics']
            print(f"\n✅ Migration Statistics:")
            print(f"  Success Rate: {report['summary']['migration_rate']:.1f}%")
            print(f"  Successful: {stats['successful_migrations']}")
            print(f"  Partial: {stats['partial_migrations']}")
            print(f"  Failed: {stats['failed_migrations']}")
            
            if report['recommendations']:
                print(f"\n💡 Recommendations:")
                for rec in report['recommendations']:
                    print(f"  • {rec}")
        
        if self.results['warnings']:
            print(f"\n⚠️ Warnings:")
            for warning in self.results['warnings'][:5]:
                print(f"  • {warning}")
        
        if self.results['errors']:
            print(f"\n❌ Errors:")
            for error in self.results['errors']:
                print(f"  • {error}")
        
        print("\n" + "="*60 + "\n")


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='BPMN to Tallyfy Migrator - Self-contained rule-based migration'
    )
    
    parser.add_argument(
        'bpmn_file',
        help='Path to BPMN 2.0 XML file'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output JSON file for Tallyfy template',
        default=None
    )
    
    parser.add_argument(
        '-v', '--verbose',
        help='Verbose output',
        action='store_true'
    )
    
    parser.add_argument(
        '--no-report',
        help='Skip printing report',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if file exists
    if not os.path.exists(args.bpmn_file):
        print(f"Error: File '{args.bpmn_file}' not found")
        sys.exit(1)
    
    # Create migrator and run migration
    migrator = BPMNToTallyfyMigrator()
    
    print(f"🚀 Starting migration of {args.bpmn_file}...")
    results = migrator.migrate_file(args.bpmn_file, args.output)
    
    # Print report unless disabled
    if not args.no_report:
        migrator.print_report()
    
    # Exit with appropriate code
    if results['errors']:
        sys.exit(1)
    elif results['migration_report'].get('summary', {}).get('manual_work_required'):
        print("⚠️ Migration completed with warnings. Manual work required.")
        sys.exit(0)
    else:
        print("✅ Migration completed successfully!")
        sys.exit(0)


if __name__ == '__main__':
    main()