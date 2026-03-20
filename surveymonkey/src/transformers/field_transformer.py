"""
SurveyMonkey Field Transformer
Transforms SurveyMonkey question types to Tallyfy fields
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class FieldTransformer:
    """Transform SurveyMonkey questions to Tallyfy fields"""

    def __init__(self, ai_client: Optional[Any] = None):
        """Initialize field transformer"""
        self.ai_client = ai_client

        # SurveyMonkey question family/subtype to Tallyfy field type mappings
        # SurveyMonkey questions have a 'family' and 'subtype' structure
        self.type_map = {
            # Single choice questions
            'single_choice': 'radio',
            'single_choice:vertical': 'radio',
            'single_choice:horiz': 'radio',
            'single_choice:menu': 'dropdown',

            # Multiple choice questions
            'multiple_choice': 'multiselect',
            'multiple_choice:vertical': 'multiselect',

            # Dropdown
            'dropdown': 'dropdown',

            # Open-ended text
            'open_ended': 'text',
            'open_ended:single': 'text',
            'open_ended:multi': 'textarea',
            'open_ended:essay': 'textarea',
            'open_ended:numerical': 'text',  # With numeric validation

            # Matrix / rating scale
            'matrix': 'textarea',       # Flattened as text
            'matrix:single': 'textarea',
            'matrix:multi': 'textarea',
            'matrix:rating': 'textarea',
            'matrix:menu': 'textarea',

            # Ranking
            'ranking': 'textarea',      # Serialized as ordered text

            # Demographic
            'demographic': 'text',      # Multiple fields generated

            # DateTime
            'datetime': 'date',
            'datetime:date': 'date',
            'datetime:time': 'text',
            'datetime:both': 'text',    # Combined date/time as text

            # File upload
            'file_upload': 'file',

            # Slider / star rating
            'slider': 'text',           # Numeric value as text
            'slider:star_rating': 'text',

            # Presentation / text elements (non-input)
            'presentation': None,       # Skip display-only elements
            'presentation:text': None,
            'presentation:image': None,
            'presentation:descriptive_text': None,

            # Image choice
            'image_choice': 'radio',
            'image_choice:single_answer': 'radio',
            'image_choice:multi_answer': 'multiselect',
        }

        logger.info("SurveyMonkey field transformer initialized")

    def transform(self, question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform single SurveyMonkey question to Tallyfy field"""
        family = question.get('family', '')
        subtype = question.get('subtype', '')

        # Build lookup key: try family:subtype first, then family alone
        lookup_key = f"{family}:{subtype}" if subtype else family
        tallyfy_type = self.type_map.get(lookup_key)

        # Fallback to family-only lookup
        if tallyfy_type is None and lookup_key != family:
            tallyfy_type = self.type_map.get(family)

        # Skip presentation/display-only elements
        if tallyfy_type is None and family in ['presentation']:
            return None

        # Default to text for unknown types
        if tallyfy_type is None:
            tallyfy_type = 'text'
            logger.warning(f"Unknown question type '{family}:{subtype}', defaulting to text")

        # Build base field
        tallyfy_field = {
            'type': tallyfy_type,
            'label': self._clean_heading(question.get('headings', [{}])[0].get('heading', 'Untitled Question')),
            'name': f"field_{question.get('id', '')}",
            'required': question.get('required', {}).get('text', '') != '',
            'help_text': question.get('headings', [{}])[0].get('description', ''),
            'metadata': {
                'surveymonkey_id': question.get('id'),
                'surveymonkey_family': family,
                'surveymonkey_subtype': subtype,
                'surveymonkey_position': question.get('position')
            }
        }

        # Handle choice-based questions (single_choice, multiple_choice, dropdown)
        if family in ['single_choice', 'multiple_choice', 'dropdown', 'image_choice']:
            answers = question.get('answers', {})
            choices = answers.get('choices', []) or answers.get('rows', [])
            tallyfy_field['options'] = self._transform_choices(choices)

            # Handle "other" option
            other = answers.get('other', {})
            if other and other.get('is_answer_choice'):
                tallyfy_field['options'].append({
                    'value': 'other',
                    'label': other.get('text', 'Other')
                })

        # Handle matrix questions
        if family == 'matrix':
            answers = question.get('answers', {})
            rows = answers.get('rows', [])
            choices = answers.get('choices', [])

            tallyfy_field['help_text'] = self._format_matrix_help(rows, choices)
            tallyfy_field['metadata']['matrix_rows'] = len(rows)
            tallyfy_field['metadata']['matrix_columns'] = len(choices)

        # Handle ranking questions
        if family == 'ranking':
            answers = question.get('answers', {})
            choices = answers.get('choices', [])
            tallyfy_field['help_text'] = 'Rank the following items in order of preference:\n' + \
                '\n'.join(f"- {c.get('text', '')}" for c in choices)

        # Handle demographic questions (generate multiple sub-fields)
        if family == 'demographic':
            tallyfy_field['metadata']['is_demographic'] = True
            tallyfy_field['metadata']['sub_fields'] = self._get_demographic_sub_fields(question)

        # Handle slider / star rating
        if family == 'slider':
            answers = question.get('answers', {})
            tallyfy_field['help_text'] = f"Scale: {answers.get('min', 0)} to {answers.get('max', 100)}"

        # Handle datetime
        if family == 'datetime':
            if subtype == 'both':
                tallyfy_field['help_text'] = 'Enter date and time'

        # Add validation rules
        tallyfy_field['validation'] = self._get_validation(family, subtype, question)

        return tallyfy_field

    def _clean_heading(self, heading: str) -> str:
        """Clean HTML from question heading"""
        if not heading:
            return 'Untitled Question'

        # Strip basic HTML tags
        import re
        clean = re.sub(r'<[^>]+>', '', heading)
        return clean.strip() or 'Untitled Question'

    def _transform_choices(self, choices: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Transform SurveyMonkey choices to Tallyfy options"""
        options = []

        for choice in choices:
            option = {
                'value': str(choice.get('id', choice.get('text', ''))),
                'label': choice.get('text', '')
            }

            # Note if choice has image
            if choice.get('image'):
                option['metadata'] = {'has_image': True, 'image_url': choice['image'].get('url')}

            options.append(option)

        return options

    def _format_matrix_help(self, rows: List[Dict], choices: List[Dict]) -> str:
        """Format matrix question as help text for textarea"""
        lines = ['Matrix question - please provide answers for each row:']
        row_labels = [r.get('text', f'Row {i+1}') for i, r in enumerate(rows)]
        col_labels = [c.get('text', f'Column {i+1}') for i, c in enumerate(choices)]

        lines.append(f"Columns: {', '.join(col_labels)}")
        for label in row_labels:
            lines.append(f"- {label}: [your answer]")

        return '\n'.join(lines)

    def _get_demographic_sub_fields(self, question: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get sub-fields for demographic question"""
        answers = question.get('answers', {})
        rows = answers.get('rows', [])

        sub_fields = []
        for row in rows:
            row_type = row.get('type', 'text')
            sub_fields.append({
                'name': row.get('text', 'Field'),
                'type': 'text',
                'original_type': row_type
            })

        return sub_fields

    def _get_validation(self, family: str, subtype: str,
                       question: Dict[str, Any]) -> Optional[str]:
        """Get validation rules for field"""
        rules = []

        # Type-specific validation
        if family == 'open_ended' and subtype == 'numerical':
            rules.append('numeric')
            validation = question.get('validation', {})
            if validation.get('min'):
                rules.append(f"min:{validation['min']}")
            if validation.get('max'):
                rules.append(f"max:{validation['max']}")

        elif family == 'datetime':
            if subtype == 'date':
                rules.append('date')

        elif family == 'open_ended':
            validation = question.get('validation', {})
            if validation.get('type') == 'email':
                rules.append('email')
            elif validation.get('type') == 'integer':
                rules.append('numeric')
            elif validation.get('min_length'):
                rules.append(f"min:{validation['min_length']}")
            elif validation.get('max_length'):
                rules.append(f"max:{validation['max_length']}")

        # Required validation
        required = question.get('required', {})
        if required and required.get('text'):
            rules.append('required')

        return '|'.join(rules) if rules else None

    def transform_batch(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple questions"""
        transformed = []

        for question in questions:
            result = self.transform(question)
            if result:
                transformed.append(result)

        logger.info(f"Transformed {len(transformed)} fields from {len(questions)} SurveyMonkey questions")
        return transformed

    def analyze_field_complexity(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze question transformation complexity"""
        family = question.get('family', 'unknown')
        subtype = question.get('subtype', '')

        complexity = {
            'question_id': question.get('id'),
            'question_family': family,
            'question_subtype': subtype,
            'complexity': 'simple',
            'issues': []
        }

        # Check for complex features
        if family == 'matrix':
            answers = question.get('answers', {})
            rows = len(answers.get('rows', []))
            cols = len(answers.get('choices', []))
            if rows * cols > 20:
                complexity['complexity'] = 'complex'
                complexity['issues'].append(f'Large matrix ({rows}x{cols}) flattened to textarea')
            else:
                complexity['complexity'] = 'medium'
                complexity['issues'].append('Matrix question flattened to textarea')

        if family == 'ranking':
            choices = len(question.get('answers', {}).get('choices', []))
            if choices > 10:
                complexity['complexity'] = 'medium'
                complexity['issues'].append(f'Ranking with {choices} items serialized as text')

        if family == 'demographic':
            complexity['complexity'] = 'medium'
            complexity['issues'].append('Demographic split into multiple text fields')

        if family == 'file_upload':
            complexity['complexity'] = 'medium'
            complexity['issues'].append('File upload - size limits may apply')

        if family == 'slider':
            complexity['issues'].append('Slider converted to text input')

        if family == 'image_choice':
            complexity['issues'].append('Image choice labels only - images not displayed')

        return complexity
