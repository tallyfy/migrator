# NextMatter to Tallyfy Object Mapping

## Core Object Mappings

### Organizational Structure

| NextMatter Object | Tallyfy Object | Notes |
|------------------|----------------|-------|
| Organization | Organization | Company account |
| Workflow | Blueprint | Process template |
| Instance | Process Instance | Running workflow |
| User | Member | User accounts |
| Team | Group | User groupings |
| Role | Role | Permission sets |

### Workflow/Process Structure

| NextMatter Object | Tallyfy Object | Transformation Logic |
|------------------|----------------|----------------------|
| Workflow | Blueprint | Process definition |
| Step | Task/Step | Individual activities |
| Form | Kick-off Form | Data collection |
| Gate | Approval Step | Decision point |
| Integration Step | Integration Task | External system call |
| Parallel Steps | Parallel Tasks | Simultaneous execution |
| Conditional Step | Conditional Task | Logic-based execution |

## Step Type Mappings

### Core Step Types

| NextMatter Step Type | Tallyfy Step Type | Implementation |
|---------------------|-------------------|----------------|
| Task | Task | Manual activity |
| Form | Form Step | Data input |
| Approval | Approval | Decision gate |
| Integration | Integration Task | API call |
| Email | Notification | Email send |
| Wait | Timer Step | Delay execution |
| Split | Parallel Branch | Fork workflow |
| Join | Merge Point | Synchronize branches |
| Decision | Conditional Branch | If/then logic |

### Advanced Step Features

| NextMatter Feature | Tallyfy Implementation | Strategy |
|-------------------|------------------------|----------|
| Step Instructions | Task Description | Rich text content |
| Step Forms | Form Fields | Data collection |
| Step Attachments | File Attachments | Document upload |
| Step Comments | Task Comments | Discussion thread |
| Step Timeline | Task Duration | Time tracking |
| Step Dependencies | Step Prerequisites | Execution order |
| Step Escalation | Escalation Rules | Timeout actions |

## Form Field Mappings

### Field Types

| NextMatter Field | Tallyfy Field | Conversion |
|-----------------|---------------|------------|
| Text | Short Text | Direct |
| Long Text | Long Text | Direct |
| Number | Number | Direct |
| Date | Date | Direct |
| Time | Time | Direct |
| DateTime | DateTime | Combined |
| Dropdown | Dropdown | Options preserved |
| Radio | Radio Select | Single choice |
| Checkbox | Multi-select | Multiple choices |
| File Upload | File Attachment | Document upload |
| User Select | Member Select | User picker |
| Email | Email | Validated |
| URL | URL | Link field |
| Money | Currency | Number with format |

### Dynamic Fields

| Dynamic Feature | Tallyfy Approach | Implementation |
|----------------|------------------|----------------|
| Calculated Fields | Formula Fields | Computation rules |
| Lookup Fields | Reference Fields | Data retrieval |
| Dependent Fields | Conditional Fields | Show/hide logic |
| Validation Rules | Field Validation | Input constraints |
| Default Values | Pre-filled Fields | Initial values |
| Required Logic | Dynamic Required | Conditional mandatory |

## Integration Capabilities

### Native Integrations

| NextMatter Integration | Tallyfy Alternative | Migration Path |
|-----------------------|-------------------|----------------|
| Slack | Slack Webhook | Reconfigure |
| Microsoft Teams | Teams Integration | Setup new |
| Jira | API Integration | Webhook/API |
| Salesforce | CRM Connect | API mapping |
| SAP | Enterprise Integration | Custom API |
| Email | SMTP/Email | Direct support |
| Webhooks | Webhooks | URL update |
| REST API | API Tasks | Endpoint config |

### Integration Patterns

| Integration Type | Implementation | Configuration |
|-----------------|----------------|---------------|
| Data Push | Outbound Webhook | POST request |
| Data Pull | API Call | GET request |
| Synchronization | Two-way Sync | Bidirectional |
| Notification | Alert System | Event trigger |
| Document Generation | Template Merge | Dynamic creation |
| System Update | PATCH/PUT | Update records |

## Workflow Logic

### Conditional Logic

| NextMatter Condition | Tallyfy Rule | Transformation |
|---------------------|--------------|----------------|
| If/Then | Conditional Step | Branch logic |
| Switch/Case | Multi-branch | Multiple paths |
| Loop | Recurring Task | Iteration logic |
| Wait Until | Wait Condition | Pause until met |
| Skip | Bypass Step | Conditional skip |
| Abort | Cancel Process | Termination |

### Parallel Processing

| Parallel Feature | Tallyfy Implementation | Method |
|-----------------|------------------------|--------|
| Split Gateway | Parallel Start | Fork point |
| Join Gateway | Parallel End | Merge point |
| AND Split | All Branches | Execute all |
| OR Split | Any Branch | Execute one |
| Complex Gateway | Custom Logic | Rule-based |

## Paradigm Shifts

### 1. Workflow Engine → Process Platform
**NextMatter**: Technical workflow engine
**Tallyfy**: Business process platform
**Transformation**: Technical steps to business tasks

### 2. Integration-Heavy → Human-Centric
**NextMatter**: Deep system integrations
**Tallyfy**: Human tasks with integrations
**Transformation**: Balance automation with visibility

### 3. Complex Gateways → Simple Branching
**NextMatter**: BPMN-style gateways
**Tallyfy**: Intuitive conditions
**Transformation**: Simplify complex logic

### 4. Instance Variables → Process Data
**NextMatter**: Workflow variables
**Tallyfy**: Form fields and data
**Transformation**: Variables become fields

### 5. Technical Forms → User Forms
**NextMatter**: Data collection forms
**Tallyfy**: User-friendly forms
**Transformation**: Enhance UX

## Data & Variables

### Variable Mapping

| NextMatter Variable | Tallyfy Data | Storage |
|--------------------|--------------|---------|
| Workflow Variable | Process Field | Form data |
| Step Variable | Step Field | Local data |
| Global Variable | Shared Field | Cross-step |
| System Variable | Metadata | Read-only |
| User Variable | User Context | Assignment |
| Calculated Variable | Computed Field | Formula |

### Data Types

| NextMatter Type | Tallyfy Type | Conversion |
|----------------|--------------|------------|
| String | Text | Direct |
| Integer | Number | Whole numbers |
| Decimal | Number | Decimals |
| Boolean | Yes/No | True/false |
| Date | Date | Date only |
| Timestamp | DateTime | Date + time |
| Object | JSON | Structured data |
| Array | Table | Multiple rows |

## Roles & Permissions

### Role Mapping

| NextMatter Role | Tallyfy Role | Permissions |
|----------------|--------------|-------------|
| Workflow Owner | Process Owner | Full control |
| Participant | Process Member | Execute tasks |
| Viewer | Guest User | Read-only |
| Admin | Administrator | System admin |
| Manager | Supervisor | Team oversight |

### Assignment Rules

| Assignment Type | Tallyfy Method | Implementation |
|----------------|----------------|----------------|
| Direct Assignment | User Selection | Specific person |
| Role Assignment | Role-based | Any with role |
| Dynamic Assignment | Rule-based | Conditional |
| Round Robin | Load Balancing | Distribution |
| Escalation | Timeout Reassign | Time-based |

## Monitoring & Analytics

### Performance Metrics

| NextMatter Metric | Tallyfy Metric | Tracking |
|------------------|----------------|----------|
| Cycle Time | Process Duration | Total time |
| Step Duration | Task Time | Step timing |
| Wait Time | Idle Time | Queue time |
| Processing Time | Active Time | Work time |
| SLA Compliance | Due Date Met | On-time rate |
| Throughput | Completion Rate | Volume/time |

## Data Preservation Strategy

### High Priority (Must Preserve)
- Workflow definitions
- All active instances
- Form data and fields
- User assignments
- Integration configurations
- Step logic and conditions
- Comments and attachments
- Approval history

### Medium Priority (Preserve if Possible)
- Historical instances
- Performance metrics
- Audit logs
- Version history
- Template library
- Custom scripts
- Notification templates
- Report configurations

### Low Priority (Document Only)
- UI customizations
- Personal preferences
- Draft workflows
- Test instances
- Deleted items
- System logs
- Debug information

## Migration Complexity Levels

### Simple Workflow (1-2 hours)
- <10 steps
- Linear flow
- Basic forms
- No integrations
- Simple assignments

### Medium Workflow (2-4 hours)
- 10-30 steps
- Some branching
- Multiple forms
- 1-2 integrations
- Role-based assignments

### Complex Workflow (4-8 hours)
- 30+ steps
- Complex branching
- Parallel processing
- Multiple integrations
- Dynamic assignments
- Custom logic

### Enterprise Workflow (8+ hours)
- 50+ steps
- Nested workflows
- Heavy integration
- Complex gateways
- Custom scripts
- Multi-system orchestration

## Special Handling Requirements

### 1. Integration Steps
- Map API endpoints
- Transform payloads
- Handle authentication
- Configure error handling
- Set up retries

### 2. Parallel Gateways
- Identify split type
- Map join conditions
- Handle synchronization
- Manage timeouts
- Document logic

### 3. Complex Forms
- Map all field types
- Preserve validations
- Handle calculations
- Maintain dependencies
- Convert layouts

### 4. Dynamic Assignments
- Document rules
- Map conditions
- Handle escalations
- Configure round-robin
- Set up delegates

### 5. Custom Scripts
- Extract business logic
- Convert to rules
- Document algorithms
- Create alternatives
- Flag for review

## Recommended Migration Sequence

1. **Discovery Phase**
   - Catalog workflows
   - Map integrations
   - Document custom logic
   - Identify active instances

2. **User Setup**
   - Export users
   - Create accounts
   - Map roles
   - Set permissions

3. **Workflow Structure**
   - Create blueprints
   - Map steps
   - Configure branching
   - Set up forms

4. **Integration Configuration**
   - Map endpoints
   - Configure authentication
   - Set up webhooks
   - Test connections

5. **Logic Transfer**
   - Implement conditions
   - Configure assignments
   - Set up escalations
   - Create rules

6. **Instance Migration**
   - Export active instances
   - Transform data
   - Import to Tallyfy
   - Verify state

7. **Testing & Validation**
   - Test workflows
   - Verify integrations
   - Check assignments
   - Validate data

## Known Limitations

### Cannot Migrate
- Custom scripts/code
- Complex BPMN patterns
- Advanced timer events
- Signal/message events
- Compensation handlers
- Transaction boundaries
- Custom UI components

### Requires Manual Setup
- Complex integration logic
- Custom authentication
- Advanced gateways
- Nested sub-processes
- Error compensation
- Custom reports
- API extensions

## Migration Validation Checklist

- [ ] All workflows mapped
- [ ] Steps correctly sequenced
- [ ] Forms fully configured
- [ ] Integrations connected
- [ ] Users and roles mapped
- [ ] Assignments configured
- [ ] Logic implemented
- [ ] Parallel flows handled
- [ ] Data migrated
- [ ] Instances transferred
- [ ] Permissions set
- [ ] Notifications configured
- [ ] Testing completed
- [ ] Performance verified
- [ ] Documentation updated

## Integration Migration Guide

### API Integration Pattern
```
NextMatter:
- Integration Step
- Endpoint: POST /api/v1/create
- Headers: Authorization
- Body: JSON payload

Tallyfy:
- API Task Step
- Webhook configuration
- Authentication setup
- Response handling
```

### Notification Pattern
```
NextMatter:
- Email step
- Template with variables
- Recipient rules

Tallyfy:
- Notification rule
- Email template
- Dynamic recipients
```

### Data Transformation Pattern
```
NextMatter:
- Script step
- Transform logic
- Variable mapping

Tallyfy:
- Calculated fields
- Transformation rules
- Field mapping
```