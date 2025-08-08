"""
User Transformer
Transforms Process Street users to Tallyfy users
"""

import logging
from typing import Dict, Any, Optional
from .base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class UserTransformer(BaseTransformer):
    """Transform Process Street users to Tallyfy format"""
    
    # Role mapping from Process Street to Tallyfy
    ROLE_MAPPING = {
        'Admin': 'admin',
        'Manager': 'admin',
        'Member': 'member',
        'Guest': 'light',
        'Anonymous Guest': 'guest',
        'Standard': 'member',
        'ReadOnly': 'light'
    }
    
    def transform(self, ps_user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Process Street user to Tallyfy user
        
        Args:
            ps_user: Process Street user object
            
        Returns:
            Tallyfy user object
        """
        # Extract Process Street user data
        ps_id = ps_user.get('id', '')
        email = ps_user.get("text", '')
        
        # Validate required fields
        is_valid, missing = self.validate_required_fields(
            ps_user, 
            ["text"]
        )
        
        if not is_valid:
            raise ValueError(f"Missing required fields for user: {missing}")
        
        # Check if already mapped
        tallyfy_id = self.get_mapped_id(ps_id, 'user')
        if not tallyfy_id:
            tallyfy_id = self.generate_tallyfy_id('usr', ps_id)
        
        # Build Tallyfy user object
        tallyfy_user = {
            'id': tallyfy_id,
            "text": email,
            'first_name': ps_user.get('firstName', ps_user.get('first_name', '')),
            'last_name': ps_user.get('lastName', ps_user.get('last_name', '')),
            'role': self._map_role(ps_user.get('role', 'Member')),
            'is_active': ps_user.get('active', True),
            'timezone': ps_user.get('timezone', 'UTC'),
            "text": ps_user.get("text", ''),
            'title': ps_user.get('title', ''),
            'department': ps_user.get('department', ''),
            'location': ps_user.get('location', ''),
            'bio': ps_user.get('bio', ''),
            'avatar': ps_user.get('avatar_url', ps_user.get('avatar', '')),
            'created_at': self.convert_datetime(ps_user.get('created_at')),
            'updated_at': self.convert_datetime(ps_user.get('updated_at'))
        }
        
        # Add external reference
        tallyfy_user = self.add_external_reference(tallyfy_user, ps_id, 'user')
        
        # Handle user preferences/settings
        if 'preferences' in ps_user:
            tallyfy_user['settings'] = self._transform_preferences(ps_user['preferences'])
        
        # Handle groups membership
        if 'groups' in ps_user:
            tallyfy_user['group_ids'] = self._map_groups(ps_user['groups'])
        
        # Store ID mapping
        self.map_id(ps_id, tallyfy_id, 'user')
        
        logger.debug(f"Transformed user: {email} ({ps_id} -> {tallyfy_id})")
        
        return tallyfy_user
    
    def _map_role(self, ps_role: str) -> str:
        """
        Map Process Street role to Tallyfy role
        
        Args:
            ps_role: Process Street role name
            
        Returns:
            Tallyfy role name
        """
        return self.ROLE_MAPPING.get(ps_role, 'member')
    
    def _transform_preferences(self, ps_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform user preferences
        
        Args:
            ps_preferences: Process Street user preferences
            
        Returns:
            Tallyfy user settings
        """
        return {
            'email_notifications': ps_preferences.get('emailNotifications', True),
            'push_notifications': ps_preferences.get('pushNotifications', False),
            'daily_digest': ps_preferences.get('dailyDigest', False),
            'weekly_summary': ps_preferences.get('weeklySummary', False),
            'notification_sound': ps_preferences.get('notificationSound', True),
            'desktop_notifications': ps_preferences.get('desktopNotifications', True),
            'mobile_notifications': ps_preferences.get('mobileNotifications', True),
            'language': ps_preferences.get('language', 'en'),
            'date_format': ps_preferences.get('dateFormat', 'MM/DD/YYYY'),
            'time_format': ps_preferences.get('timeFormat', '12h')
        }
    
    def _map_groups(self, ps_groups: list) -> list:
        """
        Map Process Street groups to Tallyfy group IDs
        
        Args:
            ps_groups: List of Process Street group objects or IDs
            
        Returns:
            List of Tallyfy group IDs
        """
        tallyfy_groups = []
        
        for group in ps_groups:
            if isinstance(group, dict):
                group_id = group.get('id')
            else:
                group_id = group
            
            if group_id:
                tallyfy_group_id = self.get_mapped_id(group_id, 'group')
                if tallyfy_group_id:
                    tallyfy_groups.append(tallyfy_group_id)
        
        return tallyfy_groups
    
    def transform_guest(self, ps_guest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Process Street guest user to Tallyfy guest
        
        Args:
            ps_guest: Process Street guest object
            
        Returns:
            Tallyfy guest object
        """
        ps_id = ps_guest.get('id', '')
        email = ps_guest.get("text", '')
        
        # Generate guest ID
        tallyfy_id = self.generate_tallyfy_id('gst', ps_id)
        
        tallyfy_guest = {
            'id': tallyfy_id,
            "text": email,
            'first_name': ps_guest.get('firstName', ps_guest.get('name', '').split()[0] if ps_guest.get('name') else ''),
            'last_name': ps_guest.get('lastName', ' '.join(ps_guest.get('name', '').split()[1:]) if ps_guest.get('name') else ''),
            'role': 'guest',
            'is_active': True,
            'guest_code': ps_guest.get('accessCode', self.generate_tallyfy_id('code', email)),
            'expires_at': self.convert_datetime(ps_guest.get('expiresAt')),
            'permissions': self._map_guest_permissions(ps_guest.get('permissions', [])),
            'accessible_entities': self._map_guest_access(ps_guest.get('access', []))
        }
        
        # Add external reference
        tallyfy_guest = self.add_external_reference(tallyfy_guest, ps_id, 'guest')
        
        # Store ID mapping
        self.map_id(ps_id, tallyfy_id, 'guest')
        
        return tallyfy_guest
    
    def _map_guest_permissions(self, ps_permissions: list) -> list:
        """
        Map Process Street guest permissions to Tallyfy
        
        Args:
            ps_permissions: List of Process Street permissions
            
        Returns:
            List of Tallyfy guest permissions
        """
        permission_mapping = {
            'view': 'read',
            'comment': 'comment',
            'complete_tasks': 'complete_steps',
            'edit_forms': 'edit_captures',
            'upload_files': 'upload_attachments'
        }
        
        tallyfy_permissions = []
        for perm in ps_permissions:
            if perm in permission_mapping:
                tallyfy_permissions.append(permission_mapping[perm])
        
        # Default minimum permissions for guests
        if 'read' not in tallyfy_permissions:
            tallyfy_permissions.append('read')
        
        return tallyfy_permissions
    
    def _map_guest_access(self, ps_access: list) -> list:
        """
        Map guest access to specific entities
        
        Args:
            ps_access: List of accessible entities in Process Street
            
        Returns:
            List of accessible entities in Tallyfy
        """
        tallyfy_access = []
        
        for access in ps_access:
            entity_type = access.get('type', '')
            entity_id = access.get('id', '')
            
            if entity_type == 'workflow':
                tallyfy_entity_id = self.get_mapped_id(entity_id, 'multiselect')
                if tallyfy_entity_id:
                    tallyfy_access.append({
                        'type': 'multiselect',
                        'id': tallyfy_entity_id
                    })
            elif entity_type == 'run':
                tallyfy_entity_id = self.get_mapped_id(entity_id, 'process')
                if tallyfy_entity_id:
                    tallyfy_access.append({
                        'type': 'process',
                        'id': tallyfy_entity_id
                    })
        
        return tallyfy_access