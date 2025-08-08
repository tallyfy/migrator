"""
User Transformer
Transforms vendor users to Tallyfy users
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform vendor users to Tallyfy format"""
    
    def __init__(self, ai_client=None):
        """Initialize user transformer"""
        self.ai_client = ai_client
    
    def transform_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a vendor user to Tallyfy format"""
        try:
            tallyfy_user = {
                'email': self._extract_email(user),
                'first_name': user.get('first_name', user.get('firstName', '')),
                'last_name': user.get('last_name', user.get('lastName', '')),
                'full_name': self._extract_full_name(user),
                'role': self._transform_role(user),
                'active': user.get('active', user.get('is_active', True)),
                'vendor_metadata': {
                    'original_id': user.get('id', ''),
                    'original_role': user.get('role', ''),
                    'original_data': user
                }
            }
            
            # Add optional fields if present
            if 'phone' in user:
                tallyfy_user['phone'] = user['phone']
            if 'avatar' in user or 'avatar_url' in user:
                tallyfy_user['avatar_url'] = user.get('avatar', user.get('avatar_url'))
            
            return tallyfy_user
            
        except Exception as e:
            logger.error(f"Error transforming user: {e}")
            return self._create_fallback_user(user)
    
    def _extract_email(self, user: Dict[str, Any]) -> str:
        """Extract email from user data"""
        return user.get('email', user.get('email_address', ''))
    
    def _extract_full_name(self, user: Dict[str, Any]) -> str:
        """Extract or construct full name"""
        if 'full_name' in user:
            return user['full_name']
        if 'name' in user:
            return user['name']
        
        first = user.get('first_name', user.get('firstName', ''))
        last = user.get('last_name', user.get('lastName', ''))
        return f"{first} {last}".strip()
    
    def _transform_role(self, user: Dict[str, Any]) -> str:
        """Transform user role"""
        role = user.get('role', user.get('type', '')).lower()
        
        role_map = {
            'admin': 'admin',
            'administrator': 'admin',
            'owner': 'admin',
            'manager': 'manager',
            'member': 'member',
            'user': 'member',
            'guest': 'guest',
            'viewer': 'guest',
            'read_only': 'guest'
        }
        
        return role_map.get(role, 'member')
    
    def _create_fallback_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback user when transformation fails"""
        return {
            'email': str(user.get('email', user.get('id', 'unknown@example.com'))),
            'full_name': 'Unknown User',
            'role': 'member',
            'vendor_metadata': {'original_data': user}
        }
