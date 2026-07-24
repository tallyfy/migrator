# AI Assistant Instructions for Migrator Development

> **NEVER use auto memory** (`~/.claude/projects/*/memory/`) — store all knowledge in this repo's CLAUDE.md file.


## Overview
This directory contains production-ready migration tools to help organizations migrate from various workflow/BPM/forms vendors to Tallyfy. Each migrator is completely independent and includes AI-powered decision capabilities for handling ambiguous cases.

## 🏗️ System Architecture

### Core Architecture Layers
```
┌─────────────────────────────────────┐
│     Orchestration Layer (main.py)   │  5-phase migration controller
├─────────────────────────────────────┤
│    Transformation Layer             │  Field, template, user transformers
├─────────────────────────────────────┤
│         API Layer                   │  Vendor & Tallyfy clients
├─────────────────────────────────────┤
│        Utility Layer                │  Checkpoint, validation, logging
├─────────────────────────────────────┤
│    AI Augmentation Layer           │  Claude/GPT with fallbacks
└─────────────────────────────────────┘
```

### Design Principles
- **Complete Independence**: Each migrator is 100% self-contained
- **5-Phase Migration**: Standardized flow across all vendors
- **AI-Augmented Decisions**: Optional AI for complex transformations
- **Paradigm Shift Handling**: Intelligent conversion between workflow models
- **Resilient Design**: Checkpoint/resume, error recovery, rate limiting

## What We've Learned - Real-World AI Integration Patterns

### Successful AI Use Cases from Production

#### 1. Paradigm Shift Transformation (Pipefy, Monday.com)
**Challenge**: Converting Kanban boards with parallel work to sequential workflows
**AI Solution**: Analyzes board structure and recommends optimal transformation
**Implementation**:
```python
# Each Kanban phase becomes 3 sequential steps
def transform_kanban_phase(phase):
    return [
        {"name": f"{phase} - Entry", "type": "task"},
        {"name": f"{phase} - Work", "type": "task"},  
        {"name": f"{phase} - Exit", "type": "approval"}
    ]
```
**Fallback**: Standard 3-step pattern per phase

#### 2. Complex Form Splitting (Forms Applications)
**Challenge**: Forms with 50+ fields overwhelm users in single screen
**AI Solution**: Intelligently groups fields into logical workflow steps
**Implementation**:
- ≤20 fields → Single kick-off form
- 21-50 fields → Multi-step workflow
- >50 fields → AI-analyzed complex workflow
**Fallback**: Split every 10 fields into separate steps

#### 3. Custom Field Mapping (Monday.com's 30+ Types)
**Challenge**: Vendor-specific field types with no direct equivalent
**AI Solution**: Analyzes field name, content, and usage to find best match
**Examples**:
- Timeline → Date (start) + Date (end)
- Mirror → Short Text (readonly) with reference note
- Formula → Short Text (readonly) with calculation preserved
**Fallback**: Map to short_text with validation rules

#### 4. Conditional Logic Translation (Process Street)
**Challenge**: Complex if/then rules need Tallyfy rule engine format
**AI Solution**: Parses conditions and generates Tallyfy rule configuration
**Fallback**: Flag complex conditions for manual review

#### 5. Batch Size Optimization (High-Volume Migration)
**Challenge**: Balance between API limits, memory, and speed
**AI Solution**: Analyzes data characteristics for optimal batch size
**Fallback**: Conservative batching (10-50 items based on size)

## Tallyfy API Contract: Kick-off ("prerun") Data

**The launch request key is `prerun`. It is NOT `prerun_data`.** The API reads
`prerun` (`RunRequestValidator` reads `prerun` and `prerun.<timeline_id>`), so a body
carrying `prerun_data` is silently ignored: every kick-off value is discarded, and any
required kick-off field fails the launch with a 422.

**Its value is an OBJECT keyed by each kick-off field's 32-char `timeline_id`** -- never a
list, and never keyed by field name, label, or the source system's field id:

```json
{"prerun": {"a1b2c3d4e5f60718293a4b5c6d7e8f90": "Acme Corp"}}
```

Do not confuse this with template *creation*, where `prerun` is legitimately an array of
field **definitions**. At launch it is an object of field **values**.

**Per-field value shapes are type-dependent** (see `shared/prerun_encoder.py`, which
mirrors the proven middleware implementation):

| field_type | value |
|---|---|
| `text`, `textarea`, `email` | bare scalar |
| `date` | bare scalar, ISO-8601 string |
| `radio` | the chosen option's **text**, as a bare scalar |
| `dropdown` | `{"id": <option id>, "text": "<exact option text>"}` (both keys required) |
| `multiselect` | list of `{"id":.., "text":..}`, each with `"selected": true` |
| `table` | list with exactly one entry per defined column |
| `assignees_form` | `{"users": [int], "guests": ["email"], "groups": [id]}` |

`dropdown` and `radio` are deliberately **asymmetric**. Do not "harmonise" them.

Use `shared/prerun_encoder.py` (`build_prerun_payload`) rather than stringifying values --
stringifying breaks dropdown, multi-select, table and assignee fields. It needs the
template's kick-off field definitions to resolve source keys to `timeline_id`; without
them the keys pass through unchanged and the API discards the data.

Fetch those definitions with `shared/kickoff_fields.py` (`KickoffFieldCache`), which reads
the checklist's inlined `prerun` array -- each entry's `id` **is** the `timeline_id`
(`PrerunTransformer` maps `'id' => $prerun->timeline_id`). The adjacent `alias` is a trap:
keying by it returns 201 with `prerun: {}` and every value lost.

Pass `strict=True` on live paths. A dropped key is invisible -- the launch still returns
201 -- so a silent encoder is silent data loss.

### ⚠️ Known gap: templates are created WITHOUT kick-off fields

**No vendor currently creates kick-off fields on a Tallyfy template.** Every template is
created with an empty `prerun` array, so there is nothing for launch values to key against.

- `add_kickoff_form()` exists in 11 vendor clients (e.g. `typeform/src/api/tallyfy_client.py:234`,
  POSTing to `/checklists/{id}/preruns`) and has **zero callers**. It looks like the intended
  implementation, never wired into any orchestrator.
- `create_checklist()` POSTs only `{id,title,summary,organization_id,status,is_template}`.
  The `kickoff_form` dict that template transformers build is silently dropped.
- Step `captures` (form fields on a step) ARE created. Those are a different thing from
  template-level kick-off fields -- do not conflate them.

Until `add_kickoff_form` is wired, the instance/launch phase for a form vendor will
correctly raise `NoKickoffFieldsDefined` rather than launch processes whose kick-off data
would be discarded. Fixing that is the prerequisite for kick-off data migrating at all.

`shared/tests/test_prerun_request_key.py` pins the request key across every vendor client.
`shared/tests/test_prerun_wiring.py` pins that the encoder is actually REACHED on live
paths and that keys are timeline_ids -- the request-key test alone passed for months while
every live path still sent source-system ids.

## Tallyfy API Contract: form-field values on an EXISTING process

Kick-off data rides `prerun` at LAUNCH. Writing a value onto a process that already
exists is a **different contract**, and the routes the migrators used for it until
2026-07 (`/runs/{run}/field/{capture}/value`, `/runs/{run}/captures/{capture}/value`,
`/runs/{run}/fields/{field}/value`) **do not exist**. Neither does the `{"value": ...}`
body wrapper they sent. There are exactly two real endpoints:

**1. Single value** -- `PUT /organizations/{org}/form-field/value`

```json
{"id": "<capture-value id>", "form_value": "<typed value>"}
```

`id` is the id of the **capture value row** (`core.leads`), which the API resolves with
`CaptureValue::find($data['id'])`. It is NOT a capture/field definition id and NOT a
`timeline_id`.

**Capture-value ids are not discoverable through the API**, so a migration cannot use
this endpoint as its main path: the two places that would expose one
(`Task::allFormFields()` and `RunTransformer::includeKoFormFields()`) have their
`$field->unique_id = $lead->id` assignment commented out, so `unique_id` is always null
in responses. Every vendor client exposes it as `set_form_field_value()` for callers
that already hold a capture-value id from elsewhere.

**2. Bulk, per task (THE migration path)** --
`PUT /organizations/{org}/runs/{run_id}/tasks/{task_id}`

```json
{"taskdata": {"<capture timeline_id>": "<typed value>"}}
```

This is the canonical bulk writer (`Task::setTaskdataAttribute` ->
`Task::updateCaptureValues`) and it keys by `timeline_id`, which **is** discoverable:
`GET /organizations/{org}/runs/{run_id}/form-fields` returns every field with `id` (which
IS the `timeline_id`), `field_type`, `options`, `columns` and `task_id`. Step fields come
back under `form_fields`, kick-off fields under `ko_form_fields`.

Like `prerun`, it ignores any key that is not a `timeline_id` **and still returns 200** --
so a wrong key is silent data loss, not an error.

Use `shared/form_field_values.py` (`extract_run_form_fields` + `build_task_form_field_payloads`).
It resolves source keys against the live fields and groups them into per-task `taskdata`,
reusing `prerun_encoder`'s `encode_field_value` -- the per-type shapes are identical on both
paths, so there is exactly ONE encoder. It is strict by default: an unresolvable value
raises instead of being skipped.

`shared/tests/test_form_field_values.py` pins the wire contract for every vendor client and
drives the two live migration paths end to end.

### ⚠️ Blocking gap: form fields are never CREATED, so there is nothing to write to

The value-write contract above is correct and implemented, but it cannot complete
end to end yet, because **no migrator can create a form field on a Tallyfy template**:

- `create_capture()` posts to `/{entity_type}s/{entity_id}/field`. **No such route exists.**
  api-v2 serves capture creation only at `runs/{run}/tasks/{task}/captures`
  (`TaskCapturesController::store`) and `tasks/{task_id}/form-fields`
  (`OneOffTasks\TaskFormFieldsController::store`) -- both on task INSTANCES, neither
  on a template step.
- The payload shape is wrong too. `FieldTransformer` emits `type` (the API wants
  `field_type`), maps selects to `select` (the API wants `dropdown`), and nests
  options under `config` as `value`/`label` (the API wants top-level `options`
  with `id`/`text`).
- This is the same family as the `add_kickoff_form()` gap above: the intended code
  exists but was never reachable, so the failure has been invisible.

Consequence: `GET /runs/{run}/form-fields` comes back empty, so
`build_task_form_field_payloads` raises `UnresolvedFormFieldError` for every value.
**That is the correct behaviour** -- the alternative is a 200 response with the data
silently discarded. Fixing the capture-CREATION contract is the prerequisite for
value migration to complete, and it is a separate workstream from the value-WRITE
contract documented above.

### ⚠️ Value writes must fail LOUDLY

The pipefy path wrapped every field in `except Exception: logger.warning(...)`. Combined
with a call-arity bug (`transform_field_value(field)` against a two-argument signature),
**every single field raised `TypeError`, was downgraded to a warning, and the migration
printed a success summary with 100% of field values lost.** A failed value write must
propagate; the phase loop already counts the failure and honours `continue_on_error`.

## Critical Rules for All Migrators

### 1. Independence Rule (MANDATORY)
**EACH MIGRATOR FOLDER IS COMPLETELY INDEPENDENT**
- NEVER mention other vendors in README or documentation
- NEVER add "see also" or "similar to" references to other migrators
- NEVER include "coming soon" lists of other vendors
- Treat each migrator as if it's the only one that exists
- Each migrator must be fully self-contained and standalone

### 2. AI Integration (MANDATORY)
Every migrator MUST include AI augmentation capabilities:
- Customer provides their own Anthropic API key
- AI enhances difficult migration decisions
- All prompts stored in `prompts/` folder for editability
- Keep prompts focused (<500 tokens) with JSON responses
- ALWAYS provide deterministic fallbacks when AI unavailable

### 3. Documentation Standards
Every migrator MUST have:
- **README.md** with ALL 18 required sections (including AI features)
- **OBJECT_MAPPING.md** with exhaustive terminology mappings
- **.env.example** with AI configuration section
- **migrate.sh** executable script
- Comparison URL: https://tallyfy.com/differences/[vendor]-vs-tallyfy/

## Directory Structure Pattern

```
/migrator/[vendor-name]/
├── src/
│   ├── api/
│   │   ├── [vendor]_client.py      # Vendor API client
│   │   ├── tallyfy_client.py       # Tallyfy API client
│   │   └── ai_client.py            # Anthropic AI client
│   ├── transformers/
│   │   ├── field_transformer.py    # Field type mappings
│   │   ├── template_transformer.py # Template/form transformation
│   │   ├── user_transformer.py     # User/team transformation
│   │   └── ai_decision_maker.py   # AI-powered decisions
│   ├── prompts/                    # Editable AI prompts
│   │   ├── assess_form_complexity.txt
│   │   ├── map_ambiguous_field.txt
│   │   ├── determine_workflow_steps.txt
│   │   └── analyze_conditional_logic.txt
│   ├── utils/
│   │   ├── id_mapper.py           # SQLite ID mapping
│   │   ├── checkpoint_manager.py  # Resume capability
│   │   ├── progress_tracker.py    # Progress monitoring
│   │   └── error_handler.py       # Error recovery
│   └── main.py                     # 5-phase orchestrator
├── tests/
│   └── test_transformers.py       # With AI fallback tests
├── migrate.sh                      # Executable script
├── .env.example                    # With AI config
├── README.md                       # 18 sections
└── OBJECT_MAPPING.md              # Complete mappings
```

## AI Integration Strategy

### When to Use AI
**USE AI FOR:**
- Form complexity assessment (simple vs multi-stage)
- Ambiguous field type determination
- Workflow step generation from complex forms
- Large dataset handling strategies
- Conditional logic interpretation
- Paradigm shift transformations (Kanban→Sequential)

**DON'T USE AI FOR:**
- Direct 1:1 mappings
- Simple user migration
- Basic field transformations
- API calls
- Error handling

### AI Prompt Templates
All prompts must:
- Be stored in `prompts/` folder
- Use placeholder variables: `{field_name}`, `{field_count}`, etc.
- Request JSON responses only
- Be under 500 tokens
- Include confidence scores

### Example AI Client Implementation
```python
class AIClient:
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.enabled = bool(self.api_key)
        if self.enabled:
            self.client = Anthropic(api_key=self.api_key)
            
    def make_decision(self, prompt_file, context):
        if not self.enabled:
            return self._fallback_decision(prompt_file, context)
        # Load prompt, make API call, return decision
```

## 5-Phase Migration Architecture

All migrators follow this pattern:

### Phase 1: Discovery
- Fetch all data from source
- Assess complexity (with AI if available)
- Generate migration plan

### Phase 2: Users
- Migrate users and teams
- Map roles and permissions
- Establish ID mappings

### Phase 3: Templates/Forms
- Transform templates/workflows/forms
- Use AI for complex form decisions
- Handle paradigm shifts

### Phase 4: Instances
- Migrate running instances/submissions
- Use AI for ambiguous field mappings
- Preserve relationships

### Phase 5: Validation
- Verify data integrity
- Check ID mappings
- Generate report

## Paradigm Shifts

### Critical Transformations

#### Kanban → Sequential (Pipefy, Trello, etc.)
- Each column becomes multiple steps
- Parallel work becomes sequential
- Card movement becomes task completion
- AI assists in optimal step generation

#### Forms → Workflows (Typeform, Google Forms, etc.)
- Simple forms (≤20 fields) → Kick-off form
- Complex forms (>20 fields) → Multi-step workflow
- AI determines optimal structure
- Conditional logic preserved as rules

#### Hybrid Views → Sequential (Monday.com, Asana)
- Detect primary view type
- Apply view-specific transformation
- Document paradigm changes
- AI helps with complex mappings

## Required README Sections

1. **Requirements** - Include Anthropic API key
2. **Installation** - Step-by-step setup
3. **Configuration** - AI configuration details
4. **Quick Start** - With/without AI
5. **Architecture** - 5-phase pattern
6. **AI-Powered Features** - What AI enhances
7. **Data Mapping** - Link to OBJECT_MAPPING.md
8. **API Integration** - Authentication details
9. **Features** - Core capabilities
10. **Usage Examples** - Common scenarios
11. **Paradigm Shifts** - Critical transformations
12. **Limitations** - What cannot migrate
13. **Migration Process** - Phase details
14. **Error Handling** - Recovery strategies
15. **Performance** - Time estimates
16. **Troubleshooting** - Common issues
17. **Best Practices** - Recommendations
18. **Support** - Getting help

## Testing Requirements

Every migrator must test:
- AI availability detection
- Fallback functionality without AI
- Field mapping accuracy
- Paradigm shift handling
- Checkpoint/resume capability
- Rate limit recovery
- Batch processing

## Performance Guidelines

### With AI
- Haiku model: ~100-200 decisions/minute
- Sonnet model: ~50-100 decisions/minute
- Cache AI decisions when possible
- Batch similar decisions

### Without AI
- Deterministic fallbacks
- Heuristic-based decisions
- Manual review flags for uncertain mappings

## Common Patterns

### Form Complexity Assessment
```python
if ai_enabled:
    complexity = ai.assess_form_complexity(form)
    if complexity['strategy'] == 'simple_kickoff':
        return transform_to_kickoff(form)
    elif complexity['strategy'] == 'multi_step':
        return transform_to_workflow(form)
else:
    # Fallback heuristics
    if len(form.fields) <= 20:
        return transform_to_kickoff(form)
    else:
        return transform_to_workflow(form)
```

### Ambiguous Field Mapping
```python
if field_type not in DIRECT_MAPPINGS:
    if ai_enabled:
        mapping = ai.map_field(field)
        if mapping['confidence'] > 0.7:
            return mapping['tallyfy_type']
    # Fallback to best guess
    return guess_field_type(field)
```

## Error Handling

All migrators must:
- Log AI decisions with confidence scores
- Flag low-confidence mappings for review
- Continue without AI if unavailable
- Provide clear error messages
- Support checkpoint/resume

## Best Practices

1. **Research First**: Deep vendor API understanding
2. **Identify AI Value**: Where AI adds most value
3. **Focused Prompts**: Specific, structured responses
4. **Graceful Fallbacks**: Always have non-AI path
5. **Document Everything**: Especially paradigm shifts
6. **Test Both Paths**: With and without AI
7. **Cache Decisions**: Reuse AI responses when possible

## Development Workflow

1. **Research vendor thoroughly**
   - API documentation
   - Data models
   - Paradigm understanding

2. **Identify AI decision points**
   - Complex mappings
   - Ambiguous transformations
   - Optimization opportunities

3. **Implement with fallbacks**
   - AI-enhanced path
   - Deterministic fallback
   - Manual review flags

4. **Test comprehensively**
   - With AI enabled
   - Without AI (fallbacks)
   - Edge cases

5. **Document completely**
   - All 18 README sections
   - Exhaustive OBJECT_MAPPING.md
   - AI features clearly explained

## Current Migrators

### ✅ Production Ready (15/15) - ALL COMPLETE

#### Workflow Management Platforms
- **Process Street**: Complete workflow automation, conditional logic, variables, approvals
- **Pipefy**: GraphQL API, Kanban→Sequential paradigm shift, phase connections
- **Asana**: Hybrid views (list/board/timeline/calendar), project hierarchy, custom fields, dependencies
- **Kissflow**: Multi-module platform (processes, forms, cases, boards, datasets), complex approval chains
- **Monday.com**: 30+ field types, GraphQL complexity management, multiple view transformations
- **ClickUp**: Deep hierarchy (Team→Space→Folder→List), 14+ view types, custom fields
- **Wrike**: Complex folder nesting, project templates, custom workflows, time tracking
- **Basecamp**: Project-centric tools (todos, messages, docs, schedule), OAuth2 refresh
- **Trello**: REST API v1, board/list/card structure, Power-Ups, Butler automation

#### Form Platforms
- **Typeform**: Logic jumps, variables, calculations, complex branching
- **JotForm**: Multi-page forms, conditions, calculations, payment processing, appointments
- **Google Forms**: OAuth2/service accounts, Google Drive integration, form watches
- **Cognito Forms**: Advanced calculations, repeating sections, payment integration

#### Specialized Platforms
- **NextMatter**: Process templates, stage gates, integrations, approval workflows
- **RocketLane**: Customer onboarding, resource allocation, project templates, time tracking

## 🏭 Production Infrastructure (COMPLETE)

### Shared Components
All migrators leverage these production-ready shared components:

#### Checkpoint & Resume
- **Checkpoint Manager**: Save progress and resume interrupted migrations
- **ID Mapping**: SQLite-based tracking of migrated entities
- **Progress Tracking**: Monitor migration status and statistics

### Production Features by Vendor

#### Rate Limiting Strategies
Each vendor has specific rate limit handling:
- **Monday.com**: GraphQL complexity points (10M/min) with automatic query simplification
- **Asana**: 150 req/min with burst handling
- **Pipefy**: 100 req/min with GraphQL query batching
- **ClickUp**: 100 req/min with automatic backoff
- **Wrike**: 100 req/min with retry-after header respect
- **Basecamp**: 50 req/10s with OAuth token refresh
- **Trello**: 300 req/10s, 10K/hour dual limits
- **Process Street**: 60 req/min with conditional retry
- **Typeform**: 120 req/min with burst control
- **JotForm**: 10K req/day with daily reset tracking
- **Google Forms**: 300 req/min with service account rotation

#### Authentication Methods
Comprehensive auth support per platform:
- **OAuth2 with refresh**: Basecamp, Google Forms
- **Bearer tokens**: Asana, ClickUp, Wrike, Typeform
- **API Keys**: Process Street, Pipefy, Trello, JotForm
- **Service Accounts**: Google Forms (alternative)
- **Permanent Tokens**: Monday.com, Kissflow

### Forms-Focused Migration Strategy
Forms applications require special AI consideration:
- Assess if form should be kick-off or multi-step workflow
- Analyze conditional logic complexity
- Determine optimal workflow structure
- Map custom field types intelligently
- Group fields logically for better UX

## 🎯 Implementation Quick Start

### Step 1: Copy Template Structure
```bash
# Copy from a similar migrator (workflow vs forms)
cp -r process-street/ new-vendor/
cd new-vendor/
```

### Step 2: Update Core Files
1. Rename all vendor references in code
2. Update API authentication in `vendor_client.py`
3. Map vendor objects in `OBJECT_MAPPING.md`
4. Configure `.env.example` with vendor credentials

### Step 3: Implement 5 Phases
```python
# main.py orchestrator pattern
def migrate():
    phase1_discovery()  # Fetch & analyze
    phase2_users()      # Users & teams
    phase3_templates()  # Templates/forms
    phase4_instances()  # Active data
    phase5_validate()   # Verify migration
```

### Step 4: Add AI Decision Points
- Form complexity assessment
- Field type mapping
- Workflow structure determination
- Conditional logic interpretation

### Step 5: Test & Document
- Test with AND without AI
- Complete all 18 README sections
- Verify checkpoint/resume works
- Add integration tests

## 🔧 Troubleshooting Guide

### Common Issues & Solutions

#### Rate Limiting
- **Problem**: API rate limit exceeded
- **Solution**: Implement exponential backoff, use checkpoint manager
- **Code**: See `error_handler.py` retry logic

#### Memory Issues (Large Migrations)
- **Problem**: OOM with 10,000+ items
- **Solution**: Process in batches, clear objects between iterations
- **Batch Size**: 100 items default, adjust based on object size

#### Field Mapping Conflicts
- **Problem**: Vendor field type has no Tallyfy equivalent
- **Solution**: Use AI for intelligent mapping, fallback to text field
- **Pattern**: Timeline → Date(start) + Date(end)

#### Paradigm Shift Confusion
- **Problem**: Kanban boards don't map to sequential workflows
- **Solution**: Each column → 3 steps (Entry, Work, Exit)
- **Documentation**: Always explain paradigm shifts clearly

## 📊 Performance Optimization

### Batch Processing Guidelines
```python
BATCH_SIZES = {
    'users': 100,        # Light objects
    'templates': 50,     # Medium complexity
    'instances': 25,     # Heavy with data
    'attachments': 10    # Large files
}
```

### API Call Optimization
- **Parallel Fetching**: Use asyncio for independent calls
- **Caching**: Cache user mappings, field types
- **Pagination**: Handle vendor-specific pagination patterns
- **Rate Limiting**: Respect vendor limits (1-2s between calls)

### Memory Management
```python
# Clear large objects between batches
del large_response
gc.collect()
```

## 🔐 Security Best Practices

### API Key Management
- Store in `.env` file (never commit)
- Support multiple auth methods (OAuth2, API keys)
- Validate credentials before migration
- Clear tokens after completion

### Data Privacy
- Log minimal PII
- Sanitize logs before sharing
- Support data residency requirements
- Implement audit trails

## 📈 Migration Strategies

### Small Organizations (<100 users, <50 templates)
- Run complete migration in one session
- No need for checkpoint/resume
- Use default batch sizes

### Medium Organizations (100-1000 users, 50-500 templates)
- Enable checkpoint/resume
- Run in phases if needed
- Monitor progress closely
- Consider off-hours migration

### Large Organizations (1000+ users, 500+ templates)
- Mandatory checkpoint/resume
- Phase migration over days/weeks
- Pilot with subset first
- Use AI for optimization decisions

## 🧪 Testing Requirements

### Unit Tests
- Field transformer mappings
- AI fallback mechanisms
- Error handling paths
- Checkpoint/resume logic

### Integration Tests
- Full 5-phase flow
- API authentication
- Rate limit handling
- Large dataset processing

### Test Data
```python
# Create test fixtures
test_data/
├── small_dataset.json   # 10 items
├── medium_dataset.json  # 100 items
├── large_dataset.json   # 1000 items
└── edge_cases.json      # Complex scenarios
```

## 📝 Code Quality Standards

### Python Best Practices
- Type hints for all functions
- Docstrings with examples
- Error handling with context
- Logging at appropriate levels
- PEP 8 compliance

### Git Workflow
- Feature branches for new migrators
- Atomic commits with clear messages
- PR template compliance
- Code review before merge


## Key Success Metrics

- ✅ Migration works without AI (fallbacks)
- ✅ AI improves quality when available
- ✅ Clear documentation of paradigm shifts
- ✅ Comprehensive field mappings
- ✅ Production-ready error handling
- ✅ Resume capability for large migrations
- ✅ <2% data loss/corruption rate
- ✅ Customer can self-serve migration

## 🎉 Production Accomplishments

### What's Been Built (ALL COMPLETE)
All 15 migrators now have:
- ✅ **Production API Clients**: Real endpoints, not templates
- ✅ **Vendor-Specific Rate Limiting**: From 50 req/10s to 10M complexity points
- ✅ **Authentication Methods**: OAuth2, API keys, bearer tokens, service accounts
- ✅ **Complexity Analysis**: Every client has paradigm shift helpers
- ✅ **Field Type Mapping**: 200+ mappings across all platforms
- ✅ **Batch Operations**: Optimized for each vendor's limits
- ✅ **Error Recovery**: Exponential backoff with retries
- ✅ **Data Export**: Complete `get_all_data()` implementations

### Infrastructure Components (COMPLETE)
- **Checkpoint System**: Resume capability for interrupted migrations
- **ID Mapping**: SQLite-based tracking of migrated entities
- **Error Recovery**: Exponential backoff and retry mechanisms

### Paradigm Shift Implementations
Each vendor includes specific transformation helpers:
- **Kanban → Sequential**: Pipefy, Trello (3 steps per column)
- **Forms → Workflows**: All form platforms (complexity-based splitting)
- **Projects → Processes**: Asana, Basecamp, Wrike
- **Multi-View → Single**: Monday.com, ClickUp (view analysis)
- **Modules → Templates**: Kissflow (module distribution analysis)

### Rate Limit Implementations by Vendor
- **GraphQL Complexity**: Monday.com (10M points/min), Pipefy (100 req/min)
- **Dual Limits**: Trello (300/10s + 10K/hour)
- **Daily Limits**: JotForm (10K/day with reset tracking)
- **Burst Control**: Typeform (120/min with 10 burst)
- **OAuth Refresh**: Basecamp (50/10s with token refresh)
- **Per-Second**: Google Forms (10/sec), Wrike (5/sec)

## Remember

Each migrator is a complete, standalone, production-ready solution. All 15 platforms have actual API implementations, not templates. AI enhances but doesn't replace core logic. Always provide fallbacks. Document everything. Test both paths. The goal is to enable customers to successfully migrate their data with minimal support.