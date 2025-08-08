"""Transform Monday.com boards to Tallyfy blueprints."""

import logging
from typing import Dict, Any, List, Optional
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class BoardTransformer:
    """Transform Monday.com boards to Tallyfy blueprints.
    
    Handles the paradigm shift from Monday's hybrid views (Table/Kanban/Timeline/Calendar)
    to Tallyfy's sequential workflow model.
    """
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_board_to_blueprint(self, board: Dict[str, Any],
                                   items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Transform Monday.com board to Tallyfy blueprint.
        
        Args:
            board: Monday.com board object
            items: Optional list of board items for analysis
            
        Returns:
            Tallyfy blueprint object
        """
        board_id = board.get('id', '')
        board_name = board.get('name', 'Untitled Board')
        board_kind = board.get('board_kind', 'public')
        
        logger.info(f"Transforming board '{board_name}' (ID: {board_id}) to blueprint")
        
        # Determine transformation strategy based on board views
        views = board.get('views', [])
        primary_view = self._determine_primary_view(views)
        
        blueprint = {
            'name': board_name,
            'description': self._format_description(board, primary_view),
            'steps': self._create_workflow_steps(board, primary_view),
            'kick_off_form': self._create_kickoff_form(board),
            'tags': self._extract_tags(board),
            'permissions': self._transform_permissions(board),
            'metadata': {
                'source': 'monday',
                'original_id': board_id,
                'board_kind': board_kind,
                'workspace_id': board.get('workspace_id'),
                'primary_view': primary_view,
                'groups': [g.get('title') for g in board.get('groups', [])],
                'created_at': board.get('created_at'),
                'updated_at': board.get('updated_at')
            }
        }
        
        # Add workflow rules based on automations (if available)
        if board.get('automations'):
            blueprint['rules'] = self._document_automations(board['automations'])
        
        # Add migration notes for complex features
        blueprint['migration_notes'] = self._create_migration_notes(board)
        
        return blueprint
    
    def _determine_primary_view(self, views: List[Dict[str, Any]]) -> str:
        """Determine the primary view type used in the board.
        
        Args:
            views: List of board views
            
        Returns:
            Primary view type
        """
        if not views:
            return 'table'  # Default
        
        # Check for Kanban view (requires special transformation)
        for view in views:
            if view.get('type') == 'kanban':
                return 'kanban'
        
        # Check for Timeline/Gantt (requires dependency handling)
        for view in views:
            if view.get('type') in ['timeline', 'gantt']:
                return 'timeline'
        
        # Check for Calendar view
        for view in views:
            if view.get('type') == 'calendar':
                return 'calendar'
        
        # Default to table view
        return 'table'
    
    def _format_description(self, board: Dict[str, Any], primary_view: str) -> str:
        """Format board description with paradigm notes.
        
        Args:
            board: Monday.com board
            primary_view: Primary view type
            
        Returns:
            Formatted description
        """
        description = board.get('description', '')
        
        # Add paradigm shift warning based on view type
        if primary_view == 'kanban':
            paradigm_note = """

⚠️ **KANBAN VIEW TRANSFORMATION** ⚠️
This board used Kanban view in Monday.com. In Tallyfy:
- Each status/column becomes a sequential step
- Cards moving between columns becomes task progression
- Parallel work in columns becomes sequential tasks
- Train users on the new sequential flow
"""
        elif primary_view == 'timeline':
            paradigm_note = """

⚠️ **TIMELINE VIEW TRANSFORMATION** ⚠️
This board used Timeline/Gantt view in Monday.com. In Tallyfy:
- Timeline dependencies become sequential steps
- Parallel timelines become ordered tasks
- Date ranges preserved in task deadlines
- Visual timeline not available (use reporting instead)
"""
        elif primary_view == 'calendar':
            paradigm_note = """

⚠️ **CALENDAR VIEW TRANSFORMATION** ⚠️
This board used Calendar view in Monday.com. In Tallyfy:
- Calendar items become tasks with due dates
- Recurring events need manual configuration
- Date-based view not available (use filters instead)
"""
        else:
            paradigm_note = """

📋 **TABLE VIEW TRANSFORMATION**
This board used Table view in Monday.com. In Tallyfy:
- Each group becomes a process phase
- Items become process instances
- Columns become form fields
- Updates become task comments
"""
        
        # Add board metadata
        migration_note = f"\n\n---\n*Migrated from Monday.com {board.get('board_kind', 'board')}*"
        
        if board.get('workspace_id'):
            migration_note += f"\n*Workspace ID: {board['workspace_id']}*"
        
        owner = board.get('owner', {})
        if owner:
            migration_note += f"\n*Original Owner: {owner.get('name', 'Unknown')}*"
        
        return description + paradigm_note + migration_note
    
    def _create_workflow_steps(self, board: Dict[str, Any], primary_view: str) -> List[Dict[str, Any]]:
        """Create workflow steps based on board structure and view type.
        
        Args:
            board: Monday.com board
            primary_view: Primary view type
            
        Returns:
            List of Tallyfy steps
        """
        steps = []
        step_order = 1
        
        # Get groups (sections in the board)
        groups = board.get('groups', [])
        
        if primary_view == 'kanban':
            # For Kanban view, create steps based on status columns
            steps.extend(self._create_kanban_steps(board, step_order))
        elif primary_view == 'timeline':
            # For Timeline view, create steps based on dependencies
            steps.extend(self._create_timeline_steps(board, step_order))
        else:
            # For Table/Calendar views, create steps based on groups
            for group in groups:
                group_steps = self._create_group_steps(group, board, step_order)
                steps.extend(group_steps)
                step_order += len(group_steps)
        
        # Add final completion step
        steps.append({
            'order': len(steps) + 1,
            'name': 'Process Complete',
            'type': 'approval',
            'description': 'Final review and completion',
            "assignees_form": 'process_owner',
            'duration': 1,
            'form_fields': [
                {
                    'name': 'Completion Status',
                    'type': 'dropdown',
                    'required': True,
                    'options': [
                        {'value': 'completed', 'label': 'Completed Successfully'},
                        {'value': 'cancelled', 'label': 'Cancelled'},
                        {'value': 'on_hold', 'label': 'On Hold'}
                    ]
                },
                {
                    'name': 'Final Notes',
                    'type': 'textarea',
                    'required': False
                }
            ]
        })
        
        logger.info(f"Created {len(steps)} steps for board workflow")
        return steps
    
    def _create_kanban_steps(self, board: Dict[str, Any], start_order: int) -> List[Dict[str, Any]]:
        """Create steps for Kanban view transformation.
        
        Args:
            board: Monday.com board
            start_order: Starting step order
            
        Returns:
            List of steps for Kanban workflow
        """
        steps = []
        order = start_order
        
        # Find status columns
        status_columns = []
        for column in board.get('columns', []):
            if column.get('type') == 'status':
                status_columns.append(column)
        
        if not status_columns:
            # No status columns, use groups instead
            return self._create_group_based_steps(board, start_order)
        
        # Get status options from the main status column
        main_status = status_columns[0] if status_columns else None
        if main_status:
            import json
            try:
                settings = json.loads(main_status.get('settings_str', '{}'))
                status_labels = settings.get('labels', {})
                
                # Create step for each status
                for index, label in status_labels.items():
                    step = {
                        'order': order,
                        'name': f"Status: {label}",
                        'type': 'task',
                        'description': f"Work on items in '{label}' status",
                        "assignees_form": 'assigned_member',
                        'duration': 2,
                        'form_fields': [
                            {
                                'name': 'Status Update',
                                'type': 'textarea',
                                'description': f'Progress update for {label} status',
                                'required': False
                            },
                            {
                                'name': 'Ready to Progress',
                                'type': 'radio',
                                'description': 'Is this ready to move to the next status?',
                                'required': True,
                                'options': [
                                    {'value': 'yes', 'label': 'Yes, ready to progress'},
                                    {'value': 'no', 'label': 'No, needs more work'}
                                ]
                            }
                        ],
                        'metadata': {
                            'status_index': index,
                            'status_label': label,
                            'is_kanban_column': True
                        }
                    }
                    steps.append(step)
                    order += 1
            except:
                logger.warning("Failed to parse status settings, using default steps")
        
        return steps
    
    def _create_timeline_steps(self, board: Dict[str, Any], start_order: int) -> List[Dict[str, Any]]:
        """Create steps for Timeline view transformation.
        
        Args:
            board: Monday.com board
            start_order: Starting step order
            
        Returns:
            List of steps for timeline workflow
        """
        steps = []
        order = start_order
        
        # Find timeline and dependency columns
        timeline_columns = []
        dependency_columns = []
        
        for column in board.get('columns', []):
            if column.get('type') == 'timeline':
                timeline_columns.append(column)
            elif column.get('type') == 'dependency':
                dependency_columns.append(column)
        
        # Create phase-based steps
        groups = board.get('groups', [])
        for group in groups:
            # Phase start
            steps.append({
                'order': order,
                'name': f"{group.get('title', 'Phase')} - Start",
                'type': 'task',
                'description': f"Begin work on {group.get('title', 'phase')}",
                "assignees_form": 'assigned_member',
                'duration': 0,
                'metadata': {
                    'group_id': group.get('id'),
                    'is_phase_start': True
                }
            })
            order += 1
            
            # Phase work
            steps.append({
                'order': order,
                'name': f"{group.get('title', 'Phase')} - Work",
                'type': 'task',
                'description': f"Complete tasks in {group.get('title', 'phase')}",
                "assignees_form": 'assigned_member',
                'duration': 5,
                'form_fields': self._create_group_fields(board, group),
                'metadata': {
                    'group_id': group.get('id'),
                    'is_phase_work': True
                }
            })
            order += 1
            
            # Phase review
            steps.append({
                'order': order,
                'name': f"{group.get('title', 'Phase')} - Review",
                'type': 'approval',
                'description': f"Review and approve {group.get('title', 'phase')}",
                "assignees_form": 'process_owner',
                'duration': 1,
                'form_fields': [
                    {
                        'name': 'Phase Complete',
                        'type': 'radio',
                        'required': True,
                        'options': [
                            {'value': 'approved', 'label': 'Approved'},
                            {'value': 'needs_revision', 'label': 'Needs Revision'}
                        ]
                    }
                ],
                'metadata': {
                    'group_id': group.get('id'),
                    'is_phase_review': True
                }
            })
            order += 1
        
        return steps
    
    def _create_group_steps(self, group: Dict[str, Any], board: Dict[str, Any],
                          start_order: int) -> List[Dict[str, Any]]:
        """Create steps for a board group.
        
        Args:
            group: Monday.com group
            board: Parent board
            start_order: Starting step order
            
        Returns:
            List of steps for the group
        """
        steps = []
        
        # Create a task step for the group
        step = {
            'order': start_order,
            'name': group.get('title', f'Group {start_order}'),
            'type': 'task',
            'description': f"Complete items in {group.get('title', 'group')}",
            "assignees_form": 'assigned_member',
            'duration': 3,
            'form_fields': self._create_group_fields(board, group),
            'metadata': {
                'group_id': group.get('id'),
                'group_color': group.get('color'),
                'group_position': group.get('position')
            }
        }
        
        steps.append(step)
        
        return steps
    
    def _create_group_based_steps(self, board: Dict[str, Any], start_order: int) -> List[Dict[str, Any]]:
        """Create steps based on board groups when no status columns exist.
        
        Args:
            board: Monday.com board
            start_order: Starting step order
            
        Returns:
            List of steps
        """
        steps = []
        order = start_order
        
        groups = board.get('groups', [])
        for group in groups:
            step = {
                'order': order,
                'name': group.get('title', f'Step {order}'),
                'type': 'task',
                'description': f"Work on items in {group.get('title', 'this group')}",
                "assignees_form": 'assigned_member',
                'duration': 3,
                'form_fields': self._create_group_fields(board, group),
                'metadata': {
                    'group_id': group.get('id'),
                    'group_color': group.get('color')
                }
            }
            steps.append(step)
            order += 1
        
        return steps
    
    def _create_group_fields(self, board: Dict[str, Any], group: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create form fields for a group.
        
        Args:
            board: Monday.com board
            group: Board group
            
        Returns:
            List of form fields
        """
        fields = []
        
        # Add field for each non-system column
        for column in board.get('columns', []):
            column_type = column.get('type', '')
            
            # Skip system columns
            if column_type in ['name', 'creation_log', 'last_updated', 'auto_number', 'item_id']:
                continue
            
            # Transform column to field
            field = self.field_transformer.transform_column(column)
            fields.append(field)
            
            # Add end date field for timeline columns
            if column_type == 'timeline':
                end_field = self.field_transformer.create_timeline_end_field(column)
                fields.append(end_field)
        
        # Add group-specific notes field
        fields.append({
            'name': f"{group.get('title', 'Group')} Notes",
            'type': 'textarea',
            'description': 'Additional notes for this group',
            'required': False
        })
        
        return fields
    
    def _create_kickoff_form(self, board: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create kick-off form from board columns.
        
        Args:
            board: Monday.com board
            
        Returns:
            List of kick-off form fields
        """
        form_fields = []
        
        # Add item name field
        form_fields.append({
            'name': 'Item Name',
            'type': 'text',
            'description': 'Name for this item/task',
            'required': True
        })
        
        # Add group selector if multiple groups
        groups = board.get('groups', [])
        if len(groups) > 1:
            form_fields.append({
                'name': 'Group',
                'type': 'dropdown',
                'description': 'Select the group for this item',
                'required': True,
                'options': [
                    {'value': g.get('id', ''), 'label': g.get('title', '')}
                    for g in groups
                ]
            })
        
        # Add fields for key columns
        priority_columns = ['status', 'people', 'date', 'timeline', 'priority']
        
        for column in board.get('columns', []):
            column_type = column.get('type', '')
            
            # Include priority columns in kick-off form
            if column_type in priority_columns:
                field = self.field_transformer.transform_column(column)
                form_fields.append(field)
        
        # Add description field
        form_fields.append({
            'name': 'Description',
            'type': 'textarea',
            'description': 'Detailed description',
            'required': False
        })
        
        # Add priority field if not already present
        if not any(f['name'] == 'Priority' for f in form_fields):
            form_fields.append({
                'name': 'Priority',
                'type': 'dropdown',
                'description': 'Task priority',
                'required': False,
                'options': [
                    {'value': 'critical', 'label': 'Critical'},
                    {'value': 'high', 'label': 'High'},
                    {'value': 'medium', 'label': 'Medium'},
                    {'value': 'low', 'label': 'Low'}
                ],
                'default_value': 'medium'
            })
        
        return form_fields
    
    def _extract_tags(self, board: Dict[str, Any]) -> List[str]:
        """Extract tags from board.
        
        Args:
            board: Monday.com board
            
        Returns:
            List of tags
        """
        tags = []
        
        # Add board tags
        if board.get('tags'):
            tags.extend(board['tags'])
        
        # Add metadata tags
        tags.append('source:monday')
        tags.append(f"board-kind:{board.get('board_kind', 'public')}")
        
        # Add view tags
        for view in board.get('views', []):
            tags.append(f"view:{view.get('type', 'unknown')}")
        
        # Add group names as tags
        for group in board.get('groups', []):
            group_title = group.get('title', '').lower().replace(' ', '-')
            if group_title:
                tags.append(f"group:{group_title}")
        
        return tags
    
    def _transform_permissions(self, board: Dict[str, Any]) -> Dict[str, Any]:
        """Transform board permissions.
        
        Args:
            board: Monday.com board
            
        Returns:
            Tallyfy permission configuration
        """
        permissions = board.get('permissions', {})
        
        # Map Monday.com permissions to Tallyfy
        return {
            'visibility': 'private' if board.get('board_kind') == 'private' else 'organization',
            'admins': [],  # Would need to map from board owners
            'members': [],  # Would need to map from board members
            'viewers': [],  # Would need to map from board viewers
            'can_edit': permissions.get('everyone_can_edit', False)
        }
    
    def _document_automations(self, automations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Document automations for manual recreation.
        
        Args:
            automations: Board automations
            
        Returns:
            List of documented automation rules
        """
        rules = []
        
        # Monday.com automations are not fully exposed via API
        # Document what we know for manual recreation
        
        rules.append({
            'name': 'Automation Documentation',
            'description': 'Monday.com automations need manual recreation in Tallyfy',
            'type': 'documentation',
            'note': 'Review original board automations and recreate using Tallyfy rules'
        })
        
        return rules
    
    def _create_migration_notes(self, board: Dict[str, Any]) -> str:
        """Create detailed migration notes.
        
        Args:
            board: Monday.com board
            
        Returns:
            Migration notes text
        """
        notes = """
## Migration Notes

### Board Structure
"""
        
        # Document groups
        groups = board.get('groups', [])
        if groups:
            notes += f"- **Groups**: {len(groups)} groups migrated as workflow phases\n"
            for group in groups:
                notes += f"  - {group.get('title', 'Unnamed')}\n"
        
        # Document columns
        columns = board.get('columns', [])
        column_types = {}
        for col in columns:
            col_type = col.get('type', 'unknown')
            column_types[col_type] = column_types.get(col_type, 0) + 1
        
        notes += f"\n### Column Types ({len(columns)} total)\n"
        for col_type, count in column_types.items():
            notes += f"- {col_type}: {count}\n"
        
        # Document views
        views = board.get('views', [])
        if views:
            notes += f"\n### Original Views ({len(views)} total)\n"
            for view in views:
                notes += f"- {view.get('name', 'Unnamed')} ({view.get('type', 'unknown')})\n"
        
        # Add manual configuration notes
        notes += """
### Manual Configuration Required

1. **Automations**: Review and recreate board automations as Tallyfy rules
2. **Mirror Columns**: Set up cross-blueprint references for mirror fields
3. **Formula Fields**: Recreate calculations using Tallyfy's formula capabilities
4. **Connect Boards**: Link related blueprints manually
5. **Subitems**: Review subitem conversion to checklists
6. **Integrations**: Reconnect third-party integrations

### User Training Points

- **View Changes**: Train users on sequential workflow vs. previous views
- **Status Updates**: New method for updating task status
- **Collaboration**: Use comments instead of updates
- **File Management**: File uploads now attached to specific tasks
"""
        
        return notes