"""Checkpoint management for resumable migrations"""

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointManager:
    """Manages checkpoints for resumable migration process"""
    
    def __init__(self, checkpoint_dir: str = None):
        """Initialize checkpoint manager"""
        if checkpoint_dir:
            self.checkpoint_dir = Path(checkpoint_dir)
        else:
            self.checkpoint_dir = Path.cwd() / 'checkpoints'
        
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.current_checkpoint = None
    
    def save_checkpoint(self, name: str, data: Any, metadata: Dict = None):
        """Save a checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{name}.checkpoint"
        
        checkpoint = {
            'name': name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {},
            'data': data
        }
        
        # Try JSON first, fall back to pickle for complex objects
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)
        except (TypeError, ValueError):
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
        
        self.current_checkpoint = name
        print(f"✓ Checkpoint saved: {name}")
    
    def load_checkpoint(self, name: str) -> Optional[Any]:
        """Load a checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{name}.checkpoint"
        
        if not checkpoint_file.exists():
            return None
        
        # Try JSON first, then pickle
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
        
        print(f"✓ Checkpoint loaded: {name}")
        return checkpoint.get('data')
    
    def checkpoint_exists(self, name: str) -> bool:
        """Check if a checkpoint exists"""
        checkpoint_file = self.checkpoint_dir / f"{name}.checkpoint"
        return checkpoint_file.exists()
    
    def list_checkpoints(self) -> list:
        """List all available checkpoints"""
        checkpoints = []
        
        for file in self.checkpoint_dir.glob('*.checkpoint'):
            try:
                # Try to read metadata
                with open(file, 'r') as f:
                    data = json.load(f)
                    checkpoints.append({
                        'name': data.get('name', file.stem),
                        'timestamp': data.get('timestamp'),
                        'file': str(file)
                    })
            except:
                checkpoints.append({
                    'name': file.stem,
                    'file': str(file)
                })
        
        return sorted(checkpoints, key=lambda x: x.get('timestamp', ''))
    
    def clear_checkpoints(self):
        """Clear all checkpoints"""
        for file in self.checkpoint_dir.glob('*.checkpoint'):
            file.unlink()
        print("✓ All checkpoints cleared")
    
    def get_last_checkpoint(self) -> Optional[str]:
        """Get the name of the last checkpoint"""
        checkpoints = self.list_checkpoints()
        return checkpoints[-1]['name'] if checkpoints else None