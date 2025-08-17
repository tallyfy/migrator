#!/bin/bash

# BPMN to Tallyfy Migration Script - Production Version
# Complete migration pipeline with validation and reporting

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

# Function to display usage
usage() {
    cat << EOF
$(echo -e "${GREEN}BPMN to Tallyfy Migrator v2.0${NC}")

Usage: $0 [OPTIONS] <bpmn_file>

$(echo -e "${BLUE}Options:${NC}")
    -o, --output FILE    Save Tallyfy template to JSON file
    -a, --analyze        Only analyze complexity (don't migrate)
    -v, --verbose        Enable verbose output
    -h, --help          Display this help message

$(echo -e "${BLUE}Examples:${NC}")
    # Analyze complexity
    $0 --analyze process.bpmn
    
    # Full migration
    $0 -o template.json process.bpmn
    
    # Quick test
    $0 examples/simple_process.bpmn

$(echo -e "${YELLOW}Current Status:${NC}")
    ✅ Working: Simple sequential processes, basic XOR gateways
    ⚠️  Partial: Complex conditions, parallel gateways, forms
    ❌ Not Working: Loops, boundary events, subprocesses
    
    See MIGRATION_GAPS_AND_ISSUES.md for complete details

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -a|--analyze)
            ANALYZE_ONLY=true
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
    echo -e "${RED}Error: No input file or directory specified${NC}"
    usage
fi

# Check if input exists
if [ ! -e "$INPUT" ]; then
    echo -e "${RED}Error: Input '$INPUT' does not exist${NC}"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Display header
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     BPMN to Tallyfy Migrator v2.0     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "Input: ${BLUE}$INPUT${NC}"

if [ ! -z "$OUTPUT" ]; then
    echo -e "Output: ${BLUE}$OUTPUT${NC}"
fi

# Build command
CMD="python3 migrate_bpmn.py \"$INPUT\""

if [ "$ANALYZE_ONLY" = true ]; then
    CMD="$CMD --analyze"
fi

if [ ! -z "$OUTPUT" ]; then
    CMD="$CMD --output \"$OUTPUT\""
fi

if [ "$VERBOSE" = true ]; then
    CMD="$CMD --verbose"
fi

echo ""

# Run migration
eval $CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Process completed successfully${NC}"
else
    echo ""
    echo -e "${RED}✗ Process failed${NC}"
    exit 1
fi