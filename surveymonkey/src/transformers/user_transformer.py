"""
SurveyMonkey User Transformer
Transforms SurveyMonkey team/group members to Tallyfy users
"""

import logging
from typing import Dict, Any, List, Optional
import hashlib

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform SurveyMonkey users to Tallyfy users"""

    def __init__(self):
        """Initialize user transformer"""
        self.role_mapping = {
            'admin': 'admin',
            'power': 'admin',
            'full': 'member',
            'viewer': 'guest',
            'respondent': 'guest'
        }
        logger.info("SurveyMonkey user transformer initialized")

    def transform(self, member: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SurveyMonkey group member to Tallyfy user"""

        # Extract member details
        email = member.get('email', '')
        name = member.get('username', member.get('name', ''))
        role = member.get('type', member.get('role', 'viewer')).lower()

        # SurveyMonkey user info from /users/me or group members
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
                'source': 'surveymonkey',
                'surveymonkey_user_id': member.get('id'),
                'surveymonkey_role': role,
                'surveymonkey_username': member.get('username'),
                'group_id': member.get('group_id'),
                'date_created': member.get('date_created')
            }
        }

        # Add status
        status = member.get('status', 'active')
        user['status'] = 'active' if status == 'active' else 'inactive'

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
            return 'SurveyMonkey'

        parts = full_name.strip().split(' ')
        if len(parts) > 1:
            return ' '.join(parts[1:])
        return ''

    def _get_permissions(self, role: str) -> List[str]:
        """Get Tallyfy permissions based on SurveyMonkey role"""

        permission_map = {
            'admin': [
                'create_processes',
                'edit_processes',
                'delete_processes',
                'manage_users',
                'manage_billing',
                'view_analytics',
                'export_data'
            ],
            'power': [
                'create_processes',
                'edit_processes',
                'delete_processes',
                'manage_users',
                'view_analytics',
                'export_data'
            ],
            'full': [
                'create_processes',
                'edit_own_processes',
                'view_processes',
                'complete_tasks'
            ],
            'viewer': [
                'view_processes',
                'view_analytics'
            ],
            'respondent': [
                'view_own_processes'
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

    def transform_account(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SurveyMonkey account to Tallyfy organization"""

        # Account info from /users/me endpoint
        account_type = account_info.get('account_type', 'basic')

        return {
            'name': account_info.get('username', 'SurveyMonkey Account'),
            'subdomain': self._generate_subdomain(account_info.get('username', '')),
            'metadata': {
                'source': 'surveymonkey',
                'surveymonkey_user_id': account_info.get('id'),
                'surveymonkey_account_type': account_type,
                'date_created': account_info.get('date_created'),
                'date_last_login': account_info.get('date_last_login'),
                'language': account_info.get('language', 'en'),
                'first_name': account_info.get('first_name'),
                'last_name': account_info.get('last_name'),
                'email': account_info.get('email')
            },
            'settings': {
                'timezone': 'UTC',
                'language': account_info.get('language', 'en'),
                'date_format': 'MM/DD/YYYY',
                'time_format': '12h'
            }
        }

    def _generate_subdomain(self, username: str) -> str:
        """Generate valid subdomain from username"""
        if not username:
            return 'surveymonkey-migration'

        # Clean and format
        subdomain = username.lower()
        subdomain = ''.join(c if c.isalnum() or c == '-' else '-' for c in subdomain)
        subdomain = '-'.join(filter(None, subdomain.split('-')))

        # Ensure it starts with a letter
        if subdomain and not subdomain[0].isalpha():
            subdomain = 'sm-' + subdomain

        # Limit length
        if len(subdomain) > 30:
            subdomain = subdomain[:30]

        return subdomain or 'surveymonkey-migration'

    def extract_respondent_users(self, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract unique respondents as guest users from survey responses"""
        respondents = {}

        for response in responses:
            email = None
            name = None

            # Check custom variables
            custom_vars = response.get('custom_variables', {})
            if 'email' in custom_vars:
                email = custom_vars['email']
            if 'name' in custom_vars:
                name = custom_vars['name']
            if 'first_name' in custom_vars:
                name = custom_vars.get('first_name', '')
                if 'last_name' in custom_vars:
                    name += f" {custom_vars['last_name']}"

            # Check response metadata
            metadata = response.get('metadata', {})
            if metadata.get('respondent'):
                resp_meta = metadata['respondent']
                if not email and resp_meta.get('email'):
                    email = resp_meta['email']
                if not name and resp_meta.get('first_name'):
                    name = f"{resp_meta.get('first_name', '')} {resp_meta.get('last_name', '')}".strip()

            # Also check answers for email-type questions
            for page in response.get('pages', []):
                for question in page.get('questions', []):
                    for answer in question.get('answers', []):
                        # Check if answer looks like an email
                        text = answer.get('text', '')
                        if not email and '@' in text and '.' in text:
                            email = text

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
                        'source': 'surveymonkey_respondent',
                        'response_count': 1,
                        'first_response': response.get('date_created'),
                        'last_response': response.get('date_created')
                    },
                    'permissions': ['view_own_processes']
                }
            elif email and email in respondents:
                # Update response count
                respondents[email]['metadata']['response_count'] += 1
                respondents[email]['metadata']['last_response'] = response.get('date_created')

        return list(respondents.values())

    def analyze_user_activity(self, account_info: Dict[str, Any],
                            surveys: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user activity and engagement"""

        analysis = {
            'account_type': account_info.get('account_type', 'unknown'),
            'total_surveys': len(surveys),
            'date_last_login': account_info.get('date_last_login'),
            'survey_ownership': {},
            'survey_creation_pattern': {}
        }

        # Analyze survey creation patterns
        for survey in surveys:
            date_created = survey.get('date_created', '')
            if date_created:
                month = date_created[:7]  # YYYY-MM
                analysis['survey_creation_pattern'][month] = \
                    analysis['survey_creation_pattern'].get(month, 0) + 1

        return analysis
