# SurveyMonkey to Tallyfy Migrator

## Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## Getting Started with Tallyfy

- **Migration Documentation**: [https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/](https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/)
- **Open API Documentation**: [https://go.tallyfy.com/api/](https://go.tallyfy.com/api/)
- **Start Free Trial**: [https://tallyfy.com/start/](https://tallyfy.com/start/)
- **Schedule a Call**: [https://tallyfy.com/booking/](https://tallyfy.com/booking/)

## Overview

Transform your SurveyMonkey surveys with their multi-page structures, question logic, and rich question types into Tallyfy's AI-powered workflow automation platform. This production-ready migrator intelligently determines whether surveys should remain as simple kick-off forms or be split into multi-step workflows, handling complete data migration including questions, page logic, piping, collectors, and responses.

### Key Benefits
- AI-powered survey complexity analysis and intelligent splitting
- Automatic conversion of large surveys (>20 questions) into multi-step workflows
- SurveyMonkey page structure preserved as workflow steps
- Complete question type mapping with validation preservation
- Page logic and skip patterns transformed to conditional rules
- Response data migration with full fidelity
- Custom variable and piping support
- Checkpoint/resume for large survey libraries

### What Gets Migrated
- **Surveys** -> Tallyfy Blueprints (single form or multi-step workflow)
- **Questions** -> Tallyfy fields with appropriate field types
- **Pages** -> Workflow steps with logical grouping
- **Page Logic** -> Conditional Rules and Branching
- **Responses** -> Process Instances with Data
- **Custom Variables** -> Process Metadata
- **File Uploads** -> Attachments or External Links
- **Collectors** -> Metadata (reconfiguration needed)
- **Team Members** -> Tallyfy Users

## Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large survey libraries)
- Network access to both SurveyMonkey and Tallyfy APIs
- SurveyMonkey account with API access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **SurveyMonkey**: OAuth 2.0 access token from developer portal (https://developer.surveymonkey.com/)
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Required)**: API key for survey splitting decisions from https://console.anthropic.com/

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/surveymonkey

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

### Required Configuration

```env
# SurveyMonkey API Configuration
SURVEYMONKEY_ACCESS_TOKEN=your_oauth_access_token_here

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORG_ID=your_organization_subdomain

# Migration Options
MIGRATE_RESPONSES=true
MAX_RESPONSES_PER_SURVEY=50
```

### Required AI Configuration (Essential for Survey Splitting)

```env
# Anthropic API for intelligent survey splitting decisions
ANTHROPIC_API_KEY=sk-ant-api03-...  # REQUIRED for survey analysis
AI_MODEL=claude-opus-4-6
AI_TEMPERATURE=0
AI_MAX_TOKENS=500
```

## Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Survey access permissions
- AI availability (required)
- Survey complexity analysis

### 2. Dry Run (Preview without changes)
```bash
./migrate.sh --dry-run
```
Shows survey transformation preview including splitting decisions.

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

## AI-Powered Features

This migrator uses AI as a critical component for intelligent survey transformation:

### When AI Makes Critical Decisions

1. **Survey Complexity Assessment**: Determines splitting strategy
   - Analyzes total question count, page count, logic complexity
   - **<=15 questions without logic** -> Single kick-off form
   - **16-30 questions or moderate logic** -> Page-based multi-step workflow
   - **>30 questions or complex skip logic** -> Complex workflow (5+ steps)
   - Groups related questions intelligently (demographics, ratings, etc.)

2. **Intelligent Question Grouping**: Creates logical workflow steps
   - Groups demographic questions together
   - Separates choice-based from open-ended questions
   - Places matrix/ranking questions in dedicated steps
   - Optimizes for user cognitive load

## Question Type Mapping

### Complete SurveyMonkey to Tallyfy Field Mapping

| SurveyMonkey Question | Tallyfy Field | Notes | Supported |
|----------------------|---------------|-------|-----------|
| **single_choice** | radio | Direct mapping | Yes |
| **single_choice (menu)** | dropdown | Dropdown variant | Yes |
| **multiple_choice** | multiselect | Multiple selection | Yes |
| **dropdown** | dropdown | Direct mapping | Yes |
| **open_ended (single)** | text | Short text input | Yes |
| **open_ended (multi/essay)** | textarea | Long text input | Yes |
| **open_ended (numerical)** | text | With numeric validation | Yes |
| **matrix (single)** | textarea | Flattened as text | Partial |
| **matrix (multi)** | textarea | Flattened as text | Partial |
| **matrix (rating)** | textarea | Flattened as text | Partial |
| **ranking** | textarea | Serialized as ordered text | Partial |
| **demographic** | text | Multiple fields generated | Yes |
| **datetime (date)** | date | Direct mapping | Yes |
| **datetime (time)** | text | Time as text | Partial |
| **datetime (both)** | text | Combined date/time | Partial |
| **file_upload** | file | Size limits apply | Yes |
| **slider** | text | Numeric value as text | Partial |
| **slider (star_rating)** | text | Star count as text | Partial |
| **image_choice (single)** | radio | Text labels only | Partial |
| **image_choice (multi)** | multiselect | Text labels only | Partial |
| **presentation/text** | (skipped) | Display-only element | N/A |

### Field Features Support

| Feature | Tallyfy Support | Migration Strategy |
|---------|-----------------|-------------------|
| Required fields | Full | Direct mapping |
| Field validation | Partial | Email, numeric, URL supported |
| Min/max values | Full | Validation rules preserved |
| Custom error messages | None | Generic validation messages |
| Question descriptions | Full | Preserved as help text |
| Answer piping | Limited | Stored as metadata |
| Skip logic | Limited | Converted to step conditions |

## Migration Phases

### Phase 1: Discovery & Survey Analysis (10-20 minutes)
- Connects to SurveyMonkey API
- Fetches all surveys with full details (pages and questions)
- Gets group/team member information
- **AI analyzes each survey for complexity**
- Determines splitting strategy
- Generates transformation plan

### Phase 2: User Migration (5-15 minutes)
- Maps SurveyMonkey team/group members to Tallyfy users
- Creates guest users from respondent emails
- Preserves role assignments (admin, power, full, viewer)

### Phase 3: Survey Structure Transformation (30-60 minutes)
- **Critical AI Decision**: Split or keep whole
- Converts surveys to blueprints
- Maps pages to workflow steps
- Groups questions into logical sections (if splitting)
- Transforms question types to Tallyfy fields
- Preserves validation rules

### Phase 4: Response Migration (1-4 hours)
- Fetches survey responses via bulk endpoint
- Creates process instances
- Maps response data to fields
- Handles all answer types (choices, text, matrix, ranking, files)
- Preserves submission metadata and custom variables
- Maintains respondent information

### Phase 5: Validation & Testing (15-30 minutes)
- Verifies field mappings
- Validates template structures
- Tests workflow flow
- Generates migration report
- Lists items requiring manual configuration

## Advanced Features

### Checkpoint & Resume
- Automatic checkpoint after each survey migration
- SQLite database tracks progress and decisions
- Resume from exact interruption point: `--resume`
- Preserves AI analysis results

### Selective Migration
```bash
# Migrate specific surveys only
./migrate.sh --surveys "Customer Survey,Employee Feedback"

# Skip response migration
./migrate.sh --skip-responses

# Force single form (no splitting)
./migrate.sh --no-split

# Custom splitting threshold
./migrate.sh --split-threshold 30
```

## Paradigm Shifts

### Critical Transformation: Multi-Page Survey -> Structured Workflow

SurveyMonkey's multi-page survey approach maps naturally to Tallyfy's step-based workflow:

#### Pages -> Steps
- **Before (SurveyMonkey)**: Multiple pages with questions, optional skip logic
- **After (Tallyfy)**: Multiple steps with form fields, conditional rules
- **AI Strategy**: Uses page boundaries as natural step breaks
- **User Impact**: Similar completion experience

#### Question Types -> Field Types
- **Before (SurveyMonkey)**: Rich question types (matrix, ranking, sliders, image choice)
- **After (Tallyfy)**: Standard form fields (text, radio, dropdown, file)
- **AI Strategy**: Best-fit mapping with metadata preservation
- **User Impact**: Some visual differences for complex question types

#### Skip Logic -> Conditional Rules
- **Before (SurveyMonkey)**: Page-level and question-level skip logic
- **After (Tallyfy)**: Rule-based conditions between steps
- **AI Strategy**: Simplifies complex logic while preserving intent
- **User Impact**: Less dynamic but more predictable

## Known Limitations

### Cannot Migrate
- **Matrix Visual Layout**: Matrix questions are flattened to textarea
- **Image Choice Images**: Only text labels preserved, images not displayed
- **Slider Visual**: Slider UI becomes text input
- **Star Rating Visual**: Star rating becomes numeric text
- **Piping/Variables**: Dynamic text substitution becomes static
- **Quiz Scoring**: Quiz scores stored as metadata only

### Requires Manual Configuration
- **Complex Skip Logic**: Some patterns need simplification
- **Collector Settings**: Email invitations, web links need reconfiguration
- **Branding/Themes**: Custom styling not supported
- **A/B Testing**: Random assignment not supported
- **Integrations**: Webhook and API integrations need reconfiguration

## Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 10 surveys | 20-30 minutes | < 1GB |
| 10-50 surveys | 45-90 minutes | 1-2GB |
| 50-200 surveys | 2-4 hours | 2-3GB |
| > 200 surveys | 4-8 hours | 3-4GB |

### Rate Limits
- **SurveyMonkey**: 120 requests/minute (Basic), 500 requests/minute (Platinum)
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 5-10 surveys/hour
- **Bottleneck**: AI analysis and question grouping

## Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: `401 Unauthorized: Invalid access token`
**Solution**:
- Regenerate OAuth token in SurveyMonkey developer portal
- Ensure token has required scopes (surveys, responses, users)
- Check token has not expired

#### Rate Limit Exceeded
**Error**: `429 Too Many Requests`
**Solution**:
- Implement delays between API calls (automatic)
- Check your SurveyMonkey plan rate limits
- Use exponential backoff

#### Survey Too Complex
**Error**: `Survey complexity exceeds threshold`
**Solution**:
- Review AI splitting recommendations
- Manually adjust question groupings
- Consider breaking into multiple blueprints

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Analyze survey complexity
./migrate.sh --analyze-survey "survey_id" > analysis.json
```

## Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `survey_complexity_analysis.csv` - Complexity scores and decisions
- `field_mappings.csv` - All question type conversions
- `splitting_decisions.json` - AI survey splitting logic
- `errors.log` - Detailed error information
- `ai_decisions.json` - All AI reasoning
- `manual_review.md` - Items requiring attention

## Security

### Credential Handling
- OAuth access tokens in environment only
- No credentials in logs or code
- Token rotation recommended
- All processing done locally

### Data Privacy
- AI processes structure, not response data
- Response data encrypted in transit
- GDPR compliant options available
- No data stored on third-party services

## Tallyfy Field Types Reference

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

## SurveyMonkey API Reference

### Base URL
`https://api.surveymonkey.com/v3`

### Authentication
OAuth 2.0 Bearer token in Authorization header.

### Key Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/surveys` | GET | List all surveys |
| `/surveys/{id}/details` | GET | Full survey with pages and questions |
| `/surveys/{id}/responses/bulk` | GET | Bulk response export |
| `/surveys/{id}/collectors` | GET | Survey collectors |
| `/users/me` | GET | Current user/account info |
| `/groups` | GET | Team groups |
| `/groups/{id}/members` | GET | Group members |

### Pagination
SurveyMonkey uses `page` and `per_page` parameters:
```json
{
  "data": [...],
  "per_page": 100,
  "page": 1,
  "total": 250,
  "links": {
    "self": "https://api.surveymonkey.com/v3/surveys?page=1",
    "next": "https://api.surveymonkey.com/v3/surveys?page=2"
  }
}
```

### Question Families
- `single_choice` - Radio buttons or dropdown
- `multiple_choice` - Checkboxes
- `dropdown` - Dropdown menu
- `open_ended` - Text input (single, multi, essay, numerical)
- `matrix` - Grid/table (single, multi, rating, menu)
- `ranking` - Drag-and-drop ranking
- `demographic` - Contact information fields
- `datetime` - Date and/or time picker
- `file_upload` - File attachment
- `slider` - Slider or star rating
- `image_choice` - Image-based selection
- `presentation` - Display text/image (no input)

## Support

### Getting Help
1. Check [Troubleshooting](#troubleshooting) section
2. Review survey analysis reports
3. Check field mapping documentation
4. Verify API connectivity
5. Review AI splitting decisions

### Resources
- SurveyMonkey API Docs: https://developer.surveymonkey.com/api/v3/
- Tallyfy API Docs: https://developers.tallyfy.com/
- SurveyMonkey Developer Portal: https://developer.surveymonkey.com/

## Additional Resources

### Version Information
- Migrator Version: 1.0.0
- SurveyMonkey API: v3
- Tallyfy API: v2
- Last Updated: 2026-03-20

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
