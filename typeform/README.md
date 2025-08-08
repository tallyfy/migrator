# Typeform to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Transform your Typeform conversational forms with their sophisticated logic jumps and engaging UI into Tallyfy's AI-powered workflow automation platform. This production-ready migrator intelligently determines whether forms should remain as simple kick-off forms or be split into multi-step workflows, handling complete data migration including questions, logic jumps, variables, calculations, and responses.

### Key Benefits
- ✅ AI-powered form complexity analysis and intelligent splitting
- ✅ Automatic conversion of large forms (>20 fields) into multi-step workflows
- ✅ Logic jump transformation to Tallyfy conditional rules
- ✅ Complete field type mapping with validation preservation
- ✅ Variable and calculation handling
- ✅ Response data migration with full fidelity
- ✅ Hidden field and URL parameter support
- ✅ Checkpoint/resume for large form libraries

### What Gets Migrated
- **Forms** → Tallyfy Blueprints (single form or multi-step workflow)
- **Questions** → Tallyfy field with appropriate field types
- **Logic Jumps** → Conditional Rules and Branching
- **Variables** → Process Variables or Calculated Fields
- **Hidden Fields** → Hidden field or Metadata
- **Responses** → Process Instances with Data
- **File Uploads** → Attachments or External Links
- **Webhooks** → Process Triggers (reconfiguration needed)
- **Themes** → Basic styling (limited support)

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large form libraries)
- Network access to both Typeform and Tallyfy APIs
- Typeform account with API access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Typeform**: Personal Access Token from account settings
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Required)**: API key for form splitting decisions from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/typeform

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
# Typeform API Configuration
TYPEFORM_ACCESS_TOKEN=tfp_your_personal_access_token_here
TYPEFORM_API_BASE=https://api.typeform.com  # or https://api.eu.typeform.com for EU

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
FORM_SPLITTING_THRESHOLD=20  # Fields above this trigger multi-step consideration
MIGRATE_RESPONSES=true  # Migrate form responses as process instances
PRESERVE_LOGIC_JUMPS=true  # Convert logic to conditional rules
VARIABLE_HANDLING=process_data  # Options: process_data, calculated_fields, metadata
```

### Required AI Configuration (Essential for Form Splitting)

```env
# Anthropic API for intelligent form splitting decisions
ANTHROPIC_API_KEY=sk-ant-api03-...  # REQUIRED for form analysis
AI_MODEL=claude-3-haiku-20240307
AI_TEMPERATURE=0
AI_MAX_TOKENS=500

# AI Feature Flags
AI_ANALYZE_FORM_COMPLEXITY=true  # Determine if form needs splitting
AI_GROUP_FIELDS_LOGICALLY=true  # Smart field grouping for steps
AI_MAP_COMPLEX_LOGIC=true  # Convert logic jumps intelligently
AI_OPTIMIZE_USER_FLOW=true  # Create optimal step sequence
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Form access permissions
- AI availability (required)
- Form complexity analysis

### 2. Dry Run (Preview without changes)
```bash
./migrate.sh --dry-run
```
Shows form transformation preview including splitting decisions.

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

This migrator uses AI as a critical component for intelligent form transformation:

### When AI Makes Critical Decisions

1. **Form Complexity Assessment**: Determines splitting strategy
   - Analyzes total field count, logic complexity, sections
   - **≤20 fields without complex logic** → Single kick-off form
   - **21-50 fields or moderate logic** → Multi-step workflow (2-4 steps)
   - **>50 fields or complex branching** → Complex workflow (5+ steps)
   - Groups related fields intelligently (contact info, preferences, etc.)

2. **Intelligent Field Grouping**: Creates logical workflow steps
   - Groups contact information together
   - Separates different topic sections
   - Places conditional fields in appropriate steps
   - Optimizes for user cognitive load

## 🔧 Technical Implementation Details

### Form Complexity Assessment Algorithm

```python
def assess_form_complexity(form):
    """Determine optimal transformation strategy"""
    
    # Calculate complexity score
    complexity_score = 0
    complexity_score += len(form.fields)  # Base field count
    complexity_score += len(form.logic) * 5  # Logic jumps add complexity
    complexity_score += len(form.variables) * 2  # Variables add complexity
    complexity_score += len(form.calculations) * 3  # Calculations add complexity
    
    # Check for special features
    has_payment = any(f.type == 'payment' for f in form.fields)
    has_file_upload = any(f.type == 'file_upload' for f in form.fields)
    has_branching = len(form.logic) > 3
    
    # AI-enhanced decision if available
    if ai_client and ai_client.enabled:
        ai_decision = ai_client.analyze_form_complexity({
            'field_count': len(form.fields),
            'logic_count': len(form.logic),
            'has_payment': has_payment,
            'field_types': [f.type for f in form.fields],
            'form_title': form.title
        })
        if ai_decision.confidence > 0.7:
            return ai_decision.strategy
    
    # Fallback heuristics
    if complexity_score <= 20 and not has_branching:
        return 'single_kickoff'
    elif complexity_score <= 50:
        return 'multi_step_simple'  # 2-4 steps
    else:
        return 'multi_step_complex'  # 5+ steps

def group_fields_into_steps(fields, strategy):
    """Intelligently group fields into workflow steps"""
    
    if strategy == 'single_kickoff':
        return [{'name': 'Form Submission', 'fields': fields}]
    
    # Common field groupings
    groups = {
        'personal': ['first_name', 'last_name', 'date_of_birth'],
        'contact': ['email', 'phone', 'address'],
        'preferences': ['newsletter', 'notifications', 'interests'],
        'payment': ['card_number', 'billing_address'],
        'documents': ['file_upload', 'resume', 'portfolio']
    }
    
    steps = []
    grouped_fields = set()
    
    # Group by predefined categories
    for group_name, field_patterns in groups.items():
        group_fields = []
        for field in fields:
            if any(pattern in field.ref.lower() for pattern in field_patterns):
                group_fields.append(field)
                grouped_fields.add(field.id)
        
        if group_fields:
            steps.append({
                'name': f'{group_name.title()} Information',
                'fields': group_fields
            })
    
    # Group remaining fields
    remaining = [f for f in fields if f.id not in grouped_fields]
    if remaining:
        # Split into chunks of 10 fields
        for i in range(0, len(remaining), 10):
            chunk = remaining[i:i+10]
            steps.append({
                'name': f'Additional Information {i//10 + 1}',
                'fields': chunk
            })
    
    return steps
```

### Field Type Transformation Matrix

```python
TYPEFORM_TO_TALLYFY_FIELD_MAP = {
    # Text inputs
    'short_text': 'text',
    'long_text': 'textarea',
    'email': 'email',
    'phone_number': 'phone',
    'website': 'url',
    
    # Selection fields
    'multiple_choice': 'radio',
    'dropdown': 'dropdown',
    'picture_choice': 'radio',  # With image URLs in description
    'yes_no': 'yes_no',
    'legal': 'yes_no',
    
    # Number inputs
    'number': 'number',
    'rating': 'rating',
    'opinion_scale': 'scale',
    'nps': 'scale',  # Net Promoter Score
    
    # Date/Time
    'date': 'date',
    
    # File handling
    'file_upload': 'file',
    
    # Special handling required
    'payment': 'text',  # Store payment reference only
    'group': None,  # Section header, not a field
    'statement': 'information',  # Informational text
    'matrix': 'table',  # Convert to table field
    'ranking': 'multiselect',  # With ordering preserved
}

def transform_typeform_field(field):
    """Transform Typeform field with special handling"""
    
    tallyfy_type = TYPEFORM_TO_TALLYFY_FIELD_MAP.get(field.type)
    
    base_field = {
        'name': field.title,
        'type': tallyfy_type,
        'required': field.required,
        'description': field.description
    }
    
    # Special handling for specific types
    if field.type == 'multiple_choice':
        base_field['options'] = [choice.label for choice in field.choices]
        base_field['allow_multiple'] = field.allow_multiple_selection
        
    elif field.type == 'picture_choice':
        # Store images as descriptions
        base_field['options'] = []
        for choice in field.choices:
            option = {
                'label': choice.label,
                'image_url': choice.attachment.href
            }
            base_field['options'].append(option)
            
    elif field.type == 'opinion_scale':
        base_field['min'] = field.start_at_one and 1 or 0
        base_field['max'] = field.steps
        base_field['labels'] = {
            'left': field.labels.left,
            'right': field.labels.right
        }
        
    elif field.type == 'file_upload':
        base_field['max_size_mb'] = 100  # Tallyfy limit
        base_field['allowed_types'] = field.properties.get('file_types', [])
        
    return base_field
```

### Logic Jump Transformation

```python
def transform_logic_jumps(form):
    """Convert Typeform logic jumps to Tallyfy conditional rules"""
    
    rules = []
    for logic in form.logic:
        for action in logic.actions:
            if action.action == 'jump':
                rule = {
                    'type': 'field_value',
                    'field_ref': logic.ref,
                    'condition': transform_condition(action.condition),
                    'action': {
                        'type': 'skip_to_step',
                        'target': map_ref_to_step(action.details.to.value)
                    }
                }
            elif action.action == 'add_variable':
                rule = {
                    'type': 'calculation',
                    'field_ref': logic.ref,
                    'variable': action.details.variable,
                    'expression': action.details.expression
                }
            rules.append(rule)
    
    return rules

def transform_condition(condition):
    """Transform Typeform condition to Tallyfy format"""
    
    operator_map = {
        'equal': '==',
        'not_equal': '!=',
        'greater_than': '>',
        'less_than': '<',
        'greater_equal': '>=',
        'less_equal': '<=',
        'contains': 'contains',
        'begins_with': 'starts_with',
        'ends_with': 'ends_with',
        'is_answered': 'is_not_empty',
        'is_not_answered': 'is_empty'
    }
    
    return {
        'operator': operator_map.get(condition.op, condition.op),
        'value': condition.vars[0].value if condition.vars else None
    }
```

### Response Migration Strategy

```python
def migrate_responses(form_id, blueprint_id):
    """Migrate form responses as process instances"""
    
    # Fetch responses in batches
    page_token = None
    total_migrated = 0
    
    while True:
        responses = typeform_client.get_responses(
            form_id,
            page_size=100,
            page_token=page_token
        )
        
        for response in responses.items:
            # Transform response to process instance
            process_data = {
                'blueprint_id': blueprint_id,
                'name': f"Response {response.response_id}",
                'created_at': response.submitted_at,
                'field_data': {}
            }
            
            # Map answers to field values
            for answer in response.answers:
                field_name = map_field_ref(answer.field.ref)
                process_data['field_data'][field_name] = extract_answer_value(answer)
            
            # Handle file uploads
            if response.file_uploads:
                process_data['attachments'] = migrate_files(response.file_uploads)
            
            # Create process instance
            tallyfy_client.create_process(process_data)
            total_migrated += 1
        
        if not responses.has_more:
            break
        page_token = responses.next_token
        
        # Rate limiting
        time.sleep(0.5)
    
    return total_migrated
```

### Performance Optimization

```python
# API Rate Limits
TYPEFORM_RATE_LIMITS = {
    'requests_per_second': 2,
    'requests_per_minute': 120,
    'batch_size': 100
}

# Memory Management for Large Forms
def process_large_form_library(workspace_id):
    """Process large form libraries efficiently"""
    
    forms = typeform_client.get_forms(workspace_id)
    
    for form_batch in chunk(forms, size=10):
        # Process forms in batches
        for form in form_batch:
            # Fetch full form definition
            full_form = typeform_client.get_form(form.id)
            
            # Transform and migrate
            blueprint = transform_form_to_blueprint(full_form)
            tallyfy_client.create_blueprint(blueprint)
            
            # Clear memory
            del full_form
            gc.collect()
        
        # Rate limit protection
        time.sleep(5)
```

### Migration Time Estimates

| Form Library Size | Forms | Total Questions | Responses | Migration Time |
|-------------------|-------|-----------------|-----------|----------------|
| Small | <10 | <200 | <1,000 | 30-60 min |
| Medium | 10-50 | 200-1,000 | 1,000-10,000 | 2-4 hours |
| Large | 50-200 | 1,000-5,000 | 10,000-50,000 | 8-16 hours |
| Enterprise | 200+ | 5,000+ | 50,000+ | 24-48 hours |

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `RATE_LIMIT_EXCEEDED` | Too many API calls | Implement 0.5s delay between calls |
| `FORM_TOO_COMPLEX` | >100 fields | Split into multiple blueprints |
| `LOGIC_JUMP_CIRCULAR` | Circular logic detected | Flag for manual review |
| `FILE_TOO_LARGE` | Upload >100MB | Store as external link |
| `PAYMENT_FIELD_FOUND` | Payment processing | Requires manual setup in Tallyfy |

3. **Logic Jump Transformation**: Converts conversational flow
   - Maps Typeform jumps to Tallyfy conditional rules
   - Handles complex branching patterns
   - Preserves skip logic and conditional display
   - Creates decision points in workflow

4. **Variable and Calculation Mapping**: Preserves dynamic elements
   - Score variables → Process scoring
   - Price calculations → Calculated fields
   - Hidden fields → Process metadata
   - Custom variables → Process data

5. **Response Flow Optimization**: Maintains engagement
   - Preserves Typeform's conversational feel where possible
   - Creates logical step progression
   - Minimizes redundant navigation
   - Maintains completion momentum

### AI Decision Transparency
- Form complexity scores with detailed reasoning
- Field grouping logic explained
- Logic transformation mappings documented
- Confidence scores for all decisions
- Manual review flags for complex cases
- Edit prompts in `src/prompts/` to customize behavior

## 📊 Field Type Mapping

### Complete Typeform to Tallyfy Field Mapping

| Typeform Field | Tallyfy field | Notes | Supported |
|----------------|-----------------|-------|-----------|
| **short_text** | text | Direct mapping | ✅ |
| **long_text** | textarea | Direct mapping | ✅ |
| **email** | text | With email validation | ✅ |
| **number** | text | Positive integers only | ✅ |
| **phone_number** | text | With phone validation | ✅ |
| **website** | text | With URL validation | ✅ |
| **multiple_choice** | radio_buttons or checklist | Single/multiple selection | ✅ |
| **dropdown** | dropdown | Direct mapping | ✅ |
| **picture_choice** | radio | Text labels only, images as reference | ⚠️ |
| **yes_no** | radio | Binary choice | ✅ |
| **opinion_scale** | text | 1-10 scale as number | ✅ |
| **rating** | text | Star rating as number | ✅ |
| **nps** | text | 0-10 scale | ✅ |
| **ranking** | textarea | As ordered list text | ⚠️ |
| **matrix** | table | Limited support | ⚠️ |
| **date** | date | Direct mapping | ✅ |
| **file_upload** | file | Size limits apply | ✅ |
| **payment** | Not supported | External payment required | ❌ |
| **legal** | textarea | As disclaimer text | ✅ |
| **statement** | textarea | Informational text | ✅ |
| **calendly** | text | As scheduling link | ⚠️ |
| **contact_info** | Multiple fields | Split into components | ✅ |
| **address** | textarea | Combined address field | ✅ |

### Field Features Support

| Feature | Tallyfy Support | Migration Strategy |
|---------|-----------------|-------------------|
| Required fields | ✅ Full | Direct mapping |
| Field validation | ✅ Partial | Email, URL, phone supported |
| Min/max length | ✅ Full | Character limits preserved |
| Custom error messages | ❌ None | Generic validation messages |
| Placeholder text | ✅ Full | Preserved as help text |
| Hidden fields | ✅ Full | As hidden field |
| Calculated fields | ⚠️ Limited | One-time calculation only |
| File size limits | ✅ Full | Respects Tallyfy limits |

## 📊 Migration Phases

### Phase 1: Discovery & Form Analysis (10-20 minutes)
- Connects to Typeform API
- Fetches all forms and structures
- **AI analyzes each form for complexity**
- Determines splitting strategy
- Maps logic jump patterns
- Generates transformation plan

### Phase 2: Form Structure Transformation (30-60 minutes)
- **Critical AI Decision**: Split or keep whole
- Converts forms to blueprints
- Groups fields into logical steps (if splitting)
- Transforms logic jumps to rules
- Maps variables and calculations
- Preserves hidden fields

### Phase 3: Response Migration (1-4 hours)
- Fetches form responses
- Creates process instances
- Maps response data to fields
- Preserves submission metadata
- Handles file attachments
- Maintains response relationships

### Phase 4: Validation & Testing (15-30 minutes)
- Verifies field mappings
- Validates logic transformations
- Tests workflow flow
- Generates migration report
- Lists items requiring manual configuration

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 10 forms
- SQLite database tracks decisions
- Resume from exact interruption point: `--resume`
- Preserves AI analysis results

### Selective Migration
```bash
# Migrate specific forms only
./migrate.sh --forms "Customer Survey,Lead Generation"

# Skip response migration
./migrate.sh --skip-responses

# Force single form (no splitting)
./migrate.sh --no-split

# Custom splitting threshold
./migrate.sh --split-threshold 30
```

### Form Analysis Options
```bash
# Analyze forms without migrating
./migrate.sh --analyze-only

# Generate splitting recommendations
./migrate.sh --splitting-report

# Export field mappings
./migrate.sh --export-mappings
```

## 🎯 Paradigm Shifts

### Critical Transformation: Conversational → Structured Workflow

Typeform's one-question-at-a-time conversational approach differs from Tallyfy's structured workflow model:

#### Conversational Flow → Step-Based Process
- **Before (Typeform)**: One question at a time, dynamic progression
- **After (Tallyfy)**: Multiple fields per step, structured flow
- **AI Strategy**: Groups related questions into logical steps
- **User Impact**: Different completion experience

#### Logic Jumps → Conditional Rules
- **Before (Typeform)**: Complex branching based on any answer
- **After (Tallyfy)**: Rule-based conditions between steps
- **AI Strategy**: Simplifies complex logic while preserving intent
- **User Impact**: Less dynamic but more predictable

#### Variables & Calculations → Static or Process Data
- **Before (Typeform)**: Real-time calculations and scoring
- **After (Tallyfy)**: One-time calculations or manual updates
- **AI Strategy**: Determines best approach per variable
- **User Impact**: Some dynamic features become static

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Payment Processing**: No native payment support in Tallyfy
- ❌ **Video Responses**: Not supported, text alternative needed
- ❌ **Calendly Integration**: Manual calendar setup required
- ❌ **Picture Choices**: Images not displayed, labels only
- ❌ **Matrix Questions**: Limited table support
- ❌ **Real-time Calculations**: Become one-time calculations

### Requires Manual Configuration
- ⚠️ **Complex Logic Jumps**: Some patterns need simplification
- ⚠️ **Custom Themes**: Basic styling only
- ⚠️ **Webhook Endpoints**: Need reconfiguration
- ⚠️ **Ranking Questions**: Convert to text lists
- ⚠️ **Advanced Validations**: Custom regex patterns not supported

## 🔍 Validation

### Automatic Validation
- ✅ Form structure integrity
- ✅ Field type compatibility
- ✅ Logic transformation validity
- ✅ Required field preservation
- ✅ Response data mapping
- ✅ File upload accessibility
- ✅ Workflow step sequencing

### Manual Validation Checklist
- [ ] Verify form splitting decisions are logical
- [ ] Check field groupings make sense
- [ ] Confirm logic jumps work correctly
- [ ] Validate calculations if used
- [ ] Test end-to-end form completion
- [ ] Review AI splitting recommendations
- [ ] Verify response data integrity

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 10 forms | 20-30 minutes | < 1GB |
| 10-50 forms | 45-90 minutes | 1-2GB |
| 50-200 forms | 2-4 hours | 2-3GB |
| > 200 forms | 4-8 hours | 3-4GB |

### Rate Limits
- **Typeform**: 2 requests/second
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 5-10 forms/hour
- **Bottleneck**: AI analysis and field grouping

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: `401 Unauthorized: Invalid access token`
**Solution**: 
- Regenerate token in Typeform settings
- Ensure token starts with 'tfp_'
- Check token hasn't expired

#### Rate Limit Exceeded
**Error**: `429 Too Many Requests`
**Solution**: 
- Implement 0.5 second delays
- Stay under 2 requests/second
- Use exponential backoff

#### Form Too Complex
**Error**: `Form complexity exceeds threshold`
**Solution**:
- Review AI splitting recommendations
- Manually adjust groupings
- Consider breaking into multiple forms

#### Logic Jump Failed
**Error**: `Cannot map complex logic pattern`
**Solution**:
- Simplify logic in Typeform first
- Use manual rules in Tallyfy
- Document complex patterns

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Analyze form complexity
./migrate.sh --analyze-form "form_id" > analysis.json

# Preview splitting decision
./migrate.sh --preview-split "form_id"
```

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `form_complexity_analysis.csv` - Complexity scores and decisions
- `field_mappings.csv` - All field type conversions
- `splitting_decisions.json` - AI form splitting logic
- `logic_transformations.csv` - Jump to rule mappings
- `errors.log` - Detailed error information
- `ai_decisions.json` - All AI reasoning
- `manual_review.md` - Items requiring attention

## 🔒 Security

### Credential Handling
- Personal access tokens in environment only
- No credentials in logs or code
- Token rotation recommended
- OAuth 2.0 available for production

### Data Privacy
- All processing done locally
- AI processes structure, not response data
- GDPR compliant options
- Response data encrypted in transit


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
2. Review form analysis reports
3. Check field mapping documentation
4. Verify API connectivity
5. Review AI splitting decisions

### Resources
- Typeform API Docs: https://developer.typeform.com/
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/typeform-vs-tallyfy/
- Form Design Best Practices: https://tallyfy.com/forms/

## 📚 Additional Resources

### Documentation
- [FIELD_MAPPING.md](docs/FIELD_MAPPING.md) - Detailed field type mappings
- [LOGIC_TRANSFORMATION.md](docs/LOGIC_TRANSFORMATION.md) - Logic jump patterns
- [SPLITTING_STRATEGIES.md](docs/SPLITTING_STRATEGIES.md) - Form splitting algorithms
- [AI_DECISIONS.md](docs/AI_DECISIONS.md) - AI reasoning documentation

### Version Information
- Migrator Version: 1.0.0
- Typeform API: v1
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.