"""
Tests for the Tallyfy kick-off ("prerun") value encoder.

These pin the API contract that the migrators were violating:
  * the request key is `prerun`, never `prerun_data`
  * its value is an OBJECT keyed by each field's timeline_id, never a list
  * per-field value shapes are type-dependent, and dropdown/radio differ
"""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prerun_encoder import (  # noqa: E402
    PRERUN_KEY,
    build_prerun_payload,
    encode_assignees_form,
    encode_field_value,
    normalize_prerun_object,
    resolve_capture,
)

TIMELINE_ID = 'a1b2c3d4e5f60718293a4b5c6d7e8f90'


def capture(field_type, **extra):
    """Build a minimal kick-off field definition."""
    definition = {
        'timeline_id': TIMELINE_ID,
        'id': 'local-id',
        'alias': 'my_field',
        'label': 'My Field',
        'field_type': field_type,
    }
    definition.update(extra)
    return definition


class TestRequestKey:
    """The API reads `prerun`; `prerun_data` is silently discarded."""

    def test_request_key_is_prerun(self):
        assert PRERUN_KEY == 'prerun'


class TestScalarFields:
    """text / textarea / date / email take a bare scalar."""

    @pytest.mark.parametrize('field_type', ['text', 'textarea', 'email'])
    def test_scalar_passthrough(self, field_type):
        assert encode_field_value('hello', capture(field_type)) == 'hello'

    def test_non_string_scalar_is_stringified(self):
        assert encode_field_value(42, capture('text')) == '42'

    def test_date_string_passes_through(self):
        value = '2026-03-11T09:30:00.000Z'
        assert encode_field_value(value, capture('date')) == value

    def test_datetime_is_rendered_iso8601(self):
        from datetime import datetime

        encoded = encode_field_value(datetime(2026, 3, 11, 9, 30, 0), capture('date'))
        assert encoded == '2026-03-11T09:30:00.000Z'
        assert isinstance(encoded, str)


class TestDropdownAndRadioAsymmetry:
    """dropdown needs {id, text}; radio needs the bare text. Do not harmonise."""

    OPTIONS = [{'id': 'opt1', 'text': 'Yes'}, {'id': 'opt2', 'text': 'No'}]

    def test_dropdown_returns_id_and_text_object(self):
        encoded = encode_field_value('Yes', capture('dropdown', options=self.OPTIONS))
        assert encoded == {'id': 'opt1', 'text': 'Yes'}

    def test_dropdown_matches_by_option_id_too(self):
        encoded = encode_field_value('opt2', capture('dropdown', options=self.OPTIONS))
        assert encoded == {'id': 'opt2', 'text': 'No'}

    def test_dropdown_unmatched_value_is_omitted(self):
        assert encode_field_value('Maybe', capture('dropdown', options=self.OPTIONS)) is None

    def test_radio_returns_bare_text_not_object(self):
        encoded = encode_field_value('Yes', capture('radio', options=self.OPTIONS))
        assert encoded == 'Yes'
        assert not isinstance(encoded, dict)

    def test_radio_resolves_an_id_to_its_text(self):
        assert encode_field_value('opt2', capture('radio', options=self.OPTIONS)) == 'No'


class TestMultiselect:
    """multiselect takes a list of {id, text} with `selected` set per item."""

    OPTIONS = [
        {'id': 'a', 'text': 'Alpha'},
        {'id': 'b', 'text': 'Beta'},
        {'id': 'c', 'text': 'Gamma'},
    ]

    def test_encodes_each_choice_as_an_object(self):
        encoded = encode_field_value(['Alpha', 'Gamma'], capture('multiselect', options=self.OPTIONS))
        assert encoded == [
            {'id': 'a', 'text': 'Alpha', 'selected': True},
            {'id': 'c', 'text': 'Gamma', 'selected': True},
        ]

    def test_single_value_is_accepted(self):
        encoded = encode_field_value('Beta', capture('multiselect', options=self.OPTIONS))
        assert encoded == [{'id': 'b', 'text': 'Beta', 'selected': True}]

    def test_unmatched_choices_are_dropped(self):
        encoded = encode_field_value(['Alpha', 'Nope'], capture('multiselect', options=self.OPTIONS))
        assert encoded == [{'id': 'a', 'text': 'Alpha', 'selected': True}]

    def test_capture_options_are_not_mutated(self):
        definition = capture('multiselect', options=self.OPTIONS)
        encode_field_value(['Alpha'], definition)
        assert all('selected' not in option for option in self.OPTIONS)


class TestTable:
    """table takes a list with exactly one entry per defined column."""

    COLUMNS = [{'id': 'c1', 'name': 'Item'}, {'id': 'c2', 'name': 'Qty'}]

    def test_json_string_is_parsed(self):
        encoded = encode_field_value('["Widget", "3"]', capture('table', columns=self.COLUMNS))
        assert encoded == ['Widget', '3']

    def test_dict_is_projected_onto_column_order(self):
        encoded = encode_field_value({'c1': 'Widget', 'c2': '3'}, capture('table', columns=self.COLUMNS))
        assert encoded == ['Widget', '3']

    def test_list_matching_column_count_passes_through(self):
        encoded = encode_field_value(['Widget', '3'], capture('table', columns=self.COLUMNS))
        assert encoded == ['Widget', '3']
        assert len(encoded) == len(self.COLUMNS)


class TestAssigneesForm:
    """assignees_form takes {"users": [], "guests": [], "groups": []}."""

    MEMBERS = [{'id': 7, 'email': 'member@example.com'}]

    def test_members_become_users_and_others_become_guests(self):
        encoded = encode_field_value(
            'member@example.com, outsider@example.com',
            capture('assignees_form'),
            org_members=self.MEMBERS,
        )
        assert encoded == {'users': [7], 'guests': ['outsider@example.com'], 'groups': []}

    def test_guests_are_never_sole_assignees(self):
        encoded = encode_assignees_form(
            'outsider@example.com', self.MEMBERS, current_user_id=99
        )
        assert encoded == {'users': [99], 'guests': ['outsider@example.com'], 'groups': []}

    def test_invalid_emails_are_ignored(self):
        encoded = encode_assignees_form('not-an-email', self.MEMBERS, current_user_id=99)
        assert encoded == {'users': [], 'guests': [], 'groups': []}


class TestNormalizePrerunObject:
    """The API never accepts a list for prerun."""

    def test_list_of_field_id_value_pairs_becomes_an_object(self):
        normalized = normalize_prerun_object([
            {'field_id': 'f1', 'value': 'one'},
            {'field_id': 'f2', 'value': 'two'},
        ])
        assert normalized == {'f1': 'one', 'f2': 'two'}

    def test_dict_is_copied_not_aliased(self):
        source = {'f1': 'one'}
        assert normalize_prerun_object(source) == source
        assert normalize_prerun_object(source) is not source

    def test_none_becomes_empty_object(self):
        assert normalize_prerun_object(None) == {}


class TestResolveCapture:
    """Source keys may be a timeline_id, id, alias or label."""

    @pytest.mark.parametrize('key', [TIMELINE_ID, 'local-id', 'my_field', 'My Field'])
    def test_resolves_by_each_identifier(self, key):
        assert resolve_capture(key, [capture('text')]) is not None

    def test_unknown_key_resolves_to_none(self):
        assert resolve_capture('nope', [capture('text')]) is None


class TestBuildPrerunPayload:
    """The payload is an object keyed by timeline_id, with typed values."""

    def test_keys_by_timeline_id_not_by_source_key(self):
        payload = build_prerun_payload({'my_field': 'hello'}, [capture('text')])
        assert payload == {TIMELINE_ID: 'hello'}

    def test_values_are_typed_per_field(self):
        options = [{'id': 'opt1', 'text': 'Yes'}]
        payload = build_prerun_payload(
            {'my_field': 'Yes'}, [capture('dropdown', options=options)]
        )
        assert payload == {TIMELINE_ID: {'id': 'opt1', 'text': 'Yes'}}

    def test_unresolvable_keys_are_dropped(self):
        payload = build_prerun_payload({'unknown_field': 'x'}, [capture('text')])
        assert payload == {}

    def test_list_input_is_normalised_then_keyed(self):
        payload = build_prerun_payload(
            [{'field_id': 'my_field', 'value': 'hello'}], [capture('text')]
        )
        assert payload == {TIMELINE_ID: 'hello'}

    def test_without_captures_keys_pass_through_unchanged(self):
        payload = build_prerun_payload({'my_field': 'hello'})
        assert payload == {'my_field': 'hello'}

    def test_empty_input_yields_empty_object(self):
        assert build_prerun_payload({}, [capture('text')]) == {}
        assert build_prerun_payload(None, [capture('text')]) == {}
