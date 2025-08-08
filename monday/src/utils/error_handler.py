"""Error handling for Monday.com migration."""

import logging
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handle and track errors during migration."""
    
    # Error categories
    ERROR_CATEGORIES = {
        'api': 'API call failures',
        'validation': 'Data validation errors',
        'transformation': 'Data transformation errors',
        'rate_limit': 'Rate limiting errors',
        'network': 'Network connectivity errors',
        'authentication': 'Authentication failures',
        'permission': 'Permission denied errors',
        'data': 'Data integrity errors',
        'unknown': 'Unknown errors'
    }
    
    # Retryable error types
    RETRYABLE_ERRORS = [
        'rate_limit',
        'network',
        'api'
    ]
    
    def __init__(self, max_errors: int = 1000):
        """Initialize error handler.
        
        Args:
            max_errors: Maximum number of errors to keep in memory
        """
        self.max_errors = max_errors
        self.errors = []
        self.error_counts = defaultdict(int)
        self.error_by_category = defaultdict(list)
        self.retry_counts = defaultdict(int)
        self.critical_errors = []
    
    def handle_error(self, error: Exception, context: Optional[str] = None,
                    item_id: Optional[str] = None, retry_count: int = 0) -> Dict[str, Any]:
        """Handle an error.
        
        Args:
            error: The exception that occurred
            context: Context where error occurred
            item_id: ID of item being processed
            retry_count: Number of retries attempted
            
        Returns:
            Error information dictionary
        """
        error_info = self._create_error_info(error, context, item_id, retry_count)
        
        # Store error
        self._store_error(error_info)
        
        # Log error
        self._log_error(error_info)
        
        # Check if critical
        if self._is_critical_error(error_info):
            self.critical_errors.append(error_info)
            logger.critical(f"CRITICAL ERROR: {error_info['message']}")
        
        return error_info
    
    def _create_error_info(self, error: Exception, context: Optional[str],
                          item_id: Optional[str], retry_count: int) -> Dict[str, Any]:
        """Create error information dictionary.
        
        Args:
            error: The exception
            context: Error context
            item_id: Item ID
            retry_count: Retry count
            
        Returns:
            Error information
        """
        error_type = type(error).__name__
        error_message = str(error)
        category = self._categorize_error(error)
        
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'category': category,
            'message': error_message,
            'context': context,
            'item_id': item_id,
            'retry_count': retry_count,
            'retryable': category in self.RETRYABLE_ERRORS,
            'traceback': traceback.format_exc()
        }
        
        # Add error-specific details
        if hasattr(error, 'response'):
            # API error with response
            response = error.response
            if hasattr(response, 'status_code'):
                error_info['status_code'] = response.status_code
            if hasattr(response, "text"):
                error_info['response_body'] = response.text[:500]  # First 500 chars
        
        if hasattr(error, 'errors'):
            # Validation errors
            error_info['validation_errors'] = error.errors
        
        return error_info
    
    def _categorize_error(self, error: Exception) -> str:
        """Categorize error type.
        
        Args:
            error: The exception
            
        Returns:
            Error category
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Check for rate limiting
        if 'rate' in error_message or 'limit' in error_message or 'too many' in error_message:
            return 'rate_limit'
        
        # Check for network errors
        if 'connection' in error_message or 'timeout' in error_message or 'network' in error_message:
            return 'network'
        
        # Check for authentication
        if 'auth' in error_message or 'token' in error_message or 'unauthorized' in error_message:
            return 'authentication'
        
        # Check for permissions
        if 'permission' in error_message or 'forbidden' in error_message or 'access denied' in error_message:
            return 'permission'
        
        # Check for validation
        if 'validation' in error_type or 'invalid' in error_message:
            return 'validation'
        
        # Check for API errors
        if 'api' in error_type.lower() or hasattr(error, 'response'):
            return 'api'
        
        # Check for data errors
        if 'integrity' in error_message or 'constraint' in error_message:
            return 'data'
        
        # Default
        return 'unknown'
    
    def _store_error(self, error_info: Dict[str, Any]):
        """Store error information.
        
        Args:
            error_info: Error information
        """
        # Add to main list
        self.errors.append(error_info)
        
        # Trim if needed
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # Update counts
        category = error_info['category']
        self.error_counts[category] += 1
        
        # Store by category
        self.error_by_category[category].append(error_info)
        if len(self.error_by_category[category]) > 100:
            self.error_by_category[category] = self.error_by_category[category][-100:]
        
        # Track retries
        if error_info['item_id']:
            self.retry_counts[error_info['item_id']] = error_info['retry_count']
    
    def _log_error(self, error_info: Dict[str, Any]):
        """Log error based on severity.
        
        Args:
            error_info: Error information
        """
        message = f"[{error_info['category'].upper()}] {error_info['message']}"
        
        if error_info.get('context'):
            message += f" (Context: {error_info['context']})"
        
        if error_info.get('item_id'):
            message += f" (Item: {error_info['item_id']})"
        
        if error_info['retry_count'] > 0:
            message += f" (Retry: {error_info['retry_count']})"
        
        # Log based on category
        if error_info['category'] in ['authentication', 'permission']:
            logger.error(message)
        elif error_info['category'] == 'rate_limit':
            logger.warning(message)
        elif error_info['retryable']:
            logger.warning(message)
        else:
            logger.error(message)
    
    def _is_critical_error(self, error_info: Dict[str, Any]) -> bool:
        """Check if error is critical.
        
        Args:
            error_info: Error information
            
        Returns:
            True if critical
        """
        # Authentication errors are critical
        if error_info['category'] == 'authentication':
            return True
        
        # Permission errors after retries
        if error_info['category'] == 'permission' and error_info['retry_count'] > 2:
            return True
        
        # Too many errors of same type
        if self.error_counts[error_info['category']] > 50:
            return True
        
        # Specific status codes
        if error_info.get('status_code') in [401, 403, 500, 503]:
            return True
        
        return False
    
    def should_retry(self, error: Exception, retry_count: int = 0) -> bool:
        """Check if error should be retried.
        
        Args:
            error: The exception
            retry_count: Current retry count
            
        Returns:
            True if should retry
        """
        if retry_count >= 3:
            return False
        
        category = self._categorize_error(error)
        return category in self.RETRYABLE_ERRORS
    
    def get_retry_delay(self, retry_count: int, error_category: str) -> int:
        """Get retry delay in seconds.
        
        Args:
            retry_count: Current retry count
            error_category: Error category
            
        Returns:
            Delay in seconds
        """
        if error_category == 'rate_limit':
            # Exponential backoff for rate limits
            return min(300, 30 * (2 ** retry_count))  # 30s, 60s, 120s, max 300s
        elif error_category == 'network':
            # Linear backoff for network
            return min(60, 10 * (retry_count + 1))  # 10s, 20s, 30s, max 60s
        else:
            # Quick retry for other errors
            return min(10, 2 * (retry_count + 1))  # 2s, 4s, 6s, max 10s
    
    def get_errors(self, category: Optional[str] = None,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get errors.
        
        Args:
            category: Optional category filter
            limit: Maximum number of errors to return
            
        Returns:
            List of errors
        """
        if category:
            errors = self.error_by_category.get(category, [])
        else:
            errors = self.errors
        
        if limit:
            return errors[-limit:]
        return errors
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary.
        
        Returns:
            Error summary
        """
        summary = {
            'total_errors': len(self.errors),
            'critical_errors': len(self.critical_errors),
            'by_category': dict(self.error_counts),
            'retryable_errors': 0,
            'non_retryable_errors': 0,
            'items_with_retries': len(self.retry_counts)
        }
        
        # Count retryable vs non-retryable
        for error in self.errors:
            if error['retryable']:
                summary['retryable_errors'] += 1
            else:
                summary['non_retryable_errors'] += 1
        
        # Add category descriptions
        summary['category_descriptions'] = self.ERROR_CATEGORIES
        
        # Find most common errors
        error_messages = defaultdict(int)
        for error in self.errors:
            error_messages[error['message'][:100]] += 1
        
        summary['most_common_errors'] = sorted(
            error_messages.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return summary
    
    def get_error_report(self) -> str:
        """Get formatted error report.
        
        Returns:
            Formatted error report
        """
        summary = self.get_error_summary()
        
        lines = [
            "Error Report",
            "=" * 60,
            f"Total Errors: {summary['total_errors']}",
            f"Critical Errors: {summary['critical_errors']}",
            f"Retryable: {summary['retryable_errors']}",
            f"Non-Retryable: {summary['non_retryable_errors']}",
            f"Items with Retries: {summary['items_with_retries']}",
            "",
            "Errors by Category:",
        ]
        
        for category, count in summary['by_category'].items():
            description = self.ERROR_CATEGORIES.get(category, 'Unknown')
            lines.append(f"  {category}: {count} - {description}")
        
        if summary['most_common_errors']:
            lines.append("")
            lines.append("Most Common Errors:")
            for error_msg, count in summary['most_common_errors']:
                lines.append(f"  ({count}x) {error_msg}")
        
        if self.critical_errors:
            lines.append("")
            lines.append("Critical Errors:")
            for error in self.critical_errors[:5]:
                lines.append(f"  [{error['timestamp']}] {error['message']}")
        
        return "\n".join(lines)
    
    def clear_errors(self, category: Optional[str] = None):
        """Clear errors.
        
        Args:
            category: Optional category to clear
        """
        if category:
            self.error_by_category[category].clear()
            self.error_counts[category] = 0
            # Remove from main list
            self.errors = [e for e in self.errors if e['category'] != category]
        else:
            self.errors.clear()
            self.error_counts.clear()
            self.error_by_category.clear()
            self.retry_counts.clear()
            self.critical_errors.clear()
        
        logger.info(f"Cleared errors{f' for category {category}' if category else ''}")
    
    def has_critical_errors(self) -> bool:
        """Check if there are critical errors.
        
        Returns:
            True if critical errors exist
        """
        return len(self.critical_errors) > 0
    
    def export_errors(self, filepath: str):
        """Export errors to JSON file.
        
        Args:
            filepath: Path to export file
        """
        import json
        
        export_data = {
            'summary': self.get_error_summary(),
            'errors': self.errors,
            'critical_errors': self.critical_errors
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(self.errors)} errors to {filepath}")