#!/usr/bin/env python3
"""
Production-Grade Monday.com API Client
Implements actual Monday.com GraphQL API with proper authentication, rate limiting, and error handling
"""

import os
import time
import json
import requests
from typing import Dict, List, Any, Optional, Generator, Union
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
from enum import Enum
from dataclasses import dataclass


class MondayRateLimitError(Exception):
    """Monday.com rate limit exceeded"""
    pass


class MondayAuthError(Exception):
    """Monday.com authentication failed"""
    pass


class MondayComplexityError(Exception):
    """Query complexity exceeded"""
    pass


class MondayColumnType(str, Enum):
    """Monday.com column types - 30+ types"""
    TEXT = "text"
    LONG_TEXT = "long-text"
    STATUS = "status"
    PERSON = "person"
    PEOPLE = "people"
    DATE = "date"
    TIMELINE = "timeline"
    TAGS = "tags"
    NUMBERS = "numbers"
    CHECKBOX = "checkbox"
    RATING = "rating"
    LINK = "link"
    EMAIL = "email"
    PHONE = "phone"
    LOCATION = "location"
    COUNTRY = "country"
    COLOR_PICKER = "color-picker"
    DROPDOWN = "dropdown"
    WEEK = "week"
    WORLD_CLOCK = "world-clock"
    VOTE = "vote"
    CREATION_LOG = "creation-log"
    LAST_UPDATED = "last-updated"
    AUTO_NUMBER = "auto-number"
    BUTTON = "button"
    DEPENDENCY = "dependency"
    PROGRESS = "progress"
    HOUR = "hour"
    FORMULA = "formula"
    MIRROR = "mirror"
    TIME_TRACKING = "time-tracking"
    FILE = "file"
    BOARD_RELATION = "board-relation"
    DOC = "doc"
    SUBITEMS = "subitems"


@dataclass
class MondayComplexity:
    """Track query complexity for Monday.com API"""
    query_cost: int = 0
    reset_at: datetime = None
    remaining: int = 10000000  # 10M complexity points per minute
    
    def update(self, headers: Dict):
        """Update complexity from response headers"""
        if 'X-Complexity-Query' in headers:
            self.query_cost = int(headers['X-Complexity-Query'])
        if 'X-Complexity-Remaining' in headers:
            self.remaining = int(headers['X-Complexity-Remaining'])
        if 'X-Complexity-Reset' in headers:
            self.reset_at = datetime.fromtimestamp(int(headers['X-Complexity-Reset']))


class MondayProductionClient:
    """
    Production Monday.com API client with actual endpoints
    Implements Monday.com GraphQL API v2
    """
    
    BASE_URL = "https://api.monday.com/v2"
    FILE_UPLOAD_URL = "https://api.monday.com/v2/file"
    
    # Monday.com rate limits (complexity-based)
    COMPLEXITY_LIMITS = {
        'per_minute': 10000000,  # 10M complexity points per minute
        'single_query_max': 5000000  # 5M max for single query
    }
    
    def __init__(self):
        """Initialize Monday.com client with actual authentication"""
        self.api_key = os.getenv('MONDAY_API_KEY')
        
        if not self.api_key:
            raise MondayAuthError("MONDAY_API_KEY required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.api_key,
            'API-Version': '2024-01',
            'Content-Type': 'application/json'
        })
        
        # Complexity tracking
        self.complexity = MondayComplexity()
        
        # Cache for frequently used data
        self.board_cache = {}
        self.user_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_complexity(self, estimated_cost: int = 1000):
        """Check if we have enough complexity points"""
        if self.complexity.remaining < estimated_cost:
            if self.complexity.reset_at:
                wait_time = (self.complexity.reset_at - datetime.now()).seconds
                if wait_time > 0:
                    self.logger.warning(f"Complexity limit reached. Waiting {wait_time}s")
                    time.sleep(wait_time)
                    self.complexity.remaining = self.COMPLEXITY_LIMITS['per_minute']
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, MondayRateLimitError))
    )
    def _make_request(self, query: str, variables: Dict = None) -> Any:
        """Make GraphQL request to Monday.com API"""
        self._check_complexity()
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        try:
            response = self.session.post(
                self.BASE_URL,
                json=payload,
                timeout=30
            )
            
            # Update complexity tracking
            self.complexity.update(response.headers)
            
            # Check for rate limit
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise MondayRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Check for errors in response
            if 'errors' in result:
                error_msg = result['errors'][0].get('message', 'Unknown error')
                
                if 'complexity' in error_msg.lower():
                    raise MondayComplexityError(f"Query too complex: {error_msg}")
                elif 'authentication' in error_msg.lower():
                    raise MondayAuthError(f"Authentication failed: {error_msg}")
                else:
                    raise Exception(f"API error: {error_msg}")
            
            return result.get('data', {})
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise MondayAuthError(f"Authentication failed: {e}")
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL MONDAY.COM API QUERIES =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        query = """
        query {
            me {
                id
                name
                email
            }
        }
        """
        
        try:
            result = self._make_request(query)
            user = result.get('me', {})
            self.logger.info(f"Connected to Monday.com as {user.get('name')}")
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_current_user(self) -> Dict[str, Any]:
        """Get authenticated user details"""
        query = """
        query {
            me {
                id
                name
                email
                url
                photo_thumb
                title
                birthday
                country_code
                location
                mobile_phone
                phone
                time_zone_identifier
                enabled
                created_at
                account {
                    id
                    name
                    slug
                    tier
                    plan {
                        period
                        tier
                        version
                    }
                }
                teams {
                    id
                    name
                }
            }
        }
        """
        
        result = self._make_request(query)
        return result.get('me', {})
    
    def get_workspaces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all workspaces"""
        query = """
        query ($limit: Int!) {
            workspaces(limit: $limit) {
                id
                name
                kind
                description
                created_at
            }
        }
        """
        
        result = self._make_request(query, {'limit': limit})
        return result.get('workspaces', [])
    
    def get_boards(self, workspace_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get boards, optionally filtered by workspace"""
        if workspace_id:
            query = """
            query ($workspace_id: Int!, $limit: Int!) {
                boards(workspace_ids: [$workspace_id], limit: $limit) {
                    id
                    name
                    description
                    state
                    board_folder_id
                    board_kind
                    owner {
                        id
                        name
                    }
                    workspace {
                        id
                        name
                    }
                    columns {
                        id
                        title
                        type
                        settings_str
                    }
                    groups {
                        id
                        title
                        color
                        position
                    }
                }
            }
            """
            variables = {'workspace_id': workspace_id, 'limit': limit}
        else:
            query = """
            query ($limit: Int!) {
                boards(limit: $limit) {
                    id
                    name
                    description
                    state
                    board_folder_id
                    board_kind
                    owner {
                        id
                        name
                    }
                    workspace {
                        id
                        name
                    }
                    columns {
                        id
                        title
                        type
                        settings_str
                    }
                    groups {
                        id
                        title
                        color
                        position
                    }
                }
            }
            """
            variables = {'limit': limit}
        
        result = self._make_request(query, variables)
        boards = result.get('boards', [])
        
        # Cache boards
        for board in boards:
            self.board_cache[board['id']] = board
        
        return boards
    
    def get_board(self, board_id: Union[str, int]) -> Dict[str, Any]:
        """Get detailed board information"""
        # Check cache first
        board_id = str(board_id)
        if board_id in self.board_cache:
            return self.board_cache[board_id]
        
        query = """
        query ($board_id: [ID!]) {
            boards(ids: $board_id) {
                id
                name
                description
                state
                board_folder_id
                board_kind
                permissions
                tags
                owner {
                    id
                    name
                    email
                }
                workspace {
                    id
                    name
                    kind
                }
                columns {
                    id
                    title
                    type
                    settings_str
                    description
                    archived
                }
                groups {
                    id
                    title
                    color
                    position
                    archived
                }
                views {
                    id
                    name
                    type
                    settings_str
                }
                activity_logs {
                    id
                    event
                    data
                    created_at
                }
            }
        }
        """
        
        result = self._make_request(query, {'board_id': board_id})
        boards = result.get('boards', [])
        
        if boards:
            board = boards[0]
            self.board_cache[board_id] = board
            return board
        
        return None
    
    def get_items(self, board_id: Union[str, int], limit: int = 100, 
                 page: int = 1) -> Dict[str, Any]:
        """Get items from a board with pagination"""
        query = """
        query ($board_id: ID!, $limit: Int!, $page: Int!) {
            boards(ids: [$board_id]) {
                items_page(limit: $limit, page: $page) {
                    cursor
                    items {
                        id
                        name
                        state
                        created_at
                        updated_at
                        creator {
                            id
                            name
                        }
                        group {
                            id
                            title
                        }
                        column_values {
                            id
                            type
                            text
                            value
                        }
                        subitems {
                            id
                            name
                            column_values {
                                id
                                text
                                value
                            }
                        }
                        assets {
                            id
                            name
                            url
                            file_size
                            uploaded_by {
                                id
                                name
                            }
                        }
                        updates {
                            id
                            body
                            created_at
                            creator {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = self._make_request(query, {
            'board_id': str(board_id),
            'limit': limit,
            'page': page
        })
        
        boards = result.get('boards', [])
        if boards:
            items_page = boards[0].get('items_page', {})
            return {
                'items': items_page.get('items', []),
                'cursor': items_page.get('cursor'),
                'has_more': items_page.get('cursor') is not None
            }
        
        return {'items': [], 'cursor': None, 'has_more': False}
    
    def get_item(self, item_id: Union[str, int]) -> Dict[str, Any]:
        """Get detailed item information"""
        query = """
        query ($item_id: [ID!]) {
            items(ids: $item_id) {
                id
                name
                state
                board {
                    id
                    name
                }
                group {
                    id
                    title
                }
                created_at
                updated_at
                creator {
                    id
                    name
                    email
                }
                column_values {
                    id
                    title
                    type
                    text
                    value
                    additional_info
                }
                subitems {
                    id
                    name
                    state
                    column_values {
                        id
                        text
                        value
                    }
                }
                assets {
                    id
                    name
                    url
                    file_size
                    file_extension
                    uploaded_by {
                        id
                        name
                    }
                }
                updates {
                    id
                    body
                    text_body
                    created_at
                    updated_at
                    creator {
                        id
                        name
                    }
                    replies {
                        id
                        body
                        created_at
                        creator {
                            id
                            name
                        }
                    }
                }
                subscribers {
                    id
                    name
                }
            }
        }
        """
        
        result = self._make_request(query, {'item_id': str(item_id)})
        items = result.get('items', [])
        return items[0] if items else None
    
    def get_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all users in account"""
        query = """
        query ($limit: Int!) {
            users(limit: $limit) {
                id
                name
                email
                url
                photo_thumb
                title
                birthday
                country_code
                location
                mobile_phone
                phone
                time_zone_identifier
                enabled
                created_at
                teams {
                    id
                    name
                }
            }
        }
        """
        
        result = self._make_request(query, {'limit': limit})
        users = result.get('users', [])
        
        # Cache users
        for user in users:
            self.user_cache[user['id']] = user
        
        return users
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams in account"""
        query = """
        query {
            teams {
                id
                name
                picture_url
                users {
                    id
                    name
                }
            }
        }
        """
        
        result = self._make_request(query)
        return result.get('teams', [])
    
    def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags in account"""
        query = """
        query {
            tags {
                id
                name
                color
            }
        }
        """
        
        result = self._make_request(query)
        return result.get('tags', [])
    
    def get_automations(self, board_id: Union[str, int]) -> List[Dict[str, Any]]:
        """Get automations for a board"""
        query = """
        query ($board_id: ID!) {
            boards(ids: [$board_id]) {
                id
                name
            }
        }
        """
        
        # Note: Automations require additional API endpoint
        # This is a placeholder - full automation API requires separate implementation
        result = self._make_request(query, {'board_id': str(board_id)})
        return []
    
    def get_integrations(self, board_id: Union[str, int]) -> List[Dict[str, Any]]:
        """Get integrations for a board"""
        # Similar to automations, integrations require separate API
        return []
    
    def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhooks"""
        query = """
        query {
            webhooks {
                id
                board_id
                url
                event
                config
            }
        }
        """
        
        result = self._make_request(query)
        return result.get('webhooks', [])
    
    # ============= SEARCH OPERATIONS =============
    
    def search_items(self, query_text: str, board_ids: List[Union[str, int]] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """Search for items across boards"""
        if board_ids:
            query = """
            query ($query_text: String!, $board_ids: [ID!], $limit: Int!) {
                items_page_by_column_values(
                    board_ids: $board_ids,
                    columns: [{column_id: "name", column_values: [$query_text]}],
                    limit: $limit
                ) {
                    items {
                        id
                        name
                        board {
                            id
                            name
                        }
                        group {
                            id
                            title
                        }
                        column_values {
                            id
                            text
                            value
                        }
                    }
                }
            }
            """
            variables = {
                'query_text': query_text,
                'board_ids': [str(bid) for bid in board_ids],
                'limit': limit
            }
        else:
            # Search all boards (more complex query)
            query = """
            query ($limit: Int!) {
                boards(limit: 100) {
                    id
                    name
                    items(limit: $limit) {
                        id
                        name
                        column_values {
                            id
                            text
                        }
                    }
                }
            }
            """
            variables = {'limit': limit}
        
        result = self._make_request(query, variables)
        
        # Process search results
        if board_ids:
            items_page = result.get('items_page_by_column_values', {})
            return items_page.get('items', [])
        else:
            # Manual filtering for global search
            items = []
            for board in result.get('boards', []):
                for item in board.get('items', []):
                    if query_text.lower() in item['name'].lower():
                        item['board'] = {'id': board['id'], 'name': board['name']}
                        items.append(item)
            return items
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_items(self, board_id: Union[str, int], 
                       batch_size: int = 100) -> Generator[List[Dict], None, None]:
        """
        Get items in batches to handle large boards
        
        Args:
            board_id: Board ID
            batch_size: Number of items per batch
            
        Yields:
            Batches of items
        """
        page = 1
        
        while True:
            response = self.get_items(board_id, limit=batch_size, page=page)
            items = response.get('items', [])
            
            if not items:
                break
            
            yield items
            
            if not response.get('has_more'):
                break
            
            page += 1
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self, workspace_id: int = None) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Args:
            workspace_id: Workspace to export (optional)
            
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Monday.com data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'account': self.get_current_user().get('account', {}),
            'workspaces': [],
            'boards': [],
            'users': [],
            'teams': [],
            'tags': [],
            'total_items': 0,
            'total_boards': 0
        }
        
        # Get users
        self.logger.info("Fetching users...")
        data['users'] = self.get_users()
        
        # Get teams
        self.logger.info("Fetching teams...")
        data['teams'] = self.get_teams()
        
        # Get tags
        self.logger.info("Fetching tags...")
        data['tags'] = self.get_tags()
        
        # Get workspaces
        if workspace_id:
            workspaces = [ws for ws in self.get_workspaces() if ws['id'] == str(workspace_id)]
        else:
            workspaces = self.get_workspaces()
        
        data['workspaces'] = workspaces
        
        # Get boards
        self.logger.info("Fetching boards...")
        if workspace_id:
            boards = self.get_boards(workspace_id=workspace_id)
        else:
            boards = self.get_boards()
        
        for board in boards:
            self.logger.info(f"Processing board: {board['name']}")
            
            # Get full board details
            board_data = self.get_board(board['id'])
            
            # Get items
            board_data['items'] = []
            item_count = 0
            
            for item_batch in self.batch_get_items(board['id']):
                board_data['items'].extend(item_batch)
                item_count += len(item_batch)
                
                # Rate limit pause
                time.sleep(1)
            
            data['total_items'] += item_count
            data['boards'].append(board_data)
            data['total_boards'] += 1
            
            self.logger.info(f"  Processed {item_count} items")
        
        self.logger.info(f"Export complete: {data['total_boards']} boards, {data['total_items']} items")
        
        return data
    
    # ============= COLUMN VALUE HELPERS =============
    
    def parse_column_value(self, column_type: str, value: Any) -> Any:
        """
        Parse column value based on type
        Monday.com stores values as JSON strings
        """
        if not value:
            return None
        
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except:
                return value
        
        # Parse based on column type
        if column_type == MondayColumnType.STATUS.value:
            return value.get('label') if isinstance(value, dict) else value
        
        elif column_type == MondayColumnType.PERSON.value:
            if isinstance(value, dict) and 'personsAndTeams' in value:
                persons = value['personsAndTeams']
                if persons:
                    return persons[0].get('id')
            return None
        
        elif column_type == MondayColumnType.PEOPLE.value:
            if isinstance(value, dict) and 'personsAndTeams' in value:
                return [p.get('id') for p in value['personsAndTeams']]
            return []
        
        elif column_type == MondayColumnType.DATE.value:
            if isinstance(value, dict):
                return value.get('date')
            return value
        
        elif column_type == MondayColumnType.TIMELINE.value:
            if isinstance(value, dict):
                return {
                    'from': value.get('from'),
                    'to': value.get('to')
                }
            return None
        
        elif column_type == MondayColumnType.TAGS.value:
            if isinstance(value, dict) and 'tag_ids' in value:
                return value['tag_ids']
            return []
        
        elif column_type == MondayColumnType.NUMBERS.value:
            if isinstance(value, (int, float, str)):
                try:
                    return float(value)
                except:
                    return None
            return None
        
        elif column_type == MondayColumnType.CHECKBOX.value:
            if isinstance(value, dict):
                return value.get('checked') == 'true'
            return False
        
        elif column_type == MondayColumnType.LINK.value:
            if isinstance(value, dict):
                return {
                    'url': value.get('url'),
                    'text': value.get('text')
                }
            return value
        
        elif column_type == MondayColumnType.FORMULA.value:
            # Formulas are read-only, return computed value
            return value
        
        elif column_type == MondayColumnType.MIRROR.value:
            # Mirror columns reference other items
            if isinstance(value, dict) and 'linkedPulseIds' in value:
                return value['linkedPulseIds']
            return []
        
        else:
            # Default: return as-is
            return value
    
    def format_column_value(self, column_type: str, value: Any) -> str:
        """
        Format value for writing to Monday.com
        Returns JSON string format expected by API
        """
        if value is None:
            return ""
        
        if column_type == MondayColumnType.STATUS.value:
            return json.dumps({'label': str(value)})
        
        elif column_type == MondayColumnType.PERSON.value:
            if isinstance(value, (str, int)):
                return json.dumps({'personsAndTeams': [{'id': int(value), 'kind': 'person'}]})
            return ""
        
        elif column_type == MondayColumnType.PEOPLE.value:
            if isinstance(value, list):
                persons = [{'id': int(p), 'kind': 'person'} for p in value]
                return json.dumps({'personsAndTeams': persons})
            return ""
        
        elif column_type == MondayColumnType.DATE.value:
            return json.dumps({'date': str(value)})
        
        elif column_type == MondayColumnType.TIMELINE.value:
            if isinstance(value, dict):
                return json.dumps({
                    'from': value.get('from'),
                    'to': value.get('to')
                })
            return ""
        
        elif column_type == MondayColumnType.TAGS.value:
            if isinstance(value, list):
                return json.dumps({'tag_ids': value})
            return ""
        
        elif column_type == MondayColumnType.NUMBERS.value:
            return str(value)
        
        elif column_type == MondayColumnType.CHECKBOX.value:
            return json.dumps({'checked': 'true' if value else 'false'})
        
        elif column_type == MondayColumnType.LINK.value:
            if isinstance(value, dict):
                return json.dumps({
                    'url': value.get('url', ''),
                    'text': value.get('text', '')
                })
            elif isinstance(value, str):
                return json.dumps({'url': value, 'text': value})
            return ""
        
        else:
            # Default: convert to string
            return str(value)
    
    # ============= CREATE OPERATIONS =============
    
    def create_board(self, name: str, board_kind: str = 'public', 
                    workspace_id: int = None) -> Dict[str, Any]:
        """Create a new board"""
        mutation = """
        mutation ($name: String!, $board_kind: BoardKind!, $workspace_id: ID) {
            create_board(
                board_name: $name,
                board_kind: $board_kind,
                workspace_id: $workspace_id
            ) {
                id
                name
            }
        }
        """
        
        variables = {
            'name': name,
            'board_kind': board_kind
        }
        
        if workspace_id:
            variables['workspace_id'] = workspace_id
        
        result = self._make_request(mutation, variables)
        return result.get('create_board', {})
    
    def create_item(self, board_id: Union[str, int], item_name: str, 
                   group_id: str = None, column_values: Dict = None) -> Dict[str, Any]:
        """Create a new item on a board"""
        mutation = """
        mutation ($board_id: ID!, $item_name: String!, $group_id: String, $column_values: JSON) {
            create_item(
                board_id: $board_id,
                item_name: $item_name,
                group_id: $group_id,
                column_values: $column_values
            ) {
                id
                name
            }
        }
        """
        
        # Format column values for API
        if column_values:
            formatted_values = {}
            board = self.get_board(board_id)
            
            for column in board.get('columns', []):
                col_id = column['id']
                if col_id in column_values:
                    formatted_values[col_id] = self.format_column_value(
                        column['type'], 
                        column_values[col_id]
                    )
            
            column_values = json.dumps(formatted_values)
        
        variables = {
            'board_id': str(board_id),
            'item_name': item_name,
            'group_id': group_id,
            'column_values': column_values
        }
        
        result = self._make_request(mutation, variables)
        return result.get('create_item', {})
    
    def create_webhook(self, board_id: Union[str, int], url: str, 
                      event: str = 'change_column_value') -> Dict[str, Any]:
        """Create webhook for board"""
        mutation = """
        mutation ($board_id: ID!, $url: String!, $event: WebhookEventType!) {
            create_webhook(
                board_id: $board_id,
                url: $url,
                event: $event
            ) {
                id
                board_id
            }
        }
        """
        
        variables = {
            'board_id': str(board_id),
            'url': url,
            'event': event
        }
        
        result = self._make_request(mutation, variables)
        return result.get('create_webhook', {})


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = MondayProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Monday.com")
        
        # Get current user
        user = client.get_current_user()
        print(f"User: {user.get('name')}")
        print(f"Account: {user.get('account', {}).get('name')}")
        
        # Get workspaces
        workspaces = client.get_workspaces()
        print(f"Found {len(workspaces)} workspaces")
        
        # Get boards
        boards = client.get_boards(limit=10)
        print(f"Found {len(boards)} boards")
        
        if boards:
            board = boards[0]
            print(f"\nBoard: {board['name']}")
            print(f"Columns: {len(board.get('columns', []))}")
            
            # Parse column types
            for column in board.get('columns', []):
                print(f"  - {column['title']}: {column['type']}")
            
            # Get items
            response = client.get_items(board['id'], limit=5)
            items = response.get('items', [])
            print(f"\nFound {len(items)} items")
            
            if items:
                item = items[0]
                print(f"Item: {item['name']}")
                
                # Parse column values
                for col_val in item.get('column_values', []):
                    parsed = client.parse_column_value(col_val['type'], col_val.get('value'))
                    print(f"  - {col_val.get('id')}: {parsed}")
    
    print("\n✅ Production Monday.com client ready!")