"""Tests for Kissflow transformers."""

import pytest
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.transformers.field_transformer import FieldTransformer
from src.transformers.process_transformer import ProcessTransformer
from src.transformers.board_transformer import BoardTransformer
from src.transformers.user_transformer import UserTransformer


class TestFieldTransformer:
    """Test field transformation logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = FieldTransformer()
    
    def test_text_field_transformation(self):
        """Test basic text field transformation."""
        kissflow_field = {
            'Id': 'field_1',
            'Name': 'Employee Name',
            'Type': 'text',
            'Required': True,
            'Description': 'Full name of employee'
        }
        
        result = self.transformer.transform_field_definition(kissflow_field)
        
        assert result['name'] == 'Employee Name'
        assert result['type'] == 'short_text'
        assert result['required'] == True
        assert result['alias'] == 'kissflow_field_1'
    
    def test_dropdown_field_transformation(self):
        """Test dropdown field with options."""
        kissflow_field = {
            'Id': 'field_2',
            'Name': 'Department',
            'Type': 'dropdown',
            'Required': False,
            'Options': [
                {'Value': 'hr', 'Label': 'Human Resources'},
                {'Value': 'it', 'Label': 'Information Technology'},
                {'Value': 'sales', 'Label': 'Sales'}
            ]
        }
        
        result = self.transformer.transform_field_definition(kissflow_field)
        
        assert result['type'] == 'dropdown'
        assert len(result['options']) == 3
        assert result['options'][0]['value'] == 'hr'
        assert result['options'][0]['label'] == 'Human Resources'
    
    def test_child_table_transformation(self):
        """Test complex child table transformation."""
        kissflow_field = {
            'Id': 'table_1',
            'Name': 'Line Items',
            'Type': 'child_table',
            'Columns': [
                {'Name': 'Product', 'Type': 'text', 'Required': True},
                {'Name': 'Quantity', 'Type': 'number', 'Required': True},
                {'Name': 'Price', 'Type': 'currency', 'Required': True}
            ],
            'MinRows': 1,
            'MaxRows': 100
        }
        
        result = self.transformer.transform_field_definition(kissflow_field)
        
        assert result['type'] == 'table'
        assert len(result['columns']) == 3
        assert result['min_rows'] == 1
        assert result['max_rows'] == 100  # Capped at Tallyfy limit
    
    def test_formula_field_transformation(self):
        """Test formula field becomes read-only text."""
        kissflow_field = {
            'Id': 'formula_1',
            'Name': 'Total',
            'Type': 'formula',
            'Formula': 'SUM(LineItems.Amount)',
            'Description': 'Calculated total'
        }
        
        result = self.transformer.transform_field_definition(kissflow_field)
        
        assert result['type'] == 'short_text'
        assert result['readonly'] == True
        assert 'Calculated field' in result['description']


class TestBoardTransformer:
    """Test Kanban to Sequential transformation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = BoardTransformer()
    
    def test_kanban_to_sequential_transformation(self):
        """Test critical Kanban → Sequential paradigm shift."""
        board = {
            'Id': 'board_1',
            'Name': 'Development Board',
            'Description': 'Software development workflow',
            'Columns': [
                {'Id': 'col_1', 'Name': 'Backlog', 'Order': 0, 'WIP_Limit': None},
                {'Id': 'col_2', 'Name': 'In Progress', 'Order': 1, 'WIP_Limit': 3},
                {'Id': 'col_3', 'Name': 'Review', 'Order': 2, 'WIP_Limit': 2},
                {'Id': 'col_4', 'Name': 'Done', 'Order': 3, 'WIP_Limit': None}
            ]
        }
        
        result = self.transformer.transform_board_to_blueprint(board)
        
        # Check paradigm shift warning in description
        assert 'PARADIGM SHIFT NOTICE' in result['description']
        assert 'Kanban→Sequential' in result['metadata']['paradigm_shift']
        
        # Verify step multiplication (4 columns × 3 steps + initial + final)
        # Initial creation + (4 columns × 3 steps) + final completion = 14 steps
        assert len(result['steps']) >= 13  # At least 13 steps
        
        # Check for Entry, Work, Exit pattern
        step_names = [step['name'] for step in result['steps']]
        assert 'Backlog - Entry' in step_names
        assert 'Backlog - Work' in step_names
        assert 'In Progress - Entry' in step_names
        assert 'In Progress - Work' in step_names
    
    def test_wip_limit_preservation(self):
        """Test WIP limits are preserved in metadata."""
        board = {
            'Id': 'board_2',
            'Name': 'Support Board',
            'Columns': [
                {'Id': 'col_1', 'Name': 'Queue', 'WIP_Limit': 10},
                {'Id': 'col_2', 'Name': 'Working', 'WIP_Limit': 5}
            ]
        }
        
        result = self.transformer.transform_board_to_blueprint(board)
        
        # Find Working - Entry step
        working_entry = next(
            (s for s in result['steps'] if s['name'] == 'Working - Entry'),
            None
        )
        
        assert working_entry is not None
        assert working_entry['metadata']['wip_limit'] == 5


class TestUserTransformer:
    """Test user and role transformation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = UserTransformer()
    
    def test_admin_role_mapping(self):
        """Test admin roles map correctly."""
        kissflow_user = {
            'Id': 'user_1',
            'Email': 'admin@company.com',
            'FirstName': 'John',
            'LastName': 'Admin',
            'Role': 'super_admin',
            'Status': 'active'
        }
        
        result = self.transformer.transform_user(kissflow_user)
        
        assert result['email'] == 'admin@company.com'
        assert result['role'] == 'admin'
        assert result['active'] == True
    
    def test_developer_becomes_admin(self):
        """Test developers are treated as admins."""
        kissflow_user = {
            'Id': 'user_2',
            'Email': 'dev@company.com',
            'Role': 'developer',
            'Status': 'active'
        }
        
        result = self.transformer.transform_user(kissflow_user)
        
        assert result['role'] == 'admin'  # Developers → Admins
    
    def test_department_group_creation(self):
        """Test department-based groups."""
        users = [
            {'Id': 'u1', 'Department': 'Sales'},
            {'Id': 'u2', 'Department': 'Sales'},
            {'Id': 'u3', 'Department': 'Marketing'}
        ]
        
        groups = self.transformer.create_department_groups(users)
        
        assert len(groups) == 2  # Sales and Marketing
        
        sales_group = next(g for g in groups if 'Sales' in g['name'])
        assert len(sales_group['members']) == 2
        assert sales_group['name'].startswith('dept_')


class TestProcessTransformer:
    """Test process transformation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = ProcessTransformer()
    
    def test_basic_process_transformation(self):
        """Test simple process to blueprint transformation."""
        process = {
            'Id': 'proc_1',
            'Name': 'Expense Approval',
            'Description': 'Employee expense approval workflow',
            'Category': 'Finance',
            'Status': 'active'
        }
        
        fields = [
            {'Id': 'f1', 'Name': 'Amount', 'Type': 'currency', 'Required': True},
            {'Id': 'f2', 'Name': 'Description', 'Type': 'textarea', 'Required': True}
        ]
        
        workflow = {
            'Steps': [
                {'Id': 's1', 'Name': 'Submit', 'Type': 'task', 'Order': 1},
                {'Id': 's2', 'Name': 'Manager Approval', 'Type': 'approval', 'Order': 2},
                {'Id': 's3', 'Name': 'Finance Review', 'Type': 'task', 'Order': 3}
            ]
        }
        
        result = self.transformer.transform_process_to_blueprint(
            process, fields, workflow
        )
        
        assert result['name'] == 'Expense Approval'
        assert len(result['steps']) == 3
        assert result['steps'][1]['type'] == 'approval'
        assert 'category:Finance' in result['tags']
    
    def test_decision_point_transformation(self):
        """Test decision points become multiple steps."""
        process = {'Id': 'proc_2', 'Name': 'Decision Process'}
        fields = []
        
        workflow = {
            'Steps': [
                {
                    'Id': 'd1',
                    'Name': 'Amount Check',
                    'Type': 'decision',
                    'Branches': [
                        {'Id': 'b1', 'Name': 'Under $1000', 'Condition': 'Amount < 1000'},
                        {'Id': 'b2', 'Name': 'Over $1000', 'Condition': 'Amount >= 1000'}
                    ]
                }
            ]
        }
        
        result = self.transformer.transform_process_to_blueprint(
            process, fields, workflow
        )
        
        # Decision creates multiple steps (decision + branches)
        assert len(result['steps']) > 1
        
        # Find decision step
        decision_step = next(
            (s for s in result['steps'] if 'Decision' in s['name']),
            None
        )
        assert decision_step is not None
        assert decision_step['type'] == 'approval'  # Decisions become approvals


def test_integration_scenario():
    """Test complete migration scenario."""
    # This would test the full migration flow
    # Simplified for demonstration
    
    # Create transformers
    field_transformer = FieldTransformer()
    board_transformer = BoardTransformer()
    
    # Test board with complex fields
    board = {
        'Id': 'board_test',
        'Name': 'Project Board',
        'Columns': [
            {'Name': 'Todo', 'Order': 0},
            {'Name': 'Done', 'Order': 1}
        ],
        'CustomFields': [
            {'Id': 'cf1', 'Name': 'Priority', 'Type': 'dropdown',
             'Options': [{'Value': 'high', 'Label': 'High'}]}
        ]
    }
    
    blueprint = board_transformer.transform_board_to_blueprint(board)
    
    # Verify transformation completeness
    assert blueprint is not None
    assert 'steps' in blueprint
    assert 'kick_off_form' in blueprint
    assert 'migration_notes' in blueprint


if __name__ == '__main__':
    pytest.main([__file__, '-v'])