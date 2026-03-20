#!/bin/bash
# SurveyMonkey to Tallyfy Migration Entry Point
# Usage: ./migrate.sh [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the migration
python3 src/main.py "$@"
