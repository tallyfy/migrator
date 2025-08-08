# Tallyfy API & Data Model Analysis

## Executive Summary

Tallyfy is an AI-powered workflow management SaaS platform built with Laravel 12 and PostgreSQL. It uses a sophisticated multi-tenant architecture with organizations as isolated tenants. The system implements a template-instance pattern where workflow templates (checklists) create running instances (runs/processes).

## Database Architecture

### Schema Organization

The database uses multiple PostgreSQL schemas for logical separation:

- **`core`** - Primary business logic and workflow data
- **`history`** - Audit trails and statistical tracking
- **`oauth`** - Laravel Passport authentication
- **`public`** - Laravel migrations and framework tables
- **`recycle`** - Soft-deleted items storage
- **`devel`** - Development utilities
- **`pganalyze`** - Performance monitoring

### ID Generation Patterns

1. **32-character hash IDs** - Primary entities use UUID-based IDs without hyphens
   - Generated via `core.gen_id()` function
   - Used for: organizations, checklists, runs, steps, tasks, users, etc.

2. **Sequential integer IDs** - Used for pivot tables and relationships
   - organizations_users, organizations_guests, activity_feeds, etc.

## Core Data Objects

### 1. Organizations (Multi-Tenant Root)

**Table**: `core.organizations`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `name` - Organization name
- `slug` - URL-friendly identifier
- `owner_id` - Primary admin user
- `subscription` (JSONB) - Recurly billing data
- `signup_params` (JSONB) - Registration configuration
- `working_days` (JSONB) - Schedule configuration
- `timezone` - Organization timezone
- `api_calls` - Usage counter
- `free_trial_days` - Trial period
- `analytics_enabled` - Analytics feature flag

**API Endpoints**:
- `GET /organizations/{org}` - Get organization details
- `PUT /organizations/{org}` - Update organization
- `GET /current-user/{user_id}/organizations` - List user's organizations

**Constraints**:
- All data is tenant-isolated by organization_id
- Organizations can have custom domains
- Support for custom SMTP configurations

### 2. Templates/Blueprints (Checklists)

**Table**: `core.checklists`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `organization_id` - Tenant isolation
- `timeline_id` - Version tracking identifier
- `version` - Version number
- `frozen_at` - Immutability timestamp
- `title` - Template name
- `summary` - Description
- `owner_id` - Creator user
- `is_public` - Public library flag
- `icon` - Visual identifier
- `type` - Template type
- `prerun` - Kickoff form configuration
- `webhook` - Integration URL
- `auto_naming` - Process naming rules
- `folderize_process` - Auto-folder organization
- `tag_process` - Auto-tagging rules

**API Endpoints**:
- `GET /organizations/{org}/checklists` - List templates
- `POST /organizations/{org}/checklists` - Create template
- `GET /organizations/{org}/checklists/{id}` - Get template
- `PUT /organizations/{org}/checklists/{id}` - Update template
- `DELETE /organizations/{org}/checklists/{id}` - Delete template
- `POST /organizations/{org}/checklists/{id}/clone` - Clone template

**Versioning System**:
- Templates use Git-like versioning with timeline_id linking versions
- Major/minor version updates supported
- Frozen versions preserved for audit

### 3. Processes/Runs (Active Workflows)

**Table**: `core.runs`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `organization_id` - Tenant isolation
- `checklist_id` - Source template
- `name` - Process name
- `summary` - Process description
- `owner_id` - Process owner
- `status` - Current state (not-started, in-progress, completed, cancelled)
- `started_at` - Start timestamp
- `completed_at` - Completion timestamp
- `due_at` - Due date
- `is_public` - Public visibility
- `folder_id` - Organization folder
- `archived_at` - Archive timestamp

**API Endpoints**:
- `GET /organizations/{org}/runs` - List processes
- `POST /organizations/{org}/runs` - Create process from template
- `GET /organizations/{org}/runs/{id}` - Get process details
- `PUT /organizations/{org}/runs/{id}` - Update process
- `DELETE /organizations/{org}/runs/{id}` - Delete process
- `POST /organizations/{org}/runs/{id}/complete` - Complete process
- `POST /organizations/{org}/runs/{id}/archive` - Archive process

### 4. Tasks/Steps

**Table**: `core.steps` (Template level)
**Table**: `core.run_tasks` (Instance level)

**Step Properties** (Template):
- `id` (VARCHAR 32) - Primary key
- `checklist_id` - Parent template
- `title` - Step name
- `summary` - Description
- `step_type` - Type (task, approval, form, email, expiring)
- `position` - Order in workflow
- `deadline` (JSONB) - Deadline configuration
- `start_date` (JSONB) - Start date rules
- `required` - Required flag
- `hidden` - Visibility flag
- `guidance` - Instructions

**Task Properties** (Instance):
- `id` (VARCHAR 32) - Primary key
- `run_id` - Parent process
- `step_id` - Source step template
- `title` - Task name
- `status` - Current state
- `task_type` - Type (task, approval, expiring, email)
- `deadline` - Due date
- `completed_at` - Completion timestamp
- `is_approved` - Approval status
- `is_oneoff_task` - Standalone task flag

**Task Types & Status**:
- **task** - Standard task → completed
- **approval** - Approval task → approved/rejected
- **expiring** - Time-sensitive → acknowledged/expired
- **email** - Email task → sent
- **expiring_email** - Combined type

**API Endpoints**:
- `GET /organizations/{org}/runs/{run_id}/tasks` - List tasks
- `GET /organizations/{org}/tasks/{id}` - Get task details
- `PUT /organizations/{org}/tasks/{id}` - Update task
- `POST /organizations/{org}/tasks/{id}/complete` - Complete task
- `POST /organizations/{org}/tasks/{id}/approve` - Approve task
- `POST /organizations/{org}/tasks/{id}/reject` - Reject task

### 5. Forms & Fields (Captures)

**Table**: `core.captures`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `class_id` - Parent entity (step/checklist)
- `alias` - Field identifier
- `field_type` - Type (text, number, date, dropdown, etc.)
- `label` - Display label
- `guidance` - Help text
- `required` - Required flag
- `options` - Choice options for dropdowns
- `position` - Display order
- `validation_rule` - Validation pattern

**Field Types**:
- Text (small/large)
- Number
- Date/DateTime
- Dropdown/Select
- Radio buttons
- Checkboxes
- File upload
- Image
- Signature
- Location

**API Endpoints**:
- `GET /organizations/{org}/checklists/{id}/form-fields` - Get template fields
- `POST /organizations/{org}/form-field/value` - Submit field value
- `GET /organizations/{org}/runs/{id}/form-fields` - Get process fields

### 6. Users & Roles

**Table**: `core.users`

**Key Properties**:
- `id` (INTEGER) - Primary key
- `firstname` - First name
- `lastname` - Last name
- `email` - Email address
- `password` - Hashed password
- `activated` - Account status
- `timezone` - User timezone
- `locale` - Language preference
- `profile_pic` - Avatar URL

**Table**: `core.organizations_users` (Relationship)
- `organization_id` - Organization
- `user_id` - User
- `role` - User role (owner, admin, member, light)
- `status` - Membership status

**Roles**:
- **Owner** - Full control
- **Admin** - Administrative access
- **Member** - Standard user
- **Light** - Limited access

**API Endpoints**:
- `GET /organizations/{org}/users` - List users
- `POST /organizations/{org}/users` - Invite user
- `GET /organizations/{org}/users/{id}` - Get user
- `PUT /organizations/{org}/users/{id}` - Update user
- `DELETE /organizations/{org}/users/{id}` - Remove user

### 7. Guests (External Participants)

**Table**: `core.guests`

**Key Properties**:
- `id` (INTEGER) - Primary key
- `firstname` - First name
- `lastname` - Last name
- `email` - Email address
- `password` - Optional password

**Table**: `core.organizations_guests` (Relationship)
- `organization_id` - Organization
- `guest_id` - Guest
- `guest_code` (VARCHAR 32) - Access token

**API Endpoints**:
- `GET /organizations/{org}/guests` - List guests
- `POST /organizations/{org}/guests` - Create guest
- `GET /organizations/{org}/guests/{guest}` - Get guest
- Guest access via guest_code parameter

### 8. Groups/Teams

**Table**: `core.groups`

**Key Properties**:
- `id` (INTEGER) - Primary key
- `organization_id` - Tenant
- `name` - Group name
- `description` - Description

**Relationships**:
- `core.groups_members` - User membership
- `core.groups_guests` - Guest membership

**API Endpoints**:
- `GET /organizations/{org}/groups` - List groups
- `POST /organizations/{org}/groups` - Create group
- `PUT /organizations/{org}/groups/{id}` - Update group
- `DELETE /organizations/{org}/groups/{id}` - Delete group

### 9. Comments & Threads

**Table**: `core.threads`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `organization_id` - Tenant
- `thread_participant_id` - Participants
- `body` - Comment text
- `parent_id` - Parent comment
- `subject_id` - Related entity
- `subject_type` - Entity type

**API Endpoints**:
- `POST /organizations/{org}/tasks/{id}/comment` - Add comment
- `GET /organizations/{org}/tasks/{id}/comments` - List comments
- `PUT /organizations/{org}/comments/{id}` - Update comment
- `DELETE /organizations/{org}/comments/{id}` - Delete comment

### 10. Files & Attachments

**Table**: `core.assets`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `organization_id` - Tenant
- `filename` - File name
- `mimetype` - File type
- `size` - File size
- `url` - Storage URL
- `subject_id` - Related entity
- `subject_type` - Entity type

**Storage**:
- Files stored in AWS S3
- Support for image resizing
- Access control via permissions

**API Endpoints**:
- `POST /organizations/{org}/upload` - Upload file
- `GET /organizations/{org}/file/{id}` - Download file
- `DELETE /organizations/{org}/file/{id}` - Delete file

### 11. Webhooks

**Table**: `core.recurring_jobs` (Webhook delivery)

**Webhook Events**:
- Process created/updated/completed
- Task created/updated/completed
- User added/removed
- Guest added/removed

**Configuration**:
- Set webhook URL per checklist
- Retry logic for failed deliveries
- Signature verification

### 12. Integrations

**Supported Integrations**:
- **Recurly** - Billing and subscriptions
- **PubNub** - Real-time messaging
- **AWS S3** - File storage
- **Mailgun** - Email delivery
- **SAML2** - Enterprise SSO
- **OAuth2** - API authentication

### 13. Permissions System

**Table**: `core.checklist_permissions`
**Table**: `core.run_permissions`

**Permission Types**:
- CHECKLIST_READ - View template
- CHECKLIST_EDIT - Edit template
- PROCESS_LAUNCH - Start process
- CHECKLIST_DUPLICATE - Clone template
- PROCESS_READ - View process

**Access Control**:
- Role-based (owner, admin, member, light)
- Entity-specific permissions
- Guest access via codes

### 14. Custom Fields

Custom fields are implemented through the captures system with support for:
- Dynamic field types
- Validation rules
- Conditional logic
- Required/optional settings
- Default values

### 15. Conditional Logic

**Table**: `core.rules`

**Key Properties**:
- `id` (VARCHAR 32) - Primary key
- `step_id` - Related step
- `rule_type` - Type of rule
- `condition` - Logic condition
- `action` - Action to perform

**Supported Conditions**:
- Field values
- Task completion
- User roles
- Date/time rules

### 16. Activity & Audit Trail

**Table**: `core.activity_feeds`

**Key Properties**:
- `id` (BIGSERIAL) - Primary key
- `organization_id` - Tenant
- `type` - Activity type
- `actor_type` - User/Guest/System
- `actor_id` - Actor identifier
- `auditable_type` - Entity type
- `auditable_id` - Entity ID
- `verb` - Action verb
- `description` - Human-readable description
- `old_value` - Previous value
- `audit_state` - Current state

**Tracked Events**:
- All CRUD operations
- Status changes
- Permission changes
- Login/logout events

## API Authentication

### Methods

1. **OAuth2 via Laravel Passport**
   - Personal access tokens
   - Client credentials
   - Password grant

2. **API Tokens**
   - Bearer token authentication
   - Token expiration management

3. **Guest Access**
   - Guest codes for limited access
   - No authentication required for public endpoints

### Authentication Headers
```http
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: application/json
```

## Data Import Capabilities

### Supported Import Methods

1. **API-based Import**
   - RESTful API endpoints for all entities
   - Bulk operations supported
   - Transactional consistency

2. **CSV Import** (Limited)
   - Users import
   - Basic data fields only

3. **Template Cloning**
   - Cross-organization copying
   - Version preservation
   - Full hierarchy duplication

### Import Constraints

1. **Rate Limits**
   - API calls tracked per organization
   - Throttling on endpoints

2. **Data Validation**
   - Required field validation
   - Type checking
   - Referential integrity

3. **Size Limits**
   - File uploads: Configurable via S3
   - Bulk operations: Chunked processing recommended

## Required vs Optional Fields

### Organizations (Required)
- `id` - Organization ID
- `name` - Organization name
- `owner_id` - Primary admin

### Checklists/Templates (Required)
- `id` - Template ID
- `organization_id` - Tenant
- `title` - Template name
- `timeline_id` - Version tracking
- `version` - Version number

### Runs/Processes (Required)
- `id` - Process ID
- `organization_id` - Tenant
- `checklist_id` - Source template
- `name` - Process name

### Tasks (Required)
- `id` - Task ID
- `organization_id` - Tenant
- Either `run_id` OR `is_oneoff_task=true`
- `title` - Task name

### Users (Required)
- `email` - Email address
- `firstname` - First name
- `lastname` - Last name

### Guests (Required)
- `email` - Email address
- `firstname` - First name
- `lastname` - Last name

## Object Relationships

### Primary Relationships

1. **Organization → Users** (Many-to-Many via organizations_users)
2. **Organization → Guests** (Many-to-Many via organizations_guests)
3. **Organization → Checklists** (One-to-Many)
4. **Checklist → Steps** (One-to-Many)
5. **Checklist → Runs** (One-to-Many)
6. **Run → Tasks** (One-to-Many)
7. **Step → Task** (Template-to-Instance)
8. **Tasks → Users/Guests** (Many-to-Many assignments)
9. **Groups → Users/Guests** (Many-to-Many membership)

### Hierarchical Structure
```
Organization
├── Users
├── Guests  
├── Groups
├── Checklists (Templates)
│   ├── Steps
│   ├── Captures (Form Fields)
│   └── Rules (Conditional Logic)
├── Runs (Processes)
│   └── Tasks
├── Assets (Files)
├── Comments/Threads
└── Activity Feed
```

## Migration Considerations

### Critical Considerations

1. **ID Mapping**
   - Tallyfy uses 32-char hash IDs for primary entities
   - Sequential integers for relationships
   - Must maintain referential integrity

2. **Multi-Tenancy**
   - All data must include organization_id
   - Tenant isolation is enforced at middleware level
   - Cross-tenant operations not supported

3. **Versioning System**
   - Templates use timeline-based versioning
   - Frozen versions preserved
   - Version history must be maintained

4. **Permissions**
   - Complex permission matrix
   - Role-based + entity-specific
   - Guest access via codes

5. **JSONB Fields**
   - PostgreSQL-specific JSONB columns
   - Complex nested structures
   - GIN indexes for performance

### Migration Strategy Recommendations

1. **Phase 1: Core Data**
   - Organizations
   - Users and roles
   - Basic authentication

2. **Phase 2: Templates**
   - Checklists
   - Steps
   - Form fields

3. **Phase 3: Processes**
   - Runs
   - Tasks
   - Assignments

4. **Phase 4: Collaboration**
   - Comments
   - Files
   - Guest access

5. **Phase 5: Advanced Features**
   - Conditional logic
   - Webhooks
   - Integrations

### Data Validation Requirements

1. **Referential Integrity**
   - All foreign keys must be valid
   - Orphaned records not allowed
   - Cascade deletes configured

2. **Business Rules**
   - Status transitions validated
   - Permission checks enforced
   - Tenant isolation maintained

3. **Data Types**
   - PostgreSQL strict type checking
   - JSONB structure validation
   - Timestamp timezone handling

## API Limitations

1. **No Built-in Versioning**
   - Single API version only
   - No backward compatibility

2. **Caching**
   - Handled by Cloudflare CDN
   - No application-level caching

3. **Rate Limiting**
   - Per-organization limits
   - API call counting
   - Throttling middleware

4. **Bulk Operations**
   - Limited bulk endpoints
   - Chunking recommended
   - Transaction size limits

## Security Considerations

1. **Authentication**
   - OAuth2 bearer tokens
   - Token expiration
   - Refresh token rotation

2. **Authorization**
   - Role-based access control
   - Entity-level permissions
   - Tenant isolation

3. **Data Protection**
   - HTTPS required
   - Input validation
   - SQL injection prevention
   - XSS protection

## Performance Optimizations

1. **Database**
   - PostgreSQL with optimized indexes
   - JSONB GIN indexes
   - Query optimization

2. **Caching**
   - Cloudflare CDN
   - Edge caching
   - Static asset optimization

3. **Background Jobs**
   - Queue-based processing
   - Async operations
   - Job retry logic

## Conclusion

Tallyfy's API provides comprehensive workflow management capabilities with sophisticated multi-tenancy, versioning, and permission systems. The platform's architecture supports complex workflows while maintaining data isolation and security. Key challenges for migration include:

1. Complex ID mapping (32-char hashes)
2. Multi-tenant data isolation
3. Template versioning system
4. JSONB data structures
5. Permission matrix complexity

Successful migration requires careful planning, phased approach, and thorough testing of data integrity and business rules.