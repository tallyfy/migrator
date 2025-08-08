# Pipefy to Tallyfy Mapping Analysis

## Executive Summary

This document provides a comprehensive analysis of how Pipefy's Kanban-based workflow system maps to Tallyfy's checklist/process model. While both platforms manage workflows, they have fundamentally different architectural approaches that create both opportunities and challenges for migration.

**Key Architectural Differences:**
- **Pipefy**: Card-centric Kanban system with phases (visual workflow)
- **Tallyfy**: Template-instance checklist system with sequential steps (task-based workflow)

## 1. Core Conceptual Mapping

### Fundamental Model Comparison

| Pipefy Concept | Tallyfy Equivalent | Mapping Complexity | Notes |
|----------------|-------------------|-------------------|-------|
| **Organization** | Organization | Low | Direct mapping with tenant isolation |
| **Pipe** | Checklist Template | Medium | Conceptual shift from board to checklist |
| **Phase** | Step/Task Group | High | Phases are containers; steps are tasks |
| **Card** | Process/Run | High | Cards are instances moving through phases |
| **Card Field** | Capture/Form Field | Low | Similar field concept |
| **Database** | Custom Entity/Data Store | Very High | No direct equivalent - requires workaround |
| **Database Record** | External Data Reference | Very High | Must use custom fields or external storage |
| **Automation** | Rules/Webhooks | Medium | Different trigger/action model |
| **Connection** | Step Dependencies | Medium | Different relationship model |

## 2. Pipefy Card System → Tallyfy Process Model

### 2.1 Card-to-Process Transformation

**Pipefy Cards** represent work items that move through phases on a visual board. Each card is an instance of work with its own fields, assignees, and state.

**Tallyfy Processes** are instances of checklists with sequential tasks that must be completed.

#### Mapping Strategy:
```
Pipefy Card → Tallyfy Process (Run)
├── Card ID → process.external_ref
├── Card Title → process.name
├── Card Description → process.summary
├── Current Phase → Current active step(s)
├── Card Fields → Process-level captures
├── Card Assignees → Process participants
├── Card Labels → Process tags
├── Card Due Date → process.due_at
└── Card Attachments → Process assets
```

#### Key Challenges:
1. **Non-linear Movement**: Cards can skip phases; Tallyfy steps are typically sequential
2. **Phase Residence**: Cards "live" in phases; Tallyfy tasks are completed and move on
3. **Multiple Cards per Phase**: Pipefy allows many cards in one phase simultaneously
4. **Visual Board Loss**: No Kanban board visualization in Tallyfy

#### Solutions:
- Use conditional logic to enable phase skipping
- Create "holding" tasks that remain active while card is in phase
- Use process status and custom fields to track phase location
- Implement external dashboard for Kanban visualization

## 3. Pipefy Phases → Tallyfy Steps

### 3.1 Phase-to-Step Architecture

**Pipefy Phases** are columns on a Kanban board where cards reside until moved to the next phase.

**Tallyfy Steps** are individual tasks within a checklist that are completed sequentially.

#### Mapping Approach:

```
Option 1: Each Phase = Group of Steps
Pipefy Phase "In Review"
└── Tallyfy Steps:
    ├── "Enter Review Phase" (marker task)
    ├── "Review Document" (actual work)
    ├── "Approve/Reject" (decision task)
    └── "Exit Review Phase" (transition task)

Option 2: Each Phase = Single Long-Running Step
Pipefy Phase "In Progress"
└── Tallyfy Step: "Work in Progress" (remains active until phase complete)

Option 3: Hybrid Approach (Recommended)
Pipefy Phase
└── Tallyfy Implementation:
    ├── Phase Entry Task (auto-complete)
    ├── Phase Work Tasks (actual activities)
    └── Phase Exit/Transition Task (moves to next phase)
```

#### Phase Properties Mapping:

| Pipefy Phase Property | Tallyfy Implementation | Method |
|----------------------|------------------------|--------|
| Phase Name | Step Group Title | Prefix steps with phase name |
| Phase Order | Step Position | Sequential ordering |
| Phase Rules | Step Conditions | Conditional logic |
| Phase Fields | Step-specific Captures | Form fields on phase tasks |
| Phase SLA | Step Deadlines | Deadline configuration |
| Can Skip Phase | Conditional Steps | Visibility rules |
| Phase Automation | Step Webhooks/Rules | Automation triggers |

### 3.2 Phase Transitions

**Challenge**: Pipefy cards move between phases; Tallyfy tasks complete and proceed.

**Solution Architecture**:
```javascript
// Conceptual Implementation
1. Create "Phase Status" custom field on process
2. Use completion of phase-exit task to update status
3. Implement webhook to track phase transitions
4. Use conditional logic to activate next phase steps
```

## 4. Pipefy Fields → Tallyfy Captures

### 4.1 Field Type Mapping

| Pipefy Field Type | Tallyfy Capture Type | Transformation Required |
|-------------------|---------------------|------------------------|
| Short Text | text | Direct |
| Long Text | textarea | Direct |
| Number | number | Direct |
| Date | date | Direct |
| Date & Time | datetime | Direct |
| Dropdown Select | select | Direct |
| Radio Select | radio | Direct |
| Checkbox | checkbox | Direct |
| Checklist | multiselect | Transform to multi-select |
| Email | email | Direct |
| Phone | text | Add validation pattern |
| Currency | number | Add currency formatting |
| Attachment | file | Direct |
| Assignee | user | User mapping required |
| Label | select/multiselect | Convert to dropdown |
| Connection | text/reference | Store as external reference |
| Database Connection | text/JSON | Store connection data |
| Statement | text (readonly) | Display-only field |
| Time | text | Custom time format |
| CPF/CNPJ | text | Brazilian ID validation |

### 4.2 Field Scope Differences

**Pipefy Field Scopes:**
1. **Pipe Fields** - Available throughout the pipe
2. **Phase Fields** - Specific to a phase
3. **Start Form Fields** - Initial card creation

**Tallyfy Field Scopes:**
1. **Process Fields** - Checklist-level captures (like Pipe fields)
2. **Step Fields** - Task-specific captures (like Phase fields)
3. **Kickoff Form** - Process initiation fields (like Start form)

#### Mapping Strategy:
```
Pipefy Pipe Fields → Tallyfy Process-level Captures
Pipefy Phase Fields → Tallyfy Step-level Captures
Pipefy Start Form → Tallyfy Kickoff Form (prerun)
```

## 5. Pipefy Databases → Tallyfy Data Storage

### 5.1 Database Challenge

**Critical Gap**: Tallyfy has no direct equivalent to Pipefy's database tables for structured data storage.

**Pipefy Databases** are:
- Separate data tables with defined schemas
- Linkable to cards via connection fields
- Searchable and filterable
- Reusable across pipes

### 5.2 Workaround Strategies

#### Option 1: External Database Integration
```
Architecture:
1. Migrate Pipefy databases to external system (PostgreSQL/MySQL)
2. Create API integration layer
3. Use Tallyfy webhooks to query/update external data
4. Store references in Tallyfy custom fields
```

#### Option 2: Process Templates as Data Records
```
Architecture:
1. Create "Data Template" checklists for each database table
2. Each database record becomes a process instance
3. Use process fields to store record data
4. Implement search via API queries
```

#### Option 3: Custom Field Arrays (Limited)
```
Architecture:
1. Store database records as JSON in text fields
2. Limited to simple, low-volume data
3. No native querying capability
4. Suitable for reference data only
```

#### Recommended Approach:
**Hybrid Solution** - Critical databases in external system, reference data in Tallyfy fields

### 5.3 Database Connection Mapping

| Pipefy Feature | Tallyfy Implementation | Limitations |
|----------------|----------------------|-------------|
| Database Records | External API/Process Instances | No native database |
| Connection Fields | Reference Fields (IDs) | Manual lookup required |
| Database Views | External Dashboard | No native views |
| Database Filters | API Query Parameters | External implementation |
| Database Forms | Separate Input Forms | Disconnected from cards |

## 6. Pipefy Automations → Tallyfy Rules

### 6.1 Automation Type Mapping

| Pipefy Automation | Tallyfy Equivalent | Implementation Complexity |
|-------------------|-------------------|--------------------------|
| When card created | Process start webhook | Low |
| When card moved | Step completion trigger | Medium |
| When field updated | Field change webhook | Medium |
| When card expires | Task deadline trigger | Low |
| Email notifications | Email task type | Low |
| Create connected card | API call to create process | High |
| Update field value | Webhook to update capture | Medium |
| Move card | Complete step + activate next | High |
| Conditional actions | Conditional logic rules | Medium |
| SLA tracking | Deadline monitoring | Medium |

### 6.2 Automation Architecture Differences

**Pipefy Automations:**
- Event-driven triggers
- Multiple actions per trigger
- Complex condition builders
- Cross-pipe operations

**Tallyfy Rules/Webhooks:**
- Step-based triggers
- Webhook endpoints for complex logic
- Conditional step visibility
- Limited cross-process operations

### 6.3 Implementation Strategy

```javascript
// Pipefy Automation
{
  "trigger": "card.moved",
  "condition": "phase.id == 'review'",
  "actions": [
    "send_email",
    "update_field",
    "create_subtask"
  ]
}

// Tallyfy Implementation
{
  "step": {
    "title": "Move to Review",
    "on_complete": {
      "webhook": "https://integration.api/handle_review",
      "email_task": true,
      "update_captures": {...}
    }
  }
}
```

## 7. Permission & Role Mapping

### 7.1 Role Comparison

| Pipefy Role | Tallyfy Role | Permission Differences |
|-------------|--------------|----------------------|
| Organization Admin | Owner/Admin | Full access |
| Pipe Admin | Checklist Owner | Template management |
| Pipe Member | Member | Standard access |
| Organization Guest | Light User | Limited features |
| Company Guest | Guest | External limited access |

### 7.2 Permission Granularity

**Pipefy Permissions** (Pipe-level):
- Start cards
- View cards
- Edit cards
- Delete cards
- Move cards between phases
- View/edit specific fields

**Tallyfy Permissions** (Checklist/Process-level):
- CHECKLIST_READ
- CHECKLIST_EDIT
- PROCESS_LAUNCH
- PROCESS_READ
- Task assignments

**Gap Analysis:**
- Pipefy has more granular field-level permissions
- Tallyfy has simpler role-based model
- Phase-specific permissions in Pipefy have no direct equivalent

## 8. Pipe Connections → Process Dependencies

### 8.1 Connection Types

**Pipefy Connections:**
1. **Parent-Child Cards** - Hierarchical relationships
2. **Connected Pipes** - Cross-pipe workflows
3. **Database Connections** - Link to database records
4. **Card Mirroring** - Synchronized cards across pipes

**Tallyfy Dependencies:**
1. **Step Dependencies** - Task prerequisites
2. **Process Triggers** - Webhook-based process creation
3. **External References** - ID storage for external systems

### 8.2 Implementation Mapping

| Pipefy Connection | Tallyfy Implementation | Method |
|-------------------|----------------------|--------|
| Parent Card | Parent Process ID field | Store reference |
| Child Cards | Subprocess creation via API | Webhook triggers |
| Connected Pipe Card | Cross-checklist process | API integration |
| Database Record | External reference field | ID storage + API |
| Card Mirror | Synchronized processes | Webhook sync |

## 9. Fundamental Incompatibilities

### 9.1 Conceptual Gaps

1. **Kanban Board Visualization**
   - **Gap**: No visual board in Tallyfy
   - **Impact**: Loss of visual workflow management
   - **Mitigation**: External dashboard integration

2. **Database Tables**
   - **Gap**: No native database functionality
   - **Impact**: Cannot store structured reference data
   - **Mitigation**: External database required

3. **Card Movement Flexibility**
   - **Gap**: Cards can't freely move between phases
   - **Impact**: Less flexible workflow progression
   - **Mitigation**: Conditional logic and status fields

4. **Multiple Cards per Phase**
   - **Gap**: Phases aren't containers in Tallyfy
   - **Impact**: Cannot visualize WIP limits
   - **Mitigation**: Custom reporting

5. **Field-Level Permissions**
   - **Gap**: No granular field permissions
   - **Impact**: Less precise access control
   - **Mitigation**: Role-based workarounds

### 9.2 Feature Gaps

| Pipefy Feature | Tallyfy Gap | Business Impact | Workaround |
|----------------|-------------|-----------------|------------|
| Public forms | Limited public access | Lead capture impact | External form integration |
| Card templates | No card template concept | Slower card creation | Process templates |
| Batch operations | Limited bulk actions | Efficiency loss | API scripting |
| Advanced reporting | Basic reporting | Analytics limitations | External BI tools |
| Time tracking | No native time tracking | No effort metrics | Manual capture fields |
| Card relationships | Simple dependencies | Complex workflow issues | External tracking |
| Email piping | No email-to-card | Email integration loss | Webhook integration |

## 10. Migration Strategy Recommendations

### 10.1 Phased Approach

**Phase 1: Foundation**
```
1. Map organizations and users
2. Create role mappings
3. Establish permission matrix
4. Set up external database (if needed)
```

**Phase 2: Template Migration**
```
1. Convert Pipes to Checklist templates
2. Transform Phases to Step groups
3. Map fields to captures
4. Configure conditional logic
```

**Phase 3: Active Card Migration**
```
1. Convert active cards to processes
2. Map current phase to active steps
3. Migrate field values to captures
4. Preserve card relationships
```

**Phase 4: Automation Recreation**
```
1. Implement webhooks for automations
2. Configure step-based triggers
3. Set up external integrations
4. Test automation flows
```

**Phase 5: Database Migration**
```
1. Export database tables
2. Implement external storage
3. Create API integration
4. Update connection references
```

### 10.2 Critical Success Factors

1. **User Training**
   - Paradigm shift from Kanban to checklist
   - New navigation patterns
   - Different automation concepts

2. **Data Integrity**
   - Preserve all card data
   - Maintain relationships
   - Keep audit trails

3. **Business Continuity**
   - Parallel run period
   - Gradual transition
   - Rollback capability

4. **Integration Requirements**
   - External database for tables
   - Dashboard for visualization
   - API bridge for automations

## 11. Technical Implementation Guide

### 11.1 Data Transformation Pipeline

```python
# Conceptual transformation flow
class PipefyToTallyfyTransformer:
    
    def transform_pipe_to_checklist(self, pipe):
        """Convert Pipefy Pipe to Tallyfy Checklist"""
        return {
            'id': generate_tallyfy_id(),
            'external_ref': pipe['id'],
            'title': pipe['name'],
            'description': pipe['description'],
            'steps': self.transform_phases_to_steps(pipe['phases']),
            'captures': self.transform_pipe_fields(pipe['fields']),
            'prerun': self.transform_start_form(pipe['start_form'])
        }
    
    def transform_card_to_process(self, card, checklist_id):
        """Convert Pipefy Card to Tallyfy Process"""
        return {
            'id': generate_tallyfy_id(),
            'external_ref': card['id'],
            'checklist_id': checklist_id,
            'name': card['title'],
            'summary': card['description'],
            'status': self.map_card_status(card),
            'current_phase': card['current_phase']['name'],
            'captures': self.transform_card_fields(card['fields'])
        }
    
    def transform_phases_to_steps(self, phases):
        """Convert Phases to Step Groups"""
        steps = []
        for phase in phases:
            # Entry marker
            steps.append({
                'title': f"Enter {phase['name']}",
                'type': 'task',
                'auto_complete': True
            })
            # Phase work tasks
            steps.extend(self.create_phase_tasks(phase))
            # Exit transition
            steps.append({
                'title': f"Complete {phase['name']}",
                'type': 'approval',
                'triggers_next_phase': True
            })
        return steps
```

### 11.2 Migration Script Architecture

```python
# Migration orchestrator
class PipefyMigrationOrchestrator:
    
    def execute_migration(self, organization_id):
        """Main migration flow"""
        
        # 1. Fetch Pipefy data
        pipes = self.fetch_pipes(organization_id)
        databases = self.fetch_databases(organization_id)
        cards = self.fetch_all_cards(pipes)
        
        # 2. Create Tallyfy structures
        self.create_organization()
        self.migrate_users()
        
        # 3. Migrate templates
        checklist_map = {}
        for pipe in pipes:
            checklist = self.migrate_pipe_template(pipe)
            checklist_map[pipe['id']] = checklist['id']
        
        # 4. Migrate active cards
        for card in cards:
            self.migrate_card(card, checklist_map)
        
        # 5. Set up integrations
        self.configure_webhooks()
        self.setup_external_database(databases)
        
        # 6. Validate migration
        self.run_validation_checks()
```

## 12. Validation & Testing Requirements

### 12.1 Migration Validation Checklist

- [ ] All pipes converted to checklists
- [ ] All phases mapped to steps
- [ ] All cards converted to processes
- [ ] Field values preserved
- [ ] User assignments maintained
- [ ] Automations recreated
- [ ] Permissions correctly mapped
- [ ] Database references preserved
- [ ] File attachments migrated
- [ ] Comments/history preserved

### 12.2 Functional Testing Requirements

1. **Workflow Progression**
   - Test phase transitions
   - Verify conditional logic
   - Validate automations

2. **Data Integrity**
   - Verify field values
   - Check calculations
   - Validate relationships

3. **User Experience**
   - Test assignments
   - Verify notifications
   - Check permissions

4. **Integration Points**
   - Test webhooks
   - Verify external database
   - Check API connections

## 13. Risk Assessment

### 13.1 High-Risk Areas

1. **Database Migration** (Critical)
   - No native equivalent
   - Requires external solution
   - Data consistency risks

2. **Automation Complexity** (High)
   - Different trigger models
   - Complex logic translation
   - Testing requirements

3. **User Adoption** (High)
   - Paradigm shift
   - Training needs
   - Resistance to change

4. **Visual Workflow Loss** (Medium)
   - No Kanban board
   - Different navigation
   - Reporting changes

### 13.2 Mitigation Strategies

1. **Technical Mitigation**
   - Comprehensive testing
   - Parallel run period
   - Rollback procedures

2. **User Mitigation**
   - Training programs
   - Documentation
   - Support resources

3. **Business Mitigation**
   - Phased rollout
   - Pilot groups
   - Success metrics

## 14. Post-Migration Considerations

### 14.1 Optimization Opportunities

1. **Simplify Workflows**
   - Remove unnecessary phases
   - Consolidate steps
   - Streamline automations

2. **Enhance Reporting**
   - Implement dashboards
   - Create custom reports
   - Set up analytics

3. **Improve Integrations**
   - API enhancements
   - Webhook optimization
   - External tool connections

### 14.2 Long-term Maintenance

1. **Data Governance**
   - Archive old processes
   - Clean up test data
   - Maintain data quality

2. **Performance Monitoring**
   - Track system performance
   - Monitor user adoption
   - Measure efficiency gains

3. **Continuous Improvement**
   - Gather user feedback
   - Iterate on workflows
   - Optimize automations

## Conclusion

Migrating from Pipefy to Tallyfy requires significant architectural transformation due to fundamental differences in workflow paradigms. While both systems manage workflows, Pipefy's Kanban-based card system differs substantially from Tallyfy's checklist-based process model.

**Key Takeaways:**

1. **Feasible but Complex**: Migration is technically feasible but requires careful planning and potentially external systems for full feature parity.

2. **Database Challenge**: Pipefy's database functionality has no direct equivalent in Tallyfy, requiring external database integration.

3. **Paradigm Shift**: Users must adapt from visual Kanban boards to sequential checklist workflows.

4. **Automation Differences**: Automation logic must be restructured around Tallyfy's step-based trigger model.

5. **Visual Gap**: Loss of Kanban visualization requires external dashboards or reporting tools.

**Success Requirements:**
- Strong technical implementation team
- Comprehensive user training program
- External database and dashboard solutions
- Thorough testing and validation
- Phased migration approach
- Clear communication of changes

The migration is best suited for organizations willing to adapt their workflows to Tallyfy's checklist model and invest in external solutions for database and visualization needs.