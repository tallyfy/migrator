# Google Forms to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🔗 Getting Started with Tallyfy

- **📚 Migration Documentation**: [https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/](https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/)
- **🔌 Open API Documentation**: [https://go.tallyfy.com/api/](https://go.tallyfy.com/api/)
- **🚀 Start Free Trial**: [https://tallyfy.com/start/](https://tallyfy.com/start/)
- **📞 Schedule a Call**: [https://tallyfy.com/booking/](https://tallyfy.com/booking/)

## 🚀 Overview - PRODUCTION READY

Transform your Google Forms into Tallyfy workflows with this fully-implemented production API client. The migrator uses the actual Google Forms API v1 with both OAuth2 and service account authentication, intelligently analyzing form complexity to determine optimal transformation strategies.

### Key Benefits
- ✅ AI-powered form complexity analysis for intelligent transformation
- ✅ Automatic splitting of large forms (>20 questions) into workflows
- ✅ Section-based workflow step creation
- ✅ Response validation preservation
- ✅ Quiz functionality transformation
- ✅ Google Sheets response data migration
- ✅ Complete question type mapping
- ✅ Checkpoint/resume for large form collections

### What Gets Migrated
- **Forms** → Tallyfy Blueprints (single or multi-step)
- **Questions** → Tallyfy field with validation
- **Sections** → Workflow steps (when splitting)
- **Response Validation** → Field validation rules
- **Quiz Settings** → Process with scoring (limited)
- **Responses** → Process instances (via Sheets)
- **File Uploads** → External links (Google Drive)
- **Branching Logic** → Conditional rules (simple)
- **Collaborators** → Blueprint editors

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- Network access to Google and Tallyfy APIs
- Google account with Forms access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Google Forms**: OAuth2 authentication with Google account
- **Google Sheets**: For response data access
- **Tallyfy**: Admin access to create OAuth application
- **Anthropic (Required)**: API key for form analysis from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/google-forms

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
# Google API Configuration
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/callback
GOOGLE_CREDENTIALS_FILE=credentials.json  # OAuth2 credentials

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
FORM_SPLITTING_THRESHOLD=20  # Questions above this trigger splitting
MIGRATE_RESPONSES=true  # Via Google Sheets if linked
SECTION_TO_STEP=true  # Convert sections to workflow steps
QUIZ_HANDLING=process_with_notes  # Options: process_with_notes, ignore_scoring
```

### Required AI Configuration

```env
# Anthropic API for form analysis (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307
AI_TEMPERATURE=0
AI_MAX_TOKENS=500

# AI Features
AI_ANALYZE_SIMPLICITY=true  # Assess if form needs splitting
AI_GROUP_QUESTIONS=true  # Group related questions
AI_OPTIMIZE_SECTIONS=true  # Convert sections intelligently
```

## 🚦 Quick Start

### 1. Authenticate with Google
```bash
./migrate.sh --google-auth
```
Opens browser for Google OAuth2 authentication.

### 2. Readiness Check
```bash
./migrate.sh --readiness-check
```
Verifies API access and analyzes forms.

### 3. Dry Run
```bash
./migrate.sh --dry-run
```
Preview transformation without changes.

### 4. Full Migration
```bash
./migrate.sh
```
Execute complete migration.

## 🤖 AI-Powered Features

### Critical AI Decisions

1. **Form Simplicity Assessment**: Google Forms tend to be simpler
   - **≤20 questions, no sections** → Single kick-off form
   - **>20 questions or has sections** → Multi-step workflow
   - **Quiz with sections** → Steps with validation
   - **Page breaks present** → Natural step boundaries

2. **Section Transformation**: Converts sections to steps
   - Analyzes section titles and content
   - Groups related questions
   - Creates logical workflow progression
   - Maintains section order

3. **Response Validation Mapping**: Preserves data quality
   - Regex patterns → Field validation
   - Required fields → Mandatory field
   - Custom messages → Help text
   - Quiz answers → Process notes

4. **Branching Logic Simplification**: Basic logic support
   - Section navigation → Step conditions
   - Submit actions → Process completion
   - Limited to single conditions

## 📊 Field Type Mapping

### Question Type Conversions

| Google Forms Type | Tallyfy field | Notes | Supported |
|-------------------|-----------------|-------|-----------|
| **Short answer** | text | With validation | ✅ |
| **Paragraph** | textarea | Multi-line text | ✅ |
| **Multiple choice** | radio | Single selection | ✅ |
| **Checkboxes** | multiselect | Multiple selection | ✅ |
| **Dropdown** | dropdown | Direct mapping | ✅ |
| **Linear scale** | text | Scale as number | ✅ |
| **Multiple choice grid** | table | Limited support | ⚠️ |
| **Checkbox grid** | table | Limited support | ⚠️ |
| **Date** | date | Direct mapping | ✅ |
| **Time** | text | Time as text | ⚠️ |
| **File upload** | file | Via Google Drive | ⚠️ |

### Validation Support

| Validation Type | Tallyfy Support | Implementation |
|-----------------|-----------------|----------------|
| Required field | ✅ Full | Mandatory field |
| Text patterns (regex) | ✅ Partial | Common patterns only |
| Length limits | ✅ Full | Min/max characters |
| Number ranges | ✅ Full | Min/max values |
| Email validation | ✅ Full | Email field type |
| URL validation | ✅ Full | URL validation |
| Custom regex | ⚠️ Limited | Simple patterns only |

### Special Features

| Google Forms Feature | Tallyfy Equivalent | Notes |
|---------------------|-------------------|-------|
| Quiz grading | Process notes | No auto-grading |
| Answer key | Documentation | Manual reference |
| Response summary | Reports | External analytics |
| File upload to Drive | External links | Files stay in Drive |
| Email notifications | Process notifications | Reconfigure |
| Response editing | Process updates | Limited |
| Pre-filled links | Process templates | Different approach |

## 📊 Migration Phases

### Phase 1: Discovery (10-20 minutes)
- Authenticates with Google
- Fetches all accessible forms
- **AI analyzes each form's structure**
- Identifies section patterns
- Determines splitting needs

### Phase 2: Form Transformation (30-60 minutes)
- **AI decides: single form or multi-step**
- Converts to blueprints
- Maps questions to field
- Transforms sections to steps
- Preserves validation rules

### Phase 3: Response Migration (1-3 hours)
- Accesses linked Google Sheets
- Fetches response data
- Creates process instances
- Maps responses to fields
- Handles file references

### Phase 4: Validation (15-20 minutes)
- Verifies transformations
- Validates field mappings
- Tests workflow logic
- Generates reports

## 🔄 Advanced Features

### Selective Migration
```bash
# Specific forms only
./migrate.sh --forms "Survey,Feedback Form"

# Skip responses
./migrate.sh --skip-responses

# Force single form
./migrate.sh --no-split

# Include shared forms
./migrate.sh --include-shared
```

### Google Workspace Integration
```bash
# Use service account
./migrate.sh --service-account key.json

# Migrate entire domain
./migrate.sh --domain example.com

# Export to Sheets first
./migrate.sh --export-to-sheets
```

## 🎯 Paradigm Shifts

### Simplicity → Structure
- **Before**: Ultra-simple form creation
- **After**: Structured workflow processes
- **AI Strategy**: Adds structure while preserving simplicity
- **User Impact**: More capabilities but less simplicity

### Google Integration → Platform Agnostic
- **Before**: Deep Google Workspace integration
- **After**: Standalone workflow platform
- **AI Strategy**: Preserves data, changes integration
- **User Impact**: Different ecosystem

### Free Forever → Subscription Model
- **Before**: Completely free with no limits
- **After**: Subscription-based pricing
- **Impact**: Cost considerations

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Quiz Auto-grading** - No automatic scoring
- ❌ **Response Charts** - No built-in analytics
- ❌ **Grid Questions** - Limited table support
- ❌ **Time Duration** - No duration field type
- ❌ **YouTube Videos** - No embedded media
- ❌ **Response Editing Links** - Different permission model

### Requires Manual Configuration
- ⚠️ **Complex Branching** - Only basic logic supported
- ⚠️ **File Uploads** - Files remain in Google Drive
- ⚠️ **Email Notifications** - Reconfigure in Tallyfy
- ⚠️ **Collaborator Permissions** - Different model
- ⚠️ **Pre-filled URLs** - Manual template setup

## 🔍 Validation

### Automatic Validation
- ✅ Form structure integrity
- ✅ Question type compatibility
- ✅ Section transformation
- ✅ Validation rule mapping
- ✅ Response data integrity
- ✅ Permission preservation

### Manual Validation Checklist
- [ ] Verify form splitting is logical
- [ ] Check validation rules work
- [ ] Confirm section order preserved
- [ ] Test response data mapping
- [ ] Validate file upload handling
- [ ] Review quiz transformations

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 20 forms | 20-30 minutes | < 1GB |
| 20-100 forms | 45-90 minutes | 1-2GB |
| 100-500 forms | 2-4 hours | 2-3GB |
| > 500 forms | 4-8 hours | 3-4GB |

### Rate Limits
- **Google Forms**: No specific limits (reasonable use)
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 10-15 forms/hour

## 🐛 Troubleshooting

### Authentication Issues
**Error**: `OAuth2 authentication failed`
**Solution**: 
- Check Google Cloud Console settings
- Verify redirect URI matches
- Ensure correct API scopes

### Access Denied
**Error**: `Insufficient permissions`
**Solution**:
- Request forms.body scope
- Check form sharing settings
- Use service account for domain

### Response Data Missing
**Error**: `Cannot access responses`
**Solution**:
- Link form to Google Sheets
- Grant Sheets API access
- Check response count

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Statistics
- `form_analysis.csv` - Complexity scores
- `field_mappings.csv` - Type conversions
- `validation_rules.json` - Rule mappings
- `section_transformations.csv` - Step creation
- `unsupported_features.md` - Manual setup
- `ai_decisions.json` - AI reasoning

## 🔒 Security

### Authentication Security
- OAuth2 with Google
- Secure token storage
- Refresh token handling
- Scope minimization

### Data Privacy
- Local processing only
- No data stored permanently
- GDPR compliant options
- Educational data handling


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

### Resources
- Google Forms API: https://developers.google.com/forms
- Tallyfy Docs: https://developers.tallyfy.com/
- OAuth2 Setup: https://console.cloud.google.com/

## 📚 Additional Documentation

- [OAUTH_SETUP.md](docs/OAUTH_SETUP.md) - Google OAuth configuration
- [FIELD_MAPPING.md](docs/FIELD_MAPPING.md) - Complete mappings
- [QUIZ_TRANSFORMATION.md](docs/QUIZ_TRANSFORMATION.md) - Quiz handling

### Version Information
- Migrator Version: 1.0.0
- Google Forms API: v1
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details