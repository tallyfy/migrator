"""
Tests for the pipe's start form, which becomes the template's kick-off fields.

`PhaseToStepTransformer._transform_start_form_fields` used to name its result
list `field` and then reuse `field` as the loop variable. Each pass replaced the
list with the transformed field dict, `field.append(field)` raised
AttributeError on that dict, the error was logged as a warning, and the method
returned the last field dict instead of a list. The orchestrator then found a
dict where it expected a list and dropped every kick-off field
(tallyfy/migrator#30, item 11).

The data below has the shape the `FieldFields` fragment in
`src/api/pipefy_client.py` asks Pipefy for: id, label, description, type,
required, editable, options, help, minimal_view and custom_validation.
"""

import os
import sys

PIPEFY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PIPEFY_ROOT)
for entry in (PIPEFY_ROOT, REPO_ROOT):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from src.transformers.phase_transformer import PhaseToStepTransformer  # noqa: E402
from shared.capture_shapes import normalize_captures  # noqa: E402


START_FORM_FIELDS = [
    {
        'id': 'company_name',
        'label': 'Company name',
        'description': 'Legal name of the customer',
        'type': 'short_text',
        'required': True,
        'editable': True,
        'options': [],
        'help': '',
        'minimal_view': True,
        'custom_validation': None,
    },
    {
        'id': 'contact_email',
        'label': 'Contact email',
        'description': '',
        'type': 'email',
        'required': True,
        'editable': True,
        'options': [],
        'help': 'We send the welcome pack here',
        'minimal_view': False,
        'custom_validation': None,
    },
    {
        'id': 'plan',
        'label': 'Plan',
        'description': '',
        'type': 'radio_vertical',
        'required': False,
        'editable': True,
        'options': ['Starter', 'Growth', 'Enterprise'],
        'help': '',
        'minimal_view': False,
        'custom_validation': None,
    },
]

PIPE = {
    'id': '301234567',
    'name': 'Customer onboarding',
    'description': 'From signed contract to first value',
    'public': False,
    'icon': 'sales',
    'color': '#4A90E2',
    'anyone_can_create_card': False,
    'expiration_time_by_unit': 5,
    'expiration_unit': 'days',
    'start_form_fields': START_FORM_FIELDS,
    'phases': [
        {
            'id': '318000001',
            'name': 'Kickoff call',
            'index': 0,
            'done': False,
            'fields': [],
            'cards_can_be_moved_to_phases': [{'id': '318000002', 'name': 'Done'}],
        },
        {
            'id': '318000002',
            'name': 'Done',
            'index': 1,
            'done': True,
            'fields': [],
            'cards_can_be_moved_to_phases': [],
        },
    ],
    'labels': [{'id': '30001', 'name': 'Priority', 'color': '#FF0000'}],
    'members': [
        {'user': {'id': '10001', 'email': 'owner@example.com', 'name': 'Pat Owner'},
         'role_name': 'admin'},
    ],
}


class TestStartFormFields:

    def test_returns_one_transformed_field_per_start_form_field(self):
        result = PhaseToStepTransformer()._transform_start_form_fields(START_FORM_FIELDS)

        assert isinstance(result, list), (
            f'expected a list of fields, got {type(result).__name__}: {result!r}'
        )
        assert [f['label'] for f in result] == ['Company name', 'Contact email', 'Plan']
        assert [f['external_ref'] for f in result] == ['company_name', 'contact_email', 'plan']
        assert [f['type'] for f in result] == ['text', 'email', 'radio']
        assert [f['is_required'] for f in result] == [True, True, False]

    def test_every_field_is_marked_as_a_start_form_field(self):
        result = PhaseToStepTransformer()._transform_start_form_fields(START_FORM_FIELDS)

        assert len(result) == 3
        for field in result:
            assert field['metadata']['is_start_form'] is True
            # The transformer's own metadata survives beside the new flag.
            assert field['metadata']['original_type'] in ('short_text', 'email', 'radio_vertical')

    def test_radio_options_are_kept(self):
        result = PhaseToStepTransformer()._transform_start_form_fields(START_FORM_FIELDS)

        plan = [f for f in result if f['external_ref'] == 'plan']
        assert len(plan) == 1
        assert [o['label'] for o in plan[0]['config']['options']] == ['Starter', 'Growth', 'Enterprise']

    def test_no_start_form_gives_an_empty_list(self):
        assert PhaseToStepTransformer()._transform_start_form_fields([]) == []


class TestPipeToChecklistKickoffFields:
    """The orchestrator pops `field` off the checklist and sends it as `prerun`."""

    def test_checklist_carries_the_start_form_as_a_list(self):
        checklist = PhaseToStepTransformer().transform_pipe_to_checklist(PIPE)

        start_form = checklist['field']
        assert isinstance(start_form, list), (
            f'checklist field must be a list, got {type(start_form).__name__}; '
            'the orchestrator drops a non-list and every kick-off field is lost'
        )
        assert [f['label'] for f in start_form] == ['Company name', 'Contact email', 'Plan']

    def test_start_form_normalises_into_a_prerun_array(self):
        checklist = PhaseToStepTransformer().transform_pipe_to_checklist(PIPE)

        # build_prerun_fields on the client delegates to normalize_captures.
        prerun = normalize_captures(checklist['field'])

        assert [p['label'] for p in prerun] == ['Company name', 'Contact email', 'Plan']
        assert [p['field_type'] for p in prerun] == ['text', 'email', 'radio']
        assert [p['required'] for p in prerun] == [True, True, False]
        assert [o['text'] for o in prerun[2]['options']] == ['Starter', 'Growth', 'Enterprise']
        assert [p['position'] for p in prerun] == [1, 2, 3]
