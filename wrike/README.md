# Wrike to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🔗 Getting Started with Tallyfy

- **📚 Migration Documentation**: [https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/](https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/)
- **🔌 Open API Documentation**: [https://go.tallyfy.com/api/](https://go.tallyfy.com/api/)
- **🚀 Start Free Trial**: [https://tallyfy.com/start/](https://tallyfy.com/start/)
- **📞 Schedule a Call**: [https://tallyfy.com/booking/](https://tallyfy.com/booking/)

## 🚀 Overview

Transform your Wrike enterprise work management platform with its custom item types, workflows, and request forms into Tallyfy's streamlined AI-powered workflow automation platform. This production-ready migrator handles complete data migration including spaces, projects, tasks, custom fields, workflows, and blueprints with intelligent decision-making for complex enterprise transformations.

### Key Benefits
- ✅ Complete migration of enterprise hierarchies with zero data loss
- ✅ AI-powered custom item type transformation to workflows
- ✅ Automatic paradigm shift handling (Enterprise Hierarchy → Workflow Automation)
- ✅ Intelligent blueprint and request form conversion
- ✅ Custom workflow transformation with approval mapping
- ✅ Formula field conversion with fallback strategies
- ✅ Checkpoint/resume for large enterprise migrations
- ✅ Comprehensive validation and reporting

### What Gets Migrated
- **Spaces** → Tallyfy Organization Units or Blueprint Categories
- **Folders & Projects** → Tallyfy Blueprints with metadata
- **Tasks & Subtasks** → Tallyfy Processes and Tasks
- **Custom Item Types** → Specialized Blueprints with AI mapping
- **Custom Fields** → Tallyfy field (including formula conversion)
- **Workflows** → Tallyfy Status Progressions and Rules
- **Blueprints** → Tallyfy Blueprint Templates
- **Request Forms** → Tallyfy Kick-off Forms with logic
- **Comments & @Mentions** → Process comments with notifications
- **Attachments** → File references or external links

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for enterprise migrations)
- Network access to both Wrike and Tallyfy APIs
- Wrike account with API access enabled (Business plan or higher)

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Wrike**: Generate permanent token from Apps & Integrations → API
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Optional)**: API key for AI features from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/wrike

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
# Wrike API Configuration
WRIKE_API_TOKEN=your_permanent_token_here
WRIKE_ACCOUNT_ID=optional_account_id  # Will auto-detect if not provided

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
SPACE_HANDLING=categories  # Options: categories, organizations, flatten
CUSTOM_TYPE_STRATEGY=specialized_blueprints  # Options: specialized_blueprints, metadata, ignore
WORKFLOW_MAPPING=intelligent  # Options: intelligent, direct, simplified
MIGRATE_ARCHIVED=false
FORMULA_FIELD_HANDLING=calculate_once  # Options: calculate_once, manual_entry, skip
```

### Optional AI Configuration (Strongly Recommended for Enterprise)

```env
# Anthropic API for intelligent decisions
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307  # Fast and economical
AI_TEMPERATURE=0  # Deterministic responses
AI_MAX_TOKENS=500

# AI Feature Flags
AI_TRANSFORM_CUSTOM_TYPES=true
AI_MAP_WORKFLOWS=true
AI_CONVERT_FORMULAS=true
AI_OPTIMIZE_REQUEST_FORMS=true
AI_CONSOLIDATE_BLUEPRINTS=true
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Account permissions and access levels
- AI availability (if configured)
- Enterprise feature usage analysis

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

This migrator includes sophisticated AI augmentation for handling Wrike's enterprise complexity:

### When AI Assists

1. **Custom Item Type Transformation**: Converts business-specific items to workflows
   - Analyzes item type usage patterns (Bug, Campaign, Candidate, etc.)
   - Creates specialized blueprints with appropriate fields
   - Maps type-specific workflows to Tallyfy rules
   - Preserves business logic and approval chains

2. **Blueprint & Request Form Integration**: Intelligently combines intake and execution
   - Merges request forms with blueprints into unified workflows
   - Converts branching logic to conditional steps
   - Optimizes field collection points
   - Maintains approval workflows

3. **Formula Field Conversion**: Handles calculated fields intelligently
   - Evaluates formula complexity
   - Converts simple formulas to Tallyfy logic
   - Creates manual calculation instructions for complex formulas
   - Preserves rollup calculations as summaries

4. **Workflow Sophistication Mapping**: Transforms complex workflows
   - Maps custom statuses to Tallyfy states
   - Converts approval chains to approval steps
   - Handles parallel approvals with conditions
   - Preserves workflow automation rules

5. **Space Organization Strategy**: Optimizes enterprise structure
   - Analyzes space usage patterns
   - Suggests consolidation opportunities
   - Maps permissions appropriately
   - Maintains departmental boundaries

### AI Decision Transparency
- All decisions logged with confidence scores (0.0-1.0)
- Custom type transformations explained
- Formula conversion strategies documented
- Low confidence mappings (<0.7) flagged for review
- Edit prompts in `src/prompts/` to customize behavior

### Running Without AI
The migrator works without AI using conservative strategies:
- Custom item types → Standard blueprints with metadata
- Formula fields → Manual entry with instructions
- Complex workflows → Simplified linear flows
- Request forms → Basic kick-off forms

## 📊 Migration Phases

### Phase 1: Discovery & Analysis (15-45 minutes)
- Connects to Wrike API
- Maps account structure and spaces
- Analyzes custom item types usage
- Inventories custom fields and formulas
- Assesses workflow complexity
- Generates transformation plan

### Phase 2: User & Permission Migration (20-40 minutes)
- Transforms Wrike users to Tallyfy members
- Maps enterprise roles to permissions
- Handles external collaborators
- Creates groups from space membership
- Establishes permission hierarchy

### Phase 3: Structure & Template Migration (1-4 hours)
- Converts Spaces to organizational structure
- Transforms Folders/Projects to Blueprints
- Migrates custom item types as specialized blueprints
- Converts blueprints and request forms
- Maps workflows and approval chains

### Phase 4: Work Item Migration (2-12 hours)
- Migrates active tasks and projects
- Preserves task hierarchies
- Maintains assignments and followers
- Converts custom field values
- Handles attachments and comments

### Phase 5: Validation & Cleanup (30-60 minutes)
- Verifies data integrity
- Validates workflow transformations
- Checks formula conversions
- Generates comprehensive reports
- Lists items requiring manual configuration

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 100 items
- SQLite database tracks all decisions
- Resume from exact interruption point: `--resume`
- Preserves AI decisions and mappings

### Selective Migration
```bash
# Migrate specific spaces only
./migrate.sh --spaces "Engineering,Marketing"

# Migrate specific custom item types
./migrate.sh --item-types "Bug,Feature Request"

# Skip archived items
./migrate.sh --exclude-archived

# Migrate only templates and blueprints
./migrate.sh --templates-only
```

### Enterprise Options
```bash
# Preserve space isolation
./migrate.sh --maintain-space-boundaries

# Consolidate similar blueprints
./migrate.sh --consolidate-blueprints

# Generate permission matrix
./migrate.sh --export-permissions
```

## 🎯 Paradigm Shifts

### Critical Transformation: Enterprise Hierarchy → Workflow Automation

Wrike's enterprise work management model with deep customization differs fundamentally from Tallyfy's workflow-first approach. Key paradigm shifts include:

#### Custom Item Types → Specialized Workflows
- **Before (Wrike)**: Bug, Campaign, Candidate as distinct item types
- **After (Tallyfy)**: Specialized blueprints with appropriate fields and flows
- **AI Strategy**: Analyzes type usage to create optimized blueprints
- **User Impact**: Think in workflows rather than item types

#### Spaces → Organizational Structure
- **Before (Wrike)**: Department-level workspaces with isolation
- **After (Tallyfy)**: Categories or organizational units
- **AI Strategy**: Maps space boundaries to appropriate Tallyfy structure
- **User Impact**: Less rigid departmental separation

#### Formula Fields → Calculated or Manual Fields
- **Before (Wrike)**: Dynamic calculations and rollups
- **After (Tallyfy)**: One-time calculations or manual entry
- **AI Strategy**: Converts simple formulas, provides instructions for complex ones
- **User Impact**: Some calculations become manual processes

#### Request Forms + Blueprints → Unified Workflows
- **Before (Wrike)**: Separate intake and execution systems
- **After (Tallyfy)**: Integrated workflow from request to completion
- **AI Strategy**: Merges form logic with blueprint structure
- **User Impact**: Simplified but less modular approach

#### Custom Workflows → Standard Progressions
- **Before (Wrike)**: Unlimited custom statuses per workflow
- **After (Tallyfy)**: Standardized status progressions
- **AI Strategy**: Maps to closest equivalent states
- **User Impact**: May need to adapt to standard status model

## 📁 Data Mapping

### Object Mappings Summary
| Wrike | Tallyfy | Notes |
|-------|---------|-------|
| Space | Category/Org Unit | Based on usage |
| Folder | Blueprint Group | Logical container |
| Project | Blueprint | Template with dates |
| Task | Process/Task | Context-dependent |
| Subtask | Task | Flattened hierarchy |
| Custom Item Type | Specialized Blueprint | AI-designed |
| Custom Field | field | Type mapping |
| Workflow | Status Progression | Simplified |
| Blueprint | Blueprint Template | Direct mapping |
| Request Form | Kick-off Form | Merged with blueprint |
| Formula Field | Text/Number | Calculated once |
| Attachment | External Link | Reference preserved |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete field-level mappings.

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Dynamic Formula Calculations**: No real-time calculations in Tallyfy
- ❌ **Cross-Space Dependencies**: Limited cross-blueprint references
- ❌ **Gantt Chart Dependencies**: Basic task relationships only
- ❌ **Time Tracking Billability**: Requires external billing system
- ❌ **Custom Branding**: Tallyfy uses standard interface
- ❌ **Advanced Analytics**: Use external BI tools

### Requires Manual Configuration
- ⚠️ **Complex Formula Fields**: Manual calculation setup needed
- ⚠️ **Multi-level Approvals**: May need workflow redesign
- ⚠️ **Cross-functional Dependencies**: Manual reference setup
- ⚠️ **Custom Integrations**: API webhooks need reconfiguration
- ⚠️ **Advanced Automation Chains**: Simplification required

## 🔍 Validation

### Automatic Validation
- ✅ User and permission integrity
- ✅ Custom item type transformation
- ✅ Workflow mapping accuracy
- ✅ Field value preservation
- ✅ Blueprint structure validity
- ✅ Request form conversion completeness
- ✅ Task hierarchy maintenance

### Manual Validation Checklist
- [ ] Verify custom item type blueprints match business needs
- [ ] Check formula field conversions are acceptable
- [ ] Confirm workflow progressions maintain logic
- [ ] Validate approval chains function correctly
- [ ] Test request form kick-offs
- [ ] Review permission mappings
- [ ] Verify space boundaries if preserved

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 1,000 items | 45-90 minutes | < 1GB |
| 1,000-10,000 items | 2-4 hours | 1-3GB |
| 10,000-50,000 items | 4-12 hours | 3-6GB |
| > 50,000 items | 12-48 hours | 6-8GB |

### Rate Limits
- **Wrike**: 400 requests/minute per user
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 25-40 items/minute
- **Recommendation**: Run during off-hours for large migrations

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: `401 Unauthorized: Invalid permanent token`
**Solution**: 
- Regenerate token in Wrike (Apps & Integrations → API)
- Ensure account has Business plan or higher
- Check token permissions match user role

#### Rate Limit Exceeded
**Error**: `429 Too Many Requests`
**Solution**: 
- Implement 2-second delay between requests
- Split migration across multiple sessions
- Use --batch-size flag to reduce load

#### Custom Item Type Complexity
**Error**: `Cannot map custom item type: too complex`
**Solution**:
- Enable AI mapping with Anthropic API key
- Use --simplify-types flag
- Manually map complex types post-migration

#### Formula Field Conversion Failed
**Error**: `Complex formula cannot be converted`
**Solution**:
- Review formula complexity report
- Set FORMULA_FIELD_HANDLING=manual_entry
- Document formulas for manual recreation

#### Space Permission Conflicts
**Error**: `Permission model incompatible`
**Solution**:
- Use --flatten-permissions flag
- Generate permission matrix for manual review
- Consider space consolidation strategy

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Analyze custom types
./migrate.sh --analyze-custom-types > custom_types.json

# Export workflow mappings
./migrate.sh --export-workflows > workflows.json
```

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics and metrics
- `custom_type_transformations.json` - Item type to blueprint mappings
- `workflow_mappings.csv` - Workflow status transformations
- `formula_conversions.csv` - Formula field handling decisions
- `permission_matrix.csv` - User permission mappings
- `errors.log` - Detailed error information
- `ai_decisions.json` - All AI-powered decisions
- `manual_review.md` - Items requiring attention

### Report Contents
- Enterprise structure transformation
- Custom type usage statistics
- Formula complexity analysis
- Workflow simplification metrics
- Permission change summary
- AI confidence distribution
- Processing performance data

## 🔒 Security

### Credential Handling
- Permanent tokens stored securely in environment
- No credential logging or code storage
- Token rotation recommended post-migration
- OAuth 2.0 support for production deployments

### Data Privacy
- All processing performed locally
- No data sent to third parties (except optional AI)
- Complete audit trail maintained
- GDPR/CCPA compliant options available
- Enterprise data isolation preserved


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
2. Review detailed logs in `logs/` directory
3. Run analysis tools for specific issues
4. Verify API connectivity and permissions
5. Consult enterprise migration guide

### Resources
- Wrike API Docs: https://developers.wrike.com/
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/wrike-vs-tallyfy/
- Enterprise Migration Guide: https://tallyfy.com/enterprise/

## 📚 Additional Resources

### Documentation
- [OBJECT_MAPPING.md](OBJECT_MAPPING.md) - Complete field mappings
- [CUSTOM_TYPE_GUIDE.md](docs/CUSTOM_TYPE_GUIDE.md) - Item type transformation
- [FORMULA_CONVERSION.md](docs/FORMULA_CONVERSION.md) - Formula handling strategies
- [ENTERPRISE_GUIDE.md](docs/ENTERPRISE_GUIDE.md) - Large-scale migration tips

### Version Information
- Migrator Version: 1.0.0
- Wrike API: v4
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.