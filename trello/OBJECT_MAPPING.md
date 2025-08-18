# Trello to Tallyfy Object Mapping

## Core Object Mappings

### Organizational Structure

| Trello Object | Tallyfy Object | Notes |
|--------------|----------------|-------|
| Workspace (Team) | Organization | Top-level container |
| Board | Blueprint | Each board becomes a process template |
| Member | Member | User accounts |
| Team | Group | User groupings |
| Guest | Guest User | Limited access users |

### Board/Process Structure

| Trello Object | Tallyfy Object | Transformation Logic |
|--------------|----------------|----------------------|
| List | Process Phase/Stage | Each list becomes sequential steps |
| Card | Task | Individual work items |
| Checklist | Sub-tasks/Checklist | Items within a task |
| Label | Tag/Category | Card categorization |
| Due Date | Due Date | Task deadlines |

### Key Paradigm Shift: Kanban → Sequential

**Critical Transformation**: Trello's parallel Kanban model must be converted to Tallyfy's sequential workflow model.

| Trello Concept | Tallyfy Implementation | Conversion Strategy |
|---------------|------------------------|-------------------|
| List (Column) | 3-Step Sequence | Each list becomes Entry → Work → Exit |
| Card Movement | Task Completion | Moving card = completing current step |
| Multiple Lists | Linear Workflow | Lists become sequential phases |
| Backlog List | Kick-off Form | Initial list for process initiation |
| Done List | Process Completion | Final approval/archive step |

## Detailed List-to-Step Transformation

### Standard Pattern (Per List)
Each Trello list transforms into 3 Tallyfy steps:

1. **Entry Step** (Task Assignment)
   - Name: "[List Name] - Ready"
   - Type: Task
   - Purpose: Item enters this phase
   - Assignment: Team member selection

2. **Work Step** (Active Work)
   - Name: "[List Name] - In Progress"
   - Type: Task with form
   - Purpose: Actual work happens here
   - Fields: Card details, checklists

3. **Exit Step** (Quality Gate)
   - Name: "[List Name] - Review"
   - Type: Approval
   - Purpose: Verify completion
   - Next: Move to next list's entry

### Example Transformation

**Trello Board**: Product Development
- Lists: Backlog → Design → Development → Testing → Deployed

**Tallyfy Process**:
1. Kick-off Form (from Backlog cards)
2. Design - Ready (Task)
3. Design - In Progress (Task)
4. Design - Review (Approval)
5. Development - Ready (Task)
6. Development - In Progress (Task)
7. Development - Review (Approval)
8. Testing - Ready (Task)
9. Testing - In Progress (Task)
10. Testing - Review (Approval)
11. Deployment - Ready (Task)
12. Deployment - In Progress (Task)
13. Final Approval (Approval)

## Field Mappings

### Card Fields

| Trello Field | Tallyfy Field | Type Conversion |
|-------------|---------------|-----------------|
| Card Name | Task Name | Direct |
| Description | Task Description | Markdown → Rich Text |
| Due Date | Due Date | Direct |
| Members | Assignees | User references |
| Labels | Tags | Multi-select |
| Cover | Header Image | File reference |
| Position | Step Order | Sequential index |

### Checklist Items

| Trello Checklist | Tallyfy Implementation | Notes |
|-----------------|------------------------|--------|
| Checklist Name | Section Header | Group related fields |
| Check Item | Checkbox Field | Yes/No field |
| Item State | Field Value | Checked = Yes |
| Item Assignee | Field Note | Store in description |

### Custom Fields

| Trello Custom Field | Tallyfy Field Type | Fallback |
|--------------------|-------------------|----------|
| Text | Short Text | Direct |
| Number | Number | Direct |
| Date | Date | Direct |
| Dropdown | Dropdown | Direct |
| Checkbox | Yes/No | Direct |

### Activity & Comments

| Trello Activity | Tallyfy Equivalent | Migration Method |
|----------------|-------------------|------------------|
| Comment | Comment | Preserve with timestamp |
| Card Move | Activity Log | Record in history |
| Member Added | Assignment | Update assignee |
| Due Date Change | Timeline Update | Update field |
| Attachment | File Reference | Link or upload |

## Advanced Features

### Power-Ups to Tallyfy Features

| Trello Power-Up | Tallyfy Alternative | Implementation |
|-----------------|-------------------|----------------|
| Butler Automation | Process Rules | Convert to conditions |
| Custom Fields | Form Fields | Direct mapping |
| Card Aging | SLA Tracking | Due date rules |
| Calendar | Timeline View | Process scheduling |
| Voting | Approval Step | Multi-approver setup |

### Automation Rules

| Butler Rule Type | Tallyfy Implementation | Example |
|-----------------|------------------------|---------|
| Card Button | Quick Action | One-click task completion |
| Board Button | Process Trigger | Start new process |
| Calendar Command | Scheduled Process | Recurring initiation |
| Due Date Command | Deadline Rule | Auto-assignment on due date |
| List Command | Phase Transition | Auto-move on completion |

## Data Preservation Strategy

### High Priority (Must Preserve)
- Board structure and lists
- All cards and their content
- Checklists and completion state
- Comments and activity
- Member assignments
- Due dates
- Labels and categorization
- Attachments (as references)

### Medium Priority (Preserve if Possible)
- Card positions within lists
- Power-Up data
- Voting results
- Card aging information
- Automation rules
- Stickers and reactions
- Card templates

### Low Priority (Document Only)
- Board backgrounds
- Card covers (aesthetic)
- Emoji reactions
- Board starred status
- Personal preferences
- Watch notifications

## Migration Complexity Levels

### Simple Board (1-2 hours)
- 3-5 lists
- <50 cards
- No custom fields
- Basic checklists
- Standard workflow

### Medium Board (2-4 hours)
- 5-10 lists
- 50-200 cards
- Custom fields
- Multiple checklists
- Some automation

### Complex Board (4-8 hours)
- 10+ lists
- 200+ cards
- Heavy automation
- Power-Ups
- Cross-board dependencies
- Complex checklists

## Special Handling Requirements

### 1. Archived Cards
- Include archived cards as completed processes
- Maintain archive timestamp
- Mark with "Archived" tag

### 2. Recurring Cards
- Identify patterns
- Create scheduled process
- Set recurrence rules

### 3. Template Cards
- Convert to blueprint templates
- Preserve as process templates
- Document template usage

### 4. Cross-Board Dependencies
- Document relationships
- Create reference fields
- Consider consolidation

### 5. Large Attachments
- Files <10MB: Direct upload
- Files >10MB: Cloud link
- Google Drive/Dropbox: Preserve links

## Recommended List Patterns

### Development Boards
```
Backlog → In Progress → Review → Done
↓
Kick-off → Development → Testing → Deployment
```

### Support Boards
```
New → Triaged → In Progress → Resolved → Closed
↓
Intake → Assessment → Resolution → Verification → Closure
```

### Marketing Boards
```
Ideas → Planning → Creation → Review → Published
↓
Ideation → Planning → Content Creation → Approval → Publishing
```

## Validation Checklist

- [ ] All boards mapped to blueprints
- [ ] Lists converted to sequential steps
- [ ] Cards migrated with content
- [ ] Checklists preserved
- [ ] Members correctly assigned
- [ ] Labels converted to tags
- [ ] Comments with timestamps
- [ ] Due dates maintained
- [ ] Attachments accessible
- [ ] Automation documented

## Known Limitations

### Cannot Migrate
- Board backgrounds and themes
- Stickers on cards
- Card positioning (Kanban visual)
- Power-Up specific data
- Board visibility settings
- Personal notification preferences

### Requires Manual Setup
- Complex Butler automations
- Cross-workspace boards
- External integrations
- Webhook configurations
- Power-Up configurations

## Migration Sequence

1. **Analysis Phase**
   - Map board structure
   - Identify automation
   - Document Power-Ups
   - Count cards and lists

2. **User Migration**
   - Export all members
   - Create Tallyfy accounts
   - Map permissions

3. **Structure Creation**
   - Create blueprints from boards
   - Define step sequences
   - Configure fields

4. **Content Migration**
   - Transfer cards as tasks
   - Migrate checklists
   - Preserve comments
   - Handle attachments

5. **Validation**
   - Verify all cards migrated
   - Test step sequences
   - Validate assignments
   - Check automations

## Transformation Examples

### Example 1: Simple Kanban
**Trello**: To Do → Doing → Done
**Tallyfy**: 
1. Process Initiation (Kick-off)
2. Task Assignment (Task)
3. Work Execution (Task)
4. Quality Review (Approval)
5. Completion (Final Step)

### Example 2: Software Development
**Trello**: Backlog → Design → Dev → QA → Staging → Production
**Tallyfy**:
1. Feature Request (Kick-off)
2. Design Phase (3 steps)
3. Development Phase (3 steps)
4. QA Phase (3 steps)
5. Staging Approval (Approval)
6. Production Deployment (3 steps)
7. Post-Deployment Verification (Final)

### Example 3: Content Pipeline
**Trello**: Ideas → Writing → Editing → Graphics → Published
**Tallyfy**:
1. Content Idea Submission (Kick-off)
2. Writing Assignment (Task)
3. Draft Creation (Task)
4. Editorial Review (Approval)
5. Graphics Creation (Task)
6. Final Review (Approval)
7. Publishing (Task)
8. Published Confirmation (Final)