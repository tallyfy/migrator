"""
Typeform Instance Transformer
Transforms Typeform responses to Tallyfy processes
"""

import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Vendor entry points run as scripts, so only `typeform/src` is on sys.path and
# `import shared` would fail. Prepend the repo root so the shared encoder is
# genuinely importable rather than silently falling back to the untyped path.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:  # Typed encoder: keys kick-off values by timeline_id and encodes per type.
    from shared.prerun_encoder import build_prerun_payload
except ImportError as _exc:  # Standalone deployment without the shared package.
    build_prerun_payload = None
    _ENCODER_IMPORT_ERROR = _exc
else:
    _ENCODER_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform Typeform responses to Tallyfy processes"""
    
    def __init__(self, ai_client: Optional[Any] = None):
        """Initialize instance transformer"""
        self.ai_client = ai_client
        logger.info("Typeform instance transformer initialized")
    
    def transform(self, response: Dict[str, Any], blueprint_id: str,
                 form_structure: Optional[Dict[str, Any]] = None,
                 kickoff_fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Transform single Typeform response to Tallyfy process.

        kickoff_fields: the target template's kick-off field definitions. They
        are required to key prerun values by timeline_id; without them the API
        silently discards every value.
        """
        
        # Extract response metadata
        response_id = response.get('response_id', response.get('token', ''))
        submitted_at = response.get('submitted_at', response.get('landed_at'))
        
        # Extract answers
        answers = response.get('answers', [])
        prerun_data = self._extract_answers(answers, form_structure, kickoff_fields)
        
        # Get respondent info
        respondent = self._get_respondent_info(response)
        
        # Create process
        process = {
            'checklist_id': blueprint_id,
            'name': f"Response from {respondent['name']} - {response_id[:8]}",
            'prerun': prerun_data,
            'metadata': {
                'source': 'typeform',
                'typeform_response_id': response_id,
                'typeform_token': response.get('token'),
                'submitted_at': submitted_at,
                'completed': response.get('completed', True),
                'time_to_complete': response.get('metadata', {}).get('browser'),
                'respondent': respondent
            }
        }
        
        # Add calculated score if present
        if response.get('calculated'):
            process['metadata']['calculated_score'] = response['calculated'].get('score')
        
        # Add variables if present
        if response.get('variables'):
            process['metadata']['variables'] = response['variables']
        
        return process
    
    @staticmethod
    def _field_titles(form_structure: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Map each Typeform field id to its human-readable title."""
        titles: Dict[str, str] = {}
        for field in (form_structure or {}).get('fields', []) or []:
            if not isinstance(field, dict):
                continue
            field_id = field.get('id')
            title = field.get('title')
            if field_id and title:
                titles[str(field_id)] = title
        return titles

    def _extract_answers(self, answers: List[Dict[str, Any]],
                        form_structure: Optional[Dict[str, Any]] = None,
                        kickoff_fields: Optional[List[Dict[str, Any]]] = None
                        ) -> Dict[str, Any]:
        """
        Build the `prerun` object from a Typeform response.

        The key must end up as the Tallyfy kick-off field's timeline_id. A
        Typeform field id is not one, so values are first keyed by the field's
        TITLE -- the only identifier shared with the Tallyfy kick-off field
        (whose label was generated from it) -- and then resolved to timeline_ids
        by the shared encoder.

        Previously this keyed by `field_<typeform id>` AND wrote the same value
        a second time under `ref_<typeform ref>`, doubling the payload. Both
        keys were discarded by the API, which keys strictly by timeline_id.
        """
        titles = self._field_titles(form_structure)
        values: Dict[str, Any] = {}
        unnamed: List[str] = []

        for answer in answers:
            field = answer.get('field', {}) or {}
            field_id = str(field.get('id', ''))
            field_type = answer.get('type', '')

            value = self._extract_answer_value(answer, field_type)
            if value is None:
                continue

            # Prefer the form's title; fall back to the title on the answer's
            # own field object if the form structure was not supplied.
            title = titles.get(field_id) or field.get('title')
            if not title:
                unnamed.append(field_id or '<unknown>')
                continue

            values[title] = value

        if unnamed:
            # Without a title there is no way to match the Tallyfy kick-off
            # field, and a guessed key is silently dropped server-side.
            raise ValueError(
                "Cannot map Typeform answers to Tallyfy kick-off fields: no title "
                f"is available for field id(s) {sorted(set(unnamed))}. Pass the form "
                "structure (form['fields'] with 'id' and 'title') to transform()."
            )

        if not values:
            return {}

        if build_prerun_payload is None:
            raise RuntimeError(
                "The shared prerun encoder is unavailable, so kick-off values cannot "
                "be keyed by timeline_id and would be silently discarded by the API. "
                f"Original import error: {_ENCODER_IMPORT_ERROR}"
            )

        if not kickoff_fields:
            raise ValueError(
                "Cannot build prerun data without the target template's kick-off "
                "field definitions. Typeform field ids and titles are not Tallyfy "
                "timeline_ids, so the API would accept the launch and discard every "
                "value. Fetch them with shared.kickoff_fields.KickoffFieldCache and "
                "pass them as kickoff_fields."
            )

        return build_prerun_payload(values, kickoff_fields, strict=True)
    
    def _extract_answer_value(self, answer: Dict[str, Any], field_type: str) -> Optional[str]:
        """Extract value from answer based on type"""
        
        if field_type == 'text':
            return answer.get('text')
        
        elif field_type == 'email':
            return answer.get('email')
        
        elif field_type == 'number':
            num = answer.get('number')
            return str(num) if num is not None else None
        
        elif field_type == 'boolean':
            val = answer.get('boolean')
            return 'yes' if val else 'no' if val is not None else None
        
        elif field_type == 'choice':
            choice = answer.get('choice')
            if choice:
                return choice.get('label', choice.get('ref', ''))
            return None
        
        elif field_type == 'choices':
            choices = answer.get('choices', {})
            if choices:
                labels = choices.get('labels', [])
                refs = choices.get('refs', [])
                return ', '.join(labels) if labels else ', '.join(refs)
            return None
        
        elif field_type == 'date':
            return answer.get('date')
        
        elif field_type == 'url':
            return answer.get('url')
        
        elif field_type == 'phone_number':
            return answer.get('phone_number')
        
        elif field_type == 'file_url':
            file_url = answer.get('file_url')
            if file_url:
                return json.dumps({'url': file_url, 'type': 'file'})
            return None
        
        elif field_type == 'payment':
            payment = answer.get('payment')
            if payment:
                return json.dumps({
                    'amount': payment.get('amount'),
                    'status': payment.get('status'),
                    'payment_id': payment.get('id')
                })
            return None
        
        else:
            # Try to extract any value
            for key in ['text', 'value', 'label', 'ref']:
                if key in answer:
                    return str(answer[key])
            
            # If complex object, serialize it
            if isinstance(answer, dict) and len(answer) > 2:
                # Remove field metadata
                clean_answer = {k: v for k, v in answer.items() if k != 'field'}
                if clean_answer:
                    return json.dumps(clean_answer)
            
            return None
    
    def _get_respondent_info(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract respondent information"""
        metadata = response.get('metadata', {})
        hidden = response.get('hidden', {})
        
        respondent = {
            'name': 'Anonymous',
            'email': None,
            'user_agent': metadata.get('user_agent'),
            'platform': metadata.get('platform'),
            'referer': metadata.get('referer'),
            'network_id': metadata.get('network_id'),
            'browser': metadata.get('browser')
        }
        
        # Check for email in hidden fields
        if 'email' in hidden:
            respondent['email'] = hidden['email']
            respondent['name'] = hidden['email'].split('@')[0]
        
        # Check for name in hidden fields
        if 'name' in hidden:
            respondent['name'] = hidden['name']
        
        # Check for user ID
        if 'user_id' in hidden:
            respondent['user_id'] = hidden['user_id']
        
        return respondent
    
    def transform_batch(self, responses: List[Dict[str, Any]], blueprint_id: str,
                       form_structure: Optional[Dict[str, Any]] = None,
                       kickoff_fields: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Transform multiple responses"""
        processes = []
        
        for response in responses:
            try:
                process = self.transform(response, blueprint_id, form_structure, kickoff_fields)
                processes.append(process)
            except Exception as e:
                logger.error(f"Failed to transform response {response.get('response_id')}: {e}")
        
        logger.info(f"Transformed {len(processes)} responses to processes")
        return processes
    
    def analyze_response_patterns(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response patterns for insights"""
        analysis = {
            'total_responses': len(responses),
            'completion_rate': 0,
            'average_completion_time': 0,
            'common_dropoff_points': [],
            'popular_choices': {},
            'submission_patterns': {}
        }
        
        completed_count = 0
        total_time = 0
        time_count = 0
        
        for response in responses:
            # Completion rate
            if response.get('completed'):
                completed_count += 1
            
            # Completion time
            metadata = response.get('metadata', {})
            if metadata.get('browser'):
                try:
                    # Browser field sometimes contains time data
                    time_data = metadata['browser']
                    if isinstance(time_data, (int, float)):
                        total_time += time_data
                        time_count += 1
                except:
                    pass
            
            # Track answer patterns
            for answer in response.get('answers', []):
                field_id = answer.get('field', {}).get('id')
                if answer.get('type') == 'choice':
                    choice = answer.get('choice', {}).get('label')
                    if choice:
                        if field_id not in analysis['popular_choices']:
                            analysis['popular_choices'][field_id] = {}
                        analysis['popular_choices'][field_id][choice] = \
                            analysis['popular_choices'][field_id].get(choice, 0) + 1
        
        # Calculate rates
        if responses:
            analysis['completion_rate'] = (completed_count / len(responses)) * 100
        
        if time_count > 0:
            analysis['average_completion_time'] = total_time / time_count
        
        return analysis
    
    def map_partial_response(self, response: Dict[str, Any], blueprint_id: str) -> Dict[str, Any]:
        """Handle partial/incomplete responses"""
        
        # Use AI to determine how to handle partial data if available
        if self.ai_client and self.ai_client.enabled:
            strategy = self.ai_client.handle_partial_response({
                'response': response,
                'completion_percentage': self._calculate_completion(response)
            })
            
            if strategy and strategy.get('confidence', 0) > 0.7:
                if strategy['action'] == 'create_draft':
                    process = self.transform(response, blueprint_id)
                    process['status'] = 'draft'
                    process['metadata']['partial'] = True
                    return process
                elif strategy['action'] == 'skip':
                    return None
        
        # Fallback: Create draft if >50% complete
        if self._calculate_completion(response) > 50:
            process = self.transform(response, blueprint_id)
            process['status'] = 'draft'
            process['metadata']['partial'] = True
            return process
        
        return None
    
    def _calculate_completion(self, response: Dict[str, Any]) -> float:
        """Calculate response completion percentage"""
        if response.get('completed'):
            return 100.0
        
        # Estimate based on answered questions
        answers = response.get('answers', [])
        if not answers:
            return 0.0
        
        # This is an estimate as we don't know total questions
        # Assume average form has 20 questions
        estimated_total = 20
        return min((len(answers) / estimated_total) * 100, 95)