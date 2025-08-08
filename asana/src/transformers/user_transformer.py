"""Transform Asana users and teams to Tallyfy members and groups."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform Asana users to Tallyfy members."""
    
    # Asana workspace membership to Tallyfy role mapping
    ROLE_MAP = {
        'admin': 'admin',           # Workspace admin -> Admin
        'member': 'member',          # Regular member -> Standard
        'guest': 'light',           # Guest -> Light member
        'limited_access': 'light',  # Limited access -> Light member
    }
    
    def transform_user(self, asana_user: Dict[str, Any],
                      workspace_membership: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Transform Asana user to Tallyfy member.
        
        Args:
            asana_user: Asana user object
            workspace_membership: User's workspace membership details
            
        Returns:
            Tallyfy member object
        """
        # Extract name parts
        full_name = asana_user.get('name', '')
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0] or 'Unknown'
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Determine role based on workspace membership
        role = 'member'  # Default to standard member
        if workspace_membership:
            asana_role = workspace_membership.get('user_task_list', {}).get('is_admin')
            if asana_role:
                role = 'admin'
            elif workspace_membership.get('is_guest'):
                role = 'light'
        
        tallyfy_member = {
            "text": asana_user.get("text", ''),
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'metadata': {
                'source': 'asana',
                'original_gid': asana_user.get('gid'),
                'photo_url': asana_user.get('photo', {}).get('image_128x128') if asana_user.get('photo') else None,
                'workspaces': asana_user.get('workspaces', [])
            }
        }
        
        logger.debug(f"Transformed user {full_name} ({asana_user.get("text")}) to {role} role")
        
        return tallyfy_member
    
    def transform_team(self, asana_team: Dict[str, Any],
                      team_members: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform Asana team to Tallyfy group.
        
        Args:
            asana_team: Asana team object
            team_members: List of team member objects
            
        Returns:
            Tallyfy group object
        """
        tallyfy_group = {
            'name': asana_team.get('name', 'Untitled Team'),
            'description': asana_team.get('description', ''),
            'members': [m.get('gid') for m in team_members],
            'metadata': {
                'source': 'asana',
                'original_gid': asana_team.get('gid'),
                'organization': asana_team.get('organization', {}).get('name'),
                'visibility': asana_team.get('visibility', 'private'),
                'html_description': asana_team.get('html_description', '')
            }
        }
        
        logger.debug(f"Transformed team {asana_team.get('name')} with {len(team_members)} members")
        
        return tallyfy_group
    
    def determine_user_permissions(self, asana_user: Dict[str, Any],
                                  projects: list[Dict[str, Any]]) -> Dict[str, list[str]]:
        """Determine user's permissions based on project membership.
        
        Args:
            asana_user: Asana user object
            projects: List of projects user is member of
            
        Returns:
            Dictionary of permission types to project IDs
        """
        permissions = {
            'owner': [],      # Projects user owns
            'editor': [],     # Projects user can edit
            'viewer': [],     # Projects user can only view
        }
        
        user_gid = asana_user.get('gid')
        
        for project in projects:
            # Check if user is owner
            if project.get('owner', {}).get('gid') == user_gid:
                permissions['owner'].append(project.get('gid'))
            # Check if user is member
            elif any(m.get('gid') == user_gid for m in project.get('members', [])):
                # In Asana, project members typically have edit access
                permissions['editor'].append(project.get('gid'))
            # Check if user has any tasks assigned
            else:
                # User might have view-only access
                permissions['viewer'].append(project.get('gid'))
        
        return permissions
    
    def transform_user_preferences(self, asana_user: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user preferences and settings.
        
        Args:
            asana_user: Asana user object
            
        Returns:
            Tallyfy user preferences
        """
        preferences = {
            'email_notifications': True,  # Default to enabled
            'timezone': 'UTC',  # Default, Asana doesn't expose timezone via API
            'language': 'en',   # Default to English
            'ui_theme': 'light', # Default theme
        }
        
        # Map any available preferences
        if asana_user.get("text"):
            preferences['notification_email'] = asana_user["text"]
        
        return preferences
    
    def calculate_user_role(self, asana_user: Dict[str, Any],
                           owned_projects: int,
                           tasks_assigned: int,
                           is_guest: bool = False) -> str:
        """Calculate appropriate Tallyfy role based on usage patterns.
        
        Args:
            asana_user: Asana user object
            owned_projects: Number of projects owned
            tasks_assigned: Number of tasks assigned
            is_guest: Whether user is a guest
            
        Returns:
            Recommended Tallyfy role
        """
        # Guests always become light members
        if is_guest:
            return 'light'
        
        # Users who own projects should be standard members or admins
        if owned_projects > 0:
            # If they own many projects, consider admin role
            if owned_projects >= 5:
                return 'admin'
            return 'member'
        
        # Users with many task assignments need standard member access
        if tasks_assigned >= 10:
            return 'member'
        
        # Users with minimal activity can be light members
        if tasks_assigned < 5:
            return 'light'
        
        # Default to standard member
        return 'member'
    
    def transform_user_activity(self, stories: list[Dict[str, Any]],
                              user_gid: str) -> Dict[str, Any]:
        """Transform user's activity history.
        
        Args:
            stories: List of story (activity) objects
            user_gid: User's GID
            
        Returns:
            User activity summary
        """
        activity = {
            'comments_created': 0,
            'tasks_completed': 0,
            'tasks_created': 0,
            'attachments_added': 0,
            'last_activity': None
        }
        
        for story in stories:
            if story.get('created_by', {}).get('gid') != user_gid:
                continue
                
            story_type = story.get('resource_subtype', story.get('type'))
            
            if story_type == 'comment_added':
                activity['comments_created'] += 1
            elif story_type == 'marked_complete':
                activity['tasks_completed'] += 1
            elif story_type == 'added':
                activity['tasks_created'] += 1
            elif story_type == 'attachment_added':
                activity['attachments_added'] += 1
            
            # Track last activity
            created_at = story.get('created_at')
            if created_at and (not activity['last_activity'] or created_at > activity['last_activity']):
                activity['last_activity'] = created_at
        
        return activity