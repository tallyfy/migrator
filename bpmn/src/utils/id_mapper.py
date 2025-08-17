"""ID mapping utilities for BPMN to Tallyfy migration"""

import json
import sqlite3
from typing import Dict, Optional, Any
from pathlib import Path


class IDMapper:
    """Maps BPMN element IDs to Tallyfy IDs"""
    
    def __init__(self, db_path: str = None):
        """Initialize ID mapper with optional database path"""
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = Path.home() / '.bpmn_migrator' / 'id_mappings.db'
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.mappings = {}
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for persistent ID mappings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS id_mappings (
                source_id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                element_type TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_mapping(self, source_id: str, target_id: str, 
                   element_type: str = None, metadata: Dict = None):
        """Add an ID mapping"""
        self.mappings[source_id] = {
            'target_id': target_id,
            'element_type': element_type,
            'metadata': metadata or {}
        }
        
        # Also save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO id_mappings 
            (source_id, target_id, element_type, metadata)
            VALUES (?, ?, ?, ?)
        ''', (source_id, target_id, element_type, 
              json.dumps(metadata) if metadata else None))
        
        conn.commit()
        conn.close()
    
    def get_mapping(self, source_id: str) -> Optional[str]:
        """Get target ID for a source ID"""
        if source_id in self.mappings:
            return self.mappings[source_id]['target_id']
        
        # Try database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT target_id FROM id_mappings WHERE source_id = ?',
            (source_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_all_mappings(self) -> Dict[str, Any]:
        """Get all ID mappings"""
        return self.mappings.copy()
    
    def clear(self):
        """Clear all mappings"""
        self.mappings.clear()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM id_mappings')
        conn.commit()
        conn.close()