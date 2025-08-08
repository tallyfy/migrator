"""
User Transformer for RocketLane to Tallyfy Migration
Handles customer, user, and team transformations with paradigm shifts
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib
import os

logger = logging.getLogger(__name__)


class UserTransformer:
    """Transform RocketLane users, customers, and teams to Tallyfy entities"""
    
    def __init__(self, ai_client=None):
        """
        Initialize user transformer
        
        Args:
            ai_client: Optional AI client for complex decisions
        """
        self.ai_client = ai_client
        self.portal_handling = os.getenv('CUSTOMER_PORTAL_HANDLING', 'guest_users')
        
        self.transformation_stats = {
            'users_total': 0,
            'users_successful': 0,
            'customers_total': 0,
            'customers_as_guests': 0,
            'customers_as_orgs': 0,
            'teams_created': 0,
            'ai_decisions': 0
        }
        
        # Track mappings for relationships
        self.user_id_map = {}
        self.customer_id_map = {}
        self.team_id_map = {}
    
    def transform_internal_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RocketLane internal user to Tallyfy member
        
        Args:
            user: RocketLane user object
            
        Returns:
            Tallyfy user structure
        """
        self.transformation_stats['users_total'] += 1
        
        # Determine role based on RocketLane permissions
        tallyfy_role = self._determine_tallyfy_role(user)
        
        # Create Tallyfy user structure
        tallyfy_user = {
            'email': user.get('email'),
            'firstname': user.get('first_name', ''),
            'lastname': user.get('last_name', ''),
            'role': tallyfy_role,
            'metadata': {
                'source': 'rocketlane',
                'original_id': user.get('id'),
                'original_role': user.get('role'),
                'department': user.get('department'),
                'title': user.get('job_title'),
                'skills': user.get('skills', []),
                'capacity_hours': user.get('capacity_hours_per_week')
            },
            'active': user.get('active', True)
        }
        
        # Add phone if available
        if user.get('phone'):
            tallyfy_user['phone'] = user['phone']
        
        # Add timezone if available
        if user.get('timezone'):
            tallyfy_user['timezone'] = user['timezone']
        
        # Add avatar URL if available
        if user.get('avatar_url'):
            tallyfy_user['avatar_url'] = user['avatar_url']
        
        # Store mapping
        self.user_id_map[user['id']] = tallyfy_user['email']
        
        self.transformation_stats['users_successful'] += 1
        return tallyfy_user
    
    def transform_customer(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RocketLane customer based on portal handling strategy
        
        Args:
            customer: RocketLane customer object
            
        Returns:
            Tallyfy entity (guest or organization)
        """
        self.transformation_stats['customers_total'] += 1
        
        # Determine handling strategy
        strategy = self._determine_customer_strategy(customer)
        
        if strategy == 'guest_users':
            result = self._transform_to_guest_user(customer)
            self.transformation_stats['customers_as_guests'] += 1
        elif strategy == 'organizations':
            result = self._transform_to_organization(customer)
            self.transformation_stats['customers_as_orgs'] += 1
        else:
            # Fallback to guest
            result = self._transform_to_guest_user(customer)
            self.transformation_stats['customers_as_guests'] += 1
        
        return result
    
    def _determine_customer_strategy(self, customer: Dict[str, Any]) -> str:
        """Determine how to handle customer transformation"""
        # Check if AI should make decision
        if self.ai_client and self.ai_client.enabled:
            try:
                decision = self.ai_client.analyze_customer_portal_usage(customer)
                if decision and decision.get('confidence', 0) > 0.7:
                    self.transformation_stats['ai_decisions'] += 1
                    return decision.get('strategy', self.portal_handling)
            except Exception as e:
                logger.warning(f"AI customer decision failed: {e}")
        
        # Fallback to configuration or heuristics
        if customer.get('portal_users_count', 0) > 5:
            # Multiple portal users suggests organization
            return 'organizations'
        elif customer.get('portal_access_enabled'):
            # Single portal access suggests guest
            return 'guest_users'
        else:
            # Use configured default
            return self.portal_handling
    
    def _transform_to_guest_user(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Transform customer to Tallyfy guest user"""
        # Get primary contact
        primary_contact = self._get_primary_contact(customer)
        
        guest_user = {
            'type': 'guest',
            'email': primary_contact.get('email'),
            'name': primary_contact.get('name', customer.get('name', 'Guest')),
            'company': customer.get('company_name') or customer.get('name'),
            'metadata': {
                'source': 'rocketlane_customer',
                'original_id': customer.get('id'),
                'tier': customer.get('tier'),
                'industry': customer.get('industry'),
                'portal_enabled': customer.get('portal_access_enabled', False),
                'value': customer.get('total_value'),
                'created_at': customer.get('created_at')
            }
        }
        
        # Add phone if available
        if primary_contact.get('phone'):
            guest_user['phone'] = primary_contact['phone']
        
        # Map additional contacts as notes
        if customer.get('contacts') and len(customer['contacts']) > 1:
            additional_contacts = []
            for contact in customer['contacts']:
                if contact.get('email') != primary_contact.get('email'):
                    additional_contacts.append({
                        'name': contact.get('name'),
                        'email': contact.get('email'),
                        'role': contact.get('role'),
                        'phone': contact.get('phone')
                    })
            guest_user['metadata']['additional_contacts'] = additional_contacts
        
        # Store mapping
        self.customer_id_map[customer['id']] = f"guest_{customer['id']}"
        
        return guest_user
    
    def _transform_to_organization(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Transform customer to Tallyfy organization"""
        organization = {
            'type': 'organization',
            'name': customer.get('company_name') or customer.get('name'),
            'subdomain': self._generate_subdomain(customer),
            'metadata': {
                'source': 'rocketlane_customer',
                'original_id': customer.get('id'),
                'tier': customer.get('tier'),
                'industry': customer.get('industry'),
                'value': customer.get('total_value'),
                'created_at': customer.get('created_at')
            },
            'members': []
        }
        
        # Add customer contacts as organization members
        for contact in customer.get('contacts', []):
            member = {
                'email': contact.get('email'),
                'name': contact.get('name'),
                'role': 'member',  # Default role in customer org
                'metadata': {
                    'original_role': contact.get('role'),
                    'is_primary': contact.get('is_primary', False)
                }
            }
            organization['members'].append(member)
        
        # Store mapping
        self.customer_id_map[customer['id']] = f"org_{customer['id']}"
        
        return organization
    
    def _get_primary_contact(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Get primary contact from customer"""
        contacts = customer.get('contacts', [])
        
        # Look for explicitly marked primary
        for contact in contacts:
            if contact.get('is_primary'):
                return contact
        
        # Look for owner/admin role
        for contact in contacts:
            if contact.get('role', '').lower() in ['owner', 'admin', 'primary']:
                return contact
        
        # Return first contact or default
        if contacts:
            return contacts[0]
        
        # Fallback to customer-level email
        return {
            'email': customer.get('email', f"customer_{customer.get('id')}@example.com"),
            'name': customer.get('name', 'Customer')
        }
    
    def _generate_subdomain(self, customer: Dict[str, Any]) -> str:
        """Generate subdomain for customer organization"""
        name = customer.get('company_name') or customer.get('name', 'customer')
        
        # Clean and format subdomain
        subdomain = name.lower()
        subdomain = ''.join(c if c.isalnum() else '-' for c in subdomain)
        subdomain = subdomain.strip('-')[:50]
        
        # Add hash suffix to ensure uniqueness
        hash_suffix = hashlib.md5(str(customer.get('id')).encode()).hexdigest()[:6]
        
        return f"{subdomain}-{hash_suffix}"
    
    def transform_team(self, team: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RocketLane team to Tallyfy group
        
        Args:
            team: RocketLane team object
            
        Returns:
            Tallyfy group structure
        """
        self.transformation_stats['teams_created'] += 1
        
        group = {
            'name': team.get('name', 'Team'),
            'description': team.get('description', ''),
            'metadata': {
                'source': 'rocketlane',
                'original_id': team.get('id'),
                'team_lead': team.get('lead_id'),
                'department': team.get('department'),
                'skills': team.get('skills', [])
            },
            'members': []
        }
        
        # Add team members
        for member_id in team.get('member_ids', []):
            if member_id in self.user_id_map:
                group['members'].append(self.user_id_map[member_id])
        
        # Store mapping
        self.team_id_map[team['id']] = f"team_{team['id']}"
        
        return group
    
    def _determine_tallyfy_role(self, user: Dict[str, Any]) -> str:
        """Determine Tallyfy role based on RocketLane permissions"""
        rl_role = user.get('role', '').lower()
        permissions = user.get('permissions', [])
        
        # Direct role mapping
        role_map = {
            'admin': 'admin',
            'administrator': 'admin',
            'owner': 'owner',
            'manager': 'admin',
            'project_manager': 'member',
            'team_lead': 'member',
            'member': 'member',
            'user': 'member',
            'viewer': 'guest',
            'readonly': 'guest',
            'guest': 'guest'
        }
        
        # Check permissions for elevated access
        admin_permissions = ['manage_users', 'manage_projects', 'manage_billing']
        if any(perm in permissions for perm in admin_permissions):
            return 'admin'
        
        return role_map.get(rl_role, 'member')
    
    def transform_users_batch(self, users: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Transform batch of users, customers, and teams
        
        Args:
            users: List of mixed user types
            
        Returns:
            Dictionary with categorized transformations
        """
        result = {
            'members': [],
            'guests': [],
            'organizations': [],
            'groups': []
        }
        
        for entity in users:
            entity_type = entity.get('type', 'user')
            
            try:
                if entity_type == 'customer':
                    transformed = self.transform_customer(entity)
                    if transformed['type'] == 'guest':
                        result['guests'].append(transformed)
                    elif transformed['type'] == 'organization':
                        result['organizations'].append(transformed)
                
                elif entity_type == 'team':
                    result['groups'].append(self.transform_team(entity))
                
                else:  # Regular user
                    result['members'].append(self.transform_internal_user(entity))
                    
            except Exception as e:
                logger.error(f"Failed to transform {entity_type} {entity.get('id')}: {e}")
        
        return result
    
    def get_id_mappings(self) -> Dict[str, Dict[str, str]]:
        """Get all ID mappings for reference"""
        return {
            'users': self.user_id_map.copy(),
            'customers': self.customer_id_map.copy(),
            'teams': self.team_id_map.copy()
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get transformation statistics"""
        return self.transformation_stats.copy()