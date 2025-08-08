#!/usr/bin/env python3
"""Check completeness of each migrator implementation."""

import os
from pathlib import Path

# Define the base directory
BASE_DIR = Path("/Users/amit/Documents/GitHub/migrator")

# List of migrators to check
MIGRATORS = [
    "process-street",
    "pipefy",
    "asana",
    "kissflow",
    "monday",
    "rocketlane",
    "clickup",
    "wrike",
    "nextmatter",
    "trello",
    "basecamp",
    "typeform",
    "jotform",
    "google-forms",
    "cognito-forms"
]

# Required files for each migrator
REQUIRED_FILES = {
    "API Clients": [
        "src/api/{vendor}_client.py",  # vendor-specific client
        "src/api/tallyfy_client.py",
        "src/api/ai_client.py"
    ],
    "Transformers": [
        "src/transformers/field_transformer.py",
        "src/transformers/template_transformer.py",
        "src/transformers/instance_transformer.py",
        "src/transformers/user_transformer.py"
    ],
    "Main": [
        "src/main.py"
    ],
    "Utils": [
        "src/utils/checkpoint_manager.py",
        "src/utils/validator.py",
        "src/utils/error_handler.py",
        "src/utils/logger_config.py"
    ]
}

def get_vendor_name(migrator):
    """Get the vendor-specific client name."""
    # Handle special cases
    if migrator == "process-street":
        return "process_street"
    elif migrator == "google-forms":
        return "google_forms"
    elif migrator == "cognito-forms":
        return "cognito_forms"
    else:
        return migrator.replace("-", "_")

def check_migrator(migrator_name):
    """Check if a migrator has all required files."""
    migrator_path = BASE_DIR / migrator_name
    
    if not migrator_path.exists():
        return None, "Directory does not exist"
    
    results = {}
    missing_files = []
    existing_files = []
    
    for category, files in REQUIRED_FILES.items():
        results[category] = {}
        for file_template in files:
            if "{vendor}" in file_template:
                vendor_name = get_vendor_name(migrator_name)
                file_path = file_template.replace("{vendor}", vendor_name)
            else:
                file_path = file_template
            
            full_path = migrator_path / file_path
            
            # Also check for alternative names (e.g., ps_client.py for process-street)
            alt_paths = []
            if "client.py" in file_path and "{vendor}" in file_template:
                # Check for abbreviated names
                if migrator_name == "process-street":
                    alt_paths.append(migrator_path / "src/api/ps_client.py")
            
            exists = full_path.exists()
            if not exists:
                for alt_path in alt_paths:
                    if alt_path.exists():
                        exists = True
                        full_path = alt_path
                        break
            
            results[category][file_path] = exists
            if exists:
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
    
    return results, missing_files, existing_files

def print_results():
    """Print the completeness check results."""
    print("=" * 80)
    print("MIGRATOR COMPLETENESS CHECK")
    print("=" * 80)
    print()
    
    summary = []
    
    for migrator in MIGRATORS:
        print(f"\n### {migrator.upper()}")
        print("-" * 40)
        
        result = check_migrator(migrator)
        
        if result[0] is None:
            print(f"❌ Directory does not exist: {migrator}")
            summary.append((migrator, 0, 0, "Missing"))
            continue
        
        results, missing_files, existing_files = result
        total_required = sum(len(files) for files in REQUIRED_FILES.values())
        total_existing = len(existing_files)
        
        # Print category-wise results
        for category, file_results in results.items():
            print(f"\n{category}:")
            for file_path, exists in file_results.items():
                status = "✅" if exists else "❌"
                print(f"  {status} {file_path}")
        
        # Print summary for this migrator
        completeness = (total_existing / total_required) * 100 if total_required > 0 else 0
        print(f"\nCompleteness: {total_existing}/{total_required} ({completeness:.1f}%)")
        
        if missing_files:
            print(f"\nMissing files ({len(missing_files)}):")
            for file in missing_files:
                print(f"  - {file}")
        
        status = "Complete" if completeness == 100 else f"{completeness:.1f}%"
        summary.append((migrator, total_existing, total_required, status))
    
    # Print overall summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Migrator':<20} {'Files':<15} {'Status':<15}")
    print("-" * 50)
    
    for migrator, existing, required, status in summary:
        if status == "Missing":
            print(f"{migrator:<20} {'N/A':<15} {status:<15}")
        else:
            print(f"{migrator:<20} {f'{existing}/{required}':<15} {status:<15}")
    
    # Count complete migrators
    complete_count = sum(1 for _, _, _, status in summary if status == "Complete")
    total_count = len(summary)
    print(f"\nTotal Complete: {complete_count}/{total_count}")

if __name__ == "__main__":
    print_results()