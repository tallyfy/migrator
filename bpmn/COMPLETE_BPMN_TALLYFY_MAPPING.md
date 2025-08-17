# Complete BPMN 2.0 to Tallyfy Mapping Matrix

## Tallyfy Capabilities Analysis (from api-v2)

### Task Types (5 types)
```php
TASK_TYPE_TASK = 'task'              // Standard task with COMPLETE button
TASK_TYPE_APPROVAL = 'approval'      // Approval with APPROVE/REJECT buttons
TASK_TYPE_EXPIRING = 'expiring'      // Time-sensitive with ACKNOWLEDGE button
TASK_TYPE_EMAIL = 'email'            // Email task with SEND button
TASK_TYPE_EXPIRING_EMAIL = 'expiring_email'  // Combined expiring + email
```

### Task Statuses (9 statuses)
```php
TASK_NOT_STARTED = 'not-started'
TASK_COMPLETED = 'completed'
TASK_INPROGRESS = 'in-progress'
TASK_AUTO_SKIPPED = 'auto-skipped'
TASK_APPROVED = 'approved'       // For approval tasks
TASK_REJECTED = 'rejected'       // For approval tasks
TASK_ACKNOWLEDGED = 'acknowledged' // For expiring tasks
TASK_EXPIRED = 'expired'         // For expiring tasks
TASK_REOPENED = 'reopened'
```

### Field Types (10 types from ALLOWED_CAPTURE_TYPES)
```php
'text'           // Short text input (max 200 chars)
'textarea'       // Long text input (max 30,000 chars)
'radio'          // Single choice radio buttons
'dropdown'       // Single select dropdown
'multiselect'    // Multiple select checkboxes
'date'           // Date picker (with optional time)
'email'          // Email field with validation
'file'           // File upload
'table'          // Table/grid data entry
'assignees_form' // User/guest assignment picker
```

### Conditional Logic Operators (11 operators)
```php
CONDITION_EQUALS = 'equals'
CONDITION_NOT_EQUALS = 'not_equals'
CONDITION_EQUALS_ANY = 'equals_any'
CONDITION_CONTAINS = 'contains'
CONDITION_NOT_CONTAINS = 'not_contains'
CONDITION_GREATER_THAN = 'greater_than'
CONDITION_LESS_THAN = 'less_than'
CONDITION_EMPTY = 'is_empty'
CONDITION_NOT_EMPTY = 'is_not_empty'
CONDITION_AND = 'and'
CONDITION_OR = 'or'
```

### Automated Actions (8 actions)
```php
ACTION_SHOW = 'show'              // Show step/field
ACTION_HIDE = 'hide'              // Hide step/field
ACTION_DEADLINE = 'deadline'      // Set deadline
ACTION_REOPEN = 'reopen'         // Reopen task
ACTION_ASSIGN = 'assign'          // Assign to user
ACTION_UNASSIGN = 'unassign'     // Remove assignment
ACTION_ASSIGN_ONLY = 'assign_only' // Exclusive assignment
ACTION_CLEAR_ASSIGNEE = 'clear_assignees' // Clear all
```

### Additional Features
- Webhooks (webhook field on steps and checklists)
- Guest permissions and assignments
- Watchers and notifications
- Comments and @mentions
- File attachments
- Process variables ({{variable}} replacement)
- Tags and folders for organization
- Kick-off forms (preruns)
- Step dependencies (position-based)

## BPMN 2.0 Complete Element Matrix

### BPMN Events (63 Permutations)

| BPMN Event Type | Position | Behavior | Tallyfy Mapping | Confidence | AI Required |
|-----------------|----------|----------|-----------------|------------|-------------|
| **None Event** | Start | - | Manual process start | 100% | No |
| None Event | End | - | Process completion | 100% | No |
| None Event | Intermediate Throw | - | Log/comment step | 80% | No |
| **Message Event** | Start | Catching | Webhook trigger | 70% | Yes |
| Message Event | Start | Catching (Multiple) | Multiple webhooks | 50% | Yes |
| Message Event | End | Throwing | Email task or webhook | 80% | No |
| Message Event | Intermediate Catch | Catching | Approval task (wait) | 60% | Yes |
| Message Event | Intermediate Throw | Throwing | Email task | 80% | No |
| Message Event | Boundary | Interrupting | Cannot map | 0% | - |
| Message Event | Boundary | Non-interrupting | Cannot map | 0% | - |
| **Timer Event** | Start | Date | External scheduler needed | 30% | Yes |
| Timer Event | Start | Cycle | External scheduler needed | 30% | Yes |
| Timer Event | Intermediate Catch | Duration | Task deadline | 70% | No |
| Timer Event | Boundary | Interrupting | Task deadline + escalation | 50% | Yes |
| Timer Event | Boundary | Non-interrupting | Cannot map | 0% | - |
| **Error Event** | End | - | Mark run as problem | 60% | No |
| Error Event | Boundary | Interrupting | Cannot map directly | 0% | - |
| Error Event | Start (Event Sub) | - | Cannot map | 0% | - |
| **Escalation Event** | End | Throwing | Notification to manager | 40% | Yes |
| Escalation Event | Intermediate Throw | - | Notification step | 40% | Yes |
| Escalation Event | Boundary | Non-interrupting | Cannot map | 0% | - |
| **Cancel Event** | End | - | Archive run | 50% | No |
| Cancel Event | Boundary | - | Cannot map | 0% | - |
| **Compensation Event** | Intermediate Throw | - | Manual rollback steps | 20% | Yes |
| Compensation Event | Boundary | - | Cannot map | 0% | - |
| Compensation Event | End | - | Cannot map | 0% | - |
| **Signal Event** | Start | Catching | Webhook trigger | 60% | Yes |
| Signal Event | End | Throwing | Webhook call | 60% | Yes |
| Signal Event | Intermediate Catch | - | Approval task | 50% | Yes |
| Signal Event | Intermediate Throw | - | Webhook call | 60% | Yes |
| Signal Event | Boundary | Interrupting | Cannot map | 0% | - |
| Signal Event | Boundary | Non-interrupting | Cannot map | 0% | - |
| **Conditional Event** | Start | - | Cannot map | 0% | - |
| Conditional Event | Intermediate Catch | - | Rule-based visibility | 40% | Yes |
| Conditional Event | Boundary | - | Cannot map | 0% | - |
| **Link Event** | Intermediate Throw | - | Go to step (manual) | 30% | Yes |
| Link Event | Intermediate Catch | - | Target step marker | 30% | Yes |
| **Terminate Event** | End | - | Force complete all | 70% | No |
| **Multiple Event** | Start | - | Multiple triggers | 20% | Yes |
| Multiple Event | End | - | Multiple actions | 30% | Yes |
| Multiple Event | Intermediate Catch | - | Complex approval | 20% | Yes |
| **Parallel Multiple Event** | Start | - | Cannot map | 0% | - |
| Parallel Multiple Event | Intermediate | - | Cannot map | 0% | - |

### BPMN Activities/Tasks (20+ Types)

| BPMN Task Type | Tallyfy Mapping | Field Mapping | Confidence | AI Required |
|----------------|-----------------|---------------|------------|-------------|
| **User Task** | Task (task) | Form fields → Captures | 95% | No |
| User Task + Form | Task with captures | Direct field mapping | 90% | No |
| User Task + Multi-instance Sequential | Multiple tasks (cloned) | Same fields | 60% | Yes |
| User Task + Multi-instance Parallel | Tasks at same position | Same fields | 50% | Yes |
| User Task + Loop | Cannot map (need external) | - | 0% | - |
| **Manual Task** | Task (task) | Description only | 95% | No |
| **Service Task** | Webhook step | Webhook URL | 70% | No |
| Service Task + REST | Webhook with payload | JSON payload | 60% | Yes |
| Service Task + SOAP | Cannot map directly | - | 20% | Yes |
| **Script Task** | Webhook to function | Script → external service | 40% | Yes |
| **Business Rule Task** | Task with rules | Complex conditions | 40% | Yes |
| Business Rule Task + DMN | Cannot map | - | 0% | - |
| **Send Task** | Email task | Email fields | 85% | No |
| **Receive Task** | Approval task | Wait for input | 70% | No |
| **Call Activity** | Cannot map (no subprocess) | - | 10% | Yes |
| **Subprocess** (Embedded) | Inline steps | Flatten structure | 50% | Yes |
| **Subprocess** (Event) | Cannot map | - | 0% | - |
| **Subprocess** (Transaction) | Cannot map | - | 0% | - |
| **Subprocess** (Ad-hoc) | Cannot map | - | 0% | - |
| **Task** (Generic) | Task (task) | Basic task | 90% | No |

### BPMN Gateways (5 Types × Multiple Configurations)

| Gateway Type | Direction | Conditions | Tallyfy Mapping | Confidence | AI Required |
|--------------|-----------|------------|-----------------|------------|-------------|
| **Exclusive (XOR)** | Diverging | 2 paths | IF-THEN-ELSE rules | 90% | No |
| Exclusive | Diverging | 3+ paths | Multiple IF-THEN rules | 85% | No |
| Exclusive | Converging | - | No action needed | 100% | No |
| Exclusive | Mixed | Complex | Separate diverge/converge | 70% | Yes |
| **Parallel (AND)** | Diverging | 2 paths | Steps at same position | 70% | No |
| Parallel | Diverging | 3+ paths | Multiple steps same position | 60% | No |
| Parallel | Converging | 2 paths | Wait step (approval) | 50% | Yes |
| Parallel | Converging | 3+ paths | Complex wait logic | 30% | Yes |
| **Inclusive (OR)** | Diverging | 2 paths | Non-exclusive rules | 60% | Yes |
| Inclusive | Diverging | 3+ paths | Complex rule set | 40% | Yes |
| Inclusive | Converging | Any | Cannot map properly | 10% | - |
| **Event-based** | Diverging | Timer + Message | Approval with timeout | 40% | Yes |
| Event-based | Diverging | Multiple events | Cannot map | 0% | - |
| **Complex** | Any | Custom logic | Manual configuration | 10% | Yes |

### BPMN Data Elements

| BPMN Data Element | Tallyfy Mapping | Implementation | Confidence | AI Required |
|-------------------|-----------------|----------------|------------|-------------|
| **Data Object** | Form field | Create as capture | 80% | No |
| Data Object (Collection) | Table field | Table capture | 70% | No |
| **Data Input** | Kick-off form field | Prerun field | 85% | No |
| **Data Output** | Task form field | Capture on task | 85% | No |
| **Data Store** | External reference | Document in description | 30% | Yes |
| **Data Association** | Field reference | {{variable}} syntax | 60% | Yes |
| **Message** | Email/webhook data | Payload mapping | 50% | Yes |
| **Input Set** | Multiple fields | Form field group | 70% | No |
| **Output Set** | Multiple fields | Task captures | 70% | No |

### BPMN Swimlanes

| BPMN Element | Tallyfy Mapping | Implementation | Confidence | AI Required |
|--------------|-----------------|----------------|------------|-------------|
| **Pool** (Single) | Template/Checklist | Direct mapping | 95% | No |
| **Pool** (Multiple) | Multiple templates | Separate checklists | 80% | Yes |
| **Pool** (Black box) | External reference | Webhook/email | 60% | Yes |
| **Lane** | Group/Role | User group assignment | 90% | No |
| **Lane** (Nested) | Nested groups | Flatten structure | 70% | Yes |
| **Message Flow** | Webhook/Email | Inter-template comm | 50% | Yes |

### BPMN Flow Elements

| BPMN Flow Type | Tallyfy Mapping | Implementation | Confidence | AI Required |
|----------------|-----------------|----------------|------------|-------------|
| **Sequence Flow** | Step order | Position attribute | 100% | No |
| **Conditional Flow** | Conditional rule | IF-THEN visibility | 85% | No |
| **Default Flow** | Else condition | Default path | 90% | No |
| **Message Flow** | Webhook | API call | 60% | Yes |
| **Association** | Documentation | Step description | 100% | No |

## Complex BPMN Patterns

### Pattern Recognition Matrix

| BPMN Pattern | Description | Tallyfy Strategy | Success Rate | AI Value |
|--------------|-------------|------------------|--------------|----------|
| **Sequential Process** | Task→Task→Task | Direct step mapping | 100% | Low |
| **Simple Decision** | Task→XOR→[A⎮B]→Merge | IF-THEN rules | 90% | Low |
| **Parallel Split-Join** | Task→AND→[A‖B]→AND→Task | Same position + wait | 60% | Medium |
| **Loop Pattern** | Task→XOR→Task (cycle) | External automation | 20% | High |
| **Multi-Instance** | Task[0..*] | Clone steps | 40% | High |
| **Deferred Choice** | →Event XOR→[Timer⎮Message] | Approval with timeout | 40% | High |
| **Milestone** | Intermediate events | Status checkpoints | 50% | Medium |
| **Cancel Region** | Transaction + Cancel | Cannot map | 0% | - |
| **Compensation** | Task + Compensation | Manual rollback | 20% | High |
| **Event Subprocess** | Error→Subprocess | Cannot map | 0% | - |

## Field Type Mappings

### BPMN Form to Tallyfy Capture

| BPMN Form Type | Tallyfy Capture | Validation | Transformation |
|----------------|-----------------|------------|----------------|
| String | text | max 200 chars | Truncate if needed |
| Text | textarea | max 30,000 chars | Direct |
| Integer | text | numeric validation | Add validation |
| Decimal | text | decimal validation | Add validation |
| Boolean | radio | Yes/No options | Convert to radio |
| Date | date | date picker | Direct |
| DateTime | date | date only | Lose time component |
| Enumeration | dropdown | single select | Direct |
| Multi-Enum | multiselect | multiple select | Direct |
| File | file | file upload | Direct |
| User | assignees_form | user picker | Direct |
| Email | email | email validation | Direct |
| URL | text | URL validation | Add validation |
| Currency | text | numeric + prefix | Add $ prefix |
| Percentage | text | numeric + suffix | Add % suffix |
| Grid/Table | table | table entry | Direct |
| Complex Object | textarea | JSON string | Serialize |

## Automation Mappings

### BPMN Expressions to Tallyfy Rules

| BPMN Expression | Tallyfy Condition | Example | AI Needed |
|-----------------|-------------------|---------|-----------|
| `${var == value}` | equals | field equals "approved" | No |
| `${var != value}` | not_equals | field not_equals "rejected" | No |
| `${var > value}` | greater_than | amount greater_than 1000 | No |
| `${var < value}` | less_than | days less_than 5 | No |
| `${var >= value}` | greater_than or equals | Complex: 2 rules | Yes |
| `${var <= value}` | less_than or equals | Complex: 2 rules | Yes |
| `${var.contains(str)}` | contains | field contains "urgent" | No |
| `${var.isEmpty()}` | is_empty | field is_empty | No |
| `${var1 && var2}` | AND condition | Multiple conditions | No |
| `${var1 || var2}` | OR condition | Multiple rules | Yes |
| `${complex expression}` | Cannot map | Manual configuration | Yes |

## Migration Confidence Matrix

### By BPMN Complexity

| Complexity Level | Elements | Tallyfy Success Rate | AI Impact | Manual Work |
|------------------|----------|---------------------|-----------|-------------|
| **Simple** | Sequential tasks, basic XOR | 90-100% | +5% | 0-1 hour |
| **Moderate** | Parallel, lanes, forms | 60-80% | +15% | 2-4 hours |
| **Complex** | Multiple gateways, events | 30-50% | +20% | 4-8 hours |
| **Very Complex** | Loops, compensation, events | 10-20% | +10% | 8-16 hours |
| **Impossible** | Event subprocess, transactions | 0% | 0% | Full redesign |

### By Element Category

| Category | Total Elements | Fully Supported | Partial | Unsupported |
|----------|---------------|-----------------|---------|-------------|
| **Events** | 63 types | 5 (8%) | 20 (32%) | 38 (60%) |
| **Tasks** | 20 types | 6 (30%) | 8 (40%) | 6 (30%) |
| **Gateways** | 15 configs | 3 (20%) | 5 (33%) | 7 (47%) |
| **Data** | 9 types | 4 (44%) | 3 (33%) | 2 (23%) |
| **Flows** | 5 types | 3 (60%) | 2 (40%) | 0 (0%) |
| **Overall** | 112 total | 21 (19%) | 38 (34%) | 53 (47%) |

## AI Decision Points

### Where AI Adds Most Value

| Decision Type | Context | AI Benefit | Example |
|--------------|---------|------------|---------|
| **Gateway Optimization** | Complex conditions | HIGH | Simplify nested conditions |
| **Pattern Recognition** | Common workflows | HIGH | Identify approval patterns |
| **Field Mapping** | Ambiguous types | MEDIUM | Map custom fields |
| **Event Transformation** | Event handling | HIGH | Convert to appropriate task type |
| **Loop Detection** | Cycle analysis | HIGH | Suggest external automation |
| **Process Splitting** | Multiple pools | HIGH | Determine template boundaries |
| **Role Mapping** | Lane assignments | MEDIUM | Consolidate similar roles |
| **Deadline Calculation** | Timer events | MEDIUM | Convert to task deadlines |
| **Message Routing** | Message flows | HIGH | Design webhook strategy |
| **Error Handling** | Exception flows | HIGH | Create fallback paths |

## Implementation Priority

### Phase 1: Core Support (MVP)
1. Sequential user tasks (95% confidence)
2. Simple XOR gateways (90% confidence)
3. Basic lanes/roles (90% confidence)
4. Simple forms (85% confidence)
5. None start/end events (100% confidence)

### Phase 2: Extended Support
1. Parallel gateways - visual (70% confidence)
2. Timer events as deadlines (70% confidence)
3. Message tasks as emails (85% confidence)
4. Service tasks as webhooks (70% confidence)
5. Data objects as fields (80% confidence)

### Phase 3: AI-Enhanced
1. Complex gateway simplification
2. Multi-instance handling
3. Event-based gateway transformation
4. Loop detection and reporting
5. Process optimization suggestions

### Phase 4: Never Support
1. Event subprocesses
2. Compensation flows
3. Transaction boundaries
4. Complex gateways
5. True parallel synchronization

## Summary Statistics

- **Total BPMN Elements**: 112 distinct types
- **Fully Mappable**: 21 (19%)
- **Partially Mappable**: 38 (34%)
- **Not Mappable**: 53 (47%)
- **AI Improves**: ~15-20% of partial mappings
- **Manual Work Required**: 70-80% of migrations
- **Realistic Automation**: 20-30% of process

This mapping matrix shows that while BPMN is incredibly rich with 112+ element variations, Tallyfy's simpler model can only directly support about 19% of these, with another 34% requiring transformation and manual work.