"""A Google Form's items must reach the template transformer as steps.

main.py builds each template from a Google Form with the form's questions under
'items', the Forms API key. The template transformer read only 'steps' or
'tasks', so every migrated template came out with no steps at all
(tallyfy/migrator#30, item 10).

This drives main.py's own transformation phase rather than a copy of the dict it
builds, so it fails if either side drifts again.
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import main  # noqa: E402


# Shaped like main.py's discovery output for one form: a Drive files().list entry
# updated with the Forms API v1 forms().get body. The API leaves out empty fields,
# so the image item has no title at all.
FORM_ID = '1aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789fixture'
GOOGLE_FORM = {
    'id': FORM_ID,
    'name': 'Vendor onboarding',
    'createdTime': '2026-03-02T15:04:11.000Z',
    'modifiedTime': '2026-10-19T09:41:27.000Z',
    'formId': FORM_ID,
    'info': {
        'title': 'Vendor onboarding',
        'documentTitle': 'Vendor onboarding',
        'description': 'Tell us about your company before we set you up.',
    },
    'settings': {'quizSettings': {}},
    'revisionId': '00000031',
    'responderUri': 'https://docs.google.com/forms/d/e/1FAIpQLSc7tWq/viewform',
    'items': [
        {
            'itemId': '3b1c2a10',
            'title': 'Company name',
            'description': 'As it appears on your tax registration.',
            'questionItem': {
                'question': {
                    'questionId': '5f0e1d2c',
                    'required': True,
                    'textQuestion': {},
                }
            },
        },
        {
            'itemId': '6a7b8c9d',
            'title': 'How many employees do you have?',
            'questionItem': {
                'question': {
                    'questionId': '0c1d2e3f',
                    'required': True,
                    'choiceQuestion': {
                        'type': 'RADIO',
                        'options': [
                            {'value': '1 to 10'},
                            {'value': '11 to 50'},
                            {'value': 'More than 50'},
                        ],
                    },
                }
            },
        },
        {
            'itemId': '1e2f3a4b',
            'title': 'Banking details',
            'description': 'We pay every vendor by ACH.',
            'pageBreakItem': {},
        },
        {
            'itemId': '7c8d9e0f',
            'title': 'Preferred start date',
            'questionItem': {
                'question': {
                    'questionId': '4a5b6c7d',
                    'dateQuestion': {'includeYear': True},
                }
            },
        },
        {
            'itemId': '2b3c4d5e',
            'imageItem': {
                'image': {
                    'contentUri': 'https://lh7-rt.googleusercontent.com/formsz/AN7BsVA',
                    'properties': {'alignment': 'CENTER'},
                }
            },
        },
    ],
}


class _FieldTransformer(main.FieldTransformer):
    """main.py's FieldTransformer with its three inherited abstract methods filled.

    main.py calls FieldTransformer() directly, but the class inherits get_forms,
    get_form_details and get_form_responses from FormMigratorBase as abstract
    methods and cannot be instantiated. Filling them in lets the wiring below
    match main.py; it is not what this test is about.
    """

    def get_forms(self):
        return []

    def get_form_details(self, form_id):
        return {}

    def get_form_responses(self, form_id):
        return []


def _orchestrator():
    """The components main.py's _initialize_components wires, and no API clients."""
    template_transformer = main.TemplateTransformer()
    template_transformer.field_transformer = _FieldTransformer()
    return types.SimpleNamespace(
        template_transformer=template_transformer,
        instance_transformer=main.InstanceTransformer(),
        user_transformer=main.UserTransformer(),
    )


class TestFormItemsBecomeSteps(unittest.TestCase):

    def setUp(self):
        discovery = {'forms': [GOOGLE_FORM], 'responses': [], 'statistics': {}}
        result = main.GoogleFormsMigrationOrchestrator._run_transformation_phase(
            _orchestrator(), discovery, {}
        )
        self.assertEqual(len(result['templates']), 1)
        self.template = result['templates'][0]

    def test_template_is_not_the_fallback(self):
        self.assertEqual(self.template['name'], 'Vendor onboarding')
        self.assertEqual(
            self.template['description'],
            'Tell us about your company before we set you up.',
        )

    def test_every_item_becomes_a_step_in_order(self):
        self.assertEqual(
            [(s['name'], s['description']) for s in self.template['steps']],
            [
                ('Company name', 'As it appears on your tax registration.'),
                ('How many employees do you have?', ''),
                ('Banking details', 'We pay every vendor by ACH.'),
                ('Preferred start date', ''),
                ('Step 5', ''),
            ],
        )

    def test_steps_are_tasks_with_no_invented_assignee_or_deadline(self):
        self.assertEqual(len(self.template['steps']), len(GOOGLE_FORM['items']))
        for step in self.template['steps']:
            self.assertEqual(step['type'], 'task')
            self.assertIsNone(step['assignee'])
            self.assertIsNone(step['due_date'])


if __name__ == '__main__':
    unittest.main()
