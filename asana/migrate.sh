#!/bin/bash

# Asana to Tallyfy Migration Script
# Production-ready wrapper with comprehensive error handling

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to print header
print_header() {
    echo ""
    print_color "$BLUE" "=============================================="
    print_color "$BLUE" "$1"
    print_color "$BLUE" "=============================================="
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_color "$RED" "❌ Python 3 is not installed"
        exit 1
    fi
    
    # Check Python version is 3.8+
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
        print_color "$RED" "❌ Python 3.8+ is required"
        python3 --version
        exit 1
    fi
    print_color "$GREEN" "✅ Python $(python3 --version 2>&1 | cut -d' ' -f2) detected"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_color "$YELLOW" "⚠️  Virtual environment not found. Creating..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if requirements are installed
    if ! python3 -c "import requests" 2>/dev/null; then
        print_color "$YELLOW" "⚠️  Dependencies not installed. Installing..."
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
    fi
    print_color "$GREEN" "✅ Dependencies installed"
    
    # Check .env file
    if [ ! -f ".env" ]; then
        print_color "$RED" "❌ .env file not found"
        print_color "$YELLOW" "Please copy .env.example to .env and configure your credentials"
        exit 1
    fi
    print_color "$GREEN" "✅ Configuration file found"
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Validate required environment variables
    if [ -z "$ASANA_ACCESS_TOKEN" ]; then
        print_color "$RED" "❌ ASANA_ACCESS_TOKEN not set in .env"
        exit 1
    fi
    
    if [ -z "$TALLYFY_API_TOKEN" ]; then
        print_color "$RED" "❌ TALLYFY_API_TOKEN not set in .env"
        exit 1
    fi
    
    if [ -z "$TALLYFY_ORG_ID" ]; then
        print_color "$RED" "❌ TALLYFY_ORG_ID not set in .env"
        exit 1
    fi
    
    print_color "$GREEN" "✅ All prerequisites met"
}

# Function to run readiness check
run_readiness_check() {
    print_header "Running Readiness Check"
    
    python3 src/main.py --readiness-check
    
    if [ $? -eq 0 ]; then
        print_color "$GREEN" "✅ System ready for migration"
        return 0
    else
        print_color "$RED" "❌ Readiness check failed"
        return 1
    fi
}

# Parse command line arguments
DRY_RUN=false
RESUME=false
REPORT_ONLY=false
READINESS_CHECK=false
PHASES=""
LOG_LEVEL="INFO"
VERBOSE=false

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
        --report-only)
            REPORT_ONLY=true
            shift
            ;;
        --readiness-check)
            READINESS_CHECK=true
            shift
            ;;
        --phases)
            PHASES="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            LOG_LEVEL="DEBUG"
            shift
            ;;
        --help)
            print_header "Asana to Tallyfy Migration Tool"
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run          Preview migration without making changes"
            echo "  --resume           Resume from last checkpoint"
            echo "  --report-only      Generate report without migrating"
            echo "  --readiness-check  Check system readiness"
            echo "  --phases PHASES    Run specific phases (comma-separated)"
            echo "                     Available: discovery,users,teams,projects,tasks,validation"
            echo "  --verbose          Enable verbose logging"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --readiness-check              # Check if ready to migrate"
            echo "  $0 --dry-run                      # Preview migration"
            echo "  $0                                # Run full migration"
            echo "  $0 --resume                       # Resume interrupted migration"
            echo "  $0 --phases discovery,users       # Run specific phases only"
            exit 0
            ;;
        *)
            print_color "$RED" "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header "Asana to Tallyfy Migration Tool"
    
    # Check prerequisites
    check_prerequisites
    
    # Run readiness check if requested
    if [ "$READINESS_CHECK" = true ]; then
        run_readiness_check
        exit $?
    fi
    
    # Show migration mode
    if [ "$DRY_RUN" = true ]; then
        print_color "$YELLOW" "🔍 Running in DRY RUN mode - no changes will be made"
    elif [ "$REPORT_ONLY" = true ]; then
        print_color "$YELLOW" "📊 Running in REPORT ONLY mode"
    elif [ "$RESUME" = true ]; then
        print_color "$YELLOW" "↪️  Resuming previous migration"
    else
        print_color "$GREEN" "🚀 Running FULL MIGRATION"
    fi
    
    # Build command
    CMD="python3 src/main.py --log-level $LOG_LEVEL"
    
    if [ "$DRY_RUN" = true ]; then
        CMD="$CMD --dry-run"
    fi
    
    if [ "$RESUME" = true ]; then
        CMD="$CMD --resume"
    fi
    
    if [ "$REPORT_ONLY" = true ]; then
        CMD="$CMD --report-only"
    fi
    
    if [ ! -z "$PHASES" ]; then
        # Convert comma-separated to space-separated
        PHASE_LIST=$(echo $PHASES | tr ',' ' ')
        CMD="$CMD --phases $PHASE_LIST"
    fi
    
    # Create necessary directories
    mkdir -p logs data checkpoints reports
    
    # Log file with timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    LOG_FILE="logs/migration_${TIMESTAMP}.log"
    
    # Run migration
    print_header "Starting Migration"
    
    if [ "$VERBOSE" = true ]; then
        echo "Command: $CMD"
        echo "Log file: $LOG_FILE"
        echo ""
    fi
    
    # Execute with logging
    if $CMD 2>&1 | tee "$LOG_FILE"; then
        print_header "Migration Completed Successfully"
        print_color "$GREEN" "✅ Migration completed successfully!"
        print_color "$BLUE" "📄 Log saved to: $LOG_FILE"
        
        # Check for report
        LATEST_REPORT=$(ls -t reports/migration_report_*.json 2>/dev/null | head -1)
        if [ ! -z "$LATEST_REPORT" ]; then
            print_color "$BLUE" "📊 Report saved to: $LATEST_REPORT"
        fi
        
        exit 0
    else
        print_header "Migration Failed"
        print_color "$RED" "❌ Migration failed. Check log for details: $LOG_FILE"
        exit 1
    fi
}

# Trap Ctrl+C
trap 'print_color "$YELLOW" "\n⚠️  Migration interrupted. Use --resume to continue."; exit 130' INT

# Run main function
main