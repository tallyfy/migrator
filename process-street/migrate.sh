#!/bin/bash

# Process Street to Tallyfy Migration Runner
# Enhanced production-ready migration script with full error handling

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to script directory
cd "$SCRIPT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Process Street to Tallyfy Migration Tool${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo "Creating .env from template..."
    
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env with your API credentials before running migration${NC}"
        echo "Required credentials:"
        echo "  - PROCESS_STREET_API_KEY: Get from Settings → API & Webhooks"
        echo "  - TALLYFY_CLIENT_ID/SECRET: Get from Admin → API → OAuth Applications"
        exit 1
    else
        echo -e "${RED}Error: .env.example not found!${NC}"
        exit 1
    fi
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Validate critical environment variables
check_env_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}Error: $1 is not set in .env file${NC}"
        exit 1
    fi
}

echo "Validating configuration..."
check_env_var "PROCESS_STREET_API_KEY"
check_env_var "TALLYFY_CLIENT_ID"
check_env_var "TALLYFY_CLIENT_SECRET"
check_env_var "TALLYFY_ORG_ID"
check_env_var "TALLYFY_ORG_SLUG"

echo -e "${GREEN}✓ Configuration validated${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create necessary directories
mkdir -p data/checkpoints data/cache data/backup logs reports

# Default config file
CONFIG_FILE="${CONFIG_FILE:-config/migration_config.yaml}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_FILE${NC}"
    echo "Please create a configuration file or set CONFIG_FILE environment variable"
    exit 1
fi

# Parse command line arguments
DRY_RUN=""
RESUME=""
VALIDATE_ONLY=""
PHASE=""
WORKFLOW_ID=""
REPORT_ONLY=""
HELP=""
READINESS_CHECK=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            echo -e "${YELLOW}Running in DRY RUN mode - no data will be migrated${NC}"
            shift
            ;;
        --resume)
            RESUME="--resume"
            echo -e "${YELLOW}Resuming from last checkpoint${NC}"
            shift
            ;;
        --validate-only)
            VALIDATE_ONLY="--validate-only"
            echo -e "${YELLOW}Running validation only${NC}"
            shift
            ;;
        --phase)
            PHASE="--phase $2"
            echo -e "${YELLOW}Running specific phase: $2${NC}"
            shift 2
            ;;
        --workflow-id)
            WORKFLOW_ID="--workflow-id $2"
            echo -e "${YELLOW}Migrating specific workflow: $2${NC}"
            shift 2
            ;;
        --report-only)
            REPORT_ONLY="--report-only"
            echo -e "${YELLOW}Generating report only - no migration${NC}"
            shift
            ;;
        --readiness-check)
            READINESS_CHECK="--readiness-check"
            echo -e "${YELLOW}Running readiness check only${NC}"
            shift
            ;;
        --help)
            HELP="true"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Show help if requested
if [ "$HELP" = "true" ]; then
    echo "Usage: ./migrate.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run          Analyze without migrating data"
    echo "  --resume           Resume from last checkpoint"
    echo "  --validate-only    Run validation phase only"
    echo "  --phase PHASE      Run specific phase (discovery, users, workflows, etc.)"
    echo "  --workflow-id ID   Migrate specific workflow only"
    echo "  --report-only      Generate migration report without migrating"
    echo "  --readiness-check  Check if ready for migration"
    echo "  --help             Show this help message"
    echo ""
    echo "Environment:"
    echo "  CONFIG_FILE        Path to config file (default: config/migration_config.yaml)"
    echo ""
    echo "Examples:"
    echo "  ./migrate.sh --dry-run                    # Test migration without changes"
    echo "  ./migrate.sh --phase discovery            # Run discovery phase only"
    echo "  ./migrate.sh --workflow-id abc123         # Migrate specific workflow"
    echo "  ./migrate.sh --resume                     # Resume interrupted migration"
    echo "  ./migrate.sh                              # Run full migration"
    echo ""
    exit 0
fi

# Show migration plan
echo ""
echo -e "${BLUE}Migration Configuration:${NC}"
echo "  Config file: $CONFIG_FILE"
echo "  Process Street Org: ${PS_ORGANIZATION_ID:-Auto-detect}"
echo "  Tallyfy Org: $TALLYFY_ORG_SLUG"
echo ""

# Run readiness check if requested
if [ "$READINESS_CHECK" = "--readiness-check" ]; then
    echo "Running readiness check..."
    python src/main.py --config "$CONFIG_FILE" --readiness-check
    exit $?
fi

# Warning for production migration
if [ -z "$DRY_RUN" ] && [ -z "$REPORT_ONLY" ] && [ -z "$VALIDATE_ONLY" ]; then
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                    ⚠️  WARNING ⚠️                      ║${NC}"
    echo -e "${YELLOW}║                                                      ║${NC}"
    echo -e "${YELLOW}║  You are about to run a PRODUCTION migration that   ║${NC}"
    echo -e "${YELLOW}║  will transfer data from Process Street to Tallyfy. ║${NC}"
    echo -e "${YELLOW}║                                                      ║${NC}"
    echo -e "${YELLOW}║  This action will:                                  ║${NC}"
    echo -e "${YELLOW}║  • Create users in Tallyfy                          ║${NC}"
    echo -e "${YELLOW}║  • Convert workflows to checklists                  ║${NC}"
    echo -e "${YELLOW}║  • Migrate active processes                         ║${NC}"
    echo -e "${YELLOW}║  • Transfer form data and comments                  ║${NC}"
    echo -e "${YELLOW}║                                                      ║${NC}"
    echo -e "${YELLOW}║  Recommended: Run with --dry-run first              ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    read -p "Do you want to proceed with the migration? (yes/no) " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo "Migration cancelled"
        exit 0
    fi
fi

# Build command
CMD="python src/main.py --config $CONFIG_FILE $DRY_RUN $RESUME $VALIDATE_ONLY $PHASE $WORKFLOW_ID $REPORT_ONLY"

# Show command being run
echo ""
echo -e "${BLUE}Executing: $CMD${NC}"
echo ""

# Run the migration
$CMD
EXIT_CODE=$?

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Migration completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Show report locations
    echo "Reports available in:"
    echo "  • Summary: reports/migration_report.json"
    echo "  • Logs: logs/"
    echo "  • ID Mappings: data/mappings.db"
    
    if [ -z "$DRY_RUN" ]; then
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Verify migrated data in Tallyfy"
        echo "2. Check for any warnings in the logs"
        echo "3. Test workflows with sample data"
        echo "4. Train users on the new platform"
        echo "5. Keep Process Street running in parallel for 30 days"
    fi
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Migration failed with exit code: $EXIT_CODE${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Check logs for details:"
    echo "  • Error log: logs/process_street_errors_*.log"
    echo "  • Main log: logs/process_street_migration_*.log"
    echo ""
    echo "To resume migration after fixing issues:"
    echo "  ./migrate.sh --resume"
    exit $EXIT_CODE
fi

# Deactivate virtual environment
deactivate