"""Transform Kissflow users and roles to Tallyfy members."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform Kissflow users, groups, and roles to Tallyfy members."""
    
    # Kissflow role to Tallyfy role mapping
    ROLE_MAPPING = {
        'super_admin': 'admin',
        'admin': 'admin',
        'developer': 'admin',  # Developers become admins in Tallyfy
        'process_admin': 'member',
        'board_admin': 'member',
        'app_admin': 'member',
        'member': 'member',
        'user': 'member',
        'light_user': 'light',  # Limited access users
        'guest': 'light',
        'viewer': 'light',
        'external': 'light'
    }
    
    # Department to group mapping
    DEPARTMENT_PREFIX = 'dept_'
    ROLE_PREFIX = 'role_'
    
    def __init__(self):
        self.transformed_users = {}
        self.transformed_groups = {}
        self.role_mappings = {}
        
    def transform_user(self, kissflow_user: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow user to Tallyfy member.
        
        Args:
            kissflow_user: Kissflow user object
            
        Returns:
            Tallyfy member object
        """
        user_id = kissflow_user.get('Id', '')
        email = kissflow_user.get('Email', '')
        
        if not email:
            logger.warning(f"User {user_id} has no email, using ID as email")
            email = f"{user_id}@kissflow-migration.local"
        
        # Map role
        kissflow_role = kissflow_user.get('Role', 'member').lower()
        tallyfy_role = self.ROLE_MAPPING.get(kissflow_role, 'member')
        
        # Check if user has admin privileges in any module
        if self._has_admin_privileges(kissflow_user):
            tallyfy_role = 'admin'
        
        tallyfy_member = {
            "text": email.lower(),
            'firstname': kissflow_user.get('FirstName', ''),
            'lastname': kissflow_user.get('LastName', ''),
            'role': tallyfy_role,
            'active': kissflow_user.get('Status', 'active') == 'active',
            'metadata': {
                'source': 'kissflow',
                'original_id': user_id,
                'original_role': kissflow_role,
                'department': kissflow_user.get('Department'),
                'designation': kissflow_user.get('Designation'),
                'employee_id': kissflow_user.get('EmployeeId'),
                'manager': kissflow_user.get('Manager'),
                'created_at': kissflow_user.get('CreatedAt'),
                'last_login': kissflow_user.get('LastLogin')
            }
        }
        
        # Add profile data
        if kissflow_user.get('ProfilePicture'):
            tallyfy_member['avatar_url'] = kissflow_user['ProfilePicture']
        
        if kissflow_user.get('Phone'):
            tallyfy_member["text"] = kissflow_user['Phone']
        
        if kissflow_user.get('TimeZone'):
            tallyfy_member['timezone'] = kissflow_user['TimeZone']
        
        # Track for group assignment
        self.transformed_users[user_id] = tallyfy_member
        
        logger.info(f"Transformed user {email} from role '{kissflow_role}' to '{tallyfy_role}'")
        
        return tallyfy_member
    
    def transform_group(self, kissflow_group: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow group/department to Tallyfy group.
        
        Args:
            kissflow_group: Kissflow group or department
            
        Returns:
            Tallyfy group object
        """
        group_id = kissflow_group.get('Id', '')
        group_type = kissflow_group.get('Type', 'group')
        
        # Determine group name based on type
        if group_type == 'department':
            name = f"{self.DEPARTMENT_PREFIX}{kissflow_group.get('Name', '')}"
        elif group_type == 'role':
            name = f"{self.ROLE_PREFIX}{kissflow_group.get('Name', '')}"
        else:
            name = kissflow_group.get('Name', 'Unnamed Group')
        
        tallyfy_group = {
            'name': name,
            'description': kissflow_group.get('Description', ''),
            'members': [],  # Will be populated separately
            'metadata': {
                'source': 'kissflow',
                'original_id': group_id,
                'original_type': group_type,
                'created_at': kissflow_group.get('CreatedAt')
            }
        }
        
        # Track group
        self.transformed_groups[group_id] = tallyfy_group
        
        logger.info(f"Transformed {group_type} '{kissflow_group.get('Name')}' to group '{name}'")
        
        return tallyfy_group
    
    def create_department_groups(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create groups based on user departments.
        
        Args:
            users: List of Kissflow users
            
        Returns:
            List of department groups
        """
        departments = {}
        
        for user in users:
            dept = user.get('Department')
            if dept and dept not in departments:
                departments[dept] = {
                    'name': f"{self.DEPARTMENT_PREFIX}{dept}",
                    'description': f"Department: {dept}",
                    'members': [],
                    'metadata': {
                        'source': 'kissflow',
                        'type': 'department',
                        'original_name': dept
                    }
                }
            
            # Add user to department group
            if dept:
                departments[dept]['members'].append(user.get('Id'))
        
        return list(departments.values())
    
    def create_role_groups(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create groups based on Kissflow roles.
        
        Args:
            users: List of Kissflow users
            
        Returns:
            List of role-based groups
        """
        role_groups = {}
        
        for user in users:
            role = user.get('Role', 'member')
            if role not in role_groups:
                role_groups[role] = {
                    'name': f"{self.ROLE_PREFIX}{role}",
                    'description': f"Users with {role} role in Kissflow",
                    'members': [],
                    'metadata': {
                        'source': 'kissflow',
                        'type': 'role',
                        'original_role': role,
                        'tallyfy_role': self.ROLE_MAPPING.get(role.lower(), 'member')
                    }
                }
            
            role_groups[role]['members'].append(user.get('Id'))
        
        return list(role_groups.values())
    
    def transform_permissions(self, permissions: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Kissflow permissions to Tallyfy permissions.
        
        Args:
            permissions: Kissflow permission object
            
        Returns:
            Tallyfy permission mapping
        """
        tallyfy_permissions = {
            'visibility': 'private',  # Default to private
            'admins': [],
            'members': [],
            'viewers': [],
            'initiators': []
        }
        
        # Map visibility
        if permissions.get('Public'):
            tallyfy_permissions['visibility'] = 'public'
        elif permissions.get('Visibility') == 'organization':
            tallyfy_permissions['visibility'] = 'organization'
        
        # Map user permissions
        for perm_type, users in permissions.get('Users', {}).items():
            if perm_type == 'admins':
                tallyfy_permissions['admins'].extend(users)
            elif perm_type == 'editors' or perm_type == 'members':
                tallyfy_permissions['members'].extend(users)
            elif perm_type == 'viewers':
                tallyfy_permissions['viewers'].extend(users)
            elif perm_type == 'initiators':
                tallyfy_permissions['initiators'].extend(users)
        
        # Map group permissions
        for perm_type, groups in permissions.get('Groups', {}).items():
            # Groups need to be expanded to user lists
            for group_id in groups:
                if group_id in self.transformed_groups:
                    group_members = self.transformed_groups[group_id].get('members', [])
                    if perm_type == 'admins':
                        tallyfy_permissions['admins'].extend(group_members)
                    elif perm_type == 'members':
                        tallyfy_permissions['members'].extend(group_members)
                    elif perm_type == 'viewers':
                        tallyfy_permissions['viewers'].extend(group_members)
        
        # Remove duplicates
        for key in ['admins', 'members', 'viewers', 'initiators']:
            tallyfy_permissions[key] = list(set(tallyfy_permissions[key]))
        
        return tallyfy_permissions
    
    def map_assignee(self, kissflow_assignee: Any) -> str:
        """Map Kissflow assignee to Tallyfy format.
        
        Args:
            kissflow_assignee: Kissflow assignee (user, group, role, etc.)
            
        Returns:
            Tallyfy assignee string
        """
        if not kissflow_assignee:
            return 'process_owner'
        
        if isinstance(kissflow_assignee, str):
            # Direct user ID or short_text
            if '@' in kissflow_assignee:
                return f"member:{kissflow_assignee.lower()}"
            # Check if it's a known user ID
            if kissflow_assignee in self.transformed_users:
                email = self.transformed_users[kissflow_assignee].get("text")
                return f"member:{email}"
            return f"member:{kissflow_assignee}"
        
        if isinstance(kissflow_assignee, dict):
            assignee_type = kissflow_assignee.get('Type', 'user')
            
            if assignee_type == 'user':
                user_id = kissflow_assignee.get('UserId') or kissflow_assignee.get('Id')
                if user_id in self.transformed_users:
                    email = self.transformed_users[user_id].get("text")
                    return f"member:{email}"
                return f"member:{user_id}"
            
            elif assignee_type == 'group':
                group_id = kissflow_assignee.get('GroupId') or kissflow_assignee.get('Id')
                if group_id in self.transformed_groups:
                    group_name = self.transformed_groups[group_id].get('name')
                    return f"group:{group_name}"
                return f"group:{group_id}"
            
            elif assignee_type == 'role':
                role = kissflow_assignee.get('Role', 'member')
                # Map specific roles
                if role == 'manager':
                    return 'manager'
                elif role == 'initiator':
                    return 'process_initiator'
                elif role == 'previous_assignee':
                    return 'previous_assignee'
                else:
                    return f"role:{role}"
            
            elif assignee_type == 'field':
                # Dynamic assignment from field value
                field = kissflow_assignee.get('Field', '')
                return f"field:{field}"
            
            elif assignee_type == 'formula':
                # Formula-based assignment
                return 'process_owner'  # Default, needs manual configuration
        
        return 'process_owner'
    
    def _has_admin_privileges(self, user: Dict[str, Any]) -> bool:
        """Check if user has admin privileges in any module.
        
        Args:
            user: Kissflow user object
            
        Returns:
            True if user has admin privileges
        """
        # Check for admin roles
        if user.get('IsSuperAdmin') or user.get('IsAdmin'):
            return True
        
        # Check module-specific admin roles
        admin_fields = ['IsProcessAdmin', 'IsBoardAdmin', 'IsAppAdmin', 
                       'IsDatasetAdmin', 'IsDeveloper']
        
        for field in admin_fields:
            if user.get(field):
                return True
        
        # Check permissions array
        permissions = user.get('Permissions', [])
        admin_permissions = ['create_process', 'create_board', 'create_app', 
                           'manage_users', 'manage_organization']
        
        for perm in admin_permissions:
            if perm in permissions:
                return True
        
        return False
    
    def create_user_migration_report(self, users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create detailed user migration report.
        
        Args:
            users: List of Kissflow users
            
        Returns:
            Migration report with statistics and mappings
        """
        report = {
            'total_users': len(users),
            'role_distribution': {},
            'department_distribution': {},
            'active_users': 0,
            'inactive_users': 0,
            'users_with_manager': 0,
            'external_users': 0,
            'role_mappings': [],
            'warnings': []
        }
        
        for user in users:
            # Count by role
            role = user.get('Role', 'member')
            report['role_distribution'][role] = report['role_distribution'].get(role, 0) + 1
            
            # Count by department
            dept = user.get('Department', 'None')
            report['department_distribution'][dept] = report['department_distribution'].get(dept, 0) + 1
            
            # Count active/inactive
            if user.get('Status') == 'active':
                report['active_users'] += 1
            else:
                report['inactive_users'] += 1
            
            # Count users with managers
            if user.get('Manager'):
                report['users_with_manager'] += 1
            
            # Count external users
            if user.get('UserType') == 'external' or user.get('IsExternal'):
                report['external_users'] += 1
            
            # Check for missing short_text
            if not user.get('Email'):
                report['warnings'].append(f"User {user.get('Id')} has no email address")
        
        # Add role mapping summary
        for kissflow_role, count in report['role_distribution'].items():
            tallyfy_role = self.ROLE_MAPPING.get(kissflow_role.lower(), 'member')
            report['role_mappings'].append({
                'kissflow_role': kissflow_role,
                'tallyfy_role': tallyfy_role,
                'user_count': count
            })
        
        return report
    
    def transform_user_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user preferences and settings.
        
        Args:
            preferences: Kissflow user preferences
            
        Returns:
            Tallyfy user settings
        """
        return {
            'notifications': {
                "text": preferences.get('EmailNotifications', True),
                'in_app': preferences.get('InAppNotifications', True),
                'daily_digest': preferences.get('DailyDigest', False),
                'weekly_summary': preferences.get('WeeklySummary', False)
            },
            'locale': {
                'language': preferences.get('Language', 'en'),
                'timezone': preferences.get('TimeZone', 'UTC'),
                'date_format': preferences.get('DateFormat', 'MM/DD/YYYY'),
                'time_format': preferences.get('TimeFormat', '12h')
            },
            'ui_preferences': {
                'theme': 'light',  # Tallyfy default
                'compact_view': preferences.get('CompactView', False),
                'show_avatars': preferences.get('ShowAvatars', True)
            }
        }