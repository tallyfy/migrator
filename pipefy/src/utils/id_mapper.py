"""
ID Mapping System for Pipefy to Tallyfy Migration
Maintains mappings between Pipefy and Tallyfy object IDs
"""

import sqlite3
import json
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class IDMapper:
    """Manages ID mappings between Pipefy and Tallyfy objects"""
    
    def __init__(self, db_path: str):
        """
        Initialize ID mapper with SQLite database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Statistics
        self.stats = {
            'mappings_created': 0,
            'lookups_performed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # In-memory cache for performance
        self.cache = {}
        self._load_cache()
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create mappings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_mappings (
                pipefy_id TEXT NOT NULL,
                tallyfy_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                PRIMARY KEY (pipefy_id, object_type)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pipefy_id 
            ON id_mappings(pipefy_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tallyfy_id 
            ON id_mappings(tallyfy_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_object_type 
            ON id_mappings(object_type)
        """)
        
        # Create reverse lookup table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reverse_mappings (
                tallyfy_id TEXT NOT NULL,
                pipefy_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                PRIMARY KEY (tallyfy_id, object_type)
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.debug(f"ID mapping database initialized at {self.db_path}")
    
    def _load_cache(self):
        """Load frequently accessed mappings into memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load recent mappings into cache
        cursor.execute("""
            SELECT pipefy_id, tallyfy_id, object_type 
            FROM id_mappings 
            ORDER BY created_at DESC 
            LIMIT 1000
        """)
        
        for pipefy_id, tallyfy_id, obj_type in cursor.fetchall():
            cache_key = f"{pipefy_id}:{obj_type}"
            self.cache[cache_key] = tallyfy_id
        
        conn.close()
        logger.debug(f"Loaded {len(self.cache)} mappings into cache")
    
    def add_mapping(self, pipefy_id: str, tallyfy_id: str, object_type: str, 
                   metadata: Optional[Dict] = None) -> None:
        """
        Add ID mapping between Pipefy and Tallyfy objects
        
        Args:
            pipefy_id: Pipefy object ID
            tallyfy_id: Tallyfy object ID
            object_type: Type of object (e.g., 'pipe', 'card', 'user', 'field')
            metadata: Optional metadata about the mapping
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert mapping
            cursor.execute("""
                INSERT OR REPLACE INTO id_mappings 
                (pipefy_id, tallyfy_id, object_type, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                pipefy_id,
                tallyfy_id,
                object_type,
                json.dumps(metadata) if metadata else None
            ))
            
            # Insert reverse mapping
            cursor.execute("""
                INSERT OR REPLACE INTO reverse_mappings 
                (tallyfy_id, pipefy_id, object_type)
                VALUES (?, ?, ?)
            """, (tallyfy_id, pipefy_id, object_type))
            
            conn.commit()
            
            # Update cache
            cache_key = f"{pipefy_id}:{object_type}"
            self.cache[cache_key] = tallyfy_id
            
            self.stats['mappings_created'] += 1
            
            logger.debug(f"Added mapping: {pipefy_id} ({object_type}) -> {tallyfy_id}")
            
        except Exception as e:
            logger.error(f"Failed to add mapping: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_tallyfy_id(self, pipefy_id: str, object_type: str) -> Optional[str]:
        """
        Get Tallyfy ID for a Pipefy object
        
        Args:
            pipefy_id: Pipefy object ID
            object_type: Type of object
            
        Returns:
            Tallyfy ID if mapping exists, None otherwise
        """
        self.stats['lookups_performed'] += 1
        
        # Check cache first
        cache_key = f"{pipefy_id}:{object_type}"
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        self.stats['cache_misses'] += 1
        
        # Query database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tallyfy_id 
            FROM id_mappings 
            WHERE pipefy_id = ? AND object_type = ?
        """, (pipefy_id, object_type))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            tallyfy_id = result[0]
            # Update cache
            self.cache[cache_key] = tallyfy_id
            return tallyfy_id
        
        return None
    
    def get_pipefy_id(self, tallyfy_id: str, object_type: str) -> Optional[str]:
        """
        Reverse lookup: Get Pipefy ID for a Tallyfy object
        
        Args:
            tallyfy_id: Tallyfy object ID
            object_type: Type of object
            
        Returns:
            Pipefy ID if mapping exists, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pipefy_id 
            FROM reverse_mappings 
            WHERE tallyfy_id = ? AND object_type = ?
        """, (tallyfy_id, object_type))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_all_mappings(self, object_type: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Get all mappings, optionally filtered by object type
        
        Args:
            object_type: Optional object type filter
            
        Returns:
            List of (pipefy_id, tallyfy_id, object_type) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if object_type:
            cursor.execute("""
                SELECT pipefy_id, tallyfy_id, object_type 
                FROM id_mappings 
                WHERE object_type = ?
                ORDER BY created_at DESC
            """, (object_type,))
        else:
            cursor.execute("""
                SELECT pipefy_id, tallyfy_id, object_type 
                FROM id_mappings 
                ORDER BY created_at DESC
            """)
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def has_mapping(self, pipefy_id: str, object_type: str) -> bool:
        """
        Check if mapping exists for Pipefy object
        
        Args:
            pipefy_id: Pipefy object ID
            object_type: Type of object
            
        Returns:
            True if mapping exists, False otherwise
        """
        return self.get_tallyfy_id(pipefy_id, object_type) is not None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get mapping statistics
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count mappings by type
        cursor.execute("""
            SELECT object_type, COUNT(*) 
            FROM id_mappings 
            GROUP BY object_type
        """)
        
        mappings_by_type = dict(cursor.fetchall())
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM id_mappings")
        total_mappings = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_mappings': total_mappings,
            'mappings_by_type': mappings_by_type,
            'cache_size': len(self.cache),
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['lookups_performed'] * 100
                if self.stats['lookups_performed'] > 0 else 0
            ),
            **self.stats
        }
    
    def export_mappings(self, output_file: str):
        """
        Export all mappings to JSON file
        
        Args:
            output_file: Path to output JSON file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pipefy_id, tallyfy_id, object_type, created_at, metadata
            FROM id_mappings
            ORDER BY created_at
        """)
        
        mappings = []
        for row in cursor.fetchall():
            mapping = {
                'pipefy_id': row[0],
                'tallyfy_id': row[1],
                'object_type': row[2],
                'created_at': row[3],
                'metadata': json.loads(row[4]) if row[4] else None
            }
            mappings.append(mapping)
        
        conn.close()
        
        with open(output_file, 'w') as f:
            json.dump(mappings, f, indent=2)
        
        logger.info(f"Exported {len(mappings)} mappings to {output_file}")
    
    def import_mappings(self, input_file: str):
        """
        Import mappings from JSON file
        
        Args:
            input_file: Path to input JSON file
        """
        with open(input_file, 'r') as f:
            mappings = json.load(f)
        
        for mapping in mappings:
            self.add_mapping(
                pipefy_id=mapping['pipefy_id'],
                tallyfy_id=mapping['tallyfy_id'],
                object_type=mapping['object_type'],
                metadata=mapping.get('metadata')
            )
        
        logger.info(f"Imported {len(mappings)} mappings from {input_file}")
    
    def clear_cache(self):
        """Clear in-memory cache"""
        self.cache.clear()
        logger.debug("Cache cleared")
    
    def vacuum_database(self):
        """Optimize database file size"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("VACUUM")
        conn.close()
        logger.debug("Database vacuumed")