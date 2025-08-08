# Asana to Tallyfy Migration Tool

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

This production-ready migration tool helps organizations seamlessly transition from Asana to Tallyfy, transforming complex project management structures into streamlined, AI-powered workflows that save 2 hours per person every day.

**Key Benefits:**
- ✅ Complete data migration including users, projects, tasks, and custom fields
- ✅ Handles all Asana layouts (List, Board, Timeline, Calendar)
- ✅ Checkpoint/resume capability for large migrations
- ✅ Comprehensive validation and reporting
- ✅ Paradigm shift handling (Kanban → Sequential workflows)

## 📋 Prerequisites

- Python 3.8 or higher
- Asana Personal Access Token
- Tallyfy API credentials
- 2GB free disk space for large migrations

## 🔧 Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/tallyfy/migrator.git
cd migrator/asana

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use any text editor
```

**Required Configuration:**
```env
ASANA_ACCESS_TOKEN=your_asana_pat_here
TALLYFY_API_TOKEN=your_tallyfy_token_here
TALLYFY_ORG_ID=your_tallyfy_org_id_here
```

### 3. Get Your Credentials

#### Asana Personal Access Token:
1. Go to https://app.asana.com/0/my-apps
2. Click "Create new token"
3. Name it "Tallyfy Migration"
4. Copy the token immediately (shown only once)

#### Tallyfy API Token:

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

1. Log into Tallyfy
2. Go to Settings > Integrations > REST API
3. Copy your personal access token
4. Note your Organization ID

## 🚦 Quick Start

### 1. Run Readiness Check

```bash
./migrate.sh --readiness-check
```

This validates:
- API connectivity
- Credentials
- Permissions
- Workspace access

### 2. Preview Migration (Dry Run)

```bash
./migrate.sh --dry-run
```

Preview what will be migrated without making any changes.

### 3. Execute Migration

```bash
./migrate.sh
```

Run the complete migration with automatic checkpoint saves.

## 📊 Migration Phases

The migration runs in sequential phases:

1. **Discovery** - Analyzes your Asana workspace
2. **Users** - Migrates user accounts and roles
3. **Teams** - Creates Tallyfy groups from Asana teams
4. **Projects** - Transforms projects into Tallyfy blueprints
5. **Tasks** - Migrates active tasks and processes
6. **Validation** - Verifies data integrity

### Run Specific Phases

```bash
# Run only discovery and users phases
./migrate.sh --phases discovery,users

# Run validation only
./migrate.sh --phases validation
```

## 🔄 Advanced Features

### Resume Interrupted Migration

```bash
./migrate.sh --resume
```

Automatically continues from the last checkpoint if migration was interrupted.

### Report-Only Mode

```bash
./migrate.sh --report-only
```

Generates a detailed analysis without performing migration.

### Verbose Logging

```bash
./migrate.sh --verbose
```

Enables DEBUG level logging for troubleshooting.

## 🎯 Paradigm Shifts

### Board View (Kanban) → Sequential Workflow

Asana's Kanban boards are transformed into sequential Tallyfy workflows:

| Asana Board | Tallyfy Workflow |
|------------|------------------|
| Column/Phase | Step Group (3 steps) |
| Card | Process/Task |
| Card Movement | Task Completion |
| Multiple cards per column | Sequential task execution |

**Example Transformation:**
```
Asana Board:
  To Do → In Progress → Review → Done

Tallyfy Workflow:
  1. To Do - Entry (notification)
  2. To Do - Work (actual tasks)
  3. To Do - Exit (approval)
  4. In Progress - Entry
  5. In Progress - Work
  6. In Progress - Exit
  ... and so on
```

### Timeline View → Dependencies

Timeline projects with dependencies are converted to sequential workflows with dependency metadata preserved for reference.

## 📁 Data Mapping

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for detailed field mappings.

### Key Mappings

| Asana | Tallyfy | Notes |
|-------|---------|-------|
| Workspace | Organization | Top-level container |
| Project | Blueprint | Template definition |
| Task | Step/Task | Individual work items |
| Custom Fields | Form Fields | Data field |
| Teams | Groups | User collections |
| Assignee | Member Assignment | User task assignment |

## ⚠️ Known Limitations

### Features Requiring Manual Recreation
- **Portfolios** - No direct equivalent, recreate as blueprint categories
- **Goals** - Use Tallyfy's reporting features instead
- **Status Updates** - Migrate as process comments
- **Inbox** - No equivalent, use Tallyfy notifications

### Partial Support
- **Recurring Tasks** - Use external automation (Zapier/Make)
- **Forms** - Limited to kick-off forms in Tallyfy
- **Rules** - Complex automations need manual recreation
- **Timeline Dependencies** - Preserved as metadata only

### File Size Limits
- Files > 100MB require external storage (S3)
- Configure S3 in .env for automatic handling

## 🔍 Validation

After migration, the tool automatically validates:

- ✅ User account creation
- ✅ Correct role assignments
- ✅ Blueprint structure integrity
- ✅ Task data preservation
- ✅ Custom field mappings
- ✅ File accessibility

### Manual Validation Checklist

1. [ ] Log into Tallyfy and verify user access
2. [ ] Check blueprint templates appear correctly
3. [ ] Verify custom fields in kick-off forms
4. [ ] Test launching a process from migrated blueprint
5. [ ] Confirm file attachments are accessible
6. [ ] Review task assignments and deadlines

## 📈 Performance

### Typical Migration Times

| Workspace Size | Estimated Time |
|---------------|----------------|
| Small (< 10 projects, < 50 users) | 10-30 minutes |
| Medium (10-50 projects, 50-200 users) | 30-90 minutes |
| Large (50-200 projects, 200-500 users) | 2-4 hours |
| Enterprise (200+ projects, 500+ users) | 4-8 hours |

### Rate Limits

- **Free Asana**: 150 requests/minute
- **Paid Asana**: 1,500 requests/minute
- **Tallyfy**: 100 requests/minute

The tool automatically handles rate limiting with exponential backoff.

## 🐛 Troubleshooting

### Common Issues

#### "Workspace not found"
```bash
# Specify workspace explicitly
export ASANA_WORKSPACE_GID=your_workspace_gid
./migrate.sh
```

#### Rate Limit Errors
```bash
# Reduce request rate
export RATE_LIMIT=60  # Requests per minute
export API_DELAY=1    # Seconds between calls
```

#### Memory Issues (Large Workspaces)
```bash
# Process in smaller batches
export BATCH_SIZE=50
./migrate.sh --phases users
./migrate.sh --phases projects --resume
```

#### Authentication Failures
1. Regenerate tokens in both systems
2. Verify tokens are copied correctly (no spaces)
3. Check organization/workspace IDs

### Debug Mode

```bash
# Enable detailed API logging
export VERBOSE_API_LOGGING=true
export SAVE_API_RESPONSES=true
./migrate.sh --verbose
```

## 📊 Reports

Migration reports are saved to `reports/` directory:

```
reports/
├── migration_report_20240115_143022.json  # Full JSON report
└── migration_summary_20240115_143022.txt  # Human-readable summary
```

### Report Contents
- Migration statistics
- Entity counts (source vs target)
- Processing times per phase
- Error logs
- Validation results
- ID mappings

## 🔒 Security

- Credentials are never logged
- API tokens stored locally in .env
- SSL/TLS for all API communications
- Checkpoint data encrypted at rest
- No data sent to third parties


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


## 🆘 Support

### Free Migration Assistance
Tallyfy provides **free 1:1 migration support** for Enterprise customers:
- Expert guidance throughout migration
- Custom script modifications if needed
- Post-migration training
- 30-day success guarantee

Contact: migrations@tallyfy.com

### Community Support
- GitHub Issues: https://github.com/tallyfy/migrator/issues
- Discord: https://discord.gg/tallyfy
- Forum: https://community.tallyfy.com

## 📚 Additional Resources

- [Asana API Documentation](https://developers.asana.com/)
- [Tallyfy API Documentation](https://api.tallyfy.com/docs)
- [Asana vs Tallyfy Comparison](https://tallyfy.com/asana-alternative/)
- [Migration Best Practices](https://tallyfy.com/migration-guide/)

## 📄 License

MIT License - See [LICENSE](../../LICENSE) file

---

**Built with ❤️ by Tallyfy**

*Empowering organizations to run AI-powered operations and save 2 hours per person every day.*