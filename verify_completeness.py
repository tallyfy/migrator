#!/usr/bin/env python3
"""
Verify completeness of all migrators
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

def check_migrator(migrator_path: Path) -> Dict[str, bool]:
    """Check if a migrator has all required components"""
    
    required_files = {
        'api_client': None,  # Will be set based on migrator name
        'tallyfy_client': 'src/api/tallyfy_client.py',
        'ai_client': 'src/api/ai_client.py',
        'field_transformer': 'src/transformers/field_transformer.py',
        'template_transformer': 'src/transformers/template_transformer.py',
        'instance_transformer': 'src/transformers/instance_transformer.py',
        'user_transformer': 'src/transformers/user_transformer.py',
        'validator': 'src/utils/validator.py',
        'logger_config': 'src/utils/logger_config.py',
        'error_handler': 'src/utils/error_handler.py',
        'checkpoint_manager': 'src/utils/checkpoint_manager.py',
        'main': 'src/main.py'
    }
    
    # Determine vendor API client name
    migrator_name = migrator_path.name
    client_mapping = {
        'wrike': 'src/api/wrike_client.py',
        'nextmatter': 'src/api/nextmatter_client.py',
        'basecamp': 'src/api/basecamp_client.py',
        'jotform': 'src/api/jotform_client.py',
        'cognito-forms': 'src/api/cognito_forms_client.py',
        'clickup': 'src/api/clickup_client.py',
        'trello': 'src/api/trello_client.py',
        'google-forms': 'src/api/google_forms_client.py',
        'typeform': 'src/api/typeform_client.py',
        'asana': 'src/api/asana_client.py',
        'kissflow': 'src/api/kissflow_client.py',
        'monday': 'src/api/monday_client.py',
        'pipefy': 'src/api/pipefy_client.py',
        'process-street': 'src/api/process_street_client.py',
        'rocketlane': 'src/api/rocketlane_client.py'
    }
    
    required_files['api_client'] = client_mapping.get(migrator_name, f'src/api/{migrator_name}_client.py')
    
    results = {}
    for component, rel_path in required_files.items():
        file_path = migrator_path / rel_path
        results[component] = file_path.exists()
    
    return results

def main():
    """Check all migrators for completeness"""
    
    base_dir = Path('/Users/amit/Documents/GitHub/migrator')
    
    # List of all migrators to check
    migrators = [
        'wrike',
        'nextmatter',
        'basecamp',
        'jotform',
        'cognito-forms',
        'clickup',
        'trello',
        'google-forms',
        'typeform',
        'asana',
        'kissflow',
        'monday',
        'pipefy',
        'process-street',
        'rocketlane'
    ]
    
    print("=" * 80)
    print("MIGRATOR COMPLETENESS CHECK")
    print("=" * 80)
    print()
    
    complete_migrators = []
    incomplete_migrators = []
    
    for migrator in migrators:
        migrator_path = base_dir / migrator
        
        if not migrator_path.exists():
            print(f"❌ {migrator}: Directory does not exist")
            incomplete_migrators.append((migrator, "Directory missing"))
            continue
        
        results = check_migrator(migrator_path)
        
        missing = [comp for comp, exists in results.items() if not exists]
        
        if not missing:
            print(f"✅ {migrator}: COMPLETE")
            complete_migrators.append(migrator)
        else:
            print(f"⚠️  {migrator}: Missing {len(missing)} components:")
            for comp in missing:
                print(f"    - {comp}")
            incomplete_migrators.append((migrator, missing))
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Complete migrators: {len(complete_migrators)}/{len(migrators)}")
    print(f"Incomplete migrators: {len(incomplete_migrators)}/{len(migrators)}")
    
    if complete_migrators:
        print("\n✅ Complete migrators:")
        for m in complete_migrators:
            print(f"  - {m}")
    
    if incomplete_migrators:
        print("\n⚠️  Incomplete migrators:")
        for m, issues in incomplete_migrators:
            if isinstance(issues, list):
                print(f"  - {m}: Missing {len(issues)} components")
            else:
                print(f"  - {m}: {issues}")
    
    # Check for vendor-specific customizations needed
    print("\n" + "=" * 80)
    print("VENDOR-SPECIFIC CUSTOMIZATIONS NEEDED")
    print("=" * 80)
    
    forms_migrators = ['jotform', 'cognito-forms', 'google-forms', 'typeform']
    workflow_migrators = ['wrike', 'nextmatter', 'basecamp', 'clickup', 'trello', 'asana', 'monday', 'pipefy', 'process-street', 'rocketlane', 'kissflow']
    
    print("\n📝 Forms-based migrators (inherit from FormMigratorBase):")
    for m in forms_migrators:
        print(f"  - {m}")
    
    print("\n🔄 Workflow-based migrators:")
    for m in workflow_migrators:
        print(f"  - {m}")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Review and customize vendor-specific API clients")
    print("2. Update transformers with vendor-specific logic")
    print("3. Test each migrator with sample data")
    print("4. Add environment variables to .env file")
    print("5. Run migrations with --dry-run flag first")

if __name__ == '__main__':
    main()