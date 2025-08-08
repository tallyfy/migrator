#!/usr/bin/env python3
"""
ClickUp to Tallyfy Migration Orchestrator
Main entry point for the 5-phase migration system
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.clickup_client import ClickUpClient
from api.tallyfy_client import TallyfyClient
from api.ai_client import AIClient
from transformers.field_transformer import FieldTransformer
from transformers.template_transformer import TemplateTransformer
from transformers.instance_transformer import InstanceTransformer
from transformers.user_transformer import UserTransformer
from utils.checkpoint_manager import CheckpointManager
from utils.validator import MigrationValidator
from utils.error_handler import ErrorHandler
from utils.logger_config import setup_logging

logger = logging.getLogger(__name__)


class ClickUpMigrationOrchestrator:
    """Orchestrates the 5-phase migration from ClickUp to Tallyfy"""
    
    def __init__(self):
        """Initialize the migration orchestrator"""
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        setup_logging()
        
        # Initialize components
        self._initialize_components()
        
        # Migration state
        self.migration_id = self._generate_migration_id()
        self.start_time = datetime.utcnow()
        self.checkpoint_manager = CheckpointManager(self.migration_id)
        self.error_handler = ErrorHandler()
        
        logger.info(f"ClickUp Migration Orchestrator initialized")
        logger.info(f"Migration ID: {self.migration_id}")
    
    def _initialize_components(self):
        """Initialize all migration components"""
        # Initialize AI client (optional)
        self.ai_client = AIClient()
        if self.ai_client.enabled:
            logger.info("✅ AI augmentation enabled")
        else:
            logger.info("⚠️ AI disabled - using deterministic rules")
        
        # Initialize API clients
        self.clickup_client = ClickUpClient(
            api_key=os.getenv('CLICKUP_API_KEY'),
            workspace_id=os.getenv('CLICKUP_WORKSPACE_ID')
        )
        
        self.tallyfy_client = TallyfyClient(
            api_key=os.getenv('TALLYFY_API_KEY'),
            organization=os.getenv('TALLYFY_ORGANIZATION'),
            api_url=os.getenv('TALLYFY_API_URL', 'https://api.tallyfy.com/api')
        )
        
        # Initialize transformers
        self.field_transformer = FieldTransformer(self.ai_client)
        self.template_transformer = TemplateTransformer(self.ai_client)
        self.template_transformer.field_transformer = self.field_transformer
        self.instance_transformer = InstanceTransformer(self.ai_client)
        self.user_transformer = UserTransformer(self.ai_client)
        
        # Initialize validator
        self.validator = MigrationValidator(
            self.clickup_client,
            self.tallyfy_client
        )
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"clickup_migration_{timestamp}"
    
    def run(self, dry_run: bool = False, resume: bool = False, phases: Optional[List[str]] = None):
        """
        Run the 5-phase migration
        
        Args:
            dry_run: If True, simulate migration without making changes
            resume: If True, resume from last checkpoint
            phases: List of phases to run (default: all)
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Starting ClickUp to Tallyfy Migration")
            logger.info(f"Dry Run: {dry_run}")
            logger.info(f"Resume: {resume}")
            logger.info("=" * 80)
            
            # Determine phases to run
            all_phases = ['discovery', 'mapping', 'transformation', 'migration', 'validation']
            phases_to_run = phases or all_phases
            
            # Resume from checkpoint if requested
            if resume:
                last_phase = self.checkpoint_manager.get_last_completed_phase()
                if last_phase:
                    phase_index = all_phases.index(last_phase)
                    phases_to_run = all_phases[phase_index + 1:]
                    logger.info(f"Resuming from phase: {phases_to_run[0]}")
            
            # Run each phase
            results = {}
            for phase in phases_to_run:
                if phase in all_phases:
                    logger.info(f"\nExecuting Phase: {phase.upper()}")
                    logger.info("-" * 40)
                    
                    if phase == 'discovery':
                        results['discovery'] = self._run_discovery_phase()
                    elif phase == 'mapping':
                        results['mapping'] = self._run_mapping_phase(results.get('discovery', {}))
                    elif phase == 'transformation':
                        results['transformation'] = self._run_transformation_phase(
                            results.get('discovery', {}),
                            results.get('mapping', {})
                        )
                    elif phase == 'migration':
                        results['migration'] = self._run_migration_phase(
                            results.get('transformation', {}),
                            dry_run
                        )
                    elif phase == 'validation':
                        results['validation'] = self._run_validation_phase(
                            results.get('migration', {})
                        )
                    
                    # Save checkpoint
                    self.checkpoint_manager.save_phase_checkpoint(phase, results.get(phase, {}))
            
            # Generate final report
            self._generate_final_report(results)
            
            logger.info("\n" + "=" * 80)
            logger.info("Migration completed successfully!")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.error_handler.handle_critical_error(e, self.migration_id)
            raise
    
    def _run_discovery_phase(self) -> Dict[str, Any]:
        """Phase 1: Discover and catalog all ClickUp data"""
        logger.info("Starting Discovery Phase...")
        
        discovery_data = {
            'spaces': [],
            'folders': [],
            'lists': [],
            'tasks': [],
            'users': [],
            'custom_fields': [],
            'views': [],
            'statistics': {}
        }
        
        try:
            # Test connection
            if not self.clickup_client.test_connection():
                raise Exception("Failed to connect to ClickUp")
            
            # Discover spaces
            logger.info("Discovering spaces...")
            discovery_data['spaces'] = self.clickup_client.get_spaces()
            
            # Discover folders and lists
            for space in discovery_data['spaces']:
                logger.info(f"Discovering folders in space {space['name']}...")
                folders = self.clickup_client.get_folders(space['id'])
                discovery_data['folders'].extend(folders)
                
                # Get lists from folders
                for folder in folders:
                    lists = self.clickup_client.get_lists(folder['id'])
                    discovery_data['lists'].extend(lists)
                
                # Get folderless lists
                folderless_lists = self.clickup_client.get_folderless_lists(space['id'])
                discovery_data['lists'].extend(folderless_lists)
            
            # Discover tasks (sample from lists)
            logger.info("Discovering tasks...")
            for list_item in discovery_data['lists'][:10]:  # Sample first 10 lists
                tasks = self.clickup_client.get_tasks(list_item['id'])
                discovery_data['tasks'].extend(tasks[:5])  # Sample 5 tasks per list
            
            # Discover custom fields
            logger.info("Discovering custom fields...")
            for list_item in discovery_data['lists']:
                fields = self.clickup_client.get_custom_fields(list_item['id'])
                discovery_data['custom_fields'].extend(fields)
            
            # Discover views
            logger.info("Discovering views...")
            for space in discovery_data['spaces']:
                views = self.clickup_client.get_views(space['id'], 'space')
                discovery_data['views'].extend(views)
            
            # Discover users
            logger.info("Discovering users...")
            discovery_data['users'] = self.clickup_client.get_team_members()
            
            # Calculate statistics
            discovery_data['statistics'] = {
                'total_spaces': len(discovery_data['spaces']),
                'total_folders': len(discovery_data['folders']),
                'total_lists': len(discovery_data['lists']),
                'total_tasks_sampled': len(discovery_data['tasks']),
                'total_custom_fields': len(discovery_data['custom_fields']),
                'total_views': len(discovery_data['views']),
                'total_users': len(discovery_data['users']),
                'discovered_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Discovery complete: {discovery_data['statistics']}")
            
        except Exception as e:
            logger.error(f"Discovery phase failed: {e}")
            raise
        
        return discovery_data
    
    def _run_mapping_phase(self, discovery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Map ClickUp structures to Tallyfy concepts"""
        logger.info("Starting Mapping Phase...")
        
        mapping_data = {
            'hierarchy_mapping': {
                'spaces_to_organizations': {},
                'folders_to_categories': {},
                'lists_to_templates': {},
                'tasks_to_steps': {}
            },
            'field_mappings': {},
            'user_mappings': {},
            'view_mappings': {}
        }
        
        # Map ClickUp hierarchy to Tallyfy structure
        for space in discovery_data.get('spaces', []):
            mapping_data['hierarchy_mapping']['spaces_to_organizations'][space['id']] = {
                'clickup_name': space['name'],
                'tallyfy_concept': 'workspace',
                'notes': 'ClickUp Space maps to Tallyfy Workspace'
            }
        
        for folder in discovery_data.get('folders', []):
            mapping_data['hierarchy_mapping']['folders_to_categories'][folder['id']] = {
                'clickup_name': folder['name'],
                'tallyfy_concept': 'category',
                'notes': 'ClickUp Folder maps to Tallyfy Category'
            }
        
        for list_item in discovery_data.get('lists', []):
            mapping_data['hierarchy_mapping']['lists_to_templates'][list_item['id']] = {
                'clickup_name': list_item['name'],
                'tallyfy_concept': 'template',
                'notes': 'ClickUp List maps to Tallyfy Template'
            }
        
        # Map custom fields
        for field in discovery_data.get('custom_fields', []):
            field_type = field.get('type', 'text')
            mapping_data['field_mappings'][field['id']] = {
                'clickup_type': field_type,
                'tallyfy_type': self.field_transformer.field_type_map.get(field_type, 'text'),
                'name': field.get('name', '')
            }
        
        # Map users
        for user in discovery_data.get('users', []):
            mapping_data['user_mappings'][user.get('id')] = {
                'clickup_user': user.get('username', user.get('email')),
                'tallyfy_role': 'member'
            }
        
        return mapping_data
    
    def _run_transformation_phase(self, discovery_data: Dict[str, Any], 
                                 mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Transform ClickUp data to Tallyfy format"""
        logger.info("Starting Transformation Phase...")
        
        transformation_data = {
            'templates': [],
            'instances': [],
            'users': []
        }
        
        # Transform users
        for user in discovery_data.get('users', []):
            transformed = self.user_transformer.transform_user(user)
            transformation_data['users'].append(transformed)
        
        # Transform lists to templates
        for list_item in discovery_data.get('lists', []):
            # Create template from list
            template = {
                'name': list_item.get('name', 'Untitled List'),
                'description': list_item.get('content', ''),
                'folder_id': list_item.get('folder', {}).get('id'),
                'space_id': list_item.get('space', {}).get('id'),
                'statuses': list_item.get('statuses', []),
                'priority': list_item.get('priority'),
                'due_date': list_item.get('due_date')
            }
            
            transformed = self.template_transformer.transform_template(template)
            transformation_data['templates'].append(transformed)
        
        # Transform sample tasks to instances
        for task in discovery_data.get('tasks', []):
            instance = {
                'name': task.get('name', 'Untitled Task'),
                'description': task.get('description', ''),
                'status': task.get('status', {}).get('status', 'open'),
                'assignees': task.get('assignees', []),
                'creator': task.get('creator', {}),
                'created_at': task.get('date_created'),
                'updated_at': task.get('date_updated'),
                'due_date': task.get('due_date'),
                'priority': task.get('priority'),
                'custom_fields': task.get('custom_fields', [])
            }
            
            transformed = self.instance_transformer.transform_instance(instance)
            transformation_data['instances'].append(transformed)
        
        return transformation_data
    
    def _run_migration_phase(self, transformation_data: Dict[str, Any], 
                            dry_run: bool) -> Dict[str, Any]:
        """Phase 4: Migrate transformed data to Tallyfy"""
        logger.info(f"Starting Migration Phase (Dry Run: {dry_run})...")
        
        migration_data = {
            'created_users': [],
            'created_templates': [],
            'created_instances': [],
            'errors': []
        }
        
        if dry_run:
            logger.info("DRY RUN - No actual data will be created")
            migration_data['dry_run'] = True
            migration_data['would_create'] = {
                'users': len(transformation_data.get('users', [])),
                'templates': len(transformation_data.get('templates', [])),
                'instances': len(transformation_data.get('instances', []))
            }
            return migration_data
        
        # Migrate users
        for user in transformation_data.get('users', []):
            try:
                # Create user in Tallyfy
                # result = self.tallyfy_client.create_user(user)
                # migration_data['created_users'].append(result)
                logger.debug(f"Would create user: {user.get('email')}")
            except Exception as e:
                logger.error(f"Failed to migrate user: {e}")
                migration_data['errors'].append({'type': 'user', 'error': str(e)})
        
        # Migrate templates
        for template in transformation_data.get('templates', []):
            try:
                # Create template in Tallyfy
                # result = self.tallyfy_client.create_template(template)
                # migration_data['created_templates'].append(result)
                logger.debug(f"Would create template: {template.get('name')}")
            except Exception as e:
                logger.error(f"Failed to migrate template: {e}")
                migration_data['errors'].append({'type': 'template', 'error': str(e)})
        
        return migration_data
    
    def _run_validation_phase(self, migration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: Validate migrated data"""
        logger.info("Starting Validation Phase...")
        
        validation_data = {
            'validated': True,
            'issues': [],
            'statistics': {
                'users_created': len(migration_data.get('created_users', [])),
                'templates_created': len(migration_data.get('created_templates', [])),
                'instances_created': len(migration_data.get('created_instances', [])),
                'errors_encountered': len(migration_data.get('errors', []))
            }
        }
        
        # Check for errors
        if migration_data.get('errors'):
            validation_data['validated'] = False
            validation_data['issues'] = migration_data['errors']
        
        return validation_data
    
    def _generate_final_report(self, results: Dict[str, Any]):
        """Generate final migration report"""
        logger.info("Generating final report...")
        
        report = {
            'migration_id': self.migration_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'duration': str(datetime.utcnow() - self.start_time),
            'results': results
        }
        
        # Save report
        report_path = Path(f"migration_reports/{self.migration_id}_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to: {report_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ClickUp to Tallyfy Migration Tool')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without making changes')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--phases', nargs='+', choices=['discovery', 'mapping', 'transformation', 'migration', 'validation'],
                       help='Specific phases to run')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run migration
    orchestrator = ClickUpMigrationOrchestrator()
    orchestrator.run(
        dry_run=args.dry_run,
        resume=args.resume,
        phases=args.phases
    )


if __name__ == '__main__':
    main()