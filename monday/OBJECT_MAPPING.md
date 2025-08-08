# Monday.com to Tallyfy Object Mapping Guide

## Executive Summary

This document provides comprehensive mapping between Monday.com and Tallyfy objects, including terminology translations, paradigm shifts, and transformation strategies.

## Table of Contents

1. [Core Platform Concepts](#core-platform-concepts)
2. [Organizational Structure](#organizational-structure)
3. [Workflow Components](#workflow-components)
4. [Data Fields Mapping](#data-fields-mapping)
5. [User Management](#user-management)
6. [Permissions & Access](#permissions--access)
7. [Automation & Rules](#automation--rules)
8. [Views & Visualization](#views--visualization)
9. [Collaboration Features](#collaboration-features)
10. [Integration Points](#integration-points)

---

## Core Platform Concepts

### Fundamental Paradigm Shift

| Aspect | Monday.com | Tallyfy | Transformation Notes |
|--------|------------|---------|---------------------|
| **Core Model** | Flexible work OS with multiple views | Sequential workflow platform | Requires fundamental rethinking of work organization |
| **Work Organization** | Boards with customizable columns | Blueprints with defined steps | From flexible to structured |
| **Task Management** | Items in groups with statuses | Processes following steps | From status-based to step-based |
| **Visualization** | Multiple concurrent views (Table, Kanban, Timeline, etc.) | Single sequential flow | Loss of view flexibility, gain in process clarity |
| **Collaboration** | Updates on items | Comments on tasks | Similar but context changes |
| **Automation** | Recipe-based automations | Rule-based workflows | Different trigger/action model |

---

## Organizational Structure

### Workspace/Organization Mapping

| Monday.com | Tallyfy | Description | Migration Impact |
|------------|---------|-------------|------------------|
| **Account** | Organization | Top-level container | Direct mapping |
| **Workspace** | - | Workspace grouping | Flattened into organization |
| **Main Workspace** | Main Organization | Primary workspace | Becomes primary org |
| **Folders** | Blueprint Categories | Board organization | Becomes tags/categories |
| **Board** | Blueprint | Work template | Core transformation unit |
| **Item** | Process | Work instance | Running workflow |
| **Subitem** | Checklist Item | Nested task | Simplified to checklist |
| **Group** | Step Group/Phase | Board sections | Becomes workflow phases |

### Hierarchical Changes

```
Monday.com Hierarchy:
Account
  └── Workspace
      └── Folder
          └── Board
              └── Group
                  └── Item
                      └── Subitem

Tallyfy Hierarchy:
Organization
  └── Blueprint (with tags)
      └── Process
          └── Step
              └── Task
                  └── Checklist
```

---

## Workflow Components

### Board to Blueprint Transformation

| Monday Board Component | Tallyfy Blueprint Component | Transformation Logic |
|------------------------|----------------------------|---------------------|
| **Board Name** | Blueprint Name | Direct transfer |
| **Board Description** | Blueprint Description | Enhanced with migration notes |
| **Board Kind** (public/private/shareable) | Blueprint Visibility | Maps to organization/private |
| **Board Owner** | Blueprint Admin | User role mapping |
| **Board Permissions** | Blueprint Permissions | Simplified permission model |
| **Board Activity** | - | Not migrated (different model) |
| **Board Views** | - | Documented in description |
| **Board Automations** | Blueprint Rules | Manual recreation required |

### Item to Process Transformation

| Monday Item Component | Tallyfy Process Component | Notes |
|----------------------|---------------------------|-------|
| **Item Name** | Process Name | Direct transfer |
| **Item ID** | Process Metadata | Stored for reference |
| **Item State** (active/archived/deleted) | Process Status | Maps to active/archived/cancelled |
| **Item Group** | Process Phase | Contextual grouping |
| **Column Values** | Process Data Fields | Type-specific transformation |
| **Item Updates** | Process Comments | Chronological preservation |
| **Item Subscribers** | Process Followers | User mapping required |
| **Item Files** | Process Attachments | File migration |
| **Creation Log** | Process Audit Trail | System field |
| **Last Updated** | Process Modified Date | System field |

---

## Data Fields Mapping

### Complete Column Type Mappings (30+ Types)

| Monday Column Type | Tallyfy Field Type | Transformation Details | Data Handling |
|-------------------|-------------------|------------------------|---------------|
| **Text** | Short Text | Direct mapping | Max 255 chars |
| **Long Text** | Long Text | Direct mapping | Unlimited |
| **Numbers** | Number | With validation | Decimal support |
| **Status** | Dropdown | Label preservation | Single select |
| **People** | Assignee Picker | User ID mapping | Multiple assignees |
| **Date** | Date | ISO 8601 format | Date only |
| **Timeline** | Date (split) | Creates start/end fields | Two date fields |
| **Tags** | Checklist | Multi-select conversion | Multiple options |
| **Dropdown** | Dropdown | Option mapping | Single select |
| **Checkbox** | Radio Buttons | Yes/No conversion | Binary choice |
| **Email** | Short Text + Validation | Email regex validation | Email format |
| **Phone** | Short Text + Validation | Phone regex validation | Phone format |
| **Link** | Short Text + Validation | URL validation | URL format |
| **Location** | Short Text | Lat/long + address | Combined string |
| **Country** | Dropdown | Country list | Predefined options |
| **Rating** | Number | 1-5 scale | Min/max validation |
| **Vote** | Number | Vote count | Positive integer |
| **Progress** | Number | 0-100 percentage | Percentage validation |
| **Formula** | Short Text (readonly) | Result only, formula documented | Static value |
| **Mirror** | Short Text (readonly) | Value copy, source noted | Static snapshot |
| **Dependency** | Dropdown | Item references | Manual linking |
| **File** | File Upload | Attachment migration | File transfer |
| **Hour** | Number | Hours tracking | Decimal hours |
| **Week** | Date | Week selection | Week start date |
| **World Clock** | Short Text | Timezone display | Text representation |
| **Creation Log** | Short Text (readonly) | Creator + timestamp | System field |
| **Last Updated** | Short Text (readonly) | Update timestamp | System field |
| **Auto Number** | Short Text (readonly) | Sequential numbering | Preserved value |
| **Item ID** | Short Text (readonly) | Unique identifier | Metadata storage |
| **Board Relation** | Dropdown | Cross-board reference | Manual setup |
| **Button** | Short Text | Action documentation | Manual recreation |
| **Color** | Dropdown | Color selection | Option mapping |
| **Doc** | Short Text | WorkDoc link | URL preservation |

### Complex Field Transformations

#### Timeline Fields
```
Monday Timeline:
{
  "from": "2024-01-01",
  "to": "2024-01-31"
}

Tallyfy Fields:
- timeline_start: "2024-01-01" (Date field)
- timeline_end: "2024-01-31" (Date field)
```

#### People/Assignee Fields
```
Monday People:
{
  "personsAndTeams": [
    {"id": "12345", "kind": "person"},
    {"id": "67890", "kind": "team"}
  ]
}

Tallyfy Assignees:
["user_abc123", "user_def456"] // Flattened, teams expanded
```

#### Status Labels
```
Monday Status:
{
  "index": 0,
  "label": "Working on it",
  "style": {"color": "#fdab3d"}
}

Tallyfy Dropdown:
{
  "value": "0",
  "label": "Working on it"
} // Style not preserved
```

---

## User Management

### User Role Mapping

| Monday.com Role | Tallyfy Role | Permissions Impact |
|-----------------|--------------|-------------------|
| **Account Admin** | Organization Admin | Full access |
| **Team Member** | Member | Standard access |
| **Viewer** | Light User | Read-only access |
| **Guest** | Light User | Limited access |
| **Board Owner** | Blueprint Admin | Blueprint management |
| **Subscriber** | Process Follower | Notification only |

### User Attributes

| Monday User Attribute | Tallyfy User Attribute | Transformation |
|----------------------|------------------------|----------------|
| **ID** | Metadata (original_id) | Stored for mapping |
| **Email** | Email (primary key) | Lowercase, validated |
| **Name** | First Name + Last Name | Split on space |
| **Title** | Title | Direct transfer |
| **Phone** | Phone | Direct transfer |
| **Location** | Location | Direct transfer |
| **Photo** | - | Not migrated |
| **Is Admin** | Role = 'admin' | Role assignment |
| **Is Guest** | Role = 'light' | Role assignment |
| **Is Pending** | Active = false | Account status |
| **Teams** | Groups | Team membership |

### Team to Group Mapping

| Monday Team | Tallyfy Group | Notes |
|-------------|---------------|-------|
| **Team Name** | Group Name | Direct transfer |
| **Team Members** | Group Members | User ID mapping |
| **Team Owners** | Group Admins | Elevated permissions |
| **Team Picture** | - | Not migrated |

---

## Permissions & Access

### Board/Blueprint Permissions

| Monday Permission | Tallyfy Permission | Behavior Change |
|-------------------|-------------------|-----------------|
| **Private Board** | Private Blueprint | Only invited users |
| **Main Board** | Organization Blueprint | All org members |
| **Shareable Board** | Organization Blueprint | Simplified model |
| **Read Only** | Viewer Permission | Can view, not edit |
| **Edit Items** | Member Permission | Can update processes |
| **Edit Everything** | Admin Permission | Full blueprint control |

### Column/Field Permissions

| Monday Column Permission | Tallyfy Field Permission | Impact |
|-------------------------|-------------------------|--------|
| **Restrict column editing** | Field readonly | Per-field control |
| **Hide column** | - | Not supported, document in notes |

---

## Automation & Rules

### Automation Mapping (Manual Recreation Required)

| Monday Automation Type | Tallyfy Equivalent | Recreation Strategy |
|-----------------------|-------------------|-------------------|
| **Status Change** | Step Completion Rule | Trigger on step done |
| **Date Arrived** | Due Date Rule | Time-based trigger |
| **Person Assigned** | Assignment Rule | User assignment trigger |
| **Item Created** | Process Start Rule | Initialization logic |
| **Every Time Period** | Scheduled Rule | Recurring triggers |
| **Custom Automation** | Custom Rule | Manual configuration |

### Recipe Components

| Monday Recipe Part | Tallyfy Rule Part | Transformation |
|-------------------|-------------------|----------------|
| **Trigger** | Rule Trigger | Different trigger types |
| **Condition** | Rule Condition | Simplified conditions |
| **Action** | Rule Action | Different action set |

---

## Views & Visualization

### View Paradigm Transformation

| Monday View Type | Tallyfy Equivalent | Migration Impact |
|------------------|-------------------|------------------|
| **Main Table** | Process List | Default view |
| **Kanban** | - | Converted to sequential steps |
| **Timeline/Gantt** | - | Converted to linear workflow |
| **Calendar** | - | Dates preserved in fields |
| **Chart** | Reports | Manual recreation |
| **Files Gallery** | - | Files attached to processes |
| **Map** | - | Location data in text fields |
| **Workload** | - | Not supported |
| **Dashboard** | Analytics | Different analytics model |

### Kanban to Sequential Transformation

```
Monday Kanban Columns:
[Backlog] → [In Progress] → [Review] → [Done]
    ↓            ↓             ↓          ↓
  Items        Items         Items     Items

Tallyfy Sequential Steps:
Step 1: Backlog Review → Step 2: Work in Progress → Step 3: Review → Step 4: Completion
```

---

## Collaboration Features

### Communication Mapping

| Monday Feature | Tallyfy Feature | Differences |
|----------------|-----------------|-------------|
| **Updates** | Comments | Threading model differs |
| **@mentions** | @mentions | Similar functionality |
| **Subscribers** | Followers | Notification model |
| **Activity Log** | Audit Trail | System tracking |
| **Notifications** | Notifications | Different triggers |

### File Management

| Monday File Feature | Tallyfy File Feature | Migration Notes |
|--------------------|---------------------|-----------------|
| **File Column** | File Upload Field | Direct migration |
| **Update Attachments** | Comment Attachments | Preserved with comments |
| **Gallery View** | - | Files listed in process |
| **File Versioning** | - | Latest version only |

---

## Integration Points

### Native Integrations (Require Reconnection)

| Integration Type | Monday.com | Tallyfy | Migration Action |
|------------------|------------|---------|------------------|
| **Email** | Email integration | Email rules | Reconfigure |
| **Slack** | Native app | Webhook/API | Reconnect |
| **Teams** | Native app | Webhook | Reconnect |
| **Google Drive** | Native integration | File links | Relink files |
| **Zapier** | Native support | Native support | Recreate zaps |
| **API** | GraphQL v2 | REST API | Rewrite integrations |
| **Webhooks** | Board webhooks | Process webhooks | Reconfigure endpoints |

---

## Migration Metadata

### Preserved in Migration

- Original Monday.com IDs (in metadata)
- Creation timestamps
- Update timestamps  
- User associations (mapped)
- Group/phase information
- Original column types
- Board/workspace references

### Lost in Migration

- View configurations
- Automation recipes (must recreate)
- Activity history (partial)
- Column formatting/colors
- Board background/theme
- Integration configurations
- Webhook settings
- Custom field formulas (values only)

### Manual Post-Migration Tasks

1. **Recreate Automations**: Use Tallyfy rules
2. **Reconnect Integrations**: Set up fresh connections
3. **Configure Notifications**: Adjust notification preferences
4. **Train Users**: Explain paradigm shifts
5. **Validate Workflows**: Test migrated processes
6. **Set Up Reports**: Create new analytics
7. **Establish Webhooks**: Configure new endpoints
8. **Link Related Blueprints**: Manual cross-references

---

## Terminology Dictionary

### Quick Reference

| Monday.com Says | Tallyfy Says | Context |
|-----------------|--------------|---------|
| Board | Blueprint | Template level |
| Item | Process | Instance level |
| Column | Field | Data capture |
| Group | Phase/Step Group | Organization |
| Update | Comment | Communication |
| Pulse | Process | Deprecated Monday term |
| Recipe | Rule | Automation |
| Workspace | Organization | Container |
| Subscriber | Follower | Notifications |
| Status | Step Status | Progress tracking |
| Timeline | Date Range | Time management |
| Person | Assignee | Task ownership |
| Subitem | Checklist | Nested tasks |
| View | - | Not applicable |
| Widget | - | Dashboard component |

---

## Notes

This mapping guide represents the complete transformation logic from Monday.com to Tallyfy. The migration involves significant paradigm shifts, particularly around view flexibility and automation capabilities. Users should expect to adapt their workflows to Tallyfy's sequential model while benefiting from its structured approach to process management.