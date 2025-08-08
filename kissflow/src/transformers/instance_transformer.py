"""Transform Kissflow running instances to Tallyfy processes."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform Kissflow running instances (processes, boards, apps) to Tallyfy processes."""
    
    # Instance status mapping
    STATUS_MAPPING = {
        'draft': 'draft',
        'in_progress': 'active',
        'active': 'active',
        'pending': 'active',
        'waiting': 'active',
        'paused': 'paused',
        'suspended': 'paused',
        'completed': 'completed',
        'done': 'completed',
        'archived': 'archived',
        'cancelled': 'cancelled',
        'rejected': 'cancelled',
        'failed': 'cancelled'
    }
    
    # Activity type mapping
    ACTIVITY_TYPE_MAPPING = {
        'task_completed': 'task_complete',
        'approval_given': 'approval',
        'comment_added': 'comment',
        'file_uploaded': 'file',
        'field_updated': 'field_update',
        'assignee_changed': 'reassign',
        'status_changed': 'status_change',
        'process_started': 'process_start',
        'process_completed': 'process_complete'
    }
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_process_instance(self, instance: Dict[str, Any],
                                  checklist_id: str,
                                  user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform Kissflow process instance to Tallyfy process.
        
        Args:
            instance: Kissflow process instance
            checklist_id: Tallyfy blueprint ID to use
            user_mapping: Mapping of Kissflow user IDs to Tallyfy member IDs
            
        Returns:
            Tallyfy process object
        """
        instance_id = instance.get('Id', '')
        instance_name = instance.get('Name') or instance.get('Title', 'Untitled Process')
        
        logger.info(f"Transforming process instance '{instance_name}' ({instance_id})")
        
        # Map status
        kissflow_status = instance.get('Status', 'in_progress').lower()
        tallyfy_status = self.STATUS_MAPPING.get(kissflow_status, 'active')
        
        # Transform the instance
        tallyfy_process = {
            'checklist_id': checklist_id,
            'name': instance_name,
            'status': tallyfy_status,
            'data': self._transform_instance_data(instance),
            'current_step': self._determine_current_step(instance),
            'assignees': self._transform_assignees(instance, user_mapping),
            'metadata': {
                'source': 'kissflow',
                'original_id': instance_id,
                'original_status': kissflow_status,
                'instance_number': instance.get('InstanceNumber'),
                'created_at': instance.get('CreatedAt'),
                'modified_at': instance.get('ModifiedAt'),
                'created_by': instance.get('CreatedBy'),
                'workflow_version': instance.get('WorkflowVersion')
            }
        }
        
        # Add dates
        if instance.get('StartedAt'):
            tallyfy_process['started_at'] = instance['StartedAt']
        
        if instance.get('CompletedAt'):
            tallyfy_process['completed_at'] = instance['CompletedAt']
        
        if instance.get('DueDate'):
            tallyfy_process['due_date'] = instance['DueDate']
        
        # Add priority
        if instance.get('Priority'):
            tallyfy_process['priority'] = instance['Priority'].lower()
        
        # Add tags
        if instance.get('Tags'):
            tallyfy_process['tags'] = instance['Tags']
        
        return tallyfy_process
    
    def transform_board_card(self, card: Dict[str, Any],
                            checklist_id: str,
                            user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform Kissflow board card to Tallyfy process.
        
        Args:
            card: Kissflow board card
            checklist_id: Tallyfy blueprint ID
            user_mapping: User ID mapping
            
        Returns:
            Tallyfy process object
        """
        card_id = card.get('Id', '')
        card_title = card.get('Title', 'Untitled Card')
        
        logger.info(f"Transforming board card '{card_title}' ({card_id})")
        
        # Determine process status based on column
        column = card.get('Column', {})
        column_name = column.get('Name', '').lower()
        
        # Map column to status
        if 'done' in column_name or 'complete' in column_name:
            status = 'completed'
        elif 'cancel' in column_name or 'reject' in column_name:
            status = 'cancelled'
        elif 'archive' in column_name:
            status = 'archived'
        else:
            status = 'active'
        
        tallyfy_process = {
            'checklist_id': checklist_id,
            'name': card_title,
            'status': status,
            'data': self._transform_card_data(card),
            'current_step': self._calculate_step_from_column(column),
            'assignees': self._transform_card_assignees(card, user_mapping),
            'metadata': {
                'source': 'kissflow',
                'original_id': card_id,
                'original_type': 'board_card',
                'board_id': card.get('BoardId'),
                'column_id': column.get('Id'),
                'column_name': column.get('Name'),
                'card_number': card.get('CardNumber'),
                'created_at': card.get('CreatedAt'),
                'modified_at': card.get('ModifiedAt'),
                'position': card.get('Position')
            }
        }
        
        # Add card-specific data
        if card.get('Description'):
            tallyfy_process['description'] = card['Description']
        
        if card.get('DueDate'):
            tallyfy_process['due_date'] = card['DueDate']
        
        if card.get('Labels'):
            tallyfy_process['tags'] = [label.get('Name', '') for label in card['Labels']]
        
        if card.get('Priority'):
            tallyfy_process['priority'] = card['Priority'].lower()
        
        # Add attachments reference
        if card.get('Attachments'):
            tallyfy_process['attachments'] = self._transform_attachments(card['Attachments'])
        
        return tallyfy_process
    
    def transform_app_record(self, record: Dict[str, Any],
                           checklist_id: str,
                           user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform Kissflow app record to Tallyfy process.
        
        Args:
            record: Kissflow app record
            checklist_id: Tallyfy blueprint ID
            user_mapping: User ID mapping
            
        Returns:
            Tallyfy process object
        """
        record_id = record.get('Id', '')
        record_name = record.get('Name') or record.get('Title', 'App Record')
        
        logger.info(f"Transforming app record '{record_name}' ({record_id})")
        
        # Map app record status
        status = 'active'  # Default for app records
        if record.get('Status'):
            status = self.STATUS_MAPPING.get(record['Status'].lower(), 'active')
        elif record.get('IsArchived'):
            status = 'archived'
        elif record.get('IsDeleted'):
            status = 'cancelled'
        
        tallyfy_process = {
            'checklist_id': checklist_id,
            'name': record_name,
            'status': status,
            'data': self._transform_app_data(record),
            'assignees': self._transform_app_assignees(record, user_mapping),
            'metadata': {
                'source': 'kissflow',
                'original_id': record_id,
                'original_type': 'app_record',
                'app_id': record.get('AppId'),
                'form_id': record.get('FormId'),
                'record_number': record.get('RecordNumber'),
                'created_at': record.get('CreatedAt'),
                'modified_at': record.get('ModifiedAt'),
                'created_by': record.get('CreatedBy')
            }
        }
        
        # Add workflow status if app record has workflow
        if record.get('WorkflowStatus'):
            tallyfy_process['workflow_status'] = record['WorkflowStatus']
            tallyfy_process['current_step'] = self._determine_app_step(record)
        
        return tallyfy_process
    
    def transform_activities(self, activities: List[Dict[str, Any]],
                           user_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Transform Kissflow activities to Tallyfy activity log.
        
        Args:
            activities: List of Kissflow activities
            user_mapping: User ID mapping
            
        Returns:
            List of Tallyfy activities
        """
        transformed_activities = []
        
        for activity in activities:
            activity_type = activity.get('Type', 'unknown').lower()
            tallyfy_type = self.ACTIVITY_TYPE_MAPPING.get(activity_type, 'note')
            
            transformed_activity = {
                'type': tallyfy_type,
                'timestamp': activity.get('Timestamp') or activity.get('CreatedAt'),
                'user': user_mapping.get(activity.get('UserId'), activity.get('UserId')),
                'description': activity.get('Description', ''),
                'metadata': {
                    'original_type': activity_type,
                    'original_id': activity.get('Id')
                }
            }
            
            # Add activity-specific data
            if activity_type == 'task_completed':
                transformed_activity['task_id'] = activity.get('TaskId')
                transformed_activity['task_name'] = activity.get('TaskName')
            
            elif activity_type == 'comment_added':
                transformed_activity['comment'] = activity.get('Comment', '')
                transformed_activity['mentions'] = self._extract_mentions(
                    activity.get('Comment', ''), user_mapping
                )
            
            elif activity_type == 'file_uploaded':
                transformed_activity["file"] = {
                    'name': activity.get('FileName'),
                    'size': activity.get('FileSize'),
                    "text": activity.get('FileUrl')
                }
            
            elif activity_type == 'field_updated':
                transformed_activity['field'] = activity.get('FieldName')
                transformed_activity['old_value'] = activity.get('OldValue')
                transformed_activity['new_value'] = activity.get('NewValue')
            
            elif activity_type == 'assignee_changed':
                transformed_activity['old_assignee'] = user_mapping.get(
                    activity.get('OldAssignee'), activity.get('OldAssignee')
                )
                transformed_activity['new_assignee'] = user_mapping.get(
                    activity.get('NewAssignee'), activity.get('NewAssignee')
                )
            
            transformed_activities.append(transformed_activity)
        
        logger.info(f"Transformed {len(activities)} activities")
        return transformed_activities
    
    def transform_comments(self, comments: List[Dict[str, Any]],
                         user_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Transform Kissflow comments to Tallyfy comments.
        
        Args:
            comments: List of Kissflow comments
            user_mapping: User ID mapping
            
        Returns:
            List of Tallyfy comments
        """
        transformed_comments = []
        
        for comment in comments:
            transformed_comment = {
                "text": comment.get('Text', ''),
                'author': user_mapping.get(comment.get('AuthorId'), comment.get('AuthorId')),
                'created_at': comment.get('CreatedAt'),
                'metadata': {
                    'original_id': comment.get('Id'),
                    'parent_id': comment.get('ParentId')  # For threaded comments
                }
            }
            
            # Add mentions
            mentions = self._extract_mentions(comment.get('Text', ''), user_mapping)
            if mentions:
                transformed_comment['mentions'] = mentions
            
            # Add attachments if present
            if comment.get('Attachments'):
                transformed_comment['attachments'] = self._transform_attachments(
                    comment['Attachments']
                )
            
            # Add reactions if present
            if comment.get('Reactions'):
                transformed_comment['reactions'] = comment['Reactions']
            
            transformed_comments.append(transformed_comment)
        
        return transformed_comments
    
    def _transform_instance_data(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Transform instance field data.
        
        Args:
            instance: Kissflow instance
            
        Returns:
            Transformed field data
        """
        data = {}
        
        # Get field values
        field_values = instance.get('FieldValues', {}) or instance.get('Data', {})
        
        for field_id, value in field_values.items():
            # Skip system fields
            if field_id.startswith('_'):
                continue
            
            # Get field definition if available
            field_def = instance.get('Fields', {}).get(field_id, {})
            if not field_def:
                # Create basic field definition
                field_def = {'Id': field_id, 'Name': field_id, 'Type': "text"}
            
            # Transform the value
            transformed_value = self.field_transformer.transform_field_value(field_def, value)
            data[field_def.get('Name', field_id)] = transformed_value
        
        return data
    
    def _transform_card_data(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """Transform board card data.
        
        Args:
            card: Kissflow board card
            
        Returns:
            Transformed card data
        """
        data = {
            'title': card.get('Title', ''),
            'description': card.get('Description', ''),
            'column': card.get('Column', {}).get('Name', ''),
            'position': card.get('Position', 0)
        }
        
        # Add custom fields
        for field_id, value in card.get('CustomFields', {}).items():
            data[f"custom_{field_id}"] = value
        
        # Add checklist items if present
        if card.get('Checklists'):
            data['checklists'] = self._transform_checklists(card['Checklists'])
        
        return data
    
    def _transform_app_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform app record data.
        
        Args:
            record: Kissflow app record
            
        Returns:
            Transformed record data
        """
        data = {}
        
        # Transform all record fields
        for field_name, value in record.items():
            # Skip system fields and metadata
            if field_name.startswith('_') or field_name in ['Id', 'CreatedAt', 'ModifiedAt']:
                continue
            
            data[field_name] = value
        
        return data
    
    def _transform_assignees(self, instance: Dict[str, Any],
                           user_mapping: Dict[str, str]) -> List[str]:
        """Transform instance assignees.
        
        Args:
            instance: Kissflow instance
            user_mapping: User ID mapping
            
        Returns:
            List of Tallyfy member IDs
        """
        assignees = []
        
        # Current assignees
        if instance.get('CurrentAssignees'):
            for assignee in instance['CurrentAssignees']:
                if isinstance(assignee, str):
                    assignees.append(user_mapping.get(assignee, assignee))
                elif isinstance(assignee, dict):
                    user_id = assignee.get('Id') or assignee.get('UserId')
                    assignees.append(user_mapping.get(user_id, user_id))
        
        # Active task assignees
        if instance.get('ActiveTasks'):
            for task in instance['ActiveTasks']:
                if task.get('AssigneeId'):
                    assignees.append(user_mapping.get(task['AssigneeId'], task['AssigneeId']))
        
        # Remove duplicates
        return list(set(assignees))
    
    def _transform_card_assignees(self, card: Dict[str, Any],
                                user_mapping: Dict[str, str]) -> List[str]:
        """Transform board card assignees.
        
        Args:
            card: Kissflow board card
            user_mapping: User ID mapping
            
        Returns:
            List of Tallyfy member IDs
        """
        assignees = []
        
        if card.get('Assignees'):
            for assignee in card['Assignees']:
                if isinstance(assignee, str):
                    assignees.append(user_mapping.get(assignee, assignee))
                elif isinstance(assignee, dict):
                    user_id = assignee.get('Id') or assignee.get('UserId')
                    assignees.append(user_mapping.get(user_id, user_id))
        
        # Add owner if different
        if card.get('OwnerId') and card['OwnerId'] not in assignees:
            assignees.append(user_mapping.get(card['OwnerId'], card['OwnerId']))
        
        return assignees
    
    def _transform_app_assignees(self, record: Dict[str, Any],
                               user_mapping: Dict[str, str]) -> List[str]:
        """Transform app record assignees.
        
        Args:
            record: Kissflow app record
            user_mapping: User ID mapping
            
        Returns:
            List of Tallyfy member IDs
        """
        assignees = []
        
        # Record owner
        if record.get('OwnerId'):
            assignees.append(user_mapping.get(record['OwnerId'], record['OwnerId']))
        
        # Workflow assignees
        if record.get('WorkflowAssignees'):
            for assignee_id in record['WorkflowAssignees']:
                assignees.append(user_mapping.get(assignee_id, assignee_id))
        
        return assignees
    
    def _determine_current_step(self, instance: Dict[str, Any]) -> Optional[int]:
        """Determine current step number from instance.
        
        Args:
            instance: Kissflow instance
            
        Returns:
            Current step number or None
        """
        # Check for explicit current step
        if instance.get('CurrentStep'):
            return instance['CurrentStep'].get('Order', 1)
        
        # Check active tasks
        if instance.get('ActiveTasks'):
            # Return the lowest order active task
            min_order = float('inf')
            for task in instance['ActiveTasks']:
                if task.get('Order', float('inf')) < min_order:
                    min_order = task['Order']
            return min_order if min_order != float('inf') else None
        
        # Check progress percentage
        if instance.get('Progress'):
            # Estimate step from progress
            total_steps = instance.get('TotalSteps', 10)
            progress = instance['Progress']
            return max(1, int((progress / 100) * total_steps))
        
        return None
    
    def _calculate_step_from_column(self, column: Dict[str, Any]) -> int:
        """Calculate step number from board column.
        
        Each column maps to 3 steps (entry, work, exit).
        
        Args:
            column: Board column
            
        Returns:
            Estimated step number
        """
        column_index = column.get('Order', column.get('Position', 0))
        # Each column = 3 steps, plus initial creation step
        return 1 + (column_index * 3) + 1  # Middle of column (work step)
    
    def _determine_app_step(self, record: Dict[str, Any]) -> Optional[int]:
        """Determine current step for app record.
        
        Args:
            record: App record
            
        Returns:
            Current step number or None
        """
        if record.get('WorkflowStep'):
            return record['WorkflowStep'].get('Order', 1)
        
        # Map workflow status to approximate step
        workflow_status = record.get('WorkflowStatus', '').lower()
        status_step_map = {
            'new': 1,
            'in_review': 2,
            'approved': 3,
            'processing': 4,
            'completed': 5
        }
        
        return status_step_map.get(workflow_status)
    
    def _transform_attachments(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform attachments.
        
        Args:
            attachments: List of Kissflow attachments
            
        Returns:
            List of transformed attachments
        """
        transformed = []
        
        for attachment in attachments:
            transformed.append({
                'name': attachment.get('Name', 'File'),
                'size': attachment.get('Size', 0),
                "text": attachment.get('Url', ''),
                'type': attachment.get('Type', 'unknown'),
                'uploaded_at': attachment.get('UploadedAt'),
                'uploaded_by': attachment.get('UploadedBy'),
                'metadata': {
                    'original_id': attachment.get('Id')
                }
            })
        
        return transformed
    
    def _transform_checklists(self, checklists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform board card checklists.
        
        Args:
            checklists: List of checklists
            
        Returns:
            Transformed checklists
        """
        transformed = []
        
        for checklist in checklists:
            items = []
            for item in checklist.get('Items', []):
                items.append({
                    "text": item.get('Text', ''),
                    'checked': item.get('Checked', False),
                    'assigned_to': item.get('AssignedTo')
                })
            
            transformed.append({
                'name': checklist.get('Name', 'Checklist'),
                'items': items,
                'progress': checklist.get('Progress', 0)
            })
        
        return transformed
    
    def _extract_mentions(self, text: str, user_mapping: Dict[str, str]) -> List[str]:
        """Extract user mentions from text.
        
        Args:
            text: Text containing mentions
            user_mapping: User ID mapping
            
        Returns:
            List of mentioned user IDs
        """
        import re
        
        mentions = []
        
        # Look for @mentions
        mention_pattern = r'@(\w+)'
        matches = re.findall(mention_pattern, text)
        
        for match in matches:
            # Try to map the username
            if match in user_mapping:
                mentions.append(user_mapping[match])
            else:
                mentions.append(match)
        
        return mentions
    
    def create_migration_report(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create instance migration report.
        
        Args:
            instances: List of instances to migrate
            
        Returns:
            Migration report
        """
        report = {
            'total_instances': len(instances),
            'status_distribution': {},
            'type_distribution': {},
            'active_instances': 0,
            'completed_instances': 0,
            'overdue_instances': 0,
            'instances_with_attachments': 0,
            'instances_with_comments': 0,
            'average_completion_time': None,
            'warnings': []
        }
        
        completion_times = []
        
        for instance in instances:
            # Count by status
            status = instance.get('Status', 'unknown')
            report['status_distribution'][status] = report['status_distribution'].get(status, 0) + 1
            
            # Count by type
            instance_type = instance.get('Type', 'process')
            report['type_distribution'][instance_type] = report['type_distribution'].get(instance_type, 0) + 1
            
            # Count active/completed
            if status.lower() in ['active', 'in_progress', 'pending']:
                report['active_instances'] += 1
            elif status.lower() in ['completed', 'done']:
                report['completed_instances'] += 1
            
            # Check overdue
            if instance.get('DueDate'):
                due_date = datetime.fromisoformat(instance['DueDate'].replace('Z', '+00:00'))
                if due_date < datetime.now(due_date.tzinfo) and status.lower() not in ['completed', 'done']:
                    report['overdue_instances'] += 1
            
            # Check attachments
            if instance.get('Attachments'):
                report['instances_with_attachments'] += 1
            
            # Check comments
            if instance.get('Comments'):
                report['instances_with_comments'] += 1
            
            # Calculate completion time
            if instance.get('StartedAt') and instance.get('CompletedAt'):
                try:
                    started = datetime.fromisoformat(instance['StartedAt'].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(instance['CompletedAt'].replace('Z', '+00:00'))
                    completion_time = (completed - started).days
                    completion_times.append(completion_time)
                except:
                    pass
            
            # Check for issues
            if not instance.get('Name') and not instance.get('Title'):
                report['warnings'].append(f"Instance {instance.get('Id')} has no name")
            
            if instance.get('HasErrors'):
                report['warnings'].append(f"Instance {instance.get('Id')} has errors: {instance.get('Errors')}")
        
        # Calculate average completion time
        if completion_times:
            report['average_completion_time'] = sum(completion_times) / len(completion_times)
        
        return report