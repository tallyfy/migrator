# Cognito Forms to Tallyfy Object Mapping

## Core Object Mappings

### Organizational Structure

| Cognito Forms Object | Tallyfy Object | Notes |
|---------------------|----------------|-------|
| Organization | Organization | Account container |
| Form | Blueprint | Process template |
| Entry | Process Instance | Form submission |
| User | Member | Account users |
| Public Link | Public Process | External access |
| Folder | Category/Tag | Form organization |

### Form/Process Structure

| Cognito Forms Object | Tallyfy Object | Transformation Logic |
|---------------------|----------------|----------------------|
| Form Fields | Kick-off Fields | Initial data collection |
| Sections | Field Groups | Logical grouping |
| Pages | Process Steps | Multi-page conversion |
| Repeating Sections | Table Fields | Dynamic row data |
| Calculations | Calculated Fields | Formula preservation |
| Workflow | Process Flow | Post-submission actions |

## Field Type Mappings

### Basic Fields

| Cognito Forms Field | Tallyfy Field | Conversion Notes |
|--------------------|---------------|------------------|
| Textbox | Short Text | Single line |
| Text Area | Long Text | Multi-line |
| Email | Email | Email validation |
| Phone | Phone | Format preserved |
| Number | Number | Numeric input |
| Currency | Number | Money format |
| Percent | Number | 0-100 range |
| Date | Date | Date picker |
| Time | Time | Time selection |
| Date/Time | DateTime | Combined field |
| Yes/No | Yes/No | Boolean |
| Choice - Radio | Radio Select | Single choice |
| Choice - Dropdown | Dropdown | Select list |
| Choice - Checkboxes | Multi-select | Multiple choices |

### Advanced Fields

| Cognito Forms Field | Tallyfy Field | Implementation Strategy |
|--------------------|---------------|------------------------|
| Address | Address Fields | Component fields |
| Name | Name Fields | First/Last/Middle |
| Rating Scale | Rating | Star or numeric |
| Signature | Signature | E-signature |
| File Upload | File Attachment | Document upload |
| Rich Text Area | Rich Text | Formatted content |
| Content | Instruction Text | Static content |
| Page Break | Step Boundary | New process step |
| Section | Field Group | Collapsible group |
| Repeating Section | Table/Grid | Dynamic rows |
| Table | Data Table | Structured data |

### Calculation Fields

| Cognito Forms Calculation | Tallyfy Implementation | Method |
|--------------------------|------------------------|--------|
| Calculated Field | Read-only Field | Display result |
| Price Calculation | Cost Field | Computed value |
| Quantity Calculation | Auto-computed | Formula in metadata |
| Date Calculation | Date Logic | Calculated dates |
| Conditional Calculation | Conditional Value | Rule-based |
| Summary Calculation | Aggregate Field | Totals/averages |

## Advanced Features

### Conditional Logic

| Cognito Forms Logic | Tallyfy Rules | Transformation |
|--------------------|---------------|---------------|
| Show/Hide Fields | Conditional Display | Dynamic visibility |
| Require Fields | Conditional Required | Dynamic validation |
| Set Field Values | Auto-populate | Value assignment |
| Skip Pages | Step Branching | Conditional flow |
| Custom Messages | Dynamic Text | Conditional content |
| Calculations | Computed Values | Formula execution |

### Payment Processing

| Payment Feature | Tallyfy Approach | Implementation |
|----------------|------------------|----------------|
| Payment Fields | Payment Step | External gateway |
| Product Fields | Line Items | Order details |
| Quantity Fields | Item Count | Numeric input |
| Discount Fields | Discount Logic | Calculation rules |
| Tax Calculation | Tax Rules | Regional logic |
| Payment Methods | Gateway Config | Stripe/PayPal/Square |
| Invoice Generation | Document Step | PDF creation |
| Receipt Email | Confirmation | Auto-send |

### Workflow Automation

| Cognito Workflow | Tallyfy Automation | Configuration |
|-----------------|-------------------|---------------|
| Email Notifications | Email Rules | Trigger conditions |
| Confirmation Emails | Auto-response | Submission confirm |
| Data Routing | Assignment Rules | Dynamic routing |
| Integration Actions | Webhooks | External systems |
| Document Generation | Template Merge | Dynamic documents |
| Approval Workflow | Approval Steps | Multi-level approval |
| Status Updates | Process Status | State transitions |

## Data Features

### OData Query Support

| OData Feature | Tallyfy API | Migration Approach |
|--------------|-------------|-------------------|
| $filter | API Filters | Query parameters |
| $select | Field Selection | Specific fields |
| $orderby | Sorting | Result ordering |
| $top/$skip | Pagination | Result limiting |
| $expand | Related Data | Include relations |
| $count | Record Count | Total results |

### Data Export Formats

| Cognito Export | Tallyfy Export | Conversion |
|---------------|----------------|------------|
| Excel | CSV/Excel | Direct export |
| CSV | CSV | Direct mapping |
| PDF | PDF | Document generation |
| JSON | JSON | API export |
| XML | JSON | Transform to JSON |
| Word Merge | Document Template | Mail merge |

## Paradigm Shifts

### 1. Form Builder → Process Designer
**Cognito Forms**: Visual form creation with fields
**Tallyfy**: Process workflow with steps
**Transformation**: Forms become multi-step processes

### 2. Entries → Active Processes
**Cognito Forms**: Static entry storage
**Tallyfy**: Active workflow instances
**Transformation**: Entries become trackable processes

### 3. Repeating Sections → Structured Data
**Cognito Forms**: Dynamic form sections
**Tallyfy**: Table fields or sub-processes
**Transformation**: Flatten or create child processes

### 4. Complex Calculations → Process Logic
**Cognito Forms**: Real-time calculations
**Tallyfy**: Step-based computations
**Transformation**: Calculate at specific steps

### 5. Payment Collection → Approval Gates
**Cognito Forms**: Integrated payment processing
**Tallyfy**: Payment as approval step
**Transformation**: Payment confirmation before proceeding

## Calculation System Mapping

### Formula Conversion

| Cognito Formula Type | Tallyfy Approach | Example |
|---------------------|------------------|---------|
| Field Reference | Variable Reference | `=[FieldName]` → `${field_name}` |
| Math Operations | Calculate Step | `=[Price]*[Quantity]` |
| Date Calculations | Date Logic | `=AddDays([Date],7)` |
| Text Functions | String Operations | `=Concat([First],[Last])` |
| Conditional Logic | If/Then Rules | `=If([Age]>=18,"Adult","Minor")` |
| Aggregate Functions | Summary Fields | `=Sum([Items].Price)` |

### Function Mappings

| Cognito Function | Tallyfy Equivalent | Implementation |
|-----------------|-------------------|----------------|
| Sum() | SUM aggregate | Total calculation |
| Count() | COUNT function | Item counting |
| Average() | AVG calculation | Mean value |
| Min()/Max() | MIN/MAX values | Range finding |
| If() | Conditional rule | Branching logic |
| And()/Or() | Logic operators | Combined conditions |
| Contains() | Text search | String matching |
| Format() | Format rules | Display formatting |

## Data Preservation Strategy

### High Priority (Must Preserve)
- Form structure and fields
- All entries/submissions
- Calculation formulas
- Conditional logic rules
- Payment configurations
- File uploads
- User assignments
- Workflow automations
- Repeating section data

### Medium Priority (Preserve if Possible)
- Form themes/styling
- Email templates
- Custom CSS/JavaScript
- Analytics data
- Form versioning
- Partial submissions
- Integration mappings
- Custom domains

### Low Priority (Document Only)
- Visual design elements
- Form themes
- Font preferences
- Color schemes
- Layout preferences
- Browser rules
- Device-specific settings

## Migration Complexity Levels

### Simple Form (1-2 hours)
- <20 fields
- No calculations
- Single page
- Basic validations
- No payments

### Medium Form (2-4 hours)
- 20-50 fields
- Basic calculations
- 2-3 pages
- Conditional logic
- Email notifications
- Some integrations

### Complex Form (4-8 hours)
- 50+ fields
- Complex calculations
- Multiple pages
- Repeating sections
- Payment processing
- Workflow automation
- Multiple integrations

### Enterprise Form (8+ hours)
- 100+ fields
- Advanced calculations
- Complex workflows
- Multi-level approvals
- Custom integrations
- Document generation
- API dependencies
- Multi-language support

## Special Handling Requirements

### 1. Repeating Sections
```
Cognito: Dynamic form sections that can be added/removed
Tallyfy: Options:
  1. Table field for simple data
  2. Sub-processes for complex sections
  3. JSON storage for preservation
```

### 2. Payment Processing
- Map payment fields to payment step
- Configure gateway settings
- Preserve product catalog
- Handle tax calculations
- Set up invoice generation

### 3. Complex Calculations
- Document all formulas
- Identify dependencies
- Create calculation steps
- Preserve calculation order
- Handle circular references

### 4. Document Generation
- Map merge fields
- Configure templates
- Set generation triggers
- Handle multiple formats
- Preserve formatting

### 5. Multi-Page Forms
- Each page → Process phase
- Preserve page conditions
- Map navigation logic
- Handle save & resume
- Track progress

## Integration Handling

### Native Integrations

| Cognito Integration | Tallyfy Alternative | Migration Path |
|--------------------|-------------------|----------------|
| Zapier | Zapier | Reconfigure zaps |
| Webhooks | Webhooks | Update endpoints |
| SQL Server | API/Database | Custom integration |
| SharePoint | Document Storage | File references |
| Salesforce | CRM Integration | API mapping |
| Mailchimp | Email Platform | Webhook/API |
| Google Sheets | Export/Import | API connection |
| PayPal/Stripe | Payment Gateway | Reconfigure |

### API Migration

| API Feature | Migration Approach | Notes |
|------------|-------------------|-------|
| REST API | Tallyfy API | Endpoint mapping |
| OData Queries | API Filters | Query translation |
| Webhooks | Webhook Rules | Event mapping |
| Custom Actions | Process Automation | Rule creation |

## Validation Rules

### Field Validation Mapping

| Cognito Validation | Tallyfy Validation | Configuration |
|-------------------|-------------------|---------------|
| Required | Required Field | Mandatory flag |
| Pattern | Regex Pattern | Pattern matching |
| Range | Min/Max Values | Numeric bounds |
| Length | Character Limits | Text constraints |
| Custom Message | Error Text | User feedback |
| Conditional Required | Dynamic Rules | Conditional logic |
| Cross-field | Field Dependencies | Related validation |

## Recommended Migration Sequence

1. **Discovery Phase**
   - Inventory all forms
   - Analyze complexity
   - Document calculations
   - Map integrations
   - Identify payment forms

2. **Planning Phase**
   - Prioritize forms
   - Map field types
   - Document logic
   - Plan workflows
   - Estimate effort

3. **User Migration**
   - Export users
   - Create accounts
   - Map permissions
   - Configure teams

4. **Form Structure**
   - Create blueprints
   - Map fields
   - Configure pages
   - Set validations

5. **Logic Transfer**
   - Implement calculations
   - Configure conditions
   - Set up branching
   - Create workflows

6. **Data Migration**
   - Export entries
   - Transform data
   - Import instances
   - Verify integrity

7. **Integration Setup**
   - Configure webhooks
   - Set up payments
   - Connect systems
   - Test workflows

8. **Validation**
   - Test submissions
   - Verify calculations
   - Check integrations
   - Validate workflows

## Known Limitations

### Cannot Migrate
- Custom CSS/JavaScript
- Form themes/styling
- Analytics history
- Version history
- Partial submissions
- Custom domains (require setup)
- Browser-specific rules

### Requires Manual Setup
- Payment gateway credentials
- Complex calculation formulas
- Custom integration code
- Advanced workflow logic
- Document templates
- Email templates
- API configurations

## Best Practices

### Form Optimization
- Simplify complex calculations
- Reduce page count
- Consolidate similar fields
- Streamline conditionals

### Process Enhancement
- Add approval steps
- Implement SLAs
- Include notifications
- Add quality checks

### Data Management
- Clean historical data
- Standardize formats
- Archive old entries
- Document schemas

## Migration Examples

### Example 1: Order Form with Payment
**Cognito Forms**:
- Customer info section
- Product selection with calculations
- Payment collection
- Order confirmation

**Tallyfy Process**:
1. Customer Information (Kick-off)
2. Product Selection (Form with calculations)
3. Order Review (Approval)
4. Payment Processing (Payment step)
5. Order Confirmation (Completion)
6. Fulfillment Trigger (Integration)

### Example 2: Multi-Level Approval Form
**Cognito Forms**:
- Request details
- Conditional routing based on amount
- Email notifications
- Status tracking

**Tallyfy Process**:
1. Request Submission (Kick-off)
2. Initial Review (Task)
3. Manager Approval (Conditional)
4. Director Approval (If amount > $10k)
5. Finance Review (Task)
6. Final Notification (Completion)

### Example 3: Event Registration with Repeating Sections
**Cognito Forms**:
- Primary registrant
- Additional attendees (repeating)
- Session selection
- Payment calculation

**Tallyfy Process**:
1. Primary Registration (Kick-off)
2. Add Attendees (Table field)
3. Session Selection (Multi-select)
4. Registration Review (Task)
5. Payment Collection (Payment)
6. Confirmation Emails (Automated)