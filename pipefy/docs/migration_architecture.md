# Pipefy to Tallyfy Migration Architecture

## System Overview

The Pipefy migration system handles the complex transformation from a GraphQL-based Kanban card system to Tallyfy's REST-based sequential checklist model. This requires sophisticated data transformation and external system integration.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Migration Orchestrator                        │
│                         (main.py)                                │
└─────────────┬──────────────────────────────┬────────────────────┘
              │                              │
              ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│   Pipefy GraphQL Client  │    │    Tallyfy REST Client       │
│   (pipefy_client.py)     │    │    (tallyfy_client.py)       │
└──────────┬───────────────┘    └───────────┬──────────────────┘
           │                                 │
           ▼                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                 Data Transformation Pipeline                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Phase     │  │     Card     │  │    Table     │          │
│  │ Transformer  │  │ Transformer  │  │  Exporter    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Automation  │  │    Field     │  │  Connection  │          │
│  │   Mapper     │  │ Transformer  │  │   Handler    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────────────────────────┘
           │                                 │
           ▼                                 ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│   External Integrations  │    │    Validation & Rollback     │
│  - Database (PostgreSQL) │    │      (validator.py)          │
│  - File Storage (S3)     │    └──────────────────────────────┘
│  - Automation (n8n/Zapier)│
└──────────────────────────┘
```

## Component Architecture

### 1. GraphQL Client Layer
**File**: `src/api/pipefy_client.py`
- GraphQL query builder and executor
- Pagination handler (50 items max)
- Rate limiting and retry logic
- Introspection for schema discovery
- Bulk query optimization

### 2. Data Extraction Pipeline
**Directory**: `src/extractors/`
- `organization_extractor.py` - Organization data with members
- `pipe_extractor.py` - Pipes with phases and fields
- `card_extractor.py` - Cards with all field values
- `table_extractor.py` - Database tables and records
- `automation_extractor.py` - Automation rules

### 3. Transformation Layer
**Directory**: `src/transformers/`
- `phase_to_step_transformer.py` - Complex phase to step group conversion
- `card_transformer.py` - Card to process mapping
- `field_transformer.py` - Field type conversions
- `automation_transformer.py` - Automation to webhook mapping
- `table_transformer.py` - Database export handler

### 4. External System Handlers
**Directory**: `src/external/`
- `database_handler.py` - PostgreSQL/MySQL integration
- `automation_handler.py` - n8n/Zapier webhook setup
- `file_storage_handler.py` - S3 file migration
- `reporting_handler.py` - BI tool integration

### 5. Migration Orchestrator
**File**: `src/main.py`
- Phase coordination
- Dependency resolution
- Progress tracking
- Error recovery
- Checkpoint management

## GraphQL Query Strategy

### Efficient Data Extraction
```graphql
# Paginated query with nested data
query GetPipeData($pipeId: ID!, $cursor: String) {
  pipe(id: $pipeId) {
    id
    name
    phases {
      id
      name
      fields {
        id
        type
        label
      }
    }
    cards(first: 50, after: $cursor) {
      edges {
        node {
          id
          title
          current_phase { id }
          fields {
            field { id }
            value
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

### Batch Query Optimization
- Group related queries in single request
- Use fragments for repeated structures
- Implement query caching for static data
- Parallel execution where possible

## Phase Transformation Strategy

### The Challenge
Pipefy phases are containers where multiple cards exist simultaneously. Tallyfy steps are sequential tasks that complete. This fundamental difference requires creative transformation.

### Solution: Phase-to-Step-Group Pattern
```python
# Each Pipefy phase becomes a Tallyfy step group:
pipefy_phase = {
    "name": "Review",
    "fields": [...],
    "cards_count": 15
}

# Transforms to:
tallyfy_step_group = {
    "title": "Review Phase",
    "steps": [
        {
            "title": "Enter Review Phase",
            "type": "notification",
            "description": "Card has entered review"
        },
        {
            "title": "Complete Review Fields",
            "type": "form",
            "captures": [...]  # Mapped from phase.fields
        },
        {
            "title": "Review Decision",
            "type": "decision",
            "options": ["Approve", "Reject", "Request Changes"]
        }
    ]
}
```

## Database Table Migration Strategy

Since Tallyfy has no equivalent to Pipefy's database tables:

### Option 1: PostgreSQL Integration (Recommended)
```python
class DatabaseMigrator:
    def migrate_table(self, pipefy_table):
        # 1. Create PostgreSQL table
        create_table_sql = self.generate_create_table(pipefy_table)
        
        # 2. Migrate records in batches
        for batch in self.get_record_batches(pipefy_table.id):
            self.insert_records(batch)
        
        # 3. Create REST API wrapper
        self.deploy_api_wrapper(pipefy_table.id)
        
        # 4. Update Tallyfy webhooks to access data
        self.create_data_webhooks(pipefy_table.id)
```

### Option 2: Airtable Migration
```python
class AirtableMigrator:
    def migrate_table(self, pipefy_table):
        # 1. Create Airtable base
        base = self.create_base(pipefy_table.name)
        
        # 2. Define schema
        self.create_fields(base, pipefy_table.fields)
        
        # 3. Import records
        self.import_records(base, pipefy_table.records)
        
        # 4. Setup Tallyfy integration
        self.configure_webhook_integration(base)
```

## Automation Migration Architecture

### Trigger Mapping Strategy
```python
TRIGGER_MAPPING = {
    "card_created": "process_started",
    "card_moved": "step_completed",
    "card_done": "process_completed",
    "field_updated": "capture_value_changed",
    "card_expired": None,  # Requires external monitoring
    "email_received": None,  # Requires email service
}

class AutomationMigrator:
    def migrate_automation(self, pipefy_automation):
        # 1. Map triggers to Tallyfy events
        tallyfy_trigger = self.map_trigger(pipefy_automation.trigger)
        
        # 2. Convert actions to webhooks
        webhook_config = self.create_webhook_handler(
            pipefy_automation.actions
        )
        
        # 3. Deploy to automation platform
        if self.requires_external_automation(pipefy_automation):
            self.deploy_to_n8n(webhook_config)
        else:
            self.create_tallyfy_webhook(webhook_config)
```

## Connection Handling Strategy

### Card Relationship Management
```python
class ConnectionHandler:
    def __init__(self):
        self.graph_db = Neo4jConnection()  # Or NetworkX for simple cases
    
    def migrate_connections(self, card):
        # 1. Store relationships in graph database
        self.graph_db.create_node(card.id, card.data)
        
        # 2. Create edges for connections
        for parent in card.parent_relations:
            self.graph_db.create_edge(parent.id, card.id, "parent")
        
        # 3. Setup webhooks for relationship events
        self.create_relationship_webhooks(card.id)
        
        # 4. Store references in Tallyfy metadata
        return {
            "metadata": {
                "parent_cards": [p.id for p in card.parent_relations],
                "child_cards": [c.id for c in card.child_relations]
            }
        }
```

## File Migration Strategy

### Large File Handling (up to 512MB)
```python
class FileMigrator:
    def __init__(self):
        self.chunk_size = 50 * 1024 * 1024  # 50MB chunks
    
    def migrate_file(self, pipefy_attachment):
        # 1. Stream download from Pipefy
        file_stream = self.download_stream(pipefy_attachment.url)
        
        # 2. Check size constraints
        if pipefy_attachment.size > TALLYFY_MAX_SIZE:
            # Store in S3, create reference
            s3_url = self.upload_to_s3(file_stream)
            return self.create_file_reference(s3_url)
        
        # 3. Direct upload to Tallyfy
        return self.upload_to_tallyfy(file_stream)
```

## Error Handling & Recovery

### Checkpoint System
```python
class CheckpointManager:
    def __init__(self, migration_id):
        self.migration_id = migration_id
        self.checkpoint_dir = f"data/checkpoints/{migration_id}"
    
    def save_checkpoint(self, phase, data):
        checkpoint = {
            "phase": phase,
            "timestamp": datetime.utcnow().isoformat(),
            "completed_items": data.get("completed", []),
            "failed_items": data.get("failed", []),
            "next_cursor": data.get("cursor"),
            "statistics": data.get("stats", {})
        }
        
        with open(f"{self.checkpoint_dir}/{phase}.json", "w") as f:
            json.dump(checkpoint, f)
    
    def resume_from_checkpoint(self, phase):
        checkpoint_file = f"{self.checkpoint_dir}/{phase}.json"
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, "r") as f:
                return json.load(f)
        return None
```

### GraphQL Error Handling
```python
class GraphQLErrorHandler:
    def handle_error(self, error, query, variables):
        error_type = error.get("extensions", {}).get("code")
        
        if error_type == "RATE_LIMITED":
            wait_time = self.calculate_backoff()
            time.sleep(wait_time)
            return self.retry_query(query, variables)
        
        elif error_type == "TIMEOUT":
            # Reduce query complexity
            simplified_query = self.simplify_query(query)
            return self.retry_query(simplified_query, variables)
        
        elif error_type == "INVALID_TOKEN":
            # Refresh authentication
            self.refresh_token()
            return self.retry_query(query, variables)
        
        else:
            # Log and continue
            self.log_error(error, query, variables)
            return None
```

## Performance Optimization

### Query Batching
```python
class QueryBatcher:
    def __init__(self, max_batch_size=10):
        self.max_batch_size = max_batch_size
        self.query_queue = []
    
    def add_query(self, query, variables):
        self.query_queue.append((query, variables))
        
        if len(self.query_queue) >= self.max_batch_size:
            return self.execute_batch()
    
    def execute_batch(self):
        batched_query = self.combine_queries(self.query_queue)
        results = self.execute_graphql(batched_query)
        self.query_queue = []
        return self.split_results(results)
```

### Parallel Processing
```python
class ParallelMigrator:
    def __init__(self, workers=4):
        self.executor = ThreadPoolExecutor(max_workers=workers)
    
    def migrate_cards_parallel(self, cards):
        futures = []
        for card_batch in self.batch_cards(cards, 20):
            future = self.executor.submit(
                self.migrate_card_batch, card_batch
            )
            futures.append(future)
        
        results = []
        for future in as_completed(futures):
            results.extend(future.result())
        
        return results
```

## Configuration Schema

```yaml
# config/pipefy_migration.yaml
source:
  api_url: "https://api.pipefy.com/graphql"
  api_token: "${PIPEFY_API_TOKEN}"
  organization_id: "${PIPEFY_ORG_ID}"
  
  # GraphQL specific
  graphql:
    max_query_depth: 5
    batch_size: 10
    timeout: 30
    introspection_enabled: true

target:
  # Tallyfy configuration (same as Process Street)
  api_url: "${TALLYFY_API_URL}"
  client_id: "${TALLYFY_CLIENT_ID}"
  client_secret: "${TALLYFY_CLIENT_SECRET}"
  organization_id: "${TALLYFY_ORG_ID}"

external_systems:
  database:
    type: "postgresql"  # postgresql, mysql, airtable
    connection_string: "${DATABASE_URL}"
    
  automation:
    platform: "n8n"  # n8n, zapier, make
    webhook_url: "${AUTOMATION_WEBHOOK_URL}"
    api_key: "${AUTOMATION_API_KEY}"
    
  storage:
    provider: "s3"  # s3, azure, gcs
    bucket: "${S3_BUCKET}"
    region: "${AWS_REGION}"

migration:
  strategies:
    tables: "external_db"  # external_db, csv_export, skip
    automations: "webhook"  # webhook, external_platform, skip
    large_files: "s3_reference"  # direct, s3_reference, skip
    
  transformation:
    phase_model: "step_group"  # step_group, flat_steps
    card_status_mapping: "strict"  # strict, flexible
    field_validation: "warn"  # strict, warn, skip
    
  phases:
    - discovery
    - foundation  # orgs, users, labels
    - structure   # pipes, phases, fields
    - data        # cards, field values
    - external    # tables, automations
    - validation
```

## Monitoring & Observability

### Metrics Collection
```python
class MigrationMetrics:
    def __init__(self):
        self.metrics = {
            "graphql_queries": 0,
            "graphql_errors": 0,
            "rest_calls": 0,
            "transformations": {},
            "external_api_calls": 0,
            "migration_duration": {}
        }
    
    def record_graphql_query(self, query, duration, success):
        self.metrics["graphql_queries"] += 1
        if not success:
            self.metrics["graphql_errors"] += 1
        
        # Track query performance
        query_type = self.extract_query_type(query)
        if query_type not in self.metrics["migration_duration"]:
            self.metrics["migration_duration"][query_type] = []
        self.metrics["migration_duration"][query_type].append(duration)
```

### Progress Tracking
```python
class ProgressTracker:
    def __init__(self, total_cards):
        self.total_cards = total_cards
        self.processed_cards = 0
        self.failed_cards = []
        
    def update_progress(self, card_id, success=True):
        if success:
            self.processed_cards += 1
        else:
            self.failed_cards.append(card_id)
        
        # Calculate metrics
        progress_pct = (self.processed_cards / self.total_cards) * 100
        success_rate = (self.processed_cards / 
                       (self.processed_cards + len(self.failed_cards))) * 100
        
        # Log progress
        logger.info(f"Progress: {progress_pct:.1f}% | Success Rate: {success_rate:.1f}%")
        
        # Update UI/Dashboard
        self.update_dashboard({
            "progress": progress_pct,
            "success_rate": success_rate,
            "failed_items": self.failed_cards
        })
```

## Security Considerations

### Token Management
```python
class SecureTokenManager:
    def __init__(self):
        self.tokens = {}
        self.load_from_env()
    
    def load_from_env(self):
        # Never hardcode tokens
        self.tokens["pipefy"] = os.environ.get("PIPEFY_API_TOKEN")
        self.tokens["tallyfy"] = {
            "client_id": os.environ.get("TALLYFY_CLIENT_ID"),
            "client_secret": os.environ.get("TALLYFY_CLIENT_SECRET")
        }
    
    def get_masked_token(self, service):
        token = self.tokens.get(service)
        if token:
            # Mask for logging
            return token[:4] + "****" + token[-4:]
        return None
```

### Data Encryption
```python
class DataEncryption:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_sensitive_data(self, data):
        # Encrypt PII before storage
        if "email" in data:
            data["email"] = self.cipher.encrypt(
                data["email"].encode()
            ).decode()
        return data
```

## Deployment Architecture

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install GraphQL dependencies
RUN pip install gql requests-toolbelt aiohttp

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "src/main.py"]
```

### Kubernetes Deployment
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pipefy-migration
spec:
  template:
    spec:
      containers:
      - name: migrator
        image: pipefy-migrator:latest
        env:
        - name: PIPEFY_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: pipefy-secrets
              key: api-token
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
      restartPolicy: OnFailure
```

## Success Criteria

### Migration Completeness
- ✅ All active cards migrated
- ✅ All field values preserved
- ✅ User permissions maintained
- ✅ File attachments accessible
- ⚠️ Database tables externally accessible
- ⚠️ Automations recreated or documented
- ✅ Comments and activity preserved

### Performance Targets
- < 100ms per GraphQL query
- < 500ms per card transformation
- < 24 hours for 10,000 cards
- 99% success rate minimum

### Data Integrity
- Zero data loss for required fields
- Relationship preservation in metadata
- Audit trail maintenance
- Rollback capability within 30 days