# Asana to Tallyfy Migration Tool

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🔗 Getting Started with Tallyfy

- **📚 Migration Documentation**: [https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/](https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/)
- **🔌 Open API Documentation**: [https://go.tallyfy.com/api/](https://go.tallyfy.com/api/)
- **🚀 Start Free Trial**: [https://tallyfy.com/start/](https://tallyfy.com/start/)
- **📞 Schedule a Call**: [https://tallyfy.com/booking/](https://tallyfy.com/booking/)

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

### Pagination Handling Implementation

```python
class AsanaClient:
    def __init__(self):
        self.client = asana.Client.access_token(self.token)
        self.page_size = 100  # Asana's max
        
    def get_all_tasks(self, project_gid):
        """Handle Asana's offset-based pagination"""
        all_tasks = []
        offset = None
        
        while True:
            # Asana uses offset token for pagination
            options = {
                'limit': self.page_size,
                'opt_fields': 'name,notes,completed,assignee,custom_fields,due_on,dependencies'
            }
            if offset:
                options['offset'] = offset
                
            result = self.client.tasks.find_by_project(project_gid, options)
            
            # Result is a generator with next_page info
            page_tasks = list(result)
            all_tasks.extend(page_tasks)
            
            # Check for next page
            if hasattr(result, '_next_page') and result._next_page:
                offset = result._next_page.get('offset')
            else:
                break
                
        return all_tasks
    
    def handle_rate_limits(self, func, *args, **kwargs):
        """Asana-specific rate limit handling"""
        max_retries = 5
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except asana.error.RateLimitEnforcedError as e:
                # Asana provides retry-after in seconds
                retry_after = e.retry_after or (base_delay * (2 ** attempt))
                logger.warning(f"Rate limited. Waiting {retry_after}s")
                time.sleep(retry_after)
            except asana.error.InvalidTokenError:
                logger.error("Invalid token - check permissions")
                raise
                
        raise Exception(f"Max retries exceeded for {func.__name__}")
```

### Custom Fields Mapping

```python
def map_custom_fields(self, asana_field):
    """Map Asana custom field types to Tallyfy"""
    
    FIELD_TYPE_MAPPING = {
        'text': 'text',
        'number': 'text',  # With numeric validation
        'enum': 'dropdown',
        'multi_enum': 'multiselect',
        'date': 'date',
        'people': 'assignees_form'
    }
    
    tallyfy_field = {
        'name': asana_field['name'],
        'type': FIELD_TYPE_MAPPING.get(asana_field['type'], 'text'),
        'required': asana_field.get('is_required', False)
    }
    
    # Handle special cases
    if asana_field['type'] == 'number':
        tallyfy_field['validation'] = 'numeric'
        if asana_field.get('precision'):
            tallyfy_field['validation'] += f"|decimal:{asana_field['precision']}"
            
    elif asana_field['type'] in ['enum', 'multi_enum']:
        # Map enum options
        tallyfy_field['options'] = [
            {
                'value': opt['gid'],
                'label': opt['name'],
                'color': opt.get('color', '#000000')
            }
            for opt in asana_field.get('enum_options', [])
        ]
        
    elif asana_field['type'] == 'people':
        # Map to user selection with multi-select
        tallyfy_field['allow_multiple'] = True
        tallyfy_field['allow_guests'] = True
        
    return tallyfy_field
```

### Task Dependencies Handling

```python
def transform_dependencies(self, task_with_deps):
    """
    Asana has complex dependency graphs, Tallyfy uses sequential steps
    Strategy: Convert to step groups with dependency metadata
    """
    
    dependency_map = {}
    step_order = []
    
    # Build dependency graph
    for task in task_with_deps:
        deps = task.get('dependencies', [])
        dependency_map[task['gid']] = {
            'task': task,
            'depends_on': [d['gid'] for d in deps],
            'dependents': []
        }
    
    # Find dependents (reverse mapping)
    for gid, info in dependency_map.items():
        for dep_gid in info['depends_on']:
            if dep_gid in dependency_map:
                dependency_map[dep_gid]['dependents'].append(gid)
    
    # Topological sort for sequential order
    visited = set()
    
    def visit(gid):
        if gid in visited:
            return
        visited.add(gid)
        
        # Visit dependencies first
        for dep_gid in dependency_map[gid]['depends_on']:
            if dep_gid in dependency_map:
                visit(dep_gid)
                
        step_order.append(gid)
    
    # Start with tasks that have no dependencies
    for gid, info in dependency_map.items():
        if not info['depends_on']:
            visit(gid)
    
    # Handle remaining (circular dependencies)
    for gid in dependency_map:
        visit(gid)
    
    # Convert to Tallyfy steps
    tallyfy_steps = []
    for i, gid in enumerate(step_order):
        task = dependency_map[gid]['task']
        
        tallyfy_steps.append({
            'name': task['name'],
            'description': task.get('notes', ''),
            'order': i + 1,
            'metadata': {
                'asana_gid': gid,
                'original_dependencies': dependency_map[gid]['depends_on'],
                'original_dependents': dependency_map[gid]['dependents']
            }
        })
    
    return tallyfy_steps
```

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

### Performance Optimization Strategies

```python
class PerformanceOptimizer:
    def __init__(self):
        self.batch_size = 100
        self.concurrent_workers = 5
        
    def optimize_large_project_migration(self, project_gid):
        """Optimizations for projects with 1000+ tasks"""
        
        # 1. Use field optimization
        minimal_fields = 'gid,name,completed,assignee.gid'
        
        # 2. Parallel processing with thread pool
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=self.concurrent_workers) as executor:
            # Fetch tasks in parallel batches
            futures = []
            
            for offset in range(0, estimated_count, self.batch_size):
                future = executor.submit(
                    self.fetch_task_batch, 
                    project_gid, 
                    offset, 
                    minimal_fields
                )
                futures.append(future)
            
            # Collect results
            all_tasks = []
            for future in futures:
                batch = future.result()
                all_tasks.extend(batch)
                
        return all_tasks
    
    def optimize_custom_fields(self, workspace_gid):
        """Cache custom field definitions"""
        
        # Custom fields are workspace-wide, cache them
        if not hasattr(self, '_custom_fields_cache'):
            self._custom_fields_cache = {}
            
        if workspace_gid not in self._custom_fields_cache:
            fields = self.client.custom_fields.find_by_workspace(
                workspace_gid,
                opt_fields='gid,name,type,enum_options,precision,is_required'
            )
            self._custom_fields_cache[workspace_gid] = {
                f['gid']: f for f in fields
            }
            
        return self._custom_fields_cache[workspace_gid]
```

### Memory-Efficient Processing

```python
def stream_large_attachments(self, attachment_gid):
    """Stream large files without loading into memory"""
    
    # Get attachment metadata
    attachment = self.client.attachments.find_by_id(attachment_gid)
    
    if attachment['size'] > 50_000_000:  # 50MB
        # Stream directly to Tallyfy
        response = requests.get(attachment['download_url'], stream=True)
        
        # Upload in chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        
        upload_session = self.tallyfy_client.create_upload_session(
            filename=attachment['name'],
            size=attachment['size']
        )
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            upload_session.upload_chunk(chunk)
            
        return upload_session.finalize()
    else:
        # Small file, use regular upload
        content = requests.get(attachment['download_url']).content
        return self.tallyfy_client.upload_file(content, attachment['name'])
```

### Common Performance Bottlenecks

| Issue | Impact | Solution |
|-------|--------|----------|
| Large custom field lists | 5-10x slower | Cache field definitions |
| Deep task dependencies | O(n²) complexity | Use topological sort |
| Many subtasks | API call explosion | Batch fetch with includes |
| Large attachments | Memory overflow | Stream processing |
| Board views with 100+ columns | Timeout issues | Process columns individually |

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