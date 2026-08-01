"""Tests for the SurveyMonkey field transformer.

This vendor shipped with no tests at all, which is why the crash below
survived: `transform()` is the only entry point the orchestrator uses, and
nothing had ever called it.
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The transformer imports a module that pulls in the Anthropic SDK, but none of
# the logic under test touches it -- and the no-key path is the one most
# migrations actually run.
if 'anthropic' not in sys.modules:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        _stub = types.ModuleType('anthropic')
        _stub.Anthropic = object
        _stub.APIError = Exception
        sys.modules['anthropic'] = _stub

from src.transformers.field_transformer import FieldTransformer


def question(**overrides):
    base = {
        'id': 'q1',
        'family': 'single_choice',
        'subtype': 'vertical',
        'headings': [{'heading': 'Pick one'}],
        'answers': {'choices': [{'id': 'a', 'text': 'A'}, {'id': 'b', 'text': 'B'}]},
    }
    base.update(overrides)
    return base


class TestRequiredFlag(unittest.TestCase):
    """`required` arrives as an object, or as null. Both are normal."""

    def setUp(self):
        self.transformer = FieldTransformer()

    def test_a_null_required_does_not_crash(self):
        """Regression: this raised AttributeError on every optional question.

        SurveyMonkey sends `"required": null` for a question that is not
        required. The code read

            question.get('required', {}).get('text', '')

        and a `.get` default only applies when the key is ABSENT -- a present
        null still returns None, so this was None.get('text').

        The proof it was wrong is 150 lines below in the same file, where
        `_build_validation_rules` does `if required and required.get('text')`.
        One of the two had to be wrong, and it was this one.
        """
        result = self.transformer.transform(question(required=None))

        self.assertFalse(result['required'])

    def test_a_required_question_is_marked_required(self):
        result = self.transformer.transform(
            question(required={'text': 'This question requires an answer'})
        )

        self.assertTrue(result['required'])

    def test_an_absent_required_key_is_not_required(self):
        result = self.transformer.transform(question())

        self.assertFalse(result['required'])

    def test_an_empty_required_text_is_not_required(self):
        result = self.transformer.transform(question(required={'text': ''}))

        self.assertFalse(result['required'])


class TestFieldShape(unittest.TestCase):
    """Whatever the question, the output must be a field Tallyfy will accept."""

    def setUp(self):
        self.transformer = FieldTransformer()

    def test_output_field_type_is_one_the_api_accepts(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, repo_root)
        from shared.capture_shapes import CAPTURE_FIELD_TYPES

        for family, subtype in [
            ('single_choice', 'vertical'),
            ('multiple_choice', 'vertical'),
            ('open_ended', 'single'),
            ('open_ended', 'essay'),
            ('datetime', 'date_only'),
            ('made_up_family', 'made_up_subtype'),
        ]:
            with self.subTest(family=family, subtype=subtype):
                result = self.transformer.transform(
                    question(family=family, subtype=subtype, required=None)
                )
                self.assertIn(
                    result['type'], CAPTURE_FIELD_TYPES,
                    f'{family}:{subtype} produced {result["type"]!r}, which '
                    f'CreateCaptureRequest rejects with a 422'
                )

    def test_an_unknown_type_falls_back_rather_than_raising(self):
        result = self.transformer.transform(
            question(family='not_a_real_family', subtype='nope', required=None)
        )

        self.assertEqual(result['type'], 'text')


if __name__ == '__main__':
    unittest.main()
