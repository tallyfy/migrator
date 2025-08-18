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
        """Make API request with rate limit handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth params
        if 'params' in kwargs:
            kwargs['params'].update(self.params)
        else:
            kwargs['params'] = self.params
        
        for attempt in range(3):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Handle rate limiting (300 req/10s per key, 100 req/10s per token)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('X-Rate-Limit-RetryAfter', 10))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    import time
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                if response.status_code == 204:
                    return {'success': True}
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    logger.error(f"API request failed after 3 attempts: {e}")
                    raise
                import time
                time.sleep(2 ** attempt)
    
    # Board Management
    def get_boards(self, filter: str = 'open') -> List[Dict[str, Any]]:
        """Get all boards for authenticated user"""
        params = {
            'filter': filter,  # open, closed, all
            'fields': 'id,name,desc,closed,dateLastActivity,memberships',
            'lists': 'open'
        }
        return self._make_request('GET', '/members/me/boards', params=params)
    
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
            member = self._make_request('GET', '/members/me')
            logger.info(f"✅ Trello API connection successful - User: {member.get('username')}")
            return True
        except Exception as e:
            logger.error(f"❌ Trello API connection failed: {e}")
            return False
    
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhooks for the token"""
        return self._make_request('GET', f'/tokens/{self.api_token}/webhooks')
    
    def get_board_actions(self, board_id: str, filter: str = 'all', limit: int = 50) -> List[Dict[str, Any]]:
        """Get board activity/actions"""
        params = {
            'filter': filter,
            'limit': limit
        }
        return self._make_request('GET', f'/boards/{board_id}/actions', params=params)
    
    def get_card_attachments(self, card_id: str) -> List[Dict[str, Any]]:
        """Get card attachments"""
        return self._make_request('GET', f'/cards/{card_id}/attachments')
    
    def get_list(self, list_id: str) -> Dict[str, Any]:
        """Get list details"""
        return self._make_request('GET', f'/lists/{list_id}')
    
    def get_list_cards(self, list_id: str) -> List[Dict[str, Any]]:
        """Get cards in a list"""
        return self._make_request('GET', f'/lists/{list_id}/cards')