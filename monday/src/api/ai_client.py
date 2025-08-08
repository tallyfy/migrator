"""
AI Client for RocketLane to Tallyfy Migration
Provides intelligent decision-making for complex transformations
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from pathlib import Path

logger = logging.getLogger(__name__)


class AIClient:
    """AI-powered decision maker for RocketLane migration challenges"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize AI client with optional API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('AI_MODEL', 'claude-3-haiku-20240307')
        self.temperature = float(os.getenv('AI_TEMPERATURE', '0'))
        self.max_tokens = int(os.getenv('AI_MAX_TOKENS', '500'))
        self.client = None
        self.enabled = False
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.enabled = True
                logger.info(f"AI client initialized with model: {self.model}")
            except Exception as e:
                logger.warning(f"AI client initialization failed: {e}")
                self.enabled = False
        else:
            logger.info("AI client disabled - no API key provided")
    
    def make_decision(self, prompt_file: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make AI-powered decision using prompt template"""
        if not self.enabled:
            return self._fallback_decision(prompt_file, context)
        
        try:
            # Load prompt template
            prompt_path = Path(__file__).parent.parent / 'prompts' / prompt_file
            with open(prompt_path, 'r') as f:
                prompt_template = f.read()
            
            # Fill template with context
            prompt = prompt_template.format(**context)
            
            # Make API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{
                    "role": "user",
                    "content": f"{prompt}\n\nRespond with valid JSON only."
                }]
            )
            
            # Parse response
            content = response.content[0].text
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            result = json.loads(content.strip())
            result['ai_powered'] = True
            
            logger.info(f"AI decision made with confidence: {result.get('confidence', 'N/A')}")
            return result
            
        except Exception as e:
            logger.warning(f"AI decision failed, using fallback: {e}")
            return self._fallback_decision(prompt_file, context)
    
    def _fallback_decision(self, prompt_file: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback when AI is unavailable"""
        
        decision_map = {
            'assess_customer_portal.txt': self._fallback_customer_portal,
            'transform_resource_allocation.txt': self._fallback_resource_allocation,
            'analyze_form_complexity.txt': self._fallback_form_complexity,
            'map_custom_field.txt': self._fallback_field_mapping,
            'optimize_phase_transformation.txt': self._fallback_phase_transformation,
            'determine_time_tracking.txt': self._fallback_time_tracking,
        }
        
        handler = decision_map.get(prompt_file, self._fallback_default)
        result = handler(context)
        result['ai_powered'] = False
        result['fallback'] = True
        return result
    
    def _fallback_customer_portal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for customer portal transformation"""
        interaction_count = context.get('interaction_count', 0)
        has_forms = context.get('has_forms', False)
        
        if interaction_count > 10 or has_forms:
            strategy = 'guest_users'
            reasoning = 'High interaction or forms present'
        else:
            strategy = 'documentation'
            reasoning = 'Low interaction, document only'
        
        return {
            'strategy': strategy,
            'confidence': 0.6,
            'reasoning': reasoning,
            'requires_review': True
        }
    
    def _fallback_resource_allocation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for resource allocation transformation"""
        allocation_percentage = context.get('allocation_percentage', 100)
        has_skills = context.get('has_skills', False)
        
        if allocation_percentage < 100:
            note = f"{allocation_percentage}% allocation"
        else:
            note = "Full allocation"
        
        if has_skills:
            skills = context.get('skills', [])
            note += f", Skills: {', '.join(skills)}"
        
        return {
            'assignment_type': 'direct',
            'assignment_note': note,
            'confidence': 0.7,
            'preserve_as_comment': allocation_percentage < 100
        }
    
    def _fallback_form_complexity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for form complexity assessment"""
        field_count = context.get('field_count', 0)
        has_sections = context.get('has_sections', False)
        has_conditions = context.get('has_conditions', False)
        is_customer_facing = context.get('is_customer_facing', False)
        
        # RocketLane-specific thresholds (lower due to customer focus)
        if field_count <= 15 and not has_conditions:
            strategy = 'simple_kickoff'
            reasoning = 'Simple form suitable for kick-off'
        elif field_count <= 30 or has_sections:
            strategy = 'multi_section'
            reasoning = 'Medium complexity, use sections'
        else:
            strategy = 'multi_step_workflow'
            reasoning = 'Complex form needs workflow steps'
        
        # Adjust for customer-facing forms
        if is_customer_facing and strategy != 'simple_kickoff':
            strategy = 'guest_form_workflow'
            reasoning += ' (customer-facing)'
        
        # Suggest step breakdown
        steps_suggested = []
        if field_count > 15:
            num_steps = (field_count // 10) + 1
            for i in range(num_steps):
                steps_suggested.append(f"Step {i+1}: Fields {i*10+1}-{min((i+1)*10, field_count)}")
        
        return {
            'strategy': strategy,
            'reasoning': reasoning,
            'suggested_steps': steps_suggested,
            'confidence': 0.65,
            'requires_review': has_conditions or is_customer_facing
        }
    
    def _fallback_field_mapping(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for custom field mapping"""
        field_type = context.get('field_type', '').lower()
        field_name = context.get('field_name', '').lower()
        sample_values = context.get('sample_values', [])
        
        # RocketLane-specific field patterns
        if 'customer' in field_name or 'client' in field_name:
            tallyfy_type = 'text'
            validation = 'none'
        elif 'resource' in field_name or "assignees_form" in field_name:
            tallyfy_type = 'member'
            validation = 'none'
        elif 'skill' in field_name:
            tallyfy_type = 'tag'
            validation = 'none'
        elif 'budget' in field_name or 'cost' in field_name:
            tallyfy_type = "text"
            validation = 'currency'
        elif 'priority' in field_type:
            tallyfy_type = 'dropdown'
            validation = 'none'
        elif 'date' in field_type or 'deadline' in field_name:
            tallyfy_type = 'date'
            validation = 'none'
        elif "text" in field_type or 'link' in field_name:
            tallyfy_type = 'link'
            validation = "text"
        elif "text" in field_type:
            tallyfy_type = "text"
            validation = "text"
        elif any(len(str(val)) > 100 for val in sample_values):
            tallyfy_type = 'textarea'
            validation = 'none'
        else:
            tallyfy_type = 'text'
            validation = 'none'
        
        return {
            'tallyfy_type': tallyfy_type,
            'validation': validation,
            'transform_needed': field_type not in ["text", "text", 'date'],
            'confidence': 0.6,
            'needs_review': 'customer' in field_name or 'resource' in field_name
        }
    
    def _fallback_phase_transformation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for phase to step transformation"""
        phase_count = context.get('phase_count', 0)
        has_parallel = context.get('has_parallel_work', False)
        avg_tasks_per_phase = context.get('avg_tasks_per_phase', 0)
        
        if has_parallel:
            # Complex transformation for parallel work
            steps_per_phase = 3  # Entry, Work, Exit pattern
            strategy = 'three_step_pattern'
        elif avg_tasks_per_phase > 5:
            steps_per_phase = 2  # Group tasks into sub-steps
            strategy = 'grouped_tasks'
        else:
            steps_per_phase = 1  # Direct mapping
            strategy = 'direct_mapping'
        
        total_steps = phase_count * steps_per_phase
        
        return {
            'strategy': strategy,
            'steps_per_phase': steps_per_phase,
            'total_steps': total_steps,
            'reasoning': f"Transform {phase_count} phases to {total_steps} steps",
            'confidence': 0.7,
            'requires_manual_review': has_parallel
        }
    
    def _fallback_time_tracking(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for time tracking transformation"""
        has_billing = context.get('has_billing', False)
        total_hours = context.get('total_hours_logged', 0)
        tracking_frequency = context.get('tracking_frequency', 'low')
        
        if has_billing:
            strategy = 'external_integration'
            reasoning = 'Billing requires external time tracking'
        elif total_hours > 100:
            strategy = 'structured_comments'
            reasoning = 'High volume needs structured format'
        elif tracking_frequency == 'high':
            strategy = 'task_comments'
            reasoning = 'Frequent tracking in comments'
        else:
            strategy = 'summary_only'
            reasoning = 'Low volume, summary sufficient'
        
        return {
            'strategy': strategy,
            'reasoning': reasoning,
            'format': '[Time: X hours] Description' if strategy == 'structured_comments' else None,
            'confidence': 0.65,
            'requires_external_tool': has_billing
        }
    
    def _fallback_default(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generic fallback for unknown prompts"""
        return {
            'decision': 'default',
            'confidence': 0.5,
            'reasoning': 'No specific handler available',
            'manual_review_required': True
        }
    
    def batch_decisions(self, prompt_file: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple items with the same prompt"""
        results = []
        for item in items:
            result = self.make_decision(prompt_file, item)
            results.append(result)
        return results
    
    def analyze_patterns(self, items: List[Dict[str, Any]], pattern_type: str) -> Dict[str, Any]:
        """Analyze patterns across multiple items for optimization"""
        if not self.enabled:
            return self._fallback_pattern_analysis(items, pattern_type)
        
        # Use AI to find patterns
        context = {
            'pattern_type': pattern_type,
            'item_count': len(items),
            'samples': items[:5],  # First 5 as samples
            'unique_values': len(set(str(item) for item in items))
        }
        
        return self.make_decision('analyze_patterns.txt', context)