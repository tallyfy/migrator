# Process Street to Tallyfy Migration Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Migration Orchestrator                      │
│                         (main.py)                                │
└─────────────┬───────────────────────────────────┬───────────────┘
              │                                   │
              ▼                                   ▼
┌──────────────────────────┐       ┌──────────────────────────────┐
│   Process Street API      │       │      Tallyfy API Client      │
│      Extractor            │       │        Importer              │
│  (ps_client.py)           │       │    (tallyfy_client.py)       │
└──────────┬───────────────┘       └───────────┬──────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Data Transformation Layer                      │
│                      (transformers/*.py)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Organization │  │   Template   │  │   Instance   │          │
│  │ Transformer  │  │ Transformer  │  │ Transformer  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     User     │  │    Forms     │  │    Files     │          │
│  │ Transformer  │  │ Transformer  │  │ Transformer  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────────────────────────┘
           │                                    │
           ▼                                    ▼
┌──────────────────────────┐       ┌──────────────────────────────┐
│    Validation Layer      │       │     Progress Tracker         │
│   (validators/*.py)      │       │    (progress.py)             │
└──────────────────────────┘       └──────────────────────────────┘
```

## Component Specifications

### 1. Migration Orchestrator
**File**: `src/main.py`
- Central control flow management
- Configuration loading
- Migration phase coordination
- Error handling and recovery
- Progress reporting

### 2. API Clients

#### Process Street Client
**File**: `src/api/ps_client.py`
- Authentication management
- Rate limiting (429 handling)
- Pagination (20 items/page)
- Data extraction methods for all objects
- CSV export handling

#### Tallyfy Client  
**File**: `src/api/tallyfy_client.py`
- OAuth2 authentication
- Batch import operations
- Error handling with retry logic
- Multi-tenant support
- Progress callbacks

### 3. Data Transformers
**Directory**: `src/transformers/`
- `organization_transformer.py` - Organization mapping
- `template_transformer.py` - Workflow to Checklist conversion
- `instance_transformer.py` - Run to Process mapping
- `user_transformer.py` - User and permission mapping
- `form_transformer.py` - Form field type conversion
- `file_transformer.py` - File migration to S3

### 4. Validators
**Directory**: `src/validators/`
- Pre-migration validation
- Post-migration verification
- Data integrity checks
- Relationship validation
- Constraint verification

### 5. Utilities
**Directory**: `src/utils/`
- `logger.py` - Structured logging
- `id_mapper.py` - ID mapping and tracking
- `file_handler.py` - File download/upload
- `config.py` - Configuration management
- `retry.py` - Retry logic with exponential backoff

## Migration Strategy

### Phase 1: Discovery & Planning (30 minutes)
1. Connect to Process Street API
2. Enumerate all organizations
3. Count all objects per organization
4. Generate migration plan
5. Estimate time and resources

### Phase 2: Foundation Migration (1-2 hours)
1. Create/verify Tallyfy organization
2. Migrate users with role mapping
3. Create groups/teams
4. Set up permissions matrix
5. Validate user access

### Phase 3: Template Migration (2-4 hours)
1. Extract all workflows/templates
2. Transform to Tallyfy checklist format
3. Convert form fields and types
4. Map conditional logic
5. Create template versions
6. Validate template structure

### Phase 4: Active Data Migration (4-8 hours)
1. Extract all workflow runs
2. Map to Tallyfy processes
3. Preserve task states
4. Migrate form data
5. Maintain progress tracking
6. Handle in-flight workflows

### Phase 5: Collaborative Data (2-3 hours)
1. Migrate comments with threading
2. Transfer file attachments to S3
3. Map activity history
4. Preserve timestamps

### Phase 6: Integration Migration (1-2 hours)
1. Recreate webhooks
2. Update API endpoints
3. Test integrations
4. Verify external connections

### Phase 7: Validation & Cleanup (1-2 hours)
1. Run validation suite
2. Generate migration report
3. Clean up temporary data
4. Document any issues

## Configuration Schema

```yaml
# config/migration_config.yaml
source:
  api_key: "process_street_api_key"
  base_url: "https://public-api.process.st"
  organization_id: "org_id"
  
target:
  api_url: "https://api.tallyfy.com"
  client_id: "oauth_client_id"
  client_secret: "oauth_client_secret"
  organization_id: "tallyfy_org_id"
  
migration:
  batch_size: 100
  retry_attempts: 3
  retry_delay: 5
  timeout: 30
  
  phases:
    - users
    - templates
    - instances
    - comments
    - files
    - webhooks
    
  options:
    preserve_ids: true
    skip_validation: false
    dry_run: false
    parallel_workers: 4
    
storage:
  temp_dir: "/migrator/data/temp"
  mapping_db: "/migrator/data/mappings.db"
  log_dir: "/migrator/logs"
  
logging:
  level: "INFO"
  format: "json"
  file: "migration_{timestamp}.log"
```

## Error Handling Strategy

### Retry Logic
```python
# Exponential backoff with jitter
retry_delays = [5, 10, 20, 40, 80]
max_retries = 5
```

### Error Categories
1. **Recoverable**: Rate limits, timeouts, network errors
2. **Data Errors**: Validation failures, constraint violations
3. **Critical**: Authentication failures, API changes
4. **Warnings**: Missing optional data, deprecated features

### Recovery Mechanisms
- Checkpoint-based resume
- Transaction rollback
- Partial migration support
- Manual intervention points

## Performance Optimization

### Batch Processing
- Organizations: Sequential (1 at a time)
- Users: Batches of 100
- Templates: Batches of 50
- Instances: Batches of 20
- Files: Parallel upload (4 workers)

### Caching Strategy
- User ID mappings
- Template ID mappings
- Frequently accessed metadata
- API responses (5-minute TTL)

### Rate Limiting
- Process Street: Respect 429 responses
- Tallyfy: 100 requests/minute
- File uploads: 4 concurrent
- Implement token bucket algorithm

## Security Considerations

### Credential Management
- Environment variables for secrets
- No hardcoded credentials
- Secure token storage
- Audit trail for all operations

### Data Protection
- Encrypt sensitive data in transit
- Secure temporary file storage
- Clean up after migration
- No logging of PII

### Access Control
- Minimal permission requirements
- Service account usage
- API key rotation support
- Multi-factor authentication

## Monitoring & Observability

### Metrics
- Objects migrated per type
- Success/failure rates
- API call counts
- Processing time per phase
- Error frequency

### Logging
- Structured JSON logs
- Correlation IDs
- Request/response logging
- Error stack traces
- Progress milestones

### Alerts
- Migration start/complete
- Critical errors
- Rate limit warnings
- Validation failures
- Manual intervention required

## Testing Strategy

### Unit Tests
- Transformer logic
- Validation rules
- API client methods
- Utility functions

### Integration Tests
- API connectivity
- End-to-end data flow
- Error handling
- Recovery mechanisms

### Migration Tests
- Dry run mode
- Sample data migration
- Rollback procedures
- Performance benchmarks

## Deployment

### Requirements
```
Python 3.9+
PostgreSQL (for mapping database)
Redis (for caching)
4GB RAM minimum
10GB disk space
```

### Docker Support
```dockerfile
FROM python:3.9-slim
WORKDIR /migrator
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/main.py"]
```

### Command Line Interface
```bash
# Full migration
python migrator.py --config config.yaml

# Dry run
python migrator.py --config config.yaml --dry-run

# Specific phase
python migrator.py --config config.yaml --phase users

# Resume from checkpoint
python migrator.py --config config.yaml --resume

# Validation only
python migrator.py --config config.yaml --validate-only
```

## Rollback Procedures

### Checkpoint System
- Save state after each phase
- Store ID mappings
- Track migrated objects
- Enable selective rollback

### Rollback Commands
```bash
# Full rollback
python migrator.py --rollback --config config.yaml

# Phase rollback
python migrator.py --rollback --phase instances

# Partial rollback
python migrator.py --rollback --from-checkpoint checkpoint_3
```

## Success Criteria

### Functional Requirements
- ✅ 100% data migration completeness
- ✅ No data corruption
- ✅ Preserve all relationships
- ✅ Maintain data integrity
- ✅ Support resume capability

### Performance Requirements
- ✅ < 24 hours for 10,000 workflows
- ✅ < 1% error rate
- ✅ 99.9% data accuracy
- ✅ Minimal API rate limiting
- ✅ Efficient resource usage

### Operational Requirements
- ✅ Comprehensive logging
- ✅ Progress visibility
- ✅ Error recovery
- ✅ Rollback capability
- ✅ Documentation completeness