"""
Progress Tracker
Provides progress tracking and reporting for migration operations
"""

import sys
import time
import logging
from typing import Iterator, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and display migration progress"""
    
    def __init__(self, show_progress: bool = True, update_interval: float = 1.0):
        """
        Initialize progress tracker
        
        Args:
            show_progress: Whether to show progress bars
            update_interval: Update interval in seconds
        """
        self.show_progress = show_progress
        self.update_interval = update_interval
        self.start_time = None
        self.current_phase = None
        self.phase_stats = {}
    
    def track(self, items: list, description: str = "Processing", 
             show_item: bool = False) -> Iterator[Any]:
        """
        Track progress through a list of items
        
        Args:
            items: List of items to process
            description: Description of the operation
            show_item: Whether to show current item being processed
            
        Yields:
            Items from the input list
        """
        total = len(items)
        
        if total == 0:
            return
        
        self.start_time = time.time()
        last_update = 0
        
        for i, item in enumerate(items, 1):
            yield item
            
            if self.show_progress:
                current_time = time.time()
                if current_time - last_update >= self.update_interval:
                    self._update_progress(i, total, description, item if show_item else None)
                    last_update = current_time
        
        # Final update
        if self.show_progress:
            self._update_progress(total, total, description, None)
            print()  # New line after progress bar
    
    def _update_progress(self, current: int, total: int, description: str, 
                        current_item: Optional[Any] = None):
        """
        Update progress display
        
        Args:
            current: Current item number
            total: Total items
            description: Operation description
            current_item: Current item being processed
        """
        percent = (current / total) * 100
        bar_length = 40
        filled_length = int(bar_length * current // total)
        
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if current > 0:
            rate = current / elapsed
            remaining = (total - current) / rate if rate > 0 else 0
            eta = self._format_time(remaining)
        else:
            eta = "calculating..."
        
        # Build status line
        status = f"\r{description}: [{bar}] {percent:.1f}% ({current}/{total})"
        
        if current_item:
            item_str = str(current_item)
            if len(item_str) > 30:
                item_str = item_str[:27] + "..."
            status += f" - {item_str}"
        
        status += f" - ETA: {eta}"
        
        # Print status
        sys.stdout.write(status)
        sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time in seconds to human-readable string
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def start_phase(self, phase_name: str, total_items: Optional[int] = None):
        """
        Start tracking a new phase
        
        Args:
            phase_name: Name of the phase
            total_items: Total items in this phase (optional)
        """
        self.current_phase = phase_name
        self.phase_stats[phase_name] = {
            'start_time': time.time(),
            'total_items': total_items,
            'processed_items': 0,
            'successful_items': 0,
            'failed_items': 0,
            'warnings': []
        }
        
        logger.info(f"Starting phase: {phase_name}")
        if total_items:
            logger.info(f"Total items to process: {total_items}")
    
    def update_phase(self, processed: int = 0, successful: int = 0, 
                    failed: int = 0, warning: Optional[str] = None):
        """
        Update current phase statistics
        
        Args:
            processed: Number of items processed
            successful: Number of successful items
            failed: Number of failed items
            warning: Optional warning message
        """
        if not self.current_phase or self.current_phase not in self.phase_stats:
            return
        
        stats = self.phase_stats[self.current_phase]
        stats['processed_items'] += processed
        stats['successful_items'] += successful
        stats['failed_items'] += failed
        
        if warning:
            stats['warnings'].append({
                'message': warning,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    def end_phase(self, phase_name: Optional[str] = None):
        """
        End tracking for a phase
        
        Args:
            phase_name: Name of the phase (uses current if not specified)
        """
        phase = phase_name or self.current_phase
        
        if not phase or phase not in self.phase_stats:
            return
        
        stats = self.phase_stats[phase]
        stats['end_time'] = time.time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        # Log phase summary
        logger.info(f"Phase '{phase}' completed:")
        logger.info(f"  Duration: {self._format_time(stats['duration'])}")
        logger.info(f"  Processed: {stats['processed_items']}")
        logger.info(f"  Successful: {stats['successful_items']}")
        logger.info(f"  Failed: {stats['failed_items']}")
        
        if stats['warnings']:
            logger.warning(f"  Warnings: {len(stats['warnings'])}")
        
        self.current_phase = None
    
    def get_phase_statistics(self, phase_name: Optional[str] = None) -> dict:
        """
        Get statistics for a phase
        
        Args:
            phase_name: Phase name (None for all phases)
            
        Returns:
            Phase statistics
        """
        if phase_name:
            return self.phase_stats.get(phase_name, {})
        return self.phase_stats.copy()
    
    def estimate_completion(self, current: int, total: int) -> Optional[datetime]:
        """
        Estimate completion time based on current progress
        
        Args:
            current: Current item count
            total: Total item count
            
        Returns:
            Estimated completion datetime
        """
        if not self.start_time or current == 0:
            return None
        
        elapsed = time.time() - self.start_time
        rate = current / elapsed
        
        if rate > 0:
            remaining = (total - current) / rate
            return datetime.utcnow() + timedelta(seconds=remaining)
        
        return None
    
    def log_progress(self, message: str, level: str = "info"):
        """
        Log a progress message
        
        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        if level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(message)
        
        # Also update current phase if applicable
        if self.current_phase and level in ["warning", "error"]:
            self.update_phase(warning=message)
    
    def create_summary_report(self) -> dict:
        """
        Create a summary report of all phases
        
        Returns:
            Summary report dictionary
        """
        report = {
            'phases': {},
            'totals': {
                'duration': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        
        for phase_name, stats in self.phase_stats.items():
            # Calculate success rate
            if stats['processed_items'] > 0:
                success_rate = (stats['successful_items'] / stats['processed_items']) * 100
            else:
                success_rate = 0
            
            report['phases'][phase_name] = {
                'duration': self._format_time(stats.get('duration', 0)),
                'processed': stats['processed_items'],
                'successful': stats['successful_items'],
                'failed': stats['failed_items'],
                'success_rate': f"{success_rate:.1f}%",
                'warnings': len(stats['warnings'])
            }
            
            # Update totals
            report['totals']['duration'] += stats.get('duration', 0)
            report['totals']['processed'] += stats['processed_items']
            report['totals']['successful'] += stats['successful_items']
            report['totals']['failed'] += stats['failed_items']
            report['totals']['warnings'] += len(stats['warnings'])
        
        # Format total duration
        report['totals']['duration'] = self._format_time(report['totals']['duration'])
        
        # Calculate overall success rate
        if report['totals']['processed'] > 0:
            report['totals']['success_rate'] = (
                f"{(report['totals']['successful'] / report['totals']['processed']) * 100:.1f}%"
            )
        else:
            report['totals']['success_rate'] = "0%"
        
        return report