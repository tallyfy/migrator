# Jotform to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Transform your Jotform forms with their extensive widget library, complex conditional logic, and advanced features into Tallyfy's AI-powered workflow automation platform. This production-ready migrator intelligently analyzes form complexity to determine optimal workflow structure, handling complete data migration including fields, widgets, conditions, calculations, and submissions.

### Key Benefits
- ✅ AI-powered form analysis for intelligent workflow creation
- ✅ Automatic splitting of complex forms (>20 fields) into multi-step processes
- ✅ Widget transformation to appropriate Tallyfy field types
- ✅ Conditional logic preservation as workflow rules
- ✅ Calculation conversion to process data
- ✅ Complete submission data migration
- ✅ File upload and signature handling
- ✅ Checkpoint/resume for large form collections

### What Gets Migrated
- **Forms** → Tallyfy Blueprints (single or multi-step based on complexity)
- **Fields** → Tallyfy field with type mapping
- **Widgets** → Appropriate field types or metadata (500+ widgets)
- **Conditions** → Workflow rules and branching
- **Calculations** → Calculated fields or process data
- **Page Breaks** → Workflow step boundaries
- **Submissions** → Process instances with data
- **File Uploads** → Attachments or external links
- **Signatures** → File attachments
- **Payment Fields** → External payment notes

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large accounts)
- Network access to both Jotform and Tallyfy APIs
- Jotform account with API access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Jotform**: API key from My Account → API section
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Required)**: API key for form analysis from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/jotform

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
# Jotform API Configuration
JOTFORM_API_KEY=your_api_key_here
JOTFORM_API_BASE=https://api.jotform.com  # or eu-api.jotform.com, hipaa-api.jotform.com

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
FORM_SPLITTING_THRESHOLD=20  # Fields above this trigger splitting analysis
WIDGET_HANDLING=best_match  # Options: best_match, metadata, skip
MIGRATE_SUBMISSIONS=true
PRESERVE_CONDITIONS=true
CALCULATION_HANDLING=process_data  # Options: process_data, one_time, skip
```

### Required AI Configuration (Essential for Form Analysis)

```env
# Anthropic API for intelligent form analysis
ANTHROPIC_API_KEY=sk-ant-api03-...  # REQUIRED for form splitting
AI_MODEL=claude-3-haiku-20240307
AI_TEMPERATURE=0
AI_MAX_TOKENS=500

# AI Feature Flags
AI_ANALYZE_COMPLEXITY=true  # Analyze form structure
AI_SPLIT_INTELLIGENTLY=true  # Smart form splitting
AI_MAP_WIDGETS=true  # Widget to field mapping
AI_TRANSFORM_CONDITIONS=true  # Condition to rule conversion
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
Verifies API connectivity and analyzes form complexity.

### 2. Dry Run (Preview without changes)
```bash
./migrate.sh --dry-run
```
Shows transformation preview including splitting decisions.

### 3. Full Migration
```bash
./migrate.sh
```
Executes complete migration with progress tracking.

### 4. Resume Interrupted Migration
```bash
./migrate.sh --resume
```
Continues from last checkpoint.

## 🤖 AI-Powered Features

### Critical AI Decisions for Form Transformation

1. **Form Complexity Analysis**: Determines optimal structure
   - **≤20 fields, no conditions** → Single kick-off form
   - **21-50 fields, simple conditions** → 2-4 step workflow
   - **>50 fields or complex logic** → 5+ step workflow
   - **Page breaks present** → Steps align with pages
   - **Collapsed sections** → Become workflow steps

2. **Widget Transformation Strategy**: Maps 500+ widgets
   - Analyzes widget functionality
   - Maps to closest Tallyfy equivalent
   - Preserves data where possible
   - Documents unsupported features

3. **Field Grouping Intelligence**: Creates logical steps
   - Groups related fields (contact, preferences, etc.)
   - Respects page breaks as natural boundaries
   - Considers conditional logic flow
   - Optimizes for user experience

4. **Condition Transformation**: Converts complex logic
   - Show/hide conditions → Step visibility rules
   - Calculate conditions → Process calculations
   - Skip logic → Branching rules
   - Email routing → Assignment rules

## 📊 Field Type Mapping

### Core Field Types

| Jotform Field | Tallyfy field | Notes | Supported |
|---------------|-----------------|-------|-----------|
| **control_textbox** | text | Direct mapping | ✅ |
| **control_textarea** | textarea | Direct mapping | ✅ |
| **control_dropdown** | dropdown | Direct mapping | ✅ |
| **control_radio** | radio | Direct mapping | ✅ |
| **control_checkbox** | multiselect | Multiple selection | ✅ |
| **control_number** | text | Numeric input | ✅ |
| **control_email** | text | With email validation | ✅ |
| **control_phone** | text | With phone validation | ✅ |
| **control_fullname** | text | Combined name field | ✅ |
| **control_address** | textarea | Combined address | ✅ |
| **control_datetime** | date | Date with optional time | ✅ |
| **control_fileupload** | file | Size limits apply | ✅ |
| **control_signature** | file | As image file | ⚠️ |
| **control_rating** | text | Rating as number | ✅ |
| **control_scale** | text | Scale as number | ✅ |
| **control_matrix** | table | Limited support | ⚠️ |

### Special Fields & Widgets

| Jotform Element | Tallyfy Mapping | Migration Strategy |
|-----------------|-----------------|-------------------|
| **control_payment** | Not supported | Document payment externally | ❌ |
| **control_product** | textarea | Product list as text | ⚠️ |
| **control_appointment** | date | Appointment time only | ⚠️ |
| **control_widget** | Varies | Depends on widget type | ⚠️ |
| **Configurable List** | table | As table if simple | ⚠️ |
| **Form Calculation** | Process data | One-time calculation | ⚠️ |
| **Image Picker** | radio | Labels only, no images | ⚠️ |
| **Spreadsheet** | table | Limited grid support | ⚠️ |
| **E-signature** | file | As signature image | ⚠️ |
| **Timer** | Not supported | Document timing needs | ❌ |
| **Maps** | text | Location as text | ⚠️ |
| **Social Media** | text | Handle/URL as text | ⚠️ |

### Widget Handling Strategy

The migrator uses AI to determine the best mapping for Jotform's 500+ widgets:

1. **Direct Mapping** - Widget has clear Tallyfy equivalent
2. **Best Match** - AI finds closest functional match
3. **Metadata** - Widget data preserved as field metadata
4. **Documentation** - Complex widgets documented for manual setup
5. **Skip** - Non-essential widgets excluded

## 📊 Migration Phases

### Phase 1: Discovery & Analysis (15-30 minutes)
- Fetches all forms via API
- **AI analyzes each form's complexity**
- Identifies widget usage patterns
- Maps conditional logic flows
- Determines splitting strategies

### Phase 2: Form Transformation (45-90 minutes)
- **AI decides: single form or multi-step workflow**
- Converts forms to blueprints
- Groups fields into logical steps
- Transforms conditions to rules
- Maps widgets to appropriate fields
- Handles calculations

### Phase 3: Submission Migration (1-6 hours)
- Fetches form submissions
- Creates process instances
- Maps submission data
- Handles file attachments
- Preserves submission metadata

### Phase 4: Validation (20-30 minutes)
- Verifies field mappings
- Validates logic transformations
- Tests workflow execution
- Generates migration report

## 🔄 Advanced Features

### Selective Migration
```bash
# Migrate specific forms
./migrate.sh --forms "Contact Form,Survey"

# Skip submissions
./migrate.sh --skip-submissions

# Force single form (no splitting)
./migrate.sh --no-split

# Custom threshold
./migrate.sh --split-threshold 30
```

### Widget Analysis
```bash
# Analyze widget usage
./migrate.sh --widget-report

# Export widget mappings
./migrate.sh --export-widget-mappings
```

## 🎯 Paradigm Shifts

### Form Builder → Workflow Platform
- **Before (Jotform)**: Form-centric with extensive customization
- **After (Tallyfy)**: Process-centric with structured workflows
- **AI Strategy**: Transforms forms into logical processes
- **User Impact**: Shift from form thinking to process thinking

### 500+ Widgets → Core Field Types
- **Before (Jotform)**: Specialized widgets for everything
- **After (Tallyfy)**: Standardized field types
- **AI Strategy**: Maps functionality, not appearance
- **User Impact**: Some visual features lost

### Complex Conditions → Workflow Rules
- **Before (Jotform)**: Intricate conditional logic
- **After (Tallyfy)**: Structured workflow rules
- **AI Strategy**: Simplifies while preserving logic
- **User Impact**: More predictable flow

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Payment Processing** - No native payments in Tallyfy
- ❌ **Appointment Scheduling** - External calendar needed
- ❌ **Timer Widgets** - No time tracking widgets
- ❌ **Social Media Widgets** - Manual integration needed
- ❌ **Advanced Calculations** - Limited to one-time calculations
- ❌ **Custom CSS/JavaScript** - No custom code support

### Requires Manual Configuration
- ⚠️ **Complex Widgets** - Many widgets need manual mapping
- ⚠️ **Multi-level Conditions** - Simplification required
- ⚠️ **Product Lists** - Convert to simple selection
- ⚠️ **Configurable Lists** - Limited table support
- ⚠️ **Image-based Fields** - Images not displayed

## 🔍 Validation

### Automatic Validation
- ✅ Form structure integrity
- ✅ Field type compatibility
- ✅ Widget mapping success
- ✅ Condition transformation
- ✅ Submission data integrity
- ✅ File attachment accessibility

### Manual Validation Checklist
- [ ] Verify form splitting is logical
- [ ] Check widget mappings are acceptable
- [ ] Confirm conditions work correctly
- [ ] Test calculations if present
- [ ] Validate end-to-end workflow
- [ ] Review unsupported widgets

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 25 forms | 30-45 minutes | < 1GB |
| 25-100 forms | 1-2 hours | 1-2GB |
| 100-500 forms | 3-6 hours | 2-3GB |
| > 500 forms | 6-12 hours | 3-4GB |

### Rate Limits (by Plan)
- **Starter**: 1,000 API calls/day
- **Bronze**: 10,000 API calls/day
- **Silver**: 50,000 API calls/day
- **Gold**: 100,000 API calls/day
- **Enterprise**: Unlimited

## 🐛 Troubleshooting

### Common Issues

#### API Limit Exceeded
**Error**: `Daily API limit reached`
**Solution**: 
- Check your Jotform plan limits
- Wait until midnight EST for reset
- Upgrade plan if needed

#### Widget Mapping Failed
**Error**: `Cannot map widget: {widget_type}`
**Solution**:
- Review widget analysis report
- Use --widget-handling metadata
- Document for manual setup

#### Form Too Complex
**Error**: `Form exceeds complexity threshold`
**Solution**:
- Review AI analysis
- Consider breaking form in Jotform first
- Adjust splitting threshold

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `form_complexity.csv` - Complexity scores
- `widget_mappings.csv` - Widget transformations
- `field_mappings.csv` - Field type conversions
- `condition_transformations.json` - Logic mappings
- `unsupported_features.md` - Manual setup needed
- `ai_decisions.json` - AI reasoning

## 🔒 Security

### Credential Handling
- API keys in environment variables only
- No credentials in logs
- Secure token storage
- Regular key rotation recommended

### Data Privacy
- Local processing only
- AI analyzes structure, not data
- HIPAA compliance option available
- GDPR compliant processing


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
- Jotform API Docs: https://api.jotform.com/docs/
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/jotform-vs-tallyfy/

## 📚 Additional Documentation

- [WIDGET_MAPPING.md](docs/WIDGET_MAPPING.md) - 500+ widget mappings
- [FIELD_TYPES.md](docs/FIELD_TYPES.md) - Complete field mapping
- [CONDITION_LOGIC.md](docs/CONDITION_LOGIC.md) - Logic transformation

### Version Information
- Migrator Version: 1.0.0
- Jotform API: v1
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details