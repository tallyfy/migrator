# Pipefy to Tallyfy Migration System

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚨 Critical Notice: Fundamental Platform Differences

**This migration involves a PARADIGM SHIFT from Kanban (Pipefy) to Sequential Checklist (Tallyfy)**. Users will need significant retraining and process adaptation.

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Critical Architecture Differences](#critical-architecture-differences)
- [Quick Start](#quick-start)
- [What Gets Migrated](#what-gets-migrated)
- [⚠️ What Does NOT Get Migrated](#️-what-does-not-get-migrated)
- [Major Limitations & Workarounds](#major-limitations--workarounds)
- [Migration Strategy](#migration-strategy)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Post-Migration Tasks](#post-migration-tasks)

## System Overview

This migration system transforms Pipefy's card-based Kanban workflow system into Tallyfy's sequential checklist model. Due to fundamental architectural differences, this is not a simple data transfer but a complete workflow transformation.

### Technology Stack

- **Source**: Pipefy GraphQL API
- **Target**: Tallyfy REST API
- **External Dependencies**: PostgreSQL/Airtable (for database tables), S3 (for large files)
- **Languages**: Python 3.9+
- **Key Libraries**: GraphQL client, transformation pipeline, external integrations

## Critical Architecture Differences

| Aspect | Pipefy | Tallyfy | Impact |
|--------|--------|---------|--------|
| **Workflow Model** | Kanban board with phases | Sequential checklist | **Complete redesign required** |
| **Progress Model** | Cards move between phases | Tasks complete in order | **Different user experience** |
| **Visualization** | Board view with columns | List view | **Loss of visual overview** |
| **Database Tables** | Native database functionality | None | **External solution required** |
| **Automation** | Event-driven with triggers | Step-completion based | **Rebuild automations** |
| **Connections** | Card relationships and dependencies | No native support | **Metadata workaround only** |

## Quick Start

### Prerequisites

1. **Pipefy Requirements:**
   - Admin or Super Admin access
   - API Token (Settings → API & Webhooks → Personal Access Token)
   - Organization ID (Organization Settings → General)

2. **Tallyfy Requirements:**
   - Admin access to target organization
   - OAuth2 credentials (Admin → API → OAuth Applications)
   - Organization ID and slug

3. **System Requirements:**
   - Python 3.9 or higher
   - PostgreSQL 12+ (for database tables)
   - 8GB RAM minimum
   - 50GB free disk space

4. **Optional External Services:**
   - AWS S3 or similar (for files > 100MB)
   - n8n/Zapier/Make (for complex automations)
   - Airtable (alternative to PostgreSQL)

### Installation

```bash
# Clone the repository
cd /path/to/migrator/pipefy

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials
```

### Running the Migration

```bash
# Simple migration (all pipes)
./migrate.sh

# Dry run to test without changes
./migrate.sh --dry-run

# Migrate specific pipe only
./migrate.sh --pipe-id 12345

# Generate analysis report only
./migrate.sh --report-only

# Skip database table migration
./migrate.sh --skip-tables

# Resume from checkpoint
./migrate.sh --resume

# Show help
./migrate.sh --help
```

### Python Direct Execution

```bash
# With specific configuration
python src/main.py --config config/migration_config.yaml --dry-run

# Specific phases only
python src/main.py --phase discovery --phase users --phase pipes

# Validate existing migration
python src/main.py --validate-only
```

## What Gets Migrated

### ✅ Successfully Migrated

1. **Organizations & Users**
   - Organization structure
   - User accounts and profiles
   - Basic role assignments

2. **Pipes → Checklists**
   - Pipe name and description
   - Public/private settings
   - Basic member assignments

3. **Phases → Step Groups**
   - Each phase becomes 3 steps:
     1. Entry notification step
     2. Work completion step
     3. Exit/routing decision step

4. **Cards → Processes**
   - Card title and description
   - Assignees
   - Due dates
   - Current status (active/completed)
   - Labels as tags

5. **Fields → field (Basic Types)**
   - Short text → Text input
   - Long text → Text area
   - Number → Number input
   - Date → Date picker
   - Select → Dropdown
   - Email → Email input
   - Checkbox → Yes/No

6. **Comments**
   - Text content
   - Author attribution
   - Timestamps

7. **Attachments**
   - Files < 100MB directly
   - Files > 100MB via S3 links

## ⚠️ What Does NOT Get Migrated

### ❌ Not Supported - No Workaround

1. **Database Tables** - Must use external PostgreSQL
2. **Card Connections/Dependencies** - No Tallyfy equivalent
3. **Conditional Logic in Forms** - Rebuild manually
4. **Public Forms** - Different mechanism in Tallyfy
5. **Email Templates** - Recreate in Tallyfy
6. **Card Metrics/SLA** - Use external analytics
7. **Time Tracking** - No native support
8. **Custom Integrations** - Rebuild via API

### ⚠️ Partially Supported

1. **Automations** → External platform (n8n/Zapier)
2. **Webhooks** → Basic events only
3. **Reports** → Export data, use external tools
4. **Field Formulas** → Store as text, calculate externally
5. **Dynamic Content** → Static snapshot only

## Major Limitations & Workarounds

### 1. Database Tables (Critical)

**Problem**: Pipefy's database tables have no Tallyfy equivalent.

**Solution**:
```bash
# Set up PostgreSQL
export DATABASE_URL=postgresql://user:pass@localhost:5432/pipefy_data

# Tables will be automatically created during migration
# Access via generated API wrapper at http://localhost:8000
```

**Alternative**: Use Airtable with API integration.

### 2. Workflow Paradigm Shift

**Problem**: Kanban board → Sequential checklist is fundamentally different.

**Impact**:
- Users can't drag cards between phases
- No visual board overview
- Progress is linear, not parallel
- Can't skip steps easily

**Mitigation**:
- Train users on new workflow
- Create detailed documentation
- Consider keeping Pipefy for visual needs

### 3. Complex Automations

**Problem**: Pipefy's automations are more sophisticated.

**Solution**: Use n8n/Zapier/Make
```json
// Example automation migration
{
  "pipefy_trigger": "card.move",
  "pipefy_condition": "phase.name == 'Approved'",
  "pipefy_action": "send_email",
  
  "tallyfy_equivalent": {
    "webhook": "process.step_completed",
    "external_platform": "n8n",
    "workflow_id": "wf_12345"
  }
}
```

### 4. Phase Transformation Complexity

Each Pipefy phase becomes 3 Tallyfy steps:

```
Pipefy Phase: "Review"
↓
Tallyfy Steps:
1. "📥 Entering Review Phase" (notification)
2. "📝 Complete Review Tasks" (work)
3. "➡️ Route to Next Phase" (decision)
```

This triples the number of steps and changes the user experience significantly.

## Migration Strategy

### Recommended Approach

1. **Phase 1: Analysis (1-2 days)**
   ```bash
   ./migrate.sh --report-only
   ```
   - Review generated report
   - Identify critical issues
   - Plan external system setup

2. **Phase 2: Test Migration (2-3 days)**
   ```bash
   ./migrate.sh --dry-run
   ```
   - Validate transformations
   - Test with subset of data
   - Train key users

3. **Phase 3: Setup External Systems (3-5 days)**
   - Configure PostgreSQL for tables
   - Set up S3 for large files
   - Configure n8n/Zapier for automations
   - Create API wrappers

4. **Phase 4: Production Migration (1-2 days)**
   ```bash
   ./migrate.sh
   ```
   - Run during low-activity period
   - Monitor progress
   - Validate results

5. **Phase 5: Parallel Operation (30 days)**
   - Keep both systems running
   - Gradually transition users
   - Fix issues as they arise
   - Gather feedback

## Configuration

### Environment Variables (.env)

```bash
# Pipefy (Source)
PIPEFY_API_TOKEN=your_token_here
PIPEFY_ORG_ID=123456

# Tallyfy (Target)
TALLYFY_API_URL=https://api.tallyfy.com
TALLYFY_CLIENT_ID=your_client_id
TALLYFY_CLIENT_SECRET=your_secret
TALLYFY_ORG_ID=your_org_id
TALLYFY_ORG_SLUG=your_org_slug

# External Systems
DATABASE_URL=postgresql://user:pass@localhost:5432/pipefy_data
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=migration-files

# Automation Platform
AUTOMATION_WEBHOOK_URL=https://your-n8n.com/webhook/migration
```

### Configuration File (config/migration_config.yaml)

```yaml
migration:
  phases:
    - discovery
    - users
    - pipes
    - cards
    - tables
    - automations
    - validation
  
  phase_config:
    cards:
      batch_size: 20
      include_completed: true
      preserve_dates: true
    
    tables:
      external_database: postgresql
      create_api_wrapper: true
      
  options:
    continue_on_error: true
    parallel_processing: false
    checkpoint_enabled: true
```

## Troubleshooting

### Common Issues

1. **GraphQL Timeout**
   ```bash
   # Increase timeout in .env
   GRAPHQL_TIMEOUT=60
   ```

2. **Rate Limiting**
   ```bash
   # Reduce batch size
   BATCH_SIZE_CARDS=10
   ```

3. **Memory Issues**
   ```bash
   # Process in smaller chunks
   ./migrate.sh --pipe-id 12345  # One pipe at a time
   ```

4. **Database Connection Failed**
   ```bash
   # Check PostgreSQL is running
   psql -U postgres -c "SELECT 1"
   ```

5. **Large File Upload Failed**
   ```bash
   # Check S3 credentials
   aws s3 ls s3://your-bucket/
   ```

### Logs and Reports

- **Main log**: `logs/pipefy_migration_YYYYMMDD_HHMMSS.log`
- **Error log**: `logs/pipefy_errors_YYYYMMDD_HHMMSS.log`
- **Reports**: `reports/migration_report.json`
- **Checkpoints**: `checkpoints/migration_*/checkpoint.json`

## Post-Migration Tasks

### Required Manual Steps

1. **Configure External Database Access**
   ```bash
   # Start API wrapper
   cd migrator/pipefy
   python database_api.py
   ```

2. **Set Up Automations**
   - Review `automations_to_configure.json`
   - Create workflows in n8n/Zapier
   - Test each automation

3. **User Training**
   - Document new workflows
   - Create video tutorials
   - Conduct training sessions

4. **Validation**
   ```bash
   python src/main.py --validate-only
   ```

5. **Performance Optimization**
   - Index database tables
   - Optimize API wrapper queries
   - Configure caching

### Rollback Plan

If migration fails:

1. **Immediate**: Stop migration process
2. **Restore**: Use Pipefy as primary system
3. **Cleanup**: Remove partial data from Tallyfy
4. **Analysis**: Review logs for root cause
5. **Retry**: Fix issues and restart migration


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


## Support and Maintenance

### Monitoring

- Check migration logs daily
- Monitor external database performance
- Track user adoption metrics
- Review automation success rates

### Regular Tasks

- **Daily**: Check error logs
- **Weekly**: Validate data integrity
- **Monthly**: Optimize database, clean up logs

### Getting Help

1. Review this README and logs
2. Check GraphQL query examples in `docs/graphql_queries.md`
3. Consult transformation logic in `src/transformers/`
4. Review field mappings in `docs/field_mapping.md`

## License

Proprietary - Internal Use Only

## Disclaimer

This migration tool fundamentally transforms workflows from Kanban to Sequential. Expect significant changes in user experience and business processes. Always test thoroughly before production migration.