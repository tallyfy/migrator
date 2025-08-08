"""ID mapping management for Monday.com to Tallyfy migration."""

import json
import sqlite3
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class IDMapper:
    """Manages ID mappings between Monday.com and Tallyfy entities."""
    
    def __init__(self, db_path: str = "monday_migration.db"):
        """Initialize ID mapper with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_database()
        
        # In-memory cache for performance
        self.cache = {
            'user': {},
            'team': {},
            'board': {},
            'item': {},
            'column': {},
            'group': {}
        }
        self._load_cache()
    
    def _init_database(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_mappings (
                entity_type TEXT NOT NULL,
                monday_id TEXT NOT NULL,
                tallyfy_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                PRIMARY KEY (entity_type, monday_id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_entity_type 
            ON id_mappings(entity_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_monday_id 
            ON id_mappings(monday_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tallyfy_id 
            ON id_mappings(tallyfy_id)
        ''')
        
        self.conn.commit()
        logger.debug("ID mapping database initialized")
    
    def _load_cache(self):
        """Load mappings into memory cache."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM id_mappings')
        
        for row in cursor.fetchall():
            entity_type = row['entity_type']
            if entity_type in self.cache:
                self.cache[entity_type][row['monday_id']] = row['tallyfy_id']
        
        logger.debug(f"Loaded {sum(len(m) for m in self.cache.values())} mappings into cache")
    
    def add_mapping(self, entity_type: str, monday_id: str, 
                   tallyfy_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Add ID mapping.
        
        Args:
            entity_type: Type of entity (user, team, board, item, etc.)
            monday_id: Monday.com entity ID
            tallyfy_id: Tallyfy entity ID
            metadata: Optional metadata
        """
        cursor = self.conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO id_mappings 
            (entity_type, monday_id, tallyfy_id, metadata)
            VALUES (?, ?, ?, ?)
        ''', (entity_type, monday_id, tallyfy_id, metadata_json))
        
        self.conn.commit()
        
        # Update cache
        if entity_type in self.cache:
            self.cache[entity_type][monday_id] = tallyfy_id
        
        logger.debug(f"Added mapping: {entity_type} {monday_id} -> {tallyfy_id}")
    
    def get_mapping(self, entity_type: str, monday_id: str) -> Optional[str]:
        """Get Tallyfy ID for Monday.com entity.
        
        Args:
            entity_type: Type of entity
            monday_id: Monday.com entity ID
            
        Returns:
            Tallyfy ID or None
        """
        # Check cache first
        if entity_type in self.cache:
            return self.cache[entity_type].get(monday_id)
        
        # Fallback to database
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT tallyfy_id FROM id_mappings
            WHERE entity_type = ? AND monday_id = ?
        ''', (entity_type, monday_id))
        
        row = cursor.fetchone()
        return row['tallyfy_id'] if row else None
    
    def get_reverse_mapping(self, entity_type: str, tallyfy_id: str) -> Optional[str]:
        """Get Monday.com ID for Tallyfy entity.
        
        Args:
            entity_type: Type of entity
            tallyfy_id: Tallyfy entity ID
            
        Returns:
            Monday.com ID or None
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT monday_id FROM id_mappings
            WHERE entity_type = ? AND tallyfy_id = ?
        ''', (entity_type, tallyfy_id))
        
        row = cursor.fetchone()
        return row['monday_id'] if row else None
    
    def get_mappings(self, entity_type: str) -> Dict[str, str]:
        """Get all mappings for entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Dictionary of Monday ID to Tallyfy ID mappings
        """
        if entity_type in self.cache:
            return self.cache[entity_type].copy()
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT monday_id, tallyfy_id FROM id_mappings
            WHERE entity_type = ?
        ''', (entity_type,))
        
        mappings = {}
        for row in cursor.fetchall():
            mappings[row['monday_id']] = row['tallyfy_id']
        
        return mappings
    
    def get_all_mappings(self) -> Dict[str, Dict[str, str]]:
        """Get all mappings.
        
        Returns:
            Dictionary of entity types to mappings
        """
        all_mappings = {}
        
        for entity_type in self.cache.keys():
            mappings = self.get_mappings(entity_type)
            if mappings:
                all_mappings[entity_type] = mappings
        
        return all_mappings
    
    def has_mapping(self, entity_type: str, monday_id: str) -> bool:
        """Check if mapping exists.
        
        Args:
            entity_type: Type of entity
            monday_id: Monday.com entity ID
            
        Returns:
            True if mapping exists
        """
        return self.get_mapping(entity_type, monday_id) is not None
    
    def delete_mapping(self, entity_type: str, monday_id: str):
        """Delete ID mapping.
        
        Args:
            entity_type: Type of entity
            monday_id: Monday.com entity ID
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM id_mappings
            WHERE entity_type = ? AND monday_id = ?
        ''', (entity_type, monday_id))
        
        self.conn.commit()
        
        # Update cache
        if entity_type in self.cache and monday_id in self.cache[entity_type]:
            del self.cache[entity_type][monday_id]
        
        logger.debug(f"Deleted mapping: {entity_type} {monday_id}")
    
    def clear_entity_type(self, entity_type: str):
        """Clear all mappings for entity type.
        
        Args:
            entity_type: Type of entity
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM id_mappings
            WHERE entity_type = ?
        ''', (entity_type,))
        
        self.conn.commit()
        
        # Clear cache
        if entity_type in self.cache:
            self.cache[entity_type].clear()
        
        logger.info(f"Cleared all mappings for entity type: {entity_type}")
    
    def clear_all(self):
        """Clear all mappings."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM id_mappings')
        self.conn.commit()
        
        # Clear cache
        for entity_type in self.cache:
            self.cache[entity_type].clear()
        
        logger.info("Cleared all ID mappings")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mapping statistics.
        
        Returns:
            Statistics dictionary
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT entity_type, COUNT(*) as count
            FROM id_mappings
            GROUP BY entity_type
        ''')
        
        stats = {
            'total': 0,
            'by_type': {}
        }
        
        for row in cursor.fetchall():
            stats['by_type'][row['entity_type']] = row['count']
            stats['total'] += row['count']
        
        return stats
    
    def export_mappings(self, filepath: str):
        """Export mappings to JSON file.
        
        Args:
            filepath: Path to export file
        """
        mappings = self.get_all_mappings()
        stats = self.get_statistics()
        
        export_data = {
            'mappings': mappings,
            'statistics': stats
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {stats['total']} mappings to {filepath}")
    
    def import_mappings(self, filepath: str):
        """Import mappings from JSON file.
        
        Args:
            filepath: Path to import file
        """
        with open(filepath, 'r') as f:
            import_data = json.load(f)
        
        mappings = import_data.get('mappings', {})
        
        count = 0
        for entity_type, type_mappings in mappings.items():
            for monday_id, tallyfy_id in type_mappings.items():
                self.add_mapping(entity_type, monday_id, tallyfy_id)
                count += 1
        
        logger.info(f"Imported {count} mappings from {filepath}")
    
    def load_state(self, state: Dict[str, Dict[str, str]]):
        """Load mappings from state dictionary.
        
        Args:
            state: State dictionary with mappings
        """
        for entity_type, mappings in state.items():
            for monday_id, tallyfy_id in mappings.items():
                self.add_mapping(entity_type, monday_id, tallyfy_id)
    
    def close(self):
        """Close database connection."""
        self.conn.close()
        logger.debug("ID mapper database connection closed")
    
    def __del__(self):
        """Destructor to ensure database connection is closed."""
        if hasattr(self, 'conn'):
            self.conn.close()