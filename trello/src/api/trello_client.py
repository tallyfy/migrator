"""
Trello API Client
Handles all interactions with Trello REST API
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TrelloClient:
    """Client for Trello API"""
    
    def __init__(self, api_key: str, api_token: str):
        """Initialize Trello client"""
        self.api_key = api_key
        self.api_token = api_token
        self.base_url = "https://api.trello.com/1"
        
        self.session = requests.Session()
        self.params = {
            'key': api_key,
            'token': api_token
        }
        
        logger.info("Trello client initialized")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth params
        if 'params' in kwargs:
            kwargs['params'].update(self.params)
        else:
            kwargs['params'] = self.params
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return {'success': True}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    # Board Management
    def get_boards(self) -> List[Dict[str, Any]]:
        """Get all boards for authenticated user"""
        return self._make_request('GET', '/members/me/boards')
    
    def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get board details"""
        return self._make_request('GET', f'/boards/{board_id}')
    
    def get_lists(self, board_id: str) -> List[Dict[str, Any]]:
        """Get lists on a board"""
        return self._make_request('GET', f'/boards/{board_id}/lists')
    
    def get_cards(self, board_id: str) -> List[Dict[str, Any]]:
        """Get all cards on a board"""
        params = {
            'attachments': True,
            'checklists': 'all',
            'customFieldItems': True,
            'members': True
        }
        return self._make_request('GET', f'/boards/{board_id}/cards', params=params)
    
    def get_card(self, card_id: str) -> Dict[str, Any]:
        """Get card details"""
        params = {
            'attachments': True,
            'checklists': 'all',
            'customFieldItems': True,
            'members': True,
            'actions': 'commentCard'
        }
        return self._make_request('GET', f'/cards/{card_id}', params=params)
    
    def get_card_actions(self, card_id: str) -> List[Dict[str, Any]]:
        """Get card activities/comments"""
        return self._make_request('GET', f'/cards/{card_id}/actions', 
                                 params={'filter': 'commentCard,updateCard'})
    
    def get_checklists(self, card_id: str) -> List[Dict[str, Any]]:
        """Get card checklists"""
        return self._make_request('GET', f'/cards/{card_id}/checklists')
    
    # Members
    def get_board_members(self, board_id: str) -> List[Dict[str, Any]]:
        """Get board members"""
        return self._make_request('GET', f'/boards/{board_id}/members')
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get organizations/workspaces"""
        return self._make_request('GET', '/members/me/organizations')
    
    def get_organization_members(self, org_id: str) -> List[Dict[str, Any]]:
        """Get organization members"""
        return self._make_request('GET', f'/organizations/{org_id}/members')
    
    # Custom Fields
    def get_custom_fields(self, board_id: str) -> List[Dict[str, Any]]:
        """Get custom fields for board"""
        return self._make_request('GET', f'/boards/{board_id}/customFields')
    
    # Labels
    def get_labels(self, board_id: str) -> List[Dict[str, Any]]:
        """Get board labels"""
        return self._make_request('GET', f'/boards/{board_id}/labels')
    
    # Discovery
    def discover_workspace(self) -> Dict[str, Any]:
        """Discover complete workspace"""
        discovery = {
            'timestamp': datetime.utcnow().isoformat(),
            'statistics': {},
            'boards': []
        }
        
        # Get boards
        boards = self.get_boards()
        discovery['statistics']['boards'] = len(boards)
        
        total_cards = 0
        total_lists = 0
        
        for board in boards[:10]:  # Limit for discovery
            lists = self.get_lists(board['id'])
            cards = self.get_cards(board['id'])
            
            total_lists += len(lists)
            total_cards += len(cards)
            
            discovery['boards'].append({
                'id': board['id'],
                'name': board['name'],
                'lists': len(lists),
                'cards': len(cards)
            })
        
        discovery['statistics']['lists'] = total_lists
        discovery['statistics']['cards'] = total_cards
        
        # Get organizations
        orgs = self.get_organizations()
        discovery['statistics']['organizations'] = len(orgs)
        
        return discovery
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            self._make_request('GET', '/members/me')
            logger.info("Trello API connection successful")
            return True
        except Exception as e:
            logger.error(f"Trello API connection failed: {e}")
            return False