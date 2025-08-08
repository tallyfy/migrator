"""Transform Asana running tasks/projects to Tallyfy processes."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform Asana active projects and tasks to Tallyfy processes."""
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
    
    def transform_active_project(self, project: Dict[str, Any],
                                tasks: List[Dict[str, Any]],
                                checklist_id: str,
                                user_map: Dict[str, str]) -> Dict[str, Any]:
        """Transform active Asana project to Tallyfy process.
        
        Args:
            project: Asana project object
            tasks: List of tasks in project
            checklist_id: Tallyfy blueprint ID this was created from
            user_map: Mapping of Asana user GIDs to Tallyfy member IDs
            
        Returns:
            Tallyfy process object
        """
        logger.info(f"Transforming active project '{project.get('name')}' to process")
        
        # Calculate process progress
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get('completed'))
        progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        process = {
            'checklist_id': checklist_id,
            'name': f"{project.get('name')} - Active",
            'status': self._determine_process_status(project, tasks),
            'progress': progress,
            'owner': user_map.get(project.get('owner', {}).get('gid'), 'system'),
            'participants': self._extract_participants(project, tasks, user_map),
            'kick_off_data': self._extract_kickoff_data(project),
            'tasks': [],
            'metadata': {
                'source': 'asana',
                'original_gid': project.get('gid'),
                'created_at': project.get('created_at'),
                'modified_at': project.get('modified_at'),
                'due_date': project.get('due_date'),
                'start_on': project.get('start_on')
            }
        }
        
        # Transform tasks to process tasks
        for idx, task in enumerate(tasks):
            process_task = self.transform_task_to_process_task(task, idx + 1, user_map)
            process['tasks'].append(process_task)
        
        return process
    
    def transform_task_to_process_task(self, task: Dict[str, Any],
                                      order: int,
                                      user_map: Dict[str, str]) -> Dict[str, Any]:
        """Transform Asana task to Tallyfy process task.
        
        Args:
            task: Asana task object
            order: Task order in process
            user_map: Mapping of Asana user GIDs to Tallyfy member IDs
            
        Returns:
            Tallyfy process task object
        """
        # Determine task status
        if task.get('completed'):
            status = 'completed'
        elif task.get("assignees_form"):
            status = 'in_progress'
        else:
            status = 'pending'
        
        process_task = {
            'order': order,
            'name': task.get('name', 'Untitled Task'),
            'description': task.get('notes', ''),
            'status': status,
            "assignees_form": user_map.get(task.get("assignees_form", {}).get('gid')) if task.get("assignees_form") else None,
            'completed_at': task.get('completed_at'),
            'completed_by': user_map.get(task.get('completed_by', {}).get('gid')) if task.get('completed_by') else None,
            'due_date': self._transform_task_due_date(task),
            'form_data': {},
            'comments': [],
            'attachments': [],
            'metadata': {
                'original_gid': task.get('gid'),
                'created_at': task.get('created_at'),
                'modified_at': task.get('modified_at'),
                'tags': [t.get('name') for t in task.get('tags', [])],
                'projects': [p.get('gid') for p in task.get('projects', [])]
            }
        }
        
        # Transform custom fields
        if task.get('custom_fields'):
            field_defs = {f['gid']: f for f in task.get('custom_fields', [])}
            process_task['form_data'] = self.field_transformer.transform_task_custom_fields(
                task['custom_fields'], field_defs
            )
        
        # Transform subtasks
        if task.get('subtasks'):
            process_task['subtasks'] = [
                {
                    'name': st.get('name'),
                    'completed': st.get('completed', False),
                    "assignees_form": user_map.get(st.get("assignees_form", {}).get('gid')) if st.get("assignees_form") else None
                }
                for st in task.get('subtasks', [])
            ]
        
        # Add dependency information
        if task.get('dependencies') or task.get('dependents'):
            process_task['dependencies'] = {
                'blocked_by': [d.get('gid') for d in task.get('dependencies', [])],
                'blocking': [d.get('gid') for d in task.get('dependents', [])]
            }
        
        return process_task
    
    def transform_stories_to_comments(self, stories: List[Dict[str, Any]],
                                     user_map: Dict[str, str]) -> List[Dict[str, Any]]:
        """Transform Asana stories to Tallyfy comments.
        
        Args:
            stories: List of Asana story objects
            user_map: Mapping of Asana user GIDs to Tallyfy member IDs
            
        Returns:
            List of Tallyfy comment objects
        """
        comments = []
        
        for story in stories:
            # Only include comment-type stories
            if story.get('type') != 'comment' and story.get('resource_subtype') != 'comment_added':
                continue
            
            comment = {
                "text": story.get("text", ''),
                'html_text': story.get('html_text', ''),
                'author': user_map.get(story.get('created_by', {}).get('gid'), 'system'),
                'created_at': story.get('created_at'),
                'metadata': {
                    'original_gid': story.get('gid'),
                    'type': story.get('type')
                }
            }
            
            comments.append(comment)
        
        return comments
    
    def transform_attachments(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Asana attachments to Tallyfy format.
        
        Args:
            attachments: List of Asana attachment objects
            
        Returns:
            List of Tallyfy attachment objects
        """
        transformed = []
        
        for attachment in attachments:
            # Check file_upload size (Tallyfy limit is 100MB)
            size = attachment.get('size', 0)
            
            if size > 100_000_000:
                # File too large, create reference instead
                transformed.append({
                    'type': 'external_link',
                    'name': attachment.get('name', 'Large File'),
                    "text": attachment.get('download_url', ''),
                    'size': size,
                    'note': 'File exceeds 100MB limit, stored as external link',
                    'metadata': {
                        'original_gid': attachment.get('gid'),
                        'host': attachment.get('host', 'asana'),
                        'created_at': attachment.get('created_at')
                    }
                })
            else:
                # Normal attachment
                transformed.append({
                    'type': "file",
                    'name': attachment.get('name', 'Untitled'),
                    "text": attachment.get('download_url', ''),
                    'size': size,
                    'metadata': {
                        'original_gid': attachment.get('gid'),
                        'host': attachment.get('host', 'asana'),
                        'created_at': attachment.get('created_at')
                    }
                })
        
        return transformed
    
    def _determine_process_status(self, project: Dict[str, Any],
                                 tasks: List[Dict[str, Any]]) -> str:
        """Determine overall process status.
        
        Args:
            project: Asana project
            tasks: List of tasks
            
        Returns:
            Process status
        """
        if not tasks:
            return 'not_started'
        
        all_completed = all(t.get('completed', False) for t in tasks)
        if all_completed:
            return 'completed'
        
        any_started = any(t.get("assignees_form") or t.get('completed') for t in tasks)
        if any_started:
            return 'in_progress'
        
        return 'not_started'
    
    def _extract_participants(self, project: Dict[str, Any],
                            tasks: List[Dict[str, Any]],
                            user_map: Dict[str, str]) -> List[str]:
        """Extract all participants from project and tasks.
        
        Args:
            project: Asana project
            tasks: List of tasks
            user_map: User GID to Tallyfy ID mapping
            
        Returns:
            List of Tallyfy member IDs
        """
        participants = set()
        
        # Add project owner
        if project.get('owner'):
            owner_id = user_map.get(project['owner'].get('gid'))
            if owner_id:
                participants.add(owner_id)
        
        # Add project members
        for member in project.get('members', []):
            member_id = user_map.get(member.get('gid'))
            if member_id:
                participants.add(member_id)
        
        # Add task assignees
        for task in tasks:
            if task.get("assignees_form"):
                assignee_id = user_map.get(task["assignees_form"].get('gid'))
                if assignee_id:
                    participants.add(assignee_id)
            
            # Add followers
            for follower in task.get('followers', []):
                follower_id = user_map.get(follower.get('gid'))
                if follower_id:
                    participants.add(follower_id)
        
        return list(participants)
    
    def _extract_kickoff_data(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Extract kick-off form data from project.
        
        Args:
            project: Asana project
            
        Returns:
            Kick-off form data
        """
        kickoff_data = {
            'process_name': project.get('name', ''),
            'process_owner': project.get('owner', {}).get('gid'),
            'priority': 'medium',  # Default
            'start_date': project.get('start_on'),
            'due_date': project.get('due_date')
        }
        
        # Add custom field values
        for field in project.get('custom_fields', []):
            field_alias = f"asana_{field.get('gid')}"
            kickoff_data[field_alias] = self._extract_field_value(field)
        
        return kickoff_data
    
    def _extract_field_value(self, field: Dict[str, Any]) -> Any:
        """Extract value from custom field.
        
        Args:
            field: Custom field object
            
        Returns:
            Field value
        """
        field_type = field.get('type')
        
        if field_type == "text":
            return field.get('text_value')
        elif field_type == "text":
            return field.get('number_value')
        elif field_type == 'enum':
            enum_value = field.get('enum_value')
            return enum_value.get('gid') if enum_value else None
        elif field_type == 'multi_enum':
            return [v.get('gid') for v in field.get('multi_enum_values', [])]
        elif field_type == 'date':
            return field.get('date_value')
        elif field_type == 'people':
            return [p.get('gid') for p in field.get('people_value', [])]
        else:
            return field.get('display_value')
    
    def _transform_task_due_date(self, task: Dict[str, Any]) -> Optional[str]:
        """Transform task due date.
        
        Args:
            task: Asana task
            
        Returns:
            ISO format due date or None
        """
        if task.get('due_at'):
            # Has specific time
            return task['due_at']
        elif task.get('due_on'):
            # Date only - add end of day time
            return f"{task['due_on']}T23:59:59Z"
        return None
    
    def create_migration_summary(self, projects: List[Dict[str, Any]],
                                tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create summary of migration for reporting.
        
        Args:
            projects: List of projects
            tasks: List of all tasks
            
        Returns:
            Migration summary
        """
        completed_tasks = [t for t in tasks if t.get('completed')]
        overdue_tasks = []
        
        # Check for overdue tasks
        now = datetime.now().isoformat()
        for task in tasks:
            if not task.get('completed') and task.get('due_on'):
                if task['due_on'] < now:
                    overdue_tasks.append(task)
        
        return {
            'total_projects': len(projects),
            'total_tasks': len(tasks),
            'completed_tasks': len(completed_tasks),
            'pending_tasks': len(tasks) - len(completed_tasks),
            'overdue_tasks': len(overdue_tasks),
            'completion_rate': (len(completed_tasks) / len(tasks) * 100) if tasks else 0,
            'projects_by_layout': self._count_by_layout(projects),
            'tasks_by_status': {
                'completed': len(completed_tasks),
                'in_progress': len([t for t in tasks if not t.get('completed') and t.get("assignees_form")]),
                'not_started': len([t for t in tasks if not t.get('completed') and not t.get("assignees_form")])
            }
        }
    
    def _count_by_layout(self, projects: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count projects by layout type.
        
        Args:
            projects: List of projects
            
        Returns:
            Count by layout
        """
        counts = {
            'list': 0,
            'board': 0,
            'timeline': 0,
            'calendar': 0
        }
        
        for project in projects:
            layout = project.get('layout', 'list')
            if layout in counts:
                counts[layout] += 1
        
        return counts