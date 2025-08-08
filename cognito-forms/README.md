# Cognito Forms to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Transform your Cognito Forms with their powerful calculations, repeating sections, and advanced logic into Tallyfy's AI-powered workflow automation platform. This production-ready migrator uses AI to intelligently handle complex form structures, determining optimal workflow design while preserving as much functionality as possible from Cognito's advanced features.

### Key Benefits
- ✅ AI-powered analysis of complex forms with calculations
- ✅ Intelligent splitting of multi-page forms into workflows
- ✅ Repeating section transformation strategies
- ✅ Calculation preservation where possible
- ✅ Conditional logic conversion to workflow rules
- ✅ Complete field type mapping
- ✅ Entry data migration with full fidelity
- ✅ Checkpoint/resume for large form libraries

### What Gets Migrated
- **Forms** → Tallyfy Blueprints (single or multi-step)
- **Fields** → Tallyfy field with validation
- **Sections** → Workflow steps or field groups
- **Page Breaks** → Step boundaries
- **Repeating Sections** → Tables or multiple instances (limited)
- **Calculations** → One-time calculations or process notes
- **Conditional Logic** → Workflow rules and branching
- **Entries** → Process instances with data
- **File Uploads** → Attachments
- **Signatures** → File attachments
- **Payment Fields** → External payment notes

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended)
- Network access to Cognito Forms and Tallyfy APIs
- Cognito Forms account with API access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Cognito Forms**: API key from Settings → Integrations
- **Tallyfy**: Admin access to create OAuth application
- **Anthropic (Required)**: API key for complex form analysis

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/cognito-forms

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
# Cognito Forms API Configuration
COGNITO_API_KEY=your_api_key_here
COGNITO_ORG_NAME=your_organization_name

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
FORM_SPLITTING_THRESHOLD=20  # Fields trigger splitting analysis
PAGE_BREAK_HANDLING=step_boundaries  # Options: step_boundaries, ignore
REPEATING_SECTION_STRATEGY=table  # Options: table, flatten, document
CALCULATION_HANDLING=one_time  # Options: one_time, document, skip
MIGRATE_ENTRIES=true
```

### Required AI Configuration

```env
# Anthropic API (REQUIRED for complex forms)
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307
AI_TEMPERATURE=0
AI_MAX_TOKENS=500

# AI Features
AI_ANALYZE_CALCULATIONS=true  # Analyze calculation complexity
AI_TRANSFORM_REPEATING=true  # Handle repeating sections
AI_MAP_CONDITIONS=true  # Convert conditional logic
AI_OPTIMIZE_WORKFLOW=true  # Create optimal structure
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
Analyzes forms and verifies API access.

### 2. Dry Run
```bash
./migrate.sh --dry-run
```
Preview transformation without changes.

### 3. Full Migration
```bash
./migrate.sh
```
Execute complete migration.

### 4. Resume Interrupted Migration
```bash
./migrate.sh --resume
```
Continue from last checkpoint.

## 🤖 AI-Powered Features

### Critical AI Decisions for Complex Forms

1. **Calculation Complexity Assessment**: Determines handling strategy
   - **Simple calculations** → Process data fields
   - **Complex formulas** → Documentation with manual setup
   - **Aggregations** → Summary fields
   - **Cross-section calculations** → Process-level data

2. **Repeating Section Transformation**: Complex structural decisions
   - **Simple repeating fields** → Table field
   - **Complex repeating sections** → Multiple process instances
   - **Nested repeating** → Documentation for manual setup
   - **Calculations on repeating data** → Summary fields

3. **Multi-Page Form Optimization**: Creates logical workflows
   - Analyzes page break placement
   - Groups related fields into steps
   - Preserves logical flow
   - Optimizes for user experience

4. **Conditional Logic Mapping**: Preserves business rules
   - Show/hide conditions → Step visibility
   - Conditional requirements → Field rules
   - Dynamic values → Process calculations
   - Workflow triggers → Process automation

## 📊 Field Type Mapping

### Core Field Types

| Cognito Forms Type | Tallyfy field | Notes | Supported |
|-------------------|-----------------|-------|-----------|
| **Textbox** | short_text or long_text | Based on settings | ✅ |
| **Name** | text | Combined name field | ✅ |
| **Email** | text | With email validation | ✅ |
| **Phone** | text | With phone validation | ✅ |
| **Website** | text | With URL validation | ✅ |
| **Address** | textarea | Combined address | ✅ |
| **Choice** | dropdown, radio_buttons, or checklist | Based on type | ✅ |
| **Yes/No** | radio | Binary choice | ✅ |
| **Rating Scale** | text | Scale as number | ✅ |
| **Date** | date | With optional time | ✅ |
| **Number** | text | Direct mapping | ✅ |
| **Currency** | text | Currency as number | ✅ |
| **Calculation** | text | Read-only result | ⚠️ |
| **Signature** | file | As image file | ⚠️ |
| **File Upload** | file | Direct mapping | ✅ |
| **Person** | assignees_form | User selection | ✅ |

### Advanced Features

| Cognito Feature | Tallyfy Support | Migration Strategy |
|-----------------|-----------------|-------------------|
| **Repeating Section** | ⚠️ Limited | Tables or documentation |
| **Table** | ⚠️ Partial | Basic table support |
| **Calculations** | ⚠️ One-time | No live calculations |
| **Aggregations** | ❌ None | Document formulas |
| **Lookup Fields** | ❌ None | Manual reference |
| **Payment Processing** | ❌ None | External payment |
| **Inventory Tracking** | ❌ None | Manual tracking |
| **Save & Resume** | ⚠️ Different | Process drafts |

### Calculation Handling

Cognito Forms' powerful calculation engine requires special handling:

1. **Simple Math** → One-time calculation on form submission
2. **Date Calculations** → Process deadlines and dates
3. **Text Manipulation** → Static text fields
4. **Aggregations** → Summary notes
5. **Complex Formulas** → Documentation for manual recreation

## 📊 Migration Phases

### Phase 1: Discovery & Analysis (20-40 minutes)
- Fetches all forms via API
- **AI analyzes calculation complexity**
- Identifies repeating sections
- Maps conditional logic
- Determines transformation strategy

### Phase 2: Form Transformation (1-2 hours)
- **AI decides structure based on complexity**
- Converts forms to blueprints
- Handles page breaks as steps
- Transforms repeating sections
- Preserves calculations where possible
- Maps conditional logic

### Phase 3: Entry Migration (2-6 hours)
- Fetches form entries
- Creates process instances
- Maps entry data to fields
- Handles repeating data
- Preserves file attachments

### Phase 4: Validation (30-45 minutes)
- Verifies field mappings
- Validates logic transformations
- Documents calculation limitations
- Generates migration report

## 🔄 Advanced Features

### Selective Migration
```bash
# Specific forms only
./migrate.sh --forms "Application,Survey"

# Skip entries
./migrate.sh --skip-entries

# Force single form (no splitting)
./migrate.sh --no-split

# Document calculations only
./migrate.sh --document-calculations
```

### Complex Form Handling
```bash
# Analyze repeating sections
./migrate.sh --analyze-repeating

# Export calculation formulas
./migrate.sh --export-calculations

# Preview transformation
./migrate.sh --preview-transformation
```

## 🎯 Paradigm Shifts

### Calculations → Static or Manual
- **Before**: Live, dynamic calculations
- **After**: One-time or manual calculations
- **AI Strategy**: Preserves simple, documents complex
- **User Impact**: Loss of real-time calculations

### Repeating Sections → Limited Support
- **Before**: Dynamic, nested repeating sections
- **After**: Simple tables or multiple instances
- **AI Strategy**: Simplifies structure
- **User Impact**: Reduced flexibility

### Advanced Logic → Workflow Rules
- **Before**: Complex conditional logic
- **After**: Simpler workflow rules
- **AI Strategy**: Preserves essential logic
- **User Impact**: Some conditions simplified

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Live Calculations** - No real-time formulas
- ❌ **Nested Repeating Sections** - Not supported
- ❌ **Payment Processing** - External payment needed
- ❌ **Lookup Fields** - No cross-form references
- ❌ **Inventory Tracking** - Manual tracking only
- ❌ **Complex Aggregations** - No sum/average on repeating data

### Requires Manual Configuration
- ⚠️ **Complex Calculations** - Document formulas for recreation
- ⚠️ **Advanced Repeating Logic** - Simplification required
- ⚠️ **Multi-level Conditions** - May need restructuring
- ⚠️ **Save & Resume** - Different implementation
- ⚠️ **Custom Workflows** - Manual rule setup

## 🔍 Validation

### Automatic Validation
- ✅ Form structure integrity
- ✅ Field type compatibility
- ✅ Basic calculation preservation
- ✅ Conditional logic mapping
- ✅ Entry data integrity
- ✅ File attachment accessibility

### Manual Validation Checklist
- [ ] Verify form splitting is logical
- [ ] Check calculation documentation
- [ ] Confirm repeating section handling
- [ ] Test conditional logic
- [ ] Validate entry data mapping
- [ ] Review unsupported features

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 25 forms | 30-60 minutes | < 1GB |
| 25-100 forms | 1-3 hours | 1-2GB |
| 100-500 forms | 3-8 hours | 2-4GB |
| > 500 forms | 8-16 hours | 4-6GB |

### API Considerations
- No published rate limits
- Reasonable use expected
- Contact support for high volume
- OData queries for bulk operations

## 🐛 Troubleshooting

### Authentication Failed
**Error**: `Invalid API key`
**Solution**: 
- Regenerate key in Settings → Integrations
- Save key immediately (cannot retrieve later)
- Check organization name

### Calculation Too Complex
**Error**: `Cannot transform calculation`
**Solution**:
- Review calculation documentation
- Simplify in Cognito first
- Use manual calculation notes

### Repeating Section Failed
**Error**: `Repeating section too complex`
**Solution**:
- Use flatten strategy
- Document structure for manual setup
- Consider splitting into multiple forms

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `calculation_analysis.csv` - Calculation complexity
- `repeating_sections.json` - Section transformations
- `field_mappings.csv` - Type conversions
- `conditional_logic.json` - Logic mappings
- `unsupported_features.md` - Manual setup needed
- `calculation_formulas.md` - Formula documentation
- `ai_decisions.json` - AI reasoning

## 🔒 Security

### API Security
- Bearer token authentication
- Secure token storage
- Up to 5 keys per integration
- Keys cannot be retrieved after creation

### Data Privacy
- Local processing only
- HIPAA compliance available
- No data permanently stored
- Audit trail maintained


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
- Cognito Forms API: https://www.cognitoforms.com/support/data-integration
- Tallyfy Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/cognito-forms-vs-tallyfy/

## 📚 Additional Documentation

- [CALCULATION_GUIDE.md](docs/CALCULATION_GUIDE.md) - Calculation transformation
- [REPEATING_SECTIONS.md](docs/REPEATING_SECTIONS.md) - Section handling
- [FIELD_MAPPING.md](docs/FIELD_MAPPING.md) - Complete mappings
- [CONDITIONAL_LOGIC.md](docs/CONDITIONAL_LOGIC.md) - Logic transformation

### Version Information
- Migrator Version: 1.0.0
- Cognito Forms API: REST/OData v4
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details