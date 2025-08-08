# Process Street to Tallyfy Migration System

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🎯 Overview

This enterprise-grade migration system provides a comprehensive solution for migrating data from Process Street to Tallyfy. It handles the complete transfer of organizations, users, workflows (templates), checklists (workflow runs), form data, comments, and associated metadata while maintaining data integrity and relationships.

## ✅ Production Ready

- **Enhanced API Client**: Fully updated for Process Street API v1.1 with proper pagination and error handling
- **Readiness Checks**: Built-in validation before migration
- **Checkpoint/Resume**: Interrupt and resume migrations safely
- **Comprehensive Logging**: Detailed logs for debugging and audit trails
- **Dry Run Mode**: Test migrations without making changes

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Migration Phases](#migration-phases)
- [What Gets Migrated](#what-gets-migrated)
- [What Does NOT Get Migrated](#what-does-not-get-migrated)
- [Known Limitations](#known-limitations)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [API Compatibility](#api-compatibility)

## System Requirements

### Process Street Requirements
- **Enterprise Plan** (required for API access)
- API Key from Settings → API & Webhooks → Personal Access Token
- Administrator or appropriate permissions
- Organization ID (optional, auto-detected)

### Tallyfy Requirements
- OAuth2 credentials from Admin → API → OAuth Applications
- Organization ID and slug
- Administrator access

### Technical Requirements
- Python 3.9 or higher
- 4GB RAM minimum
- 10GB free disk space (for data and logs)
- Network access to both APIs
- Linux/macOS/Windows with WSL

## Quick Start

### 1. Installation

```bash
# Clone or navigate to the migration directory
cd /path/to/migrator/process-street

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configure Credentials

Edit `.env` file:
```bash
# Process Street (Source)
PROCESS_STREET_API_KEY=your_api_key_here
PS_ORGANIZATION_ID=  # Optional, will auto-detect

# Tallyfy (Target)
TALLYFY_CLIENT_ID=your_client_id
TALLYFY_CLIENT_SECRET=your_client_secret
TALLYFY_ORG_ID=your_org_id
TALLYFY_ORG_SLUG=your_org_slug
```

### 3. Run Migration

```bash
# Check readiness
./migrate.sh --readiness-check

# Dry run (recommended first)
./migrate.sh --dry-run

# Full migration
./migrate.sh

# With specific options
./migrate.sh --phase discovery --phase users
./migrate.sh --workflow-id abc123
./migrate.sh --resume  # Resume interrupted migration
```

## Configuration

### Environment Variables (.env)

The system uses environment variables for sensitive configuration. See `.env.example` for all available options.

Key variables:
- `PROCESS_STREET_API_KEY`: Your Process Street API key
- `TALLYFY_CLIENT_ID/SECRET`: OAuth2 credentials
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
- `BATCH_SIZE`: Items per batch (default: 20)
- `CONTINUE_ON_ERROR`: Continue if items fail (default: true)

### Configuration File (config/migration_config.yaml)

```yaml
source:
  api_key: ${PROCESS_STREET_API_KEY}
  base_url: https://public-api.process.st/api/v1.1
  organization_id: ${PS_ORGANIZATION_ID}

target:
  api_url: ${TALLYFY_API_URL}
  client_id: ${TALLYFY_CLIENT_ID}
  client_secret: ${TALLYFY_CLIENT_SECRET}
  organization_id: ${TALLYFY_ORG_ID}
  organization_slug: ${TALLYFY_ORG_SLUG}

migration:
  phases:
    - discovery
    - users
    - groups
    - templates
    - instances
    - comments
    - files
    - webhooks
    - validation
  
  options:
    continue_on_error: true
    checkpoint_enabled: true
    batch_size: 20
```

## Migration Phases

The migration runs in sequential phases:

### 1. Discovery Phase
- Analyzes Process Street organization
- Counts all objects
- Estimates migration time
- Identifies potential issues

### 2. Users Phase
- Migrates all users
- Preserves roles and permissions
- Maps Process Street IDs to Tallyfy IDs

### 3. Groups Phase
- Creates user groups
- Assigns members

### 4. Templates Phase (Workflows)
- Converts Process Street workflows to Tallyfy checklists
- Migrates tasks and steps
- Transforms form fields to field

### 5. Instances Phase (Checklists)
- Migrates active workflow runs
- Preserves completion status
- Maintains form field values

### 6. Comments Phase
- Transfers all comments
- Maintains threading
- Preserves timestamps

### 7. Files Phase
- Downloads and re-uploads attachments
- Handles large files via S3 (optional)

### 8. Webhooks Phase
- Recreates webhooks
- Maps events

### 9. Validation Phase
- Verifies data integrity
- Checks ID mappings
- Reports any issues

## What Gets Migrated

### ✅ Fully Supported

| Process Street | Tallyfy | Notes |
|----------------|---------|-------|
| Workflows (Templates) | Checklists | Complete structure preserved |
| Tasks | Steps | Including order and dependencies |
| Form Fields | field | All standard field types |
| Checklists (Runs) | Processes | Active and completed |
| Users | Users | Roles mapped appropriately |
| Groups | Groups | With member assignments |
| Comments | Comments | Full thread history |
| File Attachments | Files | Up to 100MB directly |
| Webhooks | Webhooks | Event mapping |
| Assignments | Assignments | User-to-process links |
| Due Dates | Due Dates | Preserved exactly |

### ✅ Field Type Mappings

| Process Street Field | Tallyfy field | Notes |
|---------------------|-----------------|-------|
| Text | Text Input | Single line |
| Text Area | Text Area | Multi-line |
| Email | Email | With validation |
| URL | URL | With validation |
| Number | Number | Integer/decimal |
| Date | Date Picker | Date only |
| Date & Time | DateTime | Full timestamp |
| Dropdown | Select | Single choice |
| Multiple Choice | Checkbox Group | Multiple selections |
| File Upload | File Attachment | Max 100MB |
| Member | User Select | User assignment |

## What Does NOT Get Migrated

### ❌ Not Supported

1. **Data Sets** - No Tallyfy equivalent (export separately)
2. **Conditional Logic** - Must be recreated manually
3. **Dynamic Due Dates** - Convert to static dates
4. **Stop Tasks** - Different workflow model
5. **Approval Tasks** - Use Tallyfy's approval system
6. **Role-Based Assignments** - Recreate role logic
7. **Public Forms** - Different implementation
8. **Integrations** - Must reconnect (Zapier, etc.)
9. **Activity History** - Only current state migrated
10. **Custom Branding** - Reconfigure in Tallyfy

### ⚠️ Limitations

1. **API Quotas**: Process Street API requires Enterprise plan
2. **Rate Limits**: Automatic handling with backoff
3. **Large Files**: Files > 100MB need S3 or external storage
4. **Bulk Operations**: Limited to 20 items per batch
5. **Historical Data**: Only migrates current state, not full history

## Usage Examples

### Basic Migration

```bash
# Full migration with all phases
./migrate.sh

# Dry run first (recommended)
./migrate.sh --dry-run
```

### Selective Migration

```bash
# Specific workflow only
./migrate.sh --workflow-id abc123

# Specific phases
./migrate.sh --phase users --phase templates

# Skip validation
./migrate.sh --phase discovery --phase users --phase templates
```

### Advanced Usage

```bash
# Generate report only
./migrate.sh --report-only

# Validate previous migration
./migrate.sh --validate-only

# Resume interrupted migration
./migrate.sh --resume

# Custom configuration
CONFIG_FILE=custom_config.yaml ./migrate.sh
```

### Python Direct Usage

```python
from src.main import MigrationOrchestrator

# Initialize
orchestrator = MigrationOrchestrator('config/migration_config.yaml')

# Run readiness check
readiness = orchestrator.run_readiness_check()

# Run migration
orchestrator.run(
    phases=['users', 'templates'],
    dry_run=True,
    workflow_id='specific_workflow_id'
)
```

## API Compatibility

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.


### Process Street API v1.1

This migrator is fully compatible with Process Street API v1.1:
- Proper pagination using links
- Correct endpoints (`/workflows`, `/checklists`)
- Response format handling (`data`, `links`, `meta`)
- Rate limiting with exponential backoff
- Enterprise plan validation

### Tallyfy API v2

Compatible with Tallyfy's REST API:
- OAuth2 authentication
- Batch operations
- File upload support
- Webhook management

## Troubleshooting

### Common Issues

#### 1. Authentication Failed
```
Error: Failed to validate Process Street API key
```
**Solution**: Verify API key and Enterprise plan status

#### 2. Rate Limiting
```
Warning: Rate limit hit, waiting 60 seconds
```
**Solution**: Automatic handling, migration will continue

#### 3. Memory Issues
```
Error: Out of memory
```
**Solution**: Process in smaller batches:
```bash
./migrate.sh --phase users
./migrate.sh --phase templates --workflow-id specific_id
```

#### 4. Network Timeouts
```
Error: Request timeout after 30 seconds
```
**Solution**: Check network connectivity, API status

#### 5. Partial Migration
```
Migration interrupted at phase: templates
```
**Solution**: Resume from checkpoint:
```bash
./migrate.sh --resume
```

### Logs and Debugging

- **Main Log**: `logs/process_street_migration_YYYYMMDD_HHMMSS.log`
- **Error Log**: `logs/process_street_errors_YYYYMMDD_HHMMSS.log`
- **API Calls**: Set `LOG_LEVEL=DEBUG` in `.env`
- **Reports**: `reports/migration_report.json`

### Getting Help

1. Check logs for detailed error messages
2. Run readiness check: `./migrate.sh --readiness-check`
3. Try dry run mode: `./migrate.sh --dry-run`
4. Validate API access manually
5. Check Process Street API status

## Recovery Procedures

### Checkpoint Recovery

The system automatically saves progress:
```bash
# Resume from last checkpoint
./migrate.sh --resume

# Check checkpoint status
ls -la data/checkpoints/
cat data/checkpoints/migration_*/checkpoint.json
```

### Manual Recovery

If automatic recovery fails:
1. Check last successful phase in logs
2. Review ID mappings: `sqlite3 data/mappings.db`
3. Run specific phase: `./migrate.sh --phase <phase_name>`
4. Validate results: `./migrate.sh --validate-only`

### Rollback

To undo a migration:
1. Keep Process Street as primary system
2. Delete migrated data in Tallyfy (use with caution)
3. Clear ID mappings: `rm data/mappings.db`
4. Start fresh migration

## Performance Optimization

### For Large Migrations

1. **Batch Processing**:
   ```bash
   # Process workflows individually
   for id in $(cat workflow_ids.txt); do
     ./migrate.sh --workflow-id $id
   done
   ```

2. **Parallel Workers** (experimental):
   ```bash
   PARALLEL_WORKERS=4 ./migrate.sh
   ```

3. **Increase Batch Size**:
   ```bash
   BATCH_SIZE=50 ./migrate.sh  # Default is 20
   ```

4. **Skip Validation**:
   ```bash
   ./migrate.sh --phase discovery --phase users --phase templates
   # Run validation separately later
   ./migrate.sh --validate-only
   ```

## Post-Migration Tasks

### Required Steps

1. **Verify Data**:
   - Check user accounts in Tallyfy
   - Test workflow functionality
   - Validate form fields

2. **Update Integrations**:
   - Reconnect Zapier/Make/n8n
   - Update webhook URLs
   - Configure notifications

3. **User Training**:
   - Document changes
   - Create training materials
   - Schedule sessions

4. **Parallel Operation**:
   - Keep both systems for 30 days
   - Gradually transition users
   - Monitor for issues

### Validation Checklist

- [ ] All users migrated and can log in
- [ ] Workflows appear correctly as checklists
- [ ] Active processes show correct status
- [ ] Form data preserved accurately
- [ ] Comments and attachments accessible
- [ ] Webhooks firing correctly
- [ ] Permissions and assignments correct


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

### Before Running Migration

1. **Backup**: Export Process Street data
2. **Test**: Run dry-run mode first
3. **Plan**: Schedule during low-activity period
4. **Communicate**: Notify users of migration

### During Migration

- Monitor logs in real-time
- Check progress indicators
- Be ready to resume if interrupted
- Keep Process Street accessible

### After Migration

- Validate all data
- Train users on Tallyfy
- Monitor for issues
- Keep Process Street as backup for 30 days

## License

Proprietary - Internal Use Only

## Changelog

### Version 2.0.0 (Current)
- Complete rewrite for Process Street API v1.1
- Enhanced error handling and retry logic
- Readiness checks and validation
- Checkpoint/resume capability
- Comprehensive logging
- Production-ready status

### Version 1.0.0
- Initial implementation
- Basic migration functionality

---

**Note**: This migration tool is designed for one-time data transfer. For ongoing synchronization, consider using integration platforms like Zapier or custom webhooks.