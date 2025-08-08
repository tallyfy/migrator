# Pipefy API and Data Model - Comprehensive Research Document

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [GraphQL API Structure](#graphql-api-structure)
4. [Core Data Objects](#core-data-objects)
5. [Field Types](#field-types)
6. [Queries](#queries)
7. [Mutations](#mutations)
8. [Relationships and Connections](#relationships-and-connections)
9. [Webhooks](#webhooks)
10. [Permissions and Roles](#permissions-and-roles)
11. [Automations](#automations)
12. [SLA and Time Tracking](#sla-and-time-tracking)
13. [Bulk Operations](#bulk-operations)
14. [Data Export](#data-export)
15. [Rate Limits and Pagination](#rate-limits-and-pagination)
16. [Migration Considerations](#migration-considerations)
17. [Sample GraphQL Queries](#sample-graphql-queries)

## Overview

Pipefy is a process management platform that uses a GraphQL API for all interactions. The platform organizes work into **Pipes** (workflow templates), **Cards** (workflow instances), **Phases** (workflow stages), and **Tables** (databases).

### Key API Resources
- **Main Developer Portal**: https://developers.pipefy.com/graphql
- **API Documentation**: https://api-docs.pipefy.com/
- **GraphQL Endpoint**: https://api.pipefy.com/graphql
- **GraphiQL IDE**: https://app.pipefy.com/graphiql

## Authentication

### Methods
1. **Service Accounts** (Recommended for production)
   - OAuth2 Bearer token authentication
   - Recommended for production environments
   - Better security and organization management

2. **Personal Access Tokens** (Deprecated but still available)
   - Generated for individual users
   - Don't expire
   - Give access to all resources that user has access to
   - Ideal for testing and personal integrations

### Implementation
```http
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

### Access Requirements
- Only **admin** or **super admin** users can use Pipefy's API
- Users need appropriate role and permissions for each resource

## GraphQL API Structure

### Schema Definition
The GraphQL Schema defines the capabilities of Pipefy's GraphQL server, exposing:
- All available types and directives
- Entry points for query, mutation, and subscription operations
- Strongly typed with schema defining API's type system and all object relationships

### Root Types
- **Query**: Operations that retrieve data from the server
- **Mutation**: Operations that change data on the server
- **Subscription**: Real-time data updates (limited availability)

## Core Data Objects

### 1. Organization
**Description**: Top-level workspace/company entity

**Key Fields**:
- `id`: Unique identifier
- `name`: Organization name
- `billing_email`: Billing contact
- `created_at`: Creation timestamp
- `users`: List of organization users
- `pipes`: Associated pipes
- `tables`: Associated database tables
- `webhooks`: Organization-level webhooks

### 2. Pipe
**Description**: Workflow template/process definition

**Key Fields**:
- `id`: Unique identifier
- `uuid`: Universal unique identifier
- `suid`: Small unique ID
- `name`: Pipe name
- `description`: Pipe description
- `icon`: Visual icon
- `color`: Visual color
- `organization`: Parent organization
- `phases`: List of workflow phases
- `start_form_fields`: Initial form fields
- `members`: Pipe members
- `labels`: Available labels
- `anyone_can_create_card`: Card creation permissions
- `only_admin_can_remove_cards`: Card deletion restrictions
- `only_assignees_can_edit_cards`: Card editing restrictions
- `cards_count`: Total cards
- `opened_cards_count`: Active cards
- `childrenRelations`: Child pipe connections
- `parentsRelations`: Parent pipe connections
- `fieldConditions`: Conditional field logic
- `webhooks`: Pipe-specific webhooks
- `expiration_time_by_unit`: SLA timing
- `expiration_unit`: SLA unit in seconds

### 3. Phase
**Description**: Stage within a workflow

**Key Fields**:
- `id`: Unique identifier
- `name`: Phase name
- `description`: Phase description
- `cards_count`: Number of cards in phase
- `cards`: Cards currently in phase
- `fields`: Phase-specific fields
- `done`: Boolean indicating if phase is final
- `can_receive_card_directly_from_draft`: Direct card creation
- `expiration_time_by_unit`: SLA for phase
- `expiration_unit`: SLA time unit

### 4. Card
**Description**: Workflow instance/item

**Key Fields**:
- `id`: Unique identifier
- `uuid`: Universal unique identifier
- `suid`: Small unique ID
- `title`: Card title
- `path`: System path
- `createdAt`: Creation timestamp
- `updated_at`: Last update
- `started_current_phase_at`: Phase entry time
- `finished_at`: Completion timestamp
- `due_date`: Scheduled completion
- `done`: Completion status
- `late`: Behind schedule flag
- `expired`: Past expiration flag
- `current_phase`: Current workflow phase
- `assignees`: Assigned users
- `comments`: Card comments
- `attachments`: Linked files
- `labels`: Applied labels
- `pipe`: Associated workflow
- `age`: Seconds since creation
- `comments_count`: Total comments
- `attachments_count`: Total attachments
- `checklist_items_count`: Checklist items
- `fields`: Card field values
- `child_relations`: Connected child cards
- `parent_relations`: Connected parent cards

### 5. Table (Database)
**Description**: Database table for structured data

**Key Fields**:
- `id`: Unique identifier
- `name`: Table name
- `description`: Table description
- `color`: Visual color
- `icon`: Visual icon
- `authorization`: Access level
- `table_fields`: Field definitions
- `table_records`: Table records
- `members`: Table members
- `permissions`: User permissions
- `anyone_can_create_card`: Open record creation
- `create_record_button_label`: Custom button text
- `startFormPhaseId`: Initial form phase
- `table_records_count`: Total records

### 6. TableRecord
**Description**: Individual record in a database table

**Key Fields**:
- `id`: Unique identifier
- `title`: Record title
- `status`: Record status
- `table`: Parent table
- `record_fields`: Field values
- `created_at`: Creation timestamp
- `updated_at`: Last update
- `created_by`: Creator user
- `updated_by`: Last editor
- `labels`: Applied labels
- `parent_relations`: Parent connections
- `child_relations`: Child connections

### 7. User
**Description**: System user

**Key Fields**:
- `id`: Unique identifier
- `name`: User name
- `email`: Email address
- `username`: Username
- `avatar_url`: Profile image
- `created_at`: Account creation
- `locale`: Language preference
- `time_zone`: Timezone setting

### 8. Member
**Description**: User with specific role in pipe/table

**Key Fields**:
- `user`: User object
- `role_name`: Role in context
- `email`: Contact email

### 9. Label
**Description**: Tag for categorization

**Key Fields**:
- `id`: Unique identifier
- `name`: Label name
- `color`: Visual color

### 10. Comment
**Description**: Discussion thread entry

**Key Fields**:
- `id`: Unique identifier
- `text`: Comment content
- `created_at`: Creation timestamp
- `author`: Comment author

### 11. Attachment
**Description**: File attachment

**Key Fields**:
- `id`: Unique identifier
- `path`: File path
- `url`: Download URL
- `filename`: Original filename
- `created_at`: Upload timestamp

### 12. Webhook
**Description**: Event notification endpoint

**Key Fields**:
- `id`: Unique identifier
- `name`: Webhook name
- `url`: Endpoint URL
- `headers`: Custom headers
- `actions`: Triggering events

### 13. EmailTemplate
**Description**: Reusable email template

**Key Fields**:
- `id`: Unique identifier
- `name`: Template name
- `subject`: Email subject
- `body`: Email content
- `from_email`: Sender address
- `to_emails`: Recipients

### 14. Report
**Description**: Data analysis report

**Key Fields**:
- `id`: Unique identifier
- `name`: Report name
- `report_type`: Type of report
- `filters`: Applied filters
- `groupings`: Data groupings

### 15. CardRelation
**Description**: Connection between cards

**Key Fields**:
- `id`: Unique identifier
- `source_id`: Source card/record
- `target_id`: Target card/record
- `source_type`: Source object type
- `target_type`: Target object type

### 16. FieldCondition
**Description**: Conditional field logic

**Key Fields**:
- `id`: Unique identifier
- `name`: Condition name
- `condition`: Logic expression
- `actions`: Triggered actions
- `phase_id`: Associated phase
- `field_id`: Target field

## Field Types

### Available Field Types

1. **Text Fields**
   - `short_text`: Single line text input
   - `long_text`: Multi-line text area
   - `statement`: Display-only text

2. **Selection Fields**
   - `dropdown_select`: Single selection dropdown
   - `radio_select`: Single selection radio buttons
   - `checkbox`: Multiple selection checkboxes
   - `label_select`: Label selection

3. **Numeric Fields**
   - `number`: Numeric input
   - `currency`: Currency amount
   - `percentage`: Percentage value

4. **Date/Time Fields**
   - `date`: Date picker
   - `datetime`: Date and time picker
   - `due_date`: Special date field for deadlines

5. **Contact Fields**
   - `email`: Email address validation
   - `phone`: Phone number formatting

6. **File Fields**
   - `attachment`: File upload (max 512MB)
   - Multiple file formats supported
   - Special characters not allowed in filenames

7. **Special Fields**
   - `assignee_select`: User assignment
   - `connection`: Link to other cards/records
   - `dynamic_content`: Conditional content
   - `formula`: Calculated field

### Field Properties
- `required`: Boolean - mandatory field
- `help`: String - help text tooltip
- `description`: String - field description
- `editable`: Boolean - can be edited in other phases
- `unique`: Boolean - enforce unique values
- `minimal_view`: Boolean - show in card preview
- `custom_validation`: String - regex validation

## Queries

### Complete List of Available Queries

#### Card Queries
- `allCards`: Retrieve all cards with filters
- `card`: Get single card by ID
- `cards`: Get cards with pagination
- `findCards`: Search cards with advanced filters
- `cardsImportations`: Card import history

#### Organization Queries
- `me`: Current user information
- `organization`: Single organization details
- `organizations`: List of organizations

#### Pipe Queries
- `pipe`: Single pipe details
- `pipes`: List of pipes
- `pipe_relations`: Pipe connections
- `pipe_templates`: Available templates
- `phase`: Single phase details

#### Table/Database Queries
- `table`: Single table details
- `tables`: List of tables
- `table_record`: Single record
- `table_records`: List of records
- `table_relations`: Table connections
- `findRecords`: Search table records
- `connectedTableRecords`: Related records
- `recordsImportations`: Import history

#### Field and Form Queries
- `autoFillFields`: Field auto-completion
- `conditionalField`: Conditional field logic
- `fieldCondition`: Field condition details
- `repoItemForm`: Form structure

#### Other Queries
- `inbox_emails`: Email inbox
- `pipeReportExport`: Export report status

## Mutations

### Complete List of Available Mutations

#### Card Operations
- `createCard`: Create new card
- `updateCard`: Update card details
- `updateCardField`: Update specific field
- `updateFieldsValues`: Bulk field updates
- `deleteCard`: Delete card
- `moveCardToPhase`: Move card between phases
- `duplicateCard`: Clone card
- `createCardRelation`: Connect cards
- `deleteCardRelation`: Remove connection

#### Pipe Operations
- `createPipe`: Create new pipe
- `updatePipe`: Update pipe settings
- `deletePipe`: Delete pipe
- `clonePipes`: Duplicate pipes

#### Phase Operations
- `createPhase`: Add new phase
- `updatePhase`: Update phase
- `deletePhase`: Remove phase
- `movePhase`: Reorder phases
- `createPhaseField`: Add field to phase
- `updatePhaseField`: Update phase field
- `deletePhaseField`: Remove phase field

#### Table Operations
- `createTable`: Create database table
- `updateTable`: Update table settings
- `deleteTable`: Delete table
- `createTableField`: Add table field
- `updateTableField`: Update table field
- `deleteTableField`: Remove table field
- `createTableRecord`: Add record
- `updateTableRecord`: Update record
- `deleteTableRecord`: Delete record
- `createTableRelation`: Connect tables
- `deleteTableRelation`: Remove connection

#### Organization Operations
- `createOrganization`: Create organization
- `updateOrganization`: Update settings
- `inviteMembers`: Invite users
- `removeUserFromOrg`: Remove user
- `updateUserRole`: Change user role

#### Webhook Operations
- `createOrganizationWebhook`: Add org webhook
- `updateOrganizationWebhook`: Update webhook
- `deleteOrganizationWebhook`: Remove webhook
- `createPipeWebhook`: Add pipe webhook
- `updatePipeWebhook`: Update pipe webhook
- `deletePipeWebhook`: Remove pipe webhook
- `createTableWebhook`: Add table webhook
- `updateTableWebhook`: Update table webhook
- `deleteTableWebhook`: Remove table webhook

#### Automation Operations
- `createAutomation`: Add automation
- `updateAutomation`: Update automation
- `deleteAutomation`: Remove automation
- `createEmailTemplate`: Add email template
- `updateEmailTemplate`: Update template
- `deleteEmailTemplate`: Remove template

#### Import Operations
- `cardsImporter`: Bulk import cards from XLSX
- `recordsImporter`: Bulk import records from XLSX

#### Other Operations
- `createComment`: Add comment
- `deleteComment`: Remove comment
- `createLabel`: Add label
- `updateLabel`: Update label
- `deleteLabel`: Remove label
- `createFieldCondition`: Add conditional logic
- `updateFieldCondition`: Update condition
- `deleteFieldCondition`: Remove condition
- `createInboxEmail`: Process email
- `createPresignedUrl`: Generate upload URL
- `createPresignedUrlForPipePdfTemplate`: PDF template URL
- `configurePublicPhaseFormLink`: Public form setup
- `setRole`: Assign user role
- `deleteOrganization`: Remove organization
- `deleteUser`: Remove user

## Relationships and Connections

### Pipe Relations
- **Parent-Child Relationships**: Pipes can have hierarchical relationships
- **Connection Types**:
  - One-to-one: Single card connection
  - One-to-many: Multiple child cards
  - Many-to-many: Complex relationships

### Field Mapping
- Map fields between connected pipes
- Auto-fill fields from parent to child
- Bi-directional synchronization options

### Card Relations
```graphql
# Query child relations
cards(pipe_id: 123) {
  edges {
    node {
      child_relations {
        cards {
          title
          id
          fields {
            value
            name
          }
        }
        name
        id
      }
    }
  }
}

# Query parent relations
cards(pipe_id: 123) {
  edges {
    node {
      parent_relations {
        cards {
          title
          id
        }
      }
    }
  }
}
```

### Table Relations
- Connect database tables
- Link records across tables
- Maintain referential integrity

## Webhooks

### Types of Webhooks

1. **Organization Webhooks**
   - `user.invitation_sent`: User invited
   - `user.invitation_acceptance`: Invitation accepted
   - `user.role_set`: Role changed
   - `user.removal_from_org`: User removed

2. **Pipe/Table Webhooks**
   - `card.create`: Card created
   - `card.field_update`: Field updated
   - `card.move`: Card moved
   - `card.done`: Card completed
   - `card.delete`: Card deleted
   - `card.late`: Card is late
   - `card.expired`: Card expired
   - `card.overdue`: Card overdue

### Webhook Configuration
```graphql
mutation {
  createOrganizationWebhook(input: {
    organization_id: "123",
    name: "My Webhook",
    url: "https://example.com/webhook",
    headers: "{\"Authorization\": \"Bearer token\"}",
    actions: ["card.create", "card.move"]
  }) {
    webhook {
      id
      name
      url
    }
  }
}
```

### Webhook Limits
- Recommended: Maximum 30 webhooks per pipe
- Varies based on process size and subscription

## Permissions and Roles

### Company Roles
1. **Super Admin**
   - Full system access
   - Can manage organization
   - Can use API
   - Can create/delete pipes

2. **Admin**
   - Pipe/table management
   - Can use API
   - Can create automations
   - Can manage users in context

3. **Member**
   - Execute activities
   - View assigned work
   - Limited configuration access

4. **Guest**
   - View-only access
   - No charges incurred
   - Limited to specific pipes/tables

### Pipe/Table Permissions
- `can_create_card`: Create new items
- `can_edit_card`: Modify items
- `can_delete_card`: Remove items
- `can_move_card`: Change phases
- `can_see_card`: View items
- `can_manage_pipe`: Configure pipe

## Automations

### Automation Triggers
- Card enters phase
- Card is created
- Card is moved
- Card is updated
- Field value changes
- Card becomes late/expired
- Periodic/scheduled triggers

### Automation Actions
- Send email template
- Move card to phase
- Update field values
- Create connected card
- Assign to user
- Add label
- Create comment
- Apply SLA rules
- Call webhook

### Email Template Automations
- Trigger: Card phase entry
- Action: Send template email
- Dynamic fields in templates
- Up to 10 recipients per automation
- SMTP configuration required for Enterprise/Unlimited

### Automation Limits
- Plan-based limits on automation jobs
- Each automation execution counts as one job
- Multiple actions in single automation count as one job

## SLA and Time Tracking

### Alert Types

1. **Late Alerts**
   - Time limit per phase
   - Yellow clock indicator
   - Phase-specific duration

2. **Expired Alerts**
   - Total time in pipe
   - Red clock indicator
   - End-to-end process duration

### Advanced SLA Rules
- Account for holidays
- Different working hours per team
- Multiple timezone support
- Business hours only counting

### SLA Configuration
```graphql
mutation {
  createAutomation(input: {
    pipe_id: "123",
    trigger: "card.create",
    action: "apply_sla_rules",
    config: {
      work_week: ["monday", "tuesday", "wednesday", "thursday", "friday"],
      work_hours: "09:00-18:00",
      holidays: ["2024-12-25", "2024-01-01"],
      timezone: "America/Sao_Paulo"
    }
  }) {
    automation {
      id
    }
  }
}
```

### Time Tracking Fields
- `age`: Total card age in seconds
- `started_current_phase_at`: Phase entry timestamp
- `leadTime`: Time to completion
- `cycleTime`: Active working time
- `total_time_in_phase`: Phase duration

## Bulk Operations

### Bulk Import

#### Cards Import
```graphql
mutation {
  cardsImporter(input: {
    pipeId: 123,
    url: "https://example.com/cards.xlsx",
    assigneesColumn: "A",
    labelsColumn: "B",
    dueDateColumn: "C",
    currentPhaseColumn: "D",
    fieldValuesColumns: [
      {fieldId: "field_1", columnId: "E"},
      {fieldId: "field_2", columnId: "F"}
    ]
  }) {
    cardsImportation {
      id
      status
    }
  }
}
```

#### Records Import
```graphql
mutation {
  recordsImporter(input: {
    tableId: 456,
    url: "https://example.com/records.xlsx",
    fieldValuesColumns: [
      {fieldId: "field_1", columnId: "A"},
      {fieldId: "field_2", columnId: "B"}
    ]
  }) {
    recordsImportation {
      id
      status
    }
  }
}
```

### Bulk Updates
- No native bulk update mutation
- Use batched mutations with aliases
- Maximum ~50 mutations per request

Example:
```graphql
mutation {
  update1: updateCardField(input: {card_id: 1, field_id: "f1", new_value: "v1"}) {
    card { id }
  }
  update2: updateCardField(input: {card_id: 2, field_id: "f1", new_value: "v2"}) {
    card { id }
  }
  # ... up to ~50 updates
}
```

## Data Export

### Report Export
```graphql
mutation {
  exportPipeReport(input: {
    pipeId: 123,
    reportId: 456
  }) {
    pipeReportExport {
      id
      state
      fileURL
      requestedByUser
      startedAt
      requestedAt
    }
  }
}
```

### Export Formats
- JSON (native GraphQL response)
- CSV/Excel (requires external conversion)
- PDF (for specific reports)

### Export Limitations
- 50 requests per 24 hours per pipe
- Large exports may timeout
- JSON to CSV conversion needed externally

## Rate Limits and Pagination

### API Rate Limits
- Plan-based monthly API call limits
- Per-endpoint specific limits:
  - Pipe Reports Export: 25 requests/24 hours per pipe
  - General API calls: Varies by plan

### Pagination Requirements
- **Maximum page size**: 50 items
- **Default page size**: 30-50 items
- **Required for large datasets**

### Pagination Implementation
```graphql
query {
  cards(pipe_id: 123, first: 50) {
    edges {
      node {
        id
        title
      }
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
  }
}

# Next page
query {
  cards(pipe_id: 123, first: 50, after: "endCursor_value") {
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
```

### Cursor Usage
- `endCursor` + `after`: Next page
- `startCursor` + `before`: Previous page
- Cursors are base64-encoded strings
- Must be properly escaped in JSON

## Migration Considerations

### Critical Points for Migration

1. **Authentication Migration**
   - Convert to OAuth2 Bearer tokens
   - Migrate from Personal Access Tokens to Service Accounts
   - Store tokens securely

2. **Data Model Mapping**
   - Map source system entities to Pipefy objects
   - Consider Pipe vs Table for different data types
   - Plan field type conversions

3. **Relationship Preservation**
   - Maintain parent-child relationships
   - Map connection fields properly
   - Preserve referential integrity

4. **Permission Migration**
   - Map roles appropriately
   - Preserve access controls
   - Migrate team structures

5. **Automation Translation**
   - Convert business rules to Pipefy automations
   - Map triggers and actions
   - Handle email templates

6. **File Migration**
   - Maximum 512MB per file
   - Special character restrictions
   - Use presigned URLs for uploads

7. **Incremental Migration Strategy**
   - Use pagination for large datasets
   - Implement retry logic for rate limits
   - Track migration progress
   - Handle partial failures

8. **Data Validation**
   - Verify required fields
   - Check unique constraints
   - Validate field formats
   - Test conditional logic

9. **Performance Considerations**
   - Batch operations where possible
   - Respect rate limits
   - Use efficient pagination
   - Monitor API usage

10. **Rollback Planning**
    - Maintain source data backup
    - Track migrated entity IDs
    - Plan reverse migration if needed

## Sample GraphQL Queries

### 1. Get Organization Structure
```graphql
query GetOrganization {
  organization(id: 123) {
    id
    name
    pipes {
      id
      name
      phases {
        id
        name
        cards_count
      }
    }
    tables {
      id
      name
      table_records_count
    }
  }
}
```

### 2. Create Card with Fields
```graphql
mutation CreateCard {
  createCard(input: {
    pipe_id: 123,
    title: "New Card",
    fields_attributes: [
      {field_id: "title", field_value: "Card Title"},
      {field_id: "description", field_value: "Card Description"},
      {field_id: "due_date", field_value: "2024-12-31"},
      {field_id: "assignee", field_value: ["user@example.com"]}
    ],
    parent_ids: [456],
    label_ids: [789]
  }) {
    card {
      id
      title
      current_phase {
        name
      }
    }
  }
}
```

### 3. Search Cards with Filters
```graphql
query SearchCards {
  findCards(
    pipeId: 123,
    search: {
      fieldId: "status",
      fieldValue: "active",
      operator: EQUAL
    },
    first: 50
  ) {
    edges {
      node {
        id
        title
        current_phase {
          name
        }
        fields {
          name
          value
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### 4. Update Multiple Card Fields
```graphql
mutation UpdateCardFields {
  updateFieldsValues(input: {
    nodeId: "Card-123",
    values: [
      {fieldId: "status", value: "completed"},
      {fieldId: "completion_date", value: "2024-06-15"},
      {fieldId: "notes", value: "Successfully migrated"}
    ]
  }) {
    card {
      id
      fields {
        name
        value
      }
    }
  }
}
```

### 5. Create Table Record
```graphql
mutation CreateTableRecord {
  createTableRecord(input: {
    table_id: 456,
    title: "New Record",
    fields_attributes: [
      {field_id: "name", field_value: "John Doe"},
      {field_id: "email", field_value: "john@example.com"},
      {field_id: "department", field_value: "Engineering"}
    ]
  }) {
    table_record {
      id
      title
      record_fields {
        name
        value
      }
    }
  }
}
```

### 6. Get Pipe with Complete Details
```graphql
query GetPipeDetails {
  pipe(id: 123) {
    id
    name
    start_form_fields {
      id
      label
      type
      required
      options
    }
    phases {
      id
      name
      fields {
        id
        label
        type
        required
      }
      cards(first: 10) {
        edges {
          node {
            id
            title
            assignees {
              name
              email
            }
            labels {
              name
              color
            }
          }
        }
      }
    }
    labels {
      id
      name
      color
    }
    members {
      user {
        name
        email
      }
      role_name
    }
  }
}
```

### 7. Move Card Between Phases
```graphql
mutation MoveCard {
  moveCardToPhase(input: {
    card_id: 789,
    destination_phase_id: 456
  }) {
    card {
      id
      current_phase {
        id
        name
      }
      started_current_phase_at
    }
  }
}
```

### 8. Create Webhook
```graphql
mutation CreateWebhook {
  createOrganizationWebhook(input: {
    organization_id: 123,
    name: "Migration Webhook",
    url: "https://myapp.com/webhooks/pipefy",
    headers: "{\"Authorization\": \"Bearer secret\"}",
    actions: ["card.create", "card.move", "card.field_update"]
  }) {
    webhook {
      id
      name
      url
      actions
    }
  }
}
```

### 9. Introspection Query
```graphql
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
    queryType {
      fields {
        name
        args {
          name
          type {
            name
            kind
          }
        }
      }
    }
    mutationType {
      fields {
        name
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

### 10. Export Report
```graphql
mutation ExportReport {
  exportPipeReport(input: {
    pipeId: 123,
    reportId: 456
  }) {
    pipeReportExport {
      id
      state
      fileURL
      startedAt
      requestedAt
    }
  }
}
```

## Summary

Pipefy's GraphQL API provides comprehensive access to all platform features with:
- Strong typing and introspection capabilities
- Extensive object model covering workflows, data, and users
- Rich mutation set for all CRUD operations
- Robust relationship management
- Advanced features like SLA, automations, and webhooks
- Rate limiting requiring careful pagination
- Migration-friendly bulk import capabilities

Key limitations for migration:
- No native bulk update operations
- 50-item pagination limits
- Rate limits on API calls and exports
- File size and naming restrictions
- Limited to admin/super admin access
- JSON-only native export format