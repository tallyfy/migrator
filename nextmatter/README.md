# NextMatter to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🔗 Getting Started with Tallyfy

- **📚 Migration Documentation**: [https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/](https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/)
- **🔌 Open API Documentation**: [https://go.tallyfy.com/api/](https://go.tallyfy.com/api/)
- **🚀 Start Free Trial**: [https://tallyfy.com/start/](https://tallyfy.com/start/)
- **📞 Schedule a Call**: [https://tallyfy.com/booking/](https://tallyfy.com/booking/)

## 🚀 Overview

Transform your NextMatter operational excellence processes and compliance-focused workflows into Tallyfy's AI-powered workflow automation platform. This production-ready migrator handles complete data migration including processes, instances, steps, approvals, forms, and conditional logic with intelligent decision-making for complex operational transformations.

### Key Benefits
- ✅ Complete migration of operational processes with zero data loss
- ✅ AI-powered compliance workflow transformation
- ✅ Automatic paradigm shift handling (Service Operations → Workflow Automation)
- ✅ Intelligent conditional logic and routing preservation
- ✅ Multi-level approval chain mapping
- ✅ External participant handling (customers, vendors)
- ✅ Checkpoint/resume for large-scale migrations
- ✅ Comprehensive validation and compliance reporting

### What Gets Migrated
- **Processes** → Tallyfy Blueprints with versioning
- **Instances** → Tallyfy Processes (running workflows)
- **Steps** → Tallyfy Tasks with assignments
- **Actions/Forms** → Tallyfy field with validation
- **Conditional Logic** → Tallyfy Rules and Branching
- **Approval Chains** → Tallyfy Approval Steps
- **External Participants** → Guest Users or Forms
- **File Uploads** → Attachments or External Links
- **Routing Sections** → Conditional Step Logic
- **Digital Signatures** → Approval Confirmations

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large migrations)
- Network access to both NextMatter and Tallyfy APIs
- NextMatter account with API access enabled (Admin role required)

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **NextMatter**: Generate API key from Company > Next Matter API keys (Admin only)
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Optional)**: API key for AI features from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/nextmatter

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
# NextMatter API Configuration
NEXTMATTER_API_KEY=your_api_key_here
NEXTMATTER_BASE_URL=https://api.nextmatter.com

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
MIGRATE_ACTIVE_INSTANCES=true
MIGRATE_ARCHIVED_PROCESSES=false
EXTERNAL_PARTICIPANT_HANDLING=guest_forms  # Options: guest_forms, guest_users, documentation
COMPLIANCE_MODE=strict  # Options: strict, balanced, relaxed
APPROVAL_CHAIN_STRATEGY=preserve  # Options: preserve, simplify, flatten
```

### Optional AI Configuration (Highly Recommended for Compliance)

```env
# Anthropic API for intelligent decisions
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307  # Fast and economical
AI_TEMPERATURE=0  # Deterministic responses
AI_MAX_TOKENS=500

# AI Feature Flags
AI_ANALYZE_COMPLIANCE=true
AI_MAP_CONDITIONAL_LOGIC=true
AI_OPTIMIZE_APPROVALS=true
AI_TRANSFORM_SERVICE_FLOWS=true
AI_HANDLE_EXTERNAL_PARTICIPANTS=true
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- API key permissions
- AI availability (if configured)
- Process complexity analysis

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

This migrator includes sophisticated AI augmentation for handling NextMatter's operational excellence focus:

### When AI Assists

1. **Compliance Workflow Transformation**: Preserves audit and compliance requirements
   - Analyzes compliance checkpoints in workflows
   - Maps audit trails to Tallyfy's tracking
   - Ensures regulatory requirements are maintained
   - Creates compliance reports for validation

2. **Service Process Optimization**: Transforms service team workflows
   - Identifies customer touchpoints
   - Optimizes handoffs between teams
   - Maps SLA requirements to deadlines
   - Preserves quality checkpoints

3. **Conditional Logic & Routing**: Intelligently maps complex branching
   - Analyzes radio button conditions
   - Maps routing sections to conditional steps
   - Preserves skip logic and parallel paths
   - Optimizes decision trees

4. **Multi-Level Approval Mapping**: Handles complex approval chains
   - Maps role-based approvals
   - Preserves escalation rules
   - Handles parallel approvals
   - Maintains approval delegation logic

5. **External Participant Integration**: Manages customer/vendor interactions
   - Determines optimal guest access strategy
   - Maps external forms to kick-off forms
   - Preserves communication touchpoints
   - Maintains data privacy boundaries

### AI Decision Transparency
- All decisions logged with confidence scores (0.0-1.0)
- Compliance impact assessments documented
- Conditional logic mappings explained
- Low confidence items (<0.7) flagged for manual review
- Edit prompts in `src/prompts/` to customize behavior

### Running Without AI
The migrator works without AI using conservative strategies:
- Compliance requirements → Strict approval steps
- Conditional logic → Linear workflow with notes
- External participants → Guest form submissions
- Service processes → Standard workflows

## 📊 Migration Phases

### Phase 1: Discovery & Compliance Analysis (15-30 minutes)
- Connects to NextMatter API
- Fetches all processes and versions
- Analyzes compliance requirements
- Maps conditional logic complexity
- Identifies external touchpoints
- Generates compliance-aware migration plan

### Phase 2: User & Role Migration (20-30 minutes)
- Transforms NextMatter users to Tallyfy members
- Maps roles to appropriate permissions
- Handles external participant access
- Creates groups for teams
- Establishes approval hierarchies

### Phase 3: Process Template Migration (1-3 hours)
- Converts processes to Blueprints
- Preserves versioning information
- Maps all form actions to field
- Transforms conditional logic to rules
- Maintains approval chains
- Handles routing sections

### Phase 4: Instance Migration (2-6 hours)
- Migrates running instances as Processes
- Preserves current step states
- Maintains assignments and deadlines
- Converts form submissions
- Handles file attachments
- Preserves audit trails

### Phase 5: Compliance Validation (30-45 minutes)
- Verifies compliance requirements maintained
- Validates approval chains
- Checks audit trail completeness
- Generates compliance report
- Lists items requiring manual verification

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 50 items
- SQLite database tracks migration state
- Resume from exact interruption point: `--resume`
- Preserves all decisions and mappings

### Selective Migration
```bash
# Migrate specific processes only
./migrate.sh --processes "Customer Onboarding,Vendor Approval"

# Migrate only active instances
./migrate.sh --active-only

# Skip external participant processes
./migrate.sh --internal-only

# Migrate with specific date range
./migrate.sh --after-date 2024-01-01
```

### Compliance Options
```bash
# Generate compliance mapping report
./migrate.sh --compliance-report

# Strict compliance mode (no simplification)
./migrate.sh --compliance-mode strict

# Export audit trail mappings
./migrate.sh --export-audit-trails
```

## 🎯 Paradigm Shifts

### Critical Transformation: Service Operations → Workflow Automation

NextMatter's operational excellence focus with compliance requirements differs from Tallyfy's general workflow automation approach. Key paradigm shifts include:

#### Operational Processes → Standard Workflows
- **Before (NextMatter)**: Service-team optimized processes with operational metrics
- **After (Tallyfy)**: General workflows with task tracking
- **AI Strategy**: Preserves service quality checkpoints as validation steps
- **User Impact**: Shift from operational to workflow mindset

#### Compliance-First Design → Audit-Enabled Workflows
- **Before (NextMatter)**: Built-in compliance at every step
- **After (Tallyfy)**: Audit trail with explicit compliance steps
- **AI Strategy**: Adds compliance checkpoints where needed
- **User Impact**: More explicit compliance documentation

#### External Participant Integration → Guest Access
- **Before (NextMatter)**: Seamless external user participation
- **After (Tallyfy)**: Guest forms or limited guest access
- **AI Strategy**: Determines optimal guest interaction model
- **User Impact**: External users have different interaction patterns

#### Visual Process Builder → Template Configuration
- **Before (NextMatter)**: No-code drag-and-drop builder
- **After (Tallyfy)**: Form and step configuration
- **AI Strategy**: Translates visual flow to sequential steps
- **User Impact**: Different design paradigm

#### Routing Sections → Conditional Logic
- **Before (NextMatter)**: Button-based routing with skip logic
- **After (Tallyfy)**: Rule-based conditional branching
- **AI Strategy**: Maps routing buttons to decision points
- **User Impact**: Logic expressed differently

## 📁 Data Mapping

### Object Mappings Summary
| NextMatter | Tallyfy | Notes |
|------------|---------|-------|
| Process | Blueprint | With version metadata |
| Instance | Process | Running workflow |
| Step | Task | With assignments |
| Action | field | Form field |
| Routing Section | Conditional Step | Decision point |
| Approval | Approval Step | With escalation |
| External Participant | Guest User/Form | Context-dependent |
| File Upload | Attachment | Size limits apply |
| Digital Signature | Approval Confirmation | Simplified |
| Tags | Process Tags | Metadata |
| Deadline | Due Date | With SLA tracking |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete field-level mappings.

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Process Editor Visual Layout**: No visual builder in Tallyfy
- ❌ **Advanced Prefill Logic**: Limited data referencing
- ❌ **Custom Integration Steps**: Requires webhook reconfiguration
- ❌ **Operational Metrics**: Use external analytics
- ❌ **Service Level Tracking**: Basic deadline support only
- ❌ **Version Comparison**: Manual version tracking

### Requires Manual Configuration
- ⚠️ **Complex Routing Logic**: Some paths need manual setup
- ⚠️ **Integration Connectors**: API integrations need reconfiguration
- ⚠️ **Multi-path Approvals**: Complex approval matrices need review
- ⚠️ **External System Links**: References need updating
- ⚠️ **Compliance Reports**: Custom report generation

## 🔍 Validation

### Automatic Validation
- ✅ Process structure integrity
- ✅ Step sequence preservation
- ✅ Form field mapping accuracy
- ✅ Conditional logic validity
- ✅ Approval chain completeness
- ✅ User assignment consistency
- ✅ Compliance checkpoint presence

### Manual Validation Checklist
- [ ] Verify compliance requirements are met
- [ ] Test conditional routing logic
- [ ] Confirm approval escalations work
- [ ] Validate external participant access
- [ ] Check form validations function
- [ ] Review audit trail completeness
- [ ] Test end-to-end process flow

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 100 processes | 30-60 minutes | < 1GB |
| 100-500 processes | 1-2 hours | 1-2GB |
| 500-2000 processes | 2-6 hours | 2-4GB |
| > 2000 processes | 6-24 hours | 4-8GB |

### Rate Limits
- **NextMatter**: 100 requests/minute
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 20-30 processes/minute
- **Batch optimization**: AI determines optimal batch size

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: `401 Unauthorized: Invalid API key`
**Solution**: 
- Regenerate API key in NextMatter (Admin required)
- Verify key is active (1-year validity)
- Check key format in Authorization header

#### Rate Limit Exceeded
**Error**: `429 Too Many Requests`
**Solution**: 
- Implement 1-second delay between requests
- Reduce batch size to 10 items
- Use exponential backoff strategy

#### Compliance Validation Failed
**Error**: `Compliance requirements not met`
**Solution**:
- Enable strict compliance mode
- Review compliance report
- Manually add compliance steps

#### Conditional Logic Too Complex
**Error**: `Cannot map routing logic`
**Solution**:
- Enable AI with Anthropic API key
- Simplify to linear flow with notes
- Document complex logic for manual setup

#### External Participant Access Issue
**Error**: `Cannot create guest access`
**Solution**:
- Choose appropriate guest strategy
- Use guest forms instead of users
- Document external touchpoints

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Analyze process complexity
./migrate.sh --analyze-processes > process_analysis.json

# Export conditional logic map
./migrate.sh --export-logic > logic_map.json
```

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics and metrics
- `compliance_report.pdf` - Compliance requirement mappings
- `conditional_logic_map.csv` - Routing logic transformations
- `approval_chains.csv` - Approval hierarchy mappings
- `external_participants.csv` - Guest access decisions
- `errors.log` - Detailed error information
- `ai_decisions.json` - AI-powered transformation decisions
- `manual_review.md` - Items requiring human validation

### Report Contents
- Process transformation statistics
- Compliance checkpoint preservation
- Conditional logic complexity metrics
- Approval chain integrity
- External participant handling
- AI confidence distribution
- Performance metrics

## 🔒 Security

### Credential Handling
- API keys stored in environment variables only
- Keys expire after 1 year (NextMatter policy)
- No credentials in logs or code
- Secure token management

### Data Privacy
- All processing done locally
- No data sent to third parties (except optional AI)
- Compliance with data retention policies
- Audit trail preservation
- GDPR/CCPA compliant options


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
3. Run compliance validation: `./migrate.sh --validate-compliance`
4. Check API connectivity status
5. Review paradigm shift documentation

### Resources
- NextMatter API Docs: https://nextmatter.readme.io/
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/nextmatter-vs-tallyfy/
- Operational Excellence Guide: https://tallyfy.com/operational-excellence/

## 📚 Additional Resources

### Documentation
- [OBJECT_MAPPING.md](OBJECT_MAPPING.md) - Complete field mappings
- [COMPLIANCE_GUIDE.md](docs/COMPLIANCE_GUIDE.md) - Compliance transformation
- [CONDITIONAL_LOGIC.md](docs/CONDITIONAL_LOGIC.md) - Logic mapping strategies
- [EXTERNAL_PARTICIPANTS.md](docs/EXTERNAL_PARTICIPANTS.md) - Guest handling

### Version Information
- Migrator Version: 1.0.0
- NextMatter API: v1
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.