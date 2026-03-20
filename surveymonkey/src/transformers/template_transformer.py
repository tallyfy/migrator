"""
SurveyMonkey Template Transformer
Transforms SurveyMonkey surveys to Tallyfy blueprints
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateTransformer:
    """Transform SurveyMonkey surveys to Tallyfy blueprints"""

    def __init__(self, field_transformer, ai_client: Optional[Any] = None):
        """Initialize template transformer"""
        self.field_transformer = field_transformer
        self.ai_client = ai_client
        logger.info("SurveyMonkey template transformer initialized")

    def transform(self, survey: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SurveyMonkey survey to Tallyfy blueprint"""

        # Extract survey metadata
        survey_id = survey.get('id', '')
        title = survey.get('title', 'Untitled Survey')
        pages = survey.get('pages', [])

        # Collect all questions across pages
        all_questions = []
        for page in pages:
            all_questions.extend(page.get('questions', []))

        # Assess survey complexity
        complexity = self._assess_complexity(survey, all_questions)

        logger.info(f"Transforming SurveyMonkey '{title}' with {len(all_questions)} questions across {len(pages)} pages, complexity: {complexity}")

        if complexity == 'simple':
            return self._create_simple_blueprint(survey, all_questions)
        elif complexity == 'medium':
            return self._create_page_based_blueprint(survey)
        else:
            return self._create_complex_blueprint(survey, all_questions)

    def _assess_complexity(self, survey: Dict[str, Any],
                          all_questions: List[Dict[str, Any]]) -> str:
        """Assess survey complexity for transformation strategy"""
        pages = survey.get('pages', [])
        question_count = len(all_questions)
        page_count = len(pages)

        # Check for complex features
        has_logic = self._has_page_logic(survey)
        has_piping = self._has_piping(all_questions)
        has_matrix = any(q.get('family') == 'matrix' for q in all_questions)
        has_ranking = any(q.get('family') == 'ranking' for q in all_questions)

        # Use AI if available
        if self.ai_client and self.ai_client.enabled:
            context = {
                'question_count': question_count,
                'page_count': page_count,
                'has_logic': has_logic,
                'has_piping': has_piping,
                'has_matrix': has_matrix,
                'has_ranking': has_ranking,
                'survey_title': survey.get('title', ''),
                'vendor': 'surveymonkey'
            }

            result = self.ai_client.make_decision('analyze_survey_complexity.txt', context)
            if result and result.get('confidence', 0) > 0.7:
                return result.get('complexity', 'medium')

        # Fallback heuristics
        if question_count <= 15 and page_count <= 2 and not has_logic:
            return 'simple'
        elif question_count <= 30 or (page_count <= 5 and not has_logic):
            return 'medium'
        else:
            return 'complex'

    def _create_simple_blueprint(self, survey: Dict[str, Any],
                                all_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create simple blueprint with kickoff form"""

        # Transform all questions to fields
        tallyfy_fields = self.field_transformer.transform_batch(all_questions)

        blueprint = {
            'name': survey.get('title', 'Untitled Survey'),
            'description': self._get_survey_description(survey),
            'metadata': {
                'source': 'surveymonkey',
                'surveymonkey_id': survey.get('id'),
                'survey_category': survey.get('category', ''),
                'date_created': survey.get('date_created'),
                'date_modified': survey.get('date_modified'),
                'response_count': survey.get('response_count', 0),
                'question_count': len(all_questions),
                'page_count': len(survey.get('pages', [])),
                'complexity': 'simple'
            },
            'kickoff_form': {
                'fields': tallyfy_fields
            },
            'steps': [
                {
                    'name': 'Review Submission',
                    'type': 'task',
                    'description': 'Review the survey submission and verify all data',
                    'assigned_to': 'process_owner'
                },
                {
                    'name': 'Process Response',
                    'type': 'task',
                    'description': 'Process the submission according to business rules',
                    'assigned_to': 'process_owner'
                }
            ]
        }

        return blueprint

    def _create_page_based_blueprint(self, survey: Dict[str, Any]) -> Dict[str, Any]:
        """Create blueprint using SurveyMonkey pages as steps"""
        pages = survey.get('pages', [])

        blueprint = {
            'name': survey.get('title', 'Untitled Survey'),
            'description': self._get_survey_description(survey),
            'metadata': {
                'source': 'surveymonkey',
                'surveymonkey_id': survey.get('id'),
                'question_count': sum(len(p.get('questions', [])) for p in pages),
                'page_count': len(pages),
                'complexity': 'medium'
            },
            'steps': []
        }

        # Create a step for each survey page
        for idx, page in enumerate(pages):
            page_questions = page.get('questions', [])

            # Skip empty pages
            if not page_questions:
                continue

            page_fields = self.field_transformer.transform_batch(page_questions)

            step = {
                'name': page.get('title', '') or f'Page {idx + 1}',
                'type': 'form',
                'description': page.get('description', ''),
                'form_fields': page_fields,
                'assigned_to': 'process_owner'
            }
            blueprint['steps'].append(step)

        # Add processing steps
        blueprint['steps'].extend([
            {
                'name': 'Validate Submission',
                'type': 'approval',
                'description': 'Validate all submitted data for completeness and accuracy',
                'assigned_to': 'manager'
            },
            {
                'name': 'Process Data',
                'type': 'task',
                'description': 'Process the validated submission',
                'assigned_to': 'process_owner'
            }
        ])

        return blueprint

    def _create_complex_blueprint(self, survey: Dict[str, Any],
                                 all_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create complex multi-step workflow"""
        pages = survey.get('pages', [])

        # Use AI to determine optimal grouping if available
        if self.ai_client and self.ai_client.enabled:
            field_groups = self.ai_client.make_decision('optimize_page_transformation.txt', {
                'pages': [{'title': p.get('title', ''), 'question_count': len(p.get('questions', []))} for p in pages],
                'total_questions': len(all_questions),
                'survey_title': survey.get('title', ''),
                'page_count': len(pages),
                'avg_questions_per_page': len(all_questions) / max(len(pages), 1)
            })

            if field_groups and field_groups.get('confidence', 0) > 0.7:
                groups = self._apply_ai_grouping(pages, field_groups)
            else:
                groups = self._intelligent_question_grouping(pages, all_questions)
        else:
            groups = self._intelligent_question_grouping(pages, all_questions)

        blueprint = {
            'name': survey.get('title', 'Untitled Survey'),
            'description': self._get_survey_description(survey),
            'metadata': {
                'source': 'surveymonkey',
                'surveymonkey_id': survey.get('id'),
                'question_count': len(all_questions),
                'page_count': len(pages),
                'step_count': len(groups),
                'complexity': 'complex',
                'has_logic': self._has_page_logic(survey),
                'has_piping': self._has_piping(all_questions)
            },
            'steps': []
        }

        # Create steps for each group
        for group in groups:
            group_fields = self.field_transformer.transform_batch(group['questions'])

            step = {
                'name': group['name'],
                'type': 'form',
                'description': group.get('description', ''),
                'form_fields': group_fields,
                'assigned_to': 'process_owner'
            }
            blueprint['steps'].append(step)

            # Add validation step if needed
            if group.get('requires_validation'):
                blueprint['steps'].append({
                    'name': f"Validate {group['name']}",
                    'type': 'approval',
                    'description': f"Validate {group['name']} data before proceeding",
                    'assigned_to': 'manager'
                })

        # Add final processing steps
        blueprint['steps'].extend([
            {
                'name': 'Final Review',
                'type': 'approval',
                'description': 'Final review of all submitted data',
                'assigned_to': 'manager'
            },
            {
                'name': 'Complete Processing',
                'type': 'task',
                'description': 'Complete final processing and archival',
                'assigned_to': 'process_owner'
            }
        ])

        return blueprint

    def _intelligent_question_grouping(self, pages: List[Dict[str, Any]],
                                       all_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Intelligently group questions for complex surveys"""
        groups = []

        # First, try to use page boundaries
        for page in pages:
            page_questions = page.get('questions', [])
            if not page_questions:
                continue

            page_title = page.get('title', '')

            # If page has more than 15 questions, split it
            if len(page_questions) > 15:
                # Categorize questions within the page
                sub_groups = self._categorize_questions(page_questions, page_title)
                groups.extend(sub_groups)
            else:
                groups.append({
                    'name': page_title or f'Section {len(groups) + 1}',
                    'description': page.get('description', ''),
                    'questions': page_questions,
                    'requires_validation': len(page_questions) > 10
                })

        return groups

    def _categorize_questions(self, questions: List[Dict[str, Any]],
                             page_title: str) -> List[Dict[str, Any]]:
        """Categorize questions into logical groups"""
        groups = []

        # Categorize by question type/content
        demographic_questions = []
        choice_questions = []
        text_questions = []
        matrix_questions = []
        other_questions = []

        for question in questions:
            family = question.get('family', '')
            heading = question.get('headings', [{}])[0].get('heading', '').lower()

            if family == 'demographic':
                demographic_questions.append(question)
            elif family in ['single_choice', 'multiple_choice', 'dropdown', 'image_choice']:
                choice_questions.append(question)
            elif family in ['open_ended']:
                text_questions.append(question)
            elif family in ['matrix', 'ranking']:
                matrix_questions.append(question)
            else:
                other_questions.append(question)

        # Create groups from categories
        if demographic_questions:
            groups.append({
                'name': f'{page_title} - Demographics' if page_title else 'Demographics',
                'questions': demographic_questions,
                'requires_validation': True
            })

        if choice_questions:
            # Split choice questions into chunks of 10
            for i in range(0, len(choice_questions), 10):
                chunk = choice_questions[i:i+10]
                suffix = f' ({i//10 + 1})' if len(choice_questions) > 10 else ''
                groups.append({
                    'name': f'{page_title} - Selections{suffix}' if page_title else f'Selections{suffix}',
                    'questions': chunk,
                    'requires_validation': False
                })

        if text_questions:
            groups.append({
                'name': f'{page_title} - Open Responses' if page_title else 'Open Responses',
                'questions': text_questions,
                'requires_validation': False
            })

        if matrix_questions:
            groups.append({
                'name': f'{page_title} - Ratings' if page_title else 'Ratings',
                'questions': matrix_questions,
                'requires_validation': False
            })

        if other_questions:
            groups.append({
                'name': f'{page_title} - Additional' if page_title else 'Additional Questions',
                'questions': other_questions,
                'requires_validation': False
            })

        return groups

    def _apply_ai_grouping(self, pages: List[Dict[str, Any]],
                          ai_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply AI-suggested grouping"""
        # Flatten all questions
        all_questions = []
        for page in pages:
            all_questions.extend(page.get('questions', []))

        suggested_groups = ai_result.get('groups', [])
        groups = []

        for suggestion in suggested_groups:
            # Get questions for this group based on indices
            start = suggestion.get('start_index', 0)
            end = suggestion.get('end_index', len(all_questions))
            group_questions = all_questions[start:end]

            if group_questions:
                groups.append({
                    'name': suggestion.get('name', f'Section {len(groups) + 1}'),
                    'description': suggestion.get('description', ''),
                    'questions': group_questions,
                    'requires_validation': suggestion.get('requires_validation', False)
                })

        # If AI grouping produced no results, fall back
        if not groups:
            return self._intelligent_question_grouping(pages, all_questions)

        return groups

    def _has_page_logic(self, survey: Dict[str, Any]) -> bool:
        """Check if survey has page skip logic"""
        for page in survey.get('pages', []):
            # SurveyMonkey stores logic at the question level
            for question in page.get('questions', []):
                if question.get('sorting'):
                    return True
                # Check for skip logic in validation
                if question.get('validation', {}).get('type') == 'skip_logic':
                    return True
        return False

    def _has_piping(self, questions: List[Dict[str, Any]]) -> bool:
        """Check if survey uses piping (variable substitution)"""
        for question in questions:
            headings = question.get('headings', [])
            for heading in headings:
                text = heading.get('heading', '')
                # SurveyMonkey piping uses {{Q1}} syntax
                if '{{' in text and '}}' in text:
                    return True
        return False

    def _get_survey_description(self, survey: Dict[str, Any]) -> str:
        """Extract survey description"""
        # Try custom variables or survey-level description
        custom_variables = survey.get('custom_variables', {})

        # Check first page for intro text
        pages = survey.get('pages', [])
        if pages:
            first_page = pages[0]
            description = first_page.get('description', '')
            if description:
                return description

            # Check for presentation/text questions on first page
            for question in first_page.get('questions', []):
                if question.get('family') == 'presentation':
                    headings = question.get('headings', [])
                    if headings:
                        return headings[0].get('heading', '')

        # Fallback to survey title
        return survey.get('title', '')

    def transform_batch(self, surveys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple surveys"""
        blueprints = []

        for survey in surveys:
            try:
                blueprint = self.transform(survey)
                blueprints.append(blueprint)
                logger.info(f"Successfully transformed survey '{survey.get('title')}'")
            except Exception as e:
                logger.error(f"Failed to transform survey '{survey.get('title')}': {e}")

        return blueprints
