#!/usr/bin/env python3
"""
Production-Grade Pipefy API Client
Implements actual Pipefy GraphQL API with proper authentication, rate limiting, and error handling
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


class PipefyRateLimitError(Exception):
    """Pipefy rate limit exceeded"""
    pass


class PipefyAuthError(Exception):
    """Pipefy authentication failed"""
    pass


class PipefyFieldType(str, Enum):
    """Pipefy field types"""
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    DUE_DATE = "due_date"
    CURRENCY = "currency"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    EMAIL = "email"
    PHONE = "phone"
    CPFCNPJ = "cpfcnpj"  # Brazilian tax ID
    ASSIGNEE_SELECT = "assignee_select"
    LABEL_SELECT = "label_select"
    ATTACHMENT = "attachment"
    CHECKLIST = "checklist"
    CONNECTION = "connection"
    DATABASE_CONNECTION = "database_connection"
    STATEMENT = "statement"
    TIME = "time"
    ID = "id"


class PipefyPhaseType(str, Enum):
    """Pipefy phase types"""
    START = "start"
    NORMAL = "normal"
    DONE = "done"


@dataclass
class PipefyRateLimit:
    """Rate limit tracking for Pipefy API"""
    requests_per_minute: int = 500
    minute_start: datetime = None
    requests_this_minute: int = 0
    
    def __post_init__(self):
        if self.minute_start is None:
            self.minute_start = datetime.now()


class PipefyProductionClient:
    """
    Production Pipefy API client with actual endpoints
    Implements Pipefy GraphQL API
    """
    
    BASE_URL = "https://api.pipefy.com/graphql"
    
    def __init__(self):
        """Initialize Pipefy client with actual authentication"""
        self.api_token = os.getenv('PIPEFY_API_TOKEN')
        
        if not self.api_token:
            raise PipefyAuthError("PIPEFY_API_TOKEN required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self.rate_limit = PipefyRateLimit()
        
        # Cache for frequently used data
        self.pipe_cache = {}
        self.organization_cache = {}
        
        self.logger = logging.getLogger(__name__)
    
    def _check_rate_limit(self):
        """Check and enforce Pipefy rate limits"""
        now = datetime.now()
        
        # Reset minute counter
        if now - self.rate_limit.minute_start > timedelta(minutes=1):
            self.rate_limit.requests_this_minute = 0
            self.rate_limit.minute_start = now
        
        # Check requests per minute
        if self.rate_limit.requests_this_minute >= self.rate_limit.requests_per_minute:
            wait_time = 60 - (now - self.rate_limit.minute_start).seconds
            self.logger.warning(f"Rate limit reached. Waiting {wait_time}s")
            time.sleep(wait_time)
            self.rate_limit.requests_this_minute = 0
            self.rate_limit.minute_start = datetime.now()
        
        self.rate_limit.requests_this_minute += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, PipefyRateLimitError))
    )
    def _make_request(self, query: str, variables: Dict = None) -> Any:
        """Make GraphQL request to Pipefy API"""
        self._check_rate_limit()
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        try:
            response = self.session.post(
                self.BASE_URL,
                json=payload,
                timeout=30
            )
            
            # Check for rate limit
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                raise PipefyRateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Check for errors in response
            if 'errors' in result:
                error_msg = result['errors'][0].get('message', 'Unknown error')
                
                if 'authentication' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                    raise PipefyAuthError(f"Authentication failed: {error_msg}")
                else:
                    raise Exception(f"API error: {error_msg}")
            
            return result.get('data', {})
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise PipefyAuthError(f"Authentication failed: {e}")
            else:
                self.logger.error(f"HTTP error: {e}")
                raise
    
    # ============= ACTUAL PIPEFY API QUERIES =============
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        query = """
        query {
            me {
                id
                name
                email
                avatar_url
                created_at
                locale
                time_zone
            }
        }
        """
        
        try:
            result = self._make_request(query)
            user = result.get('me', {})
            self.logger.info(f"Connected to Pipefy as {user.get('name')}")
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
                username
                email
                avatar_url
                created_at
                locale
                time_zone
                departmentKey
            }
        }
        """
        
        result = self._make_request(query)
        return result.get('me', {})
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations accessible to the user"""
        query = """
        query {
            organizations {
                id
                name
                created_at
                members_count
                pipes_count
                only_admin_can_create_pipes
                only_admin_can_invite_users
                pipes {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
                tables {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        
        result = self._make_request(query)
        orgs = result.get('organizations', [])
        
        # Cache organizations
        for org in orgs:
            self.organization_cache[org['id']] = org
        
        return orgs
    
    def get_pipes(self, organization_id: str = None) -> List[Dict[str, Any]]:
        """Get all pipes, optionally filtered by organization"""
        if organization_id:
            query = """
            query ($org_id: ID!) {
                organization(id: $org_id) {
                    pipes {
                        edges {
                            node {
                                id
                                name
                                description
                                icon
                                color
                                created_at
                                anyone_can_create_card
                                public
                                public_form
                                phases {
                                    id
                                    name
                                    description
                                    cards_count
                                    done
                                    fields {
                                        id
                                        label
                                        type
                                        required
                                        editable
                                        options
                                    }
                                }
                                start_form_fields {
                                    id
                                    label
                                    type
                                    required
                                    editable
                                    options
                                    help
                                }
                                labels {
                                    id
                                    name
                                    color
                                }
                                members {
                                    user {
                                        id
                                        name
                                        email
                                    }
                                    role_name
                                }
                            }
                        }
                    }
                }
            }
            """
            
            result = self._make_request(query, {'org_id': organization_id})
            org = result.get('organization', {})
            pipes_edges = org.get('pipes', {}).get('edges', [])
            pipes = [edge['node'] for edge in pipes_edges]
        else:
            query = """
            query {
                pipes {
                    edges {
                        node {
                            id
                            name
                            description
                            icon
                            color
                            created_at
                            anyone_can_create_card
                            public
                            public_form
                            phases {
                                id
                                name
                                description
                                cards_count
                                done
                                fields {
                                    id
                                    label
                                    type
                                    required
                                    editable
                                    options
                                }
                            }
                            start_form_fields {
                                id
                                label
                                type
                                required
                                editable
                                options
                                help
                            }
                            labels {
                                id
                                name
                                color
                            }
                            members {
                                user {
                                    id
                                    name
                                    email
                                }
                                role_name
                            }
                        }
                    }
                }
            }
            """
            
            result = self._make_request(query)
            pipes_edges = result.get('pipes', {}).get('edges', [])
            pipes = [edge['node'] for edge in pipes_edges]
        
        # Cache pipes
        for pipe in pipes:
            self.pipe_cache[pipe['id']] = pipe
        
        return pipes
    
    def get_pipe(self, pipe_id: Union[str, int]) -> Dict[str, Any]:
        """Get detailed pipe information"""
        # Check cache first
        pipe_id = str(pipe_id)
        if pipe_id in self.pipe_cache:
            return self.pipe_cache[pipe_id]
        
        query = """
        query ($pipe_id: ID!) {
            pipe(id: $pipe_id) {
                id
                name
                description
                icon
                color
                created_at
                anyone_can_create_card
                public
                public_form
                public_form_settings {
                    organizationName
                    submitButtonText
                    submitButtonColor
                    thankYouTitle
                    redirectTo
                }
                phases {
                    id
                    name
                    description
                    cards_count
                    done
                    can_receive_card_directly_from_draft
                    fields {
                        id
                        label
                        type
                        required
                        editable
                        options
                        help
                        minimal_view
                        custom_validation
                    }
                }
                start_form_fields {
                    id
                    label
                    type
                    required
                    editable
                    options
                    help
                    description
                    minimal_view
                    custom_validation
                }
                labels {
                    id
                    name
                    color
                }
                members {
                    user {
                        id
                        name
                        email
                        avatar_url
                    }
                    role_name
                }
                webhooks {
                    id
                    name
                    url
                    headers
                    actions
                }
            }
        }
        """
        
        result = self._make_request(query, {'pipe_id': pipe_id})
        pipe = result.get('pipe', {})
        
        if pipe:
            self.pipe_cache[pipe_id] = pipe
        
        return pipe
    
    def get_cards(self, pipe_id: Union[str, int], first: int = 50, 
                 after: str = None) -> Dict[str, Any]:
        """Get cards from a pipe with pagination"""
        query = """
        query ($pipe_id: ID!, $first: Int!, $after: String) {
            pipe(id: $pipe_id) {
                id
                name
                cards(first: $first, after: $after) {
                    edges {
                        node {
                            id
                            title
                            assignees {
                                id
                                name
                                email
                            }
                            comments {
                                id
                                text
                                created_at
                                author {
                                    id
                                    name
                                }
                            }
                            comments_count
                            current_phase {
                                id
                                name
                            }
                            done
                            due_date
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
                            labels {
                                id
                                name
                                color
                            }
                            phases_history {
                                phase {
                                    id
                                    name
                                }
                                firstTimeIn
                                lastTimeOut
                                duration
                            }
                            url
                            created_at
                            updated_at
                            started_current_phase_at
                            createdBy {
                                id
                                name
                            }
                            attachments {
                                url
                                name
                                createdAt
                                createdBy {
                                    id
                                    name
                                }
                            }
                            subtitles {
                                id
                                value
                            }
                            expired
                            late
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        }
        """
        
        variables = {
            'pipe_id': str(pipe_id),
            'first': first
        }
        
        if after:
            variables['after'] = after
        
        result = self._make_request(query, variables)
        pipe = result.get('pipe', {})
        cards_data = pipe.get('cards', {})
        
        return {
            'cards': [edge['node'] for edge in cards_data.get('edges', [])],
            'pageInfo': cards_data.get('pageInfo', {}),
            'pipe': {'id': pipe.get('id'), 'name': pipe.get('name')}
        }
    
    def get_card(self, card_id: Union[str, int]) -> Dict[str, Any]:
        """Get detailed card information"""
        query = """
        query ($card_id: ID!) {
            card(id: $card_id) {
                id
                title
                assignees {
                    id
                    name
                    email
                    avatar_url
                }
                comments {
                    id
                    text
                    created_at
                    author {
                        id
                        name
                    }
                }
                comments_count
                current_phase {
                    id
                    name
                    description
                    done
                }
                done
                due_date
                fields {
                    field {
                        id
                        label
                        type
                        options
                        required
                    }
                    value
                    filled_at
                    updated_at
                    phase_field {
                        id
                        label
                        type
                    }
                }
                labels {
                    id
                    name
                    color
                }
                phases_history {
                    phase {
                        id
                        name
                    }
                    firstTimeIn
                    lastTimeOut
                    duration
                }
                pipe {
                    id
                    name
                }
                url
                created_at
                updated_at
                started_current_phase_at
                createdBy {
                    id
                    name
                    email
                }
                attachments {
                    url
                    name
                    createdAt
                    createdBy {
                        id
                        name
                    }
                }
                child_relations {
                    cards {
                        id
                        title
                    }
                    source_type
                    source_id
                }
                parent_relations {
                    cards {
                        id
                        title
                    }
                    source_type
                    source_id
                }
                subtitles {
                    id
                    value
                }
                expired
                late
            }
        }
        """
        
        result = self._make_request(query, {'card_id': str(card_id)})
        return result.get('card', {})
    
    def get_tables(self, organization_id: str = None) -> List[Dict[str, Any]]:
        """Get database tables (Pipefy databases)"""
        if organization_id:
            query = """
            query ($org_id: ID!) {
                organization(id: $org_id) {
                    tables {
                        edges {
                            node {
                                id
                                name
                                description
                                icon
                                public
                                authorization
                                create_record_button_label
                                title_field {
                                    id
                                    label
                                }
                                summary_attributes {
                                    id
                                    label
                                }
                                table_fields {
                                    id
                                    label
                                    type
                                    required
                                    editable
                                    options
                                }
                                table_records_count
                            }
                        }
                    }
                }
            }
            """
            
            result = self._make_request(query, {'org_id': organization_id})
            org = result.get('organization', {})
            tables_edges = org.get('tables', {}).get('edges', [])
            return [edge['node'] for edge in tables_edges]
        else:
            query = """
            query {
                tables {
                    edges {
                        node {
                            id
                            name
                            description
                            icon
                            public
                            authorization
                            table_fields {
                                id
                                label
                                type
                                required
                                editable
                                options
                            }
                            table_records_count
                        }
                    }
                }
            }
            """
            
            result = self._make_request(query)
            tables_edges = result.get('tables', {}).get('edges', [])
            return [edge['node'] for edge in tables_edges]
    
    def get_table_records(self, table_id: Union[str, int], first: int = 50, 
                         after: str = None) -> Dict[str, Any]:
        """Get records from a database table"""
        query = """
        query ($table_id: ID!, $first: Int!, $after: String) {
            table(id: $table_id) {
                id
                name
                table_records(first: $first, after: $after) {
                    edges {
                        node {
                            id
                            title
                            status {
                                id
                                name
                            }
                            created_at
                            updated_at
                            created_by {
                                id
                                name
                            }
                            record_fields {
                                field {
                                    id
                                    label
                                    type
                                }
                                value
                                filled_at
                                updated_at
                            }
                            parent_relations {
                                id
                                name
                                source_type
                            }
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        }
        """
        
        variables = {
            'table_id': str(table_id),
            'first': first
        }
        
        if after:
            variables['after'] = after
        
        result = self._make_request(query, variables)
        table = result.get('table', {})
        records_data = table.get('table_records', {})
        
        return {
            'records': [edge['node'] for edge in records_data.get('edges', [])],
            'pageInfo': records_data.get('pageInfo', {}),
            'table': {'id': table.get('id'), 'name': table.get('name')}
        }
    
    def get_automations(self, pipe_id: Union[str, int]) -> List[Dict[str, Any]]:
        """Get automations for a pipe"""
        # Note: Automations are not directly accessible via GraphQL
        # This would require specific API endpoints or admin access
        return []
    
    def get_webhooks(self, pipe_id: Union[str, int]) -> List[Dict[str, Any]]:
        """Get webhooks for a pipe"""
        pipe = self.get_pipe(pipe_id)
        return pipe.get('webhooks', [])
    
    # ============= BATCH OPERATIONS =============
    
    def batch_get_cards(self, pipe_id: Union[str, int], 
                       batch_size: int = 50) -> Generator[List[Dict], None, None]:
        """
        Get cards in batches to handle large pipes
        
        Args:
            pipe_id: Pipe ID
            batch_size: Number of cards per batch
            
        Yields:
            Batches of cards
        """
        after = None
        
        while True:
            response = self.get_cards(pipe_id, first=batch_size, after=after)
            cards = response.get('cards', [])
            
            if not cards:
                break
            
            yield cards
            
            page_info = response.get('pageInfo', {})
            if not page_info.get('hasNextPage'):
                break
            
            after = page_info.get('endCursor')
            time.sleep(0.5)  # Rate limit pause
    
    def get_all_data(self, organization_id: str = None) -> Dict[str, Any]:
        """
        Get all data for migration
        
        Args:
            organization_id: Organization to export (optional)
            
        Returns:
            Complete data structure for migration
        """
        self.logger.info("Starting complete Pipefy data export")
        
        data = {
            'export_date': datetime.utcnow().isoformat(),
            'user': self.get_current_user(),
            'organizations': [],
            'pipes': [],
            'tables': [],
            'total_cards': 0,
            'total_pipes': 0,
            'total_tables': 0
        }
        
        # Get organizations
        if organization_id:
            orgs = [org for org in self.get_organizations() if org['id'] == str(organization_id)]
        else:
            orgs = self.get_organizations()
        
        data['organizations'] = orgs
        
        # Process each organization
        for org in orgs:
            self.logger.info(f"Processing organization: {org['name']}")
            
            # Get pipes
            pipes = self.get_pipes(org['id'])
            
            for pipe in pipes:
                self.logger.info(f"  Processing pipe: {pipe['name']}")
                
                # Get full pipe details
                pipe_data = self.get_pipe(pipe['id'])
                
                # Get cards
                pipe_data['cards'] = []
                card_count = 0
                
                for card_batch in self.batch_get_cards(pipe['id']):
                    pipe_data['cards'].extend(card_batch)
                    card_count += len(card_batch)
                    
                    # Rate limit pause
                    time.sleep(1)
                
                data['total_cards'] += card_count
                data['pipes'].append(pipe_data)
                data['total_pipes'] += 1
                
                self.logger.info(f"    Processed {card_count} cards")
            
            # Get database tables
            tables = self.get_tables(org['id'])
            
            for table in tables:
                self.logger.info(f"  Processing table: {table['name']}")
                
                # Get records
                table['records'] = []
                after = None
                
                while True:
                    response = self.get_table_records(table['id'], first=50, after=after)
                    records = response.get('records', [])
                    
                    if not records:
                        break
                    
                    table['records'].extend(records)
                    
                    page_info = response.get('pageInfo', {})
                    if not page_info.get('hasNextPage'):
                        break
                    
                    after = page_info.get('endCursor')
                    time.sleep(0.5)
                
                data['tables'].append(table)
                data['total_tables'] += 1
                
                self.logger.info(f"    Processed {len(table['records'])} records")
        
        self.logger.info(f"Export complete: {data['total_pipes']} pipes, {data['total_cards']} cards")
        
        return data
    
    # ============= PARADIGM SHIFT HELPERS =============
    
    def analyze_pipe_structure(self, pipe_id: Union[str, int]) -> Dict[str, Any]:
        """
        Analyze pipe structure for paradigm shift handling
        Pipefy uses Kanban paradigm that needs conversion
        """
        pipe = self.get_pipe(pipe_id)
        
        analysis = {
            'phases_count': len(pipe.get('phases', [])),
            'has_start_form': bool(pipe.get('start_form_fields', [])),
            'has_done_phase': False,
            'parallel_phases': [],
            'sequential_phases': [],
            'field_complexity': 0
        }
        
        # Analyze phases
        for phase in pipe.get('phases', []):
            if phase.get('done'):
                analysis['has_done_phase'] = True
            
            # Count fields per phase
            field_count = len(phase.get('fields', []))
            analysis['field_complexity'] += field_count
            
            # Determine if phase is parallel or sequential
            if phase.get('can_receive_card_directly_from_draft'):
                analysis['parallel_phases'].append(phase['name'])
            else:
                analysis['sequential_phases'].append(phase['name'])
        
        # Add start form fields to complexity
        analysis['field_complexity'] += len(pipe.get('start_form_fields', []))
        
        # Recommend transformation strategy
        if analysis['phases_count'] <= 3:
            analysis['recommended_strategy'] = 'simple_workflow'
        elif analysis['parallel_phases']:
            analysis['recommended_strategy'] = 'parallel_to_sequential'
        else:
            analysis['recommended_strategy'] = 'direct_phase_mapping'
        
        return analysis
    
    def parse_field_value(self, field_type: str, value: Any) -> Any:
        """
        Parse field value based on Pipefy field type
        """
        if not value:
            return None
        
        if field_type == PipefyFieldType.SELECT.value:
            # Select fields return array of selected options
            if isinstance(value, list):
                return value[0] if value else None
            return value
        
        elif field_type == PipefyFieldType.CHECKBOX.value:
            # Checkbox returns array of checked options
            return value if isinstance(value, list) else []
        
        elif field_type == PipefyFieldType.DATE.value:
            # Date fields return ISO format
            return value
        
        elif field_type == PipefyFieldType.DATETIME.value:
            # DateTime fields return ISO format with time
            return value
        
        elif field_type == PipefyFieldType.NUMBER.value:
            # Number fields
            try:
                return float(value) if value else None
            except:
                return None
        
        elif field_type == PipefyFieldType.CURRENCY.value:
            # Currency fields return as string with formatting
            try:
                # Remove currency symbols and parse
                clean_value = ''.join(c for c in str(value) if c.isdigit() or c == '.')
                return float(clean_value) if clean_value else None
            except:
                return None
        
        elif field_type == PipefyFieldType.ASSIGNEE_SELECT.value:
            # Assignee fields return user IDs
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        elif field_type == PipefyFieldType.CONNECTION.value:
            # Connection fields link to other cards
            if isinstance(value, list):
                return [{'id': item.get('id'), 'title': item.get('title')} for item in value]
            return []
        
        elif field_type == PipefyFieldType.DATABASE_CONNECTION.value:
            # Database connection fields link to table records
            if isinstance(value, list):
                return [{'id': item.get('id'), 'title': item.get('title')} for item in value]
            return []
        
        else:
            # Default: return as-is
            return value
    
    # ============= CREATE OPERATIONS =============
    
    def create_pipe(self, organization_id: str, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new pipe"""
        mutation = """
        mutation ($org_id: ID!, $name: String!, $icon: String, $anyone_can_create_card: Boolean) {
            createPipe(input: {
                organization_id: $org_id,
                name: $name,
                icon: $icon,
                anyone_can_create_card: $anyone_can_create_card
            }) {
                pipe {
                    id
                    name
                }
            }
        }
        """
        
        variables = {
            'org_id': organization_id,
            'name': name,
            'icon': kwargs.get('icon', 'pipe'),
            'anyone_can_create_card': kwargs.get('anyone_can_create_card', True)
        }
        
        result = self._make_request(mutation, variables)
        return result.get('createPipe', {}).get('pipe', {})
    
    def create_card(self, pipe_id: Union[str, int], title: str, 
                   fields_attributes: List[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Create a new card in a pipe"""
        mutation = """
        mutation ($pipe_id: ID!, $title: String!, $fields: [FieldValueInput], 
                 $assignee_ids: [ID], $label_ids: [ID], $due_date: DateTime) {
            createCard(input: {
                pipe_id: $pipe_id,
                title: $title,
                fields_attributes: $fields,
                assignee_ids: $assignee_ids,
                label_ids: $label_ids,
                due_date: $due_date
            }) {
                card {
                    id
                    title
                }
            }
        }
        """
        
        variables = {
            'pipe_id': str(pipe_id),
            'title': title
        }
        
        if fields_attributes:
            variables['fields'] = fields_attributes
        
        if 'assignee_ids' in kwargs:
            variables['assignee_ids'] = kwargs['assignee_ids']
        
        if 'label_ids' in kwargs:
            variables['label_ids'] = kwargs['label_ids']
        
        if 'due_date' in kwargs:
            variables['due_date'] = kwargs['due_date']
        
        result = self._make_request(mutation, variables)
        return result.get('createCard', {}).get('card', {})
    
    def move_card_to_phase(self, card_id: Union[str, int], 
                          destination_phase_id: Union[str, int]) -> Dict[str, Any]:
        """Move card to different phase"""
        mutation = """
        mutation ($card_id: ID!, $phase_id: ID!) {
            moveCardToPhase(input: {
                card_id: $card_id,
                destination_phase_id: $phase_id
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
            'card_id': str(card_id),
            'phase_id': str(destination_phase_id)
        }
        
        result = self._make_request(mutation, variables)
        return result.get('moveCardToPhase', {}).get('card', {})
    
    def create_webhook(self, pipe_id: Union[str, int], name: str, url: str, 
                      actions: List[str]) -> Dict[str, Any]:
        """Create webhook for pipe"""
        mutation = """
        mutation ($pipe_id: ID!, $name: String!, $url: String!, $actions: [String!]!) {
            createWebhook(input: {
                pipe_id: $pipe_id,
                name: $name,
                url: $url,
                actions: $actions
            }) {
                webhook {
                    id
                    name
                    url
                }
            }
        }
        """
        
        variables = {
            'pipe_id': str(pipe_id),
            'name': name,
            'url': url,
            'actions': actions
        }
        
        result = self._make_request(mutation, variables)
        return result.get('createWebhook', {}).get('webhook', {})


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    # Example usage
    client = PipefyProductionClient()
    
    # Test connection
    if client.test_connection():
        print("✅ Connected to Pipefy")
        
        # Get current user
        user = client.get_current_user()
        print(f"User: {user.get('name')} ({user.get('email')})")
        
        # Get organizations
        orgs = client.get_organizations()
        print(f"Found {len(orgs)} organizations")
        
        if orgs:
            org = orgs[0]
            print(f"\nOrganization: {org['name']}")
            
            # Get pipes
            pipes = client.get_pipes(org['id'])
            print(f"Found {len(pipes)} pipes")
            
            if pipes:
                pipe = pipes[0]
                print(f"\nPipe: {pipe['name']}")
                print(f"Phases: {len(pipe.get('phases', []))}")
                
                # Analyze pipe structure
                analysis = client.analyze_pipe_structure(pipe['id'])
                print(f"Structure analysis:")
                print(f"  - Phases: {analysis['phases_count']}")
                print(f"  - Has start form: {analysis['has_start_form']}")
                print(f"  - Field complexity: {analysis['field_complexity']}")
                print(f"  - Recommended strategy: {analysis['recommended_strategy']}")
                
                # Get cards
                response = client.get_cards(pipe['id'], first=5)
                cards = response.get('cards', [])
                print(f"\nFound {len(cards)} cards (showing first 5)")
                
                for card in cards[:3]:
                    print(f"  - {card['title']} (Phase: {card.get('current_phase', {}).get('name')})")
    
    print("\n✅ Production Pipefy client ready!")