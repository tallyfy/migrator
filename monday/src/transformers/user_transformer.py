"""Transform Monday.com users and teams to Tallyfy members and groups."""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform Monday.com users, teams, and permissions to Tallyfy."""
    
    # Monday.com user types to Tallyfy roles mapping
    ROLE_MAPPING = {
        # Monday.com admins
        'admin': 'admin',
        
        # Regular members
        'member': 'member',
        'team_member': 'member',
        'user': 'member',
        
        # View-only users
        'viewer': 'light',
        'view_only': 'light',
        
        # Guest users
        'guest': 'light',
        'external': 'light'
    }
    
    def __init__(self):
        self.transformed_users = {}
        self.transformed_teams = {}
        self.user_mapping = {}
        
    def transform_user(self, monday_user: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Monday.com user to Tallyfy member.
        
        Args:
            monday_user: Monday.com user object
            
        Returns:
            Tallyfy member object
        """
        user_id = monday_user.get('id', '')
        email = monday_user.get("text", '')
        
        if not email:
            logger.warning(f"User {user_id} has no email, skipping")
            return None
        
        # Determine role based on Monday.com permissions
        tallyfy_role = self._determine_role(monday_user)
        
        # Extract name parts
        name = monday_user.get('name', '').strip()
        name_parts = name.split(' ', 1) if name else ['', '']
        first_name = name_parts[0] or 'User'
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        tallyfy_member = {
            "text": email.lower(),
            'firstname': first_name,
            'lastname': last_name,
            'role': tallyfy_role,
            'active': monday_user.get('enabled', True),
            'title': monday_user.get('title', ''),
            "text": monday_user.get("text", ''),
            'location': monday_user.get('location', ''),
            'metadata': {
                'source': 'monday',
                'original_id': user_id,
                'is_admin': monday_user.get('is_admin', False),
                'is_guest': monday_user.get('is_guest', False),
                'is_pending': monday_user.get('is_pending', False),
                'is_view_only': monday_user.get('is_view_only', False),
                'created_at': monday_user.get('created_at'),
                'photo_url': monday_user.get('photo_thumb', '')
            }
        }
        
        # Track transformed user
        self.transformed_users[user_id] = tallyfy_member
        self.user_mapping[user_id] = email
        
        logger.info(f"Transformed user '{name}' ({email}) to role '{tallyfy_role}'")
        
        return tallyfy_member
    
    def transform_team(self, monday_team: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Monday.com team to Tallyfy group.
        
        Args:
            monday_team: Monday.com team object
            
        Returns:
            Tallyfy group object
        """
        team_id = monday_team.get('id', '')
        team_name = monday_team.get('name', 'Unnamed Team')
        
        # Get team members
        member_ids = []
        for user in monday_team.get('users', []):
            user_id = user.get('id', '')
            if user_id in self.user_mapping:
                member_ids.append(self.user_mapping[user_id])
        
        # Get team owners
        owner_ids = []
        for owner in monday_team.get('owners', []):
            owner_id = owner.get('id', '')
            if owner_id in self.user_mapping:
                owner_ids.append(self.user_mapping[owner_id])
        
        tallyfy_group = {
            'name': team_name,
            'description': f"Team migrated from Monday.com",
            'members': member_ids,
            'admins': owner_ids,  # Team owners become group admins
            'metadata': {
                'source': 'monday',
                'original_id': team_id,
                'picture_url': monday_team.get('picture_url', ''),
                'member_count': len(member_ids),
                'owner_count': len(owner_ids)
            }
        }
        
        # Track transformed team
        self.transformed_teams[team_id] = tallyfy_group
        
        logger.info(f"Transformed team '{team_name}' with {len(member_ids)} members")
        
        return tallyfy_group
    
    def _determine_role(self, user: Dict[str, Any]) -> str:
        """Determine Tallyfy role based on Monday.com user attributes.
        
        Args:
            user: Monday.com user object
            
        Returns:
            Tallyfy role string
        """
        # Admin users
        if user.get('is_admin'):
            return 'admin'
        
        # View-only users
        if user.get('is_view_only'):
            return 'light'
        
        # Guest users
        if user.get('is_guest'):
            return 'light'
        
        # Default to member
        return 'member'
    
    def create_workspace_groups(self, workspaces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create groups based on Monday.com workspaces.
        
        Args:
            workspaces: List of Monday.com workspaces
            
        Returns:
            List of Tallyfy groups
        """
        groups = []
        
        for workspace in workspaces:
            workspace_id = workspace.get('id', '')
            workspace_name = workspace.get('name', 'Unnamed Workspace')
            workspace_kind = workspace.get('kind', 'open')
            
            group = {
                'name': f"Workspace: {workspace_name}",
                'description': f"Members of Monday.com {workspace_kind} workspace",
                'members': [],  # Would need to be populated based on workspace members
                'metadata': {
                    'source': 'monday',
                    'type': 'workspace',
                    'original_id': workspace_id,
                    'workspace_kind': workspace_kind,
                    'created_at': workspace.get('created_at'),
                    'settings': workspace.get('settings', {})
                }
            }
            
            groups.append(group)
            
        logger.info(f"Created {len(groups)} workspace-based groups")
        
        return groups
    
    def map_board_permissions(self, board: Dict[str, Any],
                            user_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map board-level permissions to Tallyfy blueprint permissions.
        
        Args:
            board: Monday.com board object
            user_mapping: Mapping of Monday user IDs to Tallyfy member IDs
            
        Returns:
            Tallyfy permission configuration
        """
        permissions = {
            'admins': [],
            'members': [],
            'viewers': [],
            'visibility': 'organization'  # Default
        }
        
        # Map board owner
        owner = board.get('owner', {})
        if owner and owner.get('id') in user_mapping:
            permissions['admins'].append(user_mapping[owner['id']])
        
        # Map board kind to visibility
        board_kind = board.get('board_kind', 'public')
        if board_kind == 'private':
            permissions['visibility'] = 'private'
        elif board_kind == 'share':
            permissions['visibility'] = 'organization'  # Shareable boards
        else:
            permissions['visibility'] = 'organization'
        
        # Map board permissions
        board_perms = board.get('permissions', {})
        if isinstance(board_perms, dict):
            # Map specific user permissions if available
            for user_id, perm_level in board_perms.items():
                if user_id in user_mapping:
                    tallyfy_user = user_mapping[user_id]
                    if perm_level == 'write':
                        permissions['members'].append(tallyfy_user)
                    elif perm_level == 'read':
                        permissions['viewers'].append(tallyfy_user)
        
        return permissions
    
    def create_user_migration_report(self, users: List[Dict[str, Any]],
                                   teams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create detailed user migration report.
        
        Args:
            users: List of Monday.com users
            teams: List of Monday.com teams
            
        Returns:
            Migration report with statistics
        """
        report = {
            'total_users': len(users),
            'total_teams': len(teams),
            'role_distribution': {
                'admins': 0,
                'members': 0,
                'viewers': 0,
                'guests': 0
            },
            'user_status': {
                'active': 0,
                'pending': 0,
                'disabled': 0
            },
            'teams_summary': [],
            'warnings': [],
            'role_mappings': []
        }
        
        # Analyze users
        for user in users:
            # Count by role
            if user.get('is_admin'):
                report['role_distribution']['admins'] += 1
            elif user.get('is_view_only'):
                report['role_distribution']['viewers'] += 1
            elif user.get('is_guest'):
                report['role_distribution']['guests'] += 1
            else:
                report['role_distribution']['members'] += 1
            
            # Count by status
            if user.get('is_pending'):
                report['user_status']['pending'] += 1
            elif not user.get('enabled', True):
                report['user_status']['disabled'] += 1
            else:
                report['user_status']['active'] += 1
            
            # Check for issues
            if not user.get("text"):
                report['warnings'].append(f"User {user.get('id')} has no email address")
            
            if user.get('is_pending'):
                report['warnings'].append(f"User {user.get('name', 'Unknown')} is pending activation")
        
        # Analyze teams
        for team in teams:
            team_summary = {
                'name': team.get('name', 'Unnamed'),
                'member_count': len(team.get('users', [])),
                'owner_count': len(team.get('owners', []))
            }
            report['teams_summary'].append(team_summary)
        
        # Add role mapping summary
        report['role_mappings'] = [
            {'monday_role': 'Admin', 'tallyfy_role': 'Admin', 'count': report['role_distribution']['admins']},
            {'monday_role': 'Member', 'tallyfy_role': 'Member', 'count': report['role_distribution']['members']},
            {'monday_role': 'Viewer', 'tallyfy_role': 'Light', 'count': report['role_distribution']['viewers']},
            {'monday_role': 'Guest', 'tallyfy_role': 'Light', 'count': report['role_distribution']['guests']}
        ]
        
        return report
    
    def handle_guest_users(self, guest_users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle guest users separately.
        
        Args:
            guest_users: List of guest users
            
        Returns:
            List of transformed guest members
        """
        guest_members = []
        
        for guest in guest_users:
            if not guest.get("text"):
                continue
            
            member = self.transform_user(guest)
            if member:
                # Ensure guests are light users
                member['role'] = 'light'
                member['metadata']['is_external_guest'] = True
                guest_members.append(member)
        
        logger.info(f"Processed {len(guest_members)} guest users")
        
        return guest_members
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get transformed user by Monday.com ID.
        
        Args:
            user_id: Monday.com user ID
            
        Returns:
            Transformed Tallyfy member or None
        """
        return self.transformed_users.get(user_id)
    
    def get_team_by_id(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get transformed team by Monday.com ID.
        
        Args:
            team_id: Monday.com team ID
            
        Returns:
            Transformed Tallyfy group or None
        """
        return self.transformed_teams.get(team_id)