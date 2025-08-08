"""
Logger Configuration for RocketLane Migration
Sets up comprehensive logging for the migration process
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import sys


def setup_logging(log_level: str = None, log_file: str = None):
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Get configuration from environment or defaults
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    log_file = log_file or os.getenv('LOG_FILE', 'logs/migration.log')
    
    # Create logs directory if it doesn't exist
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (detailed format)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Create separate error log
    error_log_file = log_file.replace('.log', '_errors.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    configure_module_loggers()
    
    # Log initial setup
    root_logger.info("=" * 60)
    root_logger.info(f"RocketLane to Tallyfy Migration Started")
    root_logger.info(f"Log Level: {log_level}")
    root_logger.info(f"Log File: {log_file}")
    root_logger.info("=" * 60)


def configure_module_loggers():
    """Configure specific module loggers"""
    
    # Reduce verbosity of external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    
    # Set specific levels for migration modules
    module_configs = {
        'api.rocketlane_client': logging.DEBUG,
        'api.tallyfy_client': logging.DEBUG,
        'api.ai_client': logging.INFO,
        'transformers.field_transformer': logging.INFO,
        'transformers.template_transformer': logging.INFO,
        'transformers.instance_transformer': logging.INFO,
        'transformers.user_transformer': logging.INFO,
        'utils.checkpoint_manager': logging.INFO,
        'utils.validator': logging.INFO,
        'utils.error_handler': logging.DEBUG
    }
    
    for module_name, level in module_configs.items():
        logger = logging.getLogger(module_name)
        logger.setLevel(level)


class MigrationLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds migration context to log messages
    """
    
    def __init__(self, logger, migration_id: str):
        """
        Initialize adapter with migration context
        
        Args:
            logger: Base logger
            migration_id: Migration ID to include in logs
        """
        super().__init__(logger, {'migration_id': migration_id})
    
    def process(self, msg, kwargs):
        """Add migration ID to log messages"""
        return f"[{self.extra['migration_id']}] {msg}", kwargs


class ProgressLogger:
    """
    Specialized logger for tracking migration progress
    """
    
    def __init__(self, total_items: int, phase: str):
        """
        Initialize progress logger
        
        Args:
            total_items: Total number of items to process
            phase: Current migration phase
        """
        self.logger = logging.getLogger(__name__)
        self.total_items = total_items
        self.phase = phase
        self.processed = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.last_log_time = self.start_time
        self.log_interval = 10  # Log every 10 items or 30 seconds
    
    def update(self, processed: int = None, error: bool = False):
        """
        Update progress
        
        Args:
            processed: Number of items processed (increments if None)
            error: Whether this was an error
        """
        if processed is not None:
            self.processed = processed
        else:
            self.processed += 1
        
        if error:
            self.errors += 1
        
        # Check if we should log
        current_time = datetime.now()
        time_elapsed = (current_time - self.last_log_time).total_seconds()
        
        should_log = (
            self.processed % self.log_interval == 0 or
            time_elapsed >= 30 or
            self.processed == self.total_items
        )
        
        if should_log:
            self._log_progress()
            self.last_log_time = current_time
    
    def _log_progress(self):
        """Log current progress"""
        if self.total_items > 0:
            percentage = (self.processed / self.total_items) * 100
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            if self.processed > 0:
                rate = self.processed / elapsed
                eta_seconds = (self.total_items - self.processed) / rate if rate > 0 else 0
                eta = format_duration(eta_seconds)
            else:
                eta = "calculating..."
            
            self.logger.info(
                f"[{self.phase}] Progress: {self.processed}/{self.total_items} "
                f"({percentage:.1f}%) - Errors: {self.errors} - ETA: {eta}"
            )
    
    def complete(self):
        """Log completion"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.processed / elapsed if elapsed > 0 else 0
        
        self.logger.info(
            f"[{self.phase}] Completed: {self.processed}/{self.total_items} items "
            f"in {format_duration(elapsed)} ({rate:.1f} items/sec) - "
            f"Errors: {self.errors}"
        )


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


class APICallLogger:
    """
    Logger for tracking API calls and rate limits
    """
    
    def __init__(self, api_name: str):
        """
        Initialize API call logger
        
        Args:
            api_name: Name of the API (rocketlane or tallyfy)
        """
        self.logger = logging.getLogger(f"api.{api_name}")
        self.api_name = api_name
        self.call_count = 0
        self.error_count = 0
        self.rate_limit_hits = 0
        self.start_time = datetime.now()
    
    def log_request(self, method: str, endpoint: str, params: dict = None):
        """Log API request"""
        self.call_count += 1
        self.logger.debug(f"{method} {endpoint} - Params: {params}")
    
    def log_response(self, status_code: int, response_time: float):
        """Log API response"""
        self.logger.debug(f"Response: {status_code} - Time: {response_time:.2f}s")
        
        if status_code == 429:
            self.rate_limit_hits += 1
            self.logger.warning(f"Rate limit hit ({self.rate_limit_hits} total)")
        elif status_code >= 400:
            self.error_count += 1
    
    def get_stats(self) -> dict:
        """Get API call statistics"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'api': self.api_name,
            'total_calls': self.call_count,
            'errors': self.error_count,
            'rate_limit_hits': self.rate_limit_hits,
            'calls_per_minute': (self.call_count / elapsed) * 60 if elapsed > 0 else 0
        }