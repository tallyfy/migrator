"""ID mapping between Kissflow and Tallyfy objects."""

import sqlite3
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class IDMapper:
    """Manages ID mappings between Kissflow and Tallyfy objects."""
    
    def __init__(self, db_path: str = 'id_mappings.db'):
        """Initialize ID mapper with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self._create_tables()
        logger.info(f"ID Mapper initialized with database: {db_path}")
    
    def _create_tables(self):
        """Create mapping tables if they don't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_type TEXT NOT NULL,
                kissflow_id TEXT NOT NULL,
                tallyfy_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                UNIQUE(object_type, kissflow_id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_kissflow_id 
            ON id_mappings(object_type, kissflow_id)
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tallyfy_id 
            ON id_mappings(object_type, tallyfy_id)
        ''')
        
        self.connection.commit()
    
    def add_mapping(self, object_type: str, kissflow_id: str, 
                   tallyfy_id: str, metadata: Optional[str] = None):
        """Add ID mapping.
        
        Args:
            object_type: Type of object (user, process, board, app, dataset, instance)
            kissflow_id: Kissflow object ID
            tallyfy_id: Tallyfy object ID
            metadata: Optional metadata JSON string
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO id_mappings 
                (object_type, kissflow_id, tallyfy_id, metadata)
                VALUES (?, ?, ?, ?)
            ''', (object_type, kissflow_id, tallyfy_id, metadata))
            self.connection.commit()
            logger.debug(f"Added mapping: {object_type} {kissflow_id} -> {tallyfy_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to add mapping: {e}")
            raise
    
    def get_tallyfy_id(self, object_type: str, kissflow_id: str) -> Optional[str]:
        """Get Tallyfy ID for a Kissflow object.
        
        Args:
            object_type: Type of object
            kissflow_id: Kissflow object ID
            
        Returns:
            Tallyfy ID or None if not found
        """
        self.cursor.execute('''
            SELECT tallyfy_id FROM id_mappings
            WHERE object_type = ? AND kissflow_id = ?
        ''', (object_type, kissflow_id))
        
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_kissflow_id(self, object_type: str, tallyfy_id: str) -> Optional[str]:
        """Get Kissflow ID for a Tallyfy object.
        
        Args:
            object_type: Type of object
            tallyfy_id: Tallyfy object ID
            
        Returns:
            Kissflow ID or None if not found
        """
        self.cursor.execute('''
            SELECT kissflow_id FROM id_mappings
            WHERE object_type = ? AND tallyfy_id = ?
        ''', (object_type, tallyfy_id))
        
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_all_mappings(self, object_type: Optional[str] = None) -> List[Tuple]:
        """Get all mappings, optionally filtered by type.
        
        Args:
            object_type: Optional object type filter
            
        Returns:
            List of mapping tuples
        """
        if object_type:
            self.cursor.execute('''
                SELECT object_type, kissflow_id, tallyfy_id, created_at, metadata
                FROM id_mappings
                WHERE object_type = ?
                ORDER BY created_at DESC
            ''', (object_type,))
        else:
            self.cursor.execute('''
                SELECT object_type, kissflow_id, tallyfy_id, created_at, metadata
                FROM id_mappings
                ORDER BY object_type, created_at DESC
            ''')
        
        return self.cursor.fetchall()
    
    def get_mapping_stats(self) -> Dict[str, int]:
        """Get statistics about mappings.
        
        Returns:
            Dictionary with counts by object type
        """
        self.cursor.execute('''
            SELECT object_type, COUNT(*) as count
            FROM id_mappings
            GROUP BY object_type
        ''')
        
        stats = {}
        for row in self.cursor.fetchall():
            stats[row[0]] = row[1]
        
        return stats
    
    def delete_mapping(self, object_type: str, kissflow_id: str):
        """Delete a mapping.
        
        Args:
            object_type: Type of object
            kissflow_id: Kissflow object ID
        """
        self.cursor.execute('''
            DELETE FROM id_mappings
            WHERE object_type = ? AND kissflow_id = ?
        ''', (object_type, kissflow_id))
        self.connection.commit()
        logger.debug(f"Deleted mapping: {object_type} {kissflow_id}")
    
    def clear_all_mappings(self):
        """Clear all mappings (use with caution)."""
        self.cursor.execute('DELETE FROM id_mappings')
        self.connection.commit()
        logger.warning("Cleared all ID mappings")
    
    def export_mappings(self, file_path: str):
        """Export mappings to CSV file.
        
        Args:
            file_path: Path to CSV file
        """
        import csv
        
        mappings = self.get_all_mappings()
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Object Type', 'Kissflow ID', 'Tallyfy ID', 'Created At', 'Metadata'])
            writer.writerows(mappings)
        
        logger.info(f"Exported {len(mappings)} mappings to {file_path}")
    
    def import_mappings(self, file_path: str):
        """Import mappings from CSV file.
        
        Args:
            file_path: Path to CSV file
        """
        import csv
        
        count = 0
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.add_mapping(
                    row['Object Type'],
                    row['Kissflow ID'],
                    row['Tallyfy ID'],
                    row.get('Metadata')
                )
                count += 1
        
        logger.info(f"Imported {count} mappings from {file_path}")
    
    def close(self):
        """Close database connection."""
        self.connection.close()
        logger.debug("ID Mapper database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()