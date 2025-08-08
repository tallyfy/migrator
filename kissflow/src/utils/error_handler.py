"""Handle and track migration errors."""

import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handle migration errors with recovery strategies."""
    
    def __init__(self, max_retries: int = 3):
        """Initialize error handler.
        
        Args:
            max_retries: Maximum retry attempts for recoverable errors
        """
        self.max_retries = max_retries
        self.errors = []
        self.retry_counts = {}
        self.critical_errors = []
        self.recoverable_errors = []
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                    recoverable: bool = True) -> bool:
        """Handle an error with appropriate strategy.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            recoverable: Whether the error is recoverable
            
        Returns:
            True if error was handled and operation can retry
        """
        error_info = self._create_error_info(error, context)
        self.errors.append(error_info)
        
        # Log the error
        logger.error(f"Error occurred: {error_info['message']}")
        if context:
            logger.error(f"Context: {json.dumps(context, default=str)}")
        
        if not recoverable:
            self.critical_errors.append(error_info)
            return False
        
        # Check if we should retry
        error_key = self._get_error_key(error, context)
        self.retry_counts[error_key] = self.retry_counts.get(error_key, 0) + 1
        
        if self.retry_counts[error_key] <= self.max_retries:
            self.recoverable_errors.append(error_info)
            logger.info(f"Retry attempt {self.retry_counts[error_key]}/{self.max_retries} for error: {error_key}")
            return True
        else:
            logger.error(f"Max retries exceeded for error: {error_key}")
            self.critical_errors.append(error_info)
            return False
    
    def handle_critical_error(self, error: Exception, 
                            context: Optional[Dict[str, Any]] = None):
        """Handle a critical error that stops migration.
        
        Args:
            error: The critical exception
            context: Additional context
        """
        error_info = self._create_error_info(error, context, critical=True)
        self.critical_errors.append(error_info)
        
        logger.critical(f"CRITICAL ERROR: {error_info['message']}")
        logger.critical(f"Stack trace:\n{error_info['stack_trace']}")
        
        # Save error report
        self._save_error_report(error_info)
    
    def classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate handling.
        
        Args:
            error: The exception to classify
            
        Returns:
            Error classification
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Rate limit errors
        if 'rate limit' in error_msg or 'too many requests' in error_msg:
            return 'rate_limit'
        
        # Authentication errors
        if 'unauthorized' in error_msg or 'authentication' in error_msg:
            return 'authentication'
        
        # Network errors
        if 'connection' in error_msg or 'timeout' in error_msg:
            return 'network'
        
        # Data validation errors
        if 'validation' in error_msg or 'invalid' in error_msg:
            return 'validation'
        
        # Permission errors
        if 'permission' in error_msg or 'forbidden' in error_msg:
            return 'permission'
        
        # API errors
        if error_type in ['HTTPError', 'RequestException']:
            return 'api_error'
        
        # Default
        return 'unknown'
    
    def get_recovery_strategy(self, error: Exception) -> Dict[str, Any]:
        """Determine recovery strategy for an error.
        
        Args:
            error: The exception
            
        Returns:
            Recovery strategy dictionary
        """
        error_class = self.classify_error(error)
        
        strategies = {
            'rate_limit': {
                'action': 'wait_and_retry',
                'wait_time': 3600,  # Wait 1 hour
                'message': 'Rate limit hit, waiting before retry'
            },
            'authentication': {
                'action': 'fail',
                'message': 'Authentication failed, check credentials'
            },
            'network': {
                'action': 'retry_with_backoff',
                'initial_wait': 5,
                'max_wait': 60,
                'message': 'Network error, retrying with backoff'
            },
            'validation': {
                'action': 'skip_and_log',
                'message': 'Validation error, skipping item'
            },
            'permission': {
                'action': 'fail',
                'message': 'Permission denied, check access rights'
            },
            'api_error': {
                'action': 'retry',
                'message': 'API error, retrying'
            },
            'unknown': {
                'action': 'log_and_continue',
                'message': 'Unknown error, logging and continuing'
            }
        }
        
        return strategies.get(error_class, strategies['unknown'])
    
    def _create_error_info(self, error: Exception,
                         context: Optional[Dict[str, Any]] = None,
                         critical: bool = False) -> Dict[str, Any]:
        """Create detailed error information.
        
        Args:
            error: The exception
            context: Additional context
            critical: Whether this is a critical error
            
        Returns:
            Error information dictionary
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'type': type(error).__name__,
            'message': str(error),
            'classification': self.classify_error(error),
            'critical': critical,
            'context': context or {},
            'stack_trace': traceback.format_exc()
        }
    
    def _get_error_key(self, error: Exception,
                      context: Optional[Dict[str, Any]] = None) -> str:
        """Generate unique key for error tracking.
        
        Args:
            error: The exception
            context: Additional context
            
        Returns:
            Error key string
        """
        error_type = type(error).__name__
        
        # Include context in key if available
        if context:
            if 'object_type' in context:
                return f"{error_type}_{context['object_type']}"
            elif 'phase' in context:
                return f"{error_type}_{context['phase']}"
        
        return error_type
    
    def _save_error_report(self, error_info: Dict[str, Any]):
        """Save error report to file.
        
        Args:
            error_info: Error information to save
        """
        filename = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(error_info, f, indent=2, default=str)
            logger.info(f"Error report saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save error report: {e}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors.
        
        Returns:
            Error summary dictionary
        """
        error_types = {}
        for error in self.errors:
            error_type = error['classification']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': len(self.errors),
            'critical_errors': len(self.critical_errors),
            'recoverable_errors': len(self.recoverable_errors),
            'error_types': error_types,
            'retry_counts': self.retry_counts
        }
    
    def generate_error_report(self) -> str:
        """Generate comprehensive error report.
        
        Returns:
            Formatted error report
        """
        report = []
        report.append("=" * 60)
        report.append("ERROR REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        summary = self.get_error_summary()
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Errors: {summary['total_errors']}")
        report.append(f"Critical Errors: {summary['critical_errors']}")
        report.append(f"Recoverable Errors: {summary['recoverable_errors']}")
        report.append("")
        
        # Error type distribution
        report.append("ERROR TYPES")
        report.append("-" * 40)
        for error_type, count in summary['error_types'].items():
            report.append(f"  {error_type}: {count}")
        report.append("")
        
        # Critical errors detail
        if self.critical_errors:
            report.append("CRITICAL ERRORS")
            report.append("-" * 40)
            for idx, error in enumerate(self.critical_errors[:10], 1):
                report.append(f"\n{idx}. {error['timestamp']}")
                report.append(f"   Type: {error['type']}")
                report.append(f"   Message: {error['message']}")
                if error.get('context'):
                    report.append(f"   Context: {json.dumps(error['context'], default=str)}")
            
            if len(self.critical_errors) > 10:
                report.append(f"\n... and {len(self.critical_errors) - 10} more critical errors")
        
        # Recent errors
        if self.errors:
            report.append("\nRECENT ERRORS (Last 10)")
            report.append("-" * 40)
            for error in self.errors[-10:]:
                report.append(f"  [{error['timestamp']}] {error['type']}: {error['message'][:80]}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def clear_errors(self):
        """Clear all tracked errors."""
        self.errors = []
        self.critical_errors = []
        self.recoverable_errors = []
        self.retry_counts = {}
        logger.debug("Cleared all error tracking")
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors occurred.
        
        Returns:
            True if critical errors exist
        """
        return len(self.critical_errors) > 0
    
    def get_retry_count(self, error_key: str) -> int:
        """Get retry count for specific error.
        
        Args:
            error_key: Error key
            
        Returns:
            Number of retries attempted
        """
        return self.retry_counts.get(error_key, 0)