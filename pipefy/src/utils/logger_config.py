"""
Logging Configuration for Pipefy Migration
Sets up comprehensive logging for the migration process
"""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import colorlog
import json


def setup_logging(config: Dict[str, Any]):
    """
    Setup logging configuration for migration
    
    Args:
        config: Logging configuration dictionary
    """
    # Get log level from config or environment
    log_level = os.environ.get('LOG_LEVEL', config.get('level', 'INFO')).upper()
    
    # Create logs directory
    log_dir = Path(config.get('directory', 'logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"pipefy_migration_{timestamp}.log"
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console formatter with colors
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s - %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # File handler - detailed logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=config.get('max_size', 10 * 1024 * 1024),  # 10MB
        backupCount=config.get('backup_count', 5)
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler - less verbose
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(console_formatter)
    
    # Error file_upload handler - errors only
    error_file = log_dir / f"pipefy_errors_{timestamp}.log"
    error_handler = logging.FileHandler(error_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # JSON handler for structured logs (if configured)
    json_handler = None
    if config.get('json_logging', False):
        json_file = log_dir / f"pipefy_migration_{timestamp}.json"
        json_handler = JSONLogHandler(json_file)
        json_handler.setLevel(logging.DEBUG)
    
    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)
    if json_handler:
        root_logger.addHandler(json_handler)
    
    # Configure specific loggers
    configure_module_loggers(log_level)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Pipefy to Tallyfy Migration Logging Initialized")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Log File: {log_file}")
    logger.info(f"Error File: {error_file}")
    logger.info("=" * 60)


def configure_module_loggers(default_level: str):
    """
    Configure logging levels for specific modules
    
    Args:
        default_level: Default logging level
    """
    # Quiet down noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('gql').setLevel(logging.WARNING)
    logging.getLogger('graphql').setLevel(logging.WARNING)
    
    # Set specific module levels
    module_levels = {
        'pipefy_client': logging.DEBUG,
        'tallyfy_client': logging.DEBUG,
        'phase_transformer': logging.DEBUG,
        'field_transformer': logging.DEBUG,
        'id_mapper': logging.INFO,
        'validator': logging.INFO,
        'database_migrator': logging.INFO
    }
    
    for module, level in module_levels.items():
        logging.getLogger(module).setLevel(level)


class JSONLogHandler(logging.Handler):
    """Custom handler for JSON structured logging"""
    
    def __init__(self, filename: str):
        """
        Initialize JSON log handler
        
        Args:
            filename: Path to JSON log file
        """
        super().__init__()
        self.filename = filename
        self.file = open(filename, 'a')
    
    def emit(self, record):
        """
        Emit a log record as JSON
        
        Args:
            record: Log record to emit
        """
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'function': record.funcName,
                'line': record.lineno,
                'message': record.getMessage(),
                'module': record.module,
                'process': record.process,
                'thread': record.thread
            }
            
            # Add exception info if present
            if record.exc_info:
                log_entry['exception'] = self.format(record)
            
            # Add extra fields
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 
                              'funcName', 'levelname', 'levelno', 'lineno',
                              'module', 'msecs', 'message', 'pathname', 'process',
                              'processName', 'relativeCreated', 'thread', 'threadName',
                              'exc_info', 'exc_text', 'stack_info']:
                    log_entry[key] = value
            
            self.file.write(json.dumps(log_entry) + '\n')
            self.file.flush()
            
        except Exception:
            self.handleError(record)
    
    def close(self):
        """Close the JSON log file"""
        self.file.close()
        super().close()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_api_call(logger: logging.Logger, method: str, url: str, 
                 response_code: int = None, duration: float = None):
    """
    Log API call details
    
    Args:
        logger: Logger instance
        method: HTTP method
        url: Request URL
        response_code: Response status code
        duration: Call duration in seconds
    """
    extra = {
        'api_method': method,
        'api_url': url,
        'api_response_code': response_code,
        'api_duration': duration
    }
    
    if response_code and response_code >= 400:
        logger.error(f"API call failed: {method} {url} -> {response_code}", extra=extra)
    else:
        logger.debug(f"API call: {method} {url} -> {response_code}", extra=extra)


def log_transformation(logger: logging.Logger, source_type: str, target_type: str,
                      source_id: str = None, target_id: str = None, success: bool = True):
    """
    Log data transformation
    
    Args:
        logger: Logger instance
        source_type: Source object type
        target_type: Target object type
        source_id: Source object ID
        target_id: Target object ID
        success: Whether transformation succeeded
    """
    extra = {
        'transform_source_type': source_type,
        'transform_target_type': target_type,
        'transform_source_id': source_id,
        'transform_target_id': target_id,
        'transform_success': success
    }
    
    if success:
        logger.debug(f"Transformed {source_type} -> {target_type}", extra=extra)
    else:
        logger.error(f"Failed to transform {source_type} -> {target_type}", extra=extra)


def log_phase_transition(logger: logging.Logger, phase: str, status: str, 
                        items_processed: int = 0, duration: float = None):
    """
    Log migration phase transition
    
    Args:
        logger: Logger instance
        phase: Phase name
        status: Phase status (started/completed/failed)
        items_processed: Number of items processed
        duration: Phase duration in seconds
    """
    extra = {
        'phase_name': phase,
        'phase_status': status,
        'phase_items': items_processed,
        'phase_duration': duration
    }
    
    if status == 'started':
        logger.info(f"Phase started: {phase}", extra=extra)
    elif status == 'completed':
        logger.info(f"Phase completed: {phase} ({items_processed} items in {duration:.2f}s)", extra=extra)
    else:
        logger.error(f"Phase failed: {phase}", extra=extra)