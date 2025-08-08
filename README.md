# Tallyfy Universal Migration Tool

A comprehensive migration system for importing data from various workflow and form platforms into Tallyfy.

## ⚠️ Important Notice

This is open source software that we are happy to share with the community. While we provide this code freely and are glad to help, **users take full responsibility for running and modifying this software**. Please test thoroughly in a non-production environment before using with production data. No warranty is provided, and users should review the MIT License for full terms and conditions.

## 🚀 Supported Platforms

### Workflow Platforms (15 total)
- ✅ **Asana** - Project and task management
- ✅ **Basecamp** - Project collaboration
- ✅ **ClickUp** - All-in-one productivity platform
- ✅ **Kissflow** - Digital workplace platform
- ✅ **Monday.com** - Work operating system
- ✅ **NextMatter** - Operations automation
- ✅ **Pipefy** - Process management
- ✅ **Process Street** - Checklist and workflow management
- ✅ **RocketLane** - Customer onboarding platform
- ✅ **Trello** - Kanban board system
- ✅ **Wrike** - Collaborative work management

### Form Platforms
- ✅ **Cognito Forms** - Online form builder
- ✅ **Google Forms** - Google's form solution
- ✅ **Jotform** - Online form builder
- ✅ **Typeform** - Conversational forms

## 📋 Features

- **5-Phase Migration System**: Discovery → Mapping → Transformation → Migration → Validation
- **AI-Powered Augmentation**: Optional AI enhancement for intelligent data transformation
- **Checkpoint & Recovery**: Resume interrupted migrations from last successful point
- **Dry Run Mode**: Test migrations without making actual changes
- **Comprehensive Logging**: Detailed logs for debugging and audit trails
- **Rate Limit Management**: Automatic handling of API rate limits
- **Batch Processing**: Efficient handling of large datasets
- **Field Mapping**: Intelligent mapping of vendor fields to Tallyfy fields
- **User Migration**: Transfer users with appropriate roles and permissions
- **Form Response Migration**: Convert form submissions to process instances

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/tallyfy/migrator.git
cd migrator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy and configure environment variables:
```bash
cp .env.template .env
# Edit .env with your API keys and settings
```

## 🔧 Configuration

### Required Environment Variables

Each migrator requires specific API credentials. See `.env.template` for the complete list.

#### Essential for all migrations:
- `TALLYFY_API_KEY` - Your Tallyfy API key
- `TALLYFY_ORGANIZATION` - Your Tallyfy organization ID

#### Platform-specific credentials:
Configure only the platforms you're migrating from. Each platform section in `.env.template` shows the required variables.

### Optional AI Enhancement

For improved migration quality with AI-powered field mapping and data transformation:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- Set `AI_ENABLED=true`

## 📖 Usage

### Basic Migration

Run a complete migration for a specific platform:

```bash
# Navigate to the specific migrator
cd migrator/[platform-name]/src

# Run migration (dry run by default)
python main.py --dry-run

# Run actual migration
python main.py

# Run specific phases only
python main.py --phases discovery mapping

# Resume from checkpoint
python main.py --resume

# Enable verbose logging
python main.py --verbose
```

### Examples by Platform

#### Workflow Platforms

```bash
# Asana migration
cd migrator/asana/src
python main.py --dry-run

# ClickUp migration with specific phases
cd migrator/clickup/src
python main.py --phases discovery mapping transformation

# Monday.com full migration
cd migrator/monday/src
python main.py
```

#### Form Platforms

```bash
# Google Forms migration
cd migrator/google-forms/src
python main.py --dry-run

# Jotform migration with resume
cd migrator/jotform/src
python main.py --resume

# Typeform discovery only
cd migrator/typeform/src
python main.py --phases discovery
```

## 🔄 Migration Phases

### 1. Discovery Phase
- Connects to source platform
- Catalogs all available data
- Counts templates, instances, users
- Generates discovery statistics

### 2. Mapping Phase
- Maps vendor concepts to Tallyfy concepts
- Creates field type mappings
- Establishes user role mappings
- Defines hierarchy translations

### 3. Transformation Phase
- Converts vendor data to Tallyfy format
- Applies field transformations
- Processes user data
- Handles custom fields and metadata

### 4. Migration Phase
- Creates data in Tallyfy
- Handles errors gracefully
- Supports dry-run mode
- Tracks created entities

### 5. Validation Phase
- Verifies migrated data
- Checks data integrity
- Reports any issues
- Generates final statistics

## 📊 Migration Reports

After each migration, a detailed report is generated in `migration_reports/`:

```json
{
  "migration_id": "platform_migration_20240101_120000",
  "start_time": "2024-01-01T12:00:00",
  "end_time": "2024-01-01T13:30:00",
  "duration": "1:30:00",
  "results": {
    "discovery": {...},
    "mapping": {...},
    "transformation": {...},
    "migration": {...},
    "validation": {...}
  }
}
```

## 🏗️ Architecture

### Directory Structure
```
migrator/
├── shared/                 # Shared base classes and utilities
│   └── form_migrator_base.py
├── [platform-name]/       # Platform-specific migrator
│   └── src/
│       ├── api/          # API clients
│       │   ├── [vendor]_client.py
│       │   ├── tallyfy_client.py
│       │   └── ai_client.py
│       ├── transformers/ # Data transformers
│       │   ├── field_transformer.py
│       │   ├── template_transformer.py
│       │   ├── instance_transformer.py
│       │   └── user_transformer.py
│       ├── utils/        # Utilities
│       │   ├── checkpoint_manager.py
│       │   ├── error_handler.py
│       │   ├── logger_config.py
│       │   └── validator.py
│       └── main.py       # Orchestrator
```

### Component Overview

- **API Clients**: Handle platform-specific API interactions
- **Transformers**: Convert vendor data to Tallyfy format
- **Utils**: Provide logging, error handling, checkpointing
- **Orchestrator**: Manages the 5-phase migration process

## 🧪 Testing

### Dry Run Testing
Always test with dry-run mode first:
```bash
python main.py --dry-run
```

### Verification Script
Check migrator completeness:
```bash
python verify_completeness.py
```

### Sample Data Testing
Test with limited data:
```bash
# Modify discovery phase to limit data
# In main.py, adjust sample sizes
```

## 🐛 Troubleshooting

### Common Issues

1. **API Authentication Errors**
   - Verify API keys in `.env`
   - Check API key permissions
   - Ensure correct API URLs

2. **Rate Limiting**
   - Migrations automatically handle rate limits
   - Adjust `MIGRATION_RATE_LIMIT_DELAY` if needed

3. **Memory Issues with Large Datasets**
   - Use batch processing
   - Adjust `MIGRATION_BATCH_SIZE`
   - Run phases separately

4. **Failed Migrations**
   - Use `--resume` to continue from checkpoint
   - Check logs in `logs/` directory
   - Review error details in migration report

### Debug Mode
Enable detailed logging:
```bash
LOG_LEVEL=DEBUG python main.py --verbose
```

## 📝 Adding New Platforms

To add support for a new platform:

1. Create directory structure:
```bash
mkdir -p migrator/new-platform/src/{api,transformers,utils}
```

2. Implement vendor API client
3. Create transformers for the platform's data model
4. Copy utilities from existing migrator
5. Implement orchestrator following the 5-phase pattern

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

[License details here]

## 💬 Support

For issues and questions:
- Check existing documentation
- Review migration reports for errors
- Contact support with migration ID and logs

## 🔐 Security Notes

- Never commit `.env` files with actual credentials
- Rotate API keys regularly
- Use read-only API permissions where possible
- Store credentials securely
- Review migrated data for sensitive information

## 🚦 Status

All 15 migrators are complete and ready for use:
- ✅ Core components implemented
- ✅ API clients configured
- ✅ Transformers created
- ✅ 5-phase orchestration ready
- ⚠️ Vendor-specific customization may be needed
- ⚠️ Testing with real data required

## 📅 Roadmap

- [ ] Add support for more platforms
- [ ] Implement webhook-based real-time sync
- [ ] Add data export functionality
- [ ] Create web UI for migration management
- [ ] Add migration scheduling
- [ ] Implement incremental migrations