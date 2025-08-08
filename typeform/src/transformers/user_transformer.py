"""
Typeform User Transformer
Transforms Typeform workspace members to Tallyfy users
"""

import logging
from typing import Dict, Any, List, Optional
import hashlib

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform Typeform users to Tallyfy users"""
    
    def __init__(self):
        """Initialize user transformer"""
        self.role_mapping = {
            'owner': 'admin',
            'admin': 'admin', 
            'contributor': 'member',
            'viewer': 'guest',
            'custom': 'member'
        }
        logger.info("Typeform user transformer initialized")
    
    def transform(self, member: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Typeform workspace member to Tallyfy user"""
        
        # Extract member details
        email = member.get('email', '')
        name = member.get('name', member.get('alias', ''))
        role = member.get('role', 'viewer').lower()
        
        # If no name, derive from email
        if not name and email:
            name = email.split('@')[0].replace('.', ' ').title()
        
        # Map role
        tallyfy_role = self.role_mapping.get(role, 'guest')
        
        # Create user object
        user = {
            'email': email,
            'first_name': self._extract_first_name(name),
            'last_name': self._extract_last_name(name),
            'role': tallyfy_role,
            'metadata': {
                'source': 'typeform',
                'typeform_user_id': member.get('user_id'),
                'typeform_role': role,
                'typeform_alias': member.get('alias'),
                'workspace_id': member.get('workspace_id'),
                'joined_at': member.get('joined_at')
            }
        }
        
        # Add status
        if member.get('status'):
            user['status'] = 'active' if member['status'] == 'active' else 'inactive'
        else:
            user['status'] = 'active'
        
        # Add permissions based on role
        user['permissions'] = self._get_permissions(role)
        
        return user
    
    def _extract_first_name(self, full_name: str) -> str:
        """Extract first name from full name"""
        if not full_name:
            return 'User'
        
        parts = full_name.strip().split(' ')
        return parts[0] if parts else 'User'
    
    def _extract_last_name(self, full_name: str) -> str:
        """Extract last name from full name"""
        if not full_name:
            return 'Typeform'
        
        parts = full_name.strip().split(' ')
        if len(parts) > 1:
            return ' '.join(parts[1:])
        return ''
    
    def _get_permissions(self, role: str) -> List[str]:
        """Get Tallyfy permissions based on Typeform role"""
        
        permission_map = {
            'owner': [
                'create_processes',
                'edit_processes',
                'delete_processes',
                'manage_users',
                'manage_billing',
                'view_analytics',
                'export_data'
            ],
            'admin': [
                'create_processes',
                'edit_processes',
                'delete_processes',
                'manage_users',
                'view_analytics',
                'export_data'
            ],
            'contributor': [
                'create_processes',
                'edit_own_processes',
                'view_processes',
                'complete_tasks'
            ],
            'viewer': [
                'view_processes',
                'view_analytics'
            ],
            'custom': [
                'view_processes',
                'complete_tasks'
            ]
        }
        
        return permission_map.get(role, ['view_processes'])
    
    def transform_batch(self, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform multiple members"""
        users = []
        
        for member in members:
            try:
                user = self.transform(member)
                users.append(user)
                logger.info(f"Transformed user: {user['email']}")
            except Exception as e:
                logger.error(f"Failed to transform member {member.get('email')}: {e}")
        
        return users
    
    def transform_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Typeform workspace to Tallyfy organization"""
        
        return {
            'name': workspace.get('name', 'Typeform Workspace'),
            'subdomain': self._generate_subdomain(workspace.get('name', '')),
            'metadata': {
                'source': 'typeform',
                'typeform_workspace_id': workspace.get('id'),
                'typeform_account_id': workspace.get('account_id'),
                'created_at': workspace.get('created_at'),
                'plan': workspace.get('plan', {}).get('name'),
                'features': workspace.get('features', [])
            },
            'settings': {
                'timezone': workspace.get('timezone', 'UTC'),
                'language': workspace.get('language', 'en'),
                'date_format': 'MM/DD/YYYY',
                'time_format': '12h'
            }
        }
    
    def _generate_subdomain(self, workspace_name: str) -> str:
        """Generate valid subdomain from workspace name"""
        if not workspace_name:
            return 'typeform-migration'
        
        # Clean and format
        subdomain = workspace_name.lower()
        subdomain = ''.join(c if c.isalnum() or c == '-' else '-' for c in subdomain)
        subdomain = '-'.join(filter(None, subdomain.split('-')))
        
        # Ensure it starts with a letter
        if subdomain and not subdomain[0].isalpha():
            subdomain = 'tf-' + subdomain
        
        # Limit length
        if len(subdomain) > 30:
            subdomain = subdomain[:30]
        
        return subdomain or 'typeform-migration'
    
    def extract_respondent_users(self, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract unique respondents as guest users"""
        respondents = {}
        
        for response in responses:
            # Check hidden fields for email
            hidden = response.get('hidden', {})
            metadata = response.get('metadata', {})
            
            email = None
            name = None
            
            # Try to find email
            if 'email' in hidden:
                email = hidden['email']
            elif 'user_email' in hidden:
                email = hidden['user_email']
            
            # Try to find name
            if 'name' in hidden:
                name = hidden['name']
            elif 'user_name' in hidden:
                name = hidden['user_name']
            
            # Also check answers for email fields
            for answer in response.get('answers', []):
                if answer.get('type') == 'email' and answer.get('email'):
                    if not email:
                        email = answer['email']
            
            # Create guest user if we have email
            if email and email not in respondents:
                if not name:
                    name = email.split('@')[0].replace('.', ' ').title()
                
                respondents[email] = {
                    'email': email,
                    'first_name': self._extract_first_name(name),
                    'last_name': self._extract_last_name(name),
                    'role': 'guest',
                    'status': 'active',
                    'metadata': {
                        'source': 'typeform_respondent',
                        'response_count': 1,
                        'first_response': response.get('submitted_at'),
                        'last_response': response.get('submitted_at')
                    },
                    'permissions': ['view_own_processes']
                }
            elif email in respondents:
                # Update response count
                respondents[email]['metadata']['response_count'] += 1
                respondents[email]['metadata']['last_response'] = response.get('submitted_at')
        
        return list(respondents.values())
    
    def analyze_user_activity(self, members: List[Dict[str, Any]], 
                            forms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user activity and engagement"""
        
        analysis = {
            'total_users': len(members),
            'role_distribution': {},
            'active_users': 0,
            'form_ownership': {},
            'collaboration_score': 0
        }
        
        # Count roles
        for member in members:
            role = member.get('role', 'viewer')
            analysis['role_distribution'][role] = \
                analysis['role_distribution'].get(role, 0) + 1
            
            if member.get('status') == 'active':
                analysis['active_users'] += 1
        
        # Analyze form ownership
        for form in forms:
            owner = form.get('created_by', {}).get('email')
            if owner:
                analysis['form_ownership'][owner] = \
                    analysis['form_ownership'].get(owner, 0) + 1
        
        # Calculate collaboration score
        if len(members) > 1 and forms:
            unique_creators = len(set(f.get('created_by', {}).get('email', '') 
                                     for f in forms if f.get('created_by')))
            analysis['collaboration_score'] = \
                (unique_creators / len(members)) * 100 if members else 0
        
        return analysis