"""Monday.com GraphQL API client for migration."""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Generator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class MondayClient:
    """Client for interacting with Monday.com GraphQL API v2."""
    
    # GraphQL endpoint
    API_URL = "https://api.monday.com/v2"
    
    # Complexity limits
    MAX_COMPLEXITY_PER_MINUTE = 10_000_000  # 10M per minute per account
    MAX_COMPLEXITY_PER_QUERY = 5_000_000    # 5M per single query
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 500  # Max items per page
    
    def __init__(self, api_token: str):
        """Initialize Monday.com client.
        
        Args:
            api_token: Monday.com personal API token v2
        """
        self.api_token = api_token
        self.session = self._create_session()
        self.complexity_used = 0
        self.complexity_reset_time = None
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'Authorization': self.api_token,
            
            'Content-Type': 'application/json',
            'API-Version': '2024-01'  # Latest API version
        })
        
        return session
    
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query with complexity tracking.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            Query response data
        """
        # Add complexity field to track usage
        if 'complexity' not in query:
            query = query.replace('{', '{ complexity { query reset_in_x_seconds }', 1)
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        response = self.session.post(self.API_URL, json=payload)
        
        # Handle rate limiting
        if response.status_code == 429:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 60))
            logger.warning(f"Rate limited. Waiting {reset_time} seconds...")
            time.sleep(reset_time)
            return self.execute_query(query, variables)
        
        response.raise_for_status()
        data = response.json()
        
        # Track complexity
        if 'complexity' in data.get('data', {}):
            complexity_info = data['data']['complexity']
            self.complexity_used = complexity_info.get('query', 0)
            reset_in = complexity_info.get('reset_in_x_seconds', 60)
            
            logger.debug(f"Query complexity: {self.complexity_used}, Reset in: {reset_in}s")
            
            # Remove complexity from response
            del data['data']['complexity']
        
        # Check for errors
        if 'errors' in data:
            error_msg = '; '.join([e.get('message', 'Unknown error') for e in data['errors']])
            raise Exception(f"GraphQL Error: {error_msg}")
        
        return data.get('data', {})
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and get account info.
        
        Returns:
            Account information
        """
        query = """
        query {
            me {
                id
                name
                email
                account {
                    id
                    name
                    tier
                    max_users
                }
            }
        }
        """
        
        result = self.execute_query(query)
        logger.info(f"Connected to Monday.com as: {result['me']['name']}")
        return result['me']
    
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces in the account.
        
        Returns:
            List of workspace objects
        """
        query = """
        query {
            workspaces {
                id
                name
                kind
                description
                created_at
                settings {
                    icon
                    color
                }
            }
        }
        """
        
        result = self.execute_query(query)
        return result.get('workspaces', [])
    
    def get_boards(self, workspace_id: Optional[int] = None,
                  limit: int = 100) -> Generator[Dict[str, Any], None, None]:
        """Get boards with pagination.
        
        Args:
            workspace_id: Optional workspace filter
            limit: Maximum number of boards
            
        Yields:
            Board objects
        """
        query = """
        query GetBoards($limit: Int!, $page: Int, $workspace_ids: [ID]) {
            boards(
                limit: $limit
                page: $page
                workspace_ids: $workspace_ids
            ) {
                id
                name
                description
                board_kind
                state
                workspace_id
                permissions
                tags
                groups {
                    id
                    title
                    color
                    position
                }
                columns {
                    id
                    title
                    type
                    settings_str
                    description
                }
                views {
                    id
                    name
                    type
                    settings_str
                }
                owner {
                    id
                    name
                    email
                }
                created_at
                updated_at
            }
        }
        """
        
        page = 1
        boards_yielded = 0
        
        while boards_yielded < limit:
            variables = {
                'limit': min(25, limit - boards_yielded),  # Max 25 boards per query
                'page': page,
                'workspace_ids': [str(workspace_id)] if workspace_id else None
            }
            
            result = self.execute_query(query, variables)
            boards = result.get('boards', [])
            
            if not boards:
                break
            
            for board in boards:
                yield board
                boards_yielded += 1
                if boards_yielded >= limit:
                    return
            
            page += 1
    
    def get_board_items(self, board_id: int,
                       limit: int = 1000) -> Generator[Dict[str, Any], None, None]:
        """Get items from a board with pagination.
        
        Args:
            board_id: Board ID
            limit: Maximum number of items
            
        Yields:
            Item objects with column values
        """
        query = """
        query GetBoardItems($board_id: ID!, $limit: Int!, $cursor: String) {
            boards(ids: [$board_id]) {
                items_page(
                    limit: $limit
                    cursor: $cursor
                ) {
                    cursor
                    items {
                        id
                        name
                        state
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
                                type
                                text
                                value
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
                        created_at
                        updated_at
                        creator {
                            id
                            name
                            email
                        }
                    }
                }
            }
        }
        """
        
        cursor = None
        items_yielded = 0
        
        while items_yielded < limit:
            variables = {
                'board_id': board_id,
                'limit': min(self.DEFAULT_PAGE_SIZE, limit - items_yielded),
                'cursor': cursor
            }
            
            result = self.execute_query(query, variables)
            
            if not result.get('boards'):
                break
            
            items_page = result['boards'][0].get('items_page', {})
            items = items_page.get('items', [])
            
            if not items:
                break
            
            for item in items:
                yield item
                items_yielded += 1
                if items_yielded >= limit:
                    return
            
            cursor = items_page.get('cursor')
            if not cursor:
                break
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users in the account.
        
        Returns:
            List of user objects
        """
        query = """
        query {
            users {
                id
                name
                email
                title
                phone
                location
                photo_thumb
                is_admin
                is_guest
                is_pending
                is_view_only
                enabled
                created_at
                teams {
                    id
                    name
                }
            }
        }
        """
        
        result = self.execute_query(query)
        return result.get('users', [])
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams in the account.
        
        Returns:
            List of team objects
        """
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
                owners {
                    id
                    name
                }
            }
        }
        """
        
        result = self.execute_query(query)
        return result.get('teams', [])
    
    def get_automations(self, board_id: int) -> List[Dict[str, Any]]:
        """Get automations for a board.
        
        Args:
            board_id: Board ID
            
        Returns:
            List of automation objects
        """
        # Note: Automations API is limited, this gets basic info
        query = """
        query GetAutomations($board_id: ID!) {
            boards(ids: [$board_id]) {
                id
                name
            }
        }
        """
        
        # Automations are not fully exposed via API
        # Would need to document for manual recreation
        logger.warning("Automation details not fully available via API - will document for manual recreation")
        return []
    
    def get_workdocs(self, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get WorkDocs from the account.
        
        Args:
            workspace_id: Optional workspace filter
            
        Returns:
            List of WorkDoc objects
        """
        query = """
        query GetWorkDocs($workspace_id: ID) {
            docs(workspace_ids: [$workspace_id]) {
                id
                name
                kind
                url
                created_at
                created_by {
                    id
                    name
                }
                doc_folder_id
                doc_kind
                workspace {
                    id
                    name
                }
            }
        }
        """
        
        variables = {'workspace_id': workspace_id} if workspace_id else {}
        result = self.execute_query(query, variables)
        return result.get('docs', [])
    
    def get_column_value_options(self, board_id: int, column_id: str) -> List[Dict[str, Any]]:
        """Get options for dropdown/status columns.
        
        Args:
            board_id: Board ID
            column_id: Column ID
            
        Returns:
            List of options for the column
        """
        query = """
        query GetColumnOptions($board_id: ID!) {
            boards(ids: [$board_id]) {
                columns {
                    id
                    title
                    type
                    settings_str
                }
            }
        }
        """
        
        result = self.execute_query(query, {'board_id': board_id})
        
        if not result.get('boards'):
            return []
        
        for column in result['boards'][0].get('columns', []):
            if column['id'] == column_id:
                settings = json.loads(column.get('settings_str', '{}'))
                
                # Extract options based on column type
                if column['type'] == 'status':
                    return [{'label': label, 'index': idx} 
                           for idx, label in settings.get('labels', {}).items()]
                elif column['type'] == 'dropdown':
                    return settings.get('labels', [])
        
        return []
    
    def get_board_activity(self, board_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activity log for a board.
        
        Args:
            board_id: Board ID
            limit: Maximum number of activities
            
        Returns:
            List of activity objects
        """
        query = """
        query GetBoardActivity($board_id: ID!, $limit: Int!) {
            boards(ids: [$board_id]) {
                activity_logs(limit: $limit) {
                    id
                    event
                    data
                    entity
                    created_at
                    user {
                        id
                        name
                    }
                }
            }
        }
        """
        
        result = self.execute_query(query, {'board_id': board_id, 'limit': limit})
        
        if not result.get('boards'):
            return []
        
        return result['boards'][0].get('activity_logs', [])
    
    def create_webhook(self, board_id: int, url: str, event: str) -> Dict[str, Any]:
        """Create a webhook for board events.
        
        Args:
            board_id: Board ID
            url: Webhook URL
            event: Event type
            
        Returns:
            Webhook object
        """
        mutation = """
        mutation CreateWebhook($board_id: ID!, $url: String!, $event: WebhookEventType!) {
            create_webhook(
                board_id: $board_id
                url: $url
                event: $event
            ) {
                id
                board_id
            }
        }
        """
        
        variables = {
            'board_id': board_id,
            "text": url,
            'event': event
        }
        
        result = self.execute_query(mutation, variables)
        return result.get('create_webhook', {})
    
    def wait_for_complexity_reset(self):
        """Wait if approaching complexity limit."""
        if self.complexity_used > self.MAX_COMPLEXITY_PER_MINUTE * 0.8:
            wait_time = 60  # Wait full minute for reset
            logger.warning(f"Approaching complexity limit ({self.complexity_used}/{self.MAX_COMPLEXITY_PER_MINUTE}). Waiting {wait_time}s...")
            time.sleep(wait_time)
            self.complexity_used = 0