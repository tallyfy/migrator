# RocketLane to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Transform your RocketLane customer onboarding projects and implementation workflows into Tallyfy's AI-powered workflow automation platform. This production-ready migrator handles complete data migration including customers, projects, templates, tasks, forms, and documents with intelligent decision-making for complex transformations.

### Key Benefits
- ✅ Complete migration of customer onboarding workflows with zero data loss
- ✅ AI-powered transformation of customer-facing projects to internal workflows
- ✅ Automatic paradigm shift handling (Customer PSA → Internal Workflow Automation)
- ✅ Intelligent form complexity assessment and workflow generation
- ✅ Resource allocation transformation to task assignments
- ✅ Checkpoint/resume for large-scale migrations
- ✅ Comprehensive validation and reporting

### What Gets Migrated
- **Customers** → Tallyfy Guest Users or Organizations
- **Projects** → Tallyfy Processes (running instances)
- **Project Templates** → Tallyfy Blueprints
- **Tasks & Phases** → Tallyfy Tasks with proper sequencing
- **Forms & Surveys** → Tallyfy Kick-off Forms or Step Forms
- **Custom Fields** → Tallyfy field (with AI mapping)
- **Documents** → External links or attachments
- **Resource Allocations** → Task assignments
- **Time Tracking** → Comments with time logs

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large migrations)
- Network access to both RocketLane and Tallyfy APIs
- RocketLane account with API access enabled

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **RocketLane**: Generate API key from Settings > API in your RocketLane account
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Optional)**: API key for AI features from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/rocketlane

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
# RocketLane API Configuration
ROCKETLANE_API_KEY=your_api_key_here
ROCKETLANE_BASE_URL=https://api.rocketlane.com/api/1.0  # Default

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
MIGRATE_ARCHIVED=false  # Include archived projects/tasks
MIGRATE_TIME_TRACKING=true  # Convert time entries to comments
CUSTOMER_PORTAL_HANDLING=guest_users  # guest_users or organizations
```

### Optional AI Configuration (Recommended)

```env
# Anthropic API for intelligent decisions
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307  # Fast and economical
AI_TEMPERATURE=0  # Deterministic responses
AI_MAX_TOKENS=500

# AI Feature Flags
AI_ASSESS_COMPLEXITY=true
AI_MAP_FIELDS=true
AI_TRANSFORM_PARADIGM=true
AI_OPTIMIZE_BATCHES=true
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Sufficient permissions
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

This migrator includes optional AI augmentation for intelligent decision-making during complex transformations:

### When AI Assists

1. **Customer Portal Paradigm Shift**: Determines how to handle customer-facing elements
   - Converts customer visibility settings to appropriate Tallyfy permissions
   - Transforms customer forms to kick-off forms or guest submissions
   - Maps customer feedback loops to approval steps

2. **Form Complexity Assessment**: Analyzes RocketLane forms to determine optimal structure
   - Simple forms (≤20 fields) → Tallyfy kick-off form
   - Complex forms (>20 fields) → Multi-step workflow with logical grouping
   - Survey forms → Approval steps with rating field

3. **Resource Allocation Transformation**: Converts PSA resource management
   - Skills-based allocation → Task assignment with notes
   - Capacity planning → Task deadlines and SLAs
   - Placeholder resources → Unassigned tasks with role requirements

4. **Custom Field Mapping**: Intelligently maps RocketLane's custom fields
   - Analyzes field usage patterns and sample data
   - Maps to most appropriate Tallyfy field type
   - Preserves validation rules where possible

5. **Project Template Intelligence**: Optimizes template transformation
   - Identifies reusable patterns across templates
   - Suggests blueprint consolidation opportunities
   - Handles conditional logic and dynamic fields

### AI Decision Transparency
- All decisions logged with confidence scores (0.0-1.0)
- Low confidence mappings (<0.7) flagged for manual review
- Fallback to deterministic rules when AI unavailable
- Edit prompts in `src/prompts/` to customize behavior

### Running Without AI
The migrator works perfectly without AI using intelligent heuristics:
- Customer projects → Standard processes with guest access
- Forms → Field count-based complexity assessment
- Custom fields → Type-based best guess mapping
- Resource allocation → Direct task assignment

## 📊 Migration Phases

### Phase 1: Discovery (5-10 minutes)
- Connects to RocketLane API
- Fetches all customers, projects, templates, forms
- Analyzes data complexity and volume
- Generates migration plan with estimates
- Identifies paradigm shifts needed

### Phase 2: Customer & User Migration (10-30 minutes)
- Transforms RocketLane customers to appropriate Tallyfy entities
- Maps internal users to Tallyfy members
- Handles customer portal access patterns
- Creates groups for team structures
- Establishes ID mappings for relationships

### Phase 3: Template Migration (30-60 minutes)
- Converts project templates to Blueprints
- Transforms phases into sequential workflow steps
- Maps task templates with dependencies
- Handles form templates (with AI assistance)
- Preserves automation rules where possible

### Phase 4: Project Migration (1-6 hours)
- Migrates active projects as Processes
- Preserves current task states and progress
- Maintains assignee relationships
- Converts time tracking to structured comments
- Handles document references

### Phase 5: Validation (10-20 minutes)
- Verifies data integrity
- Checks relationship mappings
- Validates form field transformations
- Generates detailed migration report
- Lists items requiring manual review

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 50 items
- SQLite database tracks migration state
- Resume from exact interruption point: `--resume`
- Preserves ID mappings across sessions

### Selective Migration
```bash
# Migrate specific projects only
./migrate.sh --projects "Project Alpha,Project Beta"

# Migrate templates created after date
./migrate.sh --after-date 2024-01-01

# Exclude archived items
./migrate.sh --exclude-archived

# Migrate only templates (no running projects)
./migrate.sh --templates-only
```

### Report-Only Mode
```bash
# Analyze without migrating
./migrate.sh --report-only

# Generate detailed mapping preview
./migrate.sh --preview-mappings
```

## 🎯 Paradigm Shifts

### Critical Transformation: Customer PSA → Internal Workflow Automation

RocketLane is built around customer-facing project delivery with external collaboration, while Tallyfy focuses on internal workflow automation with optional guest access. This requires fundamental transformations:

#### Customer Portal → Guest Access
- **Before (RocketLane)**: White-labeled customer portals with project visibility
- **After (Tallyfy)**: Guest users with limited process visibility or external forms
- **AI Strategy**: Analyzes customer interaction patterns to determine optimal guest configuration
- **User Impact**: Customer interactions move from portal to email notifications or guest forms

#### Resource Management → Task Assignment
- **Before (RocketLane)**: Capacity planning, skills-based allocation, utilization tracking
- **After (Tallyfy)**: Direct task assignments with role-based routing
- **AI Strategy**: Maps resource requirements to assignment rules
- **User Impact**: Resource managers need to adapt to task-based assignment model

#### Project Phases → Sequential Steps
- **Before (RocketLane)**: Parallel phases with complex dependencies
- **After (Tallyfy)**: Sequential workflow with conditional branching
- **AI Strategy**: Analyzes phase dependencies to create optimal step sequence
- **User Impact**: Project managers think in linear workflows vs parallel tracks

#### Time Tracking → Activity Logs
- **Before (RocketLane)**: Integrated time tracking with billing
- **After (Tallyfy)**: Comments with time notation or integration with external time tracking
- **AI Strategy**: Preserves time data in structured format for reporting
- **User Impact**: Time tracking moves to external tool or manual notation

## 📁 Data Mapping

### Object Mappings Summary
| RocketLane | Tallyfy | Notes |
|------------|---------|-------|
| Customer | Guest User/Organization | Based on portal usage |
| Project | Process | Running instance |
| Project Template | Blueprint | Workflow template |
| Phase | Step Group | Logical grouping of steps |
| Task | Task | Direct mapping |
| Form | Kick-off/Step Form | Based on complexity |
| Custom Field | field | AI-assisted mapping |
| Document | External Link | Reference preserved |
| Resource | Assignee | Direct assignment |
| Time Entry | Comment | Structured time notation |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete field-level mappings.

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Billing & Invoicing**: No equivalent in Tallyfy - export to accounting system
- ❌ **Resource Capacity Planning**: No resource management - use external tool
- ❌ **Customer Portal Branding**: Tallyfy uses standard guest interface
- ❌ **Financial Reporting**: Export financial data separately
- ❌ **Gantt Chart Views**: Tallyfy uses list/kanban views only

### Requires Manual Configuration
- ⚠️ **Complex Dependencies**: Some cross-phase dependencies need manual rules
- ⚠️ **Custom Integrations**: Webhooks and API integrations need reconfiguration
- ⚠️ **Advanced Automations**: Complex automation chains may need adjustment
- ⚠️ **CSAT Surveys**: Configure as separate feedback processes

## 🔍 Validation

### Automatic Validation
- ✅ Customer to user mapping integrity
- ✅ Template structure preservation
- ✅ Task relationship consistency
- ✅ Form field mapping accuracy
- ✅ Assignment preservation
- ✅ Document link accessibility
- ✅ Custom field data integrity

### Manual Validation Checklist
- [ ] Verify customer access patterns are appropriate
- [ ] Test form submissions and data field
- [ ] Confirm workflow logic matches intent
- [ ] Validate time tracking data preservation
- [ ] Check automation rules functionality
- [ ] Review AI-flagged decisions
- [ ] Test guest user access if applicable

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 100 projects | 15-30 minutes | < 1GB |
| 100-500 projects | 1-2 hours | 1-2GB |
| 500-2000 projects | 2-6 hours | 2-4GB |
| > 2000 projects | 6-24 hours | 4-8GB |

### Rate Limits
- **RocketLane**: Minute and hour-based limits (undocumented)
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 20-30 projects/minute
- **Batch optimization**: AI determines optimal batch size

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: `401 Unauthorized: Invalid API key`
**Solution**: 
- Verify API key in .env file
- Ensure key has sufficient permissions
- Check key hasn't expired

#### Rate Limit Exceeded
**Error**: `429 Too Many Requests`
**Solution**: 
- Wait 60 seconds before retry
- Reduce batch size in configuration
- Enable AI batch optimization

#### Customer Mapping Confusion
**Error**: `Cannot determine customer handling strategy`
**Solution**:
- Set CUSTOMER_PORTAL_HANDLING in .env
- Choose: guest_users or organizations
- Run with --preview-mappings first

#### Memory Error on Large Dataset
**Error**: `MemoryError during project migration`
**Solution**:
- Reduce PROJECT_BATCH_SIZE to 10
- Increase system RAM
- Use --projects flag to migrate in chunks

#### AI Decision Failed
**Error**: `AI client unavailable or timeout`
**Solution**: 
- Check Anthropic API key
- Fallback activates automatically
- Review logs for fallback decisions

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Log all API calls
export LOG_API_CALLS=true
./migrate.sh --trace-api
```

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics and timings
- `customer_mappings.csv` - Customer to Tallyfy entity mappings
- `field_mappings.csv` - All field transformations with AI confidence
- `paradigm_shifts.json` - Major transformations applied
- `errors.log` - Issues encountered with context
- `ai_decisions.json` - All AI mapping decisions with reasoning
- `manual_review.md` - Items requiring human validation

### Report Contents
- Total items migrated by type
- Success/failure rates per phase
- Processing time breakdowns
- AI confidence distribution
- Paradigm shift summaries
- Manual review requirements
- Resource mapping statistics

## 🔒 Security

### Credential Handling
- API keys stored in environment variables only
- No credentials logged or stored in code
- Secure token management for both platforms
- Optional encryption for sensitive custom fields

### Data Privacy
- All processing done locally
- No data sent to third parties (except optional AI)
- Customer data handled per configuration
- Full audit log of all operations
- GDPR compliant processing options


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

### Getting Help
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs in `logs/` directory
3. Run readiness check: `./migrate.sh --readiness-check`
4. Verify API status for both platforms
5. Check paradigm shift documentation

### Resources
- RocketLane API Docs: https://developer.rocketlane.com/
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/rocketlane-vs-tallyfy/
- Customer Onboarding Best Practices: https://tallyfy.com/customer-onboarding/

## 📚 Additional Resources

### Documentation
- [OBJECT_MAPPING.md](OBJECT_MAPPING.md) - Complete field-level mappings
- [API_REFERENCE.md](docs/API_REFERENCE.md) - Detailed API usage
- [PARADIGM_SHIFTS.md](docs/PARADIGM_SHIFTS.md) - Transformation strategies
- [CUSTOMER_HANDLING.md](docs/CUSTOMER_HANDLING.md) - Customer portal migration guide

### Version Information
- Migrator Version: 1.0.0
- RocketLane API: v1.0
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.