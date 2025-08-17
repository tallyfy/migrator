#!/bin/bash

# BPMN to Tallyfy Migration Runner
# Self-contained rule-based migration - no AI required

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
INPUT=""
OUTPUT=""
ANALYZE_ONLY=false
VERBOSE=false
REPORT=true
USE_AI=false
API_KEY=""

# Function to display usage
usage() {
    cat << EOF
$(echo -e "${GREEN}BPMN to Tallyfy Migration Assistant${NC}")

Usage: $0 [OPTIONS] <bpmn_file>

$(echo -e "${BLUE}Options:${NC}")
    -o, --output FILE    Output JSON file for Tallyfy template
    -a, --analyze        Only analyze complexity (don't migrate)
    -r, --report         Generate detailed report (default: true)
    -v, --verbose        Enable verbose logging
    --with-ai KEY        Enable AI enhancement (optional)
    -h, --help          Display this help message

$(echo -e "${BLUE}Examples:${NC}")
    # Basic migration (rule-based)
    $0 process.bpmn

    # Analyze complexity only
    $0 --analyze process.bpmn

    # Migration with output file
    $0 -o template.json process.bpmn

    # Migration with optional AI enhancement
    $0 --with-ai sk-ant-... process.bpmn

$(echo -e "${YELLOW}Note:${NC}")
    This migrator includes complete embedded rules for all BPMN elements.
    AI enhancement is optional and can improve edge case handling.

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-ai)
            USE_AI=true
            API_KEY="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -a|--analyze)
            ANALYZE_ONLY=true
            shift
            ;;
        -r|--report)
            REPORT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            INPUT="$1"
            shift
            ;;
    esac
done

# Check if input is provided
if [ -z "$INPUT" ]; then
    echo -e "${RED}Error: No BPMN file specified${NC}"
    usage
fi

# Check if input exists
if [ ! -f "$INPUT" ]; then
    echo -e "${RED}Error: File '$INPUT' not found${NC}"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required${NC}"
    exit 1
fi

# Check/create virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import anthropic" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q anthropic lxml
fi

# Display configuration
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}     BPMN to Tallyfy Migrator          ${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "Input File: ${BLUE}$INPUT${NC}"

if [ ! -z "$OUTPUT" ]; then
    echo -e "Output File: ${BLUE}$OUTPUT${NC}"
fi

if [ "$USE_AI" = true ] && [ ! -z "$API_KEY" ]; then
    echo -e "Mode: ${GREEN}Rule-based with AI enhancement${NC}"
else
    echo -e "Mode: ${GREEN}Rule-based (112 embedded mappings)${NC}"
fi

echo -e "${GREEN}═══════════════════════════════════════${NC}"

# Run analysis or migration
if [ "$ANALYZE_ONLY" = true ]; then
    echo -e "\n${BLUE}Analyzing BPMN complexity...${NC}\n"
    python src/analyzer/bpmn_complexity_analyzer.py "$INPUT"
else
    echo -e "\n${BLUE}Starting migration...${NC}\n"
    
    # Build command - use new self-contained migrator
    CMD="python3 src/migrator.py \"$INPUT\""
    
    if [ ! -z "$OUTPUT" ]; then
        CMD="$CMD --output \"$OUTPUT\""
    fi
    
    if [ "$REPORT" = true ]; then
        CMD="$CMD --report"
    fi
    
    if [ "$VERBOSE" = true ]; then
        CMD="$CMD --verbose"
    fi
    
    # Execute migration
    eval $CMD
    
    EXIT_CODE=$?
    
    # Show results
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
        echo -e "${GREEN}       Migration Completed!            ${NC}"
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        
        if [ ! -z "$OUTPUT" ]; then
            echo -e "\nResults saved to: ${BLUE}$OUTPUT${NC}"
            
            # Show summary from JSON
            if command -v jq &> /dev/null; then
                echo -e "\n${BLUE}Quick Summary:${NC}"
                jq -r '.statistics | "  Success Rate: \(.success_rate // 0 | floor)%\n  Manual Work: \(if .manual_work_required then "Required" else "Not Required" end)"' "$OUTPUT" 2>/dev/null || true
            fi
        fi
    else
        echo -e "\n${RED}═══════════════════════════════════════${NC}"
        echo -e "${RED}       Migration Failed!               ${NC}"
        echo -e "${RED}═══════════════════════════════════════${NC}"
    fi
fi

# Deactivate virtual environment
deactivate

echo ""