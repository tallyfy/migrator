# Pipefy GraphQL Query Examples

## Essential Queries for Migration

### 1. Organization Discovery
```graphql
query GetOrganization($orgId: ID!) {
  organization(id: $orgId) {
    id
    name
    created_at
    billing_period
    members_count
    pipes_count
    tables_count
    only_admin_can_create_pipes
    only_admin_can_invite_users
    members {
      user {
        id
        email
        name
        username
        avatar_url
        locale
        time_zone
      }
      role_name
    }
  }
}
```

### 2. Complete Pipe Structure
```graphql
query GetPipeComplete($pipeId: ID!) {
  pipe(id: $pipeId) {
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
    
    # Phases with all details
    phases {
      id
      name
      description
      done
      cards_count
      index
      can_receive_card_directly_from_draft
      fields {
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
        unique
        sync_with_card
      }
      cards_can_be_moved_to_phases {
        id
        name
      }
    }
    
    # Start form configuration
    start_form_fields {
      id
      label
      description
      type
      required
      options
      default_value
    }
    
    # Labels for categorization
    labels {
      id
      name
      color
    }
    
    # Access control
    members {
      user {
        id
        email
        name
      }
      role_name
    }
    
    # Preferences
    preferences {
      everyone_can_see
      everyone_can_edit
    }
    
    # Summary statistics
    summary {
      total_cards_count
      total_done_cards_count
      total_late_cards_count
      total_expired_cards_count
    }
  }
}
```

### 3. Cards with Pagination
```graphql
query GetCards($pipeId: ID!, $first: Int!, $after: String) {
  pipe(id: $pipeId) {
    cards(first: $first, after: $after) {
      edges {
        node {
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
          
          # Current location
          current_phase {
            id
            name
          }
          
          # Assignments
          assignees {
            id
            email
            name
          }
          
          # Categorization
          labels {
            id
            name
            color
          }
          
          # All field values
          fields {
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
          
          # Comments thread
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
          
          # File attachments
          attachments {
            id
            filename
            url
            filesize
            created_at
            createdBy {
              id
              email
            }
          }
          
          # Phase movement history
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
          
          # Card relationships
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
      pageInfo {
        hasNextPage
        endCursor
        startCursor
        hasPreviousPage
      }
    }
  }
}
```

### 4. Database Tables
```graphql
query GetTables {
  tables {
    edges {
      node {
        id
        name
        description
        public
        authorization
        create_record_button_label
        
        # Title field configuration
        title_field {
          id
          label
        }
        
        # Table schema
        fields {
          id
          label
          type
          description
          required
          unique
          options
          default_value
          custom_validation
        }
        
        # Statistics
        table_records_count
        created_at
        updated_at
      }
    }
  }
}
```

### 5. Table Records with Pagination
```graphql
query GetTableRecords($tableId: ID!, $first: Int!, $after: String) {
  table(id: $tableId) {
    table_records(first: $first, after: $after) {
      edges {
        node {
          id
          title
          created_at
          updated_at
          
          # User tracking
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
          
          # All field values
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
          
          # Record relationships
          parent_relations {
            id
            name
            source_type
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
```

### 6. Webhooks Configuration
```graphql
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
```

## Mutation Examples

### 1. Bulk Import Cards
```graphql
mutation BulkImportCards($pipeId: ID!, $cards: [CardInput!]!) {
  cardsImporter(pipe_id: $pipeId, cards: $cards) {
    clientMutationId
    cardsImported
  }
}

# Variables example:
{
  "pipeId": "12345",
  "cards": [
    {
      "title": "Card 1",
      "due_date": "2024-12-31T23:59:59Z",
      "assignee_ids": ["user123"],
      "label_ids": ["label456"],
      "phase_id": "phase789",
      "fields_attributes": [
        {
          "field_id": "field1",
          "value": "Text value"
        },
        {
          "field_id": "field2",
          "value": "100"
        }
      ]
    }
  ]
}
```

### 2. Create Single Card
```graphql
mutation CreateCard($input: CreateCardInput!) {
  createCard(input: $input) {
    card {
      id
      title
      url
      current_phase {
        id
        name
      }
    }
  }
}

# Variables:
{
  "input": {
    "pipe_id": "12345",
    "title": "New Card",
    "due_date": "2024-12-31",
    "assignee_ids": ["user123"],
    "label_ids": ["label456"],
    "phase_id": "phase789",
    "fields_attributes": [
      {
        "field_id": "field1",
        "value": "Value 1"
      }
    ]
  }
}
```

### 3. Move Card Between Phases
```graphql
mutation MoveCard($cardId: ID!, $destinationPhaseId: ID!) {
  moveCardToPhase(input: {
    card_id: $cardId,
    destination_phase_id: $destinationPhaseId
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
```

### 4. Update Card Field
```graphql
mutation UpdateField($cardId: ID!, $fieldId: ID!, $value: String) {
  updateCardField(input: {
    card_id: $cardId,
    field_id: $fieldId,
    value: $value
  }) {
    card {
      id
      fields {
        field {
          id
        }
        value
      }
    }
  }
}
```

### 5. Bulk Import Table Records
```graphql
mutation ImportTableRecords($tableId: ID!, $records: [TableRecordInput!]!) {
  recordsImporter(table_id: $tableId, records: $records) {
    clientMutationId
    recordsImported
  }
}

# Variables:
{
  "tableId": "table123",
  "records": [
    {
      "title": "Record 1",
      "fields_attributes": [
        {
          "field_id": "field1",
          "value": "Value 1"
        }
      ]
    }
  ]
}
```

## Introspection Query
```graphql
query IntrospectSchema {
  __schema {
    types {
      name
      kind
      description
      fields {
        name
        type {
          name
          kind
          ofType {
            name
            kind
          }
        }
        args {
          name
          type {
            name
            kind
          }
        }
      }
    }
  }
}
```

## Performance Optimization Queries

### 1. Minimal Card Data (Fast)
```graphql
query GetCardIds($pipeId: ID!, $first: Int!) {
  pipe(id: $pipeId) {
    cards(first: $first) {
      edges {
        node {
          id
          title
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

### 2. Using Fragments for Reusability
```graphql
fragment CardBasics on Card {
  id
  title
  created_at
  current_phase {
    id
  }
}

fragment CardDetails on Card {
  ...CardBasics
  fields {
    field {
      id
    }
    value
  }
  assignees {
    id
  }
}

query GetCardsWithFragments($pipeId: ID!) {
  pipe(id: $pipeId) {
    cards(first: 50) {
      edges {
        node {
          ...CardDetails
        }
      }
    }
  }
}
```

### 3. Parallel Queries (Batch)
```graphql
query BatchQuery($pipeId1: ID!, $pipeId2: ID!) {
  pipe1: pipe(id: $pipeId1) {
    id
    name
    cards_count
  }
  pipe2: pipe(id: $pipeId2) {
    id
    name
    cards_count
  }
}
```

## Error Handling

### Check for Specific Errors
```graphql
query SafeQuery($cardId: ID!) {
  card(id: $cardId) {
    id
    title
  }
}

# Response with error:
{
  "data": {
    "card": null
  },
  "errors": [
    {
      "message": "Card not found",
      "extensions": {
        "code": "NOT_FOUND"
      }
    }
  ]
}
```

## Rate Limiting Considerations

1. **Pagination**: Always use `first` parameter (max 50)
2. **Depth**: Limit query depth to avoid complexity errors
3. **Batching**: Combine related queries when possible
4. **Caching**: Cache static data like pipe structure
5. **Retry Logic**: Implement exponential backoff for 429 errors

## Migration-Specific Queries

### 1. Count All Objects (Pre-Migration)
```graphql
query CountObjects {
  organization {
    pipes_count
    tables_count
    members_count
  }
  pipes {
    edges {
      node {
        id
        name
        cards_count
        phases {
          cards_count
        }
      }
    }
  }
}
```

### 2. Export Complete Pipe Data
```graphql
query ExportPipe($pipeId: ID!) {
  pipe(id: $pipeId) {
    # Include ALL fields from GetPipeComplete query
    # Plus cards with pagination
    # This is the master export query
  }
}
```

### 3. Verify Migration Success
```graphql
query VerifyCard($cardId: ID!) {
  card(id: $cardId) {
    id
    title
    fields {
      field {
        id
      }
      value
    }
  }
}
```