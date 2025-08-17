"""Progress tracking for migration operations"""

import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class ProgressTracker:
    """Tracks progress of migration operations"""
    
    def __init__(self, total_items: int = 0, name: str = "Migration"):
        """Initialize progress tracker"""
        self.name = name
        self.total_items = total_items
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.start_time = None
        self.end_time = None
        self.current_phase = None
        self.phase_stats = {}
    
    def start(self, phase: str = None):
        """Start tracking progress"""
        self.start_time = time.time()
        if phase:
            self.current_phase = phase
            self.phase_stats[phase] = {
                'start_time': time.time(),
                'items': 0,
                'successful': 0,
                'failed': 0
            }
        print(f"⏱ Started: {self.name}")
        if phase:
            print(f"  Phase: {phase}")
    
    def update(self, success: bool = True, increment: int = 1):
        """Update progress"""
        self.processed_items += increment
        
        if success:
            self.successful_items += increment
        else:
            self.failed_items += increment
        
        if self.current_phase and self.current_phase in self.phase_stats:
            self.phase_stats[self.current_phase]['items'] += increment
            if success:
                self.phase_stats[self.current_phase]['successful'] += increment
            else:
                self.phase_stats[self.current_phase]['failed'] += increment
        
        # Print progress every 10% or every 10 items for small sets
        if self.total_items > 0:
            percentage = (self.processed_items / self.total_items) * 100
            if self.processed_items % max(1, self.total_items // 10) == 0:
                self.print_progress()
    
    def print_progress(self):
        """Print current progress"""
        if self.total_items > 0:
            percentage = (self.processed_items / self.total_items) * 100
            elapsed = time.time() - self.start_time if self.start_time else 0
            
            if self.processed_items > 0 and elapsed > 0:
                rate = self.processed_items / elapsed
                remaining = (self.total_items - self.processed_items) / rate if rate > 0 else 0
                
                print(f"  Progress: {self.processed_items}/{self.total_items} ({percentage:.1f}%)")
                print(f"  Rate: {rate:.1f} items/sec")
                print(f"  ETA: {self._format_time(remaining)}")
            else:
                print(f"  Progress: {self.processed_items}/{self.total_items} ({percentage:.1f}%)")
        else:
            print(f"  Processed: {self.processed_items} items")
    
    def change_phase(self, phase: str):
        """Change to a new phase"""
        if self.current_phase and self.current_phase in self.phase_stats:
            self.phase_stats[self.current_phase]['end_time'] = time.time()
        
        self.current_phase = phase
        self.phase_stats[phase] = {
            'start_time': time.time(),
            'items': 0,
            'successful': 0,
            'failed': 0
        }
        print(f"\n📍 Phase: {phase}")
    
    def finish(self):
        """Finish tracking"""
        self.end_time = time.time()
        
        if self.current_phase and self.current_phase in self.phase_stats:
            self.phase_stats[self.current_phase]['end_time'] = time.time()
        
        elapsed = self.end_time - self.start_time if self.start_time else 0
        
        print(f"\n✅ Completed: {self.name}")
        print(f"  Total time: {self._format_time(elapsed)}")
        print(f"  Processed: {self.processed_items} items")
        print(f"  Successful: {self.successful_items}")
        print(f"  Failed: {self.failed_items}")
        
        if self.processed_items > 0:
            success_rate = (self.successful_items / self.processed_items) * 100
            print(f"  Success rate: {success_rate:.1f}%")
        
        if self.phase_stats:
            print("\n  Phase breakdown:")
            for phase, stats in self.phase_stats.items():
                phase_time = stats.get('end_time', time.time()) - stats['start_time']
                print(f"    {phase}: {stats['items']} items in {self._format_time(phase_time)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        return {
            'name': self.name,
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'successful_items': self.successful_items,
            'failed_items': self.failed_items,
            'success_rate': (self.successful_items / self.processed_items * 100) 
                          if self.processed_items > 0 else 0,
            'elapsed_time': elapsed,
            'current_phase': self.current_phase,
            'phase_stats': self.phase_stats
        }
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"