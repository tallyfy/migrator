"""
Base Transformer Class
Provides common functionality for all data transformers
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class BaseTransformer:
    """Base class for all data transformers"""
    
    def __init__(self, id_mapper: Optional['IDMapper'] = None):
        """
        Initialize base transformer
        
        Args:
            id_mapper: Optional ID mapping utility
        """
        self.id_mapper = id_mapper
        self.transformation_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'warnings': []
        }
    
    def generate_tallyfy_id(self, prefix: str = '', source_id: str = '') -> str:
        """
        Generate a Tallyfy-compatible 32-character hash ID
        
        Args:
            prefix: Optional prefix for the ID
            source_id: Source system ID for consistent mapping
            
        Returns:
            32-character hash ID
        """
        if source_id:
            # Generate consistent ID based on source
            hash_input = f"{prefix}_{source_id}"
            hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        else:
            # Generate random ID
            timestamp = str(datetime.utcnow().timestamp())
            hash_value = hashlib.md5(timestamp.encode()).hexdigest()
        
        if prefix:
            prefix_len = min(len(prefix), 8)
            return prefix[:prefix_len] + hash_value[:32-prefix_len]
        
        return hash_value[:32]
    
    def map_id(self, source_id: str, tallyfy_id: str, entity_type: str) -> None:
        """
        Store ID mapping
        
        Args:
            source_id: Process Street ID
            tallyfy_id: Tallyfy ID
            entity_type: Type of entity
        """
        if self.id_mapper:
            self.id_mapper.add_mapping(source_id, tallyfy_id, entity_type)
    
    def get_mapped_id(self, source_id: str, entity_type: str) -> Optional[str]:
        """
        Get mapped Tallyfy ID for a source ID
        
        Args:
            source_id: Process Street ID
            entity_type: Type of entity
            
        Returns:
            Tallyfy ID if mapped, None otherwise
        """
        if self.id_mapper:
            return self.id_mapper.get_tallyfy_id(source_id, entity_type)
        return None
    
    def clean_html(self, html_content: str) -> str:
        """
        Clean and convert HTML content to markdown
        
        Args:
            html_content: HTML string
            
        Returns:
            Cleaned markdown string
        """
        if not html_content:
            return ''
        
        # Basic HTML to Markdown conversion
        import re
        
        # Remove script and style tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        # Convert common HTML tags
        conversions = [
            (r'<br\s*/?>', '\n'),
            (r'<p[^>]*>', '\n'),
            (r'</p>', '\n'),
            (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
            (r'<b[^>]*>(.*?)</b>', r'**\1**'),
            (r'<em[^>]*>(.*?)</em>', r'*\1*'),
            (r'<i[^>]*>(.*?)</i>', r'*\1*'),
            (r'<h1[^>]*>(.*?)</h1>', r'# \1\n'),
            (r'<h2[^>]*>(.*?)</h2>', r'## \1\n'),
            (r'<h3[^>]*>(.*?)</h3>', r'### \1\n'),
            (r'<li[^>]*>(.*?)</li>', r'- \1\n'),
            (r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)'),
        ]
        
        for pattern, replacement in conversions:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Remove remaining HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content
    
    def convert_datetime(self, date_str: Optional[str]) -> Optional[str]:
        """
        Convert datetime string to ISO 8601 format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            ISO 8601 formatted datetime string
        """
        if not date_str:
            return None
        
        # Try common date formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat() + 'Z'
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return date_str
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that required fields are present
        
        Args:
            data: Data dictionary
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing.append(field)
        
        return len(missing) == 0, missing
    
    def add_external_reference(self, data: Dict[str, Any], source_id: str, source_type: str) -> Dict[str, Any]:
        """
        Add external reference metadata
        
        Args:
            data: Target data dictionary
            source_id: Source system ID
            source_type: Source system type
            
        Returns:
            Updated data dictionary
        """
        data['external_ref'] = source_id
        data['external_source'] = 'process_street'
        data['external_type'] = source_type
        data['migrated_at'] = datetime.utcnow().isoformat() + 'Z'
        
        return data
    
    def handle_transformation_error(self, source_data: Dict[str, Any], error: Exception) -> None:
        """
        Handle and log transformation errors
        
        Args:
            source_data: Original source data
            error: Exception that occurred
        """
        self.transformation_stats['failed'] += 1
        
        error_info = {
            'source_id': source_data.get('id', 'unknown'),
            'source_type': source_data.get('type', 'unknown'),
            'error': str(error),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.error(f"Transformation error: {error_info}")
        
        # Store for reporting
        self.transformation_stats['warnings'].append(error_info)
    
    def transform(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform source data to target format
        Must be implemented by subclasses
        
        Args:
            source_data: Source system data
            
        Returns:
            Transformed data for target system
        """
        raise NotImplementedError("Subclasses must implement transform method")
    
    def batch_transform(self, source_list: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """
        Transform a batch of items
        
        Args:
            source_list: List of source items
            
        Returns:
            Tuple of (successful_transforms, failed_transforms)
        """
        successful = []
        failed = []
        
        for item in source_list:
            self.transformation_stats['total'] += 1
            
            try:
                transformed = self.transform(item)
                successful.append(transformed)
                self.transformation_stats['successful'] += 1
                
            except Exception as e:
                self.handle_transformation_error(item, e)
                failed.append({
                    'source': item,
                    'error': str(e)
                })
        
        return successful, failed
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transformation statistics"""
        return self.transformation_stats.copy()