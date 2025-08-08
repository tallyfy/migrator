"""AI-powered decision maker for Pipefy migration ambiguous cases."""

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
    """AI-powered decision maker for Pipefy migration challenges."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = "claude-3-haiku-20240307",
                 temperature: float = 0.0):
        """Initialize AI client for Pipefy migration."""
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
        """Make AI-powered decision using prompt template."""
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
        """Deterministic fallback when AI unavailable."""
        fallbacks = {
            'analyze_kanban_paradigm.txt': self._fallback_kanban_analysis,
            'map_phase_to_steps.txt': self._fallback_phase_mapping,
            'optimize_card_batch.txt': self._fallback_batch_optimization,
            'map_field_type.txt': self._fallback_field_mapping,
            'analyze_sla_rules.txt': self._fallback_sla_analysis
        }
        
        handler = fallbacks.get(prompt_file, self._default_fallback)
        result = handler(context)
        result['ai_powered'] = False
        result['fallback_used'] = True
        return result
    
    def _fallback_kanban_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Kanban to Sequential paradigm shift."""
        phase_count = context.get('phase_count', 0)
        has_parallel = context.get('has_parallel_phases', False)
        
        # Each phase becomes 3 steps: Entry, Work, Exit
        step_count = phase_count * 3
        
        return {
            'transformation_strategy': 'three_step_per_phase',
            'estimated_steps': step_count,
            'requires_training': True,
            'reasoning': f'Converting {phase_count} Kanban phases to sequential workflow',
            'confidence': 0.8
        }
    
    def _fallback_phase_mapping(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Map Pipefy phase to Tallyfy steps."""
        phase_name = context.get('phase_name', 'Phase')
        phase_type = context.get('phase_type', 'standard')
        
        steps = [
            {'name': f'{phase_name} - Entry', 'type': 'task', 'description': 'Review and prepare'},
            {'name': f'{phase_name} - Work', 'type': 'task', 'description': 'Complete phase work'},
            {'name': f'{phase_name} - Exit', 'type': 'approval', 'description': 'Approve completion'}
        ]
        
        return {
            'steps': steps,
            'reasoning': 'Standard 3-step pattern for Kanban phase',
            'confidence': 0.7
        }
    
    def _fallback_batch_optimization(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize batch size for card migration."""
        total_cards = context.get('total_cards', 0)
        complexity_points = context.get('complexity_points', 1000000)
        
        # GraphQL complexity-based batching
        if complexity_points < 500000:
            batch_size = 100
        elif complexity_points < 1000000:
            batch_size = 50
        else:
            batch_size = 25
        
        return {
            'batch_size': batch_size,
            'estimated_batches': (total_cards + batch_size - 1) // batch_size,
            'reasoning': f'Based on {complexity_points} complexity points',
            'confidence': 0.7
        }
    
    def _fallback_field_mapping(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Map Pipefy field type to Tallyfy."""
        pipefy_type = context.get('pipefy_type', '').lower()
        
        # Direct mappings
        mappings = {
            'text': 'text',
            'textarea': 'textarea',
            "text": "text",
            'date': 'date',
            'datetime': 'date',
            'select': 'dropdown',
            "radio": 'radio',
            "multiselect": 'multiselect',
            "text": 'text',
            "text": 'text',
            'assignee_select': 'assignees_form',
            'attachment': 'file'
        }
        
        tallyfy_type = mappings.get(pipefy_type, 'text')
        
        return {
            'tallyfy_type': tallyfy_type,
            'needs_validation': pipefy_type in ["text", "text"],
            'confidence': 0.9 if pipefy_type in mappings else 0.5
        }
    
    def _fallback_sla_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SLA rules for migration."""
        sla_rules = context.get('sla_rules', [])
        
        return {
            'can_migrate': len(sla_rules) <= 10,
            'manual_configuration': len(sla_rules) > 0,
            'complexity': 'high' if len(sla_rules) > 5 else 'low',
            'confidence': 0.6
        }
    
    def _default_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generic fallback."""
        return {
            'decision': 'manual_review',
            'confidence': 0.5,
            'manual_review_required': True
        }