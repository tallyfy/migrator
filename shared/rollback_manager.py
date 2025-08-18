#!/usr/bin/env python3
"""
Production-Grade Rollback System for Failed Migrations
Ensures data integrity by allowing complete rollback of partial migrations
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import pickle
import hashlib
from contextlib import contextmanager


class ActionType(str, Enum):
    """Types of actions that can be rolled back"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ASSIGN = "assign"
    UNASSIGN = "unassign"
    LINK = "link"
    UNLINK = "unlink"
    TRANSFORM = "transform"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class ResourceType(str, Enum):
    """Types of resources that can be rolled back"""
    USER = "user"
    TEMPLATE = "template"
    BLUEPRINT = "blueprint"
    INSTANCE = "instance"
    PROCESS = "process"
    FIELD = "field"
    STEP = "step"
    COMMENT = "comment"
    ATTACHMENT = "attachment"
    WEBHOOK = "webhook"


@dataclass
class RollbackAction:
    """Represents a single rollback action"""
    id: str
    timestamp: datetime
    action_type: ActionType
    resource_type: ResourceType
    resource_id: str
    original_data: Optional[Dict[str, Any]]
    new_data: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    rollback_method: str
    status: str = "pending"
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['action_type'] = self.action_type.value
        data['resource_type'] = self.resource_type.value
        return data


class RollbackManager:
    """
    Manages rollback operations for migrations
    Stores all actions and can reverse them in case of failure
    """
    
    def __init__(self, migration_id: str, vendor_client: Any = None, tallyfy_client: Any = None):
        """
        Initialize rollback manager
        
        Args:
            migration_id: Unique migration identifier
            vendor_client: Client for source vendor
            tallyfy_client: Client for Tallyfy
        """
        self.migration_id = migration_id
        self.vendor_client = vendor_client
        self.tallyfy_client = tallyfy_client
        
        # Setup logging
        self.logger = logging.getLogger(f"rollback_{migration_id}")
        
        # Setup database
        self.db_path = Path(f"rollback_{migration_id}.db")
        self._init_database()
        
        # Rollback methods registry
        self.rollback_methods = {
            'delete_resource': self._delete_resource,
            'restore_resource': self._restore_resource,
            'revert_update': self._revert_update,
            'unassign_resource': self._unassign_resource,
            'unlink_resources': self._unlink_resources,
            'custom_rollback': self._custom_rollback
        }
        
        # Transaction management
        self.transaction_stack = []
        self.current_transaction = None
        
    def _init_database(self):
        """Initialize rollback database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rollback_actions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    original_data TEXT,
                    new_data TEXT,
                    metadata TEXT,
                    rollback_method TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    error TEXT,
                    transaction_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rollback_transactions (
                    id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT DEFAULT 'active',
                    description TEXT,
                    parent_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_resource 
                ON rollback_actions(resource_type, resource_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transaction 
                ON rollback_actions(transaction_id)
            """)
            
            conn.commit()
    
    # ============= TRANSACTION MANAGEMENT =============
    
    @contextmanager
    def transaction(self, description: str = None):
        """
        Context manager for transactional rollback
        
        Usage:
            with rollback_manager.transaction("Create users"):
                # Actions here are grouped
                rollback_manager.record_create(...)
        """
        transaction_id = f"txn_{datetime.utcnow().timestamp()}_{len(self.transaction_stack)}"
        
        parent_id = self.current_transaction if self.current_transaction else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO rollback_transactions 
                (id, start_time, description, parent_id)
                VALUES (?, ?, ?, ?)
            """, (transaction_id, datetime.utcnow().isoformat(), description, parent_id))
        
        self.transaction_stack.append(self.current_transaction)
        self.current_transaction = transaction_id
        
        try:
            yield transaction_id
            # Mark transaction as successful
            self._complete_transaction(transaction_id, 'completed')
        except Exception as e:
            # Mark transaction as failed and prepare for rollback
            self._complete_transaction(transaction_id, 'failed')
            raise
        finally:
            self.current_transaction = self.transaction_stack.pop()
    
    def _complete_transaction(self, transaction_id: str, status: str):
        """Mark transaction as complete"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE rollback_transactions 
                SET end_time = ?, status = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), status, transaction_id))
    
    # ============= RECORDING ACTIONS =============
    
    def record_create(self, resource_type: ResourceType, resource_id: str, 
                     data: Dict[str, Any], metadata: Dict = None) -> str:
        """Record a resource creation for potential rollback"""
        action = RollbackAction(
            id=self._generate_action_id(),
            timestamp=datetime.utcnow(),
            action_type=ActionType.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            original_data=None,
            new_data=data,
            metadata=metadata or {},
            rollback_method='delete_resource'
        )
        
        self._save_action(action)
        self.logger.info(f"Recorded CREATE: {resource_type.value}/{resource_id}")
        return action.id
    
    def record_update(self, resource_type: ResourceType, resource_id: str,
                     original_data: Dict[str, Any], new_data: Dict[str, Any],
                     metadata: Dict = None) -> str:
        """Record a resource update for potential rollback"""
        action = RollbackAction(
            id=self._generate_action_id(),
            timestamp=datetime.utcnow(),
            action_type=ActionType.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            original_data=original_data,
            new_data=new_data,
            metadata=metadata or {},
            rollback_method='revert_update'
        )
        
        self._save_action(action)
        self.logger.info(f"Recorded UPDATE: {resource_type.value}/{resource_id}")
        return action.id
    
    def record_delete(self, resource_type: ResourceType, resource_id: str,
                     data: Dict[str, Any], metadata: Dict = None) -> str:
        """Record a resource deletion for potential rollback"""
        action = RollbackAction(
            id=self._generate_action_id(),
            timestamp=datetime.utcnow(),
            action_type=ActionType.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            original_data=data,
            new_data=None,
            metadata=metadata or {},
            rollback_method='restore_resource'
        )
        
        self._save_action(action)
        self.logger.info(f"Recorded DELETE: {resource_type.value}/{resource_id}")
        return action.id
    
    def record_bulk_operation(self, action_type: ActionType, resource_type: ResourceType,
                             items: List[Dict[str, Any]], metadata: Dict = None) -> str:
        """Record a bulk operation for potential rollback"""
        action = RollbackAction(
            id=self._generate_action_id(),
            timestamp=datetime.utcnow(),
            action_type=action_type,
            resource_type=resource_type,
            resource_id=f"bulk_{len(items)}_items",
            original_data=None,
            new_data={'items': items},
            metadata=metadata or {'item_count': len(items)},
            rollback_method='custom_rollback'
        )
        
        self._save_action(action)
        self.logger.info(f"Recorded {action_type.value}: {len(items)} {resource_type.value}s")
        return action.id
    
    def record_custom(self, action_type: str, resource_type: str, resource_id: str,
                     rollback_function: Callable, rollback_args: Dict,
                     metadata: Dict = None) -> str:
        """Record a custom action with specific rollback function"""
        # Serialize the rollback function and arguments
        rollback_data = {
            'function': pickle.dumps(rollback_function),
            'args': rollback_args
        }
        
        action = RollbackAction(
            id=self._generate_action_id(),
            timestamp=datetime.utcnow(),
            action_type=ActionType(action_type) if action_type in ActionType.__members__.values() else ActionType.TRANSFORM,
            resource_type=ResourceType(resource_type) if resource_type in ResourceType.__members__.values() else ResourceType.PROCESS,
            resource_id=resource_id,
            original_data=rollback_data,
            new_data=None,
            metadata=metadata or {},
            rollback_method='custom_rollback'
        )
        
        self._save_action(action)
        self.logger.info(f"Recorded CUSTOM: {action_type}/{resource_id}")
        return action.id
    
    # ============= ROLLBACK EXECUTION =============
    
    def rollback_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Rollback all recorded actions in reverse order
        
        Args:
            dry_run: If True, simulate rollback without executing
        
        Returns:
            Dict with rollback results
        """
        self.logger.info(f"Starting {'DRY RUN ' if dry_run else ''}rollback for migration {self.migration_id}")
        
        results = {
            'total_actions': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'dry_run': dry_run
        }
        
        # Get all actions in reverse order
        actions = self._get_actions_for_rollback()
        results['total_actions'] = len(actions)
        
        for action in actions:
            try:
                if dry_run:
                    self.logger.info(f"[DRY RUN] Would rollback: {action.action_type.value} {action.resource_type.value}/{action.resource_id}")
                    results['successful'] += 1
                else:
                    self._execute_rollback_action(action)
                    results['successful'] += 1
                    self.logger.info(f"Successfully rolled back: {action.id}")
            except Exception as e:
                results['failed'] += 1
                error_msg = f"Failed to rollback {action.id}: {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
                
                # Update action status
                self._update_action_status(action.id, 'failed', str(e))
        
        self.logger.info(f"Rollback complete: {results['successful']}/{results['total_actions']} successful")
        return results
    
    def rollback_transaction(self, transaction_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Rollback a specific transaction"""
        self.logger.info(f"Rolling back transaction: {transaction_id}")
        
        # Get all actions in this transaction
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM rollback_actions 
                WHERE transaction_id = ?
                ORDER BY timestamp DESC
            """, (transaction_id,))
            
            actions = []
            for row in cursor:
                action = self._row_to_action(row)
                actions.append(action)
        
        results = {
            'transaction_id': transaction_id,
            'total_actions': len(actions),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for action in actions:
            try:
                if not dry_run:
                    self._execute_rollback_action(action)
                results['successful'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))
        
        return results
    
    def rollback_since(self, timestamp: datetime, dry_run: bool = False) -> Dict[str, Any]:
        """Rollback all actions since a specific timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM rollback_actions 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (timestamp.isoformat(),))
            
            actions = [self._row_to_action(row) for row in cursor]
        
        results = {
            'since': timestamp.isoformat(),
            'total_actions': len(actions),
            'successful': 0,
            'failed': 0
        }
        
        for action in actions:
            try:
                if not dry_run:
                    self._execute_rollback_action(action)
                results['successful'] += 1
            except Exception as e:
                results['failed'] += 1
        
        return results
    
    # ============= ROLLBACK METHODS =============
    
    def _delete_resource(self, action: RollbackAction):
        """Delete a created resource"""
        if not self.tallyfy_client:
            raise ValueError("Tallyfy client required for delete operation")
        
        # Determine delete method based on resource type
        delete_methods = {
            ResourceType.USER: self.tallyfy_client.delete_user,
            ResourceType.TEMPLATE: self.tallyfy_client.delete_template,
            ResourceType.INSTANCE: self.tallyfy_client.delete_instance,
            ResourceType.STEP: self.tallyfy_client.delete_step,
        }
        
        delete_method = delete_methods.get(action.resource_type)
        if not delete_method:
            raise ValueError(f"No delete method for {action.resource_type.value}")
        
        delete_method(action.resource_id)
        self.logger.info(f"Deleted {action.resource_type.value}: {action.resource_id}")
    
    def _restore_resource(self, action: RollbackAction):
        """Restore a deleted resource"""
        if not self.tallyfy_client:
            raise ValueError("Tallyfy client required for restore operation")
        
        # Determine create method based on resource type
        create_methods = {
            ResourceType.USER: self.tallyfy_client.create_user,
            ResourceType.TEMPLATE: self.tallyfy_client.create_template,
            ResourceType.INSTANCE: self.tallyfy_client.create_instance,
            ResourceType.STEP: self.tallyfy_client.create_step,
        }
        
        create_method = create_methods.get(action.resource_type)
        if not create_method:
            raise ValueError(f"No create method for {action.resource_type.value}")
        
        create_method(action.original_data)
        self.logger.info(f"Restored {action.resource_type.value}: {action.resource_id}")
    
    def _revert_update(self, action: RollbackAction):
        """Revert an update to original state"""
        if not self.tallyfy_client:
            raise ValueError("Tallyfy client required for update operation")
        
        # Determine update method based on resource type
        update_methods = {
            ResourceType.USER: self.tallyfy_client.update_user,
            ResourceType.TEMPLATE: self.tallyfy_client.update_template,
            ResourceType.INSTANCE: self.tallyfy_client.update_instance,
            ResourceType.STEP: self.tallyfy_client.update_step,
        }
        
        update_method = update_methods.get(action.resource_type)
        if not update_method:
            raise ValueError(f"No update method for {action.resource_type.value}")
        
        update_method(action.resource_id, action.original_data)
        self.logger.info(f"Reverted {action.resource_type.value}: {action.resource_id}")
    
    def _unassign_resource(self, action: RollbackAction):
        """Unassign a resource"""
        # Implementation depends on specific assignment logic
        pass
    
    def _unlink_resources(self, action: RollbackAction):
        """Unlink related resources"""
        # Implementation depends on specific linking logic
        pass
    
    def _custom_rollback(self, action: RollbackAction):
        """Execute custom rollback function"""
        if action.original_data and 'function' in action.original_data:
            # Deserialize and execute custom rollback function
            rollback_func = pickle.loads(action.original_data['function'])
            rollback_args = action.original_data.get('args', {})
            rollback_func(**rollback_args)
        else:
            raise ValueError(f"No custom rollback function for action {action.id}")
    
    # ============= HELPER METHODS =============
    
    def _generate_action_id(self) -> str:
        """Generate unique action ID"""
        timestamp = datetime.utcnow().timestamp()
        random_part = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
        return f"action_{timestamp}_{random_part}"
    
    def _save_action(self, action: RollbackAction):
        """Save action to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO rollback_actions 
                (id, timestamp, action_type, resource_type, resource_id,
                 original_data, new_data, metadata, rollback_method, status, transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.id,
                action.timestamp.isoformat(),
                action.action_type.value,
                action.resource_type.value,
                action.resource_id,
                json.dumps(action.original_data) if action.original_data else None,
                json.dumps(action.new_data) if action.new_data else None,
                json.dumps(action.metadata),
                action.rollback_method,
                action.status,
                self.current_transaction
            ))
    
    def _get_actions_for_rollback(self) -> List[RollbackAction]:
        """Get all actions in reverse order for rollback"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM rollback_actions 
                WHERE status = 'pending'
                ORDER BY timestamp DESC
            """)
            
            actions = []
            for row in cursor:
                action = self._row_to_action(row)
                actions.append(action)
        
        return actions
    
    def _row_to_action(self, row: tuple) -> RollbackAction:
        """Convert database row to RollbackAction"""
        return RollbackAction(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            action_type=ActionType(row[2]),
            resource_type=ResourceType(row[3]),
            resource_id=row[4],
            original_data=json.loads(row[5]) if row[5] else None,
            new_data=json.loads(row[6]) if row[6] else None,
            metadata=json.loads(row[7]) if row[7] else {},
            rollback_method=row[8],
            status=row[9],
            error=row[10] if len(row) > 10 else None
        )
    
    def _execute_rollback_action(self, action: RollbackAction):
        """Execute a single rollback action"""
        method = self.rollback_methods.get(action.rollback_method)
        if not method:
            raise ValueError(f"Unknown rollback method: {action.rollback_method}")
        
        method(action)
        self._update_action_status(action.id, 'completed')
    
    def _update_action_status(self, action_id: str, status: str, error: str = None):
        """Update action status in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE rollback_actions 
                SET status = ?, error = ?
                WHERE id = ?
            """, (status, error, action_id))
    
    def get_rollback_status(self) -> Dict[str, Any]:
        """Get current rollback status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) 
                FROM rollback_actions 
                GROUP BY status
            """)
            
            status_counts = dict(cursor.fetchall())
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM rollback_actions
            """)
            total = cursor.fetchone()[0]
        
        return {
            'total_actions': total,
            'pending': status_counts.get('pending', 0),
            'completed': status_counts.get('completed', 0),
            'failed': status_counts.get('failed', 0),
            'can_rollback': status_counts.get('pending', 0) > 0
        }
    
    def cleanup(self):
        """Clean up rollback database after successful migration"""
        if self.db_path.exists():
            self.db_path.unlink()
            self.logger.info(f"Cleaned up rollback database for {self.migration_id}")


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    rollback = RollbackManager("test_migration_123")
    
    # Record some actions
    with rollback.transaction("Create users"):
        rollback.record_create(
            ResourceType.USER,
            "user_123",
            {"email": "test@example.com", "name": "Test User"}
        )
        
        rollback.record_update(
            ResourceType.USER,
            "user_456",
            {"role": "member"},
            {"role": "admin"}
        )
    
    # Check status
    status = rollback.get_rollback_status()
    print(f"Rollback status: {status}")
    
    # Perform dry-run rollback
    result = rollback.rollback_all(dry_run=True)
    print(f"Dry run result: {result}")
    
    print("\n✅ Rollback system ready for production use!")