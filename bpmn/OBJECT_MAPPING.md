# BPMN 2.0 to Tallyfy Object Mapping Guide

## Overview

This guide provides comprehensive mapping between BPMN 2.0 elements and Tallyfy constructs, documenting how BPMN diagrams transform into executable Tallyfy templates.

## Core Paradigm Shift

BPMN represents process models with complex notation including parallel gateways, message flows, and events. Tallyfy uses a simpler sequential/parallel step model with conditional rules. This migrator intelligently transforms BPMN complexity into Tallyfy's streamlined approach.

## Element Mappings

### Process Container Elements

| BPMN Element | Tallyfy Equivalent | API Name | Transformation Strategy |
|--------------|-------------------|----------|------------------------|
| **Process** | **Blueprint/Template** | `blueprint` | Main container for workflow |
| Pool | Organization/Template | `blueprint` | Each pool becomes separate template |
| Lane | Group/Role Assignment | `group` | Lanes map to user groups for assignment |
| Subprocess | Nested Steps/Sub-template | `steps[]` | Collapsed: reference; Expanded: inline steps |
| Ad-hoc Subprocess | Template with optional steps | `blueprint` | Steps marked as optional |
| Transaction | Template with rollback rules | `blueprint` | Add compensating tasks |

### Activity Elements (Tasks)

| BPMN Task Type | Tallyfy Step Type | Task Configuration | Notes |
|----------------|-------------------|-------------------|-------|
| **User Task** | **Task Step** | `task_type: 'task'` | Direct mapping for human tasks |
| Service Task | Automated Step | `task_type: 'webhook'` | Trigger external service via webhook |
| Manual Task | Task Step | `task_type: 'task'` | Human task without system support |
| Script Task | Webhook Step | `task_type: 'webhook'` | Execute via API call |
| Send Task | Email/Webhook Step | `task_type: 'email'` | Send notification or message |
| Receive Task | Approval Step | `task_type: 'approval'` | Wait for external input |
| Business Rule Task | Conditional Step | `rules[]` | Implement as conditional logic |
| Call Activity | Template Reference | `task_type: 'template_ref'` | Launch another template |

### Gateway Elements (Flow Control)

| BPMN Gateway | Tallyfy Implementation | Complexity | Transformation Logic |
|--------------|----------------------|------------|---------------------|
| **Exclusive (XOR)** | **Conditional Rules** | Simple | IF-THEN rules determine path |
| Parallel (AND) | Parallel Steps | Medium | Steps with same position run in parallel |
| Inclusive (OR) | Multiple Conditions | Complex | Multiple rules can activate paths |
| Event-based | Wait + Conditions | Complex | Approval step with timeout rules |
| Complex | AI-Assisted Rules | Very Complex | Use AI to determine best mapping |

### Event Elements

| BPMN Event | Tallyfy Equivalent | Implementation Strategy |
|------------|-------------------|------------------------|
| **Start Event** | **Template Trigger** | Define how template starts |
| None Start | Manual Start | User initiates template |
| Message Start | Webhook Trigger | API call starts template |
| Timer Start | Scheduled Start | External scheduler triggers |
| Signal Start | Webhook Trigger | External signal via API |
| **End Event** | **Template Completion** | Define completion behavior |
| None End | Simple Complete | Template marks as done |
| Message End | Webhook on Complete | Trigger external notification |
| Terminate End | Force Complete | Stop all parallel branches |
| Error End | Failed Status | Mark template as failed |
| **Intermediate Event** | **Step Behavior** | Mid-process events |
| Timer Intermediate | Deadline/Wait | Add deadline to step |
| Message Intermediate | Webhook Step | Wait for external message |
| Signal Intermediate | Conditional Wait | Pause until condition met |
| Escalation | Notification | Alert managers/escalate |

### Flow Elements

| BPMN Flow Type | Tallyfy Mapping | Notes |
|----------------|-----------------|-------|
| **Sequence Flow** | **Step Order** | Position determines sequence |
| Default Flow | Default Path | No conditions required |
| Conditional Flow | Rule-based Path | IF-THEN conditions |
| Message Flow | Webhook/Email | Cross-template communication |
| Association | Documentation | Add to step description |

### Data Elements

| BPMN Data Element | Tallyfy Field Type | Storage Location |
|-------------------|-------------------|------------------|
| **Data Object** | **Form Field** | Template/Step fields |
| Data Input | Input Field | Kick-off form field |
| Data Output | Output Field | Capture in step |
| Data Store | External Storage | Reference in description |
| Message | Email/Webhook Data | Pass via integration |

### Artifact Elements

| BPMN Artifact | Tallyfy Implementation | Purpose |
|---------------|----------------------|---------|
| **Text Annotation** | **Step Description** | Add context to steps |
| Group | Step Grouping | Visual organization |
| Image | Attachment | Add as file attachment |

## Gateway Transformation Patterns

### Exclusive Gateway (XOR)
```
BPMN: Task1 → XOR → [condition A] → Task2
                  → [condition B] → Task3

Tallyfy: Task1 → Rules: 
                  IF condition A THEN show Task2
                  IF condition B THEN show Task3
```

### Parallel Gateway (AND)
```
BPMN: Task1 → AND → Task2
                  → Task3
                  → Task4

Tallyfy: Task1 → [Task2, Task3, Task4] (same position, parallel execution)
```

### Inclusive Gateway (OR)
```
BPMN: Task1 → OR → [condition A] → Task2
                 → [condition B] → Task3
                 → [always] → Task4

Tallyfy: Task1 → Rules:
                  IF condition A THEN show Task2
                  IF condition B THEN show Task3
                  ALWAYS show Task4
```

## Complex Transformations

### Loops and Iterations

| BPMN Pattern | Tallyfy Solution | Implementation |
|--------------|------------------|----------------|
| Standard Loop | Repeat Template | External automation to re-run |
| Multi-Instance Sequential | Multiple Steps | Create step for each instance |
| Multi-Instance Parallel | Parallel Steps | Create parallel steps |
| Loop with Condition | Conditional Rules | Check condition after each iteration |

### Compensation and Transactions

| BPMN Feature | Tallyfy Approach | Notes |
|--------------|------------------|-------|
| Compensation Task | Rollback Step | Add as conditional step |
| Transaction Boundary | Template Boundary | Separate template for transaction |
| Cancel Event | Stop Template | Mark as cancelled with reason |
| Compensate Event | Trigger Rollback | Execute compensation steps |

### Boundary Events

| BPMN Boundary Event | Tallyfy Implementation | Behavior |
|--------------------|----------------------|----------|
| Timer Boundary | Step Deadline | Escalate on timeout |
| Error Boundary | Error Handling Rule | Catch and handle errors |
| Message Boundary | Webhook Listener | React to external message |
| Escalation Boundary | Escalation Rule | Trigger escalation flow |

## Field Type Mappings

| BPMN Data Type | Tallyfy Field Type | Validation |
|----------------|-------------------|------------|
| String | text/textarea | Length limits |
| Integer | number | Numeric validation |
| Boolean | radio | Yes/No options |
| Date | date | Date picker |
| DateTime | date | Date only (time in description) |
| Document | file | File upload |
| Complex Type | table | Grid/table field |

## Swimlane Transformation

### Pool → Template
- Each pool becomes a separate Tallyfy template
- Message flows between pools become webhooks/emails
- Pool name becomes template name
- Pool documentation becomes template description

### Lane → Role/Group
- Each lane maps to a Tallyfy group
- Tasks in lane assigned to corresponding group
- Lane name becomes group name
- Cross-lane flows maintain sequence

## AI-Assisted Decisions

The migrator uses AI for complex mappings:

### When AI is Used
1. **Complex Gateway Logic**: Multiple conditions with dependencies
2. **Event Patterns**: Complex event correlations
3. **Loop Structures**: Determining optimal loop implementation
4. **Data Transformations**: Complex data type mappings
5. **Subprocess Optimization**: Inline vs. separate template decisions

### AI Decision Points
- Gateway merge/split complexity assessment
- Optimal step grouping for readability
- Conditional logic simplification
- Parallel vs. sequential execution decisions
- Form field organization

## Limitations and Workarounds

### Not Directly Supported
| BPMN Feature | Workaround | Impact |
|--------------|------------|--------|
| Complex Event Correlation | Manual coordination | Requires human oversight |
| BPMN Transactions | Multiple templates | Split into smaller processes |
| Signal Broadcasting | Webhook to multiple | Use integration platform |
| Event Subprocess | Separate template | Link via automation |
| Non-interrupting Events | Parallel branch | Add as optional path |

### Partial Support
| BPMN Feature | Tallyfy Limitation | Solution |
|--------------|-------------------|----------|
| Timer Events | No native timers | Use external scheduler |
| Message Correlation | No correlation IDs | Track in form fields |
| Multi-Instance | Limited support | Create multiple steps |
| Compensation | Manual setup | Document rollback steps |

## Migration Strategies

### Simple Processes (Linear Flow)
- Direct step-by-step mapping
- Minimal transformation required
- High fidelity preservation

### Medium Complexity (Gateways + Events)
- Gateway logic to rules
- Events to triggers/webhooks  
- Some manual review needed

### Complex Processes (Multiple Pools, Events, Transactions)
- Split into multiple templates
- External orchestration layer
- Significant transformation
- AI assistance recommended

## Post-Migration Validation

### Required Checks
1. ✓ All tasks mapped to steps
2. ✓ Gateway logic preserved
3. ✓ Events properly triggered
4. ✓ Data flow maintained
5. ✓ Roles correctly assigned
6. ✓ Sequence flow accurate

### Common Adjustments
1. Simplify complex gateways
2. Convert events to webhooks
3. Restructure parallel flows
4. Add missing form fields
5. Configure external integrations
6. Set up timers/schedulers

## Best Practices

### BPMN Preparation
1. Simplify before migration
2. Document gateway conditions clearly
3. Name all elements descriptively
4. Remove unnecessary complexity
5. Validate BPMN syntax

### Migration Process
1. Start with simple processes
2. Test gateway transformations
3. Verify event mappings
4. Validate data flow
5. Review role assignments
6. Test parallel execution

### Post-Migration
1. Train users on differences
2. Document workarounds
3. Set up integrations
4. Monitor execution
5. Gather feedback
6. Iterate improvements

## Comparison URL
For detailed comparison: https://tallyfy.com/differences/bpmn-vs-tallyfy/