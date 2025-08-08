#!/bin/bash

# ClickUp to Tallyfy Migration Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Default values
DRY_RUN=false
RESUME=false
READINESS_CHECK=false
VERBOSE=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "ClickUp to Tallyfy Migration Tool"
    echo ""
    echo "Options:"
    echo "  --dry-run          Preview migration without changes"
    echo "  --resume           Resume interrupted migration"
    echo "  --readiness-check  Verify API connectivity"
    echo "  --verbose          Enable verbose logging"
    echo "  --help             Display this help"
    echo ""
    exit 0
}

# Parse arguments
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
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi
    
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            echo -e "${YELLOW}Creating .env from .env.example${NC}"
            cp .env.example .env
            echo -e "${RED}Please configure your API keys in .env${NC}"
            exit 1
        fi
    fi
    
    if ! python3 -c "import requests" 2>/dev/null; then
        echo -e "${YELLOW}Installing dependencies...${NC}"
        pip install -q -r requirements.txt
    fi
    
    echo -e "${GREEN}Prerequisites OK${NC}"
}

run_readiness_check() {
    echo -e "${BLUE}Running readiness check...${NC}"
    python3 -c "
import sys
sys.path.insert(0, 'src')
from api.clickup_client import ClickUpClient
import os
from dotenv import load_dotenv

load_dotenv()

client = ClickUpClient(os.getenv('CLICKUP_API_KEY'))
if client.test_connection():
    print('✅ ClickUp API connected')
    discovery = client.discover_workspace()
    stats = discovery['statistics']
    print(f'  Spaces: {stats.get(\"spaces\", 0)}')
    print(f'  Lists: {stats.get(\"lists\", 0)}')
    print(f'  Tasks: {stats.get(\"tasks\", 0)}')
else:
    print('❌ ClickUp API failed')
    sys.exit(1)
"
}

run_migration() {
    echo -e "${BLUE}Starting ClickUp migration...${NC}"
    
    CMD="python3 src/main.py"
    
    if [ "$DRY_RUN" = true ]; then
        CMD="$CMD --dry-run"
        echo -e "${YELLOW}DRY RUN mode${NC}"
    fi
    
    if [ "$RESUME" = true ]; then
        CMD="$CMD --resume"
    fi
    
    if [ "$VERBOSE" = true ]; then
        CMD="$CMD --verbose"
    fi
    
    mkdir -p logs reports
    
    if eval $CMD; then
        echo -e "${GREEN}Migration completed!${NC}"
    else
        echo -e "${RED}Migration failed!${NC}"
        exit 1
    fi
}

main() {
    echo -e "${BLUE}ClickUp to Tallyfy Migration v1.0.0${NC}"
    echo ""
    
    check_prerequisites
    
    if [ "$READINESS_CHECK" = true ]; then
        run_readiness_check
        exit 0
    fi
    
    run_migration
}

main