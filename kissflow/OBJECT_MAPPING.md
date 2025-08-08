# Kissflow to Tallyfy Object Mapping

## 🔄 Critical Paradigm Shifts

### 1. Unified Platform → Workflow Platform
**Kissflow**: All-in-one low-code/no-code platform  
**Tallyfy**: Sequential workflow automation  
**Impact**: Multiple module types must be transformed into workflow patterns

### 2. Kanban Boards → Sequential Steps
**Kissflow**: Visual boards with drag-and-drop cards  
**Tallyfy**: Linear task progression  
**Transformation**: Each column becomes 3 sequential steps (Entry, Work, Exit)

### 3. Apps → Complex Workflows
**Kissflow**: Custom applications with multiple forms and views  
**Tallyfy**: Single blueprint with conditional logic  
**Challenge**: Multi-form apps require creative transformation

## 📊 Terminology Mapping

### Core Objects

| Kissflow Term | Tallyfy Term | Notes |
|--------------|--------------|-------|
| **Process** | Blueprint | Direct equivalent for BPM workflows |
| **Board** | Blueprint | Requires Kanban→Sequential transformation |
| **App** | Blueprint | Complex transformation with sub-processes |
| **Dataset** | Reference Data | No native equivalent, stored as metadata |
| **Form** | Kick-off Form | Becomes process initiation |
| **Flow** | Workflow/Steps | Sequential task progression |
| **Case** | Process Instance | Running instance of blueprint |
| **Card** | Process Instance | Board cards become processes |
| **Record** | Process Data | App records become process data |

### User & Permissions

| Kissflow Term | Tallyfy Term | Mapping Logic |
|--------------|--------------|---------------|
| **Super Admin** | Admin | Full system access |
| **Admin** | Admin | Organization management |
| **Developer** | Admin | Treated as admin in Tallyfy |
| **Process Admin** | Member | Standard user with process rights |
| **Board Admin** | Member | Standard user with board rights |
| **App Admin** | Member | Standard user with app rights |
| **Member** | Member | Standard user |
| **Light User** | Light | Limited access user |
| **Guest** | Light | External limited access |
| **Department** | Group | Organizational unit |
| **Role** | Role/Group | Permission grouping |

### Workflow Components

| Kissflow Component | Tallyfy Component | Transformation |
|-------------------|-------------------|---------------|
| **Step** | Task/Step | Direct mapping |
| **Approval Step** | Approval Step | Direct mapping |
| **Decision Point** | Conditional Step | Becomes approval with branches |
| **Parallel Branch** | Sequential Steps | Parallel→Sequential with notes |
| **System Action** | Webhook/Integration | External call |
| **Email Step** | Email Step | Direct mapping |
| **Integration** | Webhook | API integration |
| **Child Workflow** | Sub-process | Linked blueprint |
| **Loop** | Conditional Return | Manual configuration needed |

### Field Types (20+ Types)

| Kissflow Field | Tallyfy Field | Data Preservation |
|---------------|---------------|-------------------|
| **Text** | Short Text | ✅ Full |
| **Textarea** | Long Text | ✅ Full |
| **Rich Text** | Long Text | ⚠️ Loses formatting |
| **Number** | Number | ✅ Full |
| **Currency** | Number | ⚠️ Loses currency symbol |
| **Date** | Date | ✅ Full |
| **DateTime** | Date | ✅ With time |
| **Dropdown** | Dropdown | ✅ Full |
| **Multi-Dropdown** | Checklist | ✅ Full |
| **Radio** | Radio Buttons | ✅ Full |
| **Checkbox** | Radio (Yes/No) | ✅ Full |
| **Yes/No** | Radio Buttons | ✅ Full |
| **User** | Assignee Picker | ✅ Full |
| **Attachment** | File Upload | ✅ Full |
| **Signature** | File Upload | ⚠️ Becomes image |
| **Child Table** | Table | ⚠️ Row limits (1000) |
| **Formula** | Read-only Text | ❌ Loses calculation |
| **Lookup** | Dropdown | ❌ Becomes static |
| **Remote Lookup** | Dropdown | ❌ Loses dynamic data |
| **Geolocation** | Text | ⚠️ Stored as coordinates |
| **Scanner** | Text | ⚠️ Barcode as text |
| **Sequence Number** | Text | ❌ Loses auto-increment |

## 🔄 Module-Specific Transformations

### Process → Blueprint
```
Kissflow Process:
├── Initiation Form
├── Workflow Steps
│   ├── Tasks
│   ├── Approvals
│   └── Decisions
├── SLA/Deadlines
└── Permissions

Tallyfy Blueprint:
├── Kick-off Form (from Initiation)
├── Sequential Steps
│   ├── Tasks
│   ├── Approvals
│   └── Conditional Logic
├── Due Dates
└── Member Permissions
```

### Board → Blueprint (CRITICAL TRANSFORMATION)
```
Kissflow Board:
├── Columns (Kanban)
│   ├── To Do
│   ├── In Progress
│   ├── Review
│   └── Done
├── Cards (Visual)
└── WIP Limits

Tallyfy Blueprint:
├── Sequential Steps (3 per column)
│   ├── To Do - Entry
│   ├── To Do - Work
│   ├── To Do - Exit
│   ├── In Progress - Entry
│   ├── In Progress - Work
│   ├── In Progress - Exit
│   ├── Review - Entry
│   ├── Review - Work
│   ├── Review - Exit
│   └── Done - Complete
└── Process Instances (from Cards)
```

### App → Blueprint (COMPLEX)
```
Kissflow App:
├── Multiple Forms
├── Views
│   ├── List
│   ├── Kanban
│   ├── Calendar
│   └── Chart
├── Workflows
└── Data Tables

Tallyfy Blueprint:
├── Master Kick-off Form (merged)
├── Conditional Steps (per form)
├── List View Only
├── Sequential Workflows
└── Reference Data (from tables)
```

### Dataset → Reference Data
```
Kissflow Dataset:
├── Master Data Table
├── Lookup Configuration
├── Sync Settings
└── Relationships

Tallyfy Reference:
├── Static JSON Data
├── Dropdown Options
├── Manual Updates
└── No Relationships
```

## ⚠️ Features That Cannot Be Migrated

### Lost Functionality
1. **Database Tables** - PostgreSQL table support
2. **Dynamic Lookups** - Real-time data fetching
3. **Calculated Fields** - Formula computations
4. **Custom Scripts** - JavaScript/Python automation
5. **Advanced Views** - Calendar, Timeline, Charts
6. **Card Movement Rules** - Automatic Kanban transitions
7. **Inter-App Dependencies** - Complex data relationships
8. **Webhooks Subscriptions** - Incoming webhooks
9. **Custom Branding** - UI customization
10. **Advanced Analytics** - Custom reports and dashboards

### Requires Manual Recreation
1. **Complex Conditions** - Multi-field decision logic
2. **Loop Patterns** - Iterative workflows
3. **Dynamic Assignments** - Formula-based routing
4. **Escalation Rules** - Time-based escalations
5. **Business Rules** - Complex validation logic

## 📋 Migration Decision Matrix

| Kissflow Feature | Migration Complexity | Recommendation |
|-----------------|---------------------|----------------|
| Simple Process | ✅ Low | Automated migration |
| Complex Process with Decisions | ⚠️ Medium | Automated + Review |
| Kanban Board | 🔴 High | Automated + Training |
| Simple App (1 form) | ✅ Low | Automated migration |
| Complex App (multi-form) | 🔴 Very High | Manual review required |
| Dataset (<100 records) | ✅ Low | Automated migration |
| Dataset (>1000 records) | ⚠️ Medium | Consider external DB |
| Forms with Formulas | 🔴 High | Manual formula recreation |
| Integrated Workflows | 🔴 Very High | Rebuild integrations |

## 🎯 Transformation Strategies

### Board → Sequential Strategy
1. **Analyze Column Flow**: Document typical card progression
2. **Create Entry Gates**: Add notification steps for column entry
3. **Define Work Steps**: Core tasks for each column
4. **Add Exit Approvals**: Validation before next column
5. **Training Focus**: Emphasize new sequential paradigm

### App → Blueprint Strategy
1. **Merge Forms**: Combine into single kick-off form
2. **Use Conditionals**: Show/hide fields based on type
3. **Create Sub-processes**: Break complex apps into multiple blueprints
4. **Flatten Workflows**: Convert parallel paths to sequential
5. **Document Limitations**: List features requiring manual work

### Dataset → Reference Strategy
1. **Export Data**: Extract all records as JSON
2. **Create Management Process**: CRUD operations workflow
3. **Build Dropdowns**: Convert lookups to static options
4. **Document Updates**: Manual process for data changes
5. **Consider Alternatives**: External database for large datasets

## 📊 Metrics & Validation

### Migration Success Metrics
- **Object Mapping Rate**: % of objects successfully mapped
- **Data Preservation**: % of data migrated without loss
- **Feature Coverage**: % of features preserved
- **User Adoption**: % of users successfully transitioned

### Validation Checkpoints
1. ✅ All users created with correct roles
2. ✅ All templates created with steps
3. ✅ Field mappings preserve data types
4. ✅ Running instances migrated with data
5. ⚠️ Board transformations reviewed
6. ⚠️ App complexity documented
7. ⚠️ Formula fields identified for manual work

## 🔗 References

- [Kissflow API Documentation](https://help.kissflow.com/en/articles/8329901)
- [Tallyfy API Documentation](https://docs.tallyfy.com/)
- [Kissflow vs Tallyfy Comparison](https://tallyfy.com/differences/tallyfy-vs-kissflow/)

---

**Note**: This mapping represents a complex transformation from a unified platform to a specialized workflow tool. Success requires careful planning, thorough testing, and comprehensive user training.