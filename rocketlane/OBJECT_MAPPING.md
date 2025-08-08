# RocketLane to Tallyfy Object Mapping

## Complete Field-Level Mappings

This document provides exhaustive mapping between RocketLane and Tallyfy objects, fields, and concepts.

## 🏢 Organization & User Mappings

### Customers → Guest Users or Organizations

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| customer.id | guest.metadata.original_id | Direct | Preserved in metadata |
| customer.name | guest.name | Direct | Company name |
| customer.company_name | guest.company | Direct | Organization name |
| customer.email | guest.email | Primary contact email | Uses primary contact |
| customer.phone | guest.phone | Optional | Primary contact phone |
| customer.tier | guest.metadata.tier | Direct | Customer tier level |
| customer.industry | guest.metadata.industry | Direct | Industry classification |
| customer.portal_access_enabled | guest.send_notifications | Boolean | Portal access → notifications |
| customer.portal_users_count | Decision factor | AI/Heuristic | >5 users → organization |
| customer.contacts[] | guest.metadata.additional_contacts | Array → JSON | Secondary contacts |
| customer.created_at | guest.metadata.created_at | Direct | Creation timestamp |
| customer.value | guest.metadata.value | Direct | Customer lifetime value |
| customer.status | guest.active | active → true | Status mapping |

### Internal Users → Members

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| user.id | member.metadata.original_id | Direct | Preserved |
| user.email | member.email | Direct | Primary identifier |
| user.first_name | member.firstname | Direct | Given name |
| user.last_name | member.lastname | Direct | Family name |
| user.role | member.role | Mapped | admin→admin, manager→admin, member→member |
| user.permissions[] | member.role | Analysis | Elevated permissions → admin |
| user.department | member.metadata.department | Direct | Department info |
| user.job_title | member.metadata.title | Direct | Job title |
| user.skills[] | member.metadata.skills | Array | Skill tags |
| user.capacity_hours_per_week | member.metadata.capacity_hours | Direct | Resource capacity |
| user.timezone | member.timezone | Direct | User timezone |
| user.avatar_url | member.avatar_url | Direct | Profile image |
| user.phone | member.phone | Optional | Contact number |
| user.active | member.active | Direct | Account status |

### Teams → Groups

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| team.id | group.metadata.original_id | Direct | Preserved |
| team.name | group.name | Direct | Team name |
| team.description | group.description | Direct | Team description |
| team.lead_id | group.metadata.team_lead | Direct | Team leader reference |
| team.member_ids[] | group.members[] | ID mapping | Mapped user IDs |
| team.department | group.metadata.department | Direct | Department |
| team.skills[] | group.metadata.skills | Array | Shared skills |

## 📋 Template & Workflow Mappings

### Project Templates → Blueprints

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| template.id | blueprint.metadata.original_id | Direct | Preserved |
| template.name | blueprint.name | Truncate 250 | Name limit |
| template.description | blueprint.summary | Truncate 2000 | Description limit |
| template.customer_type | blueprint.metadata.customer_type | Direct | Customer segment |
| template.industry | blueprint.metadata.industry | Direct | Industry vertical |
| template.estimated_duration | blueprint.metadata.duration_days | Direct | Timeline |
| template.team_size | blueprint.metadata.team_size | Direct | Resource requirement |
| template.deliverables[] | blueprint.description | Array → Text | Combined in description |
| template.customer_visible | blueprint.guest_access | Boolean | Guest visibility |
| template.sla_config | blueprint.sla | Object mapping | SLA transformation |
| template.automations[] | blueprint.automations[] | Complex mapping | Rule transformation |

### Phases → Step Groups

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| phase.id | step_group.metadata.original_phase_id | Direct | Preserved |
| phase.name | step_group.name | Truncate 600 | Step name limit |
| phase.description | step_group.description | Direct | Phase description |
| phase.order | Position in array | Numeric sort | Sequential ordering |
| phase.start_after_days | step_group.metadata.start_after | Direct | Delay from start |
| phase.duration_days | step_group.metadata.duration_days | Direct | Phase duration |
| phase.is_milestone | step_group.metadata.milestone | Boolean | Milestone flag |
| phase.entry_criteria[] | step_group.entry_conditions[] | Array mapping | Entry requirements |
| phase.exit_criteria[] | step_group.completion_conditions[] | Array mapping | Exit requirements |
| phase.default_owner | step_group.default_assignee | ID mapping | Default assignee |

### Tasks → Tasks/Steps

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| task.id | task.metadata.original_task_id | Direct | Preserved |
| task.title | task.name | Truncate 600 | Name limit |
| task.description | task.description | Direct | Task details |
| task.type | task.type | Mapped | approval, milestone, task, form |
| task.phase_id | Parent step group | Hierarchy | Nested in phase |
| task.assigned_to | task.assigned_to | ID mapping | User assignment |
| task.assigned_role | task.assignee_type = 'role' | Role-based | Role assignment |
| task.assigned_team | task.assigned_to_group | ID mapping | Team assignment |
| task.due_after_days | task.deadline_days | Direct | Relative deadline |
| task.due_date | task.due_date | Direct | Absolute deadline |
| task.due_date_critical | task.type = 'expiring' | Boolean → Type | Critical deadlines |
| task.estimated_hours | task.metadata.estimated_hours | Direct | Time estimate |
| task.actual_hours | task.metadata.actual_hours | Direct | Actual time |
| task.priority | task.metadata.priority | Direct | Priority level |
| task.dependencies[] | task.dependencies[] | Array mapping | Task dependencies |
| task.customer_visible | task.guest_can_view | Boolean | Guest visibility |
| task.customer_can_complete | task.guest_can_complete | Boolean | Guest completion |
| task.requires_approval | task.type = 'approval' | Boolean → Type | Approval tasks |
| task.approval_type | task.approval_type | Direct | any, all, specific |
| task.checklist_items[] | task.checklist[] | Array mapping | Sub-items |
| task.custom_fields | task.form_fields[] | Field transformation | Form data |

## 📝 Form & Field Mappings

### Forms → Kick-off Forms or Step Forms

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| form.id | form.metadata.original_id | Direct | Preserved |
| form.name | form.name | Direct | Form name |
| form.type | Placement decision | AI/Heuristic | kickoff vs step form |
| form.fields[] | form.fields[] | Field transformation | See field mappings |
| form.is_kickoff | kickoff_form | Boolean | Kickoff placement |
| form.customer_visible | guest_can_submit | Boolean | Guest submission |
| form.has_conditional_logic | Requires manual review | Flag | Complex logic |
| form.position | form.position | Direct | Form order |

### Field Type Mappings

| RocketLane Type | Tallyfy Type | Validation | Notes |
|----------------|--------------|------------|-------|
| text | text | max:255 | Short text |
| longtext | textarea | max:6000 | Long text |
| number | text | numeric | No native number type |
| decimal | text | numeric | Decimal validation |
| currency | text | numeric\|min:0 | Currency format |
| percentage | text | numeric\|min:0\|max:100 | Percentage validation |
| email | email | email | Email field |
| phone | text | regex:^[\d\s\-\+\(\)]+$ | Phone pattern |
| url | text | url | URL validation |
| date | date | - | Date picker |
| datetime | date | include_time=true | Date with time |
| time | text | regex | Time format |
| boolean | radio | yes/no options | Boolean to radio |
| checkbox | radio | Single checkbox |
| select | dropdown | - | Single select |
| multiselect | multiselect | - | Multiple select |
| radio | radio | - | Radio buttons |
| file | file | - | File upload |
| image | file | accept:image/* | Image upload |
| user | assignees_form | - | User picker |
| team | assignees_form | - | Team picker |
| customer | dropdown | - | Customer reference |
| project | dropdown | - | Project reference |
| task | dropdown | - | Task reference |
| milestone | dropdown | - | Milestone reference |
| rating | dropdown | 1-5 scale | Rating scale |
| slider | text | numeric | Slider value |
| formula | text | readonly | Calculated field |
| lookup | dropdown | - | Lookup field |
| barcode | text | regex:^[A-Za-z0-9]+$ | Barcode pattern |
| signature | file | - | Signature upload |
| location | text | - | Location text |
| color | dropdown | - | Color options |
| tags | multiselect | - | Tag selection |
| json | textarea | - | JSON data |
| markdown | textarea | - | Markdown text |
| html | textarea | - | HTML content |
| table | table | - | Table/grid |
| matrix | table | - | Matrix to table |
| kanban | dropdown | - | Status selection |
| gantt | date | range | Date range |
| calendar | date | - | Calendar event |
| timeline | date | - | Timeline date |

## 🏃 Instance & Process Mappings

### Projects → Processes

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| project.id | process.metadata.original_id | Direct | Preserved |
| project.name | process.name | Truncate 250 | Name limit |
| project.description | process.description | Combined | Full description |
| project.template_id | process.blueprint_id | ID mapping | Template reference |
| project.customer_id | process.guest_context.customer_id | Direct | Customer reference |
| project.customer | process.guest_context | Object mapping | Customer data |
| project.status | process.status | Mapped | Status transformation |
| project.health_status | process.metadata.health | Direct | Project health |
| project.started_at | process.metadata.started_at | Direct | Start timestamp |
| project.completed_at | process.completed_at | Direct | Completion time |
| project.owner | process.metadata.owner | Direct | Project owner |
| project.value | process.metadata.value | Direct | Project value |
| project.estimated_end_date | process.metadata.target_completion | Direct | Target date |
| project.custom_fields | process.prerun_data | Object → Object | Field values |
| project.phases[] | process.tasks[] | Complex | Phase transformation |
| project.tasks[] | process.tasks[] | Array mapping | Task transformation |
| project.time_entries[] | Comments | Time → Text | Time tracking |
| project.documents[] | process.external_documents[] | Array | Document references |
| project.comments[] | process.comments[] | Array mapping | Comments |
| project.resource_allocations[] | Task assignments | Complex | Resource mapping |

### Status Mappings

| RocketLane Status | Tallyfy Status | Notes |
|------------------|----------------|-------|
| not_started | pending | Not yet begun |
| in_progress | active | Currently working |
| active | active | Active project |
| completed | completed | Finished |
| done | completed | Finished |
| cancelled | cancelled | Terminated |
| on_hold | paused | Temporarily stopped |
| blocked | blocked | Dependency blocked |

## 🕐 Time & Resource Mappings

### Time Entries → Comments

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| time_entry.id | comment.metadata.original_id | Direct | Preserved |
| time_entry.hours | comment.metadata.hours | Direct | Hours logged |
| time_entry.description | comment.text | Formatted | "[Time: X hours] Description" |
| time_entry.date | comment.metadata.date | Direct | Entry date |
| time_entry.user_id | comment.created_by | ID mapping | User who logged |
| time_entry.task_id | Task comment | Association | Linked to task |
| time_entry.billable | comment.metadata.billable | Boolean | Billable flag |
| time_entry.activity_type | comment.metadata.activity_type | Direct | Activity category |
| time_entry.created_at | comment.created_at | Direct | Creation time |

### Resource Allocations → Assignments

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| allocation.resource_id | task.assigned_to | ID mapping | Direct assignment |
| allocation.resource_name | task.resource_note | Text note | If unmapped |
| allocation.role | task.metadata.role | Direct | Role requirement |
| allocation.percentage | Note | Text | "X% allocation" |
| allocation.skills[] | task.metadata.skills_required | Array | Required skills |
| allocation.start_date | task.metadata.allocation_start | Direct | Allocation period |
| allocation.end_date | task.metadata.allocation_end | Direct | Allocation period |
| allocation.task_ids[] | Multiple assignments | Distribution | Spread across tasks |

## 🔄 Automation & Rule Mappings

### Automations → Rules

| RocketLane Field | Tallyfy Field | Transformation | Notes |
|-----------------|---------------|----------------|-------|
| automation.name | rule.name | Direct | Rule name |
| automation.trigger.type | rule.trigger.type | Mapped | Trigger mapping |
| automation.conditions[] | rule.conditions[] | Array mapping | Conditions |
| automation.actions[] | rule.actions[] | Mapped | Action transformation |

### Trigger Type Mappings

| RocketLane Trigger | Tallyfy Trigger | Notes |
|-------------------|-----------------|-------|
| task_completed | step_completed | Task completion |
| phase_started | step_started | Phase start |
| form_submitted | form_submitted | Form submission |
| due_date_approaching | deadline_approaching | Deadline warning |
| project_started | process_started | Project start |
| customer_action | guest_action | Customer interaction |
| time_logged | comment_added | Time entry |

### Action Type Mappings

| RocketLane Action | Tallyfy Action | Notes |
|------------------|----------------|-------|
| send_email | send_notification | Email notification |
| create_task | create_step | Add task |
| update_field | set_field_value | Update value |
| assign_user | assign_step | Assignment |
| add_comment | add_comment | Comment |
| update_status | update_status | Status change |
| webhook | webhook | External call |

## 🚫 Non-Migrated Elements

### Cannot Migrate
- Billing & invoicing data
- Resource capacity planning
- Customer portal branding
- Financial reports
- Gantt chart views
- Revenue tracking
- Utilization reports
- Custom CSS/branding
- API integrations (require reconfiguration)
- Webhooks (require new endpoints)

### Requires Manual Configuration
- Complex cross-phase dependencies
- Advanced automation chains
- Custom integration mappings
- CSAT survey configurations
- Advanced permission schemes
- Custom notification templates
- Billing integrations
- Time tracking integrations

## 📊 Paradigm Shifts

### Major Transformations

1. **Customer Portal → Guest Access**
   - Portal users become guest users
   - Portal visibility becomes guest permissions
   - Customer forms become guest-submittable forms

2. **Resource Management → Task Assignment**
   - Capacity planning becomes notes
   - Skills matching becomes metadata
   - Utilization tracking requires external tool

3. **Parallel Phases → Sequential Steps**
   - Parallel work becomes sequential with conditions
   - Phase dependencies become step dependencies
   - Milestones become milestone-type steps

4. **Time Tracking → Activity Comments**
   - Time entries become structured comments
   - Billable hours preserved in metadata
   - Reports require external analysis

5. **Project Hierarchy → Flat Processes**
   - Nested projects become linked processes
   - Subprojects become separate processes
   - Parent-child relationships in metadata