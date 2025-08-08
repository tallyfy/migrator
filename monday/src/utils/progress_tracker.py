"""Progress tracking for Monday.com migration."""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track migration progress and statistics."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.start_time = time.time()
        self.stats = {
            'users_processed': 0,
            'teams_processed': 0,
            'boards_processed': 0,
            'blueprints_processed': 0,
            'items_processed': 0,
            'processes_processed': 0,
            'comments_processed': 0,
            'files_processed': 0,
            'errors_count': 0,
            'warnings_count': 0
        }
        self.phase_times = {}
        self.current_phase = None
        self.phase_start_time = None
        
        # Rate tracking
        self.rate_window = []  # List of (timestamp, count) tuples
        self.rate_window_size = 60  # 60 seconds
    
    def start_phase(self, phase_name: str):
        """Start tracking a phase.
        
        Args:
            phase_name: Name of the phase
        """
        if self.current_phase:
            self.end_phase()
        
        self.current_phase = phase_name
        self.phase_start_time = time.time()
        logger.info(f"Started phase: {phase_name}")
    
    def end_phase(self):
        """End current phase tracking."""
        if self.current_phase and self.phase_start_time:
            duration = time.time() - self.phase_start_time
            self.phase_times[self.current_phase] = duration
            logger.info(f"Completed phase: {self.current_phase} ({duration:.2f}s)")
            self.current_phase = None
            self.phase_start_time = None
    
    def increment(self, stat_name: str, count: int = 1):
        """Increment a statistic counter.
        
        Args:
            stat_name: Name of the statistic
            count: Amount to increment
        """
        if stat_name in self.stats:
            self.stats[stat_name] += count
            
            # Update rate tracking
            current_time = time.time()
            self.rate_window.append((current_time, count))
            
            # Clean old entries from rate window
            cutoff_time = current_time - self.rate_window_size
            self.rate_window = [(t, c) for t, c in self.rate_window if t > cutoff_time]
    
    def add(self, stat_name: str, value: int):
        """Add to a statistic.
        
        Args:
            stat_name: Name of the statistic
            value: Value to add
        """
        self.increment(stat_name, value)
    
    def update(self, stat_name: str, value: Any):
        """Update a statistic value.
        
        Args:
            stat_name: Name of the statistic
            value: New value
        """
        self.stats[stat_name] = value
    
    def get_rate(self) -> float:
        """Get current processing rate (items per second).
        
        Returns:
            Current rate
        """
        if not self.rate_window:
            return 0.0
        
        total_count = sum(c for _, c in self.rate_window)
        time_span = time.time() - self.rate_window[0][0]
        
        if time_span > 0:
            return total_count / time_span
        return 0.0
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start.
        
        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def get_estimated_remaining(self, total_items: int) -> Optional[float]:
        """Get estimated remaining time.
        
        Args:
            total_items: Total number of items to process
            
        Returns:
            Estimated remaining time in seconds or None
        """
        processed = sum(v for k, v in self.stats.items() if 'processed' in k)
        if processed == 0:
            return None
        
        rate = self.get_rate()
        if rate == 0:
            return None
        
        remaining_items = max(0, total_items - processed)
        return remaining_items / rate
    
    def get_progress_percentage(self, total_items: int) -> float:
        """Get progress percentage.
        
        Args:
            total_items: Total number of items
            
        Returns:
            Progress percentage (0-100)
        """
        if total_items == 0:
            return 100.0
        
        processed = sum(v for k, v in self.stats.items() if 'processed' in k)
        return min(100.0, (processed / total_items) * 100)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics.
        
        Returns:
            Statistics dictionary
        """
        elapsed = self.get_elapsed_time()
        
        return {
            **self.stats,
            'elapsed_time': elapsed,
            'elapsed_formatted': self._format_duration(elapsed),
            'current_rate': self.get_rate(),
            'phase_times': self.phase_times,
            'current_phase': self.current_phase
        }
    
    def get_summary(self, total_items: Optional[int] = None) -> str:
        """Get formatted progress summary.
        
        Args:
            total_items: Optional total items for percentage
            
        Returns:
            Formatted summary string
        """
        stats = self.get_stats()
        elapsed = stats['elapsed_formatted']
        
        lines = [
            f"Migration Progress Summary",
            f"=" * 40,
            f"Elapsed Time: {elapsed}",
            f"Current Rate: {stats['current_rate']:.2f} items/sec"
        ]
        
        if total_items:
            percentage = self.get_progress_percentage(total_items)
            lines.append(f"Progress: {percentage:.1f}%")
            
            remaining = self.get_estimated_remaining(total_items)
            if remaining:
                lines.append(f"Estimated Remaining: {self._format_duration(remaining)}")
        
        lines.append("")
        lines.append("Items Processed:")
        
        for key, value in sorted(stats.items()):
            if key.endswith('_processed') and value > 0:
                item_type = key.replace('_processed', '').replace('_', ' ').title()
                lines.append(f"  {item_type}: {value:,}")
        
        if stats.get('errors_count', 0) > 0:
            lines.append(f"  ⚠️ Errors: {stats['errors_count']}")
        
        if stats.get('warnings_count', 0) > 0:
            lines.append(f"  ⚠️ Warnings: {stats['warnings_count']}")
        
        if self.phase_times:
            lines.append("")
            lines.append("Phase Durations:")
            for phase, duration in self.phase_times.items():
                lines.append(f"  {phase}: {self._format_duration(duration)}")
        
        return "\n".join(lines)
    
    def print_progress(self, message: str = "", total_items: Optional[int] = None):
        """Print progress to console.
        
        Args:
            message: Optional message to display
            total_items: Optional total items for percentage
        """
        if message:
            print(f"\r{message}", end="")
        else:
            processed = sum(v for k, v in self.stats.items() if 'processed' in k)
            rate = self.get_rate()
            
            if total_items:
                percentage = self.get_progress_percentage(total_items)
                print(f"\rProgress: {percentage:.1f}% ({processed}/{total_items}) "
                      f"@ {rate:.2f} items/sec", end="")
            else:
                print(f"\rProcessed: {processed} items @ {rate:.2f} items/sec", end="")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def reset(self):
        """Reset all statistics."""
        self.start_time = time.time()
        for key in self.stats:
            self.stats[key] = 0
        self.phase_times.clear()
        self.current_phase = None
        self.phase_start_time = None
        self.rate_window.clear()
        logger.debug("Progress tracker reset")
    
    def load_state(self, state: Dict[str, Any]):
        """Load state from dictionary.
        
        Args:
            state: State dictionary
        """
        if 'stats' in state:
            self.stats.update(state['stats'])
        if 'phase_times' in state:
            self.phase_times.update(state['phase_times'])
        if 'start_time' in state:
            self.start_time = state['start_time']
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state.
        
        Returns:
            State dictionary
        """
        return {
            'stats': self.stats.copy(),
            'phase_times': self.phase_times.copy(),
            'start_time': self.start_time,
            'current_phase': self.current_phase
        }