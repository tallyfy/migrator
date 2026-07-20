"""
SurveyMonkey Instance Transformer
Transforms SurveyMonkey survey responses to Tallyfy processes
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform SurveyMonkey responses to Tallyfy processes"""

    def __init__(self, ai_client: Optional[Any] = None):
        """Initialize instance transformer"""
        self.ai_client = ai_client
        logger.info("SurveyMonkey instance transformer initialized")

    def transform(self, response: Dict[str, Any], blueprint_id: str,
                 survey_structure: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transform single SurveyMonkey response to Tallyfy process"""

        # Extract response metadata
        response_id = response.get('id', '')
        date_created = response.get('date_created')
        date_modified = response.get('date_modified')

        # Build question ID to heading map from survey structure
        question_map = {}
        if survey_structure:
            for page in survey_structure.get('pages', []):
                for question in page.get('questions', []):
                    q_id = question.get('id')
                    heading = question.get('headings', [{}])[0].get('heading', '')
                    question_map[q_id] = {
                        'heading': heading,
                        'family': question.get('family', ''),
                        'subtype': question.get('subtype', '')
                    }

        # Extract answers from response pages
        prerun_data = {}
        for page in response.get('pages', []):
            for question in page.get('questions', []):
                question_id = question.get('id', '')
                field_key = f"field_{question_id}"

                answers = question.get('answers', [])
                value = self._extract_answer_value(answers, question_map.get(question_id, {}))

                if value is not None:
                    prerun_data[field_key] = value

        # Get respondent info
        respondent = self._get_respondent_info(response)

        # Create process
        process = {
            'checklist_id': blueprint_id,
            'name': f"Response from {respondent['name']} - {response_id[:8]}",
            'prerun': prerun_data,
            'metadata': {
                'source': 'surveymonkey',
                'surveymonkey_response_id': response_id,
                'date_created': date_created,
                'date_modified': date_modified,
                'response_status': response.get('response_status', 'completed'),
                'collection_mode': response.get('collection_mode'),
                'collector_id': response.get('collector_id'),
                'respondent': respondent,
                'ip_address': response.get('ip_address'),
                'total_time': response.get('total_time'),
                'logic_path': response.get('logic_path', {})
            }
        }

        # Add custom variables if present
        custom_variables = response.get('custom_variables', {})
        if custom_variables:
            process['metadata']['custom_variables'] = custom_variables

        return process

    def _extract_answer_value(self, answers: List[Dict[str, Any]],
                             question_info: Dict[str, Any]) -> Optional[str]:
        """Extract answer value from SurveyMonkey response answers

        SurveyMonkey answer structure varies by question type:
        - Single choice: [{"choice_id": "xxx", "text": "Option A"}]
        - Multiple choice: [{"choice_id": "xxx"}, {"choice_id": "yyy"}]
        - Open ended: [{"text": "user input"}]
        - Matrix: [{"row_id": "xxx", "choice_id": "yyy"}]
        - Ranking: [{"choice_id": "xxx", "rank": 1}]
        - Demographic: [{"row_id": "xxx", "text": "value"}]
        - File upload: [{"download_url": "https://..."}]
        """
        if not answers:
            return None

        family = question_info.get('family', '')

        # Single text answer
        if len(answers) == 1 and 'text' in answers[0] and not answers[0].get('choice_id') and not answers[0].get('row_id'):
            return answers[0]['text']

        # Single choice
        if family in ['single_choice', 'dropdown']:
            for answer in answers:
                if answer.get('text'):
                    return answer['text']
                elif answer.get('choice_id'):
                    return str(answer['choice_id'])
            return None

        # Multiple choice
        if family == 'multiple_choice':
            selected = []
            for answer in answers:
                if answer.get('text'):
                    selected.append(answer['text'])
                elif answer.get('choice_id'):
                    selected.append(str(answer['choice_id']))
            return ', '.join(selected) if selected else None

        # Open ended (single or multi-line)
        if family == 'open_ended':
            texts = [a.get('text', '') for a in answers if a.get('text')]
            return '\n'.join(texts) if texts else None

        # Matrix / rating
        if family == 'matrix':
            rows = []
            for answer in answers:
                row_id = answer.get('row_id', '')
                choice_text = answer.get('text', answer.get('choice_id', ''))
                rows.append(f"Row {row_id}: {choice_text}")
            return '\n'.join(rows) if rows else None

        # Ranking
        if family == 'ranking':
            ranked = sorted(answers, key=lambda a: a.get('rank', 0))
            items = []
            for answer in ranked:
                rank = answer.get('rank', '?')
                text = answer.get('text', answer.get('choice_id', ''))
                items.append(f"{rank}. {text}")
            return '\n'.join(items) if items else None

        # Demographic
        if family == 'demographic':
            parts = []
            for answer in answers:
                row_id = answer.get('row_id', '')
                text = answer.get('text', '')
                if text:
                    parts.append(f"{row_id}: {text}")
            return '\n'.join(parts) if parts else None

        # DateTime
        if family == 'datetime':
            for answer in answers:
                for key in ['text', 'date', 'value']:
                    if answer.get(key):
                        return answer[key]
            # Try constructing from row-based answers (month, day, year)
            parts = {}
            for answer in answers:
                row_id = answer.get('row_id', '')
                text = answer.get('text', '')
                parts[row_id] = text
            if parts:
                return json.dumps(parts)
            return None

        # File upload
        if family == 'file_upload':
            urls = []
            for answer in answers:
                if answer.get('download_url'):
                    urls.append(answer['download_url'])
            return json.dumps({'urls': urls}) if urls else None

        # Slider / star rating
        if family == 'slider':
            for answer in answers:
                if answer.get('text'):
                    return answer['text']
                elif 'weight' in answer:
                    return str(answer['weight'])
            return None

        # Image choice
        if family == 'image_choice':
            selected = []
            for answer in answers:
                if answer.get('text'):
                    selected.append(answer['text'])
                elif answer.get('choice_id'):
                    selected.append(str(answer['choice_id']))
            return ', '.join(selected) if selected else None

        # Fallback: try to extract any text values
        texts = []
        for answer in answers:
            for key in ['text', 'value', 'choice_id']:
                if answer.get(key):
                    texts.append(str(answer[key]))
                    break

        if texts:
            return ', '.join(texts)

        # Last resort: serialize the entire answer
        return json.dumps(answers) if answers else None

    def _get_respondent_info(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract respondent information"""
        respondent = {
            'name': 'Anonymous',
            'email': None,
            'ip_address': response.get('ip_address'),
            'collection_mode': response.get('collection_mode'),
            'total_time': response.get('total_time')
        }

        # Check custom variables for identifying info
        custom_vars = response.get('custom_variables', {})
        if 'email' in custom_vars:
            respondent['email'] = custom_vars['email']
            respondent['name'] = custom_vars['email'].split('@')[0]
        if 'name' in custom_vars:
            respondent['name'] = custom_vars['name']
        if 'first_name' in custom_vars:
            respondent['name'] = custom_vars.get('first_name', '')
            if 'last_name' in custom_vars:
                respondent['name'] += f" {custom_vars['last_name']}"

        # Check metadata for email collector data
        metadata = response.get('metadata', {})
        if metadata.get('respondent'):
            resp_meta = metadata['respondent']
            if resp_meta.get('email'):
                respondent['email'] = resp_meta['email']
            if resp_meta.get('first_name'):
                respondent['name'] = f"{resp_meta.get('first_name', '')} {resp_meta.get('last_name', '')}".strip()

        return respondent

    def transform_batch(self, responses: List[Dict[str, Any]], blueprint_id: str,
                       survey_structure: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Transform multiple responses"""
        processes = []

        for response in responses:
            try:
                process = self.transform(response, blueprint_id, survey_structure)
                processes.append(process)
            except Exception as e:
                logger.error(f"Failed to transform response {response.get('id')}: {e}")

        logger.info(f"Transformed {len(processes)} responses to processes")
        return processes

    def analyze_response_patterns(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze response patterns for insights"""
        analysis = {
            'total_responses': len(responses),
            'completion_rate': 0,
            'average_completion_time': 0,
            'status_distribution': {},
            'collection_mode_distribution': {},
            'date_range': {'earliest': None, 'latest': None}
        }

        completed_count = 0
        total_time = 0
        time_count = 0

        for response in responses:
            # Status distribution
            status = response.get('response_status', 'unknown')
            analysis['status_distribution'][status] = \
                analysis['status_distribution'].get(status, 0) + 1

            if status == 'completed':
                completed_count += 1

            # Collection mode distribution
            mode = response.get('collection_mode', 'unknown')
            analysis['collection_mode_distribution'][mode] = \
                analysis['collection_mode_distribution'].get(mode, 0) + 1

            # Completion time
            total_time_val = response.get('total_time')
            if total_time_val and isinstance(total_time_val, (int, float)):
                total_time += total_time_val
                time_count += 1

            # Date range
            date_created = response.get('date_created')
            if date_created:
                if not analysis['date_range']['earliest'] or date_created < analysis['date_range']['earliest']:
                    analysis['date_range']['earliest'] = date_created
                if not analysis['date_range']['latest'] or date_created > analysis['date_range']['latest']:
                    analysis['date_range']['latest'] = date_created

        # Calculate rates
        if responses:
            analysis['completion_rate'] = (completed_count / len(responses)) * 100

        if time_count > 0:
            analysis['average_completion_time'] = total_time / time_count

        return analysis

    def map_partial_response(self, response: Dict[str, Any], blueprint_id: str,
                            survey_structure: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Handle partial/incomplete responses"""

        response_status = response.get('response_status', 'completed')

        # Use AI to determine how to handle partial data if available
        if self.ai_client and self.ai_client.enabled:
            strategy = self.ai_client.make_decision('handle_partial_response.txt', {
                'response_status': response_status,
                'completion_percentage': self._calculate_completion(response, survey_structure),
                'total_time': response.get('total_time', 0)
            })

            if strategy and strategy.get('confidence', 0) > 0.7:
                if strategy['action'] == 'create_draft':
                    process = self.transform(response, blueprint_id, survey_structure)
                    process['status'] = 'draft'
                    process['metadata']['partial'] = True
                    return process
                elif strategy['action'] == 'skip':
                    return None

        # Fallback: Create draft if partially completed
        if response_status == 'partial':
            completion = self._calculate_completion(response, survey_structure)
            if completion > 50:
                process = self.transform(response, blueprint_id, survey_structure)
                process['status'] = 'draft'
                process['metadata']['partial'] = True
                return process

        return None

    def _calculate_completion(self, response: Dict[str, Any],
                             survey_structure: Optional[Dict[str, Any]] = None) -> float:
        """Calculate response completion percentage"""
        if response.get('response_status') == 'completed':
            return 100.0

        # Count answered questions
        answered = 0
        for page in response.get('pages', []):
            for question in page.get('questions', []):
                if question.get('answers'):
                    answered += 1

        # Get total questions from survey structure
        total_questions = 0
        if survey_structure:
            for page in survey_structure.get('pages', []):
                total_questions += len(page.get('questions', []))
        else:
            # Estimate
            total_questions = max(answered * 2, 20)

        return min((answered / max(total_questions, 1)) * 100, 95)
