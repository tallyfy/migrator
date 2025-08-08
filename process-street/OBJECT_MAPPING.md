# Process Street to Tallyfy Object Mapping Guide

## Terminology Translation

This guide provides detailed mapping between Process Street and Tallyfy concepts, helping users understand how their data transforms during migration.

## Core Object Mappings

### Organizations
| Process Street | Tallyfy | Notes |
|---------------|---------|-------|
| Organization | Organization | Direct mapping |
| Workspace | Organization | Tallyfy uses flat structure |
| Folders | Tags/Categories | Organizational method differs |

### Template Objects
| Process Street | Tallyfy | API Name | Notes |
|---------------|---------|----------|-------|
| **Workflow** | **Blueprint/Template** | `blueprint` | Master process definition |
| Task Template | Step | `step` | Individual work items in template |
| Form Field | Form Field | `capture` | Data collection elements |
| Stop Task | Approval Task | `task` with type | Decision point in workflow |
| Task Group | Step Group | N/A | Logical grouping of steps |
| Conditional Logic | Rules/Conditions | `rule` | IF-THEN workflow logic |
| Role | Group | `group` | User collection for assignments |

### Instance Objects
| Process Street | Tallyfy | API Name | Notes |
|---------------|---------|----------|-------|
| **Checklist/Run** | **Process** | `run` | Running instance of template |
| Task Instance | Task | `task` | Actual work item in process |
| Task Status | Task Status | `status` | Completion state |
| Form Response | Field Value | `field_value` | Captured data |
| Assignee | Assignee | `assignee` | User assigned to task |

### User & Permission Objects
| Process Street | Tallyfy | Notes |
|---------------|---------|-------|
| Admin | Administrator | Full organization control |
| Member | Standard Member | Can create and edit templates |
| Guest | Guest | External collaborator |
| Read-only User | Light Member | Limited to task completion |
| Group | Group | Collection of users |
| Team | Organization | Separate Tallyfy organization |

### Field Type Mappings
| Process Street Field | Tallyfy Capture Type | Data Transformation |
|---------------------|---------------------|-------------------|
| Text | Short Text | Direct mapping |
| Long Text | Long Text | Direct mapping |
| Email | Short Text + Validation | Add email validation |
| URL | Short Text + Validation | Add URL validation |
| Number | Number | Direct mapping |
| Date | Date | Direct mapping |
| Date & Time | Date | Time component may be lost |
| Dropdown | Dropdown | Options preserved |
| Multiple Choice | Checklist | Convert to multi-select |
| Checkbox | Radio Buttons | Yes/No selection |
| File Upload | File Upload | Max 100MB per file |
| Member Select | Assignee Picker | User selection |
| Formula | Short Text | Store as static value |
| Email Field | Short Text | With email validation |

### Workflow Elements
| Process Street | Tallyfy | Implementation |
|---------------|---------|---------------|
| Sequential Tasks | Sequential Steps | Default behavior |
| Parallel Tasks | Parallel Steps | Configure in template |
| Dependencies | Step Dependencies | Link steps together |
| Due Dates | Deadlines | With notifications |
| Recurring Checklists | Template Scheduling | Use external automation |
| Task Comments | Task Comments | Full thread preserved |
| @Mentions | @Mentions | User notifications |
| Activity Feed | Timeline | Process history |

### Automation Features
| Process Street | Tallyfy | Migration Approach |
|---------------|---------|-------------------|
| Automations | Rules + Webhooks | Combine features |
| Zapier Integration | Zapier Integration | Reconnect after migration |
| API Triggers | Webhooks | Configure webhooks |
| Email Notifications | Email Notifications | Automatic |
| Slack Integration | Slack Integration | Reconfigure |
| Conditional Logic | IF-THEN Rules | Recreate logic |
| Dynamic Due Dates | Static Deadlines | Convert to fixed dates |
| Stop Tasks | Approval Tasks | Different implementation |

## Data Transformation Rules

### 1. Workflow to Blueprint Transformation
```
Process Street Workflow → Tallyfy Blueprint
- Name → Title
- Description → Description  
- Tasks[] → Steps[]
- Form Fields → Kick-off Form
- Settings → Template Settings
- Permissions → Access Control
```

### 2. Checklist to Process Transformation
```
Process Street Checklist → Tallyfy Process
- Name → Process Name
- Status → Process Status
- Created Date → Created At
- Tasks[] → Tasks[]
- Assignees → Participants
- Form Values → Captured Data
```

### 3. User Transformation
```
Process Street User → Tallyfy Member
- Email → Email (unique identifier)
- Name → First Name + Last Name
- Role → Member Type
- Groups → Groups
- Permissions → Template Access
```

## Feature Comparison

### ✅ Fully Supported Migrations
- User accounts and profiles
- Basic workflow structure
- Task assignments
- Comments and activity
- File attachments (< 100MB)
- Basic form fields
- Email notifications
- Webhooks

### ⚠️ Partial Support (Manual Configuration Required)
- Complex conditional logic
- Dynamic due dates (become static)
- Recurring workflows (use scheduling)
- Advanced automations
- Custom integrations
- Role-based routing

### ❌ Not Supported (No Equivalent)
- Data Sets (external storage required)
- Public form embedding
- Some formula fields
- Custom CSS/branding
- Workflow versioning
- Approval chains
- Time tracking
- Advanced analytics

## Migration Strategies

### Simple Workflows (< 10 steps)
- Direct 1:1 mapping
- Minimal data transformation
- Quick migration

### Complex Workflows (> 10 steps with logic)
- Phase-based migration
- Test in sandbox first
- Recreate automations manually
- Validate all paths

### Active Processes
- Complete in Process Street if possible
- Migrate at logical break point
- Run parallel for validation
- Gradual cutover

## Post-Migration Validation

### Required Checks
1. All users can log in ✓
2. Templates appear correctly ✓
3. Active processes migrated ✓
4. Form data preserved ✓
5. Files accessible ✓
6. Notifications working ✓

### Common Adjustments
1. Recreate conditional logic
2. Set up new integrations
3. Configure webhooks
4. Adjust permissions
5. Train users on UI differences

## API Endpoint Mappings

| Operation | Process Street API | Tallyfy API |
|-----------|-------------------|-------------|
| List Templates | `GET /workflows` | `GET /blueprints` |
| Get Template | `GET /workflows/{id}` | `GET /blueprints/{id}` |
| List Processes | `GET /checklists` | `GET /runs` |
| Get Process | `GET /checklists/{id}` | `GET /runs/{id}` |
| List Users | `GET /users` | `GET /members` |
| Create Process | `POST /checklists` | `POST /runs` |
| Update Task | `PUT /tasks/{id}` | `PUT /tasks/{id}` |
| Add Comment | `POST /comments` | `POST /comments` |

## Support Resources

- **Migration Guide**: See README.md
- **API Documentation**: 
  - Process Street: https://public-api.process.st/api/v1.1/docs/
  - Tallyfy: https://api.tallyfy.com/docs
- **Comparison**: https://tallyfy.com/process-street-alternative/
- **Support**: Free 1:1 support included with Tallyfy