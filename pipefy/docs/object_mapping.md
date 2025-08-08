# Pipefy to Tallyfy Object Mapping

## Executive Summary
This document provides comprehensive field-level mapping between Pipefy and Tallyfy objects for migration. Due to fundamental architectural differences (Kanban vs Checklist), some mappings require creative transformation strategies.

## ⚠️ Critical Architecture Differences

| Aspect | Pipefy | Tallyfy | Impact |
|--------|--------|---------|--------|
| **Model** | Kanban Board (Cards in Phases) | Sequential Checklist | Major paradigm shift |
| **Flow** | Cards move between phases | Tasks complete in sequence | Different progress model |
| **Data** | Database tables for structured data | No native database | External storage needed |
| **View** | Visual board with columns | List-based interface | UX change |

## 1. Organization Mapping

### Pipefy Organization → Tallyfy Organization
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_id | Store original | Reference only |
| name | name | Direct | Required |
| slug | slug | Validate uniqueness | Must be unique |
| created_at | created_at | Direct | Timestamp |
| billing_period | billing_profile | Map billing data | Via organization_billing |
| members_count | - | Calculate | Count org_users |
| pipes_count | - | Calculate | Count checklists |
| tables_count | - | Track externally | No equivalent |
| industry | metadata.industry | Store in metadata | Custom field |
| locale | timezone | Map locale to TZ | Default: UTC |

## 2. Pipe (Workflow) Mapping

### Pipefy Pipe → Tallyfy Checklist Template
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_ref | Store original | For tracking |
| name | title | Direct | Required |
| description | description | Direct | Optional |
| phases[] | steps[] | Complex transformation | See Phase Mapping |
| start_form_fields[] | captures[] | Field mapping | Initial form |
| labels[] | tags[] | Direct | Categorization |
| members[] | participants[] | User mapping | Access control |
| public | is_public | Direct | Boolean |
| anyone_can_create_card | config.public_submission | Direct | Boolean |
| expiration_time_by_unit | config.sla | Convert to minutes | SLA tracking |
| expiration_unit | - | Used in conversion | hour/day/month |
| created_at | created_at | Direct | Timestamp |
| updated_at | updated_at | Direct | Timestamp |
| icon | icon | Map icon names | Limited set |
| color | color | Direct hex | Color code |
| preferences | config | JSON mapping | Settings |

### Critical Transformation: Phases to Steps
Since Pipefy phases are containers for cards, not sequential steps, we must transform each phase into a group of steps:

```
Pipefy Phase "Review" with 3 fields becomes:
→ Tallyfy Step Group "Review" containing:
  - Step 1: "Enter Review Phase" (notification)
  - Step 2: "Complete Review Fields" (form with 3 captures)
  - Step 3: "Move to Next Phase" (decision)
```

## 3. Phase Mapping

### Pipefy Phase → Tallyfy Step Group
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_ref | Store original | Reference |
| name | title | Prefix with "Phase: " | Clear identification |
| description | description | Direct | Optional |
| cards_count | - | Informational only | No equivalent |
| cards_can_be_moved_to_phases[] | dependencies[] | Map phase flow | Step dependencies |
| done | task_type | Map to 'approval' if done | Completion marker |
| fields[] | captures[] | Field mapping | Phase-specific fields |
| can_receive_card_directly | config.entry_point | Boolean | Can start here |
| sla | deadline_config | Convert to deadline | Time limits |
| index | position | Multiply by 10 | Allow sub-steps |

## 4. Card (Instance) Mapping

### Pipefy Card → Tallyfy Process/Run
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_ref | Store original | Reference |
| title | title | Direct | Required |
| pipe_id | checklist_id | Map pipe to checklist | Required FK |
| current_phase_id | current_step_id | Map phase to step group | Progress tracking |
| assignees[] | participants[] | User mapping | Multiple assignees |
| labels[] | tags[] | Direct | Categorization |
| due_date | deadline | Direct | Nullable date |
| created_at | created_at | Direct | Timestamp |
| updated_at | updated_at | Direct | Timestamp |
| finished_at | completed_at | Direct | Nullable timestamp |
| expired | metadata.expired | Store as flag | Boolean |
| late | metadata.late | Store as flag | Boolean |
| done | status | Map to 'completed' | Boolean to status |
| fields[] | capture_values[] | Field value mapping | Form data |
| comments[] | comments[] | Direct with user map | Collaboration |
| attachments[] | attachments[] | File migration | S3 upload |
| phases_history[] | audit_trail[] | Track movement | History |
| child_relations[] | metadata.child_cards | Store references | Relationships |
| parent_relations[] | metadata.parent_cards | Store references | Relationships |

### Status Mapping
| Pipefy State | Tallyfy Status | Notes |
|-------------|----------------|-------|
| In any phase (not done) | active | Card is in progress |
| done = true | completed | Card is finished |
| expired = true | overdue | Past due date |
| cancelled (via deletion) | cancelled | Soft delete |

## 5. Field Mapping

### Pipefy Field → Tallyfy Capture
| Pipefy Type | Tallyfy Type | Transformation | Notes |
|-------------|--------------|----------------|-------|
| short_text | text | Direct | Single line |
| long_text | textarea | Direct | Multi-line |
| number | number | Direct | Numeric |
| currency | number | Add currency symbol | Format as currency |
| percentage | number | Store as decimal | Display as % |
| date | date | Format ISO 8601 | Date only |
| datetime | datetime | Format ISO 8601 | Date and time |
| due_date | date | Add to deadline logic | Special handling |
| email | email | Direct with validation | Email format |
| phone | phone | Direct | Phone format |
| select | select | Map options | Single choice |
| radio | radio | Map options | Single choice |
| checkbox | multiselect | Map options | Multiple choice |
| checklist | multiselect | Convert to options | Multiple choice |
| attachment | file | File migration | S3 upload |
| assignee_select | user | User mapping | Organization users |
| label_select | select | Convert labels to options | Tag selection |
| connector | text | Store pipe/card reference | No direct equivalent |
| statement | text | Read-only text | Display only |
| time | text | Format as HH:MM | No time type |
| cpf/cnpj | text | Brazilian ID with validation | Custom validation |
| formula | text | Store formula result | No calculation engine |
| dynamic_content | text | Store rendered content | No dynamic fields |

### Field Properties Mapping
| Pipefy Property | Tallyfy Property | Transformation |
|-----------------|------------------|----------------|
| label | label | Direct |
| description | help_text | Direct |
| required | is_required | Direct |
| editable | is_editable | Direct |
| options | options | Map option objects |
| default_value | default_value | Type-specific |
| custom_validation | validation_rules | Limited support |
| sync_with_card | metadata.sync | Flag only |
| minimal_view | config.minimal | Display hint |
| unique | validation.unique | Enforcement varies |

## 6. Table (Database) Mapping

### ⚠️ Critical Limitation: No Direct Equivalent
Pipefy Tables have no direct equivalent in Tallyfy. Migration strategies:

| Strategy | Implementation | Pros | Cons |
|----------|---------------|------|------|
| **External Database** | Store in PostgreSQL/MySQL | Full functionality | Requires integration |
| **CSV Export** | Static snapshot | Simple | No updates |
| **Custom Fields** | Flatten to process fields | Native storage | Limited structure |
| **API Integration** | Keep in Pipefy, access via API | No migration needed | Dependency remains |

### Pipefy Table → External Storage
| Pipefy Field | Storage Field | Notes |
|--------------|---------------|-------|
| id | table_id | Primary key |
| name | table_name | Unique identifier |
| title_field | primary_field | Display field |
| fields[] | columns[] | Schema definition |
| records[] | rows[] | Data records |
| public | access_level | Permission model |

## 7. Automation Mapping

### Pipefy Automation → Tallyfy Rules + Webhooks
| Pipefy Component | Tallyfy Equivalent | Transformation | Notes |
|------------------|-------------------|----------------|-------|
| **Triggers** | | | |
| when_card_created | process_started | Webhook on process creation | Different event model |
| when_card_moved | step_completed | Track step completion | Phase movement |
| when_field_updated | capture_updated | Field change webhook | Limited support |
| when_card_done | process_completed | Completion webhook | Status change |
| when_card_expired | - | No direct equivalent | Custom monitoring |
| when_email_received | - | No email trigger | External integration |
| **Actions** | | | |
| move_card_to_phase | complete_step | Progress to next step | Sequential only |
| update_field | update_capture | API call required | Via webhook |
| create_card | create_process | Trigger new process | Via API |
| send_email | send_notification | Email via template | Different template system |
| create_table_record | - | No database support | External system |
| delete_card | cancel_process | Soft delete only | Status change |

### Complex Automation Transformation Example
```
Pipefy: "When card moves to 'Approved' phase, update status field to 'approved' and send email"
↓
Tallyfy:
1. Create "Approved" step group
2. Add webhook on step completion
3. Webhook calls external service to:
   - Update capture value via API
   - Send email via email service
```

## 8. User & Permission Mapping

### Pipefy User → Tallyfy User
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_id | Store original | Reference |
| name | first_name + last_name | Split name | Parse required |
| email | email | Direct | Unique key |
| username | username | Direct if available | Optional |
| avatar_url | avatar | Direct URL | Image migration optional |
| created_at | created_at | Direct | Timestamp |
| locale | settings.language | Map locale | Default: en |
| time_zone | timezone | Direct | User preference |

### Role Mapping
| Pipefy Role | Tallyfy Role | Permissions | Notes |
|-------------|--------------|-------------|-------|
| Admin | admin | Full access | Organization admin |
| Member | member | Standard access | Default role |
| Guest | light | Limited access | Restricted features |
| Normal (Pipe-specific) | member | Pipe access only | Checklist permissions |

## 9. Connection/Relation Mapping

### Pipefy Card Relations → Process Links
| Pipefy Relation | Tallyfy Implementation | Notes |
|-----------------|------------------------|-------|
| parent_relations | metadata.parent_process | Store process IDs |
| child_relations | metadata.child_processes | Store process IDs |
| connected_cards | metadata.connected_processes | Cross-references |
| pipe_relations | metadata.related_checklists | Template connections |

### Implementation Strategy
Since Tallyfy doesn't have native card connections:
1. Store relationships in metadata/custom fields
2. Create webhook handlers for relationship events
3. Use external service to maintain relationship graph
4. Display via custom dashboard/reporting

## 10. Label Mapping

### Pipefy Label → Tallyfy Tag
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_ref | Store original | Reference |
| name | name | Direct | Required |
| color | color | Hex color code | Visual indicator |

## 11. Comment/Activity Mapping

### Pipefy Comment → Tallyfy Comment
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_ref | Store original | Reference |
| text | body | Direct | Required |
| created_at | created_at | Direct | Timestamp |
| author_id | user_id | User mapping | Required FK |
| card_id | process_id | Card to process mapping | Context |

## 12. Webhook Mapping

### Pipefy Webhook → Tallyfy Webhook
| Pipefy Field | Tallyfy Field | Transformation | Notes |
|--------------|---------------|----------------|-------|
| id | external_ref | Store original | Reference |
| name | name | Direct | Identifier |
| url | endpoint_url | Direct | Required |
| email | - | No email webhooks | Use email service |
| headers | headers | JSON object | Authentication |
| actions[] | events[] | Map action types | Event triggers |

## Migration Complexity Matrix

| Object Type | Complexity | Risk | Critical Issues |
|------------|------------|------|-----------------|
| Organizations | Low | Low | Straightforward mapping |
| Users | Low | Low | Simple field mapping |
| Pipes | **High** | High | Phase paradigm shift |
| Phases | **Critical** | Very High | Container vs sequential |
| Cards | High | Medium | Status and phase tracking |
| Fields | Medium | Low | Most types supported |
| **Tables** | **Critical** | Very High | No equivalent - external required |
| **Automations** | **Critical** | High | Different trigger model |
| Connections | High | High | No native support |
| Comments | Low | Low | Direct mapping |
| Files | Medium | Medium | Size limits differ |
| Webhooks | Medium | Medium | Event model differs |

## Data Volume Considerations

### Pipefy Limits
- **Cards per pipe**: Unlimited (practical: 100,000+)
- **Fields per card**: 500+
- **File size**: 512MB per file
- **API pagination**: 50 items max

### Tallyfy Limits
- **Processes per checklist**: Unlimited
- **Steps per checklist**: Recommended < 100
- **Captures per process**: Practical limit ~1000
- **File size**: 100MB typical

### Migration Batching Strategy
```
Organizations: Sequential (1 at a time)
Users: Batches of 100
Pipes: Batches of 10 (complex transformation)
Cards: Batches of 20 (with field data)
Files: Parallel upload (4 workers)
Tables: External bulk insert (1000 records/batch)
```

## Special Considerations

### 1. Phase Movement Tracking
- Create audit trail for phase transitions
- Store phase history in process metadata
- Use webhooks to track movement patterns

### 2. SLA and Time Tracking
- Pipefy SLA → Tallyfy deadline configuration
- Implement external time tracking service
- Create reports for SLA compliance

### 3. Database Table Replacement
Options in order of preference:
1. **Airtable Integration**: Similar UX to Pipefy tables
2. **PostgreSQL + Retool**: Full control and custom UI
3. **Google Sheets API**: Simple but limited
4. **Keep in Pipefy**: Access via API when needed

### 4. Automation Engine Replacement
Since Tallyfy's automation is limited:
1. **Zapier/Make**: For simple automations
2. **n8n**: Self-hosted automation
3. **Custom webhooks**: Build specific integrations
4. **Keep some in Pipefy**: Complex automations via API

### 5. Reporting and Analytics
- Pipefy reports → External BI tool (Metabase, Tableau)
- Export data regularly for analysis
- Build custom dashboards for KPIs

## Migration Order of Operations

### Phase 1: Foundation (2-4 hours)
1. Organizations
2. Users and roles
3. Labels/Tags

### Phase 2: Structure (4-8 hours)
1. Pipes → Checklists (complex transformation)
2. Phases → Step groups
3. Fields → Captures
4. Start forms

### Phase 3: Data Migration (8-16 hours)
1. Active cards → Processes
2. Field values → Capture data
3. Card relationships (metadata)
4. Comments and activity

### Phase 4: External Systems (4-8 hours)
1. Database tables → External storage
2. Complex automations → Webhook handlers
3. Reports → BI tool setup

### Phase 5: Files & Integration (2-4 hours)
1. Attachments → S3
2. Webhooks
3. Email templates

### Phase 6: Validation (2-4 hours)
1. Data integrity checks
2. Permission verification
3. Process flow testing
4. User acceptance testing

## Risk Mitigation

### High-Risk Areas
1. **Database Tables**: Requires external solution before migration
2. **Phase-based workflow**: Users need retraining
3. **Automations**: May need rebuild from scratch
4. **Card connections**: Loss of visual relationships

### Mitigation Strategies
1. **Pilot Migration**: Test with one pipe first
2. **Parallel Run**: Keep Pipefy active during transition
3. **External Tools Ready**: Database and automation solutions deployed first
4. **User Training**: Extensive training on paradigm shift
5. **Fallback Plan**: Keep Pipefy data for 90 days minimum