# Kissflow to Tallyfy Migrator

A comprehensive migration tool for moving from Kissflow (unified low-code/no-code platform) to Tallyfy.

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🔗 Getting Started with Tallyfy

- **📚 Migration Documentation**: [https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/](https://tallyfy.com/products/pro/tutorials/features/migrate-to-tallyfy/)
- **🔌 Open API Documentation**: [https://go.tallyfy.com/api/](https://go.tallyfy.com/api/)
- **🚀 Start Free Trial**: [https://tallyfy.com/start/](https://tallyfy.com/start/)
- **📞 Schedule a Call**: [https://tallyfy.com/booking/](https://tallyfy.com/booking/)

## ⚠️ Critical Paradigm Shifts

### 1. **Unified Platform → Specialized Workflow** (MAJOR)
- **Kissflow**: All-in-one platform with Processes, Boards, Apps, Datasets, Forms
- **Tallyfy**: Sequential workflow automation platform
- **Impact**: Complex functionality simplification required

### 2. **Multiple Module Types → Single Blueprint Model**
- **Kissflow**: 5 distinct modules (Process, Board, App, Dataset, Form)
- **Tallyfy**: Everything becomes a Blueprint/Process
- **Strategy**: Each module type has specialized transformer

### 3. **Kanban Boards → Sequential Workflows** (CRITICAL)
- **Kissflow Boards**: Visual Kanban with drag-and-drop cards between columns
- **Tallyfy**: Sequential task completion
- **Transformation**: Each column becomes 3 steps (Entry, Work, Exit)

### 4. **Low-Code Apps → Process Workflows**
- **Kissflow Apps**: Custom applications with forms, views, and workflows
- **Tallyfy**: Converted to complex multi-step processes
- **Limitations**: Advanced app logic requires manual configuration

## 📋 Pre-Migration Checklist

### Kissflow Side
- [ ] Admin access to Kissflow account
- [ ] Created Access Keys in Admin > API & Webhooks
- [ ] Documented custom formulas and calculations
- [ ] Listed all integrated systems
- [ ] Backed up critical data
- [ ] Identified power users for training

### Tallyfy Side
- [ ] Admin access to Tallyfy organization
- [ ] Generated API token in Settings > API
- [ ] Prepared user list for provisioning
- [ ] Set up groups/departments
- [ ] Configured SSO (if applicable)

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository>
cd migrator/kissflow
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configure Credentials
Edit `.env` file:
```env
# Kissflow Configuration
KISSFLOW_SUBDOMAIN=yourcompany
KISSFLOW_ACCOUNT_ID=acc_xxxxx
KISSFLOW_ACCESS_KEY_ID=key_xxxxx
KISSFLOW_ACCESS_KEY_SECRET=secret_xxxxx

# Tallyfy Configuration
TALLYFY_API_TOKEN=tok_xxxxx
TALLYFY_ORGANIZATION_ID=org_xxxxx
```

### 3. Run Migration
```bash
# Dry run (recommended first)
./migrate.sh --dry-run

# Generate report only
./migrate.sh --report-only

# Full migration
./migrate.sh

# Resume interrupted migration
./migrate.sh --resume
```

## 🏗️ Architecture

### Migration Phases
1. **Discovery**: Analyze Kissflow environment
2. **Users & Groups**: Migrate users and permissions
3. **Datasets**: Transform master data to reference data
4. **Templates**: Convert Processes, Boards, Apps to Blueprints
5. **Instances**: Migrate running instances
6. **Validation**: Verify migration completeness

### Key Components
```
src/
├── api/
│   ├── kissflow_client.py    # Kissflow REST API client
│   └── tallyfy_client.py     # Tallyfy API client
├── transformers/
│   ├── user_transformer.py   # User/role mapping
│   ├── process_transformer.py # BPM process transformation
│   ├── board_transformer.py  # Kanban→Sequential (critical)
│   ├── app_transformer.py    # Low-code app transformation
│   ├── dataset_transformer.py # Master data transformation
│   ├── field_transformer.py  # 20+ field type mappings
│   └── instance_transformer.py # Running instance migration
├── utils/
│   ├── id_mapper.py          # ID relationship tracking
│   ├── progress_tracker.py   # Migration progress
│   ├── validator.py          # Data validation
│   ├── checkpoint_manager.py # Resume capability
│   └── error_handler.py      # Error recovery
└── main.py                    # Orchestrator
```

## 📊 Object Mapping

### Module Type Transformations

| Kissflow Module | Tallyfy Equivalent | Complexity | Notes |
|----------------|-------------------|------------|-------|
| Process | Blueprint | Low | Direct mapping with workflow steps |
| Board | Blueprint | **HIGH** | Kanban→Sequential paradigm shift |
| App | Blueprint + Data | **VERY HIGH** | Multiple forms become complex workflow |
| Dataset | Reference Data | Medium | No native equivalent, stored as metadata |
| Form | Kick-off Form | Low | Becomes process initiation form |

### Critical Field Mappings

| Kissflow Field | Tallyfy Field | Data Loss Risk |
|---------------|---------------|----------------|
| Child Table | Table | Medium - row limits |
| Formula | Read-only Text | HIGH - loses calculation |
| Lookup | Dropdown | Medium - static options |
| Remote Lookup | Dropdown | HIGH - loses dynamic data |
| Signature | File Upload | Low - becomes image |
| Geolocation | Text | Low - stored as coordinates |

## ⚠️ Known Limitations

### Cannot Migrate
1. **Database Tables** - Kissflow supports PostgreSQL tables
2. **Custom Scripts** - JavaScript/Python automation
3. **Advanced Formulas** - Complex calculations
4. **Real-time Integrations** - Webhook subscriptions
5. **Custom Views** - Calendar, Timeline, Chart views
6. **Inter-app Relationships** - Complex data dependencies

### Requires Manual Configuration
1. **Board Automations** - Card movement rules
2. **App Workflows** - Multi-form workflows
3. **Dataset Lookups** - Dynamic dropdowns
4. **Calculated Fields** - Formula fields
5. **Role-based Views** - Complex permissions

## 🔧 Configuration Options

### Environment Variables
```bash
# Required
KISSFLOW_SUBDOMAIN          # Your Kissflow subdomain
KISSFLOW_ACCOUNT_ID         # Account identifier
KISSFLOW_ACCESS_KEY_ID      # API access key
KISSFLOW_ACCESS_KEY_SECRET  # API secret
TALLYFY_API_TOKEN          # Tallyfy API token
TALLYFY_ORGANIZATION_ID    # Organization ID

# Optional
INSTANCE_LIMIT=100         # Max instances per template
DEBUG=false                # Enable debug logging
BACKUP_DIR=./backups       # Checkpoint backup location
```

### Command Line Options
```bash
--dry-run         # Preview without changes
--report-only     # Generate analysis report
--limit N         # Limit instances to migrate
--resume          # Resume from checkpoint
--verbose         # Detailed logging
```

## 📈 Performance Considerations

### Typical Migration Times
- **Small** (< 10 processes, < 100 users): 30-60 minutes
- **Medium** (10-50 processes, 100-500 users): 2-4 hours  
- **Large** (50+ processes, 500+ users): 4-8 hours
- **Enterprise** (100+ processes, 1000+ users): 8-24 hours

### Rate Limits
- Kissflow: 100 requests/minute
- Tallyfy: 600 requests/minute
- Built-in exponential backoff and retry logic

### Multi-Module Handling Implementation

```python
class KissflowModuleRouter:
    """Routes different Kissflow modules to appropriate transformers"""
    
    def __init__(self):
        self.transformers = {
            'process': ProcessTransformer(),
            'board': BoardTransformer(),
            'app': AppTransformer(),
            'dataset': DatasetTransformer(),
            'form': FormTransformer()
        }
        
    def analyze_account(self, account_id):
        """Discover all modules in Kissflow account"""
        modules = {
            'processes': [],
            'boards': [],
            'apps': [],
            'datasets': [],
            'forms': []
        }
        
        # Fetch all module types via different endpoints
        modules['processes'] = self.client.get(f'/processes')
        modules['boards'] = self.client.get(f'/boards')
        modules['apps'] = self.client.get(f'/apps')
        modules['datasets'] = self.client.get(f'/datasets')
        modules['forms'] = self.client.get(f'/forms')
        
        # Calculate complexity score
        complexity = self.assess_migration_complexity(modules)
        
        return {
            'modules': modules,
            'total_count': sum(len(m) for m in modules.values()),
            'complexity': complexity,
            'estimated_hours': self.estimate_migration_time(modules)
        }
    
    def route_module(self, module):
        """Route module to appropriate transformer"""
        module_type = module.get('_module_type', 'process')
        transformer = self.transformers.get(module_type)
        
        if not transformer:
            logger.warning(f"Unknown module type: {module_type}")
            transformer = self.transformers['process']  # Default
            
        return transformer.transform(module)
```

### Board to Sequential Transformation

```python
class BoardTransformer:
    """Critical: Transforms Kissflow Kanban boards to Tallyfy sequential workflows"""
    
    def transform_board_to_workflow(self, board):
        """
        Kissflow Board: Columns with cards that move horizontally
        Tallyfy: Sequential steps that complete vertically
        """
        
        workflow_steps = []
        step_order = 1
        
        for column in board['columns']:
            # Each Kanban column becomes 3 steps in Tallyfy
            
            # 1. Entry step - Notification/preparation
            workflow_steps.append({
                'order': step_order,
                'name': f"Enter {column['name']}",
                'type': 'notification',
                'description': f"Item has entered {column['name']} stage",
                'auto_complete': True,
                'duration_minutes': 0
            })
            step_order += 1
            
            # 2. Work step - Actual work in this column
            workflow_steps.append({
                'order': step_order,
                'name': column['name'],
                'type': 'task',
                'description': column.get('description', ''),
                'assignees': self.map_column_assignees(column),
                'fields': self.extract_column_fields(column),
                'duration_minutes': column.get('sla_hours', 24) * 60
            })
            step_order += 1
            
            # 3. Exit step - Approval to move to next column
            if column.get('requires_approval'):
                workflow_steps.append({
                    'order': step_order,
                    'name': f"Approve exit from {column['name']}",
                    'type': 'approval',
                    'description': f"Approve moving to next stage",
                    'approvers': column.get('approvers', []),
                    'approval_type': 'any'  # or 'all'
                })
                step_order += 1
                
        return workflow_steps
    
    def handle_board_automations(self, board):
        """Convert board automations to Tallyfy rules"""
        rules = []
        
        for automation in board.get('automations', []):
            if automation['trigger'] == 'card_moved':
                # Card movement automation
                rule = {
                    'type': 'step_completion',
                    'condition': f"step_name == 'Exit {automation['from_column']}'",
                    'action': 'auto_assign',
                    'target': automation.get('assign_to')
                }
                rules.append(rule)
            elif automation['trigger'] == 'due_date_approaching':
                # Due date automation
                rule = {
                    'type': 'deadline_reminder',
                    'before_hours': automation.get('hours_before', 24),
                    'notify': automation.get('notify_users', [])
                }
                rules.append(rule)
                
        return rules
```

### App Transformation Complexity

```python
class AppTransformer:
    """Transforms complex Kissflow apps to Tallyfy blueprints"""
    
    def transform_app(self, app):
        """
        Kissflow App: Multiple forms, views, workflows, and data tables
        Tallyfy: Single blueprint with complex workflow
        """
        
        # Analyze app complexity
        complexity = {
            'forms': len(app.get('forms', [])),
            'workflows': len(app.get('workflows', [])),
            'views': len(app.get('views', [])),
            'tables': len(app.get('tables', [])),
            'total_fields': sum(len(f.get('fields', [])) for f in app.get('forms', []))
        }
        
        if complexity['forms'] > 3 or complexity['workflows'] > 1:
            # Complex app - needs splitting
            return self.split_complex_app(app)
        else:
            # Simple app - direct conversion
            return self.simple_app_conversion(app)
    
    def split_complex_app(self, app):
        """Split complex app into multiple blueprints"""
        blueprints = []
        
        # Create main blueprint
        main_blueprint = {
            'name': app['name'],
            'description': app.get('description', ''),
            'category': 'Migrated Apps',
            'steps': []
        }
        
        # Each form becomes a step group
        for form in app.get('forms', []):
            step_group = self.form_to_step_group(form)
            main_blueprint['steps'].extend(step_group)
        
        # Each workflow branch becomes a conditional path
        for workflow in app.get('workflows', []):
            if workflow.get('is_subprocess'):
                # Create separate blueprint for subprocess
                sub_blueprint = self.workflow_to_blueprint(workflow)
                sub_blueprint['name'] = f"{app['name']} - {workflow['name']}"
                blueprints.append(sub_blueprint)
            else:
                # Add to main blueprint
                workflow_steps = self.workflow_to_steps(workflow)
                main_blueprint['steps'].extend(workflow_steps)
        
        blueprints.insert(0, main_blueprint)
        return blueprints
```

### Field Type Mapping Details

```python
class FieldTransformer:
    """Maps 20+ Kissflow field types to Tallyfy"""
    
    def __init__(self):
        self.field_map = {
            # Simple mappings
            'text': 'text',
            'textarea': 'textarea',
            'email': 'email',
            'date': 'date',
            'checkbox': 'radio',  # Yes/No
            'dropdown': 'dropdown',
            'radio': 'radio',
            'file': 'file',
            
            # Complex mappings
            'child_table': self.transform_child_table,
            'formula': self.transform_formula,
            'lookup': self.transform_lookup,
            'remote_lookup': self.transform_remote_lookup,
            'signature': self.transform_signature,
            'geolocation': self.transform_geolocation,
            'user': 'assignees_form',
            'number': self.transform_number,
            'currency': self.transform_currency,
            'percentage': self.transform_percentage
        }
    
    def transform_child_table(self, field):
        """Child tables become Tallyfy table fields with limitations"""
        return {
            'type': 'table',
            'name': field['name'],
            'columns': [
                {
                    'name': col['name'],
                    'type': 'text',  # Tables only support text columns
                    'required': col.get('required', False)
                }
                for col in field.get('columns', [])[:10]  # Max 10 columns
            ],
            'max_rows': min(field.get('max_rows', 100), 100),  # Tallyfy limit
            'warning': 'Complex validations and formulas not supported in table'
        }
    
    def transform_formula(self, field):
        """Formula fields become read-only text with warning"""
        return {
            'type': 'text',
            'name': field['name'],
            'readonly': True,
            'default_value': f"[Formula: {field.get('formula', 'N/A')}]",
            'warning': 'Formula calculations not supported - requires manual calculation'
        }
    
    def transform_lookup(self, field):
        """Dataset lookups become static dropdowns"""
        # Fetch current dataset values
        dataset_id = field.get('dataset_id')
        values = self.fetch_dataset_values(dataset_id, field.get('display_field'))
        
        return {
            'type': 'dropdown',
            'name': field['name'],
            'options': [
                {'value': v['id'], 'label': v['display']}
                for v in values[:100]  # Limit to 100 options
            ],
            'warning': 'Dynamic lookup converted to static dropdown - update manually'
        }
```

## 🔍 Validation & Reporting

### Generated Reports
1. **Discovery Report** - What will be migrated
2. **Migration Report** - Real-time progress
3. **Validation Report** - Post-migration verification
4. **Error Report** - Failed items and reasons

### Validation Checks
- User account creation
- Template structure preservation
- Instance data integrity
- Permission mappings
- Workflow logic validation

## 🆘 Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Verify Access Keys are active
curl -H "Authorization: Bearer YOUR_ACCESS_KEY" \
  https://YOUR_SUBDOMAIN.kissflow.com/api/v1/accounts
```

#### Rate Limit Errors
- Migration automatically pauses for 1 hour
- Adjust INSTANCE_LIMIT to reduce load

#### Board Migration Issues
- Review 3-step pattern transformation
- Check column-to-step mapping
- Verify approval gates

#### App Migration Complexity
- Consider breaking complex apps into multiple blueprints
- Review form field mappings
- Check workflow branch logic

### Recovery Options
```bash
# Resume from checkpoint
./migrate.sh --resume

# Re-run specific phase
python3 src/main.py --phase users

# Export ID mappings
sqlite3 kissflow_tallyfy_mapping.db ".dump id_mappings"
```

## 📚 Training Requirements

### For End Users
1. **Paradigm Shift Training** (2-4 hours)
   - From Kanban to Sequential
   - From Apps to Processes
   - New UI navigation

2. **Process Training** (1-2 hours per process)
   - Step completion vs card movement
   - Approval gates
   - Task assignments

### For Administrators
1. **Blueprint Management** (4-6 hours)
2. **Permission Configuration** (2-3 hours)
3. **Reporting and Analytics** (2-3 hours)

## 🤝 Support

### Pre-Migration Support
- Review discovery report
- Identify high-risk migrations
- Plan phased approach

### Post-Migration Support
- User training sessions
- Process optimization
- Custom configuration

## 📄 License

Proprietary - Tallyfy Inc.

## 🔗 Comparison Resources

- [Tallyfy vs Kissflow](https://tallyfy.com/differences/tallyfy-vs-kissflow/)
- [Kissflow API Documentation](https://help.kissflow.com/en/articles/8329901)
- [Tallyfy API Reference](https://docs.tallyfy.com/)

---

**Critical Note**: Due to fundamental paradigm differences (especially Kanban→Sequential), thorough testing and user training are MANDATORY for successful migration.

## 📖 Tallyfy Field Types Reference

### Available Field Types in Tallyfy

Based on the ACTUAL api-v2 implementation, these are the correct field types:

1. **text** - Short text input (max 255 characters)
2. **textarea** - Long text input (max 6000 characters)
3. **radio** - Radio buttons for single selection
4. **dropdown** - Dropdown list for single selection
5. **multiselect** - Multiple choice dropdown
6. **date** - Date picker
7. **email** - Email field with validation
8. **file** - File upload
9. **table** - Table/grid input
10. **assignees_form** - User/guest assignment field

### Critical API Implementation Details

#### ID Formats
- All main entities use **32-character hash strings** (NOT integers)
- Examples: checklist_id, run_id, organization_id, task_id
- Only users and guests use integer IDs

#### API Endpoints (ACTUAL)
- Templates: `/api/organizations/{org_id}/checklists`
- Processes: `/api/organizations/{org_id}/runs`
- Tasks: `/api/organizations/{org_id}/runs/{run_id}/tasks`
- Form fields: `/api/organizations/{org_id}/checklists/{id}/form-fields`

#### Prerun/Kickoff Form Data
- Stored in `field` table with checklist class_id
- Request key is `prerun_data` (object), NOT `prerun` (array)
- Format: `{"field_id": "value"}` not array of objects

#### Field Validation
Instead of `type`, use Laravel validation rules:
- Numeric: `"validation": "numeric|min:0|max:100"`
- Email: `"validation": "email"`
- URL: `"validation": "url"`
- Required: `"required": true`

#### Required Headers
```json
{
  "Authorization": "Bearer {token}",
  "Content-Type": "application/json",
  "Accept": "application/json"
}
```
Note: X-Tallyfy-Client header is NOT required.

### Important API Notes

#### No Direct Number Type
Tallyfy does NOT have a dedicated "number" field type. For numeric inputs:
- Use **short_text** with number validation
- Add validation rules: `{"type": "number", "min": 0, "max": 100}`

#### Special Field Validations
- **Email**: short_text with pattern `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- **Phone**: short_text with pattern `^[\d\s\-\+\(\)]+$`
- **URL**: short_text with pattern `^https?://`
- **Yes/No**: radio_buttons with options `[{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}]`

#### API Endpoints
- Templates: `/organizations/{org_id}/checklists` (NOT /templates)
- Processes: `/organizations/{org_id}/runs` (NOT /processes)
- Kick-off form data uses "prerun" array (NOT "field")

#### Required Headers
All API requests MUST include:
```json
{
  "Authorization": "Bearer {token}",
  "Content-Type": "application/json",
  "Accept": "application/json",
  "X-Tallyfy-Client": "APIClient"  // MANDATORY
}
```

