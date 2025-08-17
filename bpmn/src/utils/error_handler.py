"""Error handling utilities for BPMN migration"""

import logging
import traceback
from typing import Any, Callable, Optional, Dict
from functools import wraps
import time


class MigrationError(Exception):
    """Base exception for migration errors"""
    pass


class ParseError(MigrationError):
    """Error parsing BPMN files"""
    pass


class TransformationError(MigrationError):
    """Error transforming BPMN to Tallyfy"""
    pass


class APIError(MigrationError):
    """Error communicating with APIs"""
    pass


class ErrorHandler:
    """Handles errors during migration with retry logic"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """Initialize error handler"""
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.errors = []
        self.logger = logging.getLogger(__name__)
    
    def handle_error(self, error: Exception, context: str = "", 
                    recoverable: bool = True) -> bool:
        """
        Handle an error
        
        Returns:
            True if error was handled and operation should continue
            False if error is fatal and operation should stop
        """
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'context': context,
            'traceback': traceback.format_exc(),
            'recoverable': recoverable
        }
        
        self.errors.append(error_info)
        self.logger.error(f"Error in {context}: {error}")
        
        if not recoverable:
            self.logger.error("Fatal error - cannot continue")
            return False
        
        return True
    
    def retry_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Retry an operation with exponential backoff
        
        Args:
            operation: Function to retry
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed")
        
        raise last_exception
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors"""
        return {
            'total_errors': len(self.errors),
            'recoverable_errors': sum(1 for e in self.errors if e['recoverable']),
            'fatal_errors': sum(1 for e in self.errors if not e['recoverable']),
            'error_types': self._count_error_types(),
            'errors': self.errors
        }
    
    def _count_error_types(self) -> Dict[str, int]:
        """Count errors by type"""
        error_types = {}
        for error in self.errors:
            error_type = error['type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        return error_types
    
    def clear_errors(self):
        """Clear all recorded errors"""
        self.errors.clear()
    
    def has_fatal_errors(self) -> bool:
        """Check if there are any fatal errors"""
        return any(not e['recoverable'] for e in self.errors)


def with_error_handling(context: str = "", recoverable: bool = True):
    """
    Decorator for error handling
    
    Args:
        context: Context description for error messages
        recoverable: Whether errors are recoverable
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = ErrorHandler()
                error_context = context or f"{func.__name__}"
                
                if error_handler.handle_error(e, error_context, recoverable):
                    # Return None for recoverable errors
                    return None
                else:
                    # Re-raise for fatal errors
                    raise
        
        return wrapper
    return decorator


def safe_get(dictionary: dict, *keys, default=None):
    """
    Safely get nested dictionary values
    
    Args:
        dictionary: Dictionary to get value from
        *keys: Sequence of keys
        default: Default value if key not found
        
    Returns:
        Value at nested key or default
    """
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default