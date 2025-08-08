"""
Pipefy GraphQL API Client
Handles all interactions with Pipefy's GraphQL API
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime
import requests
import backoff
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PipefyFieldType(Enum):
    """Pipefy field types enumeration"""
    SHORT_TEXT = "text"
    LONG_TEXT = "textarea"
    NUMBER = "text"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    DATETIME = "datetime"
    DUE_DATE = "due_date"
    EMAIL = "text"
    PHONE = "text"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "multiselect"
    CHECKLIST = "multiselect"
    ATTACHMENT = "attachment"
    ASSIGNEE_SELECT = "assignee_select"
    LABEL_SELECT = "label_select"
    CONNECTOR = "connector"
    STATEMENT = "statement"
    TIME = "time"
    CPF = "cpf"
    CNPJ = "cnpj"
    FORMULA = "formula"
    DYNAMIC_CONTENT = "dynamic_content"


@dataclass
class GraphQLResponse:
    """GraphQL response wrapper"""
    data: Optional[Dict[str, Any]]
    errors: Optional[List[Dict[str, Any]]]
    extensions: Optional[Dict[str, Any]]


class PipefyClient:
    """Client for interacting with Pipefy GraphQL API"""
    
    def __init__(self, api_token: str, api_url: str = "https://api.pipefy.com/graphql",
                 organization_id: Optional[str] = None):
        """
        Initialize Pipefy GraphQL client
        
        Args:
            api_token: Pipefy API token
            api_url: GraphQL endpoint URL
            organization_id: Optional organization ID to scope requests
        """
        self.api_token = api_token
        self.api_url = api_url
        self.organization_id = organization_id
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token,
            }',
            'Content-Type': 'application/json'
        })
        
        # Statistics
        self.stats = {
            'queries_executed': 0,
            'mutations_executed': 0,
            'errors': 0,
            'rate_limits_hit': 0,
            'total_items_fetched': {}
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.6  # ~100 requests per minute
        
        # Query fragments for reuse
        self.fragments = self._define_fragments()
    
    def _define_fragments(self) -> Dict[str, str]:
        """Define reusable GraphQL fragments"""
        return {
            'pipeFields': """
                fragment PipeFields on Pipe {
                    id
                    name
                    description
                    icon
                    color
                    public
                    anyone_can_create_card
                    created_at
                    updated_at
                    expiration_time_by_unit
                    expiration_unit
                }
            """,
            'phaseFields': """
                fragment PhaseFields on Phase {
                    id
                    name
                    description
                    done
                    cards_count
                    index
                    can_receive_card_directly_from_draft
                }
            """,
            'cardFields': """
                fragment CardFields on Card {
                    id
                    title
                    url
                    created_at
                    updated_at
                    finished_at
                    due_date
                    expired
                    late
                    done
                }
            """,
            'fieldFields': """
                fragment FieldFields on Field {
                    id
                    label
                    description
                    type
                    required
                    editable
                    options
                    help
                    minimal_view
                    custom_validation
                }
            """
        }
    
    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> GraphQLResponse:
        """
        Execute a GraphQL query
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            GraphQL response object
        """
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        logger.debug(f"Executing GraphQL query: {query[:100]}...")
        
        try:
            response = self.session.post(self.api_url, json=payload)
            self.last_request_time = time.time()
            self.stats['queries_executed'] += 1
            
            if response.status_code == 429:
                self.stats['rate_limits_hit'] += 1
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self.execute_query(query, variables)
            
            response.raise_for_status()
            
            result = response.json()
            
            if 'errors' in result:
                self.stats['errors'] += 1
                logger.error(f"GraphQL errors: {result['errors']}")
            
            return GraphQLResponse(
                data=result.get('data'),
                errors=result.get('errors'),
                extensions=result.get('extensions')
            )
            
        except requests.exceptions.RequestException as e:
            self.stats['errors'] += 1
            logger.error(f"Request failed: {e}")
            raise
    
    def execute_mutation(self, mutation: str, variables: Optional[Dict] = None) -> GraphQLResponse:
        """
        Execute a GraphQL mutation
        
        Args:
            mutation: GraphQL mutation string
            variables: Optional mutation variables
            
        Returns:
            GraphQL response object
        """
        self.stats['mutations_executed'] += 1
        return self.execute_query(mutation, variables)
    
    def get_organization(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get organization details
        
        Args:
            org_id: Organization ID (uses default if not provided)
            
        Returns:
            Organization data
        """
        org_id = org_id or self.organization_id
        
        query = """
            query GetOrganization($id: ID!) {
                organization(id: $id) {
                    id
                    name
                    created_at
                    billing_period
                    members_count
                    pipes_count
                    tables_count
                    only_admin_can_create_pipes
                    only_admin_can_invite_users
                }
            }
        """
        
        response = self.execute_query(query, {'id': org_id})
        
        if response.data:
            return response.data.get('organization', {})
        return {}
    
    def list_pipes(self) -> List[Dict[str, Any]]:
        """
        List all pipes in the organization
        
        Returns:
            List of pipe objects
        """
        query = """
            query ListPipes {
                pipes {
                    edges {
                        node {
                            ...PipeFields
                            phases {
                                ...PhaseFields
                            }
                            start_form_fields {
                                ...FieldFields
                            }
                            labels {
                                id
                                name
                                color
                            }
                            members {
                                user {
                                    id
                                    email
                                    name
                                }
                                role_name
                            }
                        }
                    }
                }
            }
        """ + ''.join(self.fragments.values())
        
        response = self.execute_query(query)
        
        pipes = []
        if response.data and 'pipes' in response.data:
            for edge in response.data['pipes'].get('edges', []):
                if edge.get('node'):
                    pipes.append(edge['node'])
        
        self.stats['total_items_fetched']['pipes'] = len(pipes)
        logger.info(f"Fetched {len(pipes)} pipes")
        
        return pipes
    
    def get_pipe(self, pipe_id: str) -> Dict[str, Any]:
        """
        Get detailed pipe information
        
        Args:
            pipe_id: Pipe ID
            
        Returns:
            Pipe data with all details
        """
        query = """
            query GetPipe($id: ID!) {
                pipe(id: $id) {
                    ...PipeFields
                    phases {
                        ...PhaseFields
                        fields {
                            ...FieldFields
                        }
                        cards_can_be_moved_to_phases {
                            id
                            name
                        }
                    }
                    start_form_fields {
                        ...FieldFields
                    }
                    labels {
                        id
                        name
                        color
                    }
                    members {
                        user {
                            id
                            email
                            name
                        }
                        role_name
                    }
                    preferences {
                        everyone_can_see
                        everyone_can_edit
                    }
                    summary {
                        total_cards_count
                        total_done_cards_count
                        total_late_cards_count
                        total_expired_cards_count
                    }
                }
            }
        """ + ''.join(self.fragments.values())
        
        response = self.execute_query(query, {'id': pipe_id})
        
        if response.data:
            return response.data.get('pipe', {})
        return {}
    
    def list_cards(self, pipe_id: str, first: int = 50, 
                   after: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        List cards in a pipe with pagination
        
        Args:
            pipe_id: Pipe ID
            first: Number of items per page (max 50)
            after: Cursor for pagination
            
        Yields:
            Card objects
        """
        query = """
            query ListCards($pipeId: ID!, $first: Int!, $after: String) {
                pipe(id: $pipeId) {
                    cards(first: $first, after: $after) {
                        edges {
                            node {
                                ...CardFields
                                current_phase {
                                    id
                                    name
                                }
                                assignees {
                                    id
                                    email
                                    name
                                }
                                labels {
                                    id
                                    name
                                    color
                                }
                                fields {
                                    field {
                                        id
                                        label
                                        type
                                    }
                                    value
                                    filled_at
                                    updated_at
                                }
                                comments {
                                    id
                                    text
                                    created_at
                                    author {
                                        id
                                        email
                                        name
                                    }
                                }
                                attachments {
                                    id
                                    filename
                                    url
                                    filesize
                                    created_at
                                }
                                phases_history {
                                    phase {
                                        id
                                        name
                                    }
                                    firstTimeIn
                                    lastTimeIn
                                    lastTimeOut
                                    duration
                                }
                                parent_relations {
                                    id
                                    cards {
                                        id
                                        title
                                    }
                                }
                                child_relations {
                                    id
                                    cards {
                                        id
                                        title
                                    }
                                }
                            }
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """ + self.fragments['cardFields']
        
        has_next = True
        cursor = after
        total_cards = 0
        
        while has_next:
            variables = {
                'pipeId': pipe_id,
                'first': min(first, 50),
                'after': cursor
            }
            
            response = self.execute_query(query, variables)
            
            if response.data and 'pipe' in response.data:
                cards_data = response.data['pipe'].get('cards', {})
                
                for edge in cards_data.get('edges', []):
                    if edge.get('node'):
                        yield edge['node']
                        total_cards += 1
                
                page_info = cards_data.get('pageInfo', {})
                has_next = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
            else:
                break
        
        self.stats['total_items_fetched']['cards'] = total_cards
        logger.info(f"Fetched {total_cards} cards from pipe {pipe_id}")
    
    def get_card(self, card_id: str) -> Dict[str, Any]:
        """
        Get detailed card information
        
        Args:
            card_id: Card ID
            
        Returns:
            Card data with all details
        """
        query = """
            query GetCard($id: ID!) {
                card(id: $id) {
                    ...CardFields
                    pipe {
                        id
                        name
                    }
                    current_phase {
                        id
                        name
                    }
                    assignees {
                        id
                        email
                        name
                    }
                    labels {
                        id
                        name
                        color
                    }
                    fields {
                        field {
                            id
                            label
                            type
                            options
                        }
                        value
                        array_value
                        filled_at
                        updated_at
                    }
                    comments {
                        id
                        text
                        created_at
                        author {
                            id
                            email
                            name
                        }
                    }
                    attachments {
                        id
                        filename
                        url
                        filesize
                        created_at
                        createdBy {
                            id
                            email
                            name
                        }
                    }
                    phases_history {
                        phase {
                            id
                            name
                        }
                        firstTimeIn
                        lastTimeIn
                        lastTimeOut
                        duration
                    }
                    parent_relations {
                        id
                        name
                        cards {
                            id
                            title
                            pipe {
                                id
                                name
                            }
                        }
                    }
                    child_relations {
                        id
                        name
                        cards {
                            id
                            title
                            pipe {
                                id
                                name
                            }
                        }
                    }
                }
            }
        """ + self.fragments['cardFields']
        
        response = self.execute_query(query, {'id': card_id})
        
        if response.data:
            return response.data.get('card', {})
        return {}
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """
        List all database tables in the organization
        
        Returns:
            List of table objects
        """
        query = """
            query ListTables {
                tables {
                    edges {
                        node {
                            id
                            name
                            description
                            public
                            authorization
                            create_record_button_label
                            title_field {
                                id
                                label
                            }
                            fields {
                                id
                                label
                                type
                                description
                                required
                                options
                            }
                            table_records_count
                            created_at
                            updated_at
                        }
                    }
                }
            }
        """
        
        response = self.execute_query(query)
        
        tables = []
        if response.data and 'tables' in response.data:
            for edge in response.data['tables'].get('edges', []):
                if edge.get('node'):
                    tables.append(edge['node'])
        
        self.stats['total_items_fetched']['tables'] = len(tables)
        logger.info(f"Fetched {len(tables)} tables")
        
        return tables
    
    def list_table_records(self, table_id: str, first: int = 50,
                          after: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        List records in a database table with pagination
        
        Args:
            table_id: Table ID
            first: Number of items per page (max 50)
            after: Cursor for pagination
            
        Yields:
            Table record objects
        """
        query = """
            query ListTableRecords($tableId: ID!, $first: Int!, $after: String) {
                table(id: $tableId) {
                    table_records(first: $first, after: $after) {
                        edges {
                            node {
                                id
                                title
                                created_at
                                updated_at
                                created_by {
                                    id
                                    email
                                    name
                                }
                                updated_by {
                                    id
                                    email
                                    name
                                }
                                record_fields {
                                    field {
                                        id
                                        label
                                        type
                                    }
                                    value
                                    array_value
                                    filled_at
                                    updated_at
                                }
                                parent_relations {
                                    id
                                    name
                                }
                            }
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """
        
        has_next = True
        cursor = after
        total_records = 0
        
        while has_next:
            variables = {
                'tableId': table_id,
                'first': min(first, 50),
                'after': cursor
            }
            
            response = self.execute_query(query, variables)
            
            if response.data and 'table' in response.data:
                records_data = response.data['table'].get('table_records', {})
                
                for edge in records_data.get('edges', []):
                    if edge.get('node'):
                        yield edge['node']
                        total_records += 1
                
                page_info = records_data.get('pageInfo', {})
                has_next = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
            else:
                break
        
        logger.info(f"Fetched {total_records} records from table {table_id}")
    
    def list_users(self) -> List[Dict[str, Any]]:
        """
        List all users in the organization
        
        Returns:
            List of user objects
        """
        query = """
            query ListUsers {
                organization {
                    members {
                        user {
                            id
                            email
                            name
                            username
                            avatar_url
                            created_at
                            locale
                            time_zone
                        }
                        role_name
                    }
                }
            }
        """
        
        response = self.execute_query(query)
        
        users = []
        if response.data and 'organization' in response.data:
            members = response.data['organization'].get('members', [])
            for member in members:
                user = member.get('user', {})
                user['role'] = member.get('role_name')
                users.append(user)
        
        self.stats['total_items_fetched']['users'] = len(users)
        logger.info(f"Fetched {len(users)} users")
        
        return users
    
    def get_webhooks(self, pipe_id: str) -> List[Dict[str, Any]]:
        """
        Get webhooks for a pipe
        
        Args:
            pipe_id: Pipe ID
            
        Returns:
            List of webhook objects
        """
        query = """
            query GetWebhooks($pipeId: ID!) {
                pipe(id: $pipeId) {
                    webhooks {
                        id
                        name
                        url
                        email
                        headers
                        actions
                    }
                }
            }
        """
        
        response = self.execute_query(query, {'pipeId': pipe_id})
        
        if response.data and 'pipe' in response.data:
            return response.data['pipe'].get('webhooks', [])
        return []
    
    def bulk_import_cards(self, pipe_id: str, cards_data: List[Dict]) -> Dict[str, Any]:
        """
        Bulk import cards using cardsImporter mutation
        
        Args:
            pipe_id: Target pipe ID
            cards_data: List of card data dictionaries
            
        Returns:
            Import result
        """
        mutation = """
            mutation BulkImportCards($pipeId: ID!, $cards: [CardInput!]!) {
                cardsImporter(pipe_id: $pipeId, cards: $cards) {
                    clientMutationId
                    cardsImported
                }
            }
        """
        
        # Transform cards data to match CardInput type
        formatted_cards = []
        for card in cards_data:
            formatted_card = {
                'title': card.get('title'),
                'due_date': card.get('due_date'),
                'assignee_ids': card.get('assignee_ids', []),
                'label_ids': card.get('label_ids', []),
                'phase_id': card.get('phase_id'),
                'fields_attributes': card.get('fields', [])
            }
            formatted_cards.append(formatted_card)
        
        variables = {
            'pipeId': pipe_id,
            'cards': formatted_cards
        }
        
        response = self.execute_mutation(mutation, variables)
        
        if response.data:
            return response.data.get('cardsImporter', {})
        return {}
    
    def create_card(self, pipe_id: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a single card
        
        Args:
            pipe_id: Target pipe ID
            card_data: Card data dictionary
            
        Returns:
            Created card data
        """
        mutation = """
            mutation CreateCard($pipeId: ID!, $input: CardInput!) {
                createCard(input: {
                    pipe_id: $pipeId,
                    title: $input.title,
                    due_date: $input.due_date,
                    assignee_ids: $input.assignee_ids,
                    label_ids: $input.label_ids,
                    phase_id: $input.phase_id,
                    fields_attributes: $input.fields_attributes
                }) {
                    card {
                        id
                        title
                        url
                    }
                }
            }
        """
        
        variables = {
            'pipeId': pipe_id,
            'input': card_data
        }
        
        response = self.execute_mutation(mutation, variables)
        
        if response.data:
            return response.data.get('createCard', {}).get('card', {})
        return {}
    
    def move_card_to_phase(self, card_id: str, phase_id: str) -> bool:
        """
        Move a card to a different phase
        
        Args:
            card_id: Card ID
            phase_id: Target phase ID
            
        Returns:
            Success status
        """
        mutation = """
            mutation MoveCard($cardId: ID!, $phaseId: ID!) {
                moveCardToPhase(input: {
                    card_id: $cardId,
                    destination_phase_id: $phaseId
                }) {
                    card {
                        id
                        current_phase {
                            id
                            name
                        }
                    }
                }
            }
        """
        
        variables = {
            'cardId': card_id,
            'phaseId': phase_id
        }
        
        response = self.execute_mutation(mutation, variables)
        
        return response.data is not None and 'moveCardToPhase' in response.data
    
    def update_card_field(self, card_id: str, field_id: str, value: Any) -> bool:
        """
        Update a card field value
        
        Args:
            card_id: Card ID
            field_id: Field ID
            value: New field value
            
        Returns:
            Success status
        """
        mutation = """
            mutation UpdateCardField($cardId: ID!, $fieldId: ID!, $value: String) {
                updateCardField(input: {
                    card_id: $cardId,
                    field_id: $fieldId,
                    value: $value
                }) {
                    card {
                        id
                    }
                }
            }
        """
        
        # Convert value to string if needed
        if not isinstance(value, str):
            value = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
        
        variables = {
            'cardId': card_id,
            'fieldId': field_id,
            'value': value
        }
        
        response = self.execute_mutation(mutation, variables)
        
        return response.data is not None and 'updateCardField' in response.data
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get client statistics
        
        Returns:
            Statistics dictionary
        """
        return self.stats.copy()
    
    def introspect_schema(self) -> Dict[str, Any]:
        """
        Introspect the GraphQL schema
        
        Returns:
            Schema introspection data
        """
        query = """
            query IntrospectionQuery {
                __schema {
                    types {
                        name
                        kind
                        fields {
                            name
                            type {
                                name
                                kind
                            }
                        }
                    }
                }
            }
        """
        
        response = self.execute_query(query)
        
        if response.data:
            return response.data.get('__schema', {})
        return {}