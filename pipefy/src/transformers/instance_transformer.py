"""
Instance Transformer for RocketLane to Tallyfy Migration
Handles active project to process conversion with state preservation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform RocketLane project instances to Tallyfy processes"""
    
    def __init__(self, ai_client=None):
        """
        Initialize instance transformer
        
        Args:
            ai_client: Optional AI client for complex mappings
        """
        self.ai_client = ai_client
        self.transformation_stats = {
            'total': 0,
            'successful': 0,
            'tasks_migrated': 0,
            'comments_created': 0,
            'files_referenced': 0,
            'time_entries_preserved': 0,
            'ai_assisted': 0
        }
    
    def transform_project(self, project: Dict[str, Any],
                         template_mapping: Dict[str, str],
                         user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Transform a RocketLane project to Tallyfy process
        
        Args:
            project: RocketLane project instance
            template_mapping: Mapping of RocketLane template IDs to Tallyfy blueprint IDs
            user_mapping: Mapping of RocketLane user IDs to Tallyfy user IDs
            
        Returns:
            Tallyfy process structure
        """
        self.transformation_stats['total'] += 1
        
        project_name = project.get('name', 'Untitled Project')
        logger.info(f"Transforming project: {project_name}")
        
        # Basic process structure
        process = {
            'blueprint_id': template_mapping.get(project.get('template_id')),
            'name': project_name[:250],
            'description': self._build_process_description(project),
            'metadata': {
                'source': 'rocketlane',
                'original_id': project.get('id'),
                'customer_id': project.get('customer_id'),
                'created_at': project.get('created_at'),
                'started_at': project.get('started_at'),
                'status': project.get('status'),
                'health': project.get('health_status')
            },
            'prerun_data': {},  # Kickoff form data
            'tasks': []
        }
        
        # Handle customer context
        if project.get('customer'):
            process['guest_context'] = self._transform_customer_context(
                project['customer'], user_mapping
            )
        
        # Transform project fields to prerun data
        if project.get('custom_fields'):
            process['prerun_data'] = self._transform_custom_fields(
                project['custom_fields']
            )
        
        # Transform project phases and tasks
        if project.get('phases'):
            self._transform_phases_and_tasks(
                process, project['phases'], user_mapping
            )
            
        if project.get('tasks'):
            self._transform_tasks(
                process, project['tasks'], user_mapping
            )
        
        # Transform time tracking to comments
        if project.get('time_entries'):
            self._transform_time_entries(
                process, project['time_entries'], user_mapping
            )
            self.transformation_stats['time_entries_preserved'] += len(project['time_entries'])
        
        # Transform documents and files
        if project.get('documents'):
            self._transform_documents(process, project['documents'])
            self.transformation_stats['files_referenced'] += len(project['documents'])
        
        # Transform project comments/notes
        if project.get('comments'):
            self._transform_comments(
                process, project['comments'], user_mapping
            )
            self.transformation_stats['comments_created'] += len(project['comments'])
        
        # Handle resource allocations
        if project.get('resource_allocations'):
            self._transform_resource_allocations(
                process, project['resource_allocations'], user_mapping
            )
        
        # Preserve project status
        self._set_process_status(process, project)
        
        self.transformation_stats['successful'] += 1
        return process
    
    def _build_process_description(self, project: Dict[str, Any]) -> str:
        """Build comprehensive process description"""
        parts = []
        
        if project.get('description'):
            parts.append(project['description'])
        
        if project.get('customer', {}).get('name'):
            parts.append(f"Customer: {project['customer']['name']}")
        
        if project.get('value'):
            parts.append(f"Value: ${project['value']:,.2f}")
        
        if project.get('estimated_end_date'):
            parts.append(f"Target Completion: {project['estimated_end_date']}")
        
        if project.get('owner'):
            parts.append(f"Project Owner: {project['owner']}")
        
        return ' | '.join(parts)[:2000]
    
    def _transform_customer_context(self, customer: Dict[str, Any],
                                   user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform customer information for guest context"""
        portal_handling = os.getenv('CUSTOMER_PORTAL_HANDLING', 'guest_users')
        
        context = {
            'name': customer.get('name'),
            'company': customer.get('company'),
            'email': customer.get('email'),
            'metadata': {
                'original_id': customer.get('id'),
                'tier': customer.get('tier'),
                'industry': customer.get('industry')
            }
        }
        
        if portal_handling == 'guest_users':
            # Map to guest user
            context['guest_user_id'] = user_mapping.get(
                f"customer_{customer.get('id')}"
            )
            context['send_guest_notifications'] = customer.get(
                'portal_access', False
            )
        elif portal_handling == 'organizations':
            # Map to organization
            context['organization_id'] = user_mapping.get(
                f"org_{customer.get('id')}"
            )
        
        return context
    
    def _transform_custom_fields(self, fields: Dict[str, Any]) -> Dict[str, str]:
        """Transform custom field values to prerun data"""
        prerun_data = {}
        
        for field_id, value in fields.items():
            # Convert value to string format expected by Tallyfy
            if isinstance(value, bool):
                prerun_data[field_id] = 'yes' if value else 'no'
            elif isinstance(value, (list, dict)):
                prerun_data[field_id] = json.dumps(value)
            elif value is not None:
                prerun_data[field_id] = str(value)
        
        return prerun_data
    
    def _transform_phases_and_tasks(self, process: Dict, phases: List[Dict],
                                   user_mapping: Dict[str, str]):
        """Transform project phases and their tasks"""
        for phase in phases:
            phase_status = phase.get('status', 'pending')
            
            # Create phase marker task
            phase_task = {
                'name': f"[Phase] {phase.get('name', 'Phase')}",
                'type': 'milestone',
                'status': self._map_task_status(phase_status),
                'metadata': {
                    'original_phase_id': phase.get('id'),
                    'phase_health': phase.get('health')
                }
            }
            
            if phase_status == 'completed' and phase.get('completed_at'):
                phase_task['completed_at'] = phase['completed_at']
                phase_task['completed_by'] = user_mapping.get(phase.get('completed_by'))
            
            process['tasks'].append(phase_task)
            
            # Transform tasks within phase
            for task in phase.get('tasks', []):
                transformed_task = self._transform_single_task(task, user_mapping)
                transformed_task['phase'] = phase.get('name')
                process['tasks'].append(transformed_task)
                self.transformation_stats['tasks_migrated'] += 1
    
    def _transform_tasks(self, process: Dict, tasks: List[Dict],
                        user_mapping: Dict[str, str]):
        """Transform standalone tasks"""
        for task in tasks:
            transformed_task = self._transform_single_task(task, user_mapping)
            process['tasks'].append(transformed_task)
            self.transformation_stats['tasks_migrated'] += 1
    
    def _transform_single_task(self, task: Dict[str, Any],
                              user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform individual task"""
        transformed = {
            'name': task.get('title', 'Task')[:600],
            'description': task.get('description', ''),
            'type': self._determine_task_type(task),
            'status': self._map_task_status(task.get('status')),
            'metadata': {
                'original_task_id': task.get('id'),
                'priority': task.get('priority'),
                'estimated_hours': task.get('estimated_hours'),
                'actual_hours': task.get('actual_hours')
            }
        }
        
        # Handle task assignment
        if task.get('assigned_to'):
            transformed['assigned_to'] = user_mapping.get(task['assigned_to'])
        elif task.get('assigned_team'):
            transformed['assigned_to_group'] = user_mapping.get(
                f"team_{task['assigned_team']}"
            )
        
        # Handle due dates
        if task.get('due_date'):
            transformed['due_date'] = task['due_date']
            if task.get('due_date_critical'):
                transformed['type'] = 'expiring'
        
        # Handle completion
        if task.get('status') == 'completed':
            transformed['completed_at'] = task.get('completed_at')
            transformed['completed_by'] = user_mapping.get(task.get('completed_by'))
        
        # Handle task form data
        if task.get('form_data'):
            transformed['form_values'] = self._transform_form_data(task['form_data'])
        
        # Handle checklist items
        if task.get('checklist_items'):
            transformed['checklist'] = self._transform_checklist(task['checklist_items'])
        
        # Handle dependencies
        if task.get('dependencies'):
            transformed['blocked_by'] = task['dependencies']
        
        # Handle customer visibility
        if task.get('customer_visible'):
            transformed['guest_can_view'] = True
            if task.get('customer_can_complete'):
                transformed['guest_can_complete'] = True
        
        return transformed
    
    def _determine_task_type(self, task: Dict[str, Any]) -> str:
        """Determine task type based on attributes"""
        if task.get('is_milestone'):
            return 'milestone'
        elif task.get('requires_approval'):
            return 'approval'
        elif task.get('form_fields'):
            return 'form'
        elif task.get('due_date_critical'):
            return 'expiring'
        else:
            return 'task'
    
    def _map_task_status(self, status: str) -> str:
        """Map RocketLane task status to Tallyfy status"""
        status_map = {
            'not_started': 'pending',
            'in_progress': 'in_progress',
            'completed': 'completed',
            'blocked': 'blocked',
            'cancelled': 'cancelled',
            'on_hold': 'paused',
            'pending': 'pending',
            'done': 'completed'
        }
        return status_map.get(status.lower(), 'pending')
    
    def _transform_form_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform task form data"""
        transformed = {}
        
        for field_id, value in form_data.items():
            # Apply same transformation as prerun data
            if isinstance(value, bool):
                transformed[field_id] = 'yes' if value else 'no'
            elif isinstance(value, (list, dict)):
                transformed[field_id] = json.dumps(value)
            elif value is not None:
                transformed[field_id] = str(value)
        
        return transformed
    
    def _transform_checklist(self, items: List[Dict]) -> List[Dict]:
        """Transform checklist items"""
        transformed = []
        
        for item in items:
            transformed.append({
                'text': item.get('text', ''),
                'completed': item.get('completed', False),
                'completed_at': item.get('completed_at'),
                'completed_by': item.get('completed_by')
            })
        
        return transformed
    
    def _transform_time_entries(self, process: Dict, time_entries: List[Dict],
                               user_mapping: Dict[str, str]):
        """Transform time entries to structured comments"""
        for entry in time_entries:
            comment = {
                'type': 'time_entry',
                'text': self._format_time_entry(entry),
                'created_at': entry.get('created_at'),
                'created_by': user_mapping.get(entry.get('user_id')),
                'metadata': {
                    'hours': entry.get('hours'),
                    'billable': entry.get('billable', False),
                    'task_id': entry.get('task_id'),
                    'date': entry.get('date')
                }
            }
            
            # Add to appropriate task or process level
            if entry.get('task_id'):
                # Find task and add comment
                for task in process.get('tasks', []):
                    if task['metadata'].get('original_task_id') == entry['task_id']:
                        if 'comments' not in task:
                            task['comments'] = []
                        task['comments'].append(comment)
                        break
            else:
                # Add to process level
                if 'comments' not in process:
                    process['comments'] = []
                process['comments'].append(comment)
    
    def _format_time_entry(self, entry: Dict[str, Any]) -> str:
        """Format time entry as comment text"""
        parts = [f"⏱️ Time Entry: {entry.get('hours', 0)} hours"]
        
        if entry.get('description'):
            parts.append(entry['description'])
        
        if entry.get('billable'):
            parts.append("(Billable)")
        
        if entry.get('activity_type'):
            parts.append(f"Activity: {entry['activity_type']}")
        
        return ' | '.join(parts)
    
    def _transform_documents(self, process: Dict, documents: List[Dict]):
        """Transform documents to external references"""
        process['external_documents'] = []
        
        for doc in documents:
            transformed_doc = {
                'name': doc.get('name', 'Document'),
                'url': doc.get('url') or doc.get('external_url'),
                'type': doc.get('type', 'document'),
                'uploaded_at': doc.get('uploaded_at'),
                'uploaded_by': doc.get('uploaded_by'),
                'metadata': {
                    'original_id': doc.get('id'),
                    'size_bytes': doc.get('size'),
                    'mime_type': doc.get('mime_type')
                }
            }
            
            # Note: Actual files would need to be re-uploaded to Tallyfy
            # This preserves references for manual migration
            if doc.get('is_customer_visible'):
                transformed_doc['guest_accessible'] = True
            
            process['external_documents'].append(transformed_doc)
    
    def _transform_comments(self, process: Dict, comments: List[Dict],
                          user_mapping: Dict[str, str]):
        """Transform project comments"""
        if 'comments' not in process:
            process['comments'] = []
        
        for comment in comments:
            transformed = {
                'type': 'comment',
                'text': comment.get('text', ''),
                'created_at': comment.get('created_at'),
                'created_by': user_mapping.get(comment.get('author_id')),
                'metadata': {
                    'original_id': comment.get('id'),
                    'is_internal': comment.get('internal', False)
                }
            }
            
            # Handle mentions
            if comment.get('mentions'):
                transformed['mentions'] = [
                    user_mapping.get(mention) for mention in comment['mentions']
                    if user_mapping.get(mention)
                ]
            
            # Handle attachments
            if comment.get('attachments'):
                transformed['attachments'] = comment['attachments']
            
            process['comments'].append(transformed)
    
    def _transform_resource_allocations(self, process: Dict, allocations: List[Dict],
                                       user_mapping: Dict[str, str]):
        """Transform resource allocations to task assignments"""
        allocation_notes = []
        
        for allocation in allocations:
            # Create note about resource allocation
            note = {
                'resource': allocation.get('resource_name'),
                'role': allocation.get('role'),
                'allocation_percentage': allocation.get('percentage'),
                'start_date': allocation.get('start_date'),
                'end_date': allocation.get('end_date'),
                'skills': allocation.get('required_skills', [])
            }
            allocation_notes.append(note)
            
            # Try to map to actual task assignments
            if allocation.get('task_ids'):
                for task_id in allocation['task_ids']:
                    for task in process.get('tasks', []):
                        if task['metadata'].get('original_task_id') == task_id:
                            # Assign resource to task
                            resource_id = user_mapping.get(allocation.get('resource_id'))
                            if resource_id:
                                task['assigned_to'] = resource_id
                            else:
                                # Add note about unassigned resource
                                task['resource_note'] = (
                                    f"Originally allocated to: {allocation.get('resource_name')} "
                                    f"({allocation.get('role')})"
                                )
        
        # Add allocation summary to process
        if allocation_notes:
            process['metadata']['resource_allocations'] = allocation_notes
    
    def _set_process_status(self, process: Dict, project: Dict):
        """Set process status based on project status"""
        status = project.get('status', 'active').lower()
        
        if status in ['completed', 'done', 'finished']:
            process['status'] = 'completed'
            process['completed_at'] = project.get('completed_at')
        elif status in ['cancelled', 'terminated']:
            process['status'] = 'cancelled'
            process['cancelled_at'] = project.get('cancelled_at')
        elif status in ['on_hold', 'paused']:
            process['status'] = 'paused'
        elif status in ['active', 'in_progress']:
            process['status'] = 'active'
            # Calculate progress
            if process.get('tasks'):
                completed = sum(1 for t in process['tasks'] 
                              if t.get('status') == 'completed')
                total = len(process['tasks'])
                process['progress_percentage'] = int((completed / total) * 100)
        else:
            process['status'] = 'pending'
    
    def transform_projects_batch(self, projects: List[Dict],
                                template_mapping: Dict[str, str],
                                user_mapping: Dict[str, str]) -> List[Dict]:
        """Transform multiple projects"""
        transformed = []
        
        for project in projects:
            try:
                process = self.transform_project(
                    project, template_mapping, user_mapping
                )
                transformed.append(process)
            except Exception as e:
                logger.error(f"Failed to transform project {project.get('name')}: {e}")
        
        return transformed
    
    def get_stats(self) -> Dict[str, int]:
        """Get transformation statistics"""
        return self.transformation_stats.copy()


# Import os for environment variables
import os