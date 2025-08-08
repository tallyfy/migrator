# Asana to Tallyfy Object Mapping Guide

## Terminology Translation

This guide provides detailed mapping between Asana and Tallyfy concepts, helping users understand how their project management data transforms during migration.

## Core Object Mappings

### Organizations
| Asana | Tallyfy | Notes |
|-------|---------|-------|
| Workspace/Organization | Organization | Direct mapping |
| Division | Organization | Separate Tallyfy org recommended |
| Team | Group | User collection |

### Template Objects
| Asana | Tallyfy | API Name | Notes |
|-------|---------|----------|-------|
| **Project** | **Blueprint/Template** | `blueprint` | Master process definition |
| **Project Template** | **Blueprint** | `blueprint` | Pre-configured template |
| Task | Step | `step` | Individual work item in template |
| Section | Step Group | N/A | Logical grouping of steps |
| Milestone | Approval Step | `approval` | Key decision point |
| Custom Field | Form Field | `capture` | Data collection element |
| Project Brief | Blueprint Description | `description` | Overview text |
| Rule | Automation Rule | `rule` | Workflow automation |

### Instance Objects
| Asana | Tallyfy | API Name | Notes |
|-------|---------|----------|-------|
| **Project** (active) | **Process** | `run` | Running instance |
| Task (active) | Task | `task` | Actual work item |
| Subtask | Subtask/Checklist | `checklist` | Sub-items |
| Task Status | Task Status | `status` | Completion state |
| Assignee | Assignee | `assignee` | Person responsible |
| Follower | Participant | `participant` | Stakeholder |
| Comment | Comment | `comment` | Discussion thread |

### User & Permission Objects
| Asana | Tallyfy | Notes |
|-------|---------|-------|
| Admin | Administrator | Full organization control |
| Member | Standard Member | Create and edit access |
| Guest | Light Member | Limited to task completion |
| Limited Access Member | Light Member | Restricted permissions |
| Comment-Only Member | Light Member | View and comment only |
| Project Owner | Template Owner | Blueprint control |

## View/Layout Paradigm Mapping

### Asana's Multiple Views → Tallyfy's Sequential Workflow

| Asana View | Tallyfy Implementation | Transformation Strategy |
|------------|----------------------|------------------------|
| **List View** | Sequential Steps | Direct mapping, sections become step groups |
| **Board View** | Sequential with Phases | Each column becomes 3 steps (entry/work/exit) |
| **Timeline View** | Sequential with Deadlines | Dependencies preserved as metadata |
| **Calendar View** | Steps with Due Dates | Date-based organization |
| **Gallery View** | Steps with Attachments | Visual elements attached to steps |
| **Workflow View** | Automated Workflow | Rules and triggers recreated |

## Field Type Mappings

| Asana Custom Field | Tallyfy Capture Type | Data Transformation |
|-------------------|---------------------|-------------------|
| Text | Short Text | Direct mapping |
| Number | Number | Direct mapping |
| Currency | Number | Remove currency symbol |
| Single-Select | Dropdown | Options preserved |
| Multi-Select | Checklist | Multiple selections |
| Date | Date | Direct mapping |
| People | Assignee Picker | User selection |
| Formula | Short Text (readonly) | Store calculated value |

### System Fields
| Asana Field | Tallyfy Field | Notes |
|------------|---------------|-------|
| Task Name | Step/Task Name | Direct |
| Description/Notes | Description | Rich text preserved |
| Due Date | Deadline | With time if specified |
| Start Date | Start Date | For scheduling |
| Assignee | Assignee | User mapping required |
| Projects | Process Association | Multi-homing tracked |
| Tags | Tags | Organizational metadata |
| Priority | Priority Field | Custom field in kick-off |
| Completed | Status | Boolean to status enum |

## Workflow Elements

| Asana Feature | Tallyfy Feature | Implementation |
|--------------|-----------------|----------------|
| Sequential Tasks | Sequential Steps | Default behavior |
| Dependencies | Step Dependencies | Metadata preserved |
| Approvals | Approval Tasks | Specific step type |
| Milestones | Milestone Steps | Visual indicator |
| Recurring Tasks | Template Scheduling | External automation |
| Task Templates | Step Templates | Reusable components |
| Automation Rules | Workflow Rules | IF-THEN logic |
| Forms | Kick-off Forms | Data collection |
| Status Updates | Process Comments | Timeline entries |
| Inbox | Notifications | Task assignments |

## Automation Features

| Asana Rules | Tallyfy Implementation | Migration Approach |
|------------|------------------------|-------------------|
| Auto-assign tasks | Assignment Rules | Recreate in blueprint |
| Move to section | Step Progression | Sequential flow |
| Set custom field | Field Rules | Form logic |
| Add collaborators | Participant Rules | Auto-add users |
| Create subtasks | Checklist Generation | Dynamic creation |
| Due date shifts | Deadline Calculations | Relative dates |
| Complete triggers | Completion Rules | Status-based actions |
| Comment triggers | Notification Rules | @mention handling |

## Data Transformation Rules

### 1. Project to Blueprint Transformation
```
Asana Project → Tallyfy Blueprint
- Name → Title
- Description/Brief → Description
- Sections[] → Step Groups[]
- Tasks[] → Steps[]
- Custom Fields → Kick-off Form Fields
- Rules → Automation Rules
- Default View → Metadata (preserved)
```

### 2. Active Project to Process Transformation
```
Active Asana Project → Tallyfy Process
- Name → Process Name + " - Active"
- Owner → Process Owner
- Members → Participants
- Tasks with Assignees → Active Tasks
- Progress → Completion Percentage
- Custom Field Values → Kick-off Data
```

### 3. Task Transformation
```
Asana Task → Tallyfy Step/Task
- Name → Step Name
- Notes → Description
- Assignee → Default Assignee
- Due Date → Deadline
- Subtasks[] → Checklist Items
- Attachments → File Attachments
- Comments → Task Comments
- Custom Fields → Form Fields
```

### 4. Board Column to Step Group
```
Asana Board Column → Tallyfy Step Group
For each column:
  1. [Column] - Entry (notification step)
  2. [Column] - Work (task steps)
  3. [Column] - Exit (approval step)
```

## Feature Comparison

### ✅ Fully Supported Migrations
- User accounts and profiles
- Basic project structure
- Task assignments and deadlines
- Comments and @mentions
- File attachments (< 100MB)
- Tags and categories
- Custom fields (all types)
- Basic automation rules
- Email notifications

### ⚠️ Partial Support (Manual Configuration Required)
- Complex dependencies (metadata only)
- Multi-homing (tracked but simplified)
- Recurring tasks (external automation)
- Advanced rules (manual recreation)
- Forms (kick-off only)
- Timeline view (converted to sequential)
- Board view (paradigm shift required)
- Portfolios (manual recreation)
- Goals and milestones (limited support)

### ❌ Not Supported (No Equivalent)
- Inbox (use notifications instead)
- Status updates (as comments)
- Workload management
- Calendar sync
- Voice/video in tasks
- Time tracking
- Effort estimates
- Custom app integrations (rebuild)
- Workflow builder UI

## Migration Strategies

### Small Projects (< 20 tasks)
- Direct transformation
- Minimal validation needed
- 5-10 minutes per project

### Board Projects (Kanban-style)
- **Critical**: User training required
- Transform columns to step groups
- Each column = 3 steps
- Preserve column order
- Document paradigm shift

### Timeline Projects (Dependencies)
- Map dependencies as metadata
- Create linear flow based on dates
- Note blocking relationships
- May need manual adjustment

### Large Projects (100+ tasks)
- Consider splitting into multiple blueprints
- Group by sections or phases
- Test with subset first
- Validate performance

### Active Projects
- Complete urgent tasks in Asana first
- Migrate at section boundaries
- Consider parallel run period
- Gradual user transition

## Post-Migration Validation

### Required Checks
1. All users can log into Tallyfy ✓
2. Blueprints match project structure ✓
3. Custom fields preserved ✓
4. Active processes created ✓
5. Files accessible ✓
6. Comments migrated ✓

### Manual Adjustments Often Needed
1. Recreate complex automation rules
2. Set up recurring schedules
3. Configure integrations
4. Adjust notification preferences
5. Train users on paradigm shifts
6. Update documentation/SOPs

## API Endpoint Mappings

| Operation | Asana API | Tallyfy API |
|-----------|-----------|-------------|
| List Templates | `GET /project_templates` | `GET /blueprints` |
| Get Template | `GET /projects/{id}` | `GET /blueprints/{id}` |
| List Projects | `GET /projects` | `GET /runs` |
| Get Project | `GET /projects/{id}` | `GET /runs/{id}` |
| List Tasks | `GET /tasks` | `GET /tasks` |
| Create Task | `POST /tasks` | `POST /tasks` |
| List Users | `GET /users` | `GET /members` |
| Add Comment | `POST /stories` | `POST /comments` |

## User Training Requirements

### Critical Paradigm Shifts

#### From Board View Users
**Asana**: Drag cards between columns
**Tallyfy**: Complete tasks in sequence

**Training Focus**:
- Sequential thinking vs parallel boards
- Task completion vs card movement
- Step dependencies vs column rules

#### From Timeline View Users
**Asana**: Gantt chart with dependencies
**Tallyfy**: Linear workflow with deadlines

**Training Focus**:
- Sequential execution model
- Deadline management
- Dependency documentation

### Workflow Differences

| Asana Workflow | Tallyfy Workflow | User Impact |
|---------------|------------------|-------------|
| Create project from template | Launch process from blueprint | Terminology change |
| Move task between sections | Complete step to advance | Different interaction |
| Assign to multiple projects | Single process ownership | Simplified model |
| Update custom fields anywhere | Fill forms at specific steps | Structured data entry |

## Support Resources

- **Migration Guide**: See README.md
- **API Documentation**: 
  - Asana: https://developers.asana.com/
  - Tallyfy: https://api.tallyfy.com/docs
- **Comparison**: https://tallyfy.com/asana-alternative/
- **Training Videos**: Available post-migration
- **Support**: Free 1:1 support included with Tallyfy Enterprise

## Common Migration Scenarios

### Marketing Team Migration
- Campaign projects → Campaign blueprints
- Creative briefs → Kick-off forms
- Review cycles → Approval steps
- Asset management → File attachments

### Software Development Migration
- Sprint projects → Sprint processes
- Bug tracking → Issue templates
- Code reviews → Approval workflows
- Release management → Deployment blueprints

### HR Team Migration
- Onboarding projects → Onboarding blueprints
- Interview processes → Structured workflows
- Performance reviews → Review templates
- Time-off requests → Request processes

---

**Note**: This mapping guide covers standard transformations. Complex or custom Asana configurations may require additional analysis and custom migration logic.