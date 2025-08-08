"""
Checkpoint Manager for RocketLane Migration
Enables resume capability for interrupted migrations
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage migration checkpoints for resume capability"""
    
    def __init__(self, migration_id: str, db_path: str = "checkpoints.db"):
        """
        Initialize checkpoint manager
        
        Args:
            migration_id: Unique migration identifier
            db_path: Path to SQLite database
        """
        self.migration_id = migration_id
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        self._initialize_database()
        logger.info(f"Checkpoint manager initialized for migration: {migration_id}")
    
    def _initialize_database(self):
        """Initialize SQLite database with required tables"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create migrations table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                migration_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                phase TEXT,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                metadata TEXT
            )
        """)
        
        # Create checkpoints table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data TEXT,
                FOREIGN KEY (migration_id) REFERENCES migrations (migration_id),
                UNIQUE(migration_id, phase, item_type, item_id)
            )
        """)
        
        # Create ID mappings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_mappings (
                migration_id TEXT NOT NULL,
                source_system TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_system TEXT NOT NULL,
                target_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (migration_id, source_system, source_id),
                FOREIGN KEY (migration_id) REFERENCES migrations (migration_id)
            )
        """)
        
        # Create error log table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_id TEXT NOT NULL,
                phase TEXT,
                item_type TEXT,
                item_id TEXT,
                error_type TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (migration_id) REFERENCES migrations (migration_id)
            )
        """)
        
        self.conn.commit()
        
        # Initialize or update migration record
        self._initialize_migration()
    
    def _initialize_migration(self):
        """Initialize migration record"""
        now = datetime.utcnow().isoformat()
        
        self.cursor.execute("""
            INSERT OR IGNORE INTO migrations 
            (migration_id, status, started_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (self.migration_id, 'in_progress', now, now))
        
        self.conn.commit()
    
    def save_checkpoint(self, phase: str, item_type: str, item_id: str,
                       status: str = 'completed', data: Optional[Dict] = None):
        """
        Save a checkpoint for an item
        
        Args:
            phase: Migration phase (discovery, users, templates, instances, validation)
            item_type: Type of item (user, customer, template, project, etc.)
            item_id: Unique identifier for the item
            status: Status of the item (pending, in_progress, completed, failed)
            data: Optional data to store with checkpoint
        """
        now = datetime.utcnow().isoformat()
        data_json = json.dumps(data) if data else None
        
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO checkpoints
                (migration_id, phase, item_type, item_id, status, created_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.migration_id, phase, item_type, item_id, status, now, data_json))
            
            # Update migration phase
            self.cursor.execute("""
                UPDATE migrations
                SET phase = ?, updated_at = ?
                WHERE migration_id = ?
            """, (phase, now, self.migration_id))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            self.conn.rollback()
            raise
    
    def get_checkpoint(self, phase: str, item_type: str, 
                       item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get checkpoint for a specific item
        
        Args:
            phase: Migration phase
            item_type: Type of item
            item_id: Item identifier
            
        Returns:
            Checkpoint data or None
        """
        self.cursor.execute("""
            SELECT status, created_at, data
            FROM checkpoints
            WHERE migration_id = ? AND phase = ? AND item_type = ? AND item_id = ?
        """, (self.migration_id, phase, item_type, item_id))
        
        row = self.cursor.fetchone()
        if row:
            return {
                'status': row[0],
                'created_at': row[1],
                'data': json.loads(row[2]) if row[2] else None
            }
        return None
    
    def is_item_processed(self, phase: str, item_type: str, item_id: str) -> bool:
        """Check if an item has been processed"""
        checkpoint = self.get_checkpoint(phase, item_type, item_id)
        return checkpoint is not None and checkpoint['status'] in ['completed', 'failed']
    
    def get_phase_progress(self, phase: str) -> Dict[str, int]:
        """
        Get progress statistics for a phase
        
        Args:
            phase: Migration phase
            
        Returns:
            Dictionary with counts by status
        """
        self.cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM checkpoints
            WHERE migration_id = ? AND phase = ?
            GROUP BY status
        """, (self.migration_id, phase))
        
        progress = {}
        for row in self.cursor.fetchall():
            progress[row[0]] = row[1]
        
        return progress
    
    def get_pending_items(self, phase: str, item_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get pending items for a phase
        
        Args:
            phase: Migration phase
            item_type: Optional filter by item type
            limit: Maximum number of items to return
            
        Returns:
            List of pending items
        """
        query = """
            SELECT item_type, item_id, data
            FROM checkpoints
            WHERE migration_id = ? AND phase = ? AND status = 'pending'
        """
        params = [self.migration_id, phase]
        
        if item_type:
            query += " AND item_type = ?"
            params.append(item_type)
        
        query += " LIMIT ?"
        params.append(limit)
        
        self.cursor.execute(query, params)
        
        items = []
        for row in self.cursor.fetchall():
            items.append({
                'item_type': row[0],
                'item_id': row[1],
                'data': json.loads(row[2]) if row[2] else None
            })
        
        return items
    
    def save_id_mapping(self, source_id: str, target_id: str, entity_type: str,
                       source_system: str = 'rocketlane', target_system: str = 'tallyfy'):
        """
        Save ID mapping between systems
        
        Args:
            source_id: Source system ID
            target_id: Target system ID
            entity_type: Type of entity (user, template, project, etc.)
            source_system: Source system name
            target_system: Target system name
        """
        now = datetime.utcnow().isoformat()
        
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO id_mappings
                (migration_id, source_system, source_id, target_system, target_id, 
                 entity_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.migration_id, source_system, source_id, target_system, 
                  target_id, entity_type, now))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to save ID mapping: {e}")
            self.conn.rollback()
            raise
    
    def get_id_mapping(self, source_id: str, entity_type: Optional[str] = None,
                       source_system: str = 'rocketlane') -> Optional[str]:
        """
        Get target ID for a source ID
        
        Args:
            source_id: Source system ID
            entity_type: Optional entity type filter
            source_system: Source system name
            
        Returns:
            Target ID or None
        """
        query = """
            SELECT target_id
            FROM id_mappings
            WHERE migration_id = ? AND source_system = ? AND source_id = ?
        """
        params = [self.migration_id, source_system, source_id]
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        
        return row[0] if row else None
    
    def get_all_id_mappings(self, entity_type: Optional[str] = None) -> Dict[str, str]:
        """
        Get all ID mappings
        
        Args:
            entity_type: Optional filter by entity type
            
        Returns:
            Dictionary of source_id -> target_id mappings
        """
        query = """
            SELECT source_id, target_id
            FROM id_mappings
            WHERE migration_id = ?
        """
        params = [self.migration_id]
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        self.cursor.execute(query, params)
        
        mappings = {}
        for row in self.cursor.fetchall():
            mappings[row[0]] = row[1]
        
        return mappings
    
    def log_error(self, phase: str, item_type: str, item_id: str,
                 error_type: str, error_message: str):
        """
        Log an error during migration
        
        Args:
            phase: Migration phase
            item_type: Type of item
            item_id: Item identifier
            error_type: Type of error
            error_message: Error message
        """
        now = datetime.utcnow().isoformat()
        
        try:
            self.cursor.execute("""
                INSERT INTO error_log
                (migration_id, phase, item_type, item_id, error_type, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.migration_id, phase, item_type, item_id, error_type, 
                  error_message, now))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def get_errors(self, phase: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get errors from the migration
        
        Args:
            phase: Optional filter by phase
            
        Returns:
            List of errors
        """
        query = """
            SELECT phase, item_type, item_id, error_type, error_message, created_at
            FROM error_log
            WHERE migration_id = ?
        """
        params = [self.migration_id]
        
        if phase:
            query += " AND phase = ?"
            params.append(phase)
        
        query += " ORDER BY created_at DESC"
        
        self.cursor.execute(query, params)
        
        errors = []
        for row in self.cursor.fetchall():
            errors.append({
                'phase': row[0],
                'item_type': row[1],
                'item_id': row[2],
                'error_type': row[3],
                'error_message': row[4],
                'created_at': row[5]
            })
        
        return errors
    
    def mark_migration_complete(self):
        """Mark migration as completed"""
        now = datetime.utcnow().isoformat()
        
        self.cursor.execute("""
            UPDATE migrations
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE migration_id = ?
        """, (now, now, self.migration_id))
        
        self.conn.commit()
    
    def mark_migration_failed(self, error_message: str):
        """Mark migration as failed"""
        now = datetime.utcnow().isoformat()
        
        self.cursor.execute("""
            UPDATE migrations
            SET status = 'failed', updated_at = ?, metadata = ?
            WHERE migration_id = ?
        """, (now, json.dumps({'error': error_message}), self.migration_id))
        
        self.conn.commit()
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        self.cursor.execute("""
            SELECT status, phase, started_at, updated_at, completed_at, metadata
            FROM migrations
            WHERE migration_id = ?
        """, (self.migration_id,))
        
        row = self.cursor.fetchone()
        if row:
            return {
                'migration_id': self.migration_id,
                'status': row[0],
                'phase': row[1],
                'started_at': row[2],
                'updated_at': row[3],
                'completed_at': row[4],
                'metadata': json.loads(row[5]) if row[5] else None
            }
        return None
    
    def can_resume(self) -> bool:
        """Check if migration can be resumed"""
        status = self.get_migration_status()
        return status and status['status'] == 'in_progress'
    
    def get_resume_point(self) -> Dict[str, Any]:
        """Get the point to resume migration from"""
        status = self.get_migration_status()
        if not status:
            return None
        
        # Get last checkpoint
        self.cursor.execute("""
            SELECT phase, item_type, item_id, status
            FROM checkpoints
            WHERE migration_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (self.migration_id,))
        
        row = self.cursor.fetchone()
        if row:
            return {
                'phase': row[0],
                'last_item_type': row[1],
                'last_item_id': row[2],
                'last_status': row[3]
            }
        
        return {'phase': status['phase'] or 'discovery'}
    
    def cleanup(self, keep_mappings: bool = True):
        """
        Clean up migration data
        
        Args:
            keep_mappings: Whether to keep ID mappings
        """
        if not keep_mappings:
            # Delete all migration data
            self.cursor.execute("DELETE FROM error_log WHERE migration_id = ?", 
                              (self.migration_id,))
            self.cursor.execute("DELETE FROM checkpoints WHERE migration_id = ?", 
                              (self.migration_id,))
            self.cursor.execute("DELETE FROM id_mappings WHERE migration_id = ?", 
                              (self.migration_id,))
            self.cursor.execute("DELETE FROM migrations WHERE migration_id = ?", 
                              (self.migration_id,))
        else:
            # Keep mappings but clean up other data
            self.cursor.execute("DELETE FROM error_log WHERE migration_id = ?", 
                              (self.migration_id,))
            self.cursor.execute("DELETE FROM checkpoints WHERE migration_id = ?", 
                              (self.migration_id,))
        
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()