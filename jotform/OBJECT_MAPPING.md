# Jotform to Tallyfy Object Mapping

## Core Object Mappings

### Organizational Structure

| Jotform Object | Tallyfy Object | Notes |
|---------------|----------------|-------|
| Account | Organization | Top-level container |
| Form | Blueprint | Each form becomes a process template |
| Submission | Process Instance | Form submissions become process runs |
| User | Member | Account owners and collaborators |
| Team | Group | Team workspace members |

### Form/Process Structure

| Jotform Object | Tallyfy Object | Transformation Logic |
|---------------|----------------|----------------------|
| Form Fields | Kick-off Form Fields | Initial data collection |
| Page Break | Process Phase | Multi-page forms become phases |
| Section Collapse | Field Group | Logical grouping of fields |
| Submit Actions | Process Triggers | Post-submission workflows |
| Thank You Page | Completion Step | Final confirmation |

## Field Type Mappings

### Basic Input Fields

| Jotform Field | Tallyfy Field | Conversion Notes |
|--------------|---------------|------------------|
| Short Text | Short Text | Direct mapping |
| Long Text | Long Text | Direct mapping |
| Email | Email | With validation |
| Phone | Phone | Format preserved |
| Number | Number | With min/max |
| Website URL | URL | URL validation |
| Date Picker | Date | Direct mapping |
| Time | Time | Time selection |
| Dropdown | Dropdown | Options preserved |
| Radio Button | Radio Select | Single choice |
| Checkbox | Multi-select | Multiple choices |
| Yes/No | Yes/No | Boolean field |

### Advanced Fields

| Jotform Field | Tallyfy Field | Implementation Strategy |
|--------------|---------------|------------------------|
| File Upload | File Attachment | Max size limits apply |
| Image Upload | Image Field | Visual content |
| Signature | Signature | E-signature field |
| Matrix/Scale | Rating Grid | Convert to multiple ratings |
| Slider | Number Range | Visual to numeric |
| Star Rating | Rating | 1-5 star scale |
| Address | Address Fields | Component breakdown |
| Geolocation | Location | GPS coordinates |
| Payment Fields | Custom Fields | Store payment reference |
| Appointment | Calendar Select | Date/time booking |

### Calculation & Logic Fields

| Jotform Feature | Tallyfy Implementation | Notes |
|----------------|------------------------|-------|
| Calculation Widget | Calculated Field | Convert to static or instruction |
| Form Calculation | Process Logic | Step-based calculation |
| Update/Calculate Field | Field Rules | Conditional updates |
| Conditional Logic | Step Conditions | If/then branching |
| Skip Logic | Conditional Steps | Dynamic flow |

## Widgets to Features Mapping

### Popular Widgets

| Jotform Widget | Tallyfy Equivalent | Migration Method |
|---------------|-------------------|------------------|
| Configurable List | Table Field | Multi-row data entry |
| Google Maps | Location Field | Address with map |
| Image Picker | Image Selection | Visual options |
| PDF Embedder | Document Reference | Link to PDF |
| Terms & Conditions | Agreement Field | Acceptance checkbox |
| CAPTCHA | Verification | Security step |
| Social Media | Profile Links | URL fields |
| QR Code Scanner | Text Input | Manual code entry |
| E-Signature | Signature Field | Digital signature |
| Before/After Slider | Image Comparison | Two image fields |

## Conditional Logic Transformation

### Jotform Conditions to Tallyfy Rules

| Condition Type | Tallyfy Implementation | Example |
|---------------|------------------------|---------|
| Show/Hide Field | Conditional Display | Show field if condition met |
| Skip to Page | Step Branching | Jump to specific step |
| Change Email | Dynamic Assignment | Conditional recipient |
| Change Thank You | Dynamic Completion | Different end messages |
| Require Field | Dynamic Validation | Conditional requirements |
| Calculate Field | Field Calculation | Auto-compute values |
| Enable/Disable | Field State | Lock/unlock fields |
| Update Field | Auto-populate | Set field values |

## Integration Mappings

### Native Integrations

| Jotform Integration | Tallyfy Alternative | Migration Strategy |
|-------------------|-------------------|-------------------|
| Google Sheets | Export/Webhook | API connection |
| Dropbox | File Storage | Reference links |
| Slack | Notifications | Webhook setup |
| Mailchimp | Email Integration | API connection |
| Salesforce | CRM Integration | Field mapping |
| Zapier | Zapier | Maintain connection |
| Webhooks | Webhooks | Direct transfer |
| Email | Email Notifications | SMTP setup |

## Paradigm Shifts

### 1. Form-Centric → Process-Centric
**Jotform**: Static forms with submissions
**Tallyfy**: Dynamic processes with steps
**Transformation**: Each form becomes a multi-step process

### 2. Single Submission → Ongoing Process
**Jotform**: One-time data collection
**Tallyfy**: Multi-stage workflow
**Transformation**: Form submission initiates process

### 3. Page Breaks → Sequential Steps
**Jotform**: Multi-page forms
**Tallyfy**: Step-by-step progression
**Transformation**: Each page becomes process phase

### 4. Conditional Logic → Process Branching
**Jotform**: Show/hide fields dynamically
**Tallyfy**: Conditional step execution
**Transformation**: Logic becomes workflow rules

### 5. Payment Collection → Process Integration
**Jotform**: Built-in payment processing
**Tallyfy**: External payment step
**Transformation**: Payment as approval gate

## Data Preservation Strategy

### High Priority (Must Preserve)
- Form structure and fields
- All submissions data
- Field validations
- Conditional logic rules
- File uploads (as references)
- Integration configurations
- User responses
- Calculation formulas

### Medium Priority (Preserve if Possible)
- Form themes and styling
- Widget configurations
- Autoresponder messages
- Submission limits
- Form analytics
- Partial submissions
- Prefill data
- Revision history

### Low Priority (Document Only)
- Visual design elements
- CSS customizations
- Form themes
- Thank you page design
- Email templates design
- Form URL slug
- Embed options
- Social media sharing

## Migration Complexity Levels

### Simple Form (1-2 hours)
- <20 fields
- Basic field types
- No conditional logic
- Single page
- Standard validations

### Medium Form (2-4 hours)
- 20-50 fields
- Multiple pages
- Basic conditions
- File uploads
- Some calculations
- Email notifications

### Complex Form (4-8 hours)
- 50+ fields
- Complex conditional logic
- Multiple integrations
- Payment processing
- Advanced calculations
- Widgets and apps
- Approval workflows

### Enterprise Form (8+ hours)
- 100+ fields
- Nested conditions
- Multiple workflows
- API integrations
- Custom widgets
- Complex calculations
- Multi-language support
- HIPAA compliance

## Special Handling Requirements

### 1. Payment Forms
- Document payment gateway
- Create payment approval step
- Store transaction references
- Handle refund workflows

### 2. Multi-Language Forms
- Preserve all translations
- Create language variants
- Map field translations
- Maintain language logic

### 3. Approval Workflows
- Map approval stages
- Define approver roles
- Set approval conditions
- Configure notifications

### 4. File Upload Handling
- Files <10MB: Direct upload
- Files >10MB: Cloud storage link
- Multiple files: Batch handling
- File type restrictions

### 5. Calculation Fields
```
Jotform: {field1} + {field2} * 0.1
Tallyfy: Create calculation step with formula documentation
```

### 6. Appointment Scheduling
- Convert to calendar field
- Map available slots
- Handle timezone conversion
- Booking confirmations

## Form Elements Transformation

### Headers & Text
| Jotform Element | Tallyfy Implementation | Purpose |
|----------------|------------------------|---------|
| Header | Section Title | Visual separation |
| Sub-header | Field Group Label | Subsection marking |
| Text | Instruction Text | Guidance content |
| Paragraph | Help Text | Detailed instructions |
| Divider | Visual Separator | Section break |

### Layout Elements
| Jotform Layout | Tallyfy Approach | Notes |
|---------------|------------------|-------|
| Columns | Field Order | Sequential display |
| Form Collapse | Collapsible Section | Grouped fields |
| Page Break | New Step | Process progression |
| Section | Field Group | Logical grouping |

## Submission Handling

### Submission Data Migration

| Jotform Submission | Tallyfy Process | Preservation Method |
|-------------------|-----------------|-------------------|
| Submission ID | Process ID | Unique identifier |
| Submit Date | Started Date | Timestamp preserved |
| IP Address | Metadata | Audit trail |
| Browser Info | Metadata | Technical details |
| Response Data | Form Data | Field values |
| Edit Link | Process Link | Access reference |
| PDF Download | Export | Document generation |

## Validation Rules

### Field Validation Mapping

| Jotform Validation | Tallyfy Validation | Implementation |
|-------------------|-------------------|----------------|
| Required | Required | Mandatory field |
| Email Format | Email Type | Built-in validation |
| Numeric Range | Min/Max | Number constraints |
| Text Length | Character Limit | Length validation |
| Regex Pattern | Pattern Match | Custom validation |
| Unique | Unique Value | Duplicate check |
| Date Range | Date Constraints | Valid date range |

## Recommended Migration Sequence

1. **Analysis Phase**
   - Catalog all forms
   - Document conditional logic
   - Map integrations
   - Identify payment forms

2. **User Migration**
   - Export account users
   - Create Tallyfy accounts
   - Map permissions
   - Set up teams

3. **Form Structure**
   - Create blueprints
   - Map form fields
   - Configure validations
   - Set up conditions

4. **Logic Transfer**
   - Implement conditions
   - Create calculations
   - Set up branching
   - Configure notifications

5. **Data Migration**
   - Export submissions
   - Transform data format
   - Import into Tallyfy
   - Verify data integrity

6. **Integration Setup**
   - Configure webhooks
   - Set up API connections
   - Test integrations
   - Validate workflows

7. **Testing Phase**
   - Test form submission
   - Verify calculations
   - Check conditions
   - Validate integrations

## Known Limitations

### Cannot Migrate
- Form themes and CSS
- Custom HTML/JavaScript
- Advanced widgets UI
- Form analytics history
- A/B testing data
- Submission graphs
- Form performance metrics

### Requires Manual Setup
- Payment gateway configuration
- Complex calculation formulas
- Custom widget functionality
- Advanced API integrations
- HIPAA compliance settings
- White-label branding
- Custom domains

## Migration Validation Checklist

- [ ] All forms cataloged and mapped
- [ ] Field types correctly converted
- [ ] Conditional logic preserved
- [ ] Calculations documented
- [ ] File uploads accessible
- [ ] Integrations configured
- [ ] Submissions migrated
- [ ] Validations functional
- [ ] Notifications set up
- [ ] Payment flows documented
- [ ] Multi-page forms structured
- [ ] Approval workflows created
- [ ] User permissions mapped
- [ ] Test submissions successful
- [ ] Data integrity verified

## Post-Migration Considerations

### Training Requirements
- Form builders → Process designers
- Conditional logic → Workflow rules
- Submissions → Process instances
- Analytics → Process metrics

### Process Optimization
- Simplify complex conditions
- Consolidate similar forms
- Standardize field naming
- Optimize approval flows
- Implement best practices

### Documentation Needs
- Field mapping guide
- Condition transformation rules
- Integration setup instructions
- User training materials
- Admin configuration guide