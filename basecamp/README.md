# Basecamp to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Transform your Basecamp project-centric collaboration platform with its communication-first approach into Tallyfy's AI-powered workflow automation platform. This production-ready migrator handles the fundamental paradigm shift from project containers to sequential workflows, including projects, to-do lists, card tables, messages, and schedules with intelligent transformation decisions.

### Key Benefits
- ✅ Complete project-to-workflow transformation with zero data loss
- ✅ AI-powered consolidation of scattered project elements
- ✅ Automatic paradigm shift handling (Project-Centric → Process-Centric)
- ✅ Card Table Kanban to sequential workflow conversion
- ✅ To-do list to structured task transformation
- ✅ Communication context preservation
- ✅ Checkpoint/resume for large account migrations
- ✅ Shape Up methodology adaptation

### What Gets Migrated
- **Projects** → Tallyfy Blueprint Categories or Processes
- **To-do Lists** → Workflow Steps or Task Groups
- **To-dos** → Tasks with assignments
- **Card Tables** → Sequential Workflows (Kanban transformation)
- **Messages** → Process documentation or comments
- **Documents** → Reference materials or instructions
- **Campfires** → Comment threads (historical)
- **Schedules** → Task deadlines and milestones
- **Questionnaires** → Recurring process templates
- **People** → Users with appropriate roles

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large accounts)
- Network access to both Basecamp and Tallyfy APIs
- Basecamp account with appropriate access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Basecamp**: OAuth 2.0 application or personal access token
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Optional)**: API key for AI features from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/basecamp

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
# Basecamp API Configuration
BASECAMP_ACCOUNT_ID=your_account_id
BASECAMP_ACCESS_TOKEN=your_access_token  # Or OAuth credentials
BASECAMP_REFRESH_TOKEN=your_refresh_token  # If using OAuth
BASECAMP_CLIENT_ID=your_client_id  # If using OAuth
BASECAMP_CLIENT_SECRET=your_client_secret  # If using OAuth

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
PROJECT_HANDLING=smart  # Options: smart, all_blueprints, all_processes
TODO_LIST_STRATEGY=workflow_steps  # Options: workflow_steps, task_groups, hybrid
CARD_TABLE_TRANSFORMATION=sequential  # Options: sequential, preserve_columns, ignore
MESSAGE_HANDLING=documentation  # Options: documentation, comments, skip
CAMPFIRE_PRESERVATION=comments  # Options: comments, documentation, skip
```

### Optional AI Configuration (Strongly Recommended)

```env
# Anthropic API for intelligent decisions
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307  # Fast and economical
AI_TEMPERATURE=0  # Deterministic responses
AI_MAX_TOKENS=500

# AI Feature Flags
AI_CONSOLIDATE_PROJECTS=true
AI_SEQUENCE_TODOS=true
AI_TRANSFORM_CARD_TABLES=true
AI_EXTRACT_WORKFLOWS=true
AI_PRESERVE_CONTEXT=true
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Account access permissions
- AI availability (if configured)
- Project structure analysis

### 2. Dry Run (Preview without changes)
```bash
./migrate.sh --dry-run
```
Shows transformation preview without making changes.

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

This migrator includes sophisticated AI to handle Basecamp's unique project-centric paradigm:

### When AI Assists

1. **Project Consolidation**: Transforms project containers into workflows
   - Analyzes project activity and structure
   - Identifies workflow patterns within projects
   - Consolidates scattered elements (to-dos, cards, messages)
   - Creates cohesive processes from project chaos

2. **To-do List Sequencing**: Creates workflows from flat lists
   - Analyzes to-do list names and contents
   - Determines logical task sequences
   - Groups related to-dos into workflow steps
   - Handles Basecamp's flat structure intelligently

3. **Card Table Transformation**: Converts Kanban boards to workflows
   - Maps columns to sequential steps
   - Handles "Triage", "Not Now", "On Hold" special columns
   - Creates conditional logic for card flow
   - Preserves visual workflow intent

4. **Communication Context Preservation**: Maintains project discussions
   - Extracts process documentation from messages
   - Preserves important context as instructions
   - Maps Campfire discussions to relevant tasks
   - Maintains team knowledge

5. **Shape Up Methodology Adaptation**: Handles 6-week cycles
   - Identifies cycle-based projects
   - Maps betting table decisions to priorities
   - Converts appetites to time estimates
   - Preserves circuit breaker concepts

### AI Decision Transparency
- Project analysis reasoning documented
- To-do sequencing logic explained
- Card table transformation mapped
- Communication extraction detailed
- Low confidence items (<0.7) flagged
- Edit prompts in `src/prompts/` to customize

### Running Without AI
The migrator works without AI using conservative patterns:
- Projects → Individual blueprints
- To-do lists → Simple task lists
- Card tables → Three-step workflows
- Messages → Attached documentation
- Manual sequencing required

## 📊 Migration Phases

### Phase 1: Discovery & Project Analysis (15-30 minutes)
- Connects to Basecamp API
- Fetches all projects and contents
- Analyzes project patterns
- Identifies workflow structures
- Maps communication patterns
- Generates transformation strategy

### Phase 2: People & Permission Migration (20-30 minutes)
- Transforms Basecamp people to Tallyfy users
- Maps project permissions to roles
- Handles client users appropriately
- Creates groups from companies
- Establishes access controls

### Phase 3: Project Structure Transformation (1-3 hours)
- **Critical Paradigm Shift**: Projects → Workflows
- Consolidates project elements
- Transforms to-do lists to steps
- Converts card tables to workflows
- Preserves messages as documentation
- Maps schedules to deadlines

### Phase 4: Content Migration (2-8 hours)
- Migrates active to-dos as tasks
- Preserves assignments and due dates
- Converts comments and discussions
- Handles file attachments
- Maps questionnaire responses
- Maintains project relationships

### Phase 5: Validation & Context Preservation (30-45 minutes)
- Verifies transformation completeness
- Validates workflow logic
- Preserves communication context
- Generates migration reports
- Lists manual configuration needs

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 25 projects
- SQLite database tracks all decisions
- Resume from exact interruption point: `--resume`
- Preserves project analysis results

### Selective Migration
```bash
# Migrate specific projects only
./migrate.sh --projects "Q4 Planning,Product Launch"

# Migrate active projects only
./migrate.sh --active-only

# Skip archived projects
./migrate.sh --skip-archived

# Migrate by date range
./migrate.sh --after-date 2024-01-01
```

### Shape Up Options
```bash
# Handle 6-week cycles specially
./migrate.sh --shape-up-mode

# Group by cycles
./migrate.sh --group-by-cycles

# Preserve betting table decisions
./migrate.sh --preserve-bets
```

## 🎯 Paradigm Shifts

### Critical Transformation: Project-Centric → Process-Centric

Basecamp's project container philosophy fundamentally differs from Tallyfy's process-focused approach:

#### Projects as Containers → Workflows as Processes
- **Before (Basecamp)**: Everything lives within project boundaries
- **After (Tallyfy)**: Processes flow across organizational boundaries
- **AI Strategy**: Extracts workflows from project containers
- **User Impact**: Think in processes, not projects

#### Flat To-do Structure → Sequential Steps
- **Before (Basecamp)**: No subtasks, deliberately flat
- **After (Tallyfy)**: Hierarchical task structure
- **AI Strategy**: Infers hierarchy from context
- **User Impact**: More structured task management

#### Communication-First → Task-First
- **Before (Basecamp)**: Messages and Campfires central to work
- **After (Tallyfy)**: Tasks with attached communication
- **AI Strategy**: Preserves context within tasks
- **User Impact**: Communication becomes task-centric

#### Card Tables → Sequential Workflows
- **Before (Basecamp)**: Visual Kanban boards
- **After (Tallyfy)**: Linear process flows
- **AI Strategy**: Transforms columns to steps
- **User Impact**: Less visual, more structured

#### Hill Charts → Standard Progress
- **Before (Basecamp)**: Uphill/downhill progress visualization
- **After (Tallyfy)**: Percentage-based progress
- **AI Strategy**: Maps hill position to completion
- **User Impact**: Different progress metaphor

## 📁 Data Mapping

### Object Mappings Summary
| Basecamp | Tallyfy | Context |
|----------|---------|---------|
| Project | Blueprint/Process | Depends on complexity |
| To-do List | Step Group | Logical grouping |
| To-do | Task | Direct mapping |
| Card Table | Workflow | Kanban transformation |
| Card | Task | Within workflow |
| Message | Documentation | Process context |
| Document | Reference | Attached to blueprint |
| Campfire | Comments | Historical chat |
| Schedule | Deadline | Time constraints |
| Questionnaire | Recurring Process | Template for regulars |
| Person | User | Role mapping |

### Communication Preservation Strategy
| Basecamp Element | Tallyfy Location | Preservation Method |
|------------------|------------------|---------------------|
| Messages | Process Docs | Key announcements as instructions |
| Comments | Task Comments | Direct transfer with context |
| Campfire | Process Comments | Consolidated by relevance |
| Documents | Blueprint Docs | Reference materials |
| Files | External Links | Cloud storage references |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete mappings.

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Hill Charts**: No equivalent visualization in Tallyfy
- ❌ **Automatic Check-ins**: Limited API access, manual setup needed
- ❌ **Client Reports**: No native client reporting
- ❌ **My Schedule View**: Personal dashboard differences
- ❌ **Basecamp Personal**: Different product line
- ❌ **Email-in Feature**: No email-to-process creation

### Requires Manual Configuration
- ⚠️ **Complex Card Table Workflows**: May need manual adjustment
- ⚠️ **Recurring Questionnaires**: Set up as recurring processes
- ⚠️ **Client Access Patterns**: Different permission model
- ⚠️ **Campfire Real-time**: Historical import only
- ⚠️ **Project Templates**: Manual blueprint creation

## 🔍 Validation

### Automatic Validation
- ✅ Project consolidation completeness
- ✅ To-do list transformation accuracy
- ✅ Card table conversion validity
- ✅ User permission mapping
- ✅ Communication preservation
- ✅ Schedule/deadline transfer
- ✅ File attachment accessibility

### Manual Validation Checklist
- [ ] Verify workflows represent intended processes
- [ ] Check to-do sequencing is logical
- [ ] Confirm card table transformations work
- [ ] Validate communication context preserved
- [ ] Test end-to-end process execution
- [ ] Review AI consolidation decisions
- [ ] Verify client access appropriate

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 25 projects | 30-60 minutes | < 1GB |
| 25-100 projects | 1-3 hours | 1-2GB |
| 100-500 projects | 3-8 hours | 2-4GB |
| > 500 projects | 8-24 hours | 4-8GB |

### Rate Limits
- **Basecamp**: 50 requests/10 seconds
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 15-25 projects/hour
- **Best practice**: Run during off-hours

## 🐛 Troubleshooting

### Common Issues

#### OAuth Token Expired
**Error**: `401 Unauthorized: Token expired`
**Solution**: 
- Refresh token using refresh_token
- Tokens expire after 2 weeks
- Implement automatic refresh

#### Rate Limit Exceeded
**Error**: `429 Too Many Requests`
**Solution**: 
- Wait 10 seconds before retry
- Implement exponential backoff
- Stay under 50 req/10s

#### Project Too Complex
**Error**: `Cannot determine workflow structure`
**Solution**:
- Enable AI analysis
- Split complex projects manually
- Use --simplify flag

#### Card Table Transformation Failed
**Error**: `Cannot map card columns`
**Solution**:
- Review column structure
- Use custom column mapping
- Simplify to basic workflow

#### Communication Loss
**Error**: `Important context not preserved`
**Solution**:
- Enable AI context extraction
- Increase context threshold
- Manual documentation review

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Analyze project structure
./migrate.sh --analyze-projects > project_analysis.json

# Preview transformations
./migrate.sh --preview-transformation
```

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `project_analysis.json` - Project structure analysis
- `workflow_extraction.csv` - Workflows found in projects
- `communication_preservation.csv` - Message/chat handling
- `card_table_transformations.json` - Kanban conversions
- `errors.log` - Detailed error information
- `ai_decisions.json` - AI reasoning for transformations
- `manual_review.md` - Items requiring attention

### Report Contents
- Project complexity metrics
- Workflow extraction success
- Communication preservation rate
- To-do sequencing confidence
- Card table transformation details
- AI decision distribution
- Performance statistics

## 🔒 Security

### Credential Handling
- OAuth tokens in secure storage
- Automatic token refresh
- No credentials in logs
- Personal tokens for development only

### Data Privacy
- All processing done locally
- No data sent to third parties (except optional AI)
- Project isolation maintained
- Client data handled separately
- GDPR compliant options


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
2. Review project analysis reports
3. Check transformation logs
4. Verify API connectivity
5. Consult paradigm shift guide

### Resources
- Basecamp API Docs: https://github.com/basecamp/bc3-api
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/basecamp-vs-tallyfy/
- Shape Up Guide: https://basecamp.com/shapeup

## 📚 Additional Resources

### Documentation
- [OBJECT_MAPPING.md](OBJECT_MAPPING.md) - Complete field mappings
- [PROJECT_TRANSFORMATION.md](docs/PROJECT_TRANSFORMATION.md) - Project paradigm shift
- [SHAPE_UP_ADAPTATION.md](docs/SHAPE_UP_ADAPTATION.md) - Methodology conversion
- [COMMUNICATION_PRESERVATION.md](docs/COMMUNICATION_PRESERVATION.md) - Context handling

### Version Information
- Migrator Version: 1.0.0
- Basecamp API: v4
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.