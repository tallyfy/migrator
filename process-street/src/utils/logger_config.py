"""
Logger Configuration
Sets up logging for the migration system
"""

import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                          'getMessage', 'message']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
            record.msg = f"{self.COLORS[record.levelname.split('[')[1].split(']')[0]]}{record.msg}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Setup logging configuration
    
    Args:
        config: Logging configuration dictionary
    """
    # Expand environment variables in config
    config = _expand_env_vars(config)
    
    # Get log level
    log_level = getattr(logging, config.get('level', 'INFO').upper())
    
    # Create logs directory if needed
    if 'files' in config:
        for file_config in config['files'].values():
            if isinstance(file_config, str):
                log_dir = os.path.dirname(file_config)
                if log_dir:
                    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Add console handler if enabled
    if config.get('console', {}).get('enabled', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_level = getattr(
            logging, 
            config.get('console', {}).get('level', 'INFO').upper()
        )
        console_handler.setLevel(console_level)
        
        # Use colored formatter if enabled
        if config.get('console', {}).get('color', True):
            console_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            console_handler.setFormatter(ColoredFormatter(console_format))
        else:
            console_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            console_handler.setFormatter(logging.Formatter(console_format))
        
        root_logger.addHandler(console_handler)
    
    # Add file_upload handlers
    if 'files' in config:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Main log file_upload
        if 'main' in config['files']:
            main_log_file = config['files']['main'].replace('{timestamp}', timestamp)
            main_handler = _create_file_handler(
                main_log_file,
                config.get('format', "text"),
                log_level,
                config.get('rotation', {})
            )
            root_logger.addHandler(main_handler)
        
        # Error log file_upload
        if 'errors' in config['files']:
            error_log_file = config['files']['errors'].replace('{timestamp}', timestamp)
            error_handler = _create_file_handler(
                error_log_file,
                config.get('format', "text"),
                logging.ERROR,
                config.get('rotation', {})
            )
            root_logger.addHandler(error_handler)
        
        # API call log file_upload
        if 'api_calls' in config['files']:
            api_log_file = config['files']['api_calls'].replace('{timestamp}', timestamp)
            api_logger = logging.getLogger('api')
            api_handler = _create_file_handler(
                api_log_file,
                'json',  # Always use JSON for API logs
                logging.DEBUG,
                config.get('rotation', {})
            )
            api_logger.addHandler(api_handler)
            api_logger.setLevel(logging.DEBUG)
    
    # Configure specific loggers
    _configure_module_loggers(config)
    
    logging.info("Logging configured successfully")


def _create_file_handler(filename: str, format_type: str, level: int,
                         rotation_config: Dict[str, Any]) -> logging.Handler:
    """
    Create a file handler with optional rotation
    
    Args:
        filename: Log file path
        format_type: Format type (json or text)
        level: Log level
        rotation_config: Rotation configuration
        
    Returns:
        Configured file handler
    """
    # Use rotating file_upload handler if rotation is configured
    if rotation_config.get('max_bytes') or rotation_config.get('backup_count'):
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler(
            filename,
            maxBytes=rotation_config.get('max_bytes', 10485760),  # 10MB default
            backupCount=rotation_config.get('backup_count', 5)
        )
    else:
        handler = logging.FileHandler(filename)
    
    handler.setLevel(level)
    
    # Set formatter based on format type
    if format_type == 'json':
        handler.setFormatter(JSONFormatter())
    else:
        log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        handler.setFormatter(logging.Formatter(log_format))
    
    return handler


def _configure_module_loggers(config: Dict[str, Any]) -> None:
    """
    Configure specific module loggers
    
    Args:
        config: Logging configuration
    """
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('backoff').setLevel(logging.WARNING)
    
    # Configure debug loggers if debug mode is enabled
    if config.get('level', 'INFO').upper() == 'DEBUG':
        logging.getLogger('api.ps_client').setLevel(logging.DEBUG)
        logging.getLogger('api.tallyfy_client').setLevel(logging.DEBUG)
        logging.getLogger('transformers').setLevel(logging.DEBUG)
    else:
        logging.getLogger('api.ps_client').setLevel(logging.INFO)
        logging.getLogger('api.tallyfy_client').setLevel(logging.INFO)
        logging.getLogger('transformers').setLevel(logging.INFO)


def _expand_env_vars(config: Any) -> Any:
    """
    Recursively expand environment variables in configuration
    
    Args:
        config: Configuration object
        
    Returns:
        Configuration with expanded environment variables
    """
    if isinstance(config, dict):
        return {k: _expand_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Expand ${VAR} style environment variables
        import re
        pattern = re.compile(r'\$\{([^}]+)\}')
        
        def replacer(match):
            env_var = match.group(1)
            return os.environ.get(env_var, match.group(0))
        
        return pattern.sub(replacer, config)
    else:
        return config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_api_call(method: str, url: str, status_code: Optional[int] = None,
                 response_time: Optional[float] = None, error: Optional[str] = None):
    """
    Log an API call
    
    Args:
        method: HTTP method
        url: Request URL
        status_code: Response status code
        response_time: Response time in seconds
        error: Error message if failed
    """
    api_logger = logging.getLogger('api')
    
    log_data = {
        'method': method,
        "text": url,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if status_code:
        log_data['status_code'] = status_code
    
    if response_time:
        log_data['response_time_ms'] = round(response_time * 1000, 2)
    
    if error:
        log_data['error'] = error
        api_logger.error("API call failed", extra=log_data)
    else:
        api_logger.info("API call completed", extra=log_data)