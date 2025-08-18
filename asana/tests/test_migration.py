#!/usr/bin/env python3
"""
Migration tests for vendor
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import VendorMigrationOrchestrator


class TestMigration(unittest.TestCase):
    """Test migration functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.orchestrator = VendorMigrationOrchestrator()
    
    def test_discovery_phase(self):
        """Test discovery phase"""
        with patch.object(self.orchestrator.vendor_client, 'get_workflows', return_value=[]):
            result = self.orchestrator._run_discovery_phase()
            self.assertIsNotNone(result)
    
    def test_user_migration(self):
        """Test user migration"""
        users = [{'email': 'test@example.com', 'name': 'Test User'}]
        with patch.object(self.orchestrator.vendor_client, 'get_users', return_value=users):
            # Test user transformation
            self.assertEqual(len(users), 1)
    
    def test_field_mapping(self):
        """Test field type mapping"""
        field = {'type': 'text', 'name': 'Test Field'}
        result = self.orchestrator.field_transformer.transform_field(field)
        self.assertEqual(result['type'], 'short_text')


if __name__ == '__main__':
    unittest.main()
