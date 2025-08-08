#!/bin/bash

# List of migrators to update
MIGRATORS=(
    "wrike"
    "nextmatter" 
    "basecamp"
    "jotform"
    "cognito-forms"
    "clickup"
    "trello"
    "google-forms"
)

# Source directory for utilities
SOURCE_UTILS="/Users/amit/Documents/GitHub/migrator/rocketlane/src/utils"
SOURCE_API="/Users/amit/Documents/GitHub/migrator/rocketlane/src/api"

echo "Copying utilities and API clients to all migrators..."

for MIGRATOR in "${MIGRATORS[@]}"; do
    echo "Processing $MIGRATOR..."
    
    # Create directories if they don't exist
    mkdir -p "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/utils"
    mkdir -p "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/api"
    mkdir -p "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/transformers"
    
    # Copy utilities (only if they don't exist)
    for util in validator.py logger_config.py error_handler.py checkpoint_manager.py; do
        if [ ! -f "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/utils/$util" ]; then
            cp "$SOURCE_UTILS/$util" "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/utils/"
            echo "  Copied $util"
        fi
    done
    
    # Copy Tallyfy and AI clients (only if they don't exist)
    for client in tallyfy_client.py ai_client.py; do
        if [ ! -f "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/api/$client" ]; then
            cp "$SOURCE_API/$client" "/Users/amit/Documents/GitHub/migrator/$MIGRATOR/src/api/"
            echo "  Copied $client"
        fi
    done
done

echo "Done copying utilities and API clients!"