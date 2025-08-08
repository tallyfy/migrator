"""ID mapping between Asana and Tallyfy entities."""

import sqlite3
import json
import logging
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class IDMapper:
    """Manages ID mappings between Asana and Tallyfy."""
    
    def __init__(self, db_path: str = "data/id_mappings.db"):
        """Initialize ID mapper with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database with mapping tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_mappings (
                    asana_gid TEXT PRIMARY KEY,
                    tallyfy_id TEXT NOT NULL,
                    email TEXT,
                    name TEXT,
                    role TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Teams/Groups mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_mappings (
                    asana_gid TEXT PRIMARY KEY,
                    tallyfy_id TEXT NOT NULL,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Projects/Blueprints mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_mappings (
                    asana_gid TEXT PRIMARY KEY,
                    tallyfy_id TEXT NOT NULL,
                    name TEXT,
                    is_template BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Tasks/Steps mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_mappings (
                    asana_gid TEXT PRIMARY KEY,
                    tallyfy_id TEXT NOT NULL,
                    name TEXT,
                    project_gid TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Custom fields mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS field_mappings (
                    asana_gid TEXT PRIMARY KEY,
                    tallyfy_alias TEXT NOT NULL,
                    name TEXT,
                    field_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Tags mapping table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tag_mappings (
                    asana_gid TEXT PRIMARY KEY,
                    tallyfy_id TEXT NOT NULL,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON user_mappings(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_template ON project_mappings(is_template)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_project ON task_mappings(project_gid)')
            
            conn.commit()
            logger.info(f"Initialized ID mapping database at {self.db_path}")
    
    def add_user_mapping(self, asana_gid: str, tallyfy_id: str,
                        email: str = None, name: str = None,
                        role: str = None, metadata: Dict = None) -> None:
        """Add user ID mapping.
        
        Args:
            asana_gid: Asana user GID
            tallyfy_id: Tallyfy member ID
            email: User email
            name: User name
            role: User role
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_mappings 
                (asana_gid, tallyfy_id, email, name, role, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (asana_gid, tallyfy_id, email, name, role,
                 json.dumps(metadata) if metadata else None))
            conn.commit()
            logger.debug(f"Mapped user {asana_gid} -> {tallyfy_id}")
    
    def add_team_mapping(self, asana_gid: str, tallyfy_id: str,
                        name: str = None, metadata: Dict = None) -> None:
        """Add team/group ID mapping.
        
        Args:
            asana_gid: Asana team GID
            tallyfy_id: Tallyfy group ID
            name: Team name
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO team_mappings 
                (asana_gid, tallyfy_id, name, metadata)
                VALUES (?, ?, ?, ?)
            ''', (asana_gid, tallyfy_id, name,
                 json.dumps(metadata) if metadata else None))
            conn.commit()
            logger.debug(f"Mapped team {asana_gid} -> {tallyfy_id}")
    
    def add_project_mapping(self, asana_gid: str, tallyfy_id: str,
                          name: str = None, is_template: bool = False,
                          metadata: Dict = None) -> None:
        """Add project/blueprint ID mapping.
        
        Args:
            asana_gid: Asana project GID
            tallyfy_id: Tallyfy blueprint/process ID
            name: Project name
            is_template: Whether this is a template
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO project_mappings 
                (asana_gid, tallyfy_id, name, is_template, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (asana_gid, tallyfy_id, name, is_template,
                 json.dumps(metadata) if metadata else None))
            conn.commit()
            logger.debug(f"Mapped project {asana_gid} -> {tallyfy_id}")
    
    def add_task_mapping(self, asana_gid: str, tallyfy_id: str,
                        name: str = None, project_gid: str = None,
                        metadata: Dict = None) -> None:
        """Add task/step ID mapping.
        
        Args:
            asana_gid: Asana task GID
            tallyfy_id: Tallyfy step/task ID
            name: Task name
            project_gid: Parent project GID
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO task_mappings 
                (asana_gid, tallyfy_id, name, project_gid, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (asana_gid, tallyfy_id, name, project_gid,
                 json.dumps(metadata) if metadata else None))
            conn.commit()
            logger.debug(f"Mapped task {asana_gid} -> {tallyfy_id}")
    
    def add_field_mapping(self, asana_gid: str, tallyfy_alias: str,
                         name: str = None, field_type: str = None,
                         metadata: Dict = None) -> None:
        """Add custom field mapping.
        
        Args:
            asana_gid: Asana custom field GID
            tallyfy_alias: Tallyfy field alias
            name: Field name
            field_type: Field type
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO field_mappings 
                (asana_gid, tallyfy_alias, name, field_type, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (asana_gid, tallyfy_alias, name, field_type,
                 json.dumps(metadata) if metadata else None))
            conn.commit()
            logger.debug(f"Mapped field {asana_gid} -> {tallyfy_alias}")
    
    def add_tag_mapping(self, asana_gid: str, tallyfy_id: str,
                       name: str = None) -> None:
        """Add tag mapping.
        
        Args:
            asana_gid: Asana tag GID
            tallyfy_id: Tallyfy tag ID
            name: Tag name
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tag_mappings 
                (asana_gid, tallyfy_id, name)
                VALUES (?, ?, ?)
            ''', (asana_gid, tallyfy_id, name))
            conn.commit()
            logger.debug(f"Mapped tag {asana_gid} -> {tallyfy_id}")
    
    def get_user_mapping(self, asana_gid: str) -> Optional[str]:
        """Get Tallyfy ID for Asana user.
        
        Args:
            asana_gid: Asana user GID
            
        Returns:
            Tallyfy member ID or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tallyfy_id FROM user_mappings WHERE asana_gid = ?',
                         (asana_gid,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_user_by_email(self, email: str) -> Optional[str]:
        """Get Tallyfy ID by email.
        
        Args:
            email: User email
            
        Returns:
            Tallyfy member ID or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tallyfy_id FROM user_mappings WHERE email = ?',
                         (email,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_team_mapping(self, asana_gid: str) -> Optional[str]:
        """Get Tallyfy ID for Asana team.
        
        Args:
            asana_gid: Asana team GID
            
        Returns:
            Tallyfy group ID or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tallyfy_id FROM team_mappings WHERE asana_gid = ?',
                         (asana_gid,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_project_mapping(self, asana_gid: str) -> Optional[str]:
        """Get Tallyfy ID for Asana project.
        
        Args:
            asana_gid: Asana project GID
            
        Returns:
            Tallyfy blueprint/process ID or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tallyfy_id FROM project_mappings WHERE asana_gid = ?',
                         (asana_gid,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_task_mapping(self, asana_gid: str) -> Optional[str]:
        """Get Tallyfy ID for Asana task.
        
        Args:
            asana_gid: Asana task GID
            
        Returns:
            Tallyfy step/task ID or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tallyfy_id FROM task_mappings WHERE asana_gid = ?',
                         (asana_gid,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_field_mapping(self, asana_gid: str) -> Optional[str]:
        """Get Tallyfy alias for Asana custom field.
        
        Args:
            asana_gid: Asana field GID
            
        Returns:
            Tallyfy field alias or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tallyfy_alias FROM field_mappings WHERE asana_gid = ?',
                         (asana_gid,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_all_user_mappings(self) -> Dict[str, str]:
        """Get all user mappings.
        
        Returns:
            Dictionary of Asana GID to Tallyfy ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT asana_gid, tallyfy_id FROM user_mappings')
            return dict(cursor.fetchall())
    
    def get_statistics(self) -> Dict[str, int]:
        """Get mapping statistics.
        
        Returns:
            Dictionary of entity counts
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            stats = {}
            
            for table in ['user_mappings', 'team_mappings', 'project_mappings',
                         'task_mappings', 'field_mappings', 'tag_mappings']:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                entity = table.replace('_mappings', 's')
                stats[entity] = count
            
            return stats
    
    def export_mappings(self) -> Dict[str, Any]:
        """Export all mappings for backup.
        
        Returns:
            Dictionary of all mappings
        """
        mappings = {
            'exported_at': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'mappings': {}
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Export each table
            tables = ['user_mappings', 'team_mappings', 'project_mappings',
                     'task_mappings', 'field_mappings', 'tag_mappings']
            
            for table in tables:
                cursor.execute(f'SELECT * FROM {table}')
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                mappings['mappings'][table] = [
                    dict(zip(columns, row)) for row in rows
                ]
        
        return mappings
    
    def import_mappings(self, mappings: Dict[str, Any]) -> None:
        """Import mappings from backup.
        
        Args:
            mappings: Dictionary of mappings to import
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for table_name, records in mappings.get('mappings', {}).items():
                for record in records:
                    # Build INSERT statement dynamically
                    columns = list(record.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    values = [record[col] for col in columns]
                    
                    query = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                    cursor.execute(query, values)
            
            conn.commit()
            logger.info(f"Imported mappings from backup")