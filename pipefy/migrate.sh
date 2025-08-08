#!/bin/bash

# Pipefy to Tallyfy Migration Runner
# This script simplifies running the migration with proper checks and setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to script directory
cd "$SCRIPT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Pipefy to Tallyfy Migration Tool${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure your credentials:"
    echo "  cp .env.example .env"
    exit 1
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
check_env_var "PIPEFY_API_TOKEN"
check_env_var "PIPEFY_ORG_ID"
check_env_var "TALLYFY_CLIENT_ID"
check_env_var "TALLYFY_CLIENT_SECRET"
check_env_var "TALLYFY_ORG_ID"

# Check for database configuration if tables exist
if [ ! -z "$DATABASE_URL" ]; then
    echo -e "${GREEN}✓ Database configured${NC}"
else
    echo -e "${YELLOW}⚠ No database configured - Pipefy tables will not be migrated${NC}"
    read -p "Continue without database migration? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )[\d.]+')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

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
mkdir -p data/temp data/cache data/backup logs reports

# Default config file
CONFIG_FILE="${CONFIG_FILE:-config/migration_config.yaml}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Parse command line arguments
DRY_RUN=""
PIPE_ID=""
SKIP_TABLES=""
REPORT_ONLY=""
HELP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            echo -e "${YELLOW}Running in DRY RUN mode - no data will be migrated${NC}"
            shift
            ;;
        --pipe-id)
            PIPE_ID="--pipe-id $2"
            echo -e "${YELLOW}Migrating single pipe: $2${NC}"
            shift 2
            ;;
        --skip-tables)
            SKIP_TABLES="--skip-tables"
            echo -e "${YELLOW}Skipping database table migration${NC}"
            shift
            ;;
        --report-only)
            REPORT_ONLY="--report-only"
            echo -e "${YELLOW}Generating report only - no migration${NC}"
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
    echo "  --dry-run        Analyze without migrating data"
    echo "  --pipe-id ID     Migrate specific pipe only"
    echo "  --skip-tables    Skip database table migration"
    echo "  --report-only    Generate migration report only"
    echo "  --help           Show this help message"
    echo ""
    echo "Environment:"
    echo "  CONFIG_FILE      Path to config file (default: config/migration_config.yaml)"
    echo ""
    exit 0
fi

# Warning about paradigm shift
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                         WARNING                              ║${NC}"
echo -e "${YELLOW}║                                                              ║${NC}"
echo -e "${YELLOW}║  This migration transforms Pipefy's Kanban workflow into    ║${NC}"
echo -e "${YELLOW}║  Tallyfy's sequential checklist model. This is a MAJOR      ║${NC}"
echo -e "${YELLOW}║  paradigm shift that will require:                          ║${NC}"
echo -e "${YELLOW}║                                                              ║${NC}"
echo -e "${YELLOW}║  • Complete workflow redesign                               ║${NC}"
echo -e "${YELLOW}║  • External database for Pipefy tables                      ║${NC}"
echo -e "${YELLOW}║  • Automation platform for complex rules                    ║${NC}"
echo -e "${YELLOW}║  • Significant user retraining                              ║${NC}"
echo -e "${YELLOW}║                                                              ║${NC}"
echo -e "${YELLOW}║  See README.md for critical limitations                     ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Confirmation
if [ -z "$DRY_RUN" ] && [ -z "$REPORT_ONLY" ]; then
    read -p "Do you want to proceed with the migration? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled"
        exit 0
    fi
fi

# Run the migration
echo ""
echo "Starting migration..."
echo "Configuration: $CONFIG_FILE"
echo "Timestamp: $(date)"
echo ""

# Build command
CMD="python src/main.py --config $CONFIG_FILE $DRY_RUN $PIPE_ID $SKIP_TABLES $REPORT_ONLY"

# Execute
$CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Migration completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Reports available in: reports/"
    echo "Logs available in: logs/"
    
    if [ -z "$DRY_RUN" ]; then
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "1. Verify migrated data in Tallyfy"
        echo "2. Test external database connections"
        echo "3. Configure automation webhooks"
        echo "4. Train users on new workflow"
        echo "5. Run parallel for 30 days before decommissioning Pipefy"
    fi
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Migration failed!${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Check logs for details: logs/"
    exit 1
fi

# Deactivate virtual environment
deactivate