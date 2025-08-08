# Monday.com to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## Overview

The Monday.com to Tallyfy Migrator is a comprehensive tool designed to migrate your entire Monday.com workspace to Tallyfy. This includes boards, items, users, teams, and all associated data. The migrator handles the complex paradigm shift from Monday's flexible view system (Table/Kanban/Timeline/Calendar) to Tallyfy's sequential workflow model.

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start](#quick-start)
5. [Architecture](#architecture)
6. [Data Mapping](#data-mapping)
7. [API Integration](#api-integration)
8. [Features](#features)
9. [Usage Examples](#usage-examples)
10. [Paradigm Shifts](#paradigm-shifts)
11. [Limitations](#limitations)
12. [Migration Process](#migration-process)
13. [Error Handling](#error-handling)
14. [Performance](#performance)
15. [Troubleshooting](#troubleshooting)
16. [Best Practices](#best-practices)
17. [Support](#support)

## Requirements

- Python 3.8 or higher
- Monday.com API token (Admin access recommended)
- Tallyfy API key and organization
- 4GB RAM minimum (8GB recommended for large workspaces)
- Network connectivity to both Monday.com and Tallyfy APIs

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd migrator/monday
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

### Required Settings

Edit `.env` file with your credentials:

```env
# Monday.com API Configuration
MONDAY_API_TOKEN=your_monday_api_token_here

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_api_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain
```

### Optional Settings

```env
# API Rate Limiting
MONDAY_RATE_LIMIT=50
TALLYFY_RATE_LIMIT=100

# Batch Sizes
BATCH_SIZE_USERS=50
BATCH_SIZE_ITEMS=100

# Retry Configuration
MAX_RETRIES=3
RETRY_DELAY=5
```

## Quick Start

### Option 1: Interactive Script

```bash
chmod +x migrate.sh
./migrate.sh
```

### Option 2: Direct Python Execution

```bash
# Full migration
python3 -m src.main \
  --api-token YOUR_MONDAY_TOKEN \
  --tallyfy-key YOUR_TALLYFY_KEY \
  --tallyfy-org YOUR_ORG

# Report only (no data created)
python3 -m src.main \
  --api-token YOUR_MONDAY_TOKEN \
  --tallyfy-key YOUR_TALLYFY_KEY \
  --tallyfy-org YOUR_ORG \
  --report-only

# Dry run (simulation)
python3 -m src.main \
  --api-token YOUR_MONDAY_TOKEN \
  --tallyfy-key YOUR_TALLYFY_KEY \
  --tallyfy-org YOUR_ORG \
  --dry-run
```

## Architecture

### 5-Phase Migration Process

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  Discovery  │───▶│    Users    │───▶│  Blueprints  │
└─────────────┘    └─────────────┘    └──────────────┘
                                              │
                                              ▼
                    ┌─────────────┐    ┌──────────────┐
                    │ Validation  │◀───│  Processes   │
                    └─────────────┘    └──────────────┘
```

### Key Components

- **API Clients**: GraphQL v2 client for Monday.com, REST client for Tallyfy
- **Transformers**: Convert Monday.com objects to Tallyfy format
- **ID Mapper**: SQLite-based mapping for cross-references
- **Checkpoint Manager**: Resume capability for failed migrations
- **Error Handler**: Comprehensive error tracking and recovery
- **Progress Tracker**: Real-time migration progress monitoring

## Data Mapping

### Core Object Mappings

| Monday.com | Tallyfy | Notes |
|------------|---------|-------|
| Workspace | Organization | Top-level container |
| Board | Blueprint | Workflow template |
| Item | Process | Running instance |
| Group | Step Group | Logical grouping |
| Column | Form Field | Data field |
| Update | Comment | Communication |
| Subitem | Checklist Item | Nested tasks |
| View | - | Views not directly mapped |

### Field Type Mappings (30+ Types)

| Monday Type | Tallyfy Type | Transformation |
|-------------|--------------|----------------|
| Text | Short Text | Direct mapping |
| Long Text | Long Text | Direct mapping |
| Numbers | Number | With validation |
| Status | Dropdown | Options preserved |
| People | Assignee Picker | User references |
| Date | Date | ISO format |
| Timeline | Date | Start/end split |
| Formula | Short Text (readonly) | Results only |
| Mirror | Short Text (readonly) | Value copy |
| Tags | Checklist | Multi-select |
| File | File Upload | Attachment migration |
| Rating | Number | 1-5 scale |
| ...and 20+ more | | |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete mappings.

## API Integration

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.


### Monday.com GraphQL v2

```graphql
# Example query structure
query {
  boards(limit: 100) {
    id
    name
    columns { id title type }
    groups { id title }
    items { id name column_values }
  }
}
```

- **Authentication**: API Token (Bearer)
- **Rate Limiting**: 10M complexity points/minute
- **Complexity Tracking**: Per-query monitoring
- **Pagination**: Cursor-based with 100-item pages

### Tallyfy REST API

- **Authentication**: API Key header
- **Rate Limiting**: 100 requests/minute
- **Batch Operations**: 50 items per request
- **Error Recovery**: Exponential backoff

## Features

### Core Capabilities

- ✅ Full workspace migration
- ✅ User and team migration
- ✅ Board to blueprint conversion
- ✅ Item to process transformation
- ✅ Column value preservation
- ✅ File attachment migration
- ✅ Comment/update migration
- ✅ Subitem to checklist conversion
- ✅ Permission mapping

### Advanced Features

- ✅ **Checkpoint/Resume**: Automatic recovery from failures
- ✅ **Dry Run Mode**: Preview changes without creating data
- ✅ **Report Mode**: Analyze complexity before migration
- ✅ **Selective Migration**: Choose specific boards
- ✅ **ID Mapping**: Maintain relationships
- ✅ **Progress Tracking**: Real-time status updates
- ✅ **Error Recovery**: Automatic retry with backoff
- ✅ **Validation**: Pre and post-migration checks

## Usage Examples

### Example 1: Migrate Specific Boards

```bash
python3 -m src.main \
  --api-token $MONDAY_TOKEN \
  --tallyfy-key $TALLYFY_KEY \
  --tallyfy-org myorg \
  --board-ids 123456 789012 345678
```

### Example 2: Migrate Specific Workspace

```bash
python3 -m src.main \
  --api-token $MONDAY_TOKEN \
  --tallyfy-key $TALLYFY_KEY \
  --tallyfy-org myorg \
  --workspace-ids ws_123
```

### Example 3: Resume Failed Migration

```bash
python3 -m src.main \
  --api-token $MONDAY_TOKEN \
  --tallyfy-key $TALLYFY_KEY \
  --tallyfy-org myorg \
  --resume
```

## Paradigm Shifts

### Critical Transformation: Kanban → Sequential

Monday's Kanban view allows parallel work across columns. Tallyfy requires sequential task completion.

**Transformation Strategy:**
- Each Kanban column becomes a workflow step
- Cards in columns become tasks within steps
- Column transitions become step completions
- Parallel work converts to sequential progression

### Timeline/Gantt → Linear Workflow

Monday's Timeline view shows dependencies and parallel tracks. Tallyfy uses linear step progression.

**Transformation Strategy:**
- Timeline phases become workflow phases
- Dependencies convert to step order
- Parallel tracks merge into single flow
- Date ranges preserved in step deadlines

### Multiple Views → Single Workflow

Monday boards can have Table, Kanban, Timeline, Calendar, and other views simultaneously. Tallyfy has one sequential workflow.

**Transformation Strategy:**
- Detect primary view type
- Apply view-specific transformation
- Preserve view metadata for reference
- Document view changes in migration notes

## Limitations

### Features Not Migrated

1. **Automations**: Monday automations require manual recreation as Tallyfy rules
2. **Formulas**: Complex formulas migrated as static values
3. **Mirror Columns**: Cross-board references need manual setup
4. **Board Relations**: Connected boards require manual linking
5. **Custom Views**: Gallery, Chart, Map views not supported
6. **Integrations**: Third-party integrations need reconnection
7. **Webhooks**: Must be reconfigured in Tallyfy
8. **Dashboard Widgets**: Not directly transferable

### Data Limitations

- **Item Limit**: 10,000 items per board recommended
- **File Size**: Individual files limited to 100MB
- **Comment Depth**: Nested replies flattened
- **Activity Logs**: Limited history migration

### Manual Post-Migration Tasks

1. Review and adjust workflow steps
2. Recreate automation rules
3. Configure integrations
4. Set up notifications
5. Train users on paradigm changes
6. Validate data accuracy

## Migration Process

### Phase 1: Discovery (5-10 minutes)
- Fetch all workspaces
- Retrieve boards with columns
- Get users and teams
- Count items and complexity
- Generate migration plan

### Phase 2: User Migration (5-15 minutes)
- Transform Monday users to Tallyfy members
- Create teams/groups
- Map user permissions
- Handle guest users
- Establish ID mappings

### Phase 3: Blueprint Creation (10-30 minutes)
- Transform boards to blueprints
- Convert columns to form fields
- Create workflow steps
- Map permissions
- Document paradigm shifts

### Phase 4: Process Migration (30-120 minutes)
- Transform items to processes
- Migrate column values
- Convert subitems to checklists
- Transfer file attachments
- Import comments/updates

### Phase 5: Validation (5 minutes)
- Verify ID mappings
- Check data integrity
- Validate relationships
- Generate report
- Log any issues

## Error Handling

### Automatic Recovery

- **Rate Limiting**: Exponential backoff (30s → 5min → 30min)
- **Network Errors**: 3 retries with delay
- **API Errors**: Categorized handling
- **Data Errors**: Skip and log

### Error Categories

| Category | Description | Action |
|----------|-------------|--------|
| Rate Limit | API limit reached | Wait and retry |
| Authentication | Invalid credentials | Halt migration |
| Network | Connection issues | Retry with backoff |
| Validation | Data validation failed | Skip item, log error |
| Transformation | Conversion error | Use fallback, log warning |

### Error Reporting

Errors are logged to:
- Console output
- `logs/migration_TIMESTAMP.log`
- `.monday_migration/error_log.json`
- Final migration report

## Performance

### Optimization Strategies

1. **Batch Processing**: 50-100 items per API call
2. **Parallel Requests**: When complexity allows
3. **Caching**: In-memory ID mappings
4. **Pagination**: 100-item pages
5. **Complexity Management**: Track GraphQL points

### Expected Performance

| Workspace Size | Migration Time | Memory Usage |
|----------------|----------------|--------------|
| Small (< 1000 items) | 15-30 minutes | < 1GB |
| Medium (1000-10000 items) | 30-90 minutes | 1-2GB |
| Large (10000-50000 items) | 2-6 hours | 2-4GB |
| Enterprise (50000+ items) | 6-24 hours | 4-8GB |

### Rate Limits

- **Monday.com**: 10M complexity points/minute
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 50-100 items/minute

## Troubleshooting

### Common Issues

#### 1. Authentication Failed
```
Error: Invalid API token
Solution: Verify token in .env file, ensure admin access
```

#### 2. Rate Limit Exceeded
```
Error: Too many requests
Solution: Wait 2-3 hours, or reduce batch size
```

#### 3. Memory Error
```
Error: Out of memory
Solution: Process smaller batches, increase system RAM
```

#### 4. Network Timeout
```
Error: Connection timeout
Solution: Check network, retry with --resume flag
```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python3 -m src.main --verbose
```

### Validation Commands

```bash
# Check checkpoint status
python3 -c "from src.utils.checkpoint_manager import CheckpointManager; cm = CheckpointManager(); print(cm.get_checkpoint_info())"

# Verify ID mappings
python3 -c "from src.utils.id_mapper import IDMapper; im = IDMapper(); print(im.get_statistics())"
```

## Best Practices

### Before Migration

1. **Backup Data**: Export Monday.com data
2. **Clean Up**: Archive old items, remove test data
3. **Notify Users**: Inform about downtime and changes
4. **Test Small**: Try with one board first
5. **Review Mappings**: Understand paradigm shifts

### During Migration

1. **Monitor Progress**: Watch console output
2. **Check Logs**: Review for warnings
3. **Avoid Changes**: Don't modify Monday data
4. **Network Stability**: Ensure consistent connection
5. **Resource Monitoring**: Watch memory usage

### After Migration

1. **Validate Data**: Spot-check migrated items
2. **User Training**: Explain new workflow model
3. **Recreate Automations**: Set up Tallyfy rules
4. **Test Workflows**: Run sample processes
5. **Gather Feedback**: Get user input


## 📖 Tallyfy Field Types Reference

### Available Field Types in Tallyfy

Based on the ACTUAL api-v2 implementation, these are the correct field types:

1. **text** - Short text input (max 255 characters)
2. **textarea** - Long text input (max 6000 characters)
3. **radio** - Radio buttons for single selection
4. **dropdown** - Dropdown list for single selection
5. **multiselect** - Multiple choice dropdown
6. **date** - Date picker
7. **email** - Email field with validation
8. **file** - File upload
9. **table** - Table/grid input
10. **assignees_form** - User/guest assignment field

### Critical API Implementation Details

#### ID Formats
- All main entities use **32-character hash strings** (NOT integers)
- Examples: checklist_id, run_id, organization_id, task_id
- Only users and guests use integer IDs

#### API Endpoints (ACTUAL)
- Templates: `/api/organizations/{org_id}/checklists`
- Processes: `/api/organizations/{org_id}/runs`
- Tasks: `/api/organizations/{org_id}/runs/{run_id}/tasks`
- Form fields: `/api/organizations/{org_id}/checklists/{id}/form-fields`

#### Prerun/Kickoff Form Data
- Stored in `field` table with checklist class_id
- Request key is `prerun_data` (object), NOT `prerun` (array)
- Format: `{"field_id": "value"}` not array of objects

#### Field Validation
Instead of `type`, use Laravel validation rules:
- Numeric: `"validation": "numeric|min:0|max:100"`
- Email: `"validation": "email"`
- URL: `"validation": "url"`
- Required: `"required": true`

#### Required Headers
```json
{
  "Authorization": "Bearer {token}",
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```
Note: X-Tallyfy-Client header is NOT required.

### Important API Notes

#### No Direct Number Type
Tallyfy does NOT have a dedicated "number" field type. For numeric inputs:
- Use **short_text** with number validation
- Add validation rules: `{"type": "number", "min": 0, "max": 100}`

#### Special Field Validations
- **Email**: short_text with pattern `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- **Phone**: short_text with pattern `^[\d\s\-\+\(\)]+$`
- **URL**: short_text with pattern `^https?://`
- **Yes/No**: radio_buttons with options `[{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}]`

#### API Endpoints
- Templates: `/organizations/{org_id}/checklists` (NOT /templates)
- Processes: `/organizations/{org_id}/runs` (NOT /processes)
- Kick-off form data uses "prerun" array (NOT "field")

#### Required Headers
All API requests MUST include:
```json
{
  "Authorization": "Bearer {token}",
  "Content-Type": "application/json",
  "Accept": "application/json",
  "X-Tallyfy-Client": "APIClient"  // MANDATORY
}
```


## Support

### Resources

- **Documentation**: See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for detailed mappings
- **Logs**: Check `logs/` directory for detailed output
- **Checkpoints**: Resume from `.monday_migration/`
- **Reports**: Review `migration_report_*.json`

### Comparison

For detailed Monday.com vs Tallyfy comparison:
- https://tallyfy.com/differences/monday-vs-tallyfy/

### Getting Help

1. Check error logs for specific issues
2. Review troubleshooting section
3. Verify API credentials and permissions
4. Ensure network connectivity
5. Check Monday.com API status

---

## License

This migrator is provided as-is for Monday.com to Tallyfy migration purposes.

## Version

Version 1.0.0 - Full-featured Monday.com to Tallyfy migration tool