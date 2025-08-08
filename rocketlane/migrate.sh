#!/bin/bash

# RocketLane to Tallyfy Migration Script
# Production-ready migration tool with AI augmentation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Default values
DRY_RUN=false
RESUME=false
READINESS_CHECK=false
VERBOSE=false
REPORT_ONLY=false
TEMPLATES_ONLY=false
EXCLUDE_ARCHIVED=false
PREVIEW_MAPPINGS=false
PROJECTS=""
AFTER_DATE=""

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "RocketLane to Tallyfy Migration Tool"
    echo ""
    echo "Options:"
    echo "  --dry-run                Run migration in preview mode without making changes"
    echo "  --resume                 Resume interrupted migration from last checkpoint"
    echo "  --readiness-check        Verify API connectivity and configuration"
    echo "  --verbose               Enable verbose logging"
    echo "  --report-only           Generate migration report without migrating"
    echo "  --templates-only        Migrate only templates, skip running projects"
    echo "  --exclude-archived      Skip archived projects and templates"
    echo "  --preview-mappings      Preview field and object mappings"
    echo "  --projects \"A,B,C\"      Migrate specific projects only (comma-separated)"
    echo "  --after-date YYYY-MM-DD Only migrate items created after this date"
    echo "  --help                  Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --readiness-check                    # Verify setup"
    echo "  $0 --dry-run                           # Preview migration"
    echo "  $0                                      # Run full migration"
    echo "  $0 --resume                            # Resume interrupted migration"
    echo "  $0 --projects \"Project Alpha,Beta\"     # Selective migration"
    echo ""
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --resume)
            RESUME=true
            shift
            ;;
        --readiness-check)
            READINESS_CHECK=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --report-only)
            REPORT_ONLY=true
            shift
            ;;
        --templates-only)
            TEMPLATES_ONLY=true
            shift
            ;;
        --exclude-archived)
            EXCLUDE_ARCHIVED=true
            shift
            ;;
        --preview-mappings)
            PREVIEW_MAPPINGS=true
            shift
            ;;
        --projects)
            PROJECTS="$2"
            shift 2
            ;;
        --after-date)
            AFTER_DATE="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.8"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
        exit 1
    fi
    
    # Check virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check dependencies
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            echo -e "${YELLOW}Creating .env from .env.example${NC}"
            cp .env.example .env
            echo -e "${RED}Please configure your API keys in .env file${NC}"
            exit 1
        else
            echo -e "${RED}Error: .env file not found${NC}"
            exit 1
        fi
    fi
    
    # Install requirements if needed
    if ! python3 -c "import requests" 2>/dev/null; then
        echo -e "${YELLOW}Installing dependencies...${NC}"
        pip install -q -r requirements.txt
    fi
    
    echo -e "${GREEN}Prerequisites check passed${NC}"
}

# Function to run readiness check
run_readiness_check() {
    echo -e "${BLUE}Running readiness check...${NC}"
    
    python3 -c "
import sys
sys.path.insert(0, 'src')
from api.rocketlane_client import RocketLaneClient
from api.tallyfy_client import TallyfyClient
from api.ai_client import AIClient
import os
from dotenv import load_dotenv

load_dotenv()

print('Checking RocketLane API...')
try:
    rl_client = RocketLaneClient(
        api_key=os.getenv('ROCKETLANE_API_KEY'),
        base_url=os.getenv('ROCKETLANE_BASE_URL', 'https://api.rocketlane.com/api/1.0')
    )
    if rl_client.test_connection():
        print('✅ RocketLane API: Connected')
        discovery = rl_client.discover_all_data()
        print(f'  - Users: {discovery[\"statistics\"].get(\"users\", 0)}')
        print(f'  - Customers: {discovery[\"statistics\"].get(\"customers\", 0)}')
        print(f'  - Templates: {discovery[\"statistics\"].get(\"templates\", 0)}')
        print(f'  - Projects: {discovery[\"statistics\"].get(\"projects\", 0)}')
    else:
        print('❌ RocketLane API: Failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ RocketLane API: {e}')
    sys.exit(1)

print()
print('Checking Tallyfy API...')
try:
    tf_client = TallyfyClient(
        api_key=os.getenv('TALLYFY_API_KEY'),
        organization=os.getenv('TALLYFY_ORGANIZATION')
    )
    stats = tf_client.get_statistics()
    print('✅ Tallyfy API: Connected')
    print(f'  - Organization: {os.getenv(\"TALLYFY_ORGANIZATION\")}')
    print(f'  - Existing templates: {stats.get(\"templates\", 0)}')
    print(f'  - Existing processes: {stats.get(\"processes\", 0)}')
except Exception as e:
    print(f'❌ Tallyfy API: {e}')
    sys.exit(1)

print()
print('Checking AI augmentation...')
ai_client = AIClient()
if ai_client.enabled:
    print(f'✅ AI: Enabled (Model: {ai_client.model})')
else:
    print('⚠️  AI: Disabled (using fallback logic)')

print()
print('✅ All systems ready for migration')
"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Readiness check completed successfully${NC}"
    else
        echo -e "${RED}Readiness check failed${NC}"
        exit 1
    fi
}

# Function to run migration
run_migration() {
    echo -e "${BLUE}Starting RocketLane to Tallyfy migration...${NC}"
    
    # Build command
    CMD="python3 src/main.py"
    
    if [ "$DRY_RUN" = true ]; then
        CMD="$CMD --dry-run"
        echo -e "${YELLOW}Running in DRY RUN mode - no changes will be made${NC}"
    fi
    
    if [ "$RESUME" = true ]; then
        CMD="$CMD --resume"
        echo -e "${YELLOW}Resuming from last checkpoint${NC}"
    fi
    
    if [ "$VERBOSE" = true ]; then
        CMD="$CMD --verbose"
        export LOG_LEVEL=DEBUG
    fi
    
    if [ "$REPORT_ONLY" = true ]; then
        CMD="$CMD --report-only"
    fi
    
    if [ "$TEMPLATES_ONLY" = true ]; then
        CMD="$CMD --templates-only"
    fi
    
    if [ "$EXCLUDE_ARCHIVED" = true ]; then
        CMD="$CMD --exclude-archived"
    fi
    
    if [ "$PREVIEW_MAPPINGS" = true ]; then
        CMD="$CMD --preview-mappings"
    fi
    
    if [ -n "$PROJECTS" ]; then
        CMD="$CMD --projects \"$PROJECTS\""
    fi
    
    if [ -n "$AFTER_DATE" ]; then
        CMD="$CMD --after-date $AFTER_DATE"
    fi
    
    # Create logs directory
    mkdir -p logs
    
    # Run migration
    echo -e "${BLUE}Executing: $CMD${NC}"
    echo ""
    
    if eval $CMD; then
        echo ""
        echo -e "${GREEN}Migration completed successfully!${NC}"
        echo -e "${BLUE}Check logs/migration.log for details${NC}"
        echo -e "${BLUE}Check reports/ directory for migration reports${NC}"
    else
        echo ""
        echo -e "${RED}Migration failed!${NC}"
        echo -e "${YELLOW}Check logs/migration_errors.log for error details${NC}"
        echo -e "${YELLOW}You can resume the migration with: $0 --resume${NC}"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}     RocketLane to Tallyfy Migration Tool v1.0.0      ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Handle readiness check
    if [ "$READINESS_CHECK" = true ]; then
        run_readiness_check
        exit 0
    fi
    
    # Run migration
    run_migration
}

# Execute main function
main