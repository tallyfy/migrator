#!/usr/bin/env python3
"""
BPMN to Tallyfy Rule Engine
Contains all mapping rules and transformation logic embedded directly in code
No external AI required - all decisions are deterministic based on BPMN spec analysis
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MappingRule:
    """Represents a BPMN to Tallyfy mapping rule"""
    bpmn_type: str
    conditions: Dict[str, Any]
    tallyfy_mapping: Dict[str, Any]
    confidence: float
    strategy: str  # direct, transform, partial, unsupported
    manual_steps: List[str]
    warnings: List[str]
    description: str


class BPMNToTallyfyRuleEngine:
    """
    Complete rule engine with all BPMN to Tallyfy mappings
    Based on analysis of 112+ BPMN element permutations
    """
    
    def __init__(self):
        """Initialize with complete rule set"""
        self.rules = self._initialize_rules()
        self.pattern_rules = self._initialize_pattern_rules()
        self.field_mappings = self._initialize_field_mappings()
        self.gateway_rules = self._initialize_gateway_rules()
        self.event_rules = self._initialize_event_rules()
        
    def _initialize_rules(self) -> Dict[str, MappingRule]:
        """Initialize all BPMN element mapping rules"""
        
        rules = {}
        
        # ============== TASK MAPPINGS ==============
        # User Task - 95% confidence
        rules['userTask'] = MappingRule(
            bpmn_type='userTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'button_text': 'Complete'
            },
            confidence=0.95,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='Direct mapping to standard task'
        )
        
        # Manual Task - 95% confidence
        rules['manualTask'] = MappingRule(
            bpmn_type='manualTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'button_text': 'Complete',
                'note': 'Manual task - no automation'
            },
            confidence=0.95,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='Manual task maps to standard task'
        )
        
        # Service Task - 70% confidence
        rules['serviceTask'] = MappingRule(
            bpmn_type='serviceTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'webhook': True,
                'webhook_url': '{{CONFIGURE_WEBHOOK}}',
                'button_text': 'Trigger Service'
            },
            confidence=0.70,
            strategy='transform',
            manual_steps=[
                'Configure webhook URL for service call',
                'Map service parameters to webhook payload',
                'Set up error handling if needed'
            ],
            warnings=['Service task requires webhook configuration'],
            description='Service task maps to webhook-enabled step'
        )
        
        # Script Task - 40% confidence
        rules['scriptTask'] = MappingRule(
            bpmn_type='scriptTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'webhook': True,
                'note': 'Script execution via external service'
            },
            confidence=0.40,
            strategy='partial',
            manual_steps=[
                'Move script logic to external service',
                'Create webhook endpoint for script',
                'Configure webhook in Tallyfy'
            ],
            warnings=[
                'Scripts cannot run natively in Tallyfy',
                'Requires external script execution service'
            ],
            description='Script task requires external execution'
        )
        
        # Business Rule Task - 40% confidence
        rules['businessRuleTask'] = MappingRule(
            bpmn_type='businessRuleTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'captures': [],  # Will be populated with decision fields
                'rules': []  # Will be populated with conditional logic
            },
            confidence=0.40,
            strategy='partial',
            manual_steps=[
                'Convert business rules to Tallyfy conditions',
                'Create form fields for rule inputs',
                'Configure IF-THEN logic for decisions'
            ],
            warnings=['Complex business rules may need simplification'],
            description='Business rules converted to conditional logic'
        )
        
        # Send Task - 85% confidence
        rules['sendTask'] = MappingRule(
            bpmn_type='sendTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'email',
                'button_text': 'Send'
            },
            confidence=0.85,
            strategy='direct',
            manual_steps=['Configure email recipients and template'],
            warnings=[],
            description='Send task maps to email task'
        )
        
        # Receive Task - 70% confidence
        rules['receiveTask'] = MappingRule(
            bpmn_type='receiveTask',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'approval',
                'button_text': 'Acknowledge Receipt'
            },
            confidence=0.70,
            strategy='transform',
            manual_steps=['Configure as approval to wait for external input'],
            warnings=['Receive semantics approximated with approval'],
            description='Receive task as approval/wait step'
        )
        
        # Generic Task - 90% confidence
        rules['task'] = MappingRule(
            bpmn_type='task',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'button_text': 'Complete'
            },
            confidence=0.90,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='Generic task maps to standard task'
        )
        
        # Call Activity - 10% confidence
        rules['callActivity'] = MappingRule(
            bpmn_type='callActivity',
            conditions={},
            tallyfy_mapping={
                'type': 'step',
                'task_type': 'task',
                'note': 'MANUAL: Link to separate template'
            },
            confidence=0.10,
            strategy='unsupported',
            manual_steps=[
                'Create separate template for called process',
                'Add manual instructions to run other template',
                'Consider using webhook to trigger other template'
            ],
            warnings=['No native subprocess support in Tallyfy'],
            description='Call activity requires separate template'
        )
        
        # Subprocess - 50% confidence
        rules['subProcess'] = MappingRule(
            bpmn_type='subProcess',
            conditions={'type': 'embedded'},
            tallyfy_mapping={
                'type': 'inline_steps',
                'note': 'Subprocess flattened into main process'
            },
            confidence=0.50,
            strategy='transform',
            manual_steps=[
                'Flatten subprocess steps into main flow',
                'Add section markers for subprocess boundaries'
            ],
            warnings=['Subprocess structure will be flattened'],
            description='Embedded subprocess inlined'
        )
        
        return rules
    
    def _initialize_pattern_rules(self) -> Dict[str, MappingRule]:
        """Initialize common BPMN pattern rules"""
        
        patterns = {}
        
        # Sequential Process - 100% confidence
        patterns['sequential'] = MappingRule(
            bpmn_type='pattern:sequential',
            conditions={'tasks': 'sequential', 'gateways': 0},
            tallyfy_mapping={
                'type': 'direct_sequence',
                'strategy': 'maintain_order'
            },
            confidence=1.00,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='Sequential tasks map directly'
        )
        
        # Simple Decision - 90% confidence
        patterns['simple_decision'] = MappingRule(
            bpmn_type='pattern:xor_decision',
            conditions={'gateway': 'exclusiveGateway', 'branches': 2},
            tallyfy_mapping={
                'type': 'conditional_rule',
                'rule_type': 'if_then_else'
            },
            confidence=0.90,
            strategy='direct',
            manual_steps=['Configure decision conditions'],
            warnings=[],
            description='XOR gateway as IF-THEN-ELSE'
        )
        
        # Parallel Split-Join - 60% confidence
        patterns['parallel_split_join'] = MappingRule(
            bpmn_type='pattern:parallel',
            conditions={'gateway': 'parallelGateway'},
            tallyfy_mapping={
                'type': 'visual_parallel',
                'implementation': 'same_position_steps'
            },
            confidence=0.60,
            strategy='partial',
            manual_steps=[
                'Create steps at same position for visual parallelism',
                'Add wait/approval step for synchronization if needed'
            ],
            warnings=['No true parallel execution in Tallyfy'],
            description='Parallel simulated with positioning'
        )
        
        # Loop Pattern - 20% confidence
        patterns['loop'] = MappingRule(
            bpmn_type='pattern:loop',
            conditions={'loop': True},
            tallyfy_mapping={
                'type': 'unsupported',
                'alternative': 'external_automation'
            },
            confidence=0.20,
            strategy='unsupported',
            manual_steps=[
                'Loops require external automation',
                'Consider using recurring schedules',
                'May need to redesign without loops'
            ],
            warnings=['Loops not supported - needs redesign'],
            description='Loop patterns cannot be migrated'
        )
        
        # Multi-Instance - 40% confidence
        patterns['multi_instance'] = MappingRule(
            bpmn_type='pattern:multi_instance',
            conditions={'multiInstance': True},
            tallyfy_mapping={
                'type': 'cloned_steps',
                'note': 'Create multiple copies of step'
            },
            confidence=0.40,
            strategy='partial',
            manual_steps=[
                'Manually clone steps for each instance',
                'Configure assignments for each copy',
                'May need external orchestration for dynamic instances'
            ],
            warnings=['Multi-instance requires manual setup'],
            description='Multi-instance as cloned steps'
        )
        
        # Deferred Choice - 40% confidence
        patterns['deferred_choice'] = MappingRule(
            bpmn_type='pattern:event_based_gateway',
            conditions={'gateway': 'eventBasedGateway'},
            tallyfy_mapping={
                'type': 'approval_with_timeout',
                'task_type': 'expiring'
            },
            confidence=0.40,
            strategy='partial',
            manual_steps=[
                'Use expiring task for timeout branch',
                'Configure approval for message branch'
            ],
            warnings=['Event-based choice simplified'],
            description='Event choice as expiring approval'
        )
        
        return patterns
    
    def _initialize_field_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize BPMN form field to Tallyfy capture mappings"""
        
        return {
            # Direct mappings
            'string': {
                'tallyfy_type': 'text',
                'max_length': 200,
                'transformation': 'truncate_if_needed'
            },
            'text': {
                'tallyfy_type': 'textarea',
                'max_length': 30000,
                'transformation': 'direct'
            },
            'integer': {
                'tallyfy_type': 'text',
                'validation': 'numeric',
                'transformation': 'add_numeric_validation'
            },
            'decimal': {
                'tallyfy_type': 'text',
                'validation': 'decimal',
                'transformation': 'add_decimal_validation'
            },
            'boolean': {
                'tallyfy_type': 'radio',
                'options': ['Yes', 'No'],
                'transformation': 'convert_to_radio'
            },
            'date': {
                'tallyfy_type': 'date',
                'transformation': 'direct'
            },
            'datetime': {
                'tallyfy_type': 'date',
                'transformation': 'lose_time_component',
                'warning': 'Time component will be lost'
            },
            'enumeration': {
                'tallyfy_type': 'dropdown',
                'transformation': 'map_to_dropdown'
            },
            'multi_enum': {
                'tallyfy_type': 'multiselect',
                'transformation': 'map_to_multiselect'
            },
            'file': {
                'tallyfy_type': 'file',
                'transformation': 'direct'
            },
            'user': {
                'tallyfy_type': 'assignees_form',
                'transformation': 'map_to_user_picker'
            },
            'email': {
                'tallyfy_type': 'email',
                'transformation': 'direct'
            },
            'url': {
                'tallyfy_type': 'text',
                'validation': 'url',
                'transformation': 'add_url_validation'
            },
            'currency': {
                'tallyfy_type': 'text',
                'prefix': '$',
                'validation': 'numeric',
                'transformation': 'add_currency_format'
            },
            'percentage': {
                'tallyfy_type': 'text',
                'suffix': '%',
                'validation': 'numeric',
                'transformation': 'add_percentage_format'
            },
            'table': {
                'tallyfy_type': 'table',
                'transformation': 'direct'
            },
            'complex': {
                'tallyfy_type': 'textarea',
                'transformation': 'serialize_to_json',
                'warning': 'Complex object serialized as JSON'
            }
        }
    
    def _initialize_gateway_rules(self) -> Dict[str, MappingRule]:
        """Initialize gateway-specific rules"""
        
        gateways = {}
        
        # Exclusive Gateway (XOR) - Diverging
        gateways['exclusiveGateway_diverging'] = MappingRule(
            bpmn_type='exclusiveGateway',
            conditions={'direction': 'diverging', 'branches': 2},
            tallyfy_mapping={
                'type': 'conditional_rules',
                'implementation': 'if_then_else',
                'rule_structure': {
                    'if': {'condition': '{{CONFIGURE}}', 'action': 'show', 'target': 'branch_1'},
                    'else': {'action': 'show', 'target': 'branch_2'}
                }
            },
            confidence=0.90,
            strategy='direct',
            manual_steps=['Configure branch conditions'],
            warnings=[],
            description='XOR gateway as IF-THEN-ELSE rules'
        )
        
        # Exclusive Gateway - Multiple branches
        gateways['exclusiveGateway_multiple'] = MappingRule(
            bpmn_type='exclusiveGateway',
            conditions={'direction': 'diverging', 'branches': '>2'},
            tallyfy_mapping={
                'type': 'conditional_rules',
                'implementation': 'multiple_if_then',
                'rule_structure': 'cascade_if_conditions'
            },
            confidence=0.85,
            strategy='transform',
            manual_steps=[
                'Create IF-THEN rule for each branch',
                'Ensure conditions are mutually exclusive',
                'Add default branch as final ELSE'
            ],
            warnings=['Multiple conditions need careful configuration'],
            description='Multiple XOR branches as cascading rules'
        )
        
        # Exclusive Gateway - Converging
        gateways['exclusiveGateway_converging'] = MappingRule(
            bpmn_type='exclusiveGateway',
            conditions={'direction': 'converging'},
            tallyfy_mapping={
                'type': 'no_action',
                'note': 'Converging XOR needs no special handling'
            },
            confidence=1.00,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='XOR merge requires no action'
        )
        
        # Parallel Gateway (AND) - Diverging
        gateways['parallelGateway_diverging'] = MappingRule(
            bpmn_type='parallelGateway',
            conditions={'direction': 'diverging'},
            tallyfy_mapping={
                'type': 'parallel_visual',
                'implementation': 'same_position',
                'note': 'Create all parallel steps at same position'
            },
            confidence=0.70,
            strategy='partial',
            manual_steps=[
                'Create parallel steps at same position',
                'Assign to different users if needed',
                'Steps execute sequentially but appear parallel'
            ],
            warnings=['Visual parallelism only - not true concurrent execution'],
            description='AND split as same-position steps'
        )
        
        # Parallel Gateway - Converging
        gateways['parallelGateway_converging'] = MappingRule(
            bpmn_type='parallelGateway',
            conditions={'direction': 'converging'},
            tallyfy_mapping={
                'type': 'wait_step',
                'task_type': 'approval',
                'note': 'Wait for all parallel branches'
            },
            confidence=0.50,
            strategy='partial',
            manual_steps=[
                'Create approval step to wait for all branches',
                'Configure to require all parallel tasks complete',
                'May need manual coordination'
            ],
            warnings=['AND join requires manual synchronization'],
            description='AND join as wait/approval step'
        )
        
        # Inclusive Gateway (OR) - Diverging
        gateways['inclusiveGateway_diverging'] = MappingRule(
            bpmn_type='inclusiveGateway',
            conditions={'direction': 'diverging'},
            tallyfy_mapping={
                'type': 'multiple_rules',
                'implementation': 'non_exclusive_conditions'
            },
            confidence=0.60,
            strategy='partial',
            manual_steps=[
                'Create non-exclusive rules for each path',
                'Multiple paths can be active',
                'Configure show/hide for each branch independently'
            ],
            warnings=['OR semantics approximated with rules'],
            description='OR gateway as non-exclusive rules'
        )
        
        # Inclusive Gateway - Converging
        gateways['inclusiveGateway_converging'] = MappingRule(
            bpmn_type='inclusiveGateway',
            conditions={'direction': 'converging'},
            tallyfy_mapping={
                'type': 'unsupported',
                'reason': 'Cannot synchronize variable paths'
            },
            confidence=0.10,
            strategy='unsupported',
            manual_steps=[
                'OR join cannot be properly mapped',
                'Consider redesigning without OR join',
                'May need external orchestration'
            ],
            warnings=['OR join not supported in Tallyfy'],
            description='OR join cannot be migrated'
        )
        
        # Event-based Gateway
        gateways['eventBasedGateway'] = MappingRule(
            bpmn_type='eventBasedGateway',
            conditions={},
            tallyfy_mapping={
                'type': 'expiring_approval',
                'task_type': 'expiring',
                'note': 'Timer vs message as expiring approval'
            },
            confidence=0.40,
            strategy='partial',
            manual_steps=[
                'Use expiring task for timer path',
                'Configure approval for message path',
                'Limited to timeout scenarios'
            ],
            warnings=['Event-based choice simplified significantly'],
            description='Event gateway as expiring task'
        )
        
        # Complex Gateway
        gateways['complexGateway'] = MappingRule(
            bpmn_type='complexGateway',
            conditions={},
            tallyfy_mapping={
                'type': 'unsupported',
                'reason': 'Complex conditions cannot be mapped'
            },
            confidence=0.10,
            strategy='unsupported',
            manual_steps=[
                'Complex gateway logic must be redesigned',
                'Break down into simpler patterns',
                'May require process restructuring'
            ],
            warnings=['Complex gateways not supported'],
            description='Complex gateway cannot be migrated'
        )
        
        return gateways
    
    def _initialize_event_rules(self) -> Dict[str, MappingRule]:
        """Initialize event-specific rules"""
        
        events = {}
        
        # Start Events
        events['startEvent_none'] = MappingRule(
            bpmn_type='startEvent',
            conditions={'eventType': 'none'},
            tallyfy_mapping={
                'type': 'manual_start',
                'trigger': 'user_initiated'
            },
            confidence=1.00,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='Manual process start'
        )
        
        events['startEvent_message'] = MappingRule(
            bpmn_type='startEvent',
            conditions={'eventType': 'message'},
            tallyfy_mapping={
                'type': 'webhook_trigger',
                'webhook_url': '{{CONFIGURE_WEBHOOK}}'
            },
            confidence=0.70,
            strategy='transform',
            manual_steps=['Configure webhook URL for process trigger'],
            warnings=['Message start requires webhook setup'],
            description='Message start as webhook trigger'
        )
        
        events['startEvent_timer'] = MappingRule(
            bpmn_type='startEvent',
            conditions={'eventType': 'timer'},
            tallyfy_mapping={
                'type': 'external_scheduler',
                'note': 'Use external scheduling service'
            },
            confidence=0.30,
            strategy='partial',
            manual_steps=[
                'Set up external scheduler (cron, Zapier, etc)',
                'Configure to trigger process via API',
                'No native scheduling in Tallyfy'
            ],
            warnings=['Timer start requires external scheduler'],
            description='Timer start needs external scheduling'
        )
        
        events['startEvent_signal'] = MappingRule(
            bpmn_type='startEvent',
            conditions={'eventType': 'signal'},
            tallyfy_mapping={
                'type': 'webhook_trigger',
                'note': 'Signal as webhook'
            },
            confidence=0.60,
            strategy='partial',
            manual_steps=['Configure webhook for signal reception'],
            warnings=['Signal semantics approximated'],
            description='Signal start as webhook'
        )
        
        # End Events
        events['endEvent_none'] = MappingRule(
            bpmn_type='endEvent',
            conditions={'eventType': 'none'},
            tallyfy_mapping={
                'type': 'process_complete',
                'action': 'archive_run'
            },
            confidence=1.00,
            strategy='direct',
            manual_steps=[],
            warnings=[],
            description='Normal process completion'
        )
        
        events['endEvent_message'] = MappingRule(
            bpmn_type='endEvent',
            conditions={'eventType': 'message'},
            tallyfy_mapping={
                'type': 'final_step',
                'task_type': 'email',
                'action': 'send_completion_message'
            },
            confidence=0.80,
            strategy='transform',
            manual_steps=['Configure completion email'],
            warnings=[],
            description='Message end as email task'
        )
        
        events['endEvent_error'] = MappingRule(
            bpmn_type='endEvent',
            conditions={'eventType': 'error'},
            tallyfy_mapping={
                'type': 'mark_problem',
                'action': 'flag_run_as_problem'
            },
            confidence=0.60,
            strategy='partial',
            manual_steps=['Configure error handling'],
            warnings=['Error semantics simplified'],
            description='Error end marks run as problem'
        )
        
        events['endEvent_terminate'] = MappingRule(
            bpmn_type='endEvent',
            conditions={'eventType': 'terminate'},
            tallyfy_mapping={
                'type': 'force_complete',
                'action': 'complete_all_tasks'
            },
            confidence=0.70,
            strategy='partial',
            manual_steps=['May need to configure force completion'],
            warnings=['Terminate semantics approximated'],
            description='Terminate as force complete'
        )
        
        # Intermediate Events
        events['intermediateCatchEvent_timer'] = MappingRule(
            bpmn_type='intermediateCatchEvent',
            conditions={'eventType': 'timer'},
            tallyfy_mapping={
                'type': 'task_deadline',
                'deadline_type': 'duration'
            },
            confidence=0.70,
            strategy='transform',
            manual_steps=['Configure task deadline'],
            warnings=[],
            description='Timer as task deadline'
        )
        
        events['intermediateCatchEvent_message'] = MappingRule(
            bpmn_type='intermediateCatchEvent',
            conditions={'eventType': 'message'},
            tallyfy_mapping={
                'type': 'approval_task',
                'task_type': 'approval',
                'note': 'Wait for external input'
            },
            confidence=0.60,
            strategy='partial',
            manual_steps=['Configure as approval to wait for message'],
            warnings=['Message catch approximated as approval'],
            description='Message catch as approval wait'
        )
        
        events['intermediateThrowEvent_message'] = MappingRule(
            bpmn_type='intermediateThrowEvent',
            conditions={'eventType': 'message'},
            tallyfy_mapping={
                'type': 'email_task',
                'task_type': 'email'
            },
            confidence=0.80,
            strategy='direct',
            manual_steps=['Configure email recipients'],
            warnings=[],
            description='Message throw as email'
        )
        
        # Boundary Events - Generally not supported
        events['boundaryEvent'] = MappingRule(
            bpmn_type='boundaryEvent',
            conditions={},
            tallyfy_mapping={
                'type': 'unsupported',
                'reason': 'No boundary event equivalent'
            },
            confidence=0.00,
            strategy='unsupported',
            manual_steps=[
                'Boundary events cannot be migrated',
                'Consider alternative error handling',
                'May need process redesign'
            ],
            warnings=['Boundary events not supported in Tallyfy'],
            description='Boundary events cannot be mapped'
        )
        
        return events
    
    def analyze_element(self, element: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a BPMN element and return migration decision
        
        Args:
            element: BPMN element data
            context: Optional context about surrounding elements
            
        Returns:
            Migration decision with mapping, confidence, and instructions
        """
        
        element_type = element.get('type', '')
        element_id = element.get('id', '')
        element_name = element.get('name', 'Unnamed')
        
        # Check for direct element mapping
        if element_type in self.rules:
            rule = self.rules[element_type]
            return self._create_decision(element, rule)
        
        # Check for gateway-specific rules
        if 'Gateway' in element_type:
            return self._analyze_gateway(element, context)
        
        # Check for event-specific rules
        if 'Event' in element_type:
            return self._analyze_event(element, context)
        
        # Check for pattern matches
        pattern = self._detect_pattern(element, context)
        if pattern:
            return self._create_decision(element, pattern)
        
        # Default unsupported response
        return {
            'element_type': element_type,
            'element_id': element_id,
            'element_name': element_name,
            'confidence': 0.0,
            'strategy': 'unsupported',
            'tallyfy_mapping': {},
            'manual_steps': [f'Element type {element_type} is not supported'],
            'warnings': [f'No Tallyfy equivalent for {element_type}'],
            'reasoning': f'Element type {element_type} has no mapping rule'
        }
    
    def _analyze_gateway(self, element: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze gateway elements with context"""
        
        gateway_type = element.get('type', '')
        
        # Determine gateway direction
        incoming = len(element.get('incoming', []))
        outgoing = len(element.get('outgoing', []))
        
        if incoming == 1 and outgoing > 1:
            direction = 'diverging'
        elif incoming > 1 and outgoing == 1:
            direction = 'converging'
        else:
            direction = 'mixed'
        
        # Build gateway key
        gateway_key = f"{gateway_type}_{direction}"
        
        # Check for specific gateway rule
        if gateway_key in self.gateway_rules:
            rule = self.gateway_rules[gateway_key]
            return self._create_decision(element, rule)
        
        # Check for base gateway type
        if gateway_type in self.gateway_rules:
            rule = self.gateway_rules[gateway_type]
            return self._create_decision(element, rule)
        
        # Default gateway response
        return {
            'element_type': gateway_type,
            'element_id': element.get('id', ''),
            'element_name': element.get('name', 'Gateway'),
            'confidence': 0.1,
            'strategy': 'unsupported',
            'tallyfy_mapping': {},
            'manual_steps': [f'{gateway_type} requires manual configuration'],
            'warnings': ['Complex gateway pattern detected'],
            'reasoning': f'Gateway pattern {gateway_key} needs manual review'
        }
    
    def _analyze_event(self, element: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze event elements"""
        
        event_type = element.get('type', '')
        event_definition = self._get_event_definition(element)
        
        # Build event key
        event_key = f"{event_type}_{event_definition}" if event_definition else event_type
        
        # Check for specific event rule
        if event_key in self.event_rules:
            rule = self.event_rules[event_key]
            return self._create_decision(element, rule)
        
        # Check for base event type
        if event_type in self.event_rules:
            rule = self.event_rules[event_type]
            return self._create_decision(element, rule)
        
        # Default event response
        return {
            'element_type': event_type,
            'element_id': element.get('id', ''),
            'element_name': element.get('name', 'Event'),
            'confidence': 0.1,
            'strategy': 'unsupported',
            'tallyfy_mapping': {},
            'manual_steps': [f'{event_type} cannot be migrated'],
            'warnings': ['Event type not supported'],
            'reasoning': f'Event {event_key} has no Tallyfy equivalent'
        }
    
    def _get_event_definition(self, element: Dict[str, Any]) -> Optional[str]:
        """Extract event definition type from element"""
        
        # Check for event definition child elements
        for key in element.get('attributes', {}):
            if 'EventDefinition' in key:
                return key.replace('EventDefinition', '').lower()
        
        # Check for specific event markers
        if element.get('messageRef'):
            return 'message'
        if element.get('timerEventDefinition'):
            return 'timer'
        if element.get('signalRef'):
            return 'signal'
        if element.get('errorRef'):
            return 'error'
        
        return 'none'
    
    def _detect_pattern(self, element: Dict[str, Any], context: Dict[str, Any]) -> Optional[MappingRule]:
        """Detect common BPMN patterns"""
        
        if not context:
            return None
        
        # Check for sequential pattern
        if context.get('pattern') == 'sequential':
            return self.pattern_rules.get('sequential')
        
        # Check for loop pattern
        if element.get('loopCharacteristics'):
            return self.pattern_rules.get('loop')
        
        # Check for multi-instance
        if element.get('multiInstanceLoopCharacteristics'):
            return self.pattern_rules.get('multi_instance')
        
        return None
    
    def _create_decision(self, element: Dict[str, Any], rule: MappingRule) -> Dict[str, Any]:
        """Create migration decision from rule"""
        
        return {
            'element_type': element.get('type', ''),
            'element_id': element.get('id', ''),
            'element_name': element.get('name', 'Unnamed'),
            'confidence': rule.confidence,
            'strategy': rule.strategy,
            'tallyfy_mapping': rule.tallyfy_mapping.copy(),
            'manual_steps': rule.manual_steps.copy(),
            'warnings': rule.warnings.copy(),
            'reasoning': rule.description
        }
    
    def map_form_field(self, field_type: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map BPMN form field to Tallyfy capture
        
        Args:
            field_type: BPMN field type
            field_data: Field properties
            
        Returns:
            Tallyfy capture configuration
        """
        
        mapping = self.field_mappings.get(field_type, self.field_mappings.get('text'))
        
        capture = {
            'type': mapping['tallyfy_type'],
            'label': field_data.get('label', field_data.get('name', 'Field')),
            'required': field_data.get('required', False)
        }
        
        # Add validation if specified
        if 'validation' in mapping:
            capture['validation'] = mapping['validation']
        
        # Add formatting
        if 'prefix' in mapping:
            capture['prefix'] = mapping['prefix']
        if 'suffix' in mapping:
            capture['suffix'] = mapping['suffix']
        
        # Handle options for select fields
        if field_type in ['enumeration', 'multi_enum', 'boolean']:
            if field_type == 'boolean':
                capture['options'] = mapping['options']
            else:
                capture['options'] = field_data.get('options', [])
        
        # Add any warnings
        if 'warning' in mapping:
            capture['warning'] = mapping['warning']
        
        return capture
    
    def suggest_optimization(self, process_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest process optimizations based on analysis
        
        Args:
            process_stats: Statistics about the process
            
        Returns:
            Optimization recommendations
        """
        
        recommendations = []
        complexity_score = 0
        
        # Analyze task count
        task_count = process_stats.get('task_count', 0)
        if task_count > 20:
            recommendations.append('Consider breaking into multiple templates')
            complexity_score += 2
        
        # Analyze gateway complexity
        gateway_count = process_stats.get('gateway_count', 0)
        if gateway_count > 5:
            recommendations.append('Simplify decision logic where possible')
            complexity_score += 3
        
        # Check for unsupported elements
        unsupported = process_stats.get('unsupported_count', 0)
        if unsupported > 0:
            recommendations.append(f'Redesign {unsupported} unsupported elements')
            complexity_score += unsupported
        
        # Check for loops
        if process_stats.get('has_loops'):
            recommendations.append('Remove loops - use external scheduling instead')
            complexity_score += 5
        
        # Check for parallel gateways
        if process_stats.get('parallel_gateways', 0) > 0:
            recommendations.append('Review parallel execution requirements')
            complexity_score += 2
        
        # Determine migration difficulty
        if complexity_score < 5:
            difficulty = 'Simple'
            estimated_hours = '1-2 hours'
        elif complexity_score < 10:
            difficulty = 'Moderate'
            estimated_hours = '2-4 hours'
        elif complexity_score < 15:
            difficulty = 'Complex'
            estimated_hours = '4-8 hours'
        else:
            difficulty = 'Very Complex'
            estimated_hours = '8+ hours'
        
        return {
            'difficulty': difficulty,
            'complexity_score': complexity_score,
            'estimated_manual_work': estimated_hours,
            'recommendations': recommendations,
            'success_likelihood': max(0, 100 - (complexity_score * 5))
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rule engine statistics"""
        
        return {
            'total_rules': len(self.rules),
            'pattern_rules': len(self.pattern_rules),
            'gateway_rules': len(self.gateway_rules),
            'event_rules': len(self.event_rules),
            'field_mappings': len(self.field_mappings),
            'supported_elements': sum(1 for r in self.rules.values() if r.confidence > 0.5),
            'partial_support': sum(1 for r in self.rules.values() if 0.2 <= r.confidence <= 0.5),
            'unsupported': sum(1 for r in self.rules.values() if r.confidence < 0.2)
        }