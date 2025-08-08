"""Transform Asana projects/checklists to Tallyfy blueprints."""

import logging
from typing import Dict, Any, List, Optional
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class TemplateTransformer:
    """Transform Asana project templates to Tallyfy blueprints."""
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_project_to_blueprint(self, project: Dict[str, Any],
                                      sections: List[Dict[str, Any]],
                                      tasks: List[Dict[str, Any]],
                                      custom_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform Asana project to Tallyfy blueprint.
        
        Args:
            project: Asana project object
            sections: List of project sections
            tasks: List of project tasks
            custom_fields: List of custom field definitions
            
        Returns:
            Tallyfy blueprint object
        """
        logger.info(f"Transforming project '{project.get('name')}' to blueprint")
        
        # Handle different project layouts (list, board, timeline, calendar)
        layout = project.get('layout', 'list')
        
        blueprint = {
            'name': project.get('name', 'Untitled Project'),
            'description': self._format_description(project, layout),
            'steps': [],
            'kick_off_form': self._create_kickoff_form(project, custom_fields),
            'tags': self._extract_tags(project),
            'metadata': {
                'source': 'asana',
                'original_gid': project.get('gid'),
                'layout': layout,
                'color': project.get('color'),
                'team': project.get('team', {}).get('name'),
                'created_at': project.get('created_at'),
                'modified_at': project.get('modified_at')
            }
        }
        
        # Transform based on layout type
        if layout == 'board':
            # Kanban board - each section becomes a step group
            blueprint['steps'] = self._transform_board_layout(sections, tasks)
        elif layout == 'timeline':
            # Timeline/Gantt - preserve dependencies
            blueprint['steps'] = self._transform_timeline_layout(tasks)
        else:
            # List or calendar - standard transformation
            blueprint['steps'] = self._transform_list_layout(sections, tasks)
        
        # Add workflow rules if any
        blueprint['rules'] = self._extract_workflow_rules(project)
        
        return blueprint
    
    def _format_description(self, project: Dict[str, Any], layout: str) -> str:
        """Format project description with metadata.
        
        Args:
            project: Asana project
            layout: Project layout type
            
        Returns:
            Formatted description
        """
        description = project.get('notes', '')
        
        # Add migration note
        migration_note = f"\n\n---\n*Migrated from Asana project (Layout: {layout})*"
        
        if project.get('due_date'):
            migration_note += f"\n*Original due date: {project['due_date']}*"
        if project.get('start_on'):
            migration_note += f"\n*Original start date: {project['start_on']}*"
            
        return description + migration_note
    
    def _create_kickoff_form(self, project: Dict[str, Any],
                            custom_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create kick-off form from project custom fields.
        
        Args:
            project: Asana project
            custom_fields: Custom field definitions
            
        Returns:
            List of form fields for kick-off
        """
        form_fields = []
        
        # Add project metadata fields
        form_fields.append({
            'name': 'Process Name',
            'type': 'text',
            'description': 'Name for this process instance',
            'required': True,
            'default_value': project.get('name', '')
        })
        
        form_fields.append({
            'name': 'Process Owner',
            'type': 'assignees_form',
            'description': 'Who is responsible for this process?',
            'required': True
        })
        
        # Add custom fields
        for field in custom_fields:
            transformed_field = self.field_transformer.transform_custom_field_definition(field)
            form_fields.append(transformed_field)
        
        # Add priority field if project uses it
        form_fields.append({
            'name': 'Priority',
            'type': 'dropdown',
            'description': 'Process priority level',
            'required': False,
            'options': [
                {'value': 'high', 'label': 'High'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'low', 'label': 'Low'}
            ]
        })
        
        return form_fields
    
    def _transform_board_layout(self, sections: List[Dict[str, Any]],
                               tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Kanban board layout to sequential steps.
        
        Each section becomes a step group with entry, work, and exit steps.
        
        Args:
            sections: Board columns
            tasks: Tasks in columns
            
        Returns:
            List of sequential steps
        """
        steps = []
        step_order = 1
        
        for section in sections:
            section_name = section.get('name', 'Untitled Section')
            section_gid = section.get('gid')
            
            # Get tasks in this section
            section_tasks = [t for t in tasks 
                           if any(s.get('gid') == section_gid 
                                 for s in t.get('memberships', []))]
            
            # Create step group for this board column
            # Entry step - notification when entering this phase
            steps.append({
                'order': step_order,
                'name': f"{section_name} - Start",
                'type': 'task',
                'description': f"Tasks have entered the {section_name} phase",
                "assignees_form": 'process_owner',
                'duration': 0,
                'metadata': {
                    'section_gid': section_gid,
                    'phase': 'entry'
                }
            })
            step_order += 1
            
            # Work steps - actual tasks in this column
            for task in section_tasks:
                steps.append(self._transform_task_to_step(task, step_order))
                step_order += 1
            
            # Exit step - approval to move to next phase
            steps.append({
                'order': step_order,
                'name': f"{section_name} - Complete",
                'type': 'approval',
                'description': f"Approve completion of {section_name} phase",
                "assignees_form": 'process_owner',
                'duration': 1,
                'metadata': {
                    'section_gid': section_gid,
                    'phase': 'exit'
                }
            })
            step_order += 1
        
        logger.info(f"Transformed {len(sections)} board columns into {len(steps)} sequential steps")
        return steps
    
    def _transform_timeline_layout(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform timeline/Gantt layout preserving dependencies.
        
        Args:
            tasks: Tasks with dependencies
            
        Returns:
            List of steps with dependency metadata
        """
        steps = []
        step_order = 1
        
        # Sort tasks by start date if available
        sorted_tasks = sorted(tasks, 
                            key=lambda t: t.get('start_on', '') or t.get('created_at', ''))
        
        for task in sorted_tasks:
            step = self._transform_task_to_step(task, step_order)
            
            # Add dependency information
            dependencies = task.get('dependencies', [])
            dependents = task.get('dependents', [])
            
            if dependencies or dependents:
                step['dependencies'] = {
                    'depends_on': [d.get('gid') for d in dependencies],
                    'required_for': [d.get('gid') for d in dependents]
                }
            
            # Add timeline dates
            if task.get('start_on'):
                step['start_date'] = task['start_on']
            if task.get('due_on'):
                step['due_date'] = task['due_on']
                
            steps.append(step)
            step_order += 1
        
        logger.info(f"Transformed timeline with {len(steps)} steps preserving dependencies")
        return steps
    
    def _transform_list_layout(self, sections: List[Dict[str, Any]],
                              tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform list layout to sequential steps.
        
        Args:
            sections: List sections
            tasks: Tasks in sections
            
        Returns:
            List of sequential steps
        """
        steps = []
        step_order = 1
        
        # Group tasks by section
        if sections:
            for section in sections:
                section_gid = section.get('gid')
                section_tasks = [t for t in tasks 
                               if any(s.get('gid') == section_gid 
                                     for s in t.get('memberships', []))]
                
                if section_tasks:
                    # Add section header as informational step
                    steps.append({
                        'order': step_order,
                        'name': f"Section: {section.get('name', 'Untitled')}",
                        'type': 'task',
                        'description': f"Begin tasks in section: {section.get('name')}",
                        "assignees_form": 'process_owner',
                        'duration': 0,
                        'metadata': {'is_section_header': True}
                    })
                    step_order += 1
                    
                    # Add tasks in this section
                    for task in section_tasks:
                        steps.append(self._transform_task_to_step(task, step_order))
                        step_order += 1
        else:
            # No sections, just add all tasks
            for task in tasks:
                steps.append(self._transform_task_to_step(task, step_order))
                step_order += 1
        
        logger.info(f"Transformed list layout with {len(steps)} steps")
        return steps
    
    def _transform_task_to_step(self, task: Dict[str, Any], order: int) -> Dict[str, Any]:
        """Transform individual Asana task to Tallyfy step.
        
        Args:
            task: Asana task object
            order: Step order number
            
        Returns:
            Tallyfy step object
        """
        # Determine step type based on task properties
        step_type = 'task'  # Default
        if task.get('approval_status'):
            step_type = 'approval'
        elif task.get('is_rendered_as_separator'):
            step_type = 'task'  # Separator becomes informational task
        
        step = {
            'order': order,
            'name': task.get('name', 'Untitled Task'),
            'type': step_type,
            'description': task.get('notes', ''),
            "assignees_form": self._transform_assignee(task.get("assignees_form")),
            'duration': self._calculate_duration(task),
            'form_fields': [],
            'metadata': {
                'original_gid': task.get('gid'),
                'completed': task.get('completed', False),
                'tags': [t.get('name') for t in task.get('tags', [])]
            }
        }
        
        # Add custom fields as form fields
        if task.get('custom_fields'):
            field_defs = {f['gid']: f for f in task.get('custom_fields', [])}
            transformed_fields = self.field_transformer.transform_task_custom_fields(
                task['custom_fields'], field_defs
            )
            if transformed_fields:
                step['custom_field_values'] = transformed_fields
        
        # Add subtasks as checklist
        if task.get('subtasks'):
            checklist_field = self.field_transformer.transform_subtask_to_checklist(
                task['subtasks']
            )
            if checklist_field:
                step['form_fields'].append(checklist_field)
        
        # Add due date if present
        if task.get('due_on'):
            step['deadline'] = self._transform_due_date(task['due_on'], task.get('due_at'))
        
        return step
    
    def _transform_assignee(self, assignee: Optional[Dict[str, Any]]) -> str:
        """Transform Asana assignee to Tallyfy format.
        
        Args:
            assignee: Asana user object
            
        Returns:
            Assignee identifier for Tallyfy
        """
        if not assignee:
            return 'process_owner'
        
        # Use short_text as identifier (will be mapped during user migration)
        email = assignee.get("text")
        if email:
            return f"member:{email}"
        
        return 'process_owner'
    
    def _calculate_duration(self, task: Dict[str, Any]) -> int:
        """Calculate task duration in days.
        
        Args:
            task: Asana task
            
        Returns:
            Duration in days
        """
        # If task has start and due dates, calculate difference
        if task.get('start_on') and task.get('due_on'):
            try:
                from datetime import datetime
                start = datetime.fromisoformat(task['start_on'])
                due = datetime.fromisoformat(task['due_on'])
                duration = (due - start).days
                return max(1, duration)
            except:
                pass
        
        # Default duration based on task complexity
        if task.get('subtasks'):
            return 3  # Tasks with subtasks get more time
        return 1  # Default 1 day
    
    def _transform_due_date(self, due_on: str, due_at: Optional[str]) -> Dict[str, Any]:
        """Transform Asana due date to Tallyfy deadline.
        
        Args:
            due_on: Date string
            due_at: Optional datetime string
            
        Returns:
            Deadline configuration
        """
        if due_at:
            # Has specific time
            return {
                'type': 'fixed',
                'datetime': due_at
            }
        else:
            # Date only
            return {
                'type': 'fixed',
                'date': due_on
            }
    
    def _extract_tags(self, project: Dict[str, Any]) -> List[str]:
        """Extract tags from project.
        
        Args:
            project: Asana project
            
        Returns:
            List of tag names
        """
        tags = []
        
        # Add team as tag
        if project.get('team'):
            tags.append(f"team:{project['team'].get('name', 'Unknown')}")
        
        # Add layout as tag
        tags.append(f"layout:{project.get('layout', 'list')}")
        
        # Add color as tag
        if project.get('color'):
            tags.append(f"color:{project['color']}")
        
        return tags
    
    def _extract_workflow_rules(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract workflow automation rules.
        
        Args:
            project: Asana project
            
        Returns:
            List of Tallyfy rules
        """
        rules = []
        
        # Note: Asana Rules API requires separate call
        # This is a placeholder for rule transformation
        
        # Add default rules based on project type
        if project.get('layout') == 'board':
            rules.append({
                'name': 'Auto-advance on completion',
                'trigger': 'task_completed',
                'action': 'advance_to_next_step',
                'description': 'Automatically move to next phase when tasks complete'
            })
        
        return rules