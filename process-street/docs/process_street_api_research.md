# Process Street API Comprehensive Research Document

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Authentication & Access](#authentication--access)
3. [API Architecture](#api-architecture)
4. [Complete Data Models & Objects](#complete-data-models--objects)
5. [API Endpoints](#api-endpoints)
6. [Rate Limits & Pagination](#rate-limits--pagination)
7. [Data Export Capabilities](#data-export-capabilities)
8. [Webhooks & Integrations](#webhooks--integrations)
9. [Migration Considerations](#migration-considerations)
10. [Limitations & Constraints](#limitations--constraints)

---

## Executive Summary

Process Street is a compliance operations platform that provides API access for workflow automation and process management. The API is RESTful, returns JSON responses, and requires Enterprise plan access for full API utilization.

### Key Highlights
- **Base URL**: `https://public-api.process.st/`
- **Authentication**: API Key-based (X-API-KEY header)
- **Format**: JSON responses, OpenAPI specification
- **Plan Requirement**: Enterprise plan required for API access
- **Last Updated**: May 10, 2024

### Important Notes
- Process Street recently renamed domain entities, but API endpoints still use old naming conventions
- The API is designed for ETL/ELT workloads and doesn't support incremental loads
- Full data refreshes are recommended over incremental updates

---

## Authentication & Access

### Authentication Method
- **Type**: API Key Authentication
- **Header**: `X-API-KEY: <api_key>`
- **Protocol**: HTTPS-only
- **Management**: Only administrators can create and manage API keys

### Example Authentication
```bash
curl --header "X-API-KEY: <api_key>" https://public-api.process.st/checklists
```

### Access Requirements
- Must be an organization administrator to generate API keys
- Enterprise plan required for API access
- API keys are organization-specific
- Keys managed from integrations page in organization manager area

---

## API Architecture

### Technical Specifications
- **Protocol**: REST API over HTTPS
- **Response Format**: JSON
- **Documentation Format**: OpenAPI specification
- **Error Handling**: Standard HTTP response codes
- **Request Methods**: GET, POST, PUT, DELETE

### Naming Convention Issues
**CRITICAL**: Process Street renamed domain entities in the application, but API endpoints retain old naming:
- API uses "checklists" instead of "workflow runs"
- API uses "templates" instead of "workflows"
- This mismatch can cause confusion when mapping between API and UI

---

## Complete Data Models & Objects

### 1. Organizations/Workspaces
- **Description**: Top-level container for all Process Street data
- **Key Properties**:
  - Organization ID
  - Name
  - Settings
  - Billing information
  - Plan type (impacts API access)

### 2. Workflows (Templates in API)
- **API Name**: Templates
- **Description**: Blueprint defining how a process should be completed
- **Key Properties**:
  - Template ID
  - Name
  - Description
  - Task templates
  - Form field definitions
  - Conditional logic rules
  - Default assignments
  - Permissions

### 3. Workflow Runs (Checklists in API)
- **API Name**: Checklists
- **Description**: Active running instance of a workflow/template
- **States**: Active, Completed, Archived
- **Key Properties**:
  - Checklist ID
  - Template ID (source)
  - Name
  - Status
  - Due date
  - Share link status
  - Created date
  - Modified date
  - Form field values

### 4. Tasks
- **Description**: Individual steps within a workflow run
- **Pagination**: Listed in groups of 20
- **Key Properties**:
  - Task ID
  - Task name
  - Status (completed/not completed)
  - Due date and time
  - Assignees (users or groups)
  - Stop task flag
  - Hidden status (via permissions)
  - Required field indicators
  - Task order/position

### 5. Form Fields
- **Description**: Data collection elements within tasks
- **Types**:
  - Short text
  - Long text
  - Date/time
  - Number
  - Dropdown
  - Checkbox
  - File upload
  - Email
  - URL
  - Member selector
  - Table fields
- **Key Properties**:
  - Field ID
  - Field type
  - Label
  - Required flag
  - Default value
  - Validation rules
  - Variable name (for references)
  - Multiple values support

### 6. Form Field Values
- **Description**: Actual data entered in form fields
- **Formats**:
  - Simple string
  - Array (for multiple values)
  - Object (for complex properties)
- **Pagination**: Paged results, use links section for navigation

### 7. Users
- **Types**:
  - **Admins**: Full organization control
  - **Members**: Create/edit processes
  - **Guests (Internal)**: Limited internal access
  - **Guests (External)**: Client/vendor access
  - **Guests (Anonymous)**: No login required
  - **API Keys**: System users
- **Key Properties**:
  - User ID
  - Email
  - Name
  - Role
  - Permissions
  - Group memberships

### 8. Groups
- **Description**: Collections of users for bulk assignments
- **Key Properties**:
  - Group ID
  - Name
  - Members (Admins and Members only)
  - Permissions
  - Default access levels
- **Special Group**: "All Organization" - includes all members by default

### 9. Permissions
- **Levels**:
  - Organization level
  - Folder level
  - Workflow level
  - Task level
- **Types**:
  - View
  - Edit
  - Complete
  - Admin
- **Task Visibility Controls**:
  - All Organization
  - All Guests (External)
  - Share link access
  - Specific user/group assignments

### 10. Approvals
- **Description**: Special tasks requiring sign-off
- **Pagination**: Returned 20 at a time, sorted by task order
- **Key Properties**:
  - Approval ID
  - Task ID
  - Approver
  - Status (pending/approved/rejected)
  - Comments
  - Timestamp
  - Resubmission capability

### 11. Assignments
- **Description**: Links between users/groups and tasks/checklists
- **Key Properties**:
  - Assignment ID
  - User/Group ID
  - Task/Checklist ID
  - Assignment type
  - Due date impacts

### 12. Comments
- **Description**: Discussion threads on workflow runs
- **Triggers**: Can trigger automations when posted
- **Key Properties**:
  - Comment ID
  - Author
  - Content
  - Timestamp
  - Attachments
  - Parent (for threading)

### 13. File Attachments
- **Description**: Files attached to comments or form fields
- **Storage Limits**:
  - Startup plan: 5MB per file
  - Enterprise plan: Custom limits
- **Key Properties**:
  - File ID
  - Name
  - Size
  - Type
  - URL
  - Upload date

### 14. Data Sets
- **Description**: Structured data storage for records
- **Limits**:
  - Maximum 10,000 records per import/export
  - Maximum 50 columns per record
  - Maximum 5KB per record
- **Operations**:
  - Add records
  - Update records
  - Delete records
  - Search by fields
  - Conditional creation

### 15. Webhooks
- **Types**:
  - **Incoming**: Trigger workflow runs from external events
  - **Outgoing**: Send data when Process Street events occur
- **Events**:
  - Workflow run completed
  - Task ready
  - Task completed
  - Comment posted
  - File attached
  - Data set record changes
- **Methods**: POST, PUT, GET

### 16. Activity Feed
- **Description**: Audit trail of all actions
- **Includes**:
  - User actions
  - System events
  - Timestamps
  - Change details

### 17. Dynamic Due Dates
- **Description**: Automatically calculated deadlines
- **Triggers**:
  - Date form field values
  - Task completion
  - Workflow run due date
  - Relative offsets

### 18. Conditional Logic
- **Description**: Show/hide tasks or fields based on conditions
- **Based On**:
  - Form field values
  - Task completion status
  - User properties
  - Group membership

### 19. Role Assignments
- **Description**: Dynamic task assignment based on roles
- **Properties**:
  - Role definition
  - Assignment rules
  - Fallback assignments

### 20. Stop Tasks
- **Description**: Tasks that block progress until completed
- **Properties**:
  - Enforcement of task order
  - Hand-off facilitation
  - Accountability tracking

---

## API Endpoints

### Core Endpoints (Confirmed)

#### Workflows (Templates)
- `GET /templates` - List all workflows
- `GET /templates/{id}` - Get specific workflow
- `GET /templates/{id}/tasks` - List tasks by workflow ID
- `GET /templates/{id}/form-fields` - List form fields by workflow ID

#### Workflow Runs (Checklists)
- `GET /checklists` - List workflow runs
- `POST /checklists` - Create new workflow run
- `GET /checklists/{id}` - Get specific workflow run
- `PUT /checklists/{id}` - Update workflow run
- `DELETE /checklists/{id}` - Delete workflow run
- `GET /checklists/search` - Search by name or form field value

#### Tasks
- `GET /checklists/{id}/tasks` - List tasks (paginated, 20 per page)
- `PUT /tasks/{id}` - Update task
- `POST /tasks/{id}/complete` - Complete task
- `PUT /tasks/{id}/assignees` - Update task assignees

#### Form Fields
- `GET /tasks/{id}/form-field-values` - Get form field values (paginated)
- `PUT /form-field-values/{id}` - Update form field value
- `POST /form-field-values/bulk` - Update multiple values

#### Users & Groups
- `GET /users` - List users (paginated)
- `GET /groups` - List groups
- `POST /groups` - Create group
- `PUT /groups/{id}` - Update group
- `POST /users/invite` - Invite member
- `POST /guests` - Create guest

#### Assignments
- `GET /assignments` - List assignments (paginated)
- `POST /checklists/{id}/assign` - Assign user to workflow run
- `DELETE /checklists/{id}/unassign` - Unassign user

#### Approvals
- `GET /checklists/{id}/approvals` - List approvals (20 per page)
- `POST /approvals/{id}/approve` - Approve task
- `POST /approvals/{id}/reject` - Reject task

#### Data Sets
- `GET /datasets` - List data sets
- `POST /datasets/{id}/records` - Add record
- `PUT /datasets/{id}/records/{recordId}` - Update record
- `DELETE /datasets/{id}/records/{recordId}` - Delete record
- `GET /datasets/{id}/search` - Search records

---

## Rate Limits & Pagination

### Rate Limiting
- **Status**: No specific documented rate limits
- **Recommendation**: Implement client-side rate limiting
- **Error Handling**: Must handle 429 (Too Many Requests) responses
- **Retry-After**: Respect header if provided

### Pagination Strategy
- **Default Page Size**: 20 items for most endpoints
- **Navigation**: Use `links` section in response for next/previous pages
- **Pattern**: Consistent across all list endpoints
- **Example Response Structure**:
```json
{
  "data": [...],
  "links": {
    "next": "https://public-api.process.st/resource?page=2",
    "previous": null,
    "first": "https://public-api.process.st/resource?page=1",
    "last": "https://public-api.process.st/resource?page=10"
  }
}
```

---

## Data Export Capabilities

### CSV Export
- **Primary Method**: CSV export for workflow runs
- **Access**: Available to Admins and Members
- **Methods**:
  1. Export from Reports area (most flexible)
  2. Direct export from workflow view
- **Customization**: Select specific columns or export all
- **Content Includes**:
  - Workflow run status
  - All tasks
  - Form field values
  - Assignees
  - Timestamps (in UTC)
  - Comments
  - Custom columns

### Data Set Export
- **Format**: CSV only
- **Limits**:
  - 10,000 records maximum
  - 50 columns maximum
  - 5KB per record maximum
- **Use Case**: Bulk data transfer between systems

### JSON Export
- **Native Support**: Not available
- **Workaround**: Use API to fetch and construct JSON

### Backup Strategy
- **Method**: CSV exports serve as primary backup
- **Frequency**: Manual process
- **Automation**: Possible via API scripting

---

## Webhooks & Integrations

### Webhook Capabilities

#### Outgoing Webhooks (Events)
- Workflow run completed
- Task ready for work
- Task completed
- Comment posted
- File attached to comment
- Data set record added
- Data set record updated
- Data set record deleted

#### Incoming Webhooks
- Trigger workflow runs
- Update form fields
- Complete tasks
- Add comments

### Native Integrations

#### Zapier Integration (7,000+ apps)
- **Triggers**: All major Process Street events
- **Actions**: Create, update, search operations
- **Popular Connections**:
  - Google Workspace
  - Microsoft 365
  - Slack
  - Salesforce
  - HubSpot

#### Power Automate
- **Availability**: 400+ Microsoft services
- **Features**: Full workflow automation
- **Limitations**: Regional restrictions

#### Direct Integrations
- Slack (Enterprise Grid for Enterprise plan)
- Microsoft Teams
- Google Drive
- Dropbox
- Box
- OneDrive
- Asana
- Azure Active Directory (Enterprise)
- SAML SSO (Enterprise)

---

## Migration Considerations

### Key Migration Challenges

1. **No Incremental Sync**
   - API designed for full ETL/ELT workloads
   - No change tracking or delta updates
   - Must implement own change detection

2. **Naming Mismatches**
   - API uses old terminology
   - Requires mapping layer between API and current UI terms

3. **Plan Requirements**
   - Enterprise plan required for API access
   - Limits migration testing on lower plans

4. **Data Volume Limits**
   - 10,000 record limit for data sets
   - Pagination required for large datasets
   - No bulk operations for workflow runs

5. **Export Limitations**
   - CSV only, no native JSON export
   - Manual process for comprehensive backups
   - Time zones in UTC (conversion needed)

### Migration Strategy Recommendations

1. **Phased Approach**
   - Start with organizational structure (users, groups)
   - Then workflows/templates
   - Finally, active workflow runs and data

2. **Data Mapping Requirements**
   - Create translation layer for terminology
   - Map Process Street objects to target system
   - Handle complex conditional logic and approvals

3. **Testing Considerations**
   - Use sandbox/staging environment
   - Test pagination handling
   - Verify file attachment migration
   - Validate permission mappings

4. **Performance Optimization**
   - Batch API calls where possible
   - Implement caching for static data
   - Use parallel processing for independent operations
   - Monitor API response times

---

## Limitations & Constraints

### Technical Limitations

1. **API Access**
   - Enterprise plan only
   - Administrator privileges required
   - Organization-specific API keys

2. **Data Operations**
   - No bulk update operations
   - No transaction support
   - No rollback capabilities
   - No versioning/history via API

3. **Search Capabilities**
   - Limited search parameters
   - No complex queries
   - Basic filtering only

4. **Real-time Features**
   - No WebSocket support
   - No real-time notifications
   - Polling required for updates

### Business Constraints

1. **Pricing**
   - Enterprise plan pricing is custom
   - Contact sales required
   - No trial API access

2. **Support**
   - Limited documentation
   - No public OpenAPI spec file
   - Developer support via enterprise plan only

3. **Rate Limits**
   - Undocumented limits
   - No quota information
   - Risk of unexpected throttling

### Data Constraints

1. **File Storage**
   - 5MB limit on Startup plan
   - Custom limits on Enterprise
   - No bulk file operations

2. **Record Limits**
   - 10,000 records per data set operation
   - 50 columns maximum
   - 5KB per record maximum

3. **Pagination**
   - Fixed 20 items per page for most endpoints
   - No page size customization
   - Sequential navigation only

---

## Conclusion

Process Street's API provides comprehensive access to workflow automation features but has significant limitations for migration purposes:

### Strengths
- Complete object model coverage
- RESTful design
- Good integration ecosystem
- Comprehensive webhook support

### Weaknesses
- Enterprise-only access
- No incremental sync
- Limited bulk operations
- Terminology mismatches
- Undocumented rate limits

### Migration Feasibility
Migration is technically feasible but requires:
- Enterprise plan access
- Custom change tracking implementation
- Terminology mapping layer
- Robust error handling
- Potentially significant development effort

### Recommended Next Steps
1. Obtain Enterprise API access for testing
2. Build proof-of-concept for critical data types
3. Implement comprehensive error handling
4. Create data validation framework
5. Plan for manual verification of migrated data

---

*Document Last Updated: 2025-08-07*
*Based on Process Street API documentation last updated: May 10, 2024*