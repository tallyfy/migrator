# Process Street to Tallyfy Object Mapping

## Executive Summary
This document provides a comprehensive mapping between Process Street and Tallyfy objects for migration purposes. Each mapping includes field-level details, transformation requirements, and special considerations.

## 1. Organization/Workspace Mapping

### Process Street: Organization → Tallyfy: Organization
| Process Street Field | Tallyfy Field | Transformation | Notes |
|---------------------|---------------|----------------|-------|
| id | external_id | Store original | Map to organizations.external_id |
| name | name | Direct | Required field |
| subdomain | slug | Lowercase, validate uniqueness | Must be unique |
| created_at | created_at | Direct | Timestamp conversion |
| updated_at | updated_at | Direct | Timestamp conversion |
| timezone | timezone | Direct | Default: UTC |
| billing_plan | billing_profile | Map plan types | Via organization_billing |
| user_count | - | Calculate | Count org_users |
| workflow_count | - | Calculate | Count checklists |

## 2. Template/Workflow Mapping

### Process Street: Workflow (Template) → Tallyfy: Checklist (Template)
| Process Street Field | Tallyfy Field | Transformation | Notes |
|---------------------|---------------|----------------|-------|
| id | external_ref | Store original | For reference |
| name | title | Direct | Required |
| description | description | Direct | Optional |
| tasks[] | steps[] | Complex mapping | See task mapping |
| owner_id | created_by | User ID mapping | Link to users |
| created_at | created_at | Direct | Timestamp |
| updated_at | updated_at | Direct | Timestamp |
| active | is_active | Direct | Boolean |
| public | is_public | Direct | Boolean default false |
| folder | category | Create/map categories | Via checklist_categories |
| form_fields[] | captures[] | Complex mapping | See form field mapping |
| approvals[] | - | Map to task type | approval_task type |
| stop_tasks[] | - | Map to task config | blocking: true |
| conditional_logic | rules | JSON transformation | Store in checklist_rules |
| webhooks[] | webhooks[] | API endpoint mapping | Via checklist_webhooks |

## 3. Instance/Run Mapping

### Process Street: Workflow Run (Checklist) → Tallyfy: Process (Run)
| Process Street Field | Tallyfy Field | Transformation | Notes |
|---------------------|---------------|----------------|-------|
| id | external_ref | Store original | For tracking |
| workflow_id | checklist_id | Template mapping | Required FK |
| name | title | Direct | From template + identifier |
| status | status | Map statuses | active/completed/cancelled |
| created_at | created_at | Direct | Timestamp |
| updated_at | updated_at | Direct | Timestamp |
| completed_at | completed_at | Direct | Nullable timestamp |
| created_by | created_by | User mapping | FK to users |
| task_data[] | step_instances[] | Complex mapping | See step instance mapping |
| form_values[] | capture_values[] | Data transformation | JSON storage |
| assignees[] | participants[] | User mapping | Via process_participants |
| due_date | deadline | Direct | Nullable date |
| progress | progress_percentage | Calculate | Based on completed steps |

## 4. Task/Step Mapping

### Process Street: Task → Tallyfy: Step
| Process Street Field | Tallyfy Field | Transformation | Notes |
|---------------------|---------------|----------------|-------|
| id | external_ref | Store original | Reference |
| title | title | Direct | Required |
| description | description | HTML to Markdown | Content transformation |
| type | task_type | Map types | normal/approval/form/decision |
| position | position | Direct | Integer ordering |
| required | is_required | Direct | Boolean |
| assignee_type | assignment_type | Map types | specific/role/dynamic |
| assignee | assigned_to | User/role mapping | Complex logic |
| due_date_config | deadline_config | JSON transform | Dynamic dates |
| form_fields[] | fields[] | Field mapping | Nested in step_forms |
| approval_config | approval_settings | JSON transform | For approval type |
| stop_task | blocking | Boolean flag | Blocks progress |
| conditional_show | visibility_rules | Rule mapping | JSON conditions |
| dependencies[] | dependencies[] | Task ID mapping | Via step_dependencies |

## 5. Form Field Mapping

### Process Street: Form Field → Tallyfy: Capture Field
| Process Street Type | Tallyfy Type | Transformation | Notes |
|--------------------|--------------|----------------|-------|
| text | text | Direct | Single line |
| textarea | textarea | Direct | Multi-line |
| email | email | Direct with validation | Email format |
| url | url | Direct with validation | URL format |
| date | date | Format conversion | ISO 8601 |
| dropdown | select | Options mapping | Single choice |
| multichoice | multiselect | Options mapping | Multiple choice |
| file | file | S3 migration | File storage |
| member | user | User ID mapping | Organization users |
| table | table | Complex JSON | Nested structure |

### Field Properties Mapping
| Process Street | Tallyfy | Transformation |
|----------------|---------|----------------|
| label | label | Direct |
| placeholder | placeholder | Direct |
| help_text | help_text | Direct |
| required | is_required | Direct |
| default_value | default_value | Type-specific |
| validation | validation_rules | JSON rules |
| conditional_logic | visibility_rules | Rule engine |

## 6. User & Permission Mapping

### Process Street: User → Tallyfy: User
| Process Street Field | Tallyfy Field | Transformation | Notes |
|---------------------|---------------|----------------|-------|
| id | external_id | Store original | Reference |
| email | email | Direct | Unique key |
| first_name | first_name | Direct | Required |
| last_name | last_name | Direct | Required |
| role | role | Map roles | See role mapping |
| groups[] | groups[] | Group mapping | Via user_groups |
| created_at | created_at | Direct | Timestamp |
| active | is_active | Direct | Boolean |
| avatar_url | avatar | URL storage | S3 migration |

### Role Mapping
| Process Street Role | Tallyfy Role | Permissions |
|--------------------|--------------|-------------|
| Admin | admin | Full access |
| Manager | admin | Full access |
| Member | member | Standard access |
| Guest | light | Limited access |
| Anonymous Guest | guest | External access |

## 7. Group/Team Mapping

### Process Street: Group → Tallyfy: Group
| Process Street Field | Tallyfy Field | Transformation |
|---------------------|---------------|----------------|
| id | external_ref | Store original |
| name | name | Direct |
| description | description | Direct |
| members[] | members[] | User ID mapping |
| created_at | created_at | Direct |

## 8. Comment/Activity Mapping

### Process Street: Comment → Tallyfy: Comment
| Process Street Field | Tallyfy Field | Transformation |
|---------------------|---------------|----------------|
| id | external_ref | Store original |
| content | body | HTML to Markdown |
| author_id | user_id | User mapping |
| task_id | step_id | Step mapping |
| created_at | created_at | Direct |
| attachments[] | attachments[] | File migration |

## 9. File Attachment Mapping

### Process Street: File → Tallyfy: Attachment
| Process Street Field | Tallyfy Field | Transformation |
|---------------------|---------------|----------------|
| id | external_ref | Store original |
| filename | filename | Direct |
| size | size | Direct |
| mime_type | mime_type | Direct |
| url | s3_key | S3 migration |
| uploaded_by | uploaded_by | User mapping |
| uploaded_at | created_at | Direct |

## 10. Webhook Mapping

### Process Street: Webhook → Tallyfy: Webhook
| Process Street Field | Tallyfy Field | Transformation |
|---------------------|---------------|----------------|
| id | external_ref | Store original |
| url | endpoint_url | Direct |
| events[] | events[] | Event mapping |
| active | is_active | Direct |
| secret | secret | Encryption |
| headers | headers | JSON |

## Transformation Complexity Matrix

| Object Type | Complexity | Critical Fields | Risk Areas |
|------------|------------|-----------------|------------|
| Organization | Low | name, subdomain | Subdomain conflicts |
| Templates | High | steps, forms, logic | Complex nesting |
| Instances | High | state, progress | Data consistency |
| Tasks | Medium | types, assignments | Type mapping |
| Forms | High | field types, data | Data validation |
| Users | Low | email, roles | Duplicate handling |
| Files | Medium | storage, URLs | S3 migration |
| Comments | Low | content, threading | Format conversion |
| Webhooks | Medium | endpoints, events | Event mapping |

## Special Considerations

### 1. Data Integrity
- Maintain referential integrity during migration
- Preserve timestamps and audit trails
- Handle orphaned records gracefully

### 2. ID Mapping Strategy
- Store Process Street IDs in external_ref fields
- Create mapping tables for complex relationships
- Generate new Tallyfy IDs (32-char hashes)

### 3. Content Migration
- Convert HTML content to Markdown where needed
- Preserve formatting and links
- Handle embedded images and files

### 4. Permission Migration
- Map Process Street permissions to Tallyfy matrix
- Handle role-based access control
- Preserve sharing settings

### 5. File Storage
- Download files from Process Street
- Upload to Tallyfy S3 buckets
- Update all file references

### 6. Conditional Logic
- Transform Process Street rules to Tallyfy format
- Test all conditions post-migration
- Document any unsupported features

### 7. Integration Points
- Remap webhook endpoints
- Update API integrations
- Test all external connections

## Migration Order of Operations

1. **Phase 1: Foundation**
   - Organizations
   - Users
   - Groups

2. **Phase 2: Templates**
   - Workflows → Checklists
   - Tasks → Steps
   - Form Fields → Captures

3. **Phase 3: Active Data**
   - Workflow Runs → Processes
   - Task States → Step Instances
   - Form Values → Capture Data

4. **Phase 4: Collaborative Data**
   - Comments
   - Files/Attachments
   - Activity History

5. **Phase 5: Integrations**
   - Webhooks
   - API Connections
   - External References

## Validation Checklist

- [ ] All organizations mapped with unique slugs
- [ ] All users imported with correct roles
- [ ] Templates preserve all task structures
- [ ] Form fields maintain data types
- [ ] Active runs maintain correct state
- [ ] Files successfully migrated to S3
- [ ] Comments linked to correct entities
- [ ] Permissions properly configured
- [ ] Webhooks tested and functional
- [ ] No data loss or corruption

## Risk Mitigation

1. **Data Loss Prevention**
   - Full backup before migration
   - Incremental migration approach
   - Rollback procedures ready

2. **Validation Strategy**
   - Automated validation scripts
   - Manual spot checks
   - User acceptance testing

3. **Performance Optimization**
   - Batch processing for large datasets
   - Parallel processing where possible
   - Progress tracking and resumability