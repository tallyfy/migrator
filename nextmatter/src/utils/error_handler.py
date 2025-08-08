"""
Error Handler for RocketLane Migration
Comprehensive error handling and recovery
"""

import logging
import time
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Base exception for migration errors"""
    pass


class APIError(MigrationError):
    """API-related errors"""
    pass


class TransformationError(MigrationError):
    """Data transformation errors"""
    pass


class ValidationError(MigrationError):
    """Validation errors"""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after or 60


class ErrorHandler:
    """Comprehensive error handling for migration"""
    
    def __init__(self):
        """Initialize error handler"""
        self.error_counts = {}
        self.retry_configs = {
            'default': {'max_retries': 3, 'base_delay': 1, 'max_delay': 60},
            'api': {'max_retries': 5, 'base_delay': 2, 'max_delay': 120},
            'rate_limit': {'max_retries': 10, 'base_delay': 60, 'max_delay': 600},
            'transformation': {'max_retries': 2, 'base_delay': 0.5, 'max_delay': 5}
        }
        self.error_log = []
    
    def with_retry(self, error_type: str = 'default'):
        """
        Decorator for automatic retry with exponential backoff
        
        Args:
            error_type: Type of error to handle
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                config = self.retry_configs.get(error_type, self.retry_configs['default'])
                max_retries = config['max_retries']
                base_delay = config['base_delay']
                max_delay = config['max_delay']
                
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    
                    except RateLimitError as e:
                        last_exception = e
                        if attempt < max_retries:
                            # Use retry_after if provided, otherwise exponential backoff
                            delay = e.retry_after or min(base_delay * (2 ** attempt), max_delay)
                            logger.warning(f"Rate limit hit, retrying in {delay} seconds...")
                            time.sleep(delay)
                        else:
                            self._log_error(func.__name__, e, attempt)
                            raise
                    
                    except APIError as e:
                        last_exception = e
                        if attempt < max_retries:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            logger.warning(f"API error on attempt {attempt + 1}, retrying in {delay} seconds: {e}")
                            time.sleep(delay)
                        else:
                            self._log_error(func.__name__, e, attempt)
                            raise
                    
                    except TransformationError as e:
                        last_exception = e
                        if attempt < max_retries and error_type == 'transformation':
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            logger.warning(f"Transformation error, retrying: {e}")
                            time.sleep(delay)
                        else:
                            self._log_error(func.__name__, e, attempt)
                            raise
                    
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries and error_type != 'transformation':
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            logger.warning(f"Unexpected error on attempt {attempt + 1}, retrying: {e}")
                            time.sleep(delay)
                        else:
                            self._log_error(func.__name__, e, attempt)
                            raise
                
                # Should not reach here, but just in case
                if last_exception:
                    raise last_exception
            
            return wrapper
        return decorator
    
    def handle_api_error(self, error: Exception, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle API errors with appropriate recovery strategy
        
        Args:
            error: The exception that occurred
            context: Context about the operation
            
        Returns:
            Recovery action or None
        """
        error_str = str(error)
        error_type = type(error).__name__
        
        # Check for rate limiting
        if 'rate limit' in error_str.lower() or '429' in error_str:
            return self._handle_rate_limit(error, context)
        
        # Check for authentication errors
        if '401' in error_str or 'unauthorized' in error_str.lower():
            return self._handle_auth_error(error, context)
        
        # Check for not found errors
        if '404' in error_str or 'not found' in error_str.lower():
            return self._handle_not_found(error, context)
        
        # Check for server errors
        if '500' in error_str or '502' in error_str or '503' in error_str:
            return self._handle_server_error(error, context)
        
        # Check for timeout
        if 'timeout' in error_str.lower():
            return self._handle_timeout(error, context)
        
        # Log unhandled error
        self._log_error(context.get('operation', 'unknown'), error)
        
        return None
    
    def _handle_rate_limit(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rate limit errors"""
        # Try to extract retry-after header
        retry_after = 60  # Default to 60 seconds
        
        if hasattr(error, 'response'):
            retry_after = int(error.response.headers.get('Retry-After', 60))
        
        logger.warning(f"Rate limit exceeded for {context.get('operation')}. Waiting {retry_after} seconds...")
        
        return {
            'action': 'retry',
            'delay': retry_after,
            'reason': 'rate_limit'
        }
    
    def _handle_auth_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication errors"""
        logger.error(f"Authentication error for {context.get('operation')}: {error}")
        
        return {
            'action': 'abort',
            'reason': 'authentication_failed',
            'message': 'Please check API credentials'
        }
    
    def _handle_not_found(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle not found errors"""
        # Determine if we should skip or abort
        if context.get('optional', False):
            logger.warning(f"Optional resource not found: {context.get('resource_id')}")
            return {
                'action': 'skip',
                'reason': 'resource_not_found'
            }
        else:
            logger.error(f"Required resource not found: {context.get('resource_id')}")
            return {
                'action': 'abort',
                'reason': 'required_resource_not_found'
            }
    
    def _handle_server_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle server errors"""
        logger.warning(f"Server error for {context.get('operation')}: {error}")
        
        return {
            'action': 'retry',
            'delay': 30,
            'reason': 'server_error'
        }
    
    def _handle_timeout(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle timeout errors"""
        logger.warning(f"Timeout for {context.get('operation')}")
        
        return {
            'action': 'retry',
            'delay': 5,
            'reason': 'timeout'
        }
    
    def handle_transformation_error(self, error: Exception, 
                                  item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle transformation errors
        
        Args:
            error: The exception that occurred
            item: The item being transformed
            
        Returns:
            Fallback transformation or None
        """
        logger.error(f"Transformation error for item {item.get('id')}: {error}")
        
        # Try to create minimal valid transformation
        try:
            fallback = self._create_fallback_transformation(item)
            logger.warning(f"Using fallback transformation for item {item.get('id')}")
            return fallback
        except Exception as e:
            logger.error(f"Failed to create fallback transformation: {e}")
            return None
    
    def _create_fallback_transformation(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback transformation for failed item"""
        item_type = item.get('type', 'unknown')
        
        if item_type == 'user':
            return {
                'email': item.get('email', f"user_{item.get('id')}@migrated.local"),
                'name': item.get('name', 'Migrated User'),
                'role': 'member',
                'metadata': {
                    'migration_error': True,
                    'original_id': item.get('id')
                }
            }
        
        elif item_type == 'template':
            return {
                'name': item.get('name', 'Migrated Template'),
                'description': 'Template migrated with errors - manual review required',
                'steps': [{
                    'name': 'Review Migration',
                    'type': 'task',
                    'description': 'This template had errors during migration'
                }],
                'metadata': {
                    'migration_error': True,
                    'original_id': item.get('id')
                }
            }
        
        elif item_type == 'project':
            return {
                'name': item.get('name', 'Migrated Project'),
                'status': 'paused',
                'metadata': {
                    'migration_error': True,
                    'original_id': item.get('id'),
                    'error_reason': 'Transformation failed - manual review required'
                }
            }
        
        else:
            return {
                'name': item.get('name', 'Migrated Item'),
                'type': item_type,
                'metadata': {
                    'migration_error': True,
                    'original_id': item.get('id')
                }
            }
    
    def _log_error(self, operation: str, error: Exception, attempt: int = 0):
        """Log error details"""
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'attempt': attempt
        }
        
        self.error_log.append(error_entry)
        
        # Track error counts
        error_key = f"{operation}:{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered"""
        return {
            'total_errors': len(self.error_log),
            'error_counts': self.error_counts.copy(),
            'recent_errors': self.error_log[-10:]  # Last 10 errors
        }
    
    def should_abort(self, error_threshold: int = 50) -> bool:
        """
        Check if migration should be aborted due to too many errors
        
        Args:
            error_threshold: Maximum number of errors before aborting
            
        Returns:
            True if should abort
        """
        total_errors = sum(self.error_counts.values())
        
        if total_errors >= error_threshold:
            logger.error(f"Error threshold ({error_threshold}) exceeded with {total_errors} errors")
            return True
        
        # Check for critical errors
        critical_errors = ['authentication_failed', 'api_key_invalid', 'permission_denied']
        for error_type in critical_errors:
            if any(error_type in key for key in self.error_counts.keys()):
                logger.error(f"Critical error encountered: {error_type}")
                return True
        
        return False
    
    def save_error_log(self, path: str):
        """Save error log to file"""
        with open(path, 'w') as f:
            json.dump({
                'summary': self.get_error_summary(),
                'full_log': self.error_log
            }, f, indent=2)
        
        logger.info(f"Error log saved to {path}")
    
    def clear_errors(self):
        """Clear error tracking"""
        self.error_counts.clear()
        self.error_log.clear()