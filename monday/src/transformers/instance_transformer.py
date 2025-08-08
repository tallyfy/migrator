"""Transform Monday.com items to Tallyfy processes."""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .field_transformer import FieldTransformer

logger = logging.getLogger(__name__)


class InstanceTransformer:
    """Transform Monday.com items (board items) to Tallyfy processes (running instances)."""
    
    # Item state mapping
    STATE_MAPPING = {
        'active': 'active',
        'archived': 'archived',
        'deleted': 'cancelled'
    }
    
    def __init__(self):
        self.field_transformer = FieldTransformer()
        
    def transform_item_to_process(self, item: Dict[str, Any],
                                 checklist_id: str,
                                 user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform Monday.com item to Tallyfy process.
        
        Args:
            item: Monday.com item object
            checklist_id: Tallyfy blueprint ID to use
            user_mapping: Mapping of Monday user IDs to Tallyfy member IDs
            
        Returns:
            Tallyfy process object
        """
        item_id = item.get('id', '')
        item_name = item.get('name', 'Untitled Item')
        item_state = item.get('state', 'active')
        
        logger.info(f"Transforming item '{item_name}' (ID: {item_id}) to process")
        
        # Map state
        tallyfy_status = self.STATE_MAPPING.get(item_state, 'active')
        
        # Transform the item
        tallyfy_process = {
            'checklist_id': checklist_id,
            'name': item_name,
            'status': tallyfy_status,
            'data': self._transform_column_values(item.get('column_values', [])),
            'assignees': self._extract_assignees(item, user_mapping),
            'metadata': {
                'source': 'monday',
                'original_id': item_id,
                'original_state': item_state,
                'group_id': item.get('group', {}).get('id'),
                'group_title': item.get('group', {}).get('title'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            }
        }
        
        # Add creator if available
        creator = item.get('creator', {})
        if creator and creator.get('id') in user_mapping:
            tallyfy_process['created_by'] = user_mapping[creator['id']]
        
        # Add due date if present
        due_date = self._extract_due_date(item)
        if due_date:
            tallyfy_process['due_date'] = due_date
        
        # Add priority if present
        priority = self._extract_priority(item)
        if priority:
            tallyfy_process['priority'] = priority
        
        # Handle subitems
        if item.get('subitems'):
            tallyfy_process['checklists'] = self._transform_subitems(item['subitems'])
        
        # Handle file_upload attachments
        if item.get('assets'):
            tallyfy_process['attachments'] = self._transform_assets(item['assets'])
        
        return tallyfy_process
    
    def _transform_column_values(self, column_values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform Monday.com column values to process data.
        
        Args:
            column_values: List of column value objects
            
        Returns:
            Dictionary of field values
        """
        data = {}
        
        for col_value in column_values:
            column_id = col_value.get('id', '')
            column_type = col_value.get('type', '')
            
            # Skip empty values
            if not col_value.get('value') and not col_value.get("text"):
                continue
            
            # Transform the value
            transformed_value = self.field_transformer.transform_column_value(
                column_type, col_value
            )
            
            if transformed_value is not None:
                # Use column ID as field key
                data[f"monday_{column_id}"] = transformed_value
                
                # Also store with readable name if available
                if col_value.get('title'):
                    data[col_value['title']] = transformed_value
        
        return data
    
    def _extract_assignees(self, item: Dict[str, Any],
                         user_mapping: Dict[str, str]) -> List[str]:
        """Extract assignees from item.
        
        Args:
            item: Monday.com item
            user_mapping: User ID mapping
            
        Returns:
            List of Tallyfy member IDs
        """
        assignees = []
        
        # Look for people columns in column values
        for col_value in item.get('column_values', []):
            if col_value.get('type') == 'people':
                value = col_value.get('value')
                if value:
                    try:
                        if isinstance(value, str):
                            value = json.loads(value)
                        
                        if isinstance(value, dict):
                            persons = value.get('personsAndTeams', [])
                            for person in persons:
                                person_id = person.get('id')
                                if person_id and person_id in user_mapping:
                                    assignees.append(user_mapping[person_id])
                    except:
                        logger.warning(f"Failed to parse people column value")
        
        # Remove duplicates
        return list(set(assignees))
    
    def _extract_due_date(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract due date from item.
        
        Args:
            item: Monday.com item
            
        Returns:
            Due date string or None
        """
        # Look for date or timeline columns
        for col_value in item.get('column_values', []):
            col_type = col_value.get('type', '')
            
            if col_type == 'date':
                value = col_value.get('value')
                if value:
                    try:
                        if isinstance(value, str):
                            value = json.loads(value)
                        if isinstance(value, dict):
                            return value.get('date')
                    except:
                        pass
            
            elif col_type == 'timeline':
                value = col_value.get('value')
                if value:
                    try:
                        if isinstance(value, str):
                            value = json.loads(value)
                        if isinstance(value, dict):
                            # Use end date as due date
                            return value.get('to') or value.get('from')
                    except:
                        pass
        
        return None
    
    def _extract_priority(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract priority from item.
        
        Args:
            item: Monday.com item
            
        Returns:
            Priority string or None
        """
        # Look for priority or status columns
        for col_value in item.get('column_values', []):
            col_id = col_value.get('id', '').lower()
            col_title = col_value.get('title', '').lower()
            
            # Check if this is a priority column
            if 'priority' in col_id or 'priority' in col_title:
                text = col_value.get("text", '').lower()
                
                # Map to Tallyfy priority levels
                if 'critical' in text or 'urgent' in text:
                    return 'critical'
                elif 'high' in text:
                    return 'high'
                elif 'medium' in text or 'normal' in text:
                    return 'medium'
                elif 'low' in text:
                    return 'low'
        
        return None
    
    def _transform_subitems(self, subitems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform subitems to checklists.
        
        Args:
            subitems: List of subitems
            
        Returns:
            List of checklist items
        """
        checklists = []
        
        for subitem in subitems:
            checklist_item = {
                'name': subitem.get('name', 'Subitem'),
                'checked': False,  # Would need to determine from status
                'metadata': {
                    'original_id': subitem.get('id'),
                    'column_values': self._transform_column_values(
                        subitem.get('column_values', [])
                    )
                }
            }
            
            # Try to determine if completed
            for col_value in subitem.get('column_values', []):
                if col_value.get('type') == 'status':
                    text = col_value.get("text", '').lower()
                    if 'done' in text or 'complete' in text:
                        checklist_item['checked'] = True
                        break
            
            checklists.append(checklist_item)
        
        return checklists
    
    def _transform_assets(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform item assets/files.
        
        Args:
            assets: List of asset objects
            
        Returns:
            List of attachment objects
        """
        attachments = []
        
        for asset in assets:
            attachment = {
                'name': asset.get('name', 'File'),
                "text": asset.get("text", ''),
                'size': asset.get('file_size', 0),
                'uploaded_at': asset.get('created_at'),
                'metadata': {
                    'original_id': asset.get('id'),
                    'uploaded_by': asset.get('uploaded_by', {}).get('name')
                }
            }
            attachments.append(attachment)
        
        return attachments
    
    def transform_updates(self, updates: List[Dict[str, Any]],
                        user_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Transform item updates to comments.
        
        Args:
            updates: List of update objects
            user_mapping: User ID mapping
            
        Returns:
            List of comment objects
        """
        comments = []
        
        for update in updates:
            creator = update.get('creator', {})
            creator_id = creator.get('id', '')
            
            comment = {
                "text": update.get('body', ''),
                'created_at': update.get('created_at'),
                'author': user_mapping.get(creator_id, creator.get('name', 'Unknown')),
                'metadata': {
                    'original_id': update.get('id'),
                    'author_name': creator.get('name')
                }
            }
            
            comments.append(comment)
        
        return comments
    
    def transform_activity_logs(self, activities: List[Dict[str, Any]],
                              user_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Transform activity logs to audit trail.
        
        Args:
            activities: List of activity log entries
            user_mapping: User ID mapping
            
        Returns:
            List of activity entries
        """
        audit_trail = []
        
        for activity in activities:
            user = activity.get('user', {})
            user_id = user.get('id', '')
            
            entry = {
                'event': activity.get('event', 'unknown'),
                'data': activity.get('data', ''),
                'entity': activity.get('entity', ''),
                'timestamp': activity.get('created_at'),
                'user': user_mapping.get(user_id, user.get('name', 'Unknown')),
                'metadata': {
                    'original_id': activity.get('id'),
                    'user_name': user.get('name')
                }
            }
            
            audit_trail.append(entry)
        
        return audit_trail
    
    def create_migration_report(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create item migration report.
        
        Args:
            items: List of Monday.com items
            
        Returns:
            Migration report
        """
        report = {
            'total_items': len(items),
            'state_distribution': {
                'active': 0,
                'archived': 0,
                'deleted': 0
            },
            'groups': {},
            'items_with_subitems': 0,
            'items_with_files': 0,
            'items_with_updates': 0,
            'column_types_used': {},
            'warnings': []
        }
        
        for item in items:
            # Count by state
            state = item.get('state', 'active')
            report['state_distribution'][state] = report['state_distribution'].get(state, 0) + 1
            
            # Count by group
            group = item.get('group', {})
            group_title = group.get('title', 'No Group')
            report['groups'][group_title] = report['groups'].get(group_title, 0) + 1
            
            # Count features
            if item.get('subitems'):
                report['items_with_subitems'] += 1
            
            if item.get('assets'):
                report['items_with_files'] += 1
            
            if item.get('updates'):
                report['items_with_updates'] += 1
            
            # Track column types
            for col_value in item.get('column_values', []):
                col_type = col_value.get('type', 'unknown')
                report['column_types_used'][col_type] = report['column_types_used'].get(col_type, 0) + 1
            
            # Check for issues
            if not item.get('name'):
                report['warnings'].append(f"Item {item.get('id')} has no name")
        
        return report
    
    def batch_transform_items(self, items: List[Dict[str, Any]],
                            checklist_id: str,
                            user_mapping: Dict[str, str],
                            batch_size: int = 50) -> Generator[List[Dict[str, Any]], None, None]:
        """Transform items in batches.
        
        Args:
            items: List of Monday.com items
            checklist_id: Tallyfy blueprint ID
            user_mapping: User ID mapping
            batch_size: Items per batch
            
        Yields:
            Batches of transformed processes
        """
        batch = []
        
        for item in items:
            try:
                process = self.transform_item_to_process(item, checklist_id, user_mapping)
                batch.append(process)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
                    
            except Exception as e:
                logger.error(f"Failed to transform item {item.get('id')}: {e}")
        
        # Yield remaining items
        if batch:
            yield batch


from typing import Generator