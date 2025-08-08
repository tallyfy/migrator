"""
ID Mapper
Manages mapping between Process Street and Tallyfy IDs
"""

import sqlite3
import json
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class IDMapper:
    """Manages ID mappings between Process Street and Tallyfy"""
    
    def __init__(self, db_path: str):
        """
        Initialize ID mapper with SQLite database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
        logger.info(f"ID Mapper initialized with database: {db_path}")
    
    def _create_tables(self):
        """Create mapping tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Main mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_mappings (
                source_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                tallyfy_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                PRIMARY KEY (source_id, entity_type)
            )
        """)
        
        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_lookup 
            ON id_mappings(source_id, entity_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tallyfy_lookup 
            ON id_mappings(tallyfy_id, entity_type)
        """)
        
        # Migration metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def add_mapping(self, source_id: str, tallyfy_id: str, entity_type: str, 
                   metadata: Optional[Dict] = None) -> bool:
        """
        Add an ID mapping
        
        Args:
            source_id: Process Street ID
            tallyfy_id: Tallyfy ID
            entity_type: Type of entity (user, checklist, process, etc.)
            metadata: Optional metadata about the mapping
            
        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO id_mappings 
                (source_id, source_type, tallyfy_id, entity_type, metadata)
                VALUES (?, 'process_street', ?, ?, ?)
            """, (source_id, tallyfy_id, entity_type, metadata_json))
            
            self.conn.commit()
            
            logger.debug(f"Added mapping: {source_id} -> {tallyfy_id} ({entity_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add mapping: {e}")
            return False
    
    def get_tallyfy_id(self, source_id: str, entity_type: str) -> Optional[str]:
        """
        Get Tallyfy ID for a Process Street ID
        
        Args:
            source_id: Process Street ID
            entity_type: Type of entity
            
        Returns:
            Tallyfy ID if mapped, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT tallyfy_id FROM id_mappings
                WHERE source_id = ? AND entity_type = ?
            """, (source_id, entity_type))
            
            row = cursor.fetchone()
            
            if row:
                return row['tallyfy_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Tallyfy ID: {e}")
            return None
    
    def get_source_id(self, tallyfy_id: str, entity_type: str) -> Optional[str]:
        """
        Get Process Street ID for a Tallyfy ID (reverse lookup)
        
        Args:
            tallyfy_id: Tallyfy ID
            entity_type: Type of entity
            
        Returns:
            Process Street ID if mapped, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT source_id FROM id_mappings
                WHERE tallyfy_id = ? AND entity_type = ?
            """, (tallyfy_id, entity_type))
            
            row = cursor.fetchone()
            
            if row:
                return row['source_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get source ID: {e}")
            return None
    
    def get_all_mappings(self, entity_type: Optional[str] = None) -> List[Dict]:
        """
        Get all ID mappings, optionally filtered by entity type
        
        Args:
            entity_type: Optional entity type filter
            
        Returns:
            List of mapping dictionaries
        """
        try:
            cursor = self.conn.cursor()
            
            if entity_type:
                cursor.execute("""
                    SELECT * FROM id_mappings
                    WHERE entity_type = ?
                    ORDER BY created_at DESC
                """, (entity_type,))
            else:
                cursor.execute("""
                    SELECT * FROM id_mappings
                    ORDER BY entity_type, created_at DESC
                """)
            
            rows = cursor.fetchall()
            
            mappings = []
            for row in rows:
                mapping = dict(row)
                if mapping.get('metadata'):
                    mapping['metadata'] = json.loads(mapping['metadata'])
                mappings.append(mapping)
            
            return mappings
            
        except Exception as e:
            logger.error(f"Failed to get mappings: {e}")
            return []
    
    def get_mapping_statistics(self) -> Dict[str, int]:
        """
        Get statistics about ID mappings
        
        Returns:
            Dictionary of statistics
        """
        try:
            cursor = self.conn.cursor()
            
            # Get counts by entity type
            cursor.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM id_mappings
                GROUP BY entity_type
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['entity_type']] = row['count']
            
            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM id_mappings")
            stats['total'] = cursor.fetchone()['total']
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def set_metadata(self, key: str, value: str) -> bool:
        """
        Set migration metadata
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO migration_metadata (key, value)
                VALUES (?, ?)
            """, (key, value))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set metadata: {e}")
            return False
    
    def get_metadata(self, key: str) -> Optional[str]:
        """
        Get migration metadata
        
        Args:
            key: Metadata key
            
        Returns:
            Metadata value if exists
        """
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT value FROM migration_metadata
                WHERE key = ?
            """, (key,))
            
            row = cursor.fetchone()
            
            if row:
                return row['value']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None
    
    def clear_mappings(self, entity_type: Optional[str] = None) -> bool:
        """
        Clear ID mappings
        
        Args:
            entity_type: Optional entity type to clear (None for all)
            
        Returns:
            Success status
        """
        try:
            cursor = self.conn.cursor()
            
            if entity_type:
                cursor.execute("""
                    DELETE FROM id_mappings
                    WHERE entity_type = ?
                """, (entity_type,))
                logger.info(f"Cleared mappings for entity type: {entity_type}")
            else:
                cursor.execute("DELETE FROM id_mappings")
                logger.info("Cleared all mappings")
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear mappings: {e}")
            return False
    
    def export_mappings(self, output_file: str) -> bool:
        """
        Export all mappings to a JSON file
        
        Args:
            output_file: Path to output file
            
        Returns:
            Success status
        """
        try:
            mappings = self.get_all_mappings()
            
            with open(output_file, 'w') as f:
                json.dump(mappings, f, indent=2)
            
            logger.info(f"Exported {len(mappings)} mappings to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export mappings: {e}")
            return False
    
    def import_mappings(self, input_file: str) -> bool:
        """
        Import mappings from a JSON file
        
        Args:
            input_file: Path to input file
            
        Returns:
            Success status
        """
        try:
            with open(input_file, 'r') as f:
                mappings = json.load(f)
            
            for mapping in mappings:
                self.add_mapping(
                    mapping['source_id'],
                    mapping['tallyfy_id'],
                    mapping['entity_type'],
                    mapping.get('metadata')
                )
            
            logger.info(f"Imported {len(mappings)} mappings from {input_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import mappings: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.debug("ID Mapper database connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()