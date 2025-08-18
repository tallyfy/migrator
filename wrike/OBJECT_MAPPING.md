# Wrike to Tallyfy Object Mapping

## Core Object Mappings

### Organizational Structure

| Wrike Object | Tallyfy Object | Notes |
|-------------|----------------|-------|
| Account | Organization | Top-level container |
| Space | Blueprint Category/Tag | Logical grouping of projects |
| User | Member | User accounts with roles |
| User Group | Group | Team groupings |
| Access Role | Role | Permission sets |

### Project/Process Structure

| Wrike Object | Tallyfy Object | Transformation Logic |
|-------------|----------------|----------------------|
| Folder | Blueprint Category | Top-level folders become categories |
| Project | Blueprint | Projects become process templates |
| Task | Task/Step | Individual work items |
| Subtask | Sub-step/Checklist | Nested items within tasks |
| Milestone | Approval Step | Key checkpoints requiring sign-off |

### Workflow Elements

| Wrike Object | Tallyfy Object | Mapping Strategy |
|-------------|----------------|------------------|
| Workflow | Status Progression | Custom statuses map to step states |
| Custom Status | Step Status | Map to closest Tallyfy status |
| Approval | Approval Step | Explicit approval requirements |
| Dependency | Step Dependency | Sequential/parallel relationships |
| Recurrence | Process Schedule | Recurring task patterns |

### Fields and Data

| Wrike Field Type | Tallyfy Field Type | Conversion Notes |
|-----------------|-------------------|------------------|
| Text | Short Text | Direct mapping |
| Paragraph | Long Text | Direct mapping |
| DropDown | Dropdown | Options preserved |
| Checkbox | Yes/No or Multi-select | Based on single/multiple |
| Date | Date | Direct mapping |
| Duration | Number + metadata | Store as number with unit |
| Money | Number | Currency in metadata |
| Percentage | Number | Store as 0-100 |
| Formula | Calculated/Read-only | Convert to static or instruction |
| Contact | Member Select | Map to user reference |

### Custom Item Types

| Wrike Custom Type | Tallyfy Approach | Implementation |
|------------------|------------------|----------------|
| Bug | Bug Tracking Blueprint | Specialized template with bug fields |
| Campaign | Campaign Blueprint | Marketing process template |
| Candidate | Recruitment Blueprint | HR process template |
| Custom Type | Tagged Blueprint | Use tags/metadata for type |

### Advanced Features

| Wrike Feature | Tallyfy Equivalent | Migration Strategy |
|--------------|-------------------|-------------------|
| Request Forms | Kick-off Form | Form fields become kick-off fields |
| Blueprints | Blueprint Template | Direct template mapping |
| Calendar View | Process Schedule | Due dates and timelines |
| Gantt Chart | Process Timeline | Linear representation |
| Workload View | Assignment Dashboard | User task assignments |
| Table View | Process List | Standard list view |
| Custom Fields | Form Fields | Map by type with fallbacks |
| Time Tracking | Time Metadata | Store as custom field |
| Billable Hours | Cost Tracking | Custom field with calculations |

### Comments and Activity

| Wrike Activity | Tallyfy Activity | Preservation Method |
|---------------|------------------|-------------------|
| Comment | Comment | Direct migration |
| @Mention | @Mention | Preserve user references |
| Status Change | Activity Log | Record in process history |
| Assignment | Assignment | Map user assignments |
| Attachment | File Attachment | File references or links |

### Notifications and Automation

| Wrike Automation | Tallyfy Automation | Configuration |
|-----------------|-------------------|--------------|
| Auto-assignment | Auto-assignment Rules | Rule-based assignment |
| Status Triggers | Process Rules | Conditional logic |
| Due Date Rules | Timeline Rules | Automatic scheduling |
| Notification Rules | Notification Settings | User preferences |
| Approval Routing | Approval Logic | Sequential/parallel approvals |

## Paradigm Shifts

### 1. Enterprise Hierarchy → Flat Process Structure
**Wrike**: Deep folder hierarchies with spaces > folders > projects > tasks
**Tallyfy**: Flatter structure with categories and tags
**Transformation**: Flatten deep hierarchies, use tags for organization

### 2. Custom Item Types → Process Templates
**Wrike**: Business-specific item types (Bug, Campaign, etc.)
**Tallyfy**: Process templates with appropriate fields
**Transformation**: Create specialized blueprints for each custom type

### 3. Complex Formulas → Instructions/Static Values
**Wrike**: Dynamic formula fields with calculations
**Tallyfy**: Static fields or manual calculation steps
**Transformation**: Convert formulas to either:
- One-time calculated values
- Step instructions for manual calculation
- External integration for dynamic values

### 4. Request Forms → Kick-off Forms
**Wrike**: Separate request forms for work intake
**Tallyfy**: Integrated kick-off forms
**Transformation**: Merge request form fields into process kick-off

### 5. Multiple Views → Single Process View
**Wrike**: Table, Board, Gantt, Calendar, Stream views
**Tallyfy**: Process-centric view
**Transformation**: Focus on process flow, preserve data not views

## Data Preservation Strategy

### High Priority (Must Preserve)
- User accounts and permissions
- Project/folder structure (as categories)
- Task content and descriptions
- Custom field data
- Comments and activity history
- File attachments (as references)
- Approval workflows

### Medium Priority (Preserve if Possible)
- Custom statuses
- Time tracking data
- Dependencies between tasks
- Recurring patterns
- Dashboard configurations
- Report templates

### Low Priority (Document but Don't Migrate)
- View preferences
- Personal settings
- Gantt chart positions
- Calendar color coding
- Workload calculations
- Advanced formula logic

## Migration Complexity Factors

### Simple Migration (1-2 hours per project)
- Standard projects with basic tasks
- Default workflows
- No custom fields
- <50 tasks

### Moderate Migration (2-4 hours per project)
- Custom workflows
- 5-10 custom fields
- Request forms
- 50-200 tasks
- Some dependencies

### Complex Migration (4-8 hours per project)
- Custom item types
- Complex formulas
- Multiple workflows
- Heavy automation
- 200+ tasks
- Cross-project dependencies

## Field Mapping Matrix

### Standard Fields
| Wrike Field | Tallyfy Field | Default Value | Validation |
|------------|---------------|---------------|------------|
| Title | Name | Required | Max 255 chars |
| Description | Description | Optional | Rich text |
| Status | Status | To Do | Enum values |
| Assignee | Assignee | Unassigned | Valid user |
| Due Date | Due Date | None | Future date |
| Priority | Priority | Medium | High/Medium/Low |
| Created Date | Created At | Auto | Read-only |
| Updated Date | Updated At | Auto | Read-only |

### Custom Field Mappings
| Wrike Custom Field | Detection Method | Tallyfy Type | Fallback |
|-------------------|------------------|--------------|----------|
| Email Field | Regex validation | Email | Short Text |
| URL Field | URL validation | URL | Short Text |
| Phone Field | Format pattern | Phone | Short Text |
| Score Field | Numeric range | Rating | Number |
| Multi-select | Multiple values | Multi-select | Checkboxes |

## Special Handling Requirements

### 1. Formula Fields
- Extract formula logic
- Calculate current value
- Store as static with formula in description
- Flag for manual review

### 2. Cross-Project Dependencies
- Document dependency
- Create reference in description
- Consider combining projects

### 3. Time Zone Handling
- Preserve original timezone
- Convert to Tallyfy timezone
- Note differences in metadata

### 4. File Attachments
- Under 10MB: Direct upload
- Over 10MB: Create reference link
- Cloud files: Preserve link

### 5. Approval Chains
- Sequential: Create approval steps
- Parallel: Create parallel branches
- Conditional: Add rule logic

## Validation Checklist

Post-migration validation points:

- [ ] All users successfully created/mapped
- [ ] Folder structure preserved as categories
- [ ] All projects converted to blueprints
- [ ] Custom fields data preserved
- [ ] Comments migrated with timestamps
- [ ] Approval workflows functional
- [ ] Dependencies documented
- [ ] Formula calculations documented
- [ ] File references accessible
- [ ] Permissions correctly mapped

## Known Limitations

### Cannot Migrate
- Gantt chart visual positions
- Personal view preferences
- Real-time collaboration cursors
- Version history details
- Detailed time logs
- Budget tracking
- Resource management views

### Requires Manual Setup
- Complex automation rules
- Cross-workspace dependencies
- Advanced permission schemes
- Custom integrations
- Webhook configurations
- API extensions

## Recommended Migration Sequence

1. **Preparation Phase**
   - Audit current Wrike usage
   - Identify custom item types
   - Document formulas and automation
   - Clean up unused items

2. **User Migration**
   - Export all users
   - Create in Tallyfy
   - Map permissions

3. **Structure Migration**
   - Create categories from spaces/folders
   - Establish blueprint templates
   - Configure custom fields

4. **Content Migration**
   - Migrate projects as blueprints
   - Transfer task content
   - Preserve comments

5. **Validation Phase**
   - Verify data integrity
   - Test workflows
   - Validate permissions
   - Check automations

6. **Training & Adoption**
   - Document paradigm shifts
   - Train on new workflows
   - Provide migration guide