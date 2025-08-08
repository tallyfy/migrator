"""
Typeform Instance Transformer
Transforms Typeform responses to Tallyfy processes
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform Typeform responses to Tallyfy processes"""
    
    def __init__(self, ai_client: Optional[Any] = None):
        """Initialize instance transformer"""
        self.ai_client = ai_client
        logger.info("Typeform instance transformer initialized")
    
    def transform(self, response: Dict[str, Any], blueprint_id: str, 
                 form_structure: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transform single Typeform response to Tallyfy process"""
        
        # Extract response metadata
        response_id = response.get('response_id', response.get('token', ''))
        submitted_at = response.get('submitted_at', response.get('landed_at'))
        
        # Extract answers
        answers = response.get('answers', [])
        prerun_data = self._extract_answers(answers, form_structure)
        
        # Get respondent info
        respondent = self._get_respondent_info(response)
        
        # Create process
        process = {
            'checklist_id': blueprint_id,
            'name': f"Response from {respondent['name']} - {response_id[:8]}",
            'prerun_data': prerun_data,
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
    
    def _extract_answers(self, answers: List[Dict[str, Any]], 
                        form_structure: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Extract answers as prerun data"""
        prerun_data = {}
        
        for answer in answers:
            field_id = answer.get('field', {}).get('id', '')
            field_ref = answer.get('field', {}).get('ref', '')
            field_type = answer.get('type', '')
            
            # Use field ID as key
            field_key = f"field_{field_id}"
            
            # Extract value based on answer type
            value = self._extract_answer_value(answer, field_type)
            
            if value is not None:
                prerun_data[field_key] = value
            
            # Also store by ref if available
            if field_ref:
                prerun_data[f"ref_{field_ref}"] = value
        
        return prerun_data
    
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
                       form_structure: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Transform multiple responses"""
        processes = []
        
        for response in responses:
            try:
                process = self.transform(response, blueprint_id, form_structure)
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