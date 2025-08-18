#!/usr/bin/env python3
"""
Production-Grade Trello API Client
Implements actual Trello API v1 with proper authentication, rate limiting, and error handling
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime, timedelta
from urllib.parse import urlencode
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging


class TrelloRateLimitError(Exception):
    """Trello rate limit exceeded"""
    pass


class TrelloAuthError(Exception):
    """Trello authentication failed"""
    pass


class TrelloProductionClient:
    """
    Production Trello API client with actual endpoints
    Implements Trello REST API v1
    """
    
    BASE_URL = "https://api.trello.com/1"
    
    # Actual Trello rate limits
    RATE_LIMITS = {
        'per_token_per_interval': 300,  # 300 requests per 10 seconds per token
        'per_token_per_hour': 10000,    # 10,000 requests per hour per token
        'interval_seconds': 10,
        'burst_size': 100               # Can burst up to 100 requests
    }
    
    def __init__(self):
        """Initialize Trello client with actual authentication"""
        self.api_key = os.getenv('TRELLO_API_KEY')
        self.token = os.getenv('TRELLO_TOKEN')
        
        if not self.api_key or not self.token:
            raise TrelloAuthError("TRELLO_API_KEY and TRELLO_TOKEN required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting tracking
        self.request_timestamps = []
        self.hourly_requests = 0
        self.hour_start = datetime.now()
        
        self.logger = logging.getLogger(__name__)
    
    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters for requests"""
        return {
            'key': self.api_key,
            'token': self.token
        }
    
    def _check_rate_limit(self):
        """Check and enforce rate limits"""
        now = datetime.now()
        
        # Check hourly limit
        if now - self.hour_start > timedelta(hours=1):
            self.hourly_requests = 0
            self.hour_start = now
        
        if self.hourly_requests >= self.RATE_LIMITS['per_token_per_hour']:
            wait_time = 3600 - (now - self.hour_start).seconds
            self.logger.warning(f"Hourly rate limit reached. Waiting {wait_time}s")
            time.sleep(wait_time)
            self.hourly_requests = 0
            self.hour_start = datetime.now()
        
        # Check interval limit (10 second window)
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if now - ts < timedelta(seconds=self.RATE_LIMITS['interval_seconds'])
        ]
        
        if len(self.request_timestamps) >= self.RATE_LIMITS['per_token_per_interval']:
            wait_time = self.RATE_LIMITS['interval_seconds'] - (now - self.request_timestamps[0]).seconds
            if wait_time > 0:
                self.logger.info(f"Rate limit throttling: waiting {wait_time}s")
                time.sleep(wait_time)
                self.request_timestamps = []
        
        self.request_timestamps.append(now)
        self.hourly_requests += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, TrelloRateLimitError))
    )
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None) -> Any:
        """Make authenticated request to Trello API"""
        self._check_rate_limit()
        
        # Add authentication to params
        if params is None:
            params = {}
        params.update(self._get_auth_params())
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # Check for rate limit response
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise TrelloRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            if response.text:
                return response.json()
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise TrelloAuthError(f"Authentication failed: {e}")
            elif e.response.status_code == 404:
                return None
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL TRELLO API ENDPOINTS =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            member = self._make_request('GET', '/members/me', {'fields': 'id,username'})
            self.logger.info(f"Connected to Trello as {member.get('username')}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_member(self) -> Dict[str, Any]:
        """Get authenticated member details"""
        return self._make_request('GET', '/members/me')
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations (workspaces) for authenticated user"""
        params = {
            'fields': 'id,name,displayName,desc,url,website,logoHash,products',
            'memberships': 'all'
        }
        return self._make_request('GET', '/members/me/organizations', params)
    
    def get_boards(self, org_id: str = None) -> List[Dict[str, Any]]:
        """
        Get all boards (optionally filtered by organization)
        
        Args:
            org_id: Organization ID to filter boards
        """
        if org_id:
            endpoint = f'/organizations/{org_id}/boards'
        else:
            endpoint = '/members/me/boards'
        
        params = {
            'fields': 'id,name,desc,closed,idOrganization,pinned,url,shortUrl,dateLastActivity,dateLastView',
            'lists': 'open',
            'filter': 'open'
        }
        return self._make_request('GET', endpoint, params)
    
    def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get detailed board information"""
        params = {
            'fields': 'all',
            'actions': 'all',
            'action_fields': 'all',
            'actions_limit': 50,
            'cards': 'open',
            'card_fields': 'all',
            'card_attachments': True,
            'labels': 'all',
            'lists': 'open',
            'list_fields': 'all',
            'members': 'all',
            'member_fields': 'all',
            'checklists': 'all',
            'checklist_fields': 'all',
            'organization': True,
            'organization_fields': 'all'
        }
        return self._make_request('GET', f'/boards/{board_id}', params)
    
    def get_lists(self, board_id: str) -> List[Dict[str, Any]]:
        """Get all lists for a board"""
        params = {
            'cards': 'open',
            'card_fields': 'id,name,pos,due,dueComplete',
            'fields': 'id,name,closed,pos,subscribed'
        }
        return self._make_request('GET', f'/boards/{board_id}/lists', params)
    
    def get_cards(self, board_id: str = None, list_id: str = None) -> List[Dict[str, Any]]:
        """
        Get cards from board or list
        
        Args:
            board_id: Board ID to get all cards from
            list_id: List ID to get cards from specific list
        """
        if list_id:
            endpoint = f'/lists/{list_id}/cards'
        elif board_id:
            endpoint = f'/boards/{board_id}/cards'
        else:
            raise ValueError("Either board_id or list_id required")
        
        params = {
            'fields': 'all',
            'attachments': True,
            'attachment_fields': 'all',
            'members': True,
            'member_fields': 'all',
            'membersVoted': True,
            'checkItemStates': True,
            'checklists': 'all',
            'checklist_fields': 'all',
            'board': False,
            'list': True,
            'pluginData': True,
            'stickers': True,
            'sticker_fields': 'all',
            'customFieldItems': True
        }
        return self._make_request('GET', endpoint, params)
    
    def get_card(self, card_id: str) -> Dict[str, Any]:
        """Get detailed card information"""
        params = {
            'fields': 'all',
            'attachments': True,
            'attachment_fields': 'all',
            'members': True,
            'membersVoted': True,
            'checkItemStates': True,
            'checklists': 'all',
            'checklist_fields': 'all',
            'board': True,
            'list': True,
            'pluginData': True,
            'stickers': True,
            'customFieldItems': True,
            'actions': 'commentCard,updateCard:idList',
            'actions_limit': 1000
        }
        return self._make_request('GET', f'/cards/{card_id}', params)
    
    def get_card_actions(self, card_id: str, action_types: str = None) -> List[Dict[str, Any]]:
        """
        Get card activity/history
        
        Args:
            card_id: Card ID
            action_types: Comma-separated action types to filter
        """
        params = {
            'filter': action_types or 'all',
            'fields': 'all',
            'limit': 1000,
            'format': 'list',
            'memberCreator': True,
            'memberCreator_fields': 'all'
        }
        return self._make_request('GET', f'/cards/{card_id}/actions', params)
    
    def get_checklists(self, card_id: str) -> List[Dict[str, Any]]:
        """Get all checklists for a card"""
        params = {
            'checkItems': 'all',
            'checkItem_fields': 'all',
            'fields': 'all'
        }
        return self._make_request('GET', f'/cards/{card_id}/checklists', params)
    
    def get_custom_fields(self, board_id: str) -> List[Dict[str, Any]]:
        """Get custom field definitions for a board"""
        return self._make_request('GET', f'/boards/{board_id}/customFields')
    
    def get_labels(self, board_id: str) -> List[Dict[str, Any]]:
        """Get all labels for a board"""
        params = {
            'fields': 'all',
            'limit': 50
        }
        return self._make_request('GET', f'/boards/{board_id}/labels', params)
    
    def get_members(self, board_id: str) -> List[Dict[str, Any]]:
        """Get all members of a board"""
        params = {
            'fields': 'all',
            'organization': True,
            'organization_fields': 'all'
        }
        return self._make_request('GET', f'/boards/{board_id}/members', params)
    
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhooks for authenticated token"""
        return self._make_request('GET', f'/tokens/{self.token}/webhooks')
    
    def get_power_ups(self, board_id: str) -> List[Dict[str, Any]]:
        """Get enabled Power-Ups for a board"""
        return self._make_request('GET', f'/boards/{board_id}/boardPlugins')
    
    def get_butler_commands(self, board_id: str) -> List[Dict[str, Any]]:
        """Get Butler automation commands for a board"""
        try:
            # Butler commands are accessed through board commands endpoint
            return self._make_request('GET', f'/boards/{board_id}/commands')
        except:
            # Butler might not be enabled
            return []
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_cards(self, board_id: str, batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """
        Get cards in batches to handle large boards
        
        Args:
            board_id: Board ID
            batch_size: Number of cards per batch
            
        Yields:
            Batches of cards
        """
        # Get all lists first
        lists = self.get_lists(board_id)
        
        for list_item in lists:
            cards = self.get_cards(list_id=list_item['id'])
            
            # Yield in batches
            for i in range(0, len(cards), batch_size):
                yield cards[i:i + batch_size]
                
                # Small delay between batches
                time.sleep(0.5)
    
    def get_all_data(self, org_id: str = None, include_archived: bool = False) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Args:
            org_id: Optional organization ID to limit scope
            include_archived: Include archived boards/cards
            
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Trello data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'member': self.get_member(),
            'organizations': [],
            'boards': [],
            'total_cards': 0,
            'total_lists': 0,
            'total_members': set()
        }
        
        # Get organizations
        if org_id:
            orgs = [org for org in self.get_organizations() if org['id'] == org_id]
        else:
            orgs = self.get_organizations()
        
        data['organizations'] = orgs
        
        # Get boards for each organization
        for org in orgs:
            self.logger.info(f"Processing organization: {org['name']}")
            boards = self.get_boards(org['id'])
            
            for board in boards:
                if not include_archived and board.get('closed'):
                    continue
                
                self.logger.info(f"  Processing board: {board['name']}")
                
                # Get complete board data
                board_data = self.get_board(board['id'])
                
                # Get additional data not in board endpoint
                board_data['customFields'] = self.get_custom_fields(board['id'])
                board_data['powerUps'] = self.get_power_ups(board['id'])
                board_data['butlerCommands'] = self.get_butler_commands(board['id'])
                
                # Count totals
                data['total_cards'] += len(board_data.get('cards', []))
                data['total_lists'] += len(board_data.get('lists', []))
                
                # Collect unique members
                for member in board_data.get('members', []):
                    data['total_members'].add(member['id'])
                
                data['boards'].append(board_data)
                
                # Rate limit pause between boards
                time.sleep(1)
        
        # Convert set to count
        data['total_members'] = len(data['total_members'])
        
        self.logger.info(f"Export complete: {len(data['boards'])} boards, {data['total_cards']} cards")
        
        return data
    
    # ============= SEARCH OPERATIONS =============
    
    def search(self, query: str, model_types: str = 'all', board_ids: List[str] = None) -> Dict[str, Any]:
        """
        Search Trello using the search API
        
        Args:
            query: Search query
            model_types: Comma-separated types (cards,boards,organizations,members)
            board_ids: Limit search to specific boards
        """
        params = {
            'query': query,
            'modelTypes': model_types,
            'card_fields': 'all',
            'cards_limit': 1000,
            'board_fields': 'name,idOrganization',
            'boards_limit': 100,
            'organization_fields': 'name,displayName',
            'organizations_limit': 100,
            'member_fields': 'avatarHash,fullName,initials,username',
            'members_limit': 100
        }
        
        if board_ids:
            params['idBoards'] = ','.join(board_ids)
        
        return self._make_request('GET', '/search', params)
    
    # ============= PAGINATION SUPPORT =============
    
    def get_cards_paginated(self, board_id: str, limit: int = 50, 
                           before: str = None) -> Dict[str, Any]:
        """
        Get cards with pagination support
        
        Args:
            board_id: Board ID
            limit: Cards per page
            before: Card ID to get cards before (for pagination)
        """
        params = {
            'fields': 'all',
            'limit': limit
        }
        
        if before:
            params['before'] = before
        
        cards = self._make_request('GET', f'/boards/{board_id}/cards', params)
        
        return {
            'cards': cards,
            'has_more': len(cards) == limit,
            'last_id': cards[-1]['id'] if cards else None
        }
    
    def paginate_all_cards(self, board_id: str, page_size: int = 50) -> Generator[Dict, None, None]:
        """
        Paginate through all cards on a board
        
        Yields:
            Individual cards
        """
        before = None
        
        while True:
            page = self.get_cards_paginated(board_id, limit=page_size, before=before)
            
            for card in page['cards']:
                yield card
            
            if not page['has_more']:
                break
            
            before = page['last_id']
            time.sleep(0.1)  # Small delay between pages


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = TrelloProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Trello")
        
        # Get organizations
        orgs = client.get_organizations()
        print(f"Found {len(orgs)} organizations")
        
        if orgs:
            # Get boards for first organization
            boards = client.get_boards(orgs[0]['id'])
            print(f"Found {len(boards)} boards in {orgs[0]['name']}")
            
            if boards:
                # Get cards from first board
                cards = client.get_cards(boards[0]['id'])
                print(f"Found {len(cards)} cards in {boards[0]['name']}")
    
    print("\n✅ Production Trello client ready!")