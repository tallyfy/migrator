"""
Progress Tracking for Pipefy Migration
Provides visual progress indicators and statistics
"""

import time
import logging
from typing import Iterator, Any, Optional
from datetime import datetime, timedelta
from tqdm import tqdm
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and displays migration progress"""
    
    def __init__(self):
        """Initialize progress tracker"""
        self.console = Console()
        self.start_time = datetime.now()
        self.stats = {
            'items_processed': 0,
            'items_failed': 0,
            'current_phase': None,
            'phases_completed': [],
            'rate_per_minute': 0
        }
    
    def track(self, items: Iterator, description: str = "Processing", 
             total: Optional[int] = None) -> Iterator:
        """
        Track progress of items being processed
        
        Args:
            items: Iterator of items to process
            description: Description of what's being processed
            total: Total number of items (if known)
            
        Yields:
            Items from the iterator
        """
        # Convert to list if we need to count
        if total is None:
            items_list = list(items)
            total = len(items_list)
            items = iter(items_list)
        
        # Create progress bar
        with tqdm(total=total, desc=description, unit="items") as pbar:
            for item in items:
                try:
                    yield item
                    self.stats['items_processed'] += 1
                    pbar.update(1)
                    
                    # Update rate
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    if elapsed > 0:
                        self.stats['rate_per_minute'] = (
                            self.stats['items_processed'] / elapsed * 60
                        )
                except Exception as e:
                    self.stats['items_failed'] += 1
                    logger.error(f"Error processing item: {e}")
                    raise
    
    def start_phase(self, phase_name: str):
        """
        Mark the start of a migration phase
        
        Args:
            phase_name: Name of the phase
        """
        self.stats['current_phase'] = phase_name
        self.console.print(f"\n[bold blue]Starting phase: {phase_name}[/bold blue]")
        logger.info(f"Starting phase: {phase_name}")
    
    def complete_phase(self, phase_name: str, stats: Optional[dict] = None):
        """
        Mark the completion of a migration phase
        
        Args:
            phase_name: Name of the phase
            stats: Optional statistics for the phase
        """
        self.stats['phases_completed'].append(phase_name)
        self.stats['current_phase'] = None
        
        if stats:
            self.console.print(f"[bold green]✓ Phase {phase_name} completed[/bold green]")
            self._display_phase_stats(stats)
        else:
            self.console.print(f"[bold green]✓ Phase {phase_name} completed[/bold green]")
        
        logger.info(f"Completed phase: {phase_name}")
    
    def _display_phase_stats(self, stats: dict):
        """Display statistics for a completed phase"""
        table = Table(title="Phase Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in stats.items():
            table.add_row(str(key).replace('_', ' ').title(), str(value))
        
        self.console.print(table)
    
    def show_progress_spinner(self, message: str):
        """
        Show a spinner for long-running operations
        
        Args:
            message: Message to display
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(description=message, total=None)
            while not progress.finished:
                time.sleep(0.1)
    
    def display_summary(self):
        """Display overall migration summary"""
        elapsed = datetime.now() - self.start_time
        
        summary_table = Table(title="Migration Summary", show_header=True)
        summary_table.add_column("Metric", style="cyan", width=30)
        summary_table.add_column("Value", style="green", width=20)
        
        summary_table.add_row("Total Items Processed", str(self.stats['items_processed']))
        summary_table.add_row("Failed Items", str(self.stats['items_failed']))
        summary_table.add_row("Success Rate", 
                             f"{(1 - self.stats['items_failed']/max(self.stats['items_processed'], 1)) * 100:.1f}%")
        summary_table.add_row("Phases Completed", str(len(self.stats['phases_completed'])))
        summary_table.add_row("Processing Rate", f"{self.stats['rate_per_minute']:.1f} items/min")
        summary_table.add_row("Total Time", str(elapsed).split('.')[0])
        
        self.console.print("\n")
        self.console.print(summary_table)
    
    def log_warning(self, message: str):
        """
        Log and display a warning message
        
        Args:
            message: Warning message
        """
        self.console.print(f"[yellow]⚠ {message}[/yellow]")
        logger.warning(message)
    
    def log_error(self, message: str):
        """
        Log and display an error message
        
        Args:
            message: Error message
        """
        self.console.print(f"[red]✗ {message}[/red]")
        logger.error(message)
    
    def log_success(self, message: str):
        """
        Log and display a success message
        
        Args:
            message: Success message
        """
        self.console.print(f"[green]✓ {message}[/green]")
        logger.info(message)
    
    def log_info(self, message: str):
        """
        Log and display an info message
        
        Args:
            message: Info message
        """
        self.console.print(f"[blue]ℹ {message}[/blue]")
        logger.info(message)
    
    def get_elapsed_time(self) -> timedelta:
        """
        Get elapsed time since tracking started
        
        Returns:
            Elapsed time as timedelta
        """
        return datetime.now() - self.start_time
    
    def estimate_remaining_time(self, items_remaining: int) -> Optional[timedelta]:
        """
        Estimate remaining time based on current rate
        
        Args:
            items_remaining: Number of items remaining
            
        Returns:
            Estimated time remaining or None if cannot estimate
        """
        if self.stats['rate_per_minute'] > 0:
            minutes_remaining = items_remaining / self.stats['rate_per_minute']
            return timedelta(minutes=minutes_remaining)
        return None