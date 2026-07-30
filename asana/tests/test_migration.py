#!/usr/bin/env python3
"""Asana migrator tests.

These exercise the transformers and validator directly. The orchestrator is
deliberately not constructed: AsanaMigrationOrchestrator requires live tokens
(asana_token, tallyfy_token, tallyfy_org_id) and builds real API clients, so a
meaningful orchestrator test needs fixtures this repo does not have yet.

The previous version of this file asserted against an API that never existed --
`VendorMigrationOrchestrator`, `_run_discovery_phase`, `.vendor_client` -- so it
could not even be collected. It looked like coverage while providing none.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.transformers.field_transformer import FieldTransformer
from src.transformers.user_transformer import UserTransformer
from src.utils.validator import MigrationValidator


class TestUserTransformer(unittest.TestCase):
    """Asana user -> Tallyfy member."""

    def setUp(self):
        self.transformer = UserTransformer()

    def test_email_is_read_from_the_asana_key_and_written_to_the_tallyfy_key(self):
        """Regression: the address must survive the key change.

        Asana returns it under `email` (opt_fields in asana_client.py:162);
        Tallyfy wants it under `text`. This transformer used to READ "text" from
        the Asana object, so every migrated member carried an empty email and
        nothing failed loudly.
        """
        result = self.transformer.transform_user({
            'gid': '123',
            'name': 'Jane Doe',
            'email': 'jane@example.com',
        })

        self.assertEqual(result['text'], 'jane@example.com')

    def test_a_full_name_is_split_into_first_and_last(self):
        result = self.transformer.transform_user({
            'gid': '123', 'name': 'Jane Doe', 'email': 'jane@example.com',
        })
        self.assertEqual(result['first_name'], 'Jane')
        self.assertEqual(result['last_name'], 'Doe')

    def test_a_single_word_name_leaves_the_last_name_empty(self):
        result = self.transformer.transform_user({
            'gid': '123', 'name': 'Prince', 'email': 'prince@example.com',
        })
        self.assertEqual(result['first_name'], 'Prince')
        self.assertEqual(result['last_name'], '')

    def test_users_default_to_member(self):
        result = self.transformer.transform_user({
            'gid': '123', 'name': 'Jane Doe', 'email': 'jane@example.com',
        })
        self.assertEqual(result['role'], 'member')

    def test_a_guest_workspace_membership_maps_to_light(self):
        result = self.transformer.transform_user(
            {'gid': '123', 'name': 'Jane Doe', 'email': 'jane@example.com'},
            workspace_membership={'is_guest': True},
        )
        self.assertEqual(result['role'], 'light')

    def test_the_source_gid_is_retained_for_mapping(self):
        result = self.transformer.transform_user({
            'gid': '123', 'name': 'Jane Doe', 'email': 'jane@example.com',
        })
        self.assertEqual(result['metadata']['original_gid'], '123')
        self.assertEqual(result['metadata']['source'], 'asana')

    def test_notification_preferences_read_the_asana_email_key(self):
        prefs = self.transformer.transform_user_preferences({
            'gid': '123', 'email': 'jane@example.com',
        })
        self.assertEqual(prefs['notification_email'], 'jane@example.com')


class TestFieldTransformer(unittest.TestCase):
    """Asana custom field -> Tallyfy capture."""

    def setUp(self):
        self.transformer = FieldTransformer()

    def test_an_enum_becomes_a_dropdown_carrying_its_options(self):
        result = self.transformer.transform_custom_field_definition({
            'gid': 'f1',
            'name': 'Priority',
            'type': 'enum',
            'enum_options': [
                {'gid': '1', 'name': 'High'},
                {'gid': '2', 'name': 'Low'},
            ],
        })

        self.assertEqual(result['type'], 'dropdown')
        self.assertEqual(result['name'], 'Priority')
        self.assertEqual([o['label'] for o in result['options']], ['High', 'Low'])

    def test_an_unknown_type_falls_back_to_text_rather_than_raising(self):
        result = self.transformer.transform_custom_field_definition({
            'gid': 'f2', 'name': 'Mystery', 'type': 'not_a_real_asana_type',
        })
        self.assertEqual(result['type'], 'text')

    def test_the_source_gid_is_kept_as_the_alias(self):
        result = self.transformer.transform_custom_field_definition({
            'gid': 'f3', 'name': 'Notes', 'type': 'text',
        })
        self.assertEqual(result['alias'], 'asana_f3')


class TestMigrationValidator(unittest.TestCase):
    """Pre-migration validation."""

    def setUp(self):
        self.validator = MigrationValidator()

    def test_a_user_with_an_email_passes(self):
        """Regression: this check read "text", so it rejected every real user."""
        self.assertTrue(self.validator.validate_user({
            'gid': '123', 'name': 'Jane Doe', 'email': 'jane@example.com',
        }))

    def test_a_user_with_no_email_is_still_rejected(self):
        self.assertFalse(self.validator.validate_user({
            'gid': '123', 'name': 'Jane Doe',
        }))
        self.assertIn('User missing email address', self.validator.validation_errors)

    def test_a_user_with_no_gid_is_rejected(self):
        self.assertFalse(self.validator.validate_user({
            'name': 'Jane Doe', 'email': 'jane@example.com',
        }))


if __name__ == '__main__':
    unittest.main()
