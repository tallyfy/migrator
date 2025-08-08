# Pipefy to Tallyfy Object Mapping Guide

## Terminology Translation

This guide provides comprehensive mapping between Pipefy and Tallyfy concepts, helping users understand the fundamental paradigm shift from Kanban-based to Sequential Process workflows.

## Core Object Mappings

### Organizations
| Pipefy | Tallyfy | Notes |
|--------|---------|-------|
| Organization | Organization | Direct mapping |
| Company | Organization | Tallyfy uses flat structure |
| Teams | Groups | User collections |

### Template Objects
| Pipefy | Tallyfy | API Name | Notes |
|--------|---------|----------|-------|
| **Pipe** | **Blueprint/Template** | `blueprint` | Kanban board → Sequential process |
| Phase | Step Group | N/A | Each phase becomes 3 steps |
| Card Template | Kick-off Form | `prerun` | Initial data collection |
| Field (in phase) | Form Field | `capture` | Data collection elements |
| Automation | Rules/Webhooks | `rule` | Workflow automation |
| Label | Tag | `tag` | Organizational metadata |
| Connection | Integration | N/A | External system links |

### Instance Objects
| Pipefy | Tallyfy | API Name | Notes |
|--------|---------|----------|-------|
| **Card** | **Process** | `run` | Single work item instance |
| Card in Phase | Task | `task` | Work item at specific stage |
| Field Value | Field Value | `field_value` | Captured data |
| Card Movement | Task Completion | `status` | Progress tracking |
| Assignee | Assignee | `assignee` | User assignment |
| Comment | Comment | `comment` | Discussion thread |

### User & Permission Objects
| Pipefy | Tallyfy | Notes |
|--------|---------|-------|
| Admin | Administrator | Full control |
| Member | Standard Member | Create and edit access |
| Guest | Guest | External collaborator |
| Normal User | Light Member | Task completion only |
| Pipe Admin | Template Owner | Template-specific control |

## Paradigm Shift: Kanban to Sequential

### The Fundamental Difference

**Pipefy**: Cards move through phases on a Kanban board
**Tallyfy**: Tasks complete in sequence within a process

This isn't just a terminology change - it's a complete shift in how work flows:

| Pipefy Concept | Tallyfy Implementation | Impact |
|----------------|------------------------|--------|
| Card moves between phases | Tasks complete in order | Linear progression |
| Multiple cards in a phase | Sequential task execution | No parallel cards |
| Visual board view | Timeline/checklist view | Different visualization |
| Drag-and-drop movement | Click to complete | Different interaction |
| Phase-based SLAs | Task deadlines | Granular timing |

### Phase to Step Transformation

Each Pipefy phase becomes THREE Tallyfy steps:

```
Pipefy Phase: "Review Documents"
↓
Tallyfy Steps:
1. "Review Documents - Entry" (Notification step)
2. "Review Documents - Work" (Actual task)
3. "Review Documents - Exit" (Completion check)
```

## Field Type Mappings

| Pipefy Field | Tallyfy Capture Type | Data Transformation |
|--------------|---------------------|-------------------|
| Short Text | Short Text | Direct mapping |
| Long Text | Long Text | Direct mapping |
| Number | Number | Direct mapping |
| Date | Date | Direct mapping |
| DateTime | Date | Time may be lost |
| Dropdown Select | Dropdown | Options preserved |
| Radio Select | Radio Buttons | Direct mapping |
| Checkbox Select | Checklist | Multi-select |
| Email | Short Text + Validation | Add validation |
| Phone | Short Text + Validation | Format validation |
| Currency | Number | Remove currency symbol |
| Assignee Select | Assignee Picker | User selection |
| Label Select | Tags | Metadata |
| Connection Field | Short Text | Store reference |
| Statement | Long Text (readonly) | Instructional text |
| Time | Short Text | Store as HH:MM |
| CNPJ/CPF | Short Text + Validation | Brazilian ID validation |

## Workflow Elements

| Pipefy | Tallyfy | Implementation |
|--------|---------|---------------|
| Phase Sequence | Step Order | Linear progression |
| Card Movement | Task Completion | Status change |
| SLA per Phase | Task Deadlines | Individual timing |
| Conditionals | IF-THEN Rules | Logic recreation |
| Automations | Webhooks + Rules | Combined approach |
| Email Templates | Email Tasks | Rebuilt templates |
| Recurrence | External Scheduling | Use automation tools |
| Public Forms | Kick-off Forms | Limited public access |

## Database Tables (Critical Limitation)

### ⚠️ No Direct Equivalent in Tallyfy

Pipefy's database tables have NO direct equivalent in Tallyfy. Migration strategy:

1. **Export to PostgreSQL**: Tables migrated to external database
2. **API Wrapper**: Build custom API for table access
3. **Integration**: Connect via webhooks/API calls
4. **Data Loss Risk**: Complex table relationships may break

| Pipefy Database Feature | Workaround | Complexity |
|------------------------|------------|------------|
| Table Records | PostgreSQL + API | High |
| Table Relationships | Foreign Keys in DB | High |
| Table Fields | Database Columns | Medium |
| Table Connections | API Integration | Very High |
| Record Cards | Separate Processes | Medium |

## Automation Features

| Pipefy | Tallyfy | Migration Approach |
|--------|---------|-------------------|
| Move Card Automation | Complete Task Rule | Different trigger |
| Create Card Automation | Launch Process | Via webhook |
| Update Field Automation | Update Field Rule | Recreate logic |
| Send Email Automation | Email Task | Manual rebuild |
| Conditionals | IF-THEN Rules | Complex recreation |
| SLA Automation | Deadline Notifications | Built-in feature |
| Alert Automation | Notifications | Configure new |
| Integration Automation | Webhooks | Reconnect services |

## Feature Comparison

### ✅ Fully Supported Migrations
- User accounts and profiles
- Basic pipe structure (as sequential process)
- Field data and values
- Comments and activity
- File attachments (< 100MB)
- Basic automations
- Email notifications

### ⚠️ Partial Support (Manual Work Required)
- Phase-based workflows (paradigm shift)
- Complex conditionals (rebuild required)
- Database connections (external solution)
- Public forms (limited in Tallyfy)
- Recurrence patterns (external automation)
- Multi-language support

### ❌ Not Supported (No Equivalent)
- Database tables (requires PostgreSQL)
- Kanban board visualization
- Card cloning with updates
- Phase-specific forms
- Database record cards
- Complex table relationships
- Public portal features
- Start form conditions
- Advanced reporting dashboards

## Migration Strategies

### Simple Pipes (< 5 phases, no databases)
- Direct transformation possible
- 2-4 hours per pipe
- Minimal data loss

### Complex Pipes (> 5 phases with conditionals)
- Phased migration approach
- Test extensively in sandbox
- 1-2 days per pipe
- Some feature recreation needed

### Database-Heavy Pipes
- **Critical Planning Required**
- Set up PostgreSQL first
- Build API wrapper
- Test data integrity
- 3-5 days per pipe
- Significant technical work

### Active Cards Migration
- Complete urgent cards in Pipefy first
- Migrate at phase boundaries
- Run parallel for validation
- Gradual cutover recommended

## Post-Migration Validation

### Required Checks
1. All users can access ✓
2. Process flow matches intent ✓
3. Data fields preserved ✓
4. Automations recreated ✓
5. Database connections work ✓
6. Files accessible ✓

### Common Adjustments
1. Retrain users on sequential flow
2. Rebuild complex automations
3. Set up database API endpoints
4. Configure new integrations
5. Adjust deadline strategies
6. Create new reports

## GraphQL to REST API Mapping

| Operation | Pipefy GraphQL | Tallyfy REST |
|-----------|---------------|--------------|
| List Templates | `query { pipes }` | `GET /blueprints` |
| Get Template | `query { pipe(id) }` | `GET /blueprints/{id}` |
| List Cards | `query { cards }` | `GET /runs` |
| Get Card | `query { card(id) }` | `GET /runs/{id}` |
| Create Card | `mutation { createCard }` | `POST /runs` |
| Update Card | `mutation { updateCard }` | `PUT /runs/{id}` |
| Move Card | `mutation { moveCard }` | `PUT /tasks/{id}` |

## Critical Migration Warnings

### 🚨 Paradigm Shift Impact
Users MUST understand that Pipefy's Kanban model fundamentally differs from Tallyfy's sequential process model. This isn't just a UI change - it changes how work flows through the system.

### 🚨 Database Tables
If your Pipefy implementation heavily uses database tables:
1. Migration complexity increases 10x
2. Requires technical database expertise
3. May need custom development
4. Consider if migration is worth the effort

### 🚨 Training Required
Users accustomed to dragging cards between phases will need significant retraining for Tallyfy's task-completion model.

## Support Resources

- **Migration Guide**: See README.md
- **API Documentation**: 
  - Pipefy: https://developers.pipefy.com/
  - Tallyfy: https://api.tallyfy.com/docs
- **Comparison**: https://tallyfy.com/pipefy-alternative/
- **Support**: Free migration assistance included with Tallyfy Enterprise