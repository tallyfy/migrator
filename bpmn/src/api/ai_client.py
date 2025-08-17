"""
AI Client for BPMN Migration Intelligence
Handles complex decision-making for BPMN to Tallyfy transformations
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AIClient:
    """AI client for intelligent BPMN migration decisions"""
    
    def __init__(self):
        """Initialize AI client with Anthropic API"""
        
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.enabled = bool(self.api_key)
        self.client = None
        
        if self.enabled:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                logger.info("✅ AI augmentation enabled - complex BPMN patterns will be intelligently transformed")
            except ImportError:
                logger.warning("⚠️ Anthropic library not installed - AI features disabled")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize AI client: {e}")
                self.enabled = False
        else:
            logger.info("⚠️ AI disabled - using deterministic fallbacks for complex patterns")
        
        # Load prompt templates
        self.prompts_dir = Path(__file__).parent.parent / 'prompts'
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            'decisions_made': 0,
            'ai_calls': 0,
            'fallbacks_used': 0,
            'cache_hits': 0
        }
        
        # Decision cache to avoid redundant AI calls
        self.decision_cache = {}
    
    def analyze_gateway_complexity(self, gateway: Dict[str, Any], 
                                  sequence_flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze gateway complexity and determine transformation strategy
        
        Args:
            gateway: BPMN gateway element
            sequence_flows: Related sequence flows
            
        Returns:
            Transformation strategy with confidence score
        """
        self.stats['decisions_made'] += 1
        
        # Create cache key
        cache_key = f"gateway_{gateway['type']}_{len(gateway['incoming'])}_{len(gateway['outgoing'])}"
        if cache_key in self.decision_cache:
            self.stats['cache_hits'] += 1
            return self.decision_cache[cache_key]
        
        if not self.enabled:
            self.stats['fallbacks_used'] += 1
            return self._gateway_complexity_fallback(gateway, sequence_flows)
        
        try:
            # Load prompt template
            prompt = self._load_prompt('analyze_gateway_complexity.txt')
            
            # Prepare context
            context = {
                'gateway_type': gateway['type'],
                'gateway_name': gateway.get('name', 'Unnamed'),
                'incoming_count': len(gateway['incoming']),
                'outgoing_count': len(gateway['outgoing']),
                'conditions': [f.get('condition', '') for f in sequence_flows if f['source_ref'] == gateway['id']]
            }
            
            # Format prompt
            formatted_prompt = prompt.format(**context)
            
            # Make AI call
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                system="You are an expert in BPMN to workflow transformation. Respond with JSON only.",
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            
            self.stats['ai_calls'] += 1
            
            # Parse response
            result = self._extract_json(response.content[0].text)
            
            # Cache result
            self.decision_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"AI gateway analysis failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._gateway_complexity_fallback(gateway, sequence_flows)
    
    def transform_complex_process(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze complex process and determine optimal transformation
        
        Args:
            process: BPMN process with all elements
            
        Returns:
            Transformation strategy
        """
        self.stats['decisions_made'] += 1
        
        if not self.enabled:
            self.stats['fallbacks_used'] += 1
            return self._process_transformation_fallback(process)
        
        try:
            # Load prompt template
            prompt = self._load_prompt('transform_complex_process.txt')
            
            # Prepare process summary
            context = {
                'process_name': process.get('name', 'Unnamed Process'),
                'task_count': len(process['tasks']),
                'gateway_count': len(process['gateways']),
                'event_count': len(process['events']),
                'lane_count': len(process['lanes']),
                'subprocess_count': len(process.get('subprocesses', [])),
                'has_loops': self._detect_loops(process),
                'has_parallel': any(g['type'] == 'parallelGateway' for g in process['gateways']),
                'has_events': len([e for e in process['events'] if e['type'] != 'none']) > 0
            }
            
            # Format prompt
            formatted_prompt = prompt.format(**context)
            
            # Make AI call
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                system="You are an expert in business process optimization. Respond with JSON only.",
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            
            self.stats['ai_calls'] += 1
            
            # Parse response
            return self._extract_json(response.content[0].text)
            
        except Exception as e:
            logger.error(f"AI process transformation failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._process_transformation_fallback(process)
    
    def map_complex_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map complex BPMN event to Tallyfy equivalent
        
        Args:
            event: BPMN event element
            
        Returns:
            Mapping strategy
        """
        self.stats['decisions_made'] += 1
        
        # Simple events don't need AI
        if event['type'] in ['none', 'message', 'timer']:
            return self._simple_event_mapping(event)
        
        if not self.enabled:
            self.stats['fallbacks_used'] += 1
            return self._event_mapping_fallback(event)
        
        try:
            # Load prompt template
            prompt = self._load_prompt('map_complex_event.txt')
            
            # Format prompt
            formatted_prompt = prompt.format(
                event_type=event['type'],
                event_position=event['position'],
                event_name=event.get('name', 'Unnamed')
            )
            
            # Make AI call
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                system="You are an expert in workflow event handling. Respond with JSON only.",
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            
            self.stats['ai_calls'] += 1
            
            # Parse response
            return self._extract_json(response.content[0].text)
            
        except Exception as e:
            logger.error(f"AI event mapping failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._event_mapping_fallback(event)
    
    def optimize_lane_to_role_mapping(self, lanes: List[Dict[str, Any]], 
                                     tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize mapping of BPMN lanes to Tallyfy roles/groups
        
        Args:
            lanes: List of BPMN lanes
            tasks: List of tasks with lane assignments
            
        Returns:
            Optimized role mapping
        """
        self.stats['decisions_made'] += 1
        
        if not self.enabled or len(lanes) <= 1:
            self.stats['fallbacks_used'] += 1
            return self._lane_mapping_fallback(lanes, tasks)
        
        try:
            # Load prompt template
            prompt = self._load_prompt('optimize_lane_mapping.txt')
            
            # Prepare lane summary
            lane_summary = []
            for lane in lanes:
                lane_tasks = [t for t in tasks if t['id'] in lane.get('flow_node_refs', [])]
                lane_summary.append({
                    'name': lane.get('name', 'Unnamed'),
                    'task_count': len(lane_tasks),
                    'task_types': list(set(t['type'] for t in lane_tasks))
                })
            
            # Format prompt
            formatted_prompt = prompt.format(
                lane_count=len(lanes),
                lanes=json.dumps(lane_summary, indent=2)
            )
            
            # Make AI call
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                system="You are an expert in organizational role mapping. Respond with JSON only.",
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            
            self.stats['ai_calls'] += 1
            
            # Parse response
            return self._extract_json(response.content[0].text)
            
        except Exception as e:
            logger.error(f"AI lane mapping failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._lane_mapping_fallback(lanes, tasks)
    
    def handle_loop_pattern(self, loop_elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determine best approach for handling BPMN loops
        
        Args:
            loop_elements: Elements involved in loop pattern
            
        Returns:
            Loop handling strategy
        """
        self.stats['decisions_made'] += 1
        
        if not self.enabled:
            self.stats['fallbacks_used'] += 1
            return self._loop_pattern_fallback(loop_elements)
        
        try:
            # Load prompt template
            prompt = self._load_prompt('handle_loop_pattern.txt')
            
            # Format prompt
            formatted_prompt = prompt.format(
                element_count=len(loop_elements),
                has_condition=any('condition' in e for e in loop_elements)
            )
            
            # Make AI call
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                system="You are an expert in workflow loop handling. Respond with JSON only.",
                messages=[{"role": "user", "content": formatted_prompt}]
            )
            
            self.stats['ai_calls'] += 1
            
            # Parse response
            return self._extract_json(response.content[0].text)
            
        except Exception as e:
            logger.error(f"AI loop handling failed: {e}")
            self.stats['fallbacks_used'] += 1
            return self._loop_pattern_fallback(loop_elements)
    
    # Fallback methods for when AI is unavailable
    
    def _gateway_complexity_fallback(self, gateway: Dict[str, Any], 
                                    sequence_flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic fallback for gateway analysis"""
        
        strategy = {
            'transformation': 'simple',
            'confidence': 0.7,
            'approach': 'deterministic'
        }
        
        if gateway['type'] == 'exclusiveGateway':
            strategy['transformation'] = 'conditional_rules'
            strategy['implementation'] = 'IF-THEN rules for each path'
        
        elif gateway['type'] == 'parallelGateway':
            strategy['transformation'] = 'parallel_steps'
            strategy['implementation'] = 'Create parallel steps with same position'
        
        elif gateway['type'] == 'inclusiveGateway':
            strategy['transformation'] = 'multiple_conditions'
            strategy['implementation'] = 'Multiple non-exclusive rules'
            strategy['confidence'] = 0.6
        
        elif gateway['type'] == 'eventBasedGateway':
            strategy['transformation'] = 'approval_with_timeout'
            strategy['implementation'] = 'Approval step with timeout rules'
            strategy['confidence'] = 0.5
        
        else:  # complexGateway
            strategy['transformation'] = 'manual_review'
            strategy['implementation'] = 'Requires manual configuration'
            strategy['confidence'] = 0.3
        
        return strategy
    
    def _process_transformation_fallback(self, process: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback for process transformation"""
        
        complexity_score = (
            len(process['tasks']) * 1 +
            len(process['gateways']) * 3 +
            len(process['events']) * 2 +
            len(process.get('subprocesses', [])) * 5
        )
        
        if complexity_score < 20:
            return {
                'strategy': 'direct_mapping',
                'split_into_templates': False,
                'confidence': 0.8
            }
        elif complexity_score < 50:
            return {
                'strategy': 'simplified_mapping',
                'split_into_templates': False,
                'simplifications': ['merge_parallel_gateways', 'inline_subprocesses'],
                'confidence': 0.6
            }
        else:
            return {
                'strategy': 'multi_template',
                'split_into_templates': True,
                'split_points': ['subprocesses', 'pools'],
                'confidence': 0.5
            }
    
    def _event_mapping_fallback(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback for event mapping"""
        
        mappings = {
            'signal': {'type': 'webhook', 'implementation': 'External signal via webhook'},
            'error': {'type': 'failed_status', 'implementation': 'Mark task as failed'},
            'escalation': {'type': 'notification', 'implementation': 'Send escalation notification'},
            'compensate': {'type': 'rollback_step', 'implementation': 'Add compensation steps'},
            'conditional': {'type': 'conditional_wait', 'implementation': 'Wait for condition'},
            'link': {'type': 'goto_step', 'implementation': 'Link to another step'},
            'terminate': {'type': 'force_complete', 'implementation': 'Force template completion'}
        }
        
        return mappings.get(event['type'], {
            'type': 'manual_configuration',
            'implementation': 'Requires manual setup',
            'confidence': 0.3
        })
    
    def _simple_event_mapping(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Direct mapping for simple events"""
        
        if event['type'] == 'none':
            if event['position'] == 'start':
                return {'type': 'manual_start', 'implementation': 'User initiates template'}
            else:
                return {'type': 'simple_complete', 'implementation': 'Mark as complete'}
        
        elif event['type'] == 'message':
            return {'type': 'webhook', 'implementation': 'Webhook trigger or wait'}
        
        elif event['type'] == 'timer':
            return {'type': 'deadline', 'implementation': 'Add deadline to step'}
        
        return {'type': 'unknown', 'implementation': 'Manual review required'}
    
    def _lane_mapping_fallback(self, lanes: List[Dict[str, Any]], 
                              tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic fallback for lane mapping"""
        
        role_mappings = []
        
        for lane in lanes:
            lane_name = lane.get('name', f"Lane_{lane['id']}")
            
            # Clean up common lane names
            role_name = lane_name.replace('Lane', '').replace('Swimlane', '').strip()
            
            role_mappings.append({
                'lane_id': lane['id'],
                'lane_name': lane_name,
                'tallyfy_group': role_name,
                'assignment_type': 'group'
            })
        
        return {
            'mappings': role_mappings,
            'strategy': 'direct_mapping',
            'confidence': 0.7
        }
    
    def _loop_pattern_fallback(self, loop_elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic fallback for loop patterns"""
        
        return {
            'strategy': 'external_automation',
            'implementation': 'Use external scheduler to re-run template',
            'notes': 'Tallyfy does not support native loops - requires external orchestration',
            'confidence': 0.5
        }
    
    def _detect_loops(self, process: Dict[str, Any]) -> bool:
        """Detect if process contains loop patterns"""
        
        # Simple cycle detection in sequence flows
        flows = process.get('sequence_flows', [])
        
        # Build adjacency list
        graph = {}
        for flow in flows:
            source = flow['source_ref']
            target = flow['target_ref']
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        # Check for cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True
        
        return False
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from file"""
        
        prompt_file = self.prompts_dir / filename
        
        # Create default prompt if file doesn't exist
        if not prompt_file.exists():
            self._create_default_prompts()
        
        try:
            with open(prompt_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt {filename}: {e}")
            return "Analyze the input and provide a JSON response with your best recommendation."
    
    def _create_default_prompts(self):
        """Create default prompt templates"""
        
        prompts = {
            'analyze_gateway_complexity.txt': """Analyze this BPMN gateway and determine the best transformation strategy for Tallyfy:

Gateway Type: {gateway_type}
Gateway Name: {gateway_name}
Incoming Flows: {incoming_count}
Outgoing Flows: {outgoing_count}
Conditions: {conditions}

Provide a JSON response with:
- transformation: the approach to use (conditional_rules, parallel_steps, multiple_conditions, manual_review)
- implementation: specific implementation details
- confidence: confidence score (0-1)
- notes: any important considerations""",

            'transform_complex_process.txt': """Analyze this complex BPMN process and determine optimal Tallyfy transformation:

Process Name: {process_name}
Tasks: {task_count}
Gateways: {gateway_count}
Events: {event_count}
Lanes: {lane_count}
Subprocesses: {subprocess_count}
Has Loops: {has_loops}
Has Parallel Flows: {has_parallel}
Has Complex Events: {has_events}

Provide a JSON response with:
- strategy: transformation strategy (direct_mapping, simplified_mapping, multi_template)
- split_into_templates: boolean
- simplifications: list of simplifications to apply
- confidence: confidence score (0-1)""",

            'map_complex_event.txt': """Map this BPMN event to Tallyfy:

Event Type: {event_type}
Event Position: {event_position}
Event Name: {event_name}

Provide a JSON response with:
- type: Tallyfy implementation type
- implementation: specific implementation approach
- configuration: any required configuration
- confidence: confidence score (0-1)""",

            'optimize_lane_mapping.txt': """Optimize mapping of BPMN lanes to Tallyfy groups:

Lane Count: {lane_count}
Lanes: {lanes}

Provide a JSON response with:
- mappings: array of lane to group mappings
- strategy: mapping strategy used
- consolidations: any lanes that should be combined
- confidence: confidence score (0-1)""",

            'handle_loop_pattern.txt': """Determine best approach for handling BPMN loop:

Element Count in Loop: {element_count}
Has Exit Condition: {has_condition}

Provide a JSON response with:
- strategy: loop handling strategy
- implementation: specific implementation approach
- external_requirements: any external tools needed
- confidence: confidence score (0-1)"""
        }
        
        for filename, content in prompts.items():
            prompt_file = self.prompts_dir / filename
            if not prompt_file.exists():
                with open(prompt_file, 'w') as f:
                    f.write(content)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from AI response"""
        
        try:
            # Try to parse the entire response as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Fallback to a basic response
            logger.warning("Failed to parse AI response as JSON")
            return {
                'error': 'Failed to parse response',
                'raw_response': text[:500],
                'confidence': 0.1
            }
    
    def get_stats(self) -> Dict[str, int]:
        """Get AI client statistics"""
        return self.stats.copy()