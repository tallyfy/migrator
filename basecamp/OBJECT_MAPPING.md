# Basecamp to Tallyfy Object Mapping

## Core Object Mappings

### Organizational Structure

| Basecamp Object | Tallyfy Object | Notes |
|----------------|----------------|-------|
| Account | Organization | Top-level container |
| Project | Blueprint Category | Project groupings |
| Person/User | Member | User accounts |
| Company | Group/Team | External organizations |
| Admin | Admin Role | Administrative access |

### Project/Process Structure

| Basecamp Object | Tallyfy Object | Transformation Logic |
|----------------|----------------|----------------------|
| Project | Blueprint | Each project becomes template |
| To-do List | Process Phase | Task groupings |
| To-do | Task/Step | Individual work items |
| Message Board | Comments/Notes | Communication thread |
| Schedule | Timeline | Due dates and milestones |
| Campfire | Process Chat | Real-time discussion |
| Check-in | Status Update | Regular updates |
| Docs & Files | Attachments | Document storage |

## Tool Mappings (Basecamp Dock)

### Core Tools

| Basecamp Tool | Tallyfy Equivalent | Implementation Strategy |
|--------------|-------------------|------------------------|
| Message Board | Process Comments | Thread preservation |
| To-do Lists | Process Steps | Sequential tasks |
| Schedule | Process Timeline | Calendar integration |
| Campfire | Activity Feed | Chat history |
| Check-in Questions | Recurring Tasks | Scheduled updates |
| Docs & Files | Document Library | File references |

### To-do System Transformation

| Basecamp To-do Feature | Tallyfy Implementation | Method |
|-----------------------|------------------------|--------|
| To-do List | Step Group | Related tasks |
| Individual To-do | Process Step | Single task |
| Assignee | Step Assignee | User assignment |
| Due Date | Step Deadline | Time constraint |
| Notes | Step Description | Task details |
| Comments | Step Comments | Discussion |
| Completion | Step Status | Progress tracking |
| Groups within Lists | Sub-steps | Nested structure |

## Communication Features

### Message Board

| Message Feature | Tallyfy Approach | Preservation |
|----------------|------------------|-------------|
| Message | Process Note | Important updates |
| Comments | Note Replies | Thread discussion |
| Attachments | File Links | Document references |
| Subscribers | Followers | Notification list |
| Categories | Tags | Message organization |
| Boost | Priority Flag | Important messages |

### Campfire Chat

| Campfire Feature | Tallyfy Implementation | Strategy |
|-----------------|------------------------|----------|
| Chat Messages | Activity Log | Historical record |
| @Mentions | User References | Notifications |
| File Sharing | Attachment Links | File references |
| Emoji Reactions | Comment Reactions | Simplified |
| Lines (threads) | Comment Threads | Organized discussion |
| Pings | Direct Messages | Private communication |

## Schedule & Events

### Calendar Integration

| Schedule Feature | Tallyfy Equivalent | Mapping |
|-----------------|-------------------|---------|
| Event | Scheduled Task | Calendar item |
| All-day Event | Full Day Task | Date-based |
| Recurring Event | Recurring Process | Pattern-based |
| Event Notes | Task Description | Details |
| Event Attendees | Task Assignees | Participants |
| Event Comments | Task Discussion | Related chat |

## Hill Charts (Basecamp 3)

### Progress Visualization

| Hill Chart Element | Tallyfy Tracking | Transformation |
|-------------------|------------------|----------------|
| Uphill Phase | In Progress | Problem solving |
| Hilltop | Review Point | Solution found |
| Downhill Phase | Implementation | Execution phase |
| Dots/Scopes | Task Groups | Work packages |
| Progress Updates | Status Changes | Movement tracking |

## Paradigm Shifts

### 1. Project-Centric → Process-Centric
**Basecamp**: Projects with various tools
**Tallyfy**: Processes with structured steps
**Transformation**: Project tools become process components

### 2. Flexible Tools → Structured Workflow
**Basecamp**: Mix and match tools per project
**Tallyfy**: Defined process flow
**Transformation**: Tools become workflow phases

### 3. To-do Lists → Sequential Steps
**Basecamp**: Parallel to-do lists
**Tallyfy**: Sequential process steps
**Transformation**: Lists become ordered phases

### 4. Campfire Chat → Process Communication
**Basecamp**: Real-time chat room
**Tallyfy**: Contextual comments
**Transformation**: Chat history as process notes

### 5. Hill Charts → Progress Tracking
**Basecamp**: Visual progress metaphor
**Tallyfy**: Percentage completion
**Transformation**: Hill position to progress percentage

## Project Templates

### Template Transformation

| Basecamp Template | Tallyfy Blueprint | Conversion |
|------------------|------------------|------------|
| Project Template | Blueprint Template | Structure copy |
| Tool Selection | Step Types | Component mapping |
| Default Lists | Standard Phases | Pre-defined steps |
| Team Setup | Default Assignees | Role mapping |
| Schedule Template | Timeline Rules | Duration settings |

## User & Permissions

### Access Control Mapping

| Basecamp Permission | Tallyfy Permission | Role Mapping |
|--------------------|-------------------|--------------|
| Account Owner | Organization Owner | Full control |
| Admin | Admin Role | Administrative |
| Project Member | Process Member | Participant |
| Client/Company | Guest User | Limited access |
| Can See Everything | View All | Read access |
| Can Edit | Edit Permission | Modification rights |

### User Types

| Basecamp User Type | Tallyfy User Type | Migration |
|-------------------|------------------|-----------|
| Employee | Member | Full user |
| Client | Guest | External user |
| Contractor | Member/Guest | Based on access |
| Admin | Administrator | System admin |

## Data Preservation Strategy

### High Priority (Must Preserve)
- Project structure and content
- All to-do lists and items
- Message board posts
- File attachments (as references)
- User assignments
- Due dates
- Comments and discussions
- Project descriptions

### Medium Priority (Preserve if Possible)
- Campfire chat history
- Hill chart positions
- Check-in questions/answers
- Event schedules
- Email forwards
- Notification settings
- Custom categories
- Boost status

### Low Priority (Document Only)
- Project colors/icons
- Avatar images
- Personal preferences
- Notification schedules
- Digest settings
- Time zone preferences
- UI customizations

## Migration Complexity Levels

### Simple Project (1-2 hours)
- <5 to-do lists
- <50 to-dos
- Basic message board
- Few files
- Small team

### Medium Project (2-4 hours)
- 5-15 to-do lists
- 50-200 to-dos
- Active message board
- Campfire usage
- Schedule events
- Multiple files

### Complex Project (4-8 hours)
- 15+ to-do lists
- 200+ to-dos
- Heavy tool usage
- Hill charts
- Check-in questions
- Large team
- Extensive history

### Enterprise Project (8+ hours)
- Multiple sub-projects
- 500+ to-dos
- Complex permissions
- Client access
- Heavy file usage
- Years of history
- Custom workflows

## Special Handling Requirements

### 1. Automatic Check-ins
- Convert to recurring tasks
- Set schedule pattern
- Assign to team members
- Create reminder rules

### 2. Hill Charts
- Document current positions
- Convert to progress percentages
- Preserve update history
- Map scopes to task groups

### 3. Email Forwards
- Configure email integration
- Map forward addresses
- Set up routing rules
- Preserve email threads

### 4. Client Access
- Create guest accounts
- Limit visibility
- Set permissions
- Map company associations

### 5. Campfire Rooms
- Export chat history
- Convert to process notes
- Preserve file shares
- Document @mentions

## File Handling

### Document Management

| Basecamp Files | Tallyfy Storage | Method |
|---------------|-----------------|--------|
| Direct Upload | File Attachment | Re-upload |
| Google Docs | Link Reference | URL preservation |
| Dropbox Files | External Link | Cloud reference |
| Images | Image Attachment | Embed/attach |
| Version History | Version Notes | Document versions |

## Notification System

### Alert Mapping

| Basecamp Notification | Tallyfy Alert | Configuration |
|----------------------|---------------|---------------|
| Daily Digest | Daily Summary | Email schedule |
| @Mentions | Mention Alerts | Real-time |
| Assignment | Task Assignment | Immediate |
| Due Dates | Deadline Alerts | Configurable |
| Comments | Comment Notifications | Per-step |
| Completion | Status Updates | Progress alerts |

## Recommended Migration Sequence

1. **Project Analysis**
   - Inventory all projects
   - Identify active vs archived
   - Document tool usage
   - Map team members

2. **User Migration**
   - Export all people
   - Create Tallyfy accounts
   - Map companies to groups
   - Set permissions

3. **Structure Creation**
   - Convert projects to blueprints
   - Map to-do lists to phases
   - Create step hierarchy
   - Configure timelines

4. **Content Migration**
   - Transfer to-dos as steps
   - Migrate message board
   - Export campfire history
   - Link documents

5. **Communication Transfer**
   - Preserve comments
   - Document discussions
   - Map @mentions
   - Configure notifications

6. **Testing & Validation**
   - Verify all content
   - Test assignments
   - Check permissions
   - Validate workflows

## Known Limitations

### Cannot Migrate
- Hill chart visualizations
- Campfire real-time features
- Door (login) customization
- My Schedule personal view
- Lineup feature
- Card table organization
- Native mobile app data

### Requires Manual Setup
- Email-in addresses
- Webhook integrations
- Custom domains
- SSO configuration
- API integrations
- Time tracking
- Third-party tools

## Migration Validation Checklist

- [ ] All projects mapped
- [ ] To-do lists converted
- [ ] To-dos preserved
- [ ] Users migrated
- [ ] Permissions set
- [ ] Files accessible
- [ ] Comments transferred
- [ ] Dates maintained
- [ ] Assignments correct
- [ ] Message board archived
- [ ] Campfire exported
- [ ] Schedule migrated
- [ ] Check-ins configured
- [ ] Notifications set
- [ ] Testing complete

## Common Patterns

### Marketing Project Pattern
**Basecamp Structure**:
- Campaign to-do lists
- Asset docs & files
- Team campfire
- Launch schedule

**Tallyfy Process**:
1. Campaign Planning (Phase)
2. Content Creation (Phase)
3. Asset Review (Approval)
4. Launch Preparation (Phase)
5. Go Live (Milestone)
6. Post-Launch Review (Phase)

### Software Development Pattern
**Basecamp Structure**:
- Sprint to-do lists
- Bug tracking
- Code review messages
- Release schedule

**Tallyfy Process**:
1. Sprint Planning (Kick-off)
2. Development Tasks (Parallel steps)
3. Code Review (Approval)
4. Testing Phase (Tasks)
5. Release Approval (Gate)
6. Deployment (Final)

### Client Project Pattern
**Basecamp Structure**:
- Client-visible lists
- Internal lists
- Client message board
- Milestone schedule

**Tallyfy Process**:
1. Project Initiation (Kick-off)
2. Discovery Phase (Client visible)
3. Internal Planning (Team only)
4. Implementation (Mixed visibility)
5. Client Review (Approval)
6. Project Closure (Completion)