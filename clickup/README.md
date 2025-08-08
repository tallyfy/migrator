# ClickUp to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Migrate your ClickUp workspaces, lists, tasks, and workflows to Tallyfy's streamlined process management platform. This enterprise-ready migrator handles complete workspace transformation including spaces, folders, lists, tasks, custom fields, and automations with intelligent handling of ClickUp's flexible hierarchy.

### Key Benefits
- ✅ Complete workspace migration with hierarchy preservation
- ✅ AI-powered view transformation (List/Board/Calendar → Sequential workflows)
- ✅ Custom field mapping with 15+ ClickUp field types
- ✅ Automation and dependency preservation
- ✅ Time tracking and sprint data migration
- ✅ Checkpoint/resume for large workspaces
- ✅ Comprehensive validation and reporting

### What Gets Migrated
- **Spaces** → Tallyfy Organizations/Categories
- **Folders & Lists** → Tallyfy Blueprints
- **Tasks & Subtasks** → Tallyfy Tasks with hierarchy
- **Custom Fields** → Tallyfy form fields (AI-mapped)
- **Views** → Workflow structures
- **Automations** → Tallyfy rules
- **Comments & Activities** → Process comments
- **Time Tracking** → Structured time comments
- **Attachments** → External references
- **Dependencies** → Task dependencies

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large workspaces)
- Network access to both ClickUp and Tallyfy APIs
- ClickUp workspace with API access enabled

### API Access Requirements
- **ClickUp**: Personal API token from Settings > Apps > API Token
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Optional)**: API key for AI features from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/clickup

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

## ⚙️ Configuration

### Required Configuration

```env
# ClickUp API Configuration
CLICKUP_API_KEY=pk_your_api_key_here
CLICKUP_WORKSPACE_ID=your_workspace_id  # Optional, will fetch first workspace

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
MIGRATE_ARCHIVED=false  # Include archived lists and tasks
MIGRATE_TIME_TRACKING=true  # Convert time entries
MIGRATE_SPRINTS=true  # Include sprint data
VIEW_TRANSFORMATION=intelligent  # intelligent, list_only, or preserve_all
```

### Optional AI Configuration (Recommended)

```env
# Anthropic API for intelligent decisions
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307
AI_TEMPERATURE=0
AI_MAX_TOKENS=500

# AI Feature Flags
AI_ASSESS_VIEW_COMPLEXITY=true
AI_MAP_CUSTOM_FIELDS=true
AI_OPTIMIZE_HIERARCHY=true
AI_TRANSFORM_AUTOMATIONS=true
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Workspace access and permissions
- AI availability (if configured)
- Data volume estimates

### 2. Dry Run (Preview without changes)
```bash
./migrate.sh --dry-run
```
Shows what would be migrated without making changes.

### 3. Full Migration
```bash
./migrate.sh
```
Executes complete migration with progress tracking.

### 4. Resume Interrupted Migration
```bash
./migrate.sh --resume
```
Continues from last checkpoint if migration was interrupted.

## 🤖 AI-Powered Features

### When AI Assists

1. **View Transformation**: Intelligently converts ClickUp views to workflows
   - List View → Sequential workflow
   - Board View → Kanban-inspired multi-step process
   - Calendar View → Date-driven workflow with deadlines
   - Gantt View → Dependency-based sequential process
   - Timeline View → Phased workflow approach

2. **Custom Field Mapping**: Maps ClickUp's 15+ field types
   - Relationship fields → Reference dropdowns
   - Formula fields → Calculated text (preserved)
   - Progress fields → Percentage tracking
   - Rating fields → Scale selection
   - Location fields → Address text

3. **Hierarchy Optimization**: Flattens or preserves structure
   - Deep nesting → Logical grouping
   - Subtask chains → Step sequences
   - Folder structure → Category organization

4. **Automation Translation**: Converts ClickUp automations
   - Trigger mapping to Tallyfy events
   - Condition transformation
   - Action sequence preservation

### AI Decision Transparency
- All decisions logged with confidence scores
- Low confidence (<0.7) flagged for review
- Fallback to heuristic rules when AI unavailable
- Edit prompts in `src/prompts/` to customize

### Running Without AI
The migrator works perfectly without AI using smart defaults:
- List views → Direct task mapping
- Custom fields → Type-based mapping
- Automations → Rule-based transformation
- Hierarchy → Preserve structure

## 📊 Migration Phases

### Phase 1: Discovery (5-10 minutes)
- Connects to ClickUp API
- Fetches workspace structure
- Analyzes spaces, folders, lists
- Generates migration plan
- Identifies complexity patterns

### Phase 2: User Migration (10-20 minutes)
- Migrates workspace members to Tallyfy
- Maps teams to groups
- Preserves role assignments
- Creates guest users for external collaborators
- Establishes ID mappings

### Phase 3: Template Migration (30-60 minutes)
- Converts lists to blueprints
- Transforms views to workflows
- Maps custom fields
- Preserves automations
- Handles task templates

### Phase 4: Task Migration (1-6 hours)
- Migrates active tasks as processes
- Preserves task states
- Maintains assignments
- Converts time tracking
- Links dependencies

### Phase 5: Validation (10-20 minutes)
- Verifies data integrity
- Checks relationship mappings
- Validates field transformations
- Generates migration report
- Lists items requiring review

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 100 items
- SQLite database tracks migration state
- Resume from exact interruption point
- Preserves ID mappings across sessions

### Selective Migration
```bash
# Migrate specific spaces only
./migrate.sh --spaces "Development,Marketing"

# Migrate specific lists
./migrate.sh --lists "Sprint 23,Backlog"

# Exclude archived items
./migrate.sh --exclude-archived

# Migrate only templates (no tasks)
./migrate.sh --templates-only
```

### View-Specific Options
```bash
# Force list view transformation
./migrate.sh --view-mode list

# Preserve all views as separate workflows
./migrate.sh --preserve-views

# Let AI decide per list
./migrate.sh --intelligent-views
```

## 🎯 Paradigm Shifts

### Critical Transformation: Flexible Hierarchy → Structured Workflows

ClickUp's flexible hierarchy doesn't directly map to Tallyfy's process-oriented structure. This requires intelligent transformation:

#### Nested Hierarchy → Flat Processes
- **Before (ClickUp)**: Space > Folder > List > Task > Subtasks (5 levels)
- **After (Tallyfy)**: Category > Blueprint > Process > Tasks (3 levels)
- **AI Strategy**: Analyzes depth and suggests optimal flattening
- **User Impact**: Simpler navigation but requires adaptation

#### Multiple Views → Single Workflow
- **Before (ClickUp)**: List, Board, Calendar, Gantt per list
- **After (Tallyfy)**: One sequential workflow per blueprint
- **AI Strategy**: Determines primary view usage and optimizes
- **User Impact**: Unified view but loss of view flexibility

#### Flexible Fields → Structured Forms
- **Before (ClickUp)**: Custom fields added anywhere
- **After (Tallyfy)**: Fields in kick-off or step forms
- **AI Strategy**: Groups related fields into logical forms
- **User Impact**: More structured data entry

## 📁 Data Mapping

### Object Mappings Summary
| ClickUp | Tallyfy | Notes |
|---------|---------|-------|
| Workspace | Organization | Top-level container |
| Space | Category/Tag | Organizational unit |
| Folder | Blueprint Group | Template organization |
| List | Blueprint | Workflow template |
| Task | Task/Process | Depends on status |
| Subtask | Step | Sequential steps |
| Custom Field | Form Field | AI-mapped types |
| View | Workflow Structure | Transformed |
| Automation | Rule | Trigger-action pairs |
| Time Entry | Comment | Structured format |
| Dependency | Task Link | Preserved relationships |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete field-level mappings.

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Multiple Views**: Only primary view structure migrated
- ❌ **Goals & Portfolios**: No equivalent in Tallyfy
- ❌ **Dashboards**: Reporting differs significantly
- ❌ **Workload View**: Resource management differs
- ❌ **Mind Maps**: No visual mapping in Tallyfy
- ❌ **Docs**: Migrate separately as external documentation

### Requires Manual Configuration
- ⚠️ **Complex Dependencies**: Cross-list dependencies need review
- ⚠️ **Custom Automations**: Complex conditions may need adjustment
- ⚠️ **Recurring Tasks**: Different recurrence model
- ⚠️ **Time Estimates**: Rollup calculations differ
- ⚠️ **Custom Roles**: Permission model differs

## 🔍 Validation

### Automatic Validation
- ✅ User and team mapping integrity
- ✅ List to blueprint structure
- ✅ Task hierarchy preservation
- ✅ Custom field data integrity
- ✅ Assignment preservation
- ✅ Dependency validation
- ✅ Time tracking migration

### Manual Validation Checklist
- [ ] Verify view transformation appropriateness
- [ ] Check custom field mappings
- [ ] Confirm automation rules work
- [ ] Validate dependency chains
- [ ] Review flattened hierarchies
- [ ] Test notification settings

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 1000 tasks | 15-30 minutes | < 1GB |
| 1000-5000 tasks | 30-90 minutes | 1-2GB |
| 5000-20000 tasks | 2-6 hours | 2-4GB |
| > 20000 tasks | 6-24 hours | 4-8GB |

### Rate Limits
- **ClickUp**: 100 requests/minute per token
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 40-60 tasks/minute

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
- Verify ClickUp API token is valid
- Ensure token has full access permissions
- Check Tallyfy credentials

#### View Transformation Confusion
- Set VIEW_TRANSFORMATION in .env
- Use --view-mode flag for consistency
- Review with --preview-mappings first

#### Memory Error on Large Workspace
- Reduce BATCH_SIZE to 50
- Migrate spaces separately
- Use --exclude-archived flag

#### Custom Field Mapping Issues
- Enable AI for better mapping
- Review field type compatibility
- Check OBJECT_MAPPING.md

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `view_transformations.csv` - View conversion details
- `field_mappings.csv` - Custom field mappings
- `hierarchy_changes.json` - Structure modifications
- `errors.log` - Issues encountered
- `manual_review.md` - Items needing attention

## 🔒 Security

- API keys stored in environment variables only
- No credentials logged or stored
- Secure token management
- Optional field encryption
- GDPR compliant options

## 📖 Tallyfy Field Types Reference

### Available Field Types in Tallyfy

Based on the api-v2 implementation:

1. **text** - Short text (max 255 chars)
2. **textarea** - Long text (max 6000 chars)
3. **radio** - Radio buttons
4. **dropdown** - Single selection
5. **multiselect** - Multiple selection
6. **date** - Date picker
7. **email** - Email field
8. **file** - File upload
9. **table** - Table/grid
10. **assignees_form** - User/guest assignment

### ClickUp Field Mappings

| ClickUp Type | Tallyfy Type | Notes |
|--------------|--------------|-------|
| Text | text/textarea | Based on length |
| Number | text | With numeric validation |
| Money | text | With currency format |
| Rating | dropdown | Scale options |
| Label | dropdown | Single select |
| Tasks | dropdown | Reference field |
| Users | assignees_form | User selection |
| Checkbox | radio | Yes/No |
| Date | date | Date picker |
| Drop Down | dropdown | Options preserved |
| Email | email | Email validation |
| Phone | text | Phone pattern |
| URL | text | URL validation |
| Progress | text | Percentage |
| Formula | text | Read-only preserved |

## 🆘 Support

### Resources
- ClickUp API Docs: https://clickup.com/api
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/clickup-vs-tallyfy/

---

## License

MIT License - See LICENSE file for details