#!/bin/bash

# Kissflow to Tallyfy Migration Script
# Usage: ./migrate.sh [options]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
CONFIG_FILE=".env"
DRY_RUN=false
REPORT_ONLY=false
INSTANCE_LIMIT=100
RESUME=false
VERBOSE=false

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Migrate from Kissflow to Tallyfy

OPTIONS:
    -c, --config FILE       Configuration file (default: .env)
    -d, --dry-run          Perform dry run without making changes
    -r, --report-only      Generate report without migration
    -l, --limit NUMBER     Limit number of instances to migrate (default: 100)
    --resume               Resume from last checkpoint
    -v, --verbose          Enable verbose logging
    -h, --help             Show this help message

EXAMPLES:
    # Dry run to see what would be migrated
    $0 --dry-run

    # Generate report only
    $0 --report-only

    # Full migration with custom config
    $0 --config production.env

    # Resume interrupted migration
    $0 --resume

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -r|--report-only)
            REPORT_ONLY=true
            shift
            ;;
        -l|--limit)
            INSTANCE_LIMIT="$2"
            shift 2
            ;;
        --resume)
            RESUME=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_color $RED "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_color $RED "Configuration file not found: $CONFIG_FILE"
    print_color $YELLOW "Please copy .env.example to $CONFIG_FILE and configure it"
    exit 1
fi

# Load configuration
source "$CONFIG_FILE"

# Validate required environment variables
required_vars=(
    "KISSFLOW_SUBDOMAIN"
    "KISSFLOW_ACCOUNT_ID"
    "KISSFLOW_ACCESS_KEY_ID"
    "KISSFLOW_ACCESS_KEY_SECRET"
    "TALLYFY_API_TOKEN"
    "TALLYFY_ORGANIZATION_ID"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_color $RED "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# Create configuration JSON
CONFIG_JSON=$(cat <<EOF
{
    "kissflow": {
        "subdomain": "$KISSFLOW_SUBDOMAIN",
        "account_id": "$KISSFLOW_ACCOUNT_ID",
        "access_key_id": "$KISSFLOW_ACCESS_KEY_ID",
        "access_key_secret": "$KISSFLOW_ACCESS_KEY_SECRET"
    },
    "tallyfy": {
        "api_token": "$TALLYFY_API_TOKEN",
        "organization_id": "$TALLYFY_ORGANIZATION_ID"
    },
    "dry_run": $DRY_RUN,
    "report_only": $REPORT_ONLY,
    "instance_limit": $INSTANCE_LIMIT
}
EOF
)

# Save config to temporary file
CONFIG_TEMP=$(mktemp)
echo "$CONFIG_JSON" > "$CONFIG_TEMP"

# Print migration banner
print_color $GREEN "================================================"
print_color $GREEN "     KISSFLOW TO TALLYFY MIGRATION"
print_color $GREEN "================================================"
echo ""

# Print configuration
print_color $YELLOW "Configuration:"
echo "  Kissflow Subdomain: $KISSFLOW_SUBDOMAIN"
echo "  Tallyfy Organization: $TALLYFY_ORGANIZATION_ID"
echo "  Dry Run: $DRY_RUN"
echo "  Report Only: $REPORT_ONLY"
echo "  Instance Limit: $INSTANCE_LIMIT"
echo "  Resume: $RESUME"
echo ""

# Confirm before proceeding (unless dry run or report only)
if [ "$DRY_RUN" = false ] && [ "$REPORT_ONLY" = false ]; then
    print_color $YELLOW "⚠️  WARNING: This will migrate data to Tallyfy"
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        print_color $RED "Migration cancelled"
        exit 0
    fi
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_color $RED "Python $required_version or higher is required (found $python_version)"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    print_color $YELLOW "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
print_color $YELLOW "Installing dependencies..."
pip install -q -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p checkpoints
mkdir -p reports

# Set up logging
LOG_FILE="logs/migration_$(date +%Y%m%d_%H%M%S).log"

# Build command
CMD="python3 src/main.py --config $CONFIG_TEMP"

if [ "$DRY_RUN" = true ]; then
    CMD="$CMD --dry-run"
fi

if [ "$REPORT_ONLY" = true ]; then
    CMD="$CMD --report-only"
fi

CMD="$CMD --instance-limit $INSTANCE_LIMIT"

# Run migration
print_color $GREEN "Starting migration..."
echo "Log file: $LOG_FILE"
echo ""

if [ "$VERBOSE" = true ]; then
    $CMD 2>&1 | tee "$LOG_FILE"
else
    $CMD > "$LOG_FILE" 2>&1 &
    pid=$!
    
    # Show progress
    spin='-\|/'
    i=0
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) %4 ))
        printf "\r${spin:$i:1} Migration in progress... (check $LOG_FILE for details)"
        sleep 0.5
    done
    
    # Check exit status
    wait $pid
    exit_status=$?
fi

# Clean up temp file
rm -f "$CONFIG_TEMP"

# Check results
if [ ${exit_status:-0} -eq 0 ]; then
    print_color $GREEN "\n✓ Migration completed successfully!"
    
    # Show summary from log
    echo ""
    print_color $YELLOW "Migration Summary:"
    grep "Migration Summary:" -A 10 "$LOG_FILE" | tail -11
    
    # Show report location
    report_file=$(ls -t reports/migration_final_*.txt 2>/dev/null | head -1)
    if [ -n "$report_file" ]; then
        echo ""
        print_color $GREEN "Full report available at: $report_file"
    fi
else
    print_color $RED "\n✗ Migration failed!"
    echo "Check the log file for details: $LOG_FILE"
    
    # Show last error from log
    echo ""
    print_color $RED "Last error:"
    grep -E "ERROR|CRITICAL" "$LOG_FILE" | tail -5
    
    if [ "$RESUME" = false ]; then
        echo ""
        print_color $YELLOW "You can resume the migration using: $0 --resume"
    fi
    
    exit 1
fi

# Deactivate virtual environment
deactivate

print_color $GREEN "\nMigration script completed!"