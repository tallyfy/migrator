"""AI-powered decision maker for ambiguous migration cases."""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic library not installed. AI features disabled.")

logger = logging.getLogger(__name__)


class AIClient:
    """AI-powered decision maker for ambiguous migration cases."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = "claude-3-haiku-20240307",
                 temperature: float = 0.0):
        """Initialize AI client.
        
        Args:
            api_key: Anthropic API key (or from env)
            model: Model to use (haiku for speed, sonnet for accuracy)
            temperature: 0 for deterministic, higher for creative
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('AI_MODEL', model)
        self.temperature = float(os.getenv('AI_TEMPERATURE', temperature))
        self.max_tokens = int(os.getenv('AI_MAX_TOKENS', '500'))
        self.client = None
        self.enabled = False
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.enabled = True
                logger.info(f"✅ AI client initialized with model: {self.model}")
            except Exception as e:
                logger.warning(f"⚠️ AI client initialization failed: {e}")
                self.enabled = False
        else:
            if not ANTHROPIC_AVAILABLE:
                logger.info("AI features disabled - anthropic library not installed")
            else:
                logger.info("AI features disabled - no API key provided")
    
    def make_decision(self, prompt_file: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make AI-powered decision using prompt template.
        
        Args:
            prompt_file: Name of prompt template file
            context: Context variables for prompt
            
        Returns:
            Decision dictionary with ai_powered flag
        """
        if not self.enabled:
            return self._fallback_decision(prompt_file, context)
        
        try:
            # Load prompt template
            prompt_path = Path(__file__).parent.parent / 'prompts' / prompt_file
            if not prompt_path.exists():
                logger.warning(f"Prompt file not found: {prompt_path}")
                return self._fallback_decision(prompt_file, context)
            
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
            # Extract JSON from response (handle markdown code blocks)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            result = json.loads(content.strip())
            result['ai_powered'] = True
            logger.debug(f"AI decision made: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"AI decision failed, using fallback: {e}")
            return self._fallback_decision(prompt_file, context)
    
    def _fallback_decision(self, prompt_file: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback when AI unavailable.
        
        Args:
            prompt_file: Name of prompt template
            context: Context for decision
            
        Returns:
            Fallback decision
        """
        fallbacks = {
            'assess_checklist_complexity.txt': self._fallback_checklist_complexity,
            'map_ambiguous_field.txt': self._fallback_field_mapping,
            'determine_workflow_steps.txt': self._fallback_workflow_steps,
            'analyze_conditional_logic.txt': self._fallback_conditional_logic,
            'optimize_batch_size.txt': self._fallback_batch_size
        }
        
        handler = fallbacks.get(prompt_file, self._default_fallback)
        result = handler(context)
        result['ai_powered'] = False
        result['fallback_used'] = True
        return result
    
    def _fallback_checklist_complexity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Heuristic for checklist complexity assessment."""
        task_count = context.get('task_count', 0)
        has_conditions = context.get('has_conditions', False)
        has_integrations = context.get('has_integrations', False)
        
        if task_count <= 10 and not has_conditions:
            strategy = 'simple'
        elif task_count <= 30 or has_conditions:
            strategy = 'moderate'
        else:
            strategy = 'complex'
        
        return {
            'strategy': strategy,
            'reasoning': f'Based on {task_count} tasks, conditions={has_conditions}',
            'confidence': 0.7
        }
    
    def _fallback_field_mapping(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Best-guess field type mapping."""
        vendor_type = context.get('vendor_type', '').lower()
        field_name = context.get('field_name', '').lower()
        
        # Common patterns
        if "text" in vendor_type or "text" in field_name:
            return {'tallyfy_type': 'text', 'validation': "text", 'confidence': 0.8}
        elif 'date' in vendor_type:
            return {'tallyfy_type': 'date', 'confidence': 0.9}
        elif "text" in vendor_type:
            return {'tallyfy_type': "text", 'confidence': 0.8}
        elif "file" in vendor_type:
            return {'tallyfy_type': 'file', 'confidence': 0.9}
        elif 'member' in vendor_type:
            return {'tallyfy_type': 'assignees_form', 'confidence': 0.8}
        else:
            return {'tallyfy_type': 'text', 'confidence': 0.5}
    
    def _fallback_workflow_steps(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow steps from checklist structure."""
        task_count = context.get('task_count', 0)
        
        # Group tasks into logical steps
        if task_count <= 5:
            steps = [{'name': 'Complete Checklist', 'type': 'task'}]
        else:
            step_count = min(10, task_count // 5)
            steps = [{'name': f'Phase {i+1}', 'type': 'task'} for i in range(step_count)]
        
        return {
            'steps': steps,
            'reasoning': 'Grouped tasks into logical phases',
            'confidence': 0.6
        }
    
    def _fallback_conditional_logic(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conditional logic for migration."""
        conditions = context.get('conditions', [])
        
        return {
            'has_complex_conditions': len(conditions) > 3,
            'can_migrate': True,
            'manual_review_required': len(conditions) > 0,
            'confidence': 0.5
        }
    
    def _fallback_batch_size(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal batch size."""
        total_items = context.get('total_items', 0)
        item_complexity = context.get('complexity', 'medium')
        
        if item_complexity == 'simple':
            batch_size = 100
        elif item_complexity == 'complex':
            batch_size = 25
        else:
            batch_size = 50
        
        return {
            'batch_size': batch_size,
            'reasoning': f'Based on {total_items} items with {item_complexity} complexity',
            'confidence': 0.7
        }
    
    def _default_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generic fallback for unknown prompt types."""
        return {
            'decision': 'default',
            'confidence': 0.5,
            'manual_review_required': True
        }
    
    def batch_decisions(self, prompt_file: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Make multiple decisions efficiently.
        
        Args:
            prompt_file: Prompt template to use
            items: List of context items
            
        Returns:
            List of decisions
        """
        results = []
        for item in items:
            result = self.make_decision(prompt_file, item)
            results.append(result)
        return results
    
    def log_usage(self) -> Dict[str, Any]:
        """Get AI usage statistics.
        
        Returns:
            Usage statistics
        """
        return {
            'enabled': self.enabled,
            'model': self.model if self.enabled else None,
            'temperature': self.temperature if self.enabled else None
        }