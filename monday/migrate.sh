#!/bin/bash

# Monday.com to Tallyfy Migration Script
# This script orchestrates the migration process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/migration_$(date +%Y%m%d_%H%M%S).log"

# Create logs directory
mkdir -p "$LOG_DIR"

# Functions
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}       Monday.com to Tallyfy Migration Tool${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"
    
    # Check pip
    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip is not installed"
        exit 1
    fi
    print_success "pip found"
    
    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_error ".env file not found. Please copy .env.example and configure it."
        exit 1
    fi
    print_success ".env file found"
    
    echo ""
}

install_dependencies() {
    print_info "Installing dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv "$SCRIPT_DIR/venv"
    fi
    
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
    
    # Install dependencies
    pip install -q --upgrade pip
    pip install -q requests python-dotenv
    
    print_success "Dependencies installed"
    echo ""
}

load_config() {
    print_info "Loading configuration..."
    
    # Load environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Validate required variables
    if [ -z "$MONDAY_API_TOKEN" ]; then
        print_error "MONDAY_API_TOKEN not set in .env file"
        exit 1
    fi
    
    if [ -z "$TALLYFY_API_KEY" ]; then
        print_error "TALLYFY_API_KEY not set in .env file"
        exit 1
    fi
    
    if [ -z "$TALLYFY_ORGANIZATION" ]; then
        print_error "TALLYFY_ORGANIZATION not set in .env file"
        exit 1
    fi
    
    print_success "Configuration loaded"
    echo ""
}

show_menu() {
    echo "Migration Options:"
    echo "1) Full Migration (All workspaces and boards)"
    echo "2) Selective Migration (Choose specific boards)"
    echo "3) Report Only (Analyze without migrating)"
    echo "4) Dry Run (Simulate migration)"
    echo "5) Resume Previous Migration"
    echo "6) Validate Existing Migration"
    echo "0) Exit"
    echo ""
    read -p "Select option: " option
    echo ""
}

run_migration() {
    local mode=$1
    local extra_args="${2:-}"
    
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
    
    # Base command
    cmd="python3 -m src.main"
    cmd="$cmd --api-token '$MONDAY_API_TOKEN'"
    cmd="$cmd --tallyfy-key '$TALLYFY_API_KEY'"
    cmd="$cmd --tallyfy-org '$TALLYFY_ORGANIZATION'"
    
    # Add mode-specific arguments
    case $mode in
        "full")
            print_info "Starting full migration..."
            ;;
        "selective")
            print_info "Starting selective migration..."
            cmd="$cmd $extra_args"
            ;;
        "report")
            print_info "Generating migration report..."
            cmd="$cmd --report-only"
            ;;
        "dry-run")
            print_info "Starting dry run..."
            cmd="$cmd --dry-run"
            ;;
        "resume")
            print_info "Resuming previous migration..."
            cmd="$cmd --resume"
            ;;
        "validate")
            print_info "Validating migration..."
            # Run validation separately
            python3 -c "
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.id_mapper import IDMapper

cm = CheckpointManager()
im = IDMapper()

print('Checkpoint Info:')
info = cm.get_checkpoint_info()
for key, value in info.items():
    print(f'  {key}: {value}')

print('\nID Mapping Statistics:')
stats = im.get_statistics()
for key, value in stats.items():
    print(f'  {key}: {value}')
"
            return
            ;;
        *)
            print_error "Invalid mode"
            return 1
            ;;
    esac
    
    # Run migration
    echo "Command: $cmd" >> "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    
    # Execute with logging
    eval $cmd 2>&1 | tee -a "$LOG_FILE"
    
    # Check exit code
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_success "Migration completed successfully!"
        echo ""
        print_info "Log saved to: $LOG_FILE"
    else
        print_error "Migration failed. Check log for details: $LOG_FILE"
        return 1
    fi
}

get_board_selection() {
    print_info "Enter board IDs to migrate (comma-separated):"
    read -p "Board IDs: " board_ids
    
    if [ -z "$board_ids" ]; then
        print_error "No board IDs provided"
        return 1
    fi
    
    # Convert comma-separated to space-separated
    board_ids=$(echo "$board_ids" | tr ',' ' ')
    echo "--board-ids $board_ids"
}

cleanup() {
    print_info "Cleaning up..."
    
    # Deactivate virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        deactivate
    fi
}

# Main execution
main() {
    print_header
    check_requirements
    install_dependencies
    load_config
    
    while true; do
        show_menu
        
        case $option in
            1)
                run_migration "full"
                break
                ;;
            2)
                board_args=$(get_board_selection)
                if [ $? -eq 0 ]; then
                    run_migration "selective" "$board_args"
                fi
                break
                ;;
            3)
                run_migration "report"
                break
                ;;
            4)
                run_migration "dry-run"
                break
                ;;
            5)
                run_migration "resume"
                break
                ;;
            6)
                run_migration "validate"
                ;;
            0)
                print_info "Exiting..."
                break
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        
        echo ""
    done
    
    cleanup
    echo ""
    print_info "Migration tool finished."
}

# Trap cleanup on exit
trap cleanup EXIT

# Run main function
main