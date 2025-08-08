"""Checkpoint management for resumable migrations."""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage migration checkpoints for resume capability."""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory for checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.checkpoint_dir / "checkpoints.db"
        self._init_database()
        self.current_run_id = None
        
    def _init_database(self):
        """Initialize checkpoint database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Migration runs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migration_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'in_progress',
                    workspace_gid TEXT,
                    config TEXT
                )
            ''')
            
            # Phase checkpoints table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS phase_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    data TEXT,
                    error TEXT,
                    FOREIGN KEY (run_id) REFERENCES migration_runs(run_id)
                )
            ''')
            
            # Item checkpoints table (for granular tracking)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS item_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    FOREIGN KEY (run_id) REFERENCES migration_runs(run_id),
                    UNIQUE(run_id, phase, item_type, item_id)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_phase_run ON phase_checkpoints(run_id, phase)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_item_run ON item_checkpoints(run_id, phase)')
            
            conn.commit()
    
    def start_migration(self, workspace_gid: str, config: Dict[str, Any]) -> str:
        """Start a new migration run.
        
        Args:
            workspace_gid: Asana workspace GID
            config: Migration configuration
            
        Returns:
            Run ID
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_run_id = run_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO migration_runs (run_id, workspace_gid, config)
                VALUES (?, ?, ?)
            ''', (run_id, workspace_gid, json.dumps(config)))
            conn.commit()
        
        logger.info(f"Started migration run: {run_id}")
        return run_id
    
    def save_phase_checkpoint(self, phase: str, status: str = 'in_progress',
                             data: Optional[Dict[str, Any]] = None,
                             error: Optional[str] = None) -> None:
        """Save phase checkpoint.
        
        Args:
            phase: Phase name
            status: Phase status (in_progress, completed, failed)
            data: Optional phase data
            error: Optional error message
        """
        if not self.current_run_id:
            raise ValueError("No active migration run")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if phase checkpoint exists
            cursor.execute('''
                SELECT id FROM phase_checkpoints 
                WHERE run_id = ? AND phase = ?
            ''', (self.current_run_id, phase))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing checkpoint
                if status == 'completed':
                    cursor.execute('''
                        UPDATE phase_checkpoints 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP, data = ?, error = ?
                        WHERE run_id = ? AND phase = ?
                    ''', (status, json.dumps(data) if data else None, error,
                         self.current_run_id, phase))
                else:
                    cursor.execute('''
                        UPDATE phase_checkpoints 
                        SET status = ?, data = ?, error = ?
                        WHERE run_id = ? AND phase = ?
                    ''', (status, json.dumps(data) if data else None, error,
                         self.current_run_id, phase))
            else:
                # Create new checkpoint
                cursor.execute('''
                    INSERT INTO phase_checkpoints (run_id, phase, status, data, error)
                    VALUES (?, ?, ?, ?, ?)
                ''', (self.current_run_id, phase, status,
                     json.dumps(data) if data else None, error))
            
            conn.commit()
        
        logger.debug(f"Saved checkpoint for phase {phase}: {status}")
    
    def save_item_checkpoint(self, phase: str, item_type: str,
                           item_id: str, status: str = 'completed',
                           data: Optional[Dict[str, Any]] = None) -> None:
        """Save individual item checkpoint.
        
        Args:
            phase: Current phase
            item_type: Type of item (user, project, task, etc.)
            item_id: Item identifier
            status: Processing status
            data: Optional item data
        """
        if not self.current_run_id:
            raise ValueError("No active migration run")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO item_checkpoints 
                (run_id, phase, item_type, item_id, status, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.current_run_id, phase, item_type, item_id, status,
                 json.dumps(data) if data else None))
            conn.commit()
    
    def get_processed_items(self, phase: str, item_type: str) -> List[str]:
        """Get list of already processed items.
        
        Args:
            phase: Phase name
            item_type: Type of items
            
        Returns:
            List of processed item IDs
        """
        if not self.current_run_id:
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT item_id FROM item_checkpoints
                WHERE run_id = ? AND phase = ? AND item_type = ? AND status = 'completed'
            ''', (self.current_run_id, phase, item_type))
            
            return [row[0] for row in cursor.fetchall()]
    
    def get_latest_incomplete_run(self, workspace_gid: str) -> Optional[str]:
        """Get the latest incomplete migration run.
        
        Args:
            workspace_gid: Workspace GID
            
        Returns:
            Run ID or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT run_id FROM migration_runs
                WHERE workspace_gid = ? AND status = 'in_progress'
                ORDER BY started_at DESC
                LIMIT 1
            ''', (workspace_gid,))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def resume_migration(self, run_id: str) -> Tuple[List[str], Dict[str, Any]]:
        """Resume a migration from checkpoint.
        
        Args:
            run_id: Run ID to resume
            
        Returns:
            Tuple of (remaining phases, checkpoint data)
        """
        self.current_run_id = run_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get migration config
            cursor.execute('''
                SELECT config FROM migration_runs WHERE run_id = ?
            ''', (run_id,))
            config_row = cursor.fetchone()
            config = json.loads(config_row[0]) if config_row else {}
            
            # Get completed phases
            cursor.execute('''
                SELECT phase FROM phase_checkpoints
                WHERE run_id = ? AND status = 'completed'
            ''', (run_id,))
            completed_phases = [row[0] for row in cursor.fetchall()]
            
            # Get last checkpoint data
            cursor.execute('''
                SELECT phase, data FROM phase_checkpoints
                WHERE run_id = ? AND data IS NOT NULL
                ORDER BY id DESC LIMIT 1
            ''', (run_id,))
            
            checkpoint_row = cursor.fetchone()
            checkpoint_data = json.loads(checkpoint_row[1]) if checkpoint_row else {}
            
            # Determine remaining phases
            all_phases = ['discovery', 'users', 'teams', 'projects', 'tasks', 'validation']
            remaining_phases = [p for p in all_phases if p not in completed_phases]
            
            logger.info(f"Resuming migration {run_id}")
            logger.info(f"Completed phases: {completed_phases}")
            logger.info(f"Remaining phases: {remaining_phases}")
            
            return remaining_phases, {
                'config': config,
                'checkpoint_data': checkpoint_data,
                'completed_phases': completed_phases
            }
    
    def complete_migration(self, status: str = 'completed') -> None:
        """Mark migration as complete.
        
        Args:
            status: Final status (completed, failed, cancelled)
        """
        if not self.current_run_id:
            raise ValueError("No active migration run")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE migration_runs
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE run_id = ?
            ''', (status, self.current_run_id))
            conn.commit()
        
        logger.info(f"Migration {self.current_run_id} marked as {status}")
    
    def get_run_statistics(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a migration run.
        
        Args:
            run_id: Run ID (uses current if not provided)
            
        Returns:
            Run statistics
        """
        run_id = run_id or self.current_run_id
        if not run_id:
            return {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get run info
            cursor.execute('''
                SELECT started_at, completed_at, status, workspace_gid
                FROM migration_runs WHERE run_id = ?
            ''', (run_id,))
            run_info = cursor.fetchone()
            
            if not run_info:
                return {}
            
            # Get phase statistics
            cursor.execute('''
                SELECT phase, status, started_at, completed_at
                FROM phase_checkpoints WHERE run_id = ?
            ''', (run_id,))
            phases = cursor.fetchall()
            
            # Get item counts
            cursor.execute('''
                SELECT item_type, COUNT(*) as count
                FROM item_checkpoints 
                WHERE run_id = ? AND status = 'completed'
                GROUP BY item_type
            ''', (run_id,))
            item_counts = dict(cursor.fetchall())
            
            return {
                'run_id': run_id,
                'started_at': run_info[0],
                'completed_at': run_info[1],
                'status': run_info[2],
                'workspace_gid': run_info[3],
                'phases': [
                    {
                        'phase': p[0],
                        'status': p[1],
                        'started_at': p[2],
                        'completed_at': p[3]
                    }
                    for p in phases
                ],
                'items_processed': item_counts
            }
    
    def export_checkpoint(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Export checkpoint data for backup.
        
        Args:
            run_id: Run ID to export
            
        Returns:
            Checkpoint data
        """
        run_id = run_id or self.current_run_id
        if not run_id:
            return {}
        
        stats = self.get_run_statistics(run_id)
        processed_items = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all processed items
            cursor.execute('''
                SELECT phase, item_type, item_id, status, data
                FROM item_checkpoints WHERE run_id = ?
            ''', (run_id,))
            
            for row in cursor.fetchall():
                phase, item_type, item_id, status, data = row
                if phase not in processed_items:
                    processed_items[phase] = {}
                if item_type not in processed_items[phase]:
                    processed_items[phase][item_type] = []
                
                processed_items[phase][item_type].append({
                    'id': item_id,
                    'status': status,
                    'data': json.loads(data) if data else None
                })
        
        return {
            'exported_at': datetime.now().isoformat(),
            'run_statistics': stats,
            'processed_items': processed_items
        }