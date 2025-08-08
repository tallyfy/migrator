"""Tests for Monday.com to Tallyfy transformers."""

import unittest
import json
from datetime import datetime
from src.transformers.field_transformer import FieldTransformer
from src.transformers.board_transformer import BoardTransformer
from src.transformers.user_transformer import UserTransformer
from src.transformers.instance_transformer import InstanceTransformer


class TestFieldTransformer(unittest.TestCase):
    """Test field transformation."""
    
    def setUp(self):
        self.transformer = FieldTransformer()
    
    def test_text_field_transformation(self):
        """Test text column transformation."""
        column = {
            'id': 'text1',
            'title': 'Project Name',
            'type': 'text',
            'description': 'Enter project name'
        }
        
        result = self.transformer.transform_column(column)
        
        self.assertEqual(result['type'], 'short_text')
        self.assertEqual(result['name'], 'Project Name')
        self.assertEqual(result['alias'], 'monday_text1')
    
    def test_status_field_transformation(self):
        """Test status column transformation."""
        column = {
            'id': 'status1',
            'title': 'Status',
            'type': 'status',
            'settings_str': json.dumps({
                'labels': {
                    '0': 'Not Started',
                    '1': 'In Progress',
                    '2': 'Done'
                }
            })
        }
        
        result = self.transformer.transform_column(column)
        
        self.assertEqual(result['type'], 'dropdown')
        self.assertEqual(len(result['options']), 3)
        self.assertEqual(result['options'][0]['label'], 'Not Started')
    
    def test_people_field_transformation(self):
        """Test people column transformation."""
        column = {
            'id': 'people1',
            'title': 'Assignee',
            'type': 'people'
        }
        
        result = self.transformer.transform_column(column)
        
        self.assertEqual(result['type'], 'assignee_picker')
        self.assertEqual(result['name'], 'Assignee')
    
    def test_timeline_field_transformation(self):
        """Test timeline column transformation."""
        column = {
            'id': 'timeline1',
            'title': 'Project Timeline',
            'type': 'timeline'
        }
        
        result = self.transformer.transform_column(column)
        
        self.assertEqual(result['type'], 'date')
        self.assertIn('Timeline: Start date', result['description'])
        
        # Test end date field creation
        end_field = self.transformer.create_timeline_end_field(column)
        self.assertIn('End Date', end_field['name'])
    
    def test_formula_field_transformation(self):
        """Test formula column transformation."""
        column = {
            'id': 'formula1',
            'title': 'Total Cost',
            'type': 'formula',
            'settings_str': json.dumps({
                'formula': 'SUM({cost1}, {cost2})'
            })
        }
        
        result = self.transformer.transform_column(column)
        
        self.assertTrue(result.get('readonly'))
        self.assertIn('Calculated', result['description'])
    
    def test_column_value_transformation(self):
        """Test column value transformation."""
        # Test checkbox value
        checkbox_value = {
            'value': json.dumps({'checked': 'true'}),
            'text': 'Checked'
        }
        result = self.transformer.transform_column_value('checkbox', checkbox_value)
        self.assertEqual(result, 'yes')
        
        # Test date value
        date_value = {
            'value': json.dumps({'date': '2024-01-15'}),
            'text': 'Jan 15, 2024'
        }
        result = self.transformer.transform_column_value('date', date_value)
        self.assertEqual(result, '2024-01-15')
        
        # Test numbers value
        number_value = {
            'value': '42',
            'text': '42'
        }
        result = self.transformer.transform_column_value('numbers', number_value)
        self.assertEqual(result, 42.0)


class TestBoardTransformer(unittest.TestCase):
    """Test board transformation."""
    
    def setUp(self):
        self.transformer = BoardTransformer()
    
    def test_basic_board_transformation(self):
        """Test basic board to blueprint transformation."""
        board = {
            'id': '123456',
            'name': 'Product Development',
            'description': 'Track product development tasks',
            'board_kind': 'public',
            'groups': [
                {'id': 'g1', 'title': 'Planning'},
                {'id': 'g2', 'title': 'Development'}
            ],
            'columns': [
                {'id': 'name', 'title': 'Task', 'type': 'name'},
                {'id': 'status', 'title': 'Status', 'type': 'status'}
            ]
        }
        
        result = self.transformer.transform_board_to_blueprint(board)
        
        self.assertEqual(result['name'], 'Product Development')
        self.assertIn('steps', result)
        self.assertTrue(len(result['steps']) > 0)
        self.assertIn('kick_off_form', result)
        self.assertIn('metadata', result)
        self.assertEqual(result['metadata']['original_id'], '123456')
    
    def test_kanban_view_transformation(self):
        """Test Kanban view paradigm shift."""
        board = {
            'id': '789',
            'name': 'Kanban Board',
            'views': [
                {'type': 'kanban', 'name': 'Kanban View'}
            ],
            'columns': [
                {
                    'id': 'status',
                    'type': 'status',
                    'settings_str': json.dumps({
                        'labels': {
                            '0': 'Backlog',
                            '1': 'In Progress',
                            '2': 'Done'
                        }
                    })
                }
            ],
            'groups': []
        }
        
        result = self.transformer.transform_board_to_blueprint(board)
        
        self.assertIn('KANBAN VIEW TRANSFORMATION', result['description'])
        self.assertEqual(result['metadata']['primary_view'], 'kanban')
    
    def test_timeline_view_transformation(self):
        """Test Timeline view transformation."""
        board = {
            'id': '456',
            'name': 'Project Timeline',
            'views': [
                {'type': 'timeline', 'name': 'Gantt Chart'}
            ],
            'groups': [
                {'id': 'phase1', 'title': 'Phase 1'},
                {'id': 'phase2', 'title': 'Phase 2'}
            ],
            'columns': []
        }
        
        result = self.transformer.transform_board_to_blueprint(board)
        
        self.assertIn('TIMELINE VIEW TRANSFORMATION', result['description'])
        self.assertEqual(result['metadata']['primary_view'], 'timeline')
        
        # Check for phase-based steps
        phase_steps = [s for s in result['steps'] if 'phase' in s.get('metadata', {})]
        self.assertTrue(len(phase_steps) > 0)
    
    def test_permission_transformation(self):
        """Test board permission transformation."""
        board = {
            'id': '111',
            'name': 'Private Board',
            'board_kind': 'private',
            'permissions': {
                'everyone_can_edit': False
            },
            'groups': [],
            'columns': []
        }
        
        result = self.transformer.transform_board_to_blueprint(board)
        
        self.assertEqual(result['permissions']['visibility'], 'private')
        self.assertFalse(result['permissions']['can_edit'])


class TestUserTransformer(unittest.TestCase):
    """Test user transformation."""
    
    def setUp(self):
        self.transformer = UserTransformer()
    
    def test_basic_user_transformation(self):
        """Test basic user transformation."""
        monday_user = {
            'id': 'u123',
            'name': 'John Doe',
            'email': 'john@example.com',
            'enabled': True,
            'is_admin': False,
            'title': 'Developer'
        }
        
        result = self.transformer.transform_user(monday_user)
        
        self.assertEqual(result['email'], 'john@example.com')
        self.assertEqual(result['firstname'], 'John')
        self.assertEqual(result['lastname'], 'Doe')
        self.assertEqual(result['role'], 'member')
        self.assertEqual(result['title'], 'Developer')
    
    def test_admin_user_transformation(self):
        """Test admin user transformation."""
        admin_user = {
            'id': 'u456',
            'name': 'Admin User',
            'email': 'admin@example.com',
            'is_admin': True
        }
        
        result = self.transformer.transform_user(admin_user)
        
        self.assertEqual(result['role'], 'admin')
    
    def test_guest_user_transformation(self):
        """Test guest user transformation."""
        guest_user = {
            'id': 'u789',
            'name': 'Guest User',
            'email': 'guest@example.com',
            'is_guest': True
        }
        
        result = self.transformer.transform_user(guest_user)
        
        self.assertEqual(result['role'], 'light')
    
    def test_team_transformation(self):
        """Test team transformation."""
        # First add some users
        self.transformer.transform_user({
            'id': 'u1',
            'email': 'user1@example.com',
            'name': 'User One'
        })
        self.transformer.transform_user({
            'id': 'u2',
            'email': 'user2@example.com',
            'name': 'User Two'
        })
        
        monday_team = {
            'id': 't123',
            'name': 'Engineering Team',
            'users': [
                {'id': 'u1'},
                {'id': 'u2'}
            ],
            'owners': [
                {'id': 'u1'}
            ]
        }
        
        result = self.transformer.transform_team(monday_team)
        
        self.assertEqual(result['name'], 'Engineering Team')
        self.assertEqual(len(result['members']), 2)
        self.assertEqual(len(result['admins']), 1)
        self.assertIn('user1@example.com', result['members'])
    
    def test_user_without_email(self):
        """Test user without email is skipped."""
        user_no_email = {
            'id': 'u999',
            'name': 'No Email User'
        }
        
        result = self.transformer.transform_user(user_no_email)
        
        self.assertIsNone(result)


class TestInstanceTransformer(unittest.TestCase):
    """Test instance/item transformation."""
    
    def setUp(self):
        self.transformer = InstanceTransformer()
    
    def test_basic_item_transformation(self):
        """Test basic item to process transformation."""
        item = {
            'id': 'item123',
            'name': 'Complete Documentation',
            'state': 'active',
            'group': {'id': 'g1', 'title': 'Q1 Tasks'},
            'column_values': [
                {
                    'id': 'status',
                    'type': 'status',
                    'text': 'In Progress',
                    'value': json.dumps({'label': 'In Progress'})
                }
            ],
            'created_at': '2024-01-01T10:00:00Z',
            'updated_at': '2024-01-15T15:00:00Z'
        }
        
        result = self.transformer.transform_item_to_process(
            item, 
            'blueprint123',
            {'u1': 'tallyfy_user1'}
        )
        
        self.assertEqual(result['name'], 'Complete Documentation')
        self.assertEqual(result['blueprint_id'], 'blueprint123')
        self.assertEqual(result['status'], 'active')
        self.assertIn('data', result)
        self.assertEqual(result['metadata']['original_id'], 'item123')
    
    def test_item_with_assignees(self):
        """Test item with people column transformation."""
        item = {
            'id': 'item456',
            'name': 'Task with Assignees',
            'column_values': [
                {
                    'id': 'people',
                    'type': 'people',
                    'value': json.dumps({
                        'personsAndTeams': [
                            {'id': 'u1'},
                            {'id': 'u2'}
                        ]
                    })
                }
            ]
        }
        
        user_mapping = {
            'u1': 'tallyfy_user1',
            'u2': 'tallyfy_user2'
        }
        
        result = self.transformer.transform_item_to_process(
            item,
            'blueprint123',
            user_mapping
        )
        
        self.assertEqual(len(result['assignees']), 2)
        self.assertIn('tallyfy_user1', result['assignees'])
        self.assertIn('tallyfy_user2', result['assignees'])
    
    def test_item_with_subitems(self):
        """Test item with subitems transformation."""
        item = {
            'id': 'item789',
            'name': 'Task with Subitems',
            'subitems': [
                {
                    'id': 'sub1',
                    'name': 'Subtask 1',
                    'column_values': [
                        {
                            'type': 'status',
                            'text': 'Done'
                        }
                    ]
                },
                {
                    'id': 'sub2',
                    'name': 'Subtask 2',
                    'column_values': []
                }
            ]
        }
        
        result = self.transformer.transform_item_to_process(
            item,
            'blueprint123',
            {}
        )
        
        self.assertIn('checklists', result)
        self.assertEqual(len(result['checklists']), 2)
        self.assertTrue(result['checklists'][0]['checked'])  # Done status
        self.assertFalse(result['checklists'][1]['checked'])  # No status
    
    def test_updates_transformation(self):
        """Test item updates to comments transformation."""
        updates = [
            {
                'id': 'update1',
                'body': 'This is a comment',
                'created_at': '2024-01-10T12:00:00Z',
                'creator': {
                    'id': 'u1',
                    'name': 'John Doe'
                }
            }
        ]
        
        user_mapping = {'u1': 'tallyfy_user1'}
        
        result = self.transformer.transform_updates(updates, user_mapping)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'This is a comment')
        self.assertEqual(result[0]['author'], 'tallyfy_user1')
    
    def test_migration_report_generation(self):
        """Test migration report generation."""
        items = [
            {
                'id': '1',
                'name': 'Item 1',
                'state': 'active',
                'group': {'title': 'Group A'},
                'column_values': [
                    {'type': 'text'},
                    {'type': 'status'}
                ]
            },
            {
                'id': '2',
                'name': 'Item 2',
                'state': 'archived',
                'group': {'title': 'Group B'},
                'subitems': [{'id': 's1'}],
                'assets': [{'id': 'f1'}]
            }
        ]
        
        report = self.transformer.create_migration_report(items)
        
        self.assertEqual(report['total_items'], 2)
        self.assertEqual(report['state_distribution']['active'], 1)
        self.assertEqual(report['state_distribution']['archived'], 1)
        self.assertEqual(report['items_with_subitems'], 1)
        self.assertEqual(report['items_with_files'], 1)
        self.assertIn('Group A', report['groups'])
        self.assertIn('text', report['column_types_used'])


def run_tests():
    """Run all tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()