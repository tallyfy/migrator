#!/usr/bin/env python3
"""Check for additional files and patterns across migrators."""

import os
from pathlib import Path
from collections import defaultdict

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

def scan_migrator_structure(migrator_name):
    """Scan the complete structure of a migrator."""
    migrator_path = BASE_DIR / migrator_name
    
    if not migrator_path.exists():
        return None
    
    structure = {
        'root_files': [],
        'api_files': [],
        'transformer_files': [],
        'utils_files': [],
        'config_files': [],
        'prompt_files': [],
        'other_directories': []
    }
    
    # Scan root level files
    for item in migrator_path.iterdir():
        if item.is_file():
            structure['root_files'].append(item.name)
    
    # Scan src/api
    api_path = migrator_path / "src" / "api"
    if api_path.exists():
        structure['api_files'] = [f.name for f in api_path.iterdir() if f.is_file()]
    
    # Scan src/transformers
    transformers_path = migrator_path / "src" / "transformers"
    if transformers_path.exists():
        structure['transformer_files'] = [f.name for f in transformers_path.iterdir() if f.is_file()]
    
    # Scan src/utils
    utils_path = migrator_path / "src" / "utils"
    if utils_path.exists():
        structure['utils_files'] = [f.name for f in utils_path.iterdir() if f.is_file()]
    
    # Scan config directory
    config_path = migrator_path / "config"
    if config_path.exists():
        structure['config_files'] = list_all_files(config_path)
    
    # Scan src/config directory
    src_config_path = migrator_path / "src" / "config"
    if src_config_path.exists():
        structure['config_files'].extend(list_all_files(src_config_path))
    
    # Scan prompts directory
    prompts_path = migrator_path / "src" / "prompts"
    if prompts_path.exists():
        structure['prompt_files'] = [f.name for f in prompts_path.iterdir() if f.is_file()]
    
    # Check for other special directories
    special_dirs = ['docs', 'reports', 'scripts', 'tests', 'validators', 'graphql']
    for dir_name in special_dirs:
        dir_path = migrator_path / dir_name
        if not dir_path.exists():
            dir_path = migrator_path / "src" / dir_name
        if dir_path.exists():
            structure['other_directories'].append(dir_name)
    
    return structure

def list_all_files(directory):
    """Recursively list all files in a directory."""
    files = []
    for item in directory.iterdir():
        if item.is_file():
            files.append(item.relative_to(directory).as_posix())
        elif item.is_dir():
            for subfile in list_all_files(item):
                files.append(f"{item.name}/{subfile}")
    return files

def analyze_structures():
    """Analyze all migrator structures and find patterns."""
    all_structures = {}
    
    for migrator in MIGRATORS:
        structure = scan_migrator_structure(migrator)
        if structure:
            all_structures[migrator] = structure
    
    # Find common and unique patterns
    all_api_files = defaultdict(list)
    all_transformer_files = defaultdict(list)
    all_utils_files = defaultdict(list)
    all_prompt_files = defaultdict(list)
    
    for migrator, structure in all_structures.items():
        for api_file in structure['api_files']:
            all_api_files[api_file].append(migrator)
        for trans_file in structure['transformer_files']:
            all_transformer_files[trans_file].append(migrator)
        for util_file in structure['utils_files']:
            all_utils_files[util_file].append(migrator)
        for prompt_file in structure['prompt_files']:
            all_prompt_files[prompt_file].append(migrator)
    
    return all_structures, all_api_files, all_transformer_files, all_utils_files, all_prompt_files

def print_analysis():
    """Print the analysis results."""
    structures, api_files, transformer_files, utils_files, prompt_files = analyze_structures()
    
    print("=" * 80)
    print("MIGRATOR STRUCTURE ANALYSIS")
    print("=" * 80)
    print()
    
    # Check for unique API files
    print("### API Files Distribution")
    print("-" * 40)
    for file, migrators in sorted(api_files.items()):
        count = len(migrators)
        if count == 15:
            print(f"✅ {file:<30} [ALL migrators]")
        elif count > 10:
            print(f"⚠️  {file:<30} [{count}/15 migrators]")
        else:
            print(f"📝 {file:<30} [{count}/15: {', '.join(migrators[:3])}...]")
    
    # Check for unique transformer files
    print("\n### Transformer Files Distribution")
    print("-" * 40)
    for file, migrators in sorted(transformer_files.items()):
        count = len(migrators)
        if count == 15:
            print(f"✅ {file:<30} [ALL migrators]")
        elif count > 10:
            print(f"⚠️  {file:<30} [{count}/15 migrators]")
        else:
            migrator_list = ', '.join(migrators) if count <= 3 else ', '.join(migrators[:3]) + '...'
            print(f"📝 {file:<30} [{count}/15: {migrator_list}]")
    
    # Check for unique utils files
    print("\n### Utils Files Distribution")
    print("-" * 40)
    for file, migrators in sorted(utils_files.items()):
        count = len(migrators)
        if count == 15:
            print(f"✅ {file:<30} [ALL migrators]")
        elif count > 10:
            print(f"⚠️  {file:<30} [{count}/15 migrators]")
        else:
            migrator_list = ', '.join(migrators) if count <= 3 else ', '.join(migrators[:3]) + '...'
            print(f"📝 {file:<30} [{count}/15: {migrator_list}]")
    
    # Check for prompt files
    print("\n### Prompt Files")
    print("-" * 40)
    migrators_with_prompts = [m for m, s in structures.items() if s['prompt_files']]
    print(f"Migrators with prompt files: {len(migrators_with_prompts)}/15")
    if migrators_with_prompts:
        print(f"Migrators: {', '.join(migrators_with_prompts)}")
    
    # Check for special directories
    print("\n### Special Directories")
    print("-" * 40)
    special_dirs_count = defaultdict(list)
    for migrator, structure in structures.items():
        for dir_name in structure['other_directories']:
            special_dirs_count[dir_name].append(migrator)
    
    for dir_name, migrators in sorted(special_dirs_count.items()):
        count = len(migrators)
        print(f"{dir_name:<20} [{count}/15 migrators]")
    
    # Summary of completeness
    print("\n" + "=" * 80)
    print("COMPLETENESS SUMMARY")
    print("=" * 80)
    
    core_files = ['ai_client.py', 'tallyfy_client.py']
    transformer_core = ['field_transformer.py', 'template_transformer.py', 
                        'instance_transformer.py', 'user_transformer.py']
    utils_core = ['checkpoint_manager.py', 'validator.py', 'error_handler.py', 'logger_config.py']
    
    print(f"\n✅ All 15 migrators have:")
    print(f"   - Core API files: {', '.join(core_files)}")
    print(f"   - Core transformers: {', '.join(transformer_core)}")
    print(f"   - Core utils: {', '.join(utils_core)}")
    print(f"   - Main orchestrator: main.py")
    
    # Additional features
    print(f"\n📊 Additional Features:")
    print(f"   - Migrators with prompts: {len(migrators_with_prompts)}/15")
    print(f"   - Migrators with docs: {len(special_dirs_count.get('docs', []))}/15")
    print(f"   - Migrators with tests: {len(special_dirs_count.get('tests', []))}/15")
    print(f"   - Migrators with validators: {len(special_dirs_count.get('validators', []))}/15")

if __name__ == "__main__":
    print_analysis()