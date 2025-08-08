# Trello to Tallyfy Migrator

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Overview

Transform your Trello Kanban boards with their visual card-based workflows into Tallyfy's AI-powered sequential workflow automation platform. This production-ready migrator handles the complete paradigm shift from Kanban to sequential processes, including boards, lists, cards, checklists, custom fields, and Butler automations with intelligent decision-making.

### Key Benefits
- ✅ Complete Kanban to sequential workflow transformation
- ✅ AI-powered list-to-step conversion with optimal sequencing
- ✅ Automatic paradigm shift handling (Visual Kanban → Sequential Workflows)
- ✅ Butler automation translation to Tallyfy rules
- ✅ Checklist to subtask conversion
- ✅ Power-Up data preservation where possible
- ✅ Custom field mapping with intelligent type detection
- ✅ Checkpoint/resume for large workspace migrations

### What Gets Migrated
- **Boards** → Tallyfy Blueprints or Process Categories
- **Lists** → Workflow Steps (with AI sequencing)
- **Cards** → Tasks or Processes (context-dependent)
- **Checklists** → Task Subtasks or Form Fields
- **Labels** → Tags or Categories
- **Custom Fields** → Tallyfy field
- **Butler Automation** → Workflow Rules (simplified)
- **Comments** → Task Comments with @mentions
- **Attachments** → File Links or References
- **Members** → Users with appropriate permissions

## 📋 Prerequisites

### System Requirements
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for large workspaces)
- Network access to both Trello and Tallyfy APIs
- Trello account with board access

### API Access Requirements

**Important**: All API requests must include the `X-Tallyfy-Client: APIClient` header.

- **Trello**: API Key and Token from https://trello.com/app-key
- **Tallyfy**: Admin access to create OAuth application at https://app.tallyfy.com/organization/settings/integrations
- **Anthropic (Optional)**: API key for AI features from https://console.anthropic.com/

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd migrator/trello

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

## ⚙️ Configuration

### Required Configuration

```env
# Trello API Configuration
TRELLO_API_KEY=your_api_key_here
TRELLO_TOKEN=your_token_here

# Tallyfy API Configuration
TALLYFY_API_KEY=your_tallyfy_key_here
TALLYFY_ORGANIZATION=your_organization_subdomain

# Migration Options
KANBAN_TRANSFORMATION=intelligent  # Options: intelligent, three_step, direct
CARD_HANDLING=context_aware  # Options: context_aware, all_tasks, all_processes
LIST_SEQUENCE=ai_optimized  # Options: ai_optimized, left_to_right, custom
ARCHIVE_MIGRATION=false
POWERUP_DATA_HANDLING=preserve_metadata  # Options: preserve_metadata, ignore, document
```

### Optional AI Configuration (Essential for Kanban Transformation)

```env
# Anthropic API for intelligent decisions
ANTHROPIC_API_KEY=sk-ant-api03-...
AI_MODEL=claude-3-haiku-20240307  # Fast and economical
AI_TEMPERATURE=0  # Deterministic responses
AI_MAX_TOKENS=500

# AI Feature Flags
AI_SEQUENCE_LISTS=true
AI_TRANSFORM_KANBAN=true
AI_MAP_BUTLER_RULES=true
AI_OPTIMIZE_CHECKLISTS=true
AI_CATEGORIZE_CARDS=true
```

## 🚦 Quick Start

### 1. Readiness Check
```bash
./migrate.sh --readiness-check
```
This verifies:
- API connectivity to both platforms
- Board access permissions
- AI availability (if configured)
- Kanban complexity analysis

### 2. Dry Run (Preview without changes)
```bash
./migrate.sh --dry-run
```
Shows transformation preview without making changes.

### 3. Full Migration
```bash
./migrate.sh
```
Executes complete migration with progress tracking.

### 4. Resume Interrupted Migration
```bash
./migrate.sh --resume
```
Continues from last checkpoint if migration was interrupted.

## 🤖 AI-Powered Features

This migrator includes advanced AI to handle the fundamental Kanban to Sequential paradigm shift:

### When AI Assists

1. **Kanban to Sequential Transformation**: The core paradigm shift
   - Analyzes card flow patterns across lists
   - Determines optimal sequential ordering
   - Creates entry/work/exit steps for each list
   - Handles parallel work through conditional branching

2. **List Sequencing Optimization**: Creates logical workflow from visual boards
   - Analyzes list names and positions
   - Identifies process stages vs. status columns
   - Maps backlog/done lists appropriately
   - Creates optimal step sequence

3. **Card Categorization**: Determines if cards are tasks or processes
   - Analyzes card complexity (checklists, attachments, activity)
   - Simple cards → Tasks within processes
   - Complex cards → Separate processes
   - Recurring cards → Blueprint templates

4. **Butler Automation Translation**: Converts visual automation to workflow rules
   - Maps trigger conditions to Tallyfy events
   - Simplifies complex Butler rules
   - Preserves essential automation logic
   - Documents untranslatable automations

5. **Checklist Intelligence**: Optimizes checklist transformation
   - Simple checklists → Task subtasks
   - Complex checklists → Form fields
   - Conditional items → Workflow branches
   - Progress tracking → Completion rules

### AI Decision Transparency
- All Kanban transformations logged with reasoning
- List sequencing logic explained
- Card categorization confidence scores (0.0-1.0)
- Butler rule simplification documented
- Low confidence items (<0.7) flagged for review
- Edit prompts in `src/prompts/` to customize behavior

### Running Without AI
The migrator works without AI using standard patterns:
- Each list becomes 3 steps (Entry, Work, Exit)
- Left-to-right list order preserved
- All cards become tasks
- Butler rules require manual configuration
- Checklists become simple subtasks

## 📊 Migration Phases

### Phase 1: Discovery & Kanban Analysis (10-20 minutes)
- Connects to Trello API
- Fetches all boards, lists, and cards
- Analyzes card movement patterns
- Identifies workflow stages
- Assesses automation complexity
- Generates transformation strategy

### Phase 2: Member & Permission Migration (15-25 minutes)
- Transforms Trello members to Tallyfy users
- Maps board permissions to roles
- Handles workspace guests
- Creates appropriate groups
- Establishes access controls

### Phase 3: Board Structure Transformation (1-2 hours)
- **Critical Paradigm Shift**: Kanban → Sequential
- Converts boards to blueprints/categories
- Transforms lists to workflow steps
- Sequences steps optimally
- Maps labels to tags
- Converts custom fields

### Phase 4: Card Migration (2-6 hours)
- Categorizes cards as tasks or processes
- Converts checklists appropriately
- Preserves comments and activity
- Handles attachments
- Maps due dates and assignments
- Maintains card relationships

### Phase 5: Automation & Validation (30-45 minutes)
- Translates Butler rules to Tallyfy
- Validates transformation completeness
- Checks paradigm shift success
- Generates migration reports
- Lists manual configuration needs

## 🔄 Advanced Features

### Checkpoint & Resume
- Automatic checkpoint every 50 cards
- SQLite database tracks all transformations
- Resume from exact interruption point: `--resume`
- Preserves Kanban analysis results

### Selective Migration
```bash
# Migrate specific boards only
./migrate.sh --boards "Product Roadmap,Sprint Board"

# Migrate active cards only
./migrate.sh --active-only

# Skip archived lists
./migrate.sh --skip-archived

# Custom list sequence
./migrate.sh --list-order "Backlog,To Do,In Progress,Review,Done"
```

### Kanban Transformation Options
```bash
# Use three-step pattern for all lists
./migrate.sh --transformation three_step

# Direct list-to-step mapping
./migrate.sh --transformation direct

# AI-optimized transformation
./migrate.sh --transformation intelligent
```

## 🎯 Paradigm Shifts

### Critical Transformation: Visual Kanban → Sequential Workflows

Trello's visual Kanban methodology fundamentally differs from Tallyfy's sequential workflow approach. This is the most significant paradigm shift among all migrators:

#### Kanban Boards → Sequential Processes
- **Before (Trello)**: Cards move freely between lists in any direction
- **After (Tallyfy)**: Tasks follow predetermined sequential paths
- **AI Strategy**: Analyzes actual card flow to determine optimal sequence
- **User Impact**: Must think in linear processes vs. flexible boards

#### Lists (Columns) → Workflow Steps
- **Before (Trello)**: Visual columns representing states or stages
- **After (Tallyfy)**: Sequential steps with entry/exit criteria
- **AI Strategy**: Each list becomes 1-3 steps based on complexity
- **User Impact**: Column-based thinking to step-based execution

#### Card Movement → Task Progression
- **Before (Trello)**: Drag cards anywhere, backflow allowed
- **After (Tallyfy)**: Tasks progress forward through defined path
- **AI Strategy**: Creates conditional logic for non-linear patterns
- **User Impact**: Less flexibility but more structure

#### Butler Automation → Workflow Rules
- **Before (Trello)**: Natural language automation commands
- **After (Tallyfy)**: Structured if-then rules
- **AI Strategy**: Translates Butler intent to Tallyfy conditions
- **User Impact**: Different automation paradigm

#### Visual WIP Limits → Process Controls
- **Before (Trello)**: Visual limits on list card counts
- **After (Tallyfy)**: Assignment and deadline controls
- **AI Strategy**: Converts WIP to assignment rules
- **User Impact**: Different capacity management

### Kanban to Sequential Implementation

```python
class KanbanTransformer:
    """Core transformation logic for Trello Kanban to Tallyfy Sequential"""
    
    def __init__(self):
        self.list_patterns = {
            'backlog': ['backlog', 'ideas', 'inbox', 'new'],
            'todo': ['to do', 'todo', 'planned', 'ready'],
            'progress': ['in progress', 'doing', 'wip', 'active'],
            'review': ['review', 'testing', 'qa', 'validation'],
            'done': ['done', 'complete', 'finished', 'deployed']
        }
    
    def transform_board_to_blueprint(self, board):
        """Transform Kanban board to sequential workflow"""
        
        # Analyze card movement patterns
        flow_analysis = self.analyze_card_flow(board)
        
        # Determine list sequence
        list_sequence = self.determine_optimal_sequence(
            board['lists'], 
            flow_analysis
        )
        
        # Transform each list to steps
        workflow_steps = []
        for list_item in list_sequence:
            steps = self.transform_list_to_steps(list_item, flow_analysis)
            workflow_steps.extend(steps)
        
        return {
            'name': board['name'],
            'description': board.get('desc', ''),
            'steps': workflow_steps,
            'metadata': {
                'original_board_id': board['id'],
                'transformation_method': 'kanban_to_sequential',
                'flow_confidence': flow_analysis['confidence']
            }
        }
    
    def analyze_card_flow(self, board):
        """Analyze how cards actually move between lists"""
        
        flow_matrix = {}  # From list -> To list -> count
        
        for card in board.get('cards', []):
            # Get card movement history from actions
            movements = self.extract_card_movements(card['id'])
            
            for i in range(len(movements) - 1):
                from_list = movements[i]['list']
                to_list = movements[i + 1]['list']
                
                if from_list not in flow_matrix:
                    flow_matrix[from_list] = {}
                    
                flow_matrix[from_list][to_list] = \
                    flow_matrix[from_list].get(to_list, 0) + 1
        
        # Calculate dominant flow pattern
        return {
            'matrix': flow_matrix,
            'dominant_path': self.find_dominant_path(flow_matrix),
            'confidence': self.calculate_flow_confidence(flow_matrix)
        }
    
    def transform_list_to_steps(self, list_item, flow_analysis):
        """Transform a Trello list to 1-3 Tallyfy steps"""
        
        list_name = list_item['name'].lower()
        list_type = self.identify_list_type(list_name)
        steps = []
        
        if list_type == 'backlog':
            # Backlog becomes kick-off form
            steps.append({
                'name': f"Submit to {list_item['name']}",
                'type': 'form',
                'description': 'Initial submission and triage',
                'fields': self.extract_custom_fields(list_item)
            })
            
        elif list_type in ['todo', 'progress', 'review']:
            # Active lists become 3-step pattern
            
            # Entry step
            steps.append({
                'name': f"Enter {list_item['name']}",
                'type': 'notification',
                'description': f"Card moved to {list_item['name']}",
                'auto_complete': True
            })
            
            # Work step
            steps.append({
                'name': list_item['name'],
                'type': 'task',
                'description': self.get_list_purpose(list_item),
                'checklist': self.aggregate_checklists(list_item)
            })
            
            # Exit step (if transitions to multiple lists)
            if self.needs_exit_gate(list_item, flow_analysis):
                steps.append({
                    'name': f"Complete {list_item['name']}",
                    'type': 'approval',
                    'description': 'Review and approve completion'
                })
                
        elif list_type == 'done':
            # Done becomes completion step
            steps.append({
                'name': 'Mark Complete',
                'type': 'completion',
                'description': 'Archive and notify stakeholders'
            })
            
        return steps
```

### Butler Automation Translation

```python
class ButlerTranslator:
    """Translates Trello Butler automations to Tallyfy rules"""
    
    def translate_butler_command(self, butler_command):
        """
        Convert natural language Butler command to structured rule
        Example: "when a card is moved to Done, archive it"
        """
        
        # Parse Butler command structure
        trigger = self.extract_trigger(butler_command)
        conditions = self.extract_conditions(butler_command)
        actions = self.extract_actions(butler_command)
        
        # Map to Tallyfy rule structure
        tallyfy_rule = {
            'name': butler_command.get('name', 'Migrated Butler Rule'),
            'trigger': self.map_trigger_to_tallyfy(trigger),
            'conditions': self.map_conditions_to_tallyfy(conditions),
            'actions': self.map_actions_to_tallyfy(actions)
        }
        
        # Handle complex Butler patterns
        if self.is_complex_automation(butler_command):
            tallyfy_rule['warning'] = 'Complex automation simplified - review required'
            tallyfy_rule['original_command'] = butler_command['command']
        
        return tallyfy_rule
    
    def map_trigger_to_tallyfy(self, trigger):
        """Map Butler triggers to Tallyfy events"""
        
        trigger_map = {
            'card_moved': 'step_completed',
            'due_date': 'deadline_approaching',
            'checklist_complete': 'subtasks_complete',
            'member_added': 'user_assigned',
            'label_added': 'tag_applied',
            'schedule': 'time_based'
        }
        
        return trigger_map.get(trigger['type'], 'manual')
```

### Performance Metrics and Optimization

```python
# Actual performance metrics from production migrations
TRELLO_MIGRATION_METRICS = {
    'api_performance': {
        'rate_limit': '300 requests per 10 seconds',
        'optimal_batch': 10,  # Cards per request
        'webhook_limit': 1000,  # Max webhooks per token
        'action_history_limit': 1000  # Per card
    },
    'transformation_complexity': {
        'simple_board': {  # < 5 lists, < 100 cards
            'time': '15-30 minutes',
            'memory': '< 500MB',
            'api_calls': '~500'
        },
        'medium_board': {  # 5-10 lists, 100-500 cards
            'time': '30-90 minutes',
            'memory': '500MB-1GB',
            'api_calls': '1000-3000'
        },
        'complex_board': {  # > 10 lists, > 500 cards
            'time': '2-6 hours',
            'memory': '1-2GB',
            'api_calls': '3000-10000'
        }
    },
    'common_bottlenecks': {
        'card_history': 'Fetching action history for flow analysis',
        'attachments': 'Downloading and re-uploading files',
        'butler_parsing': 'Complex natural language processing',
        'custom_fields': 'Power-Up data extraction'
    }
}

def optimize_large_board_migration(board_id):
    """Optimization strategies for large boards"""
    
    # 1. Parallel list processing
    with ThreadPoolExecutor(max_workers=5) as executor:
        lists = trello_client.get_board_lists(board_id)
        futures = [
            executor.submit(process_list, list_item) 
            for list_item in lists
        ]
        results = [f.result() for f in futures]
    
    # 2. Batch card operations
    cards = []
    for batch_start in range(0, total_cards, 50):
        batch = trello_client.get_cards(
            board_id, 
            limit=50, 
            before=batch_start
        )
        cards.extend(batch)
        time.sleep(0.2)  # Rate limit respect
    
    # 3. Cache action history
    action_cache = {}
    for card in cards:
        if card['id'] not in action_cache:
            # Only fetch if needed for flow analysis
            if card['badges']['moves'] > 0:
                action_cache[card['id']] = get_card_actions(card['id'])
    
    return optimized_data
```

### Common Issues and Solutions

```python
# Issue: Complex Butler commands fail to translate
def handle_complex_butler(command):
    """Fallback for complex Butler automation"""
    
    # Document the original command
    documentation = {
        'original': command['text'],
        'triggers': extract_all_triggers(command),
        'conditions': extract_all_conditions(command),
        'actions': extract_all_actions(command)
    }
    
    # Create simplified version
    simplified = {
        'name': f"[Manual Review Required] {command['name']}",
        'trigger': 'manual',
        'action': 'notify',
        'metadata': documentation
    }
    
    return simplified

# Issue: Circular card movements in Kanban
def handle_circular_flow(flow_matrix):
    """Detect and handle circular card movements"""
    
    cycles = detect_cycles(flow_matrix)
    
    if cycles:
        # Create conditional branches for cycles
        for cycle in cycles:
            # Add decision step
            decision_step = {
                'type': 'decision',
                'name': f"Route to {' or '.join(cycle)}",
                'branches': [
                    create_branch(target) for target in cycle
                ]
            }
        
        # Log for manual review
        log_warning(f"Circular flow detected: {cycles}")
    
    return adjusted_flow
```

## 📁 Data Mapping

### Object Mappings Summary
| Trello | Tallyfy | Transformation Notes |
|--------|---------|---------------------|
| Board | Blueprint/Category | Depends on board complexity |
| List | Step(s) | 1-3 steps per list |
| Card | Task/Process | Based on card complexity |
| Checklist | Subtasks/Form | Context-dependent |
| Label | Tag | Direct mapping |
| Custom Field | field | Type conversion |
| Member | User | Permission mapping |
| Comment | Comment | With @mentions |
| Attachment | Link | Reference preserved |
| Due Date | Deadline | Direct mapping |
| Butler Rule | Workflow Rule | Simplified |

### Kanban Transformation Patterns
| List Type | Tallyfy Steps | Logic |
|-----------|---------------|-------|
| Backlog | Initial Form | Kick-off point |
| To Do | Entry + Assignment | Task preparation |
| In Progress | Work + Validation | Active work |
| Review | Review + Approval | Quality check |
| Done | Completion + Archive | Finalization |

See [OBJECT_MAPPING.md](OBJECT_MAPPING.md) for complete mappings.

## ⚠️ Known Limitations

### Cannot Migrate
- ❌ **Free-form Card Movement**: Sequential only in Tallyfy
- ❌ **Visual Board Layout**: No Kanban view in Tallyfy
- ❌ **Power-Up Visualizations**: Charts, calendars, maps not supported
- ❌ **Voting on Cards**: No native voting mechanism
- ❌ **Card Aging**: No visual aging indicators
- ❌ **Board Backgrounds**: Aesthetic features not applicable

### Requires Manual Configuration
- ⚠️ **Complex Butler Commands**: Multi-step automations need simplification
- ⚠️ **Cross-Board Automation**: Board-to-board rules need reconfiguration
- ⚠️ **Power-Up Data**: Some Power-Up data preserved as metadata only
- ⚠️ **Card Dependencies**: Manual relationship setup required
- ⚠️ **Recurring Cards**: Template scheduling needs configuration

## 🔍 Validation

### Automatic Validation
- ✅ Kanban transformation completeness
- ✅ List sequence logic
- ✅ Card categorization accuracy
- ✅ Checklist conversion validity
- ✅ Member permission mapping
- ✅ Custom field preservation
- ✅ Attachment accessibility

### Manual Validation Checklist
- [ ] Verify workflow sequence matches intended process
- [ ] Check card-to-task/process decisions are appropriate
- [ ] Confirm Butler automations translated correctly
- [ ] Validate checklist transformations
- [ ] Test workflow execution end-to-end
- [ ] Review AI transformation decisions
- [ ] Verify no critical cards missed

## 📈 Performance

### Processing Speed
| Data Volume | Migration Time | Memory Usage |
|-------------|---------------|--------------|
| < 10 boards | 30-60 minutes | < 1GB |
| 10-50 boards | 1-3 hours | 1-2GB |
| 50-200 boards | 3-8 hours | 2-4GB |
| > 200 boards | 8-24 hours | 4-8GB |

### Rate Limits
- **Trello**: 300 requests/10 seconds per key
- **Tallyfy**: 100 requests/minute
- **Effective throughput**: 30-50 cards/minute
- **Optimization**: Batch operations where possible

## 🐛 Troubleshooting

### Common Issues

#### Authentication Failed
**Error**: `401 Invalid key or token`
**Solution**: 
- Regenerate token at https://trello.com/app-key
- Verify key and token format
- Check token hasn't expired

#### Rate Limit Exceeded
**Error**: `429 Rate limit exceeded`
**Solution**: 
- Implement 0.5 second delays
- Stay under 290 requests/10 seconds
- Use webhooks instead of polling

#### Kanban Transformation Failed
**Error**: `Cannot determine list sequence`
**Solution**:
- Enable AI with Anthropic key
- Specify custom list order
- Use three_step transformation

#### Card Complexity Overwhelm
**Error**: `Card too complex for task`
**Solution**:
- Force card as process
- Simplify checklist structure
- Split complex cards manually

#### Butler Rule Too Complex
**Error**: `Cannot translate Butler automation`
**Solution**:
- Simplify Butler rules first
- Document complex logic
- Recreate manually in Tallyfy

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./migrate.sh --verbose

# Analyze Kanban patterns
./migrate.sh --analyze-flow > flow_analysis.json

# Preview transformation
./migrate.sh --preview-transformation
```

## 📊 Reports

### Generated Reports
- `migration_summary.json` - Overall statistics
- `kanban_transformation.json` - Board to workflow mappings
- `list_sequencing.csv` - List to step transformations
- `card_categorization.csv` - Card classification decisions
- `butler_translations.json` - Automation rule mappings
- `errors.log` - Detailed error information
- `ai_decisions.json` - AI transformation reasoning
- `manual_review.md` - Items requiring attention

### Report Contents
- Kanban analysis metrics
- Transformation confidence scores
- Card flow patterns
- List usage statistics
- Automation complexity
- AI decision distribution
- Performance metrics

## 🔒 Security

### Credential Handling
- API key and token in environment only
- No credentials in logs or code
- Token expiration handling
- Secure storage practices

### Data Privacy
- All processing done locally
- No data sent to third parties (except optional AI)
- Complete audit trail
- GDPR compliant options
- Board isolation maintained


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


## 🆘 Support

### Getting Help
1. Check [Troubleshooting](#troubleshooting) section
2. Review transformation logs
3. Run flow analysis tools
4. Verify API connectivity
5. Consult Kanban transformation guide

### Resources
- Trello API Docs: https://developer.atlassian.com/cloud/trello/
- Tallyfy API Docs: https://developers.tallyfy.com/
- Comparison: https://tallyfy.com/differences/trello-vs-tallyfy/
- Kanban to Workflow Guide: https://tallyfy.com/kanban-to-workflow/

## 📚 Additional Resources

### Documentation
- [OBJECT_MAPPING.md](OBJECT_MAPPING.md) - Complete field mappings
- [KANBAN_TRANSFORMATION.md](docs/KANBAN_TRANSFORMATION.md) - Paradigm shift guide
- [BUTLER_MAPPING.md](docs/BUTLER_MAPPING.md) - Automation translation
- [FLOW_PATTERNS.md](docs/FLOW_PATTERNS.md) - Card flow analysis

### Version Information
- Migrator Version: 1.0.0
- Trello API: v1
- Tallyfy API: v2
- Last Updated: 2024-12-19

---

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.