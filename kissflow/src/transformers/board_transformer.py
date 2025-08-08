"""Transform Kissflow boards (Kanban) to Tallyfy blueprints."""

import logging
from typing import Dict, Any, List, Optional
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class BoardTransformer:
    """Transform Kissflow Kanban boards to Tallyfy sequential workflows.
    
    This handles the critical paradigm shift from Kanban to Sequential.
    """
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_board_to_blueprint(self, board: Dict[str, Any],
                                   board_items: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transform Kissflow board to Tallyfy blueprint.
        
        PARADIGM SHIFT: Kanban columns become sequential step groups.
        Each column becomes 3 steps: Entry, Work, Exit
        
        Args:
            board: Kissflow board object
            board_items: Optional list of board items for analysis
            
        Returns:
            Tallyfy blueprint object
        """
        logger.info(f"Transforming board '{board.get('Name')}' to blueprint (Kanban→Sequential paradigm shift)")
        
        blueprint = {
            'name': board.get('Name', 'Untitled Board'),
            'description': self._format_description(board),
            'steps': self._transform_columns_to_steps(board),
            'kick_off_form': self._create_kickoff_form(board),
            'tags': self._extract_tags(board),
            'metadata': {
                'source': 'kissflow',
                'original_id': board.get('Id'),
                'original_type': 'board',
                'paradigm_shift': 'kanban_to_sequential',
                'created_at': board.get('CreatedAt'),
                'modified_at': board.get('ModifiedAt'),
                'columns': [col.get('Name') for col in board.get('Columns', [])]
            }
        }
        
        # Add workflow rules based on board automation
        if board.get('Automations'):
            blueprint['rules'] = self._transform_board_automations(board['Automations'])
        
        # Add migration guidance
        blueprint['migration_notes'] = self._create_migration_notes(board)
        
        return blueprint
    
    def _format_description(self, board: Dict[str, Any]) -> str:
        """Format board description with paradigm shift warning.
        
        Args:
            board: Kissflow board
            
        Returns:
            Formatted description with migration notes
        """
        description = board.get('Description', '')
        
        # Add critical paradigm shift warning
        paradigm_warning = """

⚠️ **PARADIGM SHIFT NOTICE** ⚠️
This workflow was migrated from a Kissflow Kanban board to Tallyfy's sequential process model.

**Original Kanban Structure:**
"""
        
        # List original columns
        for col in board.get('Columns', []):
            paradigm_warning += f"\n• {col.get('Name', 'Column')}"
            if col.get('WIP_Limit'):
                paradigm_warning += f" (WIP Limit: {col['WIP_Limit']})"
        
        paradigm_warning += """

**New Sequential Structure:**
Each Kanban column has been converted to 3 sequential steps:
1. Entry - Notification when work enters this phase
2. Work - The actual tasks for this phase
3. Exit - Approval to move to next phase

**Training Required:** Users familiar with dragging cards between columns will need training on sequential task completion.
"""
        
        migration_note = f"\n\n---\n*Migrated from Kissflow Board*"
        
        if board.get('Category'):
            migration_note += f"\n*Category: {board['Category']}*"
        
        if board.get('Type'):
            migration_note += f"\n*Board Type: {board['Type']}*"
        
        return description + paradigm_warning + migration_note
    
    def _transform_columns_to_steps(self, board: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform Kanban columns to sequential steps.
        
        CRITICAL: Each column becomes 3 steps for proper workflow control.
        
        Args:
            board: Board definition
            
        Returns:
            List of sequential steps
        """
        steps = []
        step_order = 1
        columns = board.get('Columns', [])
        
        # Add initial card creation step
        steps.append({
            'order': step_order,
            'name': 'Create New Item',
            'type': 'task',
            'description': f"Create a new item for the {board.get('Name', 'board')} workflow",
            "assignees_form": 'process_initiator',
            'form_fields': self._get_card_fields(board),
            'duration': 0,
            'metadata': {
                'is_creation_step': True
            }
        })
        step_order += 1
        
        # Transform each column to step group
        for col_idx, column in enumerate(columns):
            column_name = column.get('Name', f'Column {col_idx + 1}')
            column_id = column.get('Id', f'col_{col_idx}')
            
            # Step 1: Entry notification
            entry_step = {
                'order': step_order,
                'name': f"{column_name} - Entry",
                'type': 'task',
                'description': f"Work has entered the '{column_name}' phase",
                "assignees_form": self._get_column_assignee(column),
                'duration': 0,
                'form_fields': [
                    {
                        'name': 'Entry Notes',
                        'type': 'textarea',
                        'description': f'Notes for entering {column_name} phase',
                        'required': False
                    }
                ],
                'metadata': {
                    'column_id': column_id,
                    'column_phase': 'entry',
                    'wip_limit': column.get('WIP_Limit')
                }
            }
            steps.append(entry_step)
            step_order += 1
            
            # Step 2: Actual work
            work_step = {
                'order': step_order,
                'name': f"{column_name} - Work",
                'type': 'task',
                'description': self._get_column_work_description(column),
                "assignees_form": self._get_column_assignee(column),
                'duration': self._calculate_column_duration(column),
                'form_fields': self._get_column_fields(column),
                'metadata': {
                    'column_id': column_id,
                    'column_phase': 'work',
                    'column_rules': column.get('Rules', [])
                }
            }
            
            # Add checklist for column requirements
            if column.get('Requirements'):
                checklist_field = {
                    'name': f'{column_name} Requirements',
                    'type': 'multiselect',
                    'description': 'Complete all requirements before proceeding',
                    'required': True,
                    'options': [
                        {'value': req.get('Id', str(i)), 'label': req.get('Name', f'Requirement {i+1}')}
                        for i, req in enumerate(column.get('Requirements', []))
                    ]
                }
                work_step['form_fields'].append(checklist_field)
            
            steps.append(work_step)
            step_order += 1
            
            # Step 3: Exit approval (except for final column)
            if col_idx < len(columns) - 1:
                exit_step = {
                    'order': step_order,
                    'name': f"{column_name} - Complete",
                    'type': 'approval',
                    'description': f"Approve completion of '{column_name}' phase and move to next",
                    "assignees_form": self._get_column_approver(column),
                    'duration': 1,
                    'form_fields': [
                        {
                            'name': 'Completion Review',
                            'type': 'radio',
                            'description': 'Is this phase complete?',
                            'required': True,
                            'options': [
                                {'value': 'approved', 'label': 'Approved - Move to Next Phase'},
                                {'value': 'needs_work', 'label': 'Needs More Work'},
                                {'value': 'rejected', 'label': 'Rejected - Return to Previous Phase'}
                            ]
                        },
                        {
                            'name': 'Review Comments',
                            'type': 'textarea',
                            'description': 'Comments on the completion',
                            'required': False
                        }
                    ],
                    'metadata': {
                        'column_id': column_id,
                        'column_phase': 'exit',
                        'next_column': columns[col_idx + 1].get('Name') if col_idx + 1 < len(columns) else None
                    }
                }
                steps.append(exit_step)
                step_order += 1
            else:
                # Final column - completion step
                final_step = {
                    'order': step_order,
                    'name': 'Process Complete',
                    'type': 'approval',
                    'description': 'Final approval and process completion',
                    "assignees_form": 'process_owner',
                    'duration': 1,
                    'form_fields': [
                        {
                            'name': 'Final Status',
                            'type': 'dropdown',
                            'required': True,
                            'options': [
                                {'value': 'completed', 'label': 'Completed Successfully'},
                                {'value': 'cancelled', 'label': 'Cancelled'},
                                {'value': 'failed', 'label': 'Failed'}
                            ]
                        },
                        {
                            'name': 'Completion Summary',
                            'type': 'textarea',
                            'required': True
                        }
                    ],
                    'metadata': {
                        'is_final_step': True
                    }
                }
                steps.append(final_step)
                step_order += 1
        
        logger.info(f"Transformed {len(columns)} Kanban columns into {len(steps)} sequential steps")
        return steps
    
    def _create_kickoff_form(self, board: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create kick-off form for board workflow.
        
        Args:
            board: Kissflow board
            
        Returns:
            List of form fields
        """
        form_fields = []
        
        # Basic item information
        form_fields.append({
            'name': 'Item Title',
            'type': 'text',
            'description': 'Title for this work item',
            'required': True
        })
        
        form_fields.append({
            'name': 'Item Description',
            'type': 'textarea',
            'description': 'Detailed description of the work',
            'required': True
        })
        
        form_fields.append({
            'name': 'Priority',
            'type': 'dropdown',
            'description': 'Item priority',
            'required': True,
            'options': [
                {'value': 'critical', 'label': 'Critical'},
                {'value': 'high', 'label': 'High'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'low', 'label': 'Low'}
            ],
            'default_value': 'medium'
        })
        
        form_fields.append({
            'name': 'Due Date',
            'type': 'date',
            'description': 'When should this be completed?',
            'required': False
        })
        
        # Add board-specific fields
        if board.get('CustomFields'):
            for field in board['CustomFields']:
                transformed_field = self.field_transformer.transform_field_definition(field)
                form_fields.append(transformed_field)
        
        # Add labels/tags field
        if board.get('Labels'):
            form_fields.append({
                'name': 'Labels',
                'type': 'multiselect',
                'description': 'Apply relevant labels',
                'required': False,
                'options': [
                    {'value': label.get('Id', ''), 'label': label.get('Name', '')}
                    for label in board.get('Labels', [])
                ]
            })
        
        return form_fields
    
    def _get_card_fields(self, board: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get fields for card creation.
        
        Args:
            board: Board definition
            
        Returns:
            List of form fields
        """
        fields = []
        
        # Standard card fields
        card_template = board.get('CardTemplate', {})
        
        for field in card_template.get('Fields', []):
            transformed_field = self.field_transformer.transform_field_definition(field)
            fields.append(transformed_field)
        
        return fields
    
    def _get_column_fields(self, column: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get fields specific to a column.
        
        Args:
            column: Column definition
            
        Returns:
            List of form fields
        """
        fields = []
        
        # Column-specific fields
        for field in column.get('Fields', []):
            transformed_field = self.field_transformer.transform_field_definition(field)
            fields.append(transformed_field)
        
        # Add status update field
        fields.append({
            'name': 'Status Update',
            'type': 'textarea',
            'description': f'Progress update for {column.get("Name", "this phase")}',
            'required': False
        })
        
        return fields
    
    def _get_column_work_description(self, column: Dict[str, Any]) -> str:
        """Get work description for column.
        
        Args:
            column: Column definition
            
        Returns:
            Description text
        """
        description = column.get('Description', f'Complete work in {column.get("Name", "this phase")}')
        
        if column.get('WIP_Limit'):
            description += f"\n\n**Note**: Original WIP limit was {column['WIP_Limit']} items"
        
        if column.get('Instructions'):
            description += f"\n\n**Instructions:**\n{column['Instructions']}"
        
        return description
    
    def _get_column_assignee(self, column: Dict[str, Any]) -> str:
        """Get default assignee for column work.
        
        Args:
            column: Column definition
            
        Returns:
            Assignee string
        """
        if column.get('DefaultAssignee'):
            assignee = column['DefaultAssignee']
            if isinstance(assignee, dict):
                if assignee.get('Type') == 'group':
                    return f"group:{assignee.get('Id', '')}"
                elif assignee.get('Type') == 'role':
                    return f"role:{assignee.get('Id', '')}"
                else:
                    return f"member:{assignee.get('Id', '')}"
            return f"member:{assignee}"
        
        return 'process_owner'
    
    def _get_column_approver(self, column: Dict[str, Any]) -> str:
        """Get approver for column exit.
        
        Args:
            column: Column definition
            
        Returns:
            Approver assignee string
        """
        if column.get('Approver'):
            return f"member:{column['Approver']}"
        
        # Default to column assignee_picker's manager or process owner
        return 'process_owner'
    
    def _calculate_column_duration(self, column: Dict[str, Any]) -> int:
        """Calculate expected duration for column work.
        
        Args:
            column: Column definition
            
        Returns:
            Duration in days
        """
        if column.get('SLA'):
            # Convert hours to days
            return max(1, int(column['SLA'] / 24))
        
        # Estimate based on column type
        column_name = column.get('Name', '').lower()
        if 'review' in column_name or 'approval' in column_name:
            return 2
        elif 'done' in column_name or 'complete' in column_name:
            return 0
        else:
            return 3  # Default work duration
    
    def _transform_board_automations(self, automations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform board automations to Tallyfy rules.
        
        Args:
            automations: Board automation rules
            
        Returns:
            List of Tallyfy rules
        """
        rules = []
        
        for automation in automations:
            # Card movement automations need special handling
            if automation.get('Type') == 'card_movement':
                rule = {
                    'name': f"Auto-advance: {automation.get('Name', 'Card Movement')}",
                    'description': f"Originally moved cards from {automation.get('FromColumn')} to {automation.get('ToColumn')}",
                    'trigger': {
                        'type': 'field_value',
                        'field': automation.get('TriggerField', ''),
                        'value': automation.get('TriggerValue', '')
                    },
                    'actions': [
                        {
                            'type': 'complete_task',
                            'note': 'Auto-completed based on Kissflow board automation'
                        }
                    ]
                }
                rules.append(rule)
            else:
                # Standard automation
                rule = {
                    'name': automation.get('Name', 'Automation'),
                    'description': automation.get('Description', ''),
                    'trigger': automation.get('Trigger', {}),
                    'actions': automation.get('Actions', [])
                }
                rules.append(rule)
        
        return rules
    
    def _extract_tags(self, board: Dict[str, Any]) -> List[str]:
        """Extract tags from board.
        
        Args:
            board: Kissflow board
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add board metadata as tags
        tags.append('type:board')
        tags.append('paradigm:kanban-to-sequential')
        tags.append('source:kissflow')
        
        if board.get('Category'):
            tags.append(f"category:{board['Category']}")
        
        if board.get('Type'):
            tags.append(f"board-type:{board['Type']}")
        
        # Add column names as tags for searchability
        for column in board.get('Columns', []):
            tags.append(f"column:{column.get('Name', '').lower().replace(' ', '-')}")
        
        return tags
    
    def _create_migration_notes(self, board: Dict[str, Any]) -> str:
        """Create detailed migration notes for training.
        
        Args:
            board: Kissflow board
            
        Returns:
            Migration guidance text
        """
        notes = """
## Migration Training Guide

### Key Differences from Kissflow Board

**Kissflow Board (Kanban)**:
- Cards moved between columns by dragging
- Multiple cards could be in any column
- Visual board view showed all cards at once
- WIP limits controlled column capacity

**Tallyfy Process (Sequential)**:
- Tasks complete in order
- One process instance flows through all steps
- Timeline view shows progress
- No parallel cards in same phase

### User Training Points

1. **No More Dragging**: Click "Complete" to advance instead of dragging cards
2. **Sequential Flow**: Work moves through phases in order
3. **Approval Gates**: Each phase now has explicit approval before moving forward
4. **Single Instance**: Focus on one process at a time vs multiple cards

### Workflow Equivalents

| Kissflow Action | Tallyfy Equivalent |
|----------------|-------------------|
| Create Card | Start New Process |
| Move Card to Column | Complete Current Step |
| Add Card Comment | Add Task Comment |
| Assign Card | Assign Task |
| Archive Card | Complete Process |
| Filter Board | Filter Process List |
| Board View | Timeline View |

### Recommended Training

- 30-minute orientation for all users
- Practice run with test process
- Document specific column-to-step mappings
- Create quick reference guide
"""
        return notes