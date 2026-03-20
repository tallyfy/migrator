"""
AI Client for SurveyMonkey to Tallyfy Migration
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
    """AI-powered decision maker for SurveyMonkey migration challenges"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize AI client with optional API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('AI_MODEL', 'claude-opus-4-6')
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
            'analyze_survey_complexity.txt': self._fallback_survey_complexity,
            'map_custom_field.txt': self._fallback_field_mapping,
            'optimize_page_transformation.txt': self._fallback_page_transformation,
        }

        handler = decision_map.get(prompt_file, self._fallback_default)
        result = handler(context)
        result['ai_powered'] = False
        result['fallback'] = True
        return result

    def _fallback_survey_complexity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for survey complexity assessment"""
        question_count = context.get('question_count', 0)
        page_count = context.get('page_count', 0)
        has_logic = context.get('has_logic', False)
        has_piping = context.get('has_piping', False)

        # SurveyMonkey-specific thresholds
        if question_count <= 15 and not has_logic:
            strategy = 'simple_kickoff'
            reasoning = 'Simple survey suitable for kick-off form'
        elif question_count <= 30 or page_count <= 3:
            strategy = 'multi_section'
            reasoning = 'Medium complexity, use page-based sections'
        else:
            strategy = 'multi_step_workflow'
            reasoning = 'Complex survey needs workflow steps'

        # Adjust for piping (variable substitution)
        if has_piping and strategy != 'simple_kickoff':
            strategy = 'multi_step_workflow'
            reasoning += ' (has piping/variable logic)'

        # Suggest step breakdown
        steps_suggested = []
        if question_count > 15:
            num_steps = max(page_count, (question_count // 10) + 1)
            for i in range(num_steps):
                steps_suggested.append(f"Step {i+1}: Questions {i*10+1}-{min((i+1)*10, question_count)}")

        return {
            'strategy': strategy,
            'reasoning': reasoning,
            'suggested_steps': steps_suggested,
            'confidence': 0.65,
            'requires_review': has_logic or has_piping
        }

    def _fallback_field_mapping(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for custom field mapping"""
        field_type = context.get('field_type', '').lower()
        field_name = context.get('field_name', '').lower()
        sample_values = context.get('sample_values', [])

        # SurveyMonkey-specific field patterns
        if 'email' in field_name:
            tallyfy_type = 'email'
            validation = 'email'
        elif 'date' in field_type or 'date' in field_name:
            tallyfy_type = 'date'
            validation = 'none'
        elif any(len(str(val)) > 100 for val in sample_values):
            tallyfy_type = 'textarea'
            validation = 'none'
        else:
            tallyfy_type = 'text'
            validation = 'none'

        return {
            'tallyfy_type': tallyfy_type,
            'validation': validation,
            'transform_needed': field_type not in ['text', 'date'],
            'confidence': 0.6,
            'needs_review': False
        }

    def _fallback_page_transformation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback for page to step transformation"""
        page_count = context.get('page_count', 0)
        avg_questions_per_page = context.get('avg_questions_per_page', 0)

        if avg_questions_per_page > 10:
            steps_per_page = 2  # Split large pages
            strategy = 'split_pages'
        else:
            steps_per_page = 1  # Direct mapping
            strategy = 'direct_mapping'

        total_steps = page_count * steps_per_page

        return {
            'strategy': strategy,
            'steps_per_page': steps_per_page,
            'total_steps': total_steps,
            'reasoning': f"Transform {page_count} pages to {total_steps} steps",
            'confidence': 0.7,
            'requires_manual_review': avg_questions_per_page > 15
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

    def _fallback_pattern_analysis(self, items: List[Dict[str, Any]],
                                    pattern_type: str) -> Dict[str, Any]:
        """Fallback for pattern analysis"""
        return {
            'pattern_type': pattern_type,
            'item_count': len(items),
            'patterns_found': 0,
            'confidence': 0.4,
            'ai_powered': False,
            'fallback': True
        }
