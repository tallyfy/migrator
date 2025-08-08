"""Track migration progress and provide estimates."""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and report migration progress."""
    
    def __init__(self, total_items: Optional[int] = None):
        """Initialize progress tracker.
        
        Args:
            total_items: Total number of items to process
        """
        self.total_items = total_items
        self.processed_items = 0
        self.failed_items = 0
        self.start_time = None
        self.phase_times = {}
        self.current_phase = None
        self.phase_start_time = None
        
        # For rate calculation
        self.recent_items = deque(maxlen=100)  # Track last 100 items
        self.recent_times = deque(maxlen=100)
        
        # Phase statistics
        self.phase_stats = {}
    
    def start(self, total_items: Optional[int] = None):
        """Start tracking progress.
        
        Args:
            total_items: Optional total items to process
        """
        if total_items:
            self.total_items = total_items
        self.start_time = time.time()
        self.processed_items = 0
        self.failed_items = 0
        logger.info(f"Progress tracking started. Total items: {self.total_items or 'Unknown'}")
    
    def start_phase(self, phase_name: str, total_items: Optional[int] = None):
        """Start tracking a new phase.
        
        Args:
            phase_name: Name of the phase
            total_items: Optional items in this phase
        """
        # End previous phase if exists
        if self.current_phase:
            self.end_phase()
        
        self.current_phase = phase_name
        self.phase_start_time = time.time()
        
        if phase_name not in self.phase_stats:
            self.phase_stats[phase_name] = {
                'total_items': total_items or 0,
                'processed': 0,
                'failed': 0,
                'start_time': self.phase_start_time,
                'end_time': None,
                'duration': None
            }
        
        logger.info(f"Started phase: {phase_name}")
    
    def end_phase(self):
        """End current phase and record statistics."""
        if not self.current_phase:
            return
        
        end_time = time.time()
        duration = end_time - self.phase_start_time
        
        self.phase_stats[self.current_phase]['end_time'] = end_time
        self.phase_stats[self.current_phase]['duration'] = duration
        
        phase_name = self.current_phase
        stats = self.phase_stats[phase_name]
        
        logger.info(f"Completed phase: {phase_name}")
        logger.info(f"  Duration: {self.format_duration(duration)}")
        logger.info(f"  Processed: {stats['processed']}/{stats['total_items']}")
        if stats['failed'] > 0:
            logger.warning(f"  Failed: {stats['failed']}")
        
        self.current_phase = None
        self.phase_start_time = None
    
    def update(self, items_processed: int = 1, failed: bool = False):
        """Update progress.
        
        Args:
            items_processed: Number of items processed
            failed: Whether the items failed
        """
        current_time = time.time()
        
        self.processed_items += items_processed
        if failed:
            self.failed_items += items_processed
        
        # Update phase statistics
        if self.current_phase and self.current_phase in self.phase_stats:
            self.phase_stats[self.current_phase]['processed'] += items_processed
            if failed:
                self.phase_stats[self.current_phase]['failed'] += items_processed
        
        # Track for rate calculation
        self.recent_items.append(items_processed)
        self.recent_times.append(current_time)
        
        # Log progress periodically
        if self.processed_items % 10 == 0:
            self.log_progress()
    
    def log_progress(self):
        """Log current progress."""
        if not self.start_time:
            return
        
        elapsed_time = time.time() - self.start_time
        
        # Calculate completion percentage
        if self.total_items and self.total_items > 0:
            percentage = (self.processed_items / self.total_items) * 100
            remaining = self.total_items - self.processed_items
            
            # Calculate ETA
            if self.processed_items > 0:
                rate = self.processed_items / elapsed_time
                eta_seconds = remaining / rate if rate > 0 else 0
                eta = self.format_duration(eta_seconds)
            else:
                eta = "Unknown"
            
            logger.info(
                f"Progress: {self.processed_items}/{self.total_items} "
                f"({percentage:.1f}%) - ETA: {eta}"
            )
        else:
            logger.info(f"Progress: {self.processed_items} items processed")
        
        # Show current rate
        rate = self.get_current_rate()
        if rate:
            logger.info(f"  Current rate: {rate:.1f} items/second")
        
        # Show failure rate if any
        if self.failed_items > 0:
            failure_rate = (self.failed_items / self.processed_items) * 100
            logger.warning(f"  Failure rate: {failure_rate:.1f}% ({self.failed_items} failed)")
    
    def get_current_rate(self) -> Optional[float]:
        """Calculate current processing rate.
        
        Returns:
            Items per second or None
        """
        if len(self.recent_times) < 2:
            return None
        
        time_span = self.recent_times[-1] - self.recent_times[0]
        if time_span <= 0:
            return None
        
        total_items = sum(self.recent_items)
        return total_items / time_span
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.start_time:
            return {}
        
        elapsed_time = time.time() - self.start_time
        
        stats = {
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'failed_items': self.failed_items,
            'success_rate': ((self.processed_items - self.failed_items) / self.processed_items * 100) 
                          if self.processed_items > 0 else 0,
            'elapsed_time': elapsed_time,
            'elapsed_time_formatted': self.format_duration(elapsed_time),
            'average_rate': self.processed_items / elapsed_time if elapsed_time > 0 else 0,
            'current_rate': self.get_current_rate(),
            'phases': self.phase_stats
        }
        
        # Calculate ETA if possible
        if self.total_items and self.processed_items > 0:
            remaining = self.total_items - self.processed_items
            rate = self.processed_items / elapsed_time
            if rate > 0:
                eta_seconds = remaining / rate
                stats['eta_seconds'] = eta_seconds
                stats['eta_formatted'] = self.format_duration(eta_seconds)
                stats['completion_percentage'] = (self.processed_items / self.total_items) * 100
        
        return stats
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
        else:
            days = seconds / 86400
            return f"{days:.1f} days"
    
    def print_summary(self):
        """Print a summary of the progress."""
        stats = self.get_statistics()
        
        print("\n" + "=" * 60)
        print("PROGRESS SUMMARY")
        print("=" * 60)
        
        print(f"Total Items: {stats.get('total_items', 'Unknown')}")
        print(f"Processed: {stats['processed_items']}")
        print(f"Failed: {stats['failed_items']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Elapsed Time: {stats['elapsed_time_formatted']}")
        
        if stats.get('average_rate'):
            print(f"Average Rate: {stats['average_rate']:.1f} items/second")
        
        if stats.get('current_rate'):
            print(f"Current Rate: {stats['current_rate']:.1f} items/second")
        
        if stats.get('eta_formatted'):
            print(f"ETA: {stats['eta_formatted']}")
            print(f"Completion: {stats['completion_percentage']:.1f}%")
        
        # Print phase statistics
        if self.phase_stats:
            print("\nPhase Statistics:")
            print("-" * 40)
            for phase_name, phase_stats in self.phase_stats.items():
                print(f"\n{phase_name}:")
                print(f"  Processed: {phase_stats['processed']}/{phase_stats['total_items']}")
                if phase_stats['failed'] > 0:
                    print(f"  Failed: {phase_stats['failed']}")
                if phase_stats['duration']:
                    print(f"  Duration: {self.format_duration(phase_stats['duration'])}")
        
        print("=" * 60)
    
    def reset(self):
        """Reset the progress tracker."""
        self.total_items = None
        self.processed_items = 0
        self.failed_items = 0
        self.start_time = None
        self.phase_times = {}
        self.current_phase = None
        self.phase_start_time = None
        self.recent_items.clear()
        self.recent_times.clear()
        self.phase_stats = {}
        logger.debug("Progress tracker reset")