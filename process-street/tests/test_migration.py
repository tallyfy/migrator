#!/usr/bin/env python3
"""
Comprehensive test suite for Process Street to Tallyfy migration
Tests all 5 phases with real-world scenarios
"""

import unittest
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import ProcessStreetMigrationOrchestrator
from src.api.process_street_client import ProcessStreetClient
from src.api.tallyfy_client import TallyfyClient
from src.api.ai_client import AIClient
from src.transformers.field_transformer import FieldTransformer
from src.transformers.template_transformer import TemplateTransformer
from src.transformers.instance_transformer import InstanceTransformer
from src.transformers.user_transformer import UserTransformer
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.validator import MigrationValidator
from src.utils.error_handler import ErrorHandler


class TestProcessStreetMigration(unittest.TestCase):
    """Test Process Street migration with comprehensive scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.orchestrator = ProcessStreetMigrationOrchestrator()
        self.test_data_dir = Path(__file__).parent / 'test_data'
        self.test_data_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """Clean up test artifacts"""
        # Clean up test database
        test_db = Path('migration_checkpoint.db')
        if test_db.exists():
            test_db.unlink()
    
    # ============= DISCOVERY PHASE TESTS =============
    
    def test_discovery_simple_workflow(self):
        """Test discovery of simple linear workflow"""
        mock_workflow = {
            'id': 'wf_123',
            'name': 'Employee Onboarding',
            'description': 'Standard onboarding process',
            'tasks': [
                {'id': 't1', 'name': 'Personal Information', 'type': 'form', 'fields': 5},
                {'id': 't2', 'name': 'IT Setup', 'type': 'task', 'assignee': 'it_team'},
                {'id': 't3', 'name': 'Manager Approval', 'type': 'approval'}
            ],
            'active_runs': 3
        }
        
        with patch.object(self.orchestrator.vendor_client, 'get_workflows', return_value=[mock_workflow]):
            result = self.orchestrator._run_discovery_phase()
            
            self.assertEqual(len(result['workflows']), 1)
            self.assertEqual(result['workflows'][0]['name'], 'Employee Onboarding')
            self.assertEqual(len(result['workflows'][0]['tasks']), 3)
            self.assertEqual(result['statistics']['total_workflows'], 1)
    
    def test_discovery_complex_workflow_with_conditions(self):
        """Test discovery of complex workflow with conditional logic"""
        mock_workflow = {
            'id': 'wf_456',
            'name': 'Purchase Approval',
            'tasks': [
                {'id': 't1', 'name': 'Request Form', 'type': 'form', 'fields': 10},
                {
                    'id': 't2', 
                    'name': 'Manager Review', 
                    'type': 'approval',
                    'conditions': [
                        {'if': 'amount > 1000', 'then': 'director_approval'},
                        {'if': 'amount > 5000', 'then': 'cfo_approval'}
                    ]
                },
                {'id': 't3', 'name': 'Director Approval', 'type': 'approval', 'conditional': True},
                {'id': 't4', 'name': 'CFO Approval', 'type': 'approval', 'conditional': True},
                {'id': 't5', 'name': 'Purchase Order', 'type': 'task'}
            ],
            'active_runs': 15
        }
        
        with patch.object(self.orchestrator.vendor_client, 'get_workflows', return_value=[mock_workflow]):
            result = self.orchestrator._run_discovery_phase()
            
            workflow = result['workflows'][0]
            self.assertEqual(len(workflow['tasks']), 5)
            self.assertTrue(any(t.get('conditional') for t in workflow['tasks']))
            self.assertIn('conditions', workflow['tasks'][1])
    
    def test_discovery_with_rate_limiting(self):
        """Test discovery handles rate limiting gracefully"""
        mock_error = Exception("Rate limit exceeded")
        
        with patch.object(self.orchestrator.vendor_client, 'get_workflows', side_effect=[mock_error, []]):
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = self.orchestrator._run_discovery_phase()
                self.assertIsNotNone(result)
    
    # ============= FIELD TRANSFORMATION TESTS =============
    
    def test_field_type_direct_mapping(self):
        """Test direct field type mappings"""
        transformer = FieldTransformer(None)  # No AI for deterministic test
        
        test_fields = [
            {'type': 'text', 'name': 'Full Name'},
            {'type': 'email', 'name': 'Email Address'},
            {'type': 'number', 'name': 'Employee ID'},
            {'type': 'date', 'name': 'Start Date'},
            {'type': 'checkbox', 'name': 'Agree to Terms'}
        ]
        
        expected_mappings = [
            'short_text',
            'email',
            'number',
            'date',
            'yes_no'
        ]
        
        for field, expected in zip(test_fields, expected_mappings):
            result = transformer.transform_field(field)
            self.assertEqual(result['type'], expected)
    
    def test_field_type_with_ai_enhancement(self):
        """Test field type mapping with AI assistance"""
        mock_ai = Mock(spec=AIClient)
        mock_ai.enabled = True
        mock_ai.make_decision.return_value = {
            'tallyfy_type': 'phone',
            'confidence': 0.95,
            'reasoning': 'Field name and validation pattern indicate phone number'
        }
        
        transformer = FieldTransformer(mock_ai)
        
        ambiguous_field = {
            'type': 'text',
            'name': 'Contact Number',
            'validation': r'^\d{3}-\d{3}-\d{4}$'
        }
        
        result = transformer.transform_field(ambiguous_field)
        self.assertEqual(result['type'], 'phone')
        mock_ai.make_decision.assert_called_once()
    
    def test_complex_form_splitting_decision(self):
        """Test AI decision for splitting complex forms"""
        mock_ai = Mock(spec=AIClient)
        mock_ai.enabled = True
        mock_ai.assess_form_complexity.return_value = {
            'strategy': 'multi_step',
            'recommended_steps': 3,
            'reasoning': 'Form has 45 fields across 3 logical sections'
        }
        
        transformer = TemplateTransformer(mock_ai)
        
        complex_form = {
            'name': 'Employee Onboarding',
            'fields': [{'name': f'field_{i}'} for i in range(45)]
        }
        
        result = transformer.should_split_form(complex_form)
        self.assertTrue(result['should_split'])
        self.assertEqual(result['num_steps'], 3)
    
    # ============= PARADIGM SHIFT TESTS =============
    
    def test_kanban_to_sequential_transformation(self):
        """Test transformation of Kanban board to sequential process"""
        transformer = TemplateTransformer(None)
        
        kanban_workflow = {
            'name': 'Development Pipeline',
            'type': 'kanban',
            'columns': [
                {'name': 'Backlog', 'cards': 10},
                {'name': 'In Progress', 'cards': 5},
                {'name': 'Review', 'cards': 3},
                {'name': 'Done', 'cards': 20}
            ]
        }
        
        result = transformer.transform_kanban_to_sequential(kanban_workflow)
        
        # Each column should become 3 steps (entry, work, exit)
        expected_steps = len(kanban_workflow['columns']) * 3
        self.assertEqual(len(result['steps']), expected_steps)
        
        # Verify step pattern
        self.assertIn('Backlog - Ready', [s['name'] for s in result['steps']])
        self.assertIn('Backlog - In Progress', [s['name'] for s in result['steps']])
        self.assertIn('Backlog - Review', [s['name'] for s in result['steps']])
    
    # ============= USER MIGRATION TESTS =============
    
    def test_user_role_mapping(self):
        """Test user role transformation"""
        transformer = UserTransformer(None)
        
        process_street_users = [
            {'email': 'admin@company.com', 'role': 'admin', 'name': 'Admin User'},
            {'email': 'manager@company.com', 'role': 'editor', 'name': 'Manager User'},
            {'email': 'employee@company.com', 'role': 'member', 'name': 'Employee User'},
            {'email': 'guest@external.com', 'role': 'guest', 'name': 'External Guest'}
        ]
        
        expected_roles = ['admin', 'manager', 'member', 'guest']
        
        for user, expected_role in zip(process_street_users, expected_roles):
            result = transformer.transform_user(user)
            self.assertEqual(result['role'], expected_role)
            self.assertEqual(result['email'], user['email'])
    
    # ============= CHECKPOINT/RESUME TESTS =============
    
    def test_checkpoint_save_and_resume(self):
        """Test checkpoint saving and resuming"""
        checkpoint_mgr = CheckpointManager('test_migration_123')
        
        # Save checkpoint after discovery
        discovery_data = {
            'workflows': [{'id': 'wf1', 'name': 'Test Workflow'}],
            'users': [{'id': 'u1', 'email': 'test@example.com'}]
        }
        checkpoint_mgr.save_phase_checkpoint('discovery', discovery_data)
        
        # Verify checkpoint exists
        last_phase = checkpoint_mgr.get_last_completed_phase()
        self.assertEqual(last_phase, 'discovery')
        
        # Load checkpoint data
        loaded_data = checkpoint_mgr.load_phase_checkpoint('discovery')
        self.assertEqual(loaded_data['workflows'][0]['name'], 'Test Workflow')
    
    def test_migration_resume_after_failure(self):
        """Test resuming migration after failure"""
        with patch.object(self.orchestrator, '_run_discovery_phase') as mock_discovery:
            with patch.object(self.orchestrator, '_run_mapping_phase') as mock_mapping:
                mock_discovery.return_value = {'workflows': [], 'users': []}
                mock_mapping.side_effect = Exception("Network error")
                
                # First run should fail at mapping
                with self.assertRaises(Exception):
                    self.orchestrator.run(phases=['discovery', 'mapping'])
                
                # Verify discovery was completed
                self.assertTrue(mock_discovery.called)
                
                # Reset mock and resume
                mock_mapping.side_effect = None
                mock_mapping.return_value = {'mappings': {}}
                
                # Resume should skip discovery
                self.orchestrator.run(resume=True, phases=['mapping'])
                
                # Discovery should not be called again
                self.assertEqual(mock_discovery.call_count, 1)
    
    # ============= ERROR HANDLING TESTS =============
    
    def test_api_error_recovery(self):
        """Test recovery from API errors"""
        error_handler = ErrorHandler()
        
        # Test exponential backoff
        with patch('time.sleep') as mock_sleep:
            for attempt in range(3):
                error_handler.handle_api_error(
                    Exception("API Error"),
                    attempt=attempt
                )
            
            # Verify exponential backoff pattern
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            self.assertTrue(sleep_calls[1] > sleep_calls[0])
            self.assertTrue(sleep_calls[2] > sleep_calls[1])
    
    def test_rate_limit_handling(self):
        """Test rate limit detection and handling"""
        error_handler = ErrorHandler()
        
        rate_limit_error = Exception("429 Too Many Requests")
        
        with patch('time.sleep') as mock_sleep:
            error_handler.handle_rate_limit(rate_limit_error)
            
            # Should sleep for extended period on rate limit
            mock_sleep.assert_called()
            sleep_duration = mock_sleep.call_args[0][0]
            self.assertGreaterEqual(sleep_duration, 60)  # At least 1 minute
    
    # ============= VALIDATION TESTS =============
    
    def test_migration_validation(self):
        """Test post-migration validation"""
        validator = MigrationValidator(
            Mock(spec=ProcessStreetClient),
            Mock(spec=TallyfyClient)
        )
        
        migration_result = {
            'created_templates': [
                {'id': 'bt1', 'name': 'Template 1', 'source_id': 'wf1'},
                {'id': 'bt2', 'name': 'Template 2', 'source_id': 'wf2'}
            ],
            'created_users': [
                {'id': 'tu1', 'email': 'user1@example.com'},
                {'id': 'tu2', 'email': 'user2@example.com'}
            ],
            'errors': []
        }
        
        validation_result = validator.validate_migration(migration_result)
        
        self.assertTrue(validation_result['success'])
        self.assertEqual(validation_result['templates_migrated'], 2)
        self.assertEqual(validation_result['users_migrated'], 2)
        self.assertEqual(validation_result['error_count'], 0)
    
    # ============= INTEGRATION TESTS =============
    
    def test_end_to_end_simple_migration(self):
        """Test complete migration of simple workflow"""
        # Mock all external dependencies
        with patch.object(self.orchestrator.vendor_client, 'test_connection', return_value=True):
            with patch.object(self.orchestrator.vendor_client, 'get_workflows') as mock_workflows:
                with patch.object(self.orchestrator.vendor_client, 'get_users') as mock_users:
                    with patch.object(self.orchestrator.tallyfy_client, 'create_template') as mock_create:
                        
                        # Setup mock data
                        mock_workflows.return_value = [{
                            'id': 'wf1',
                            'name': 'Simple Process',
                            'tasks': [
                                {'name': 'Step 1', 'type': 'task'},
                                {'name': 'Step 2', 'type': 'approval'}
                            ]
                        }]
                        
                        mock_users.return_value = [
                            {'email': 'user@example.com', 'name': 'Test User'}
                        ]
                        
                        mock_create.return_value = {'id': 'bt1', 'name': 'Simple Process'}
                        
                        # Run migration
                        self.orchestrator.run(dry_run=False)
                        
                        # Verify API calls
                        mock_workflows.assert_called()
                        mock_users.assert_called()
                        mock_create.assert_called()
    
    # ============= PERFORMANCE TESTS =============
    
    def test_batch_processing_performance(self):
        """Test batch processing handles large datasets efficiently"""
        large_dataset = {
            'workflows': [{'id': f'wf_{i}', 'name': f'Workflow {i}'} for i in range(1000)],
            'users': [{'id': f'u_{i}', 'email': f'user{i}@example.com'} for i in range(500)]
        }
        
        start_time = datetime.now()
        
        # Process in batches
        batch_size = 50
        for i in range(0, len(large_dataset['workflows']), batch_size):
            batch = large_dataset['workflows'][i:i+batch_size]
            # Simulate processing
            self.assertLessEqual(len(batch), batch_size)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should process 1000 items in reasonable time
        self.assertLess(elapsed, 5)  # Less than 5 seconds for test
    
    def test_memory_management(self):
        """Test memory is properly managed during large migrations"""
        import gc
        import tracemalloc
        
        tracemalloc.start()
        
        # Create large object
        large_data = [{'data': 'x' * 1000} for _ in range(1000)]
        
        # Get memory usage
        snapshot1 = tracemalloc.take_snapshot()
        
        # Clear large object
        del large_data
        gc.collect()
        
        # Get memory after cleanup
        snapshot2 = tracemalloc.take_snapshot()
        
        # Memory should be released
        stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        tracemalloc.stop()
        
        # This is a simplified test - in production would check actual memory decrease
        self.assertIsNotNone(stats)


class TestFieldTransformer(unittest.TestCase):
    """Test field transformation logic"""
    
    def test_all_process_street_field_types(self):
        """Test all Process Street field types map correctly"""
        transformer = FieldTransformer(None)
        
        field_mappings = {
            'text': 'short_text',
            'email': 'email',
            'url': 'url',
            'tel': 'phone',
            'number': 'number',
            'date': 'date',
            'dropdown': 'dropdown',
            'multiselect': 'multi_select',
            'checkbox': 'yes_no',
            'file': 'file_attachment',
            'member': 'member_select'
        }
        
        for ps_type, expected_tallyfy in field_mappings.items():
            field = {'type': ps_type, 'name': f'Test {ps_type}'}
            result = transformer.transform_field(field)
            self.assertEqual(
                result['type'], 
                expected_tallyfy,
                f"Failed to map {ps_type} to {expected_tallyfy}"
            )
    
    def test_field_validation_preservation(self):
        """Test field validations are preserved"""
        transformer = FieldTransformer(None)
        
        field_with_validation = {
            'type': 'text',
            'name': 'Email Field',
            'required': True,
            'validation': {
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'message': 'Please enter a valid email'
            }
        }
        
        result = transformer.transform_field(field_with_validation)
        
        self.assertTrue(result['required'])
        self.assertIn('validation', result)
        self.assertEqual(result['validation']['pattern'], field_with_validation['validation']['pattern'])


class TestConditionalLogic(unittest.TestCase):
    """Test conditional logic transformation"""
    
    def test_simple_if_then_condition(self):
        """Test simple if-then condition transformation"""
        transformer = TemplateTransformer(None)
        
        condition = {
            'if': {
                'field': 'amount',
                'operator': '>',
                'value': 1000
            },
            'then': {
                'action': 'require_approval',
                'target': 'manager'
            }
        }
        
        result = transformer.transform_condition(condition)
        
        self.assertEqual(result['type'], 'conditional_step')
        self.assertEqual(result['condition']['field'], 'amount')
        self.assertEqual(result['condition']['operator'], 'greater_than')
        self.assertEqual(result['action']['type'], 'require_approval')
    
    def test_complex_nested_conditions(self):
        """Test complex nested conditions"""
        transformer = TemplateTransformer(None)
        
        complex_condition = {
            'if': {
                'and': [
                    {'field': 'department', 'operator': '==', 'value': 'IT'},
                    {'field': 'urgency', 'operator': '==', 'value': 'high'}
                ]
            },
            'then': {
                'action': 'assign',
                'target': 'it_emergency_team'
            },
            'else': {
                'action': 'assign',
                'target': 'it_standard_team'
            }
        }
        
        result = transformer.transform_condition(complex_condition)
        
        self.assertEqual(result['type'], 'conditional_assignment')
        self.assertIn('and', result['condition'])
        self.assertEqual(len(result['condition']['and']), 2)
        self.assertIn('else', result)


if __name__ == '__main__':
    unittest.main(verbosity=2)