#!/usr/bin/env python3
"""Process Street migrator tests.

These exercise the transformers directly. The orchestrator is deliberately not
constructed: MigrationOrchestrator requires a config file path and builds real API
clients from it, so a meaningful orchestrator test needs fixtures this repo does
not have yet.

The previous version of this file asserted against an API that never existed --
`ProcessStreetMigrationOrchestrator`, `_run_discovery_phase`, `_run_mapping_phase`,
`.vendor_client` (the real phases are `_phase_discovery`, `_phase_users`, ...) --
so it could not even be collected. It looked like 20 tests' worth of coverage
while providing none.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.transformers.field_transformer import FieldTransformer
from src.transformers.user_transformer import UserTransformer


class TestUserTransformer(unittest.TestCase):
    """Process Street user -> Tallyfy member."""

    def setUp(self):
        self.transformer = UserTransformer()

    def test_email_is_read_from_the_source_key_and_written_to_the_tallyfy_key(self):
        """Regression: the address must survive the key change.

        The source key is `email` (OBJECT_MAPPING.md: "Email -> Email (unique
        identifier)"). This transformer used to READ "text" AND validate on it,
        so every real user raised "ValueError: Missing required fields" instead
        of migrating.

        The OUTPUT key is `email` too, and that is not a guess -- main.py:310
        hands this dict straight to `create_user(tallyfy_user)`, which does
        `self._make_request('POST', '/users', json=user_data)` with no
        remapping. So whatever key this transformer writes IS the wire key.
        The client's own docstring says "user_data: User information including
        email, ...", and `find_user_by_email` compares `user.get('email')`.

        (A migrator whose caller unpacks the dict --
        `create_member(email=member["text"], ...)` -- can legitimately keep
        `text`, because the key only reaches the wire when the whole dict is
        posted. This one posts the whole dict.)
        """
        result = self.transformer.transform({
            'id': 'u1',
            'email': 'jane@example.com',
            'firstName': 'Jane',
            'lastName': 'Doe',
            'role': 'Admin',
            'active': True,
        })

        self.assertEqual(result['email'], 'jane@example.com')

    def test_a_user_without_an_email_is_rejected_loudly(self):
        """A missing email must raise, not migrate a member with no identity."""
        with self.assertRaises(ValueError):
            self.transformer.transform({'id': 'u1', 'firstName': 'Jane'})

    def test_name_and_role_are_carried_across(self):
        result = self.transformer.transform({
            'id': 'u1', 'email': 'jane@example.com',
            'firstName': 'Jane', 'lastName': 'Doe', 'role': 'Admin',
        })
        self.assertEqual(result['first_name'], 'Jane')
        self.assertEqual(result['last_name'], 'Doe')
        self.assertEqual(result['role'], 'admin')

    def test_the_snake_case_name_spelling_is_also_accepted(self):
        """The transformer reads firstName or first_name; both appear in the wild."""
        result = self.transformer.transform({
            'id': 'u1', 'email': 'jane@example.com',
            'first_name': 'Jane', 'last_name': 'Doe',
        })
        self.assertEqual(result['first_name'], 'Jane')
        self.assertEqual(result['last_name'], 'Doe')

    def test_an_active_user_stays_active(self):
        result = self.transformer.transform({
            'id': 'u1', 'email': 'jane@example.com', 'active': True,
        })
        self.assertTrue(result['is_active'])

    def test_a_guest_carries_its_email(self):
        """Regression: transform_guest had the same wrong source key.

        A guest IS its email address in Tallyfy, so reading the wrong key
        produced guests with no identity at all.
        """
        result = self.transformer.transform_guest({
            'id': 'g1', 'email': 'guest@example.com',
        })
        self.assertEqual(result['email'], 'guest@example.com')


class TestFieldTransformer(unittest.TestCase):
    """Process Street form field -> Tallyfy capture."""

    def setUp(self):
        self.transformer = FieldTransformer()

    def test_a_text_field_maps_to_the_tallyfy_text_type(self):
        result = self.transformer.transform_field({
            'id': 'f1', 'label': 'Full Name', 'type': 'text',
        })
        self.assertEqual(result['type'], 'text')
        self.assertEqual(result['label'], 'Full Name')

    def test_a_select_becomes_a_dropdown(self):
        result = self.transformer.transform_field({
            'id': 'f2', 'label': 'Priority', 'type': 'select',
            'config': {'options': [{'label': 'High', 'value': '1'}]},
        })
        self.assertEqual(result['type'], 'dropdown')

    def test_a_select_keeps_the_options_process_street_stores_in_config_items(self):
        """Regression: a dropdown must not arrive with options: [].

        In the Process Street Public API v1.1 spec (read 2026-11-12 from
        public-api.process.st/api/v1.1/docs/openapi.json), a form field
        widget keeps its choices in `config.items`, each `{id, name}`
        (PublicApiSelectFormFieldConfig). No field config has a top-level
        `options` key. This transformer read only `field['options']`, so
        every select came out with no options.

        The payload is a widget from that spec, except that `type` holds the
        field type this transformer reads. A real widget has
        `type: FormField` and the subtype in `fieldType`.
        """
        result = self.transformer.transform_field({
            'id': 'Wd3kq0Y1pXvBoc_D9aF8Qw',
            'taskId': 'Tk7aYp2LmQvBoc_D5_RypA',
            'type': 'select',
            'fieldType': 'Select',
            'key': 'priority',
            'label': 'Priority',
            'required': True,
            'hiddenByDefault': False,
            'config': {
                'fieldType': 'Select',
                'items': [
                    {'id': 'jmBoZtynZxMBoc_D9aF8Qw', 'name': 'High'},
                    {'id': 'k2CpAuzoAyNBoc_D9aF8Qw', 'name': 'Medium'},
                    {'id': 'l3DqBvApBzOBoc_D9aF8Qw', 'name': 'Low'},
                ],
                'defaultValue': 'Medium',
            },
        })
        self.assertEqual(result['type'], 'dropdown')
        self.assertEqual([o['label'] for o in result['options']],
                         ['High', 'Medium', 'Low'])

    def test_a_select_keeps_options_given_under_config_options(self):
        """The shape tallyfy/migrator#30 item 13 names, and this file's older fixture."""
        result = self.transformer.transform_field({
            'id': 'f2', 'label': 'Priority', 'type': 'select',
            'config': {'options': [{'label': 'High', 'value': '1'},
                                   {'label': 'Low', 'value': '2'}]},
        })
        self.assertEqual([o['label'] for o in result['options']], ['High', 'Low'])

    def test_a_select_still_reads_a_top_level_options_list(self):
        """The fallback stays: GET .../form-fields/{id}/options returns
        `options: [{value, label, id}]`, and a caller may attach that list
        to the field as it stands."""
        result = self.transformer.transform_field({
            'id': 'f2', 'label': 'Priority', 'type': 'select',
            'options': [{'value': 'High', 'label': 'High',
                         'id': 'jmBoZtynZxMBoc_D9aF8Qw'}],
        })
        self.assertEqual([o['label'] for o in result['options']], ['High'])

    def test_the_source_id_and_type_are_retained_for_tracing(self):
        result = self.transformer.transform_field({
            'id': 'f3', 'label': 'Notes', 'type': 'textarea',
        })
        self.assertEqual(result['metadata']['original_id'], 'f3')
        self.assertEqual(result['metadata']['original_type'], 'textarea')

    def test_a_batch_transforms_every_field(self):
        result = self.transformer.transform_fields_batch([
            {'id': 'f1', 'label': 'A', 'type': 'text'},
            {'id': 'f2', 'label': 'B', 'type': 'text'},
        ])
        self.assertEqual(len(result), 2)
        self.assertEqual([f['label'] for f in result], ['A', 'B'])


if __name__ == '__main__':
    unittest.main()
