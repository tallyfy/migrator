"""Progress tracking for migration operations."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    
try:
    from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track and display migration progress."""
    
    def __init__(self, use_rich: bool = True, disable: bool = False):
        """Initialize progress tracker.
        
        Args:
            use_rich: Use rich library for better display
            disable: Disable progress display
        """
        self.use_rich = use_rich and RICH_AVAILABLE
        self.disable = disable
        self.start_time = None
        self.phase_times = {}
        self.current_phase = None
        self.statistics = {
            'users': {'total': 0, 'processed': 0, 'failed': 0},
            'teams': {'total': 0, 'processed': 0, 'failed': 0},
            'projects': {'total': 0, 'processed': 0, 'failed': 0},
            'tasks': {'total': 0, 'processed': 0, 'failed': 0},
            'attachments': {'total': 0, 'processed': 0, 'failed': 0},
            'comments': {'total': 0, 'processed': 0, 'failed': 0}
        }
        
        if self.use_rich:
            self.console = Console()
            self.progress = Progress(
                TextColumn("[bold blue]{task.fields[phase]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                TextColumn("{task.completed}/{task.total}"),
                "•",
                TimeRemainingColumn(),
                console=self.console,
                disable=disable
            )
            self.tasks = {}
        else:
            self.progress = None
            self.tasks = {}
    
    def start_migration(self) -> None:
        """Start migration tracking."""
        self.start_time = datetime.now()
        if self.use_rich and not self.disable:
            self.progress.start()
        logger.info("Migration started")
    
    def start_phase(self, phase: str, total: int = 100) -> Optional[TaskID]:
        """Start tracking a migration phase.
        
        Args:
            phase: Phase name
            total: Total items to process
            
        Returns:
            Task ID if using rich progress
        """
        self.current_phase = phase
        self.phase_times[phase] = {'start': datetime.now()}
        
        if self.use_rich and not self.disable:
            task_id = self.progress.add_task(
                f"[cyan]{phase}",
                total=total,
                phase=phase
            )
            self.tasks[phase] = task_id
            return task_id
        elif TQDM_AVAILABLE and not self.disable:
            self.tasks[phase] = tqdm(total=total, desc=phase, disable=self.disable)
            return None
        else:
            logger.info(f"Starting phase: {phase} (Total: {total})")
            return None
    
    def update_phase(self, phase: str, advance: int = 1, 
                    description: Optional[str] = None) -> None:
        """Update phase progress.
        
        Args:
            phase: Phase name
            advance: Number of items processed
            description: Optional description update
        """
        if self.use_rich and not self.disable:
            if phase in self.tasks:
                self.progress.update(
                    self.tasks[phase],
                    advance=advance,
                    description=description
                )
        elif TQDM_AVAILABLE and not self.disable:
            if phase in self.tasks:
                self.tasks[phase].update(advance)
                if description:
                    self.tasks[phase].set_description(description)
        else:
            if phase in self.statistics:
                self.statistics[phase]['processed'] += advance
    
    def complete_phase(self, phase: str) -> None:
        """Mark phase as complete.
        
        Args:
            phase: Phase name
        """
        if phase in self.phase_times:
            self.phase_times[phase]['end'] = datetime.now()
            duration = self.phase_times[phase]['end'] - self.phase_times[phase]['start']
            self.phase_times[phase]['duration'] = duration
            
        if self.use_rich and not self.disable:
            if phase in self.tasks:
                self.progress.update(
                    self.tasks[phase],
                    completed=self.progress.tasks[self.tasks[phase]].total
                )
        elif TQDM_AVAILABLE and not self.disable:
            if phase in self.tasks:
                self.tasks[phase].close()
        
        logger.info(f"Completed phase: {phase}")
    
    def record_success(self, entity_type: str, entity_name: str = None) -> None:
        """Record successful migration of an entity.
        
        Args:
            entity_type: Type of entity (users, projects, etc.)
            entity_name: Optional entity name for logging
        """
        if entity_type in self.statistics:
            self.statistics[entity_type]['processed'] += 1
            
        if entity_name:
            logger.debug(f"Successfully migrated {entity_type}: {entity_name}")
    
    def record_failure(self, entity_type: str, entity_name: str = None,
                      error: Exception = None) -> None:
        """Record failed migration of an entity.
        
        Args:
            entity_type: Type of entity
            entity_name: Optional entity name
            error: Exception that caused failure
        """
        if entity_type in self.statistics:
            self.statistics[entity_type]['failed'] += 1
            
        if entity_name:
            logger.error(f"Failed to migrate {entity_type}: {entity_name} - {error}")
    
    def set_total(self, entity_type: str, total: int) -> None:
        """Set total count for entity type.
        
        Args:
            entity_type: Type of entity
            total: Total count
        """
        if entity_type in self.statistics:
            self.statistics[entity_type]['total'] = total
    
    def display_summary(self) -> Dict[str, Any]:
        """Display migration summary.
        
        Returns:
            Summary statistics
        """
        if self.start_time:
            total_duration = datetime.now() - self.start_time
        else:
            total_duration = timedelta(0)
        
        summary = {
            'duration': str(total_duration),
            'statistics': self.statistics,
            'phase_times': {}
        }
        
        # Calculate phase durations
        for phase, times in self.phase_times.items():
            if 'duration' in times:
                summary['phase_times'][phase] = str(times['duration'])
        
        if self.use_rich and not self.disable:
            # Create summary table
            table = Table(title="Migration Summary", show_header=True)
            table.add_column("Entity", style="cyan", no_wrap=True)
            table.add_column("Total", style="magenta")
            table.add_column("Processed", style="green")
            table.add_column("Failed", style="red")
            table.add_column("Success Rate", justify="right")
            
            for entity_type, stats in self.statistics.items():
                if stats['total'] > 0:
                    success_rate = (stats['processed'] / stats['total']) * 100
                    table.add_row(
                        entity_type.title(),
                        str(stats['total']),
                        str(stats['processed']),
                        str(stats['failed']),
                        f"{success_rate:.1f}%"
                    )
            
            self.console.print(table)
            self.console.print(f"\n[bold]Total Duration:[/bold] {total_duration}")
            
            # Phase timing table
            if self.phase_times:
                phase_table = Table(title="Phase Durations", show_header=True)
                phase_table.add_column("Phase", style="cyan")
                phase_table.add_column("Duration", style="yellow")
                
                for phase, duration in summary['phase_times'].items():
                    phase_table.add_row(phase, duration)
                
                self.console.print(phase_table)
        else:
            # Simple short_text output
            print("\n" + "="*50)
            print("MIGRATION SUMMARY")
            print("="*50)
            
            for entity_type, stats in self.statistics.items():
                if stats['total'] > 0:
                    success_rate = (stats['processed'] / stats['total']) * 100
                    print(f"{entity_type.title()}:")
                    print(f"  Total: {stats['total']}")
                    print(f"  Processed: {stats['processed']}")
                    print(f"  Failed: {stats['failed']}")
                    print(f"  Success Rate: {success_rate:.1f}%")
            
            print(f"\nTotal Duration: {total_duration}")
            
            if self.phase_times:
                print("\nPhase Durations:")
                for phase, duration in summary['phase_times'].items():
                    print(f"  {phase}: {duration}")
        
        return summary
    
    def stop(self) -> None:
        """Stop progress tracking."""
        if self.use_rich and not self.disable:
            self.progress.stop()
        
        # Close any open tqdm bars
        if TQDM_AVAILABLE:
            for phase, bar in self.tasks.items():
                if hasattr(bar, 'close'):
                    bar.close()