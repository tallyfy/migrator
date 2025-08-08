"""Checkpoint management for resumable migration."""

import json
import os
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage migration checkpoints for resume capability."""
    
    def __init__(self, checkpoint_dir: str = ".monday_migration"):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.checkpoint_file = self.checkpoint_dir / "checkpoint.json"
        self.processed_file = self.checkpoint_dir / "processed_items.json"
        self.error_log_file = self.checkpoint_dir / "error_log.json"
        
        # In-memory cache of processed items
        self.processed_items = self._load_processed_items()
        
        logger.debug(f"Checkpoint manager initialized at {self.checkpoint_dir}")
    
    def save(self, state: Dict[str, Any]):
        """Save checkpoint state.
        
        Args:
            state: Migration state to save
        """
        try:
            checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'state': state,
                'version': '1.0'
            }
            
            # Write to temporary file_upload first
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            
            # Atomic rename
            temp_file.rename(self.checkpoint_file)
            
            logger.info(f"Checkpoint saved at {datetime.now().isoformat()}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def load(self) -> Dict[str, Any]:
        """Load checkpoint state.
        
        Returns:
            Saved state or empty dict
        """
        try:
            if not self.checkpoint_file.exists():
                logger.info("No checkpoint file found")
                return {}
            
            with open(self.checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            logger.info(f"Loaded checkpoint from {checkpoint_data.get('timestamp', 'unknown')}")
            
            return checkpoint_data.get('state', {})
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return {}
    
    def has_checkpoint(self) -> bool:
        """Check if checkpoint exists.
        
        Returns:
            True if checkpoint exists
        """
        return self.checkpoint_file.exists()
    
    def clear(self):
        """Clear all checkpoint data."""
        try:
            # Remove checkpoint file_upload
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info("Checkpoint file removed")
            
            # Clear processed items
            if self.processed_file.exists():
                self.processed_file.unlink()
                logger.info("Processed items file removed")
            
            # Clear error log
            if self.error_log_file.exists():
                self.error_log_file.unlink()
                logger.info("Error log file removed")
            
            # Clear in-memory cache
            self.processed_items.clear()
            
            logger.info("All checkpoint data cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear checkpoint: {e}")
    
    def mark_processed(self, item_type: str, item_id: str):
        """Mark an item as processed.
        
        Args:
            item_type: Type of item (board, user, item, etc.)
            item_id: Item identifier
        """
        key = f"{item_type}:{item_id}"
        
        # Add to in-memory set
        self.processed_items.add(key)
        
        # Persist to disk
        self._save_processed_items()
        
        logger.debug(f"Marked as processed: {key}")
    
    def is_processed(self, item_type: str, item_id: str) -> bool:
        """Check if item has been processed.
        
        Args:
            item_type: Type of item
            item_id: Item identifier
            
        Returns:
            True if already processed
        """
        key = f"{item_type}:{item_id}"
        return key in self.processed_items
    
    def get_processed_count(self, item_type: Optional[str] = None) -> int:
        """Get count of processed items.
        
        Args:
            item_type: Optional filter by type
            
        Returns:
            Count of processed items
        """
        if item_type:
            prefix = f"{item_type}:"
            return sum(1 for item in self.processed_items if item.startswith(prefix))
        return len(self.processed_items)
    
    def _load_processed_items(self) -> Set[str]:
        """Load processed items from file.
        
        Returns:
            Set of processed item keys
        """
        try:
            if not self.processed_file.exists():
                return set()
            
            with open(self.processed_file, 'r') as f:
                data = json.load(f)
                return set(data.get('processed', []))
                
        except Exception as e:
            logger.error(f"Failed to load processed items: {e}")
            return set()
    
    def _save_processed_items(self):
        """Save processed items to file."""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'count': len(self.processed_items),
                'processed': list(self.processed_items)
            }
            
            # Write to temporary file_upload first
            temp_file = self.processed_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            temp_file.rename(self.processed_file)
            
        except Exception as e:
            logger.error(f"Failed to save processed items: {e}")
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error to checkpoint error log.
        
        Args:
            error: Exception that occurred
            context: Context information
        """
        try:
            # Load existing errors
            errors = []
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r') as f:
                    errors = json.load(f)
            
            # Add new error
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context
            }
            errors.append(error_entry)
            
            # Keep only last 1000 errors
            if len(errors) > 1000:
                errors = errors[-1000:]
            
            # Save errors
            with open(self.error_log_file, 'w') as f:
                json.dump(errors, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to log error to checkpoint: {e}")
    
    def get_error_log(self) -> List[Dict[str, Any]]:
        """Get error log.
        
        Returns:
            List of error entries
        """
        try:
            if not self.error_log_file.exists():
                return []
            
            with open(self.error_log_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load error log: {e}")
            return []
    
    def create_backup(self):
        """Create backup of current checkpoint."""
        try:
            if not self.checkpoint_file.exists():
                logger.info("No checkpoint to backup")
                return
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.checkpoint_dir / f"checkpoint_backup_{timestamp}.json"
            
            # Copy checkpoint file_upload
            with open(self.checkpoint_file, 'r') as src:
                with open(backup_file, 'w') as dst:
                    dst.write(src.read())
            
            logger.info(f"Checkpoint backed up to {backup_file}")
            
            # Clean old backups (keep last 5)
            self._cleanup_old_backups()
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint backup: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 5):
        """Clean up old backup files.
        
        Args:
            keep_count: Number of backups to keep
        """
        try:
            # Find all backup files
            backup_files = list(self.checkpoint_dir.glob("checkpoint_backup_*.json"))
            
            # Sort by modification time
            backup_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove old backups
            if len(backup_files) > keep_count:
                for backup_file in backup_files[:-keep_count]:
                    backup_file.unlink()
                    logger.debug(f"Removed old backup: {backup_file}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def get_checkpoint_info(self) -> Dict[str, Any]:
        """Get information about current checkpoint.
        
        Returns:
            Checkpoint information
        """
        info = {
            'exists': self.has_checkpoint(),
            'checkpoint_dir': str(self.checkpoint_dir),
            'processed_count': len(self.processed_items),
            'processed_by_type': {}
        }
        
        if self.checkpoint_file.exists():
            info['checkpoint_file'] = str(self.checkpoint_file)
            info['checkpoint_size'] = self.checkpoint_file.stat().st_size
            info['checkpoint_modified'] = datetime.fromtimestamp(
                self.checkpoint_file.stat().st_mtime
            ).isoformat()
            
            # Count processed by type
            for item in self.processed_items:
                item_type = item.split(':')[0]
                info['processed_by_type'][item_type] = \
                    info['processed_by_type'].get(item_type, 0) + 1
        
        # Count errors
        if self.error_log_file.exists():
            errors = self.get_error_log()
            info['error_count'] = len(errors)
            if errors:
                info['last_error'] = errors[-1].get('timestamp')
        
        return info
    
    def validate_checkpoint(self) -> bool:
        """Validate checkpoint integrity.
        
        Returns:
            True if checkpoint is valid
        """
        try:
            if not self.checkpoint_file.exists():
                return True  # No checkpoint is valid
            
            # Try to load checkpoint
            with open(self.checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            # Check required fields
            if 'timestamp' not in checkpoint_data:
                logger.error("Checkpoint missing timestamp")
                return False
            
            if 'state' not in checkpoint_data:
                logger.error("Checkpoint missing state")
                return False
            
            # Validate timestamp format
            try:
                datetime.fromisoformat(checkpoint_data['timestamp'])
            except ValueError:
                logger.error("Invalid checkpoint timestamp format")
                return False
            
            logger.info("Checkpoint validation passed")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Checkpoint file is corrupted: {e}")
            return False
        except Exception as e:
            logger.error(f"Checkpoint validation failed: {e}")
            return False


from typing import List