"""Manage migration checkpoints for resume capability."""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage checkpoints for resumable migration."""
    
    def __init__(self, checkpoint_dir: str = 'checkpoints'):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = checkpoint_dir
        self.current_checkpoint = None
        self.checkpoint_file = os.path.join(checkpoint_dir, 'current_checkpoint.json')
        
        # Create checkpoint directory if it doesn't exist
        os.makedirs(checkpoint_dir, exist_ok=True)
        logger.info(f"Checkpoint manager initialized with directory: {checkpoint_dir}")
    
    def create_checkpoint(self, phase: str, data: Dict[str, Any]) -> str:
        """Create a new checkpoint.
        
        Args:
            phase: Current migration phase
            data: Checkpoint data
            
        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        checkpoint = {
            'id': checkpoint_id,
            'phase': phase,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        # Save checkpoint
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)
        
        # Update current checkpoint
        self.current_checkpoint = checkpoint
        self._save_current_checkpoint()
        
        logger.info(f"Created checkpoint: {checkpoint_id}")
        
        return checkpoint_id
    
    def load_checkpoint(self, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load a checkpoint.
        
        Args:
            checkpoint_id: Optional checkpoint ID, loads current if not specified
            
        Returns:
            Checkpoint data or None
        """
        if checkpoint_id:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        else:
            checkpoint_path = self.checkpoint_file
        
        if not os.path.exists(checkpoint_path):
            logger.warning(f"Checkpoint not found: {checkpoint_path}")
            return None
        
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint = json.load(f)
            
            self.current_checkpoint = checkpoint
            logger.info(f"Loaded checkpoint: {checkpoint.get('id', 'current')}")
            
            return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def update_checkpoint(self, updates: Dict[str, Any]):
        """Update current checkpoint with new data.
        
        Args:
            updates: Data to update in checkpoint
        """
        if not self.current_checkpoint:
            logger.warning("No current checkpoint to update")
            return
        
        # Update checkpoint data
        self.current_checkpoint['data'].update(updates)
        self.current_checkpoint['last_updated'] = datetime.now().isoformat()
        
        # Save updated checkpoint
        self._save_current_checkpoint()
        
        # Also save to timestamped file_upload
        checkpoint_id = self.current_checkpoint['id']
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        with open(checkpoint_path, 'w') as f:
            json.dump(self.current_checkpoint, f, indent=2, default=str)
        
        logger.debug(f"Updated checkpoint: {checkpoint_id}")
    
    def has_checkpoint(self) -> bool:
        """Check if a current checkpoint exists.
        
        Returns:
            True if checkpoint exists
        """
        return os.path.exists(self.checkpoint_file)
    
    def get_checkpoint_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current checkpoint.
        
        Returns:
            Checkpoint info or None
        """
        if not self.has_checkpoint():
            return None
        
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return None
        
        return {
            'id': checkpoint.get('id'),
            'phase': checkpoint.get('phase'),
            'timestamp': checkpoint.get('timestamp'),
            'last_updated': checkpoint.get('last_updated'),
            'statistics': self._extract_statistics(checkpoint.get('data', {}))
        }
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints.
        
        Returns:
            List of checkpoint info
        """
        checkpoints = []
        
        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith('.json') and filename != 'current_checkpoint.json':
                checkpoint_path = os.path.join(self.checkpoint_dir, filename)
                
                try:
                    with open(checkpoint_path, 'r') as f:
                        checkpoint = json.load(f)
                    
                    checkpoints.append({
                        'id': checkpoint.get('id'),
                        'phase': checkpoint.get('phase'),
                        'timestamp': checkpoint.get('timestamp'),
                        "file": filename
                    })
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {filename}: {e}")
        
        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return checkpoints
    
    def delete_checkpoint(self, checkpoint_id: str):
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to delete
        """
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
            logger.info(f"Deleted checkpoint: {checkpoint_id}")
            
            # Clear current checkpoint if it matches
            if self.current_checkpoint and self.current_checkpoint.get('id') == checkpoint_id:
                self.current_checkpoint = None
                if os.path.exists(self.checkpoint_file):
                    os.remove(self.checkpoint_file)
        else:
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
    
    def clear_all_checkpoints(self):
        """Clear all checkpoints (use with caution)."""
        count = 0
        
        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.checkpoint_dir, filename))
                count += 1
        
        self.current_checkpoint = None
        logger.warning(f"Cleared {count} checkpoints")
    
    def backup_checkpoints(self, backup_dir: str):
        """Backup all checkpoints to another directory.
        
        Args:
            backup_dir: Directory to backup checkpoints to
        """
        os.makedirs(backup_dir, exist_ok=True)
        
        count = 0
        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith('.json'):
                src = os.path.join(self.checkpoint_dir, filename)
                dst = os.path.join(backup_dir, filename)
                shutil.copy2(src, dst)
                count += 1
        
        logger.info(f"Backed up {count} checkpoints to {backup_dir}")
    
    def restore_checkpoints(self, backup_dir: str):
        """Restore checkpoints from backup.
        
        Args:
            backup_dir: Directory containing backup checkpoints
        """
        if not os.path.exists(backup_dir):
            logger.error(f"Backup directory not found: {backup_dir}")
            return
        
        count = 0
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                src = os.path.join(backup_dir, filename)
                dst = os.path.join(self.checkpoint_dir, filename)
                shutil.copy2(src, dst)
                count += 1
        
        # Load current checkpoint if it exists
        if os.path.exists(self.checkpoint_file):
            self.load_checkpoint()
        
        logger.info(f"Restored {count} checkpoints from {backup_dir}")
    
    def _save_current_checkpoint(self):
        """Save current checkpoint to file."""
        if not self.current_checkpoint:
            return
        
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.current_checkpoint, f, indent=2, default=str)
    
    def _extract_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract statistics from checkpoint data.
        
        Args:
            data: Checkpoint data
            
        Returns:
            Statistics summary
        """
        stats = {}
        
        # Extract common statistics
        if 'processed_items' in data:
            stats['processed_items'] = data['processed_items']
        
        if 'failed_items' in data:
            stats['failed_items'] = data['failed_items']
        
        if 'user_mapping' in data:
            stats['users_migrated'] = len(data['user_mapping'])
        
        if 'template_mapping' in data:
            stats['templates_migrated'] = len(data['template_mapping'])
        
        if 'instance_mapping' in data:
            stats['instances_migrated'] = len(data['instance_mapping'])
        
        return stats
    
    def get_resume_data(self) -> Optional[Dict[str, Any]]:
        """Get data needed to resume migration.
        
        Returns:
            Resume data or None
        """
        if not self.current_checkpoint:
            return None
        
        return {
            'phase': self.current_checkpoint.get('phase'),
            'data': self.current_checkpoint.get('data', {}),
            'timestamp': self.current_checkpoint.get('timestamp'),
            'last_updated': self.current_checkpoint.get('last_updated')
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - saves checkpoint on exit."""
        if exc_type is not None:
            # Save checkpoint on error
            logger.info("Saving checkpoint due to error...")
            if self.current_checkpoint:
                self.update_checkpoint({'error': str(exc_val)})


from typing import List