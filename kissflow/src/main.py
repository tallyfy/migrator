"""Main orchestrator for Kissflow to Tallyfy migration."""

import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.kissflow_client import KissflowClient
from src.api.tallyfy_client import TallyfyClient
from src.transformers.user_transformer import UserTransformer
from src.transformers.process_transformer import ProcessTransformer
from src.transformers.board_transformer import BoardTransformer
from src.transformers.app_transformer import AppTransformer
from src.transformers.dataset_transformer import DatasetTransformer
from src.transformers.instance_transformer import InstanceTransformer
from src.utils.id_mapper import IDMapper
from src.utils.progress_tracker import ProgressTracker
from src.utils.validator import Validator
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.error_handler import ErrorHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class KissflowMigrator:
    """Main orchestrator for Kissflow to Tallyfy migration."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize migrator with configuration.
        
        Args:
            config: Migration configuration
        """
        self.config = config
        self.dry_run = config.get('dry_run', False)
        self.report_only = config.get('report_only', False)
        
        # Initialize API clients
        self.kissflow_client = KissflowClient(
            subdomain=config['kissflow']['subdomain'],
            account_id=config['kissflow']['account_id'],
            access_key_id=config['kissflow']['access_key_id'],
            access_key_secret=config['kissflow']['access_key_secret']
        )
        
        self.tallyfy_client = TallyfyClient(
            api_token=config['tallyfy']['api_token'],
            organization_id=config['tallyfy']['organization_id']
        )
        
        # Initialize transformers
        self.user_transformer = UserTransformer()
        self.process_transformer = ProcessTransformer()
        self.board_transformer = BoardTransformer()
        self.app_transformer = AppTransformer()
        self.dataset_transformer = DatasetTransformer()
        self.instance_transformer = InstanceTransformer()
        
        # Initialize utilities
        self.id_mapper = IDMapper('kissflow_tallyfy_mapping.db')
        self.progress_tracker = ProgressTracker()
        self.validator = Validator()
        self.checkpoint_manager = CheckpointManager('checkpoints')
        self.error_handler = ErrorHandler()
        
        # Migration statistics
        self.stats = {
            'users': {'total': 0, 'migrated': 0, 'failed': 0},
            'processes': {'total': 0, 'migrated': 0, 'failed': 0},
            'boards': {'total': 0, 'migrated': 0, 'failed': 0},
            'apps': {'total': 0, 'migrated': 0, 'failed': 0},
            'datasets': {'total': 0, 'migrated': 0, 'failed': 0},
            'instances': {'total': 0, 'migrated': 0, 'failed': 0},
            'start_time': datetime.now(),
            'errors': []
        }
    
    def run(self) -> Dict[str, Any]:
        """Run the complete migration process.
        
        Returns:
            Migration results and statistics
        """
        logger.info("=" * 80)
        logger.info("Starting Kissflow to Tallyfy Migration")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info(f"Report Only: {self.report_only}")
        logger.info("=" * 80)
        
        try:
            # Phase 0: Pre-flight checks
            if not self._run_preflight_checks():
                logger.error("Pre-flight checks failed. Aborting migration.")
                return self.stats
            
            # Phase 1: Discovery - Analyze what needs to be migrated
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 1: DISCOVERY")
            logger.info("=" * 80)
            discovery_data = self._run_discovery()
            
            if self.report_only:
                self._generate_report(discovery_data)
                return self.stats
            
            # Phase 2: Users and Groups Migration
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 2: USERS AND GROUPS")
            logger.info("=" * 80)
            user_mapping = self._migrate_users(discovery_data['users'])
            
            # Phase 3: Datasets Migration (Reference Data)
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 3: DATASETS (REFERENCE DATA)")
            logger.info("=" * 80)
            dataset_mapping = self._migrate_datasets(discovery_data['datasets'])
            
            # Phase 4: Templates Migration (Processes, Boards, Apps)
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 4: TEMPLATES")
            logger.info("=" * 80)
            template_mapping = self._migrate_templates(discovery_data, user_mapping)
            
            # Phase 5: Running Instances Migration
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 5: RUNNING INSTANCES")
            logger.info("=" * 80)
            self._migrate_instances(discovery_data['instances'], template_mapping, user_mapping)
            
            # Phase 6: Validation
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 6: VALIDATION")
            logger.info("=" * 80)
            validation_results = self._run_validation()
            
            # Generate final report
            self.stats['end_time'] = datetime.now()
            self.stats['duration'] = str(self.stats['end_time'] - self.stats['start_time'])
            self.stats['validation'] = validation_results
            
            self._generate_final_report()
            
            logger.info("\n" + "=" * 80)
            logger.info("MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}", exc_info=True)
            self.stats['errors'].append({
                'phase': 'general',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            self.error_handler.handle_critical_error(e)
        
        return self.stats
    
    def _run_preflight_checks(self) -> bool:
        """Run pre-flight checks to ensure migration readiness.
        
        Returns:
            True if all checks pass
        """
        logger.info("Running pre-flight checks...")
        
        checks_passed = True
        
        # Check Kissflow connectivity
        try:
            org_info = self.kissflow_client.test_connection()
            logger.info(f"✓ Kissflow connection successful: {org_info.get('Name')}")
        except Exception as e:
            logger.error(f"✗ Kissflow connection failed: {str(e)}")
            checks_passed = False
        
        # Check Tallyfy connectivity
        try:
            org_info = self.tallyfy_client.test_connection()
            logger.info(f"✓ Tallyfy connection successful: {org_info.get('name')}")
        except Exception as e:
            logger.error(f"✗ Tallyfy connection failed: {str(e)}")
            checks_passed = False
        
        # Check for existing checkpoint
        if self.checkpoint_manager.has_checkpoint():
            logger.info("✓ Found existing checkpoint - migration can be resumed")
            response = input("Resume from checkpoint? (y/n): ")
            if response.lower() == 'y':
                self.checkpoint_manager.load_checkpoint()
        
        # Check disk space for logs and checkpoints
        import shutil
        free_space = shutil.disk_usage('.').free
        required_space = 1024 * 1024 * 1024  # 1GB
        if free_space < required_space:
            logger.warning(f"⚠ Low disk space: {free_space / (1024**3):.2f}GB available")
        
        return checks_passed
    
    def _run_discovery(self) -> Dict[str, Any]:
        """Discover all objects to migrate from Kissflow.
        
        Returns:
            Discovery data with all objects
        """
        discovery_data = {
            'users': [],
            'groups': [],
            'processes': [],
            'boards': [],
            'apps': [],
            'datasets': [],
            'instances': [],
            'statistics': {}
        }
        
        # Discover users
        logger.info("Discovering users...")
        discovery_data['users'] = self.kissflow_client.get_users()
        self.stats['users']['total'] = len(discovery_data['users'])
        logger.info(f"Found {len(discovery_data['users'])} users")
        
        # Discover groups
        logger.info("Discovering groups...")
        discovery_data['groups'] = self.kissflow_client.get_groups()
        logger.info(f"Found {len(discovery_data['groups'])} groups")
        
        # Discover processes
        logger.info("Discovering processes...")
        discovery_data['processes'] = self.kissflow_client.get_processes()
        self.stats['processes']['total'] = len(discovery_data['processes'])
        logger.info(f"Found {len(discovery_data['processes'])} processes")
        
        # Discover boards
        logger.info("Discovering boards...")
        discovery_data['boards'] = self.kissflow_client.get_boards()
        self.stats['boards']['total'] = len(discovery_data['boards'])
        logger.info(f"Found {len(discovery_data['boards'])} boards")
        
        # Discover apps
        logger.info("Discovering apps...")
        discovery_data['apps'] = self.kissflow_client.get_apps()
        self.stats['apps']['total'] = len(discovery_data['apps'])
        logger.info(f"Found {len(discovery_data['apps'])} apps")
        
        # Discover datasets
        logger.info("Discovering datasets...")
        discovery_data['datasets'] = self.kissflow_client.get_datasets()
        self.stats['datasets']['total'] = len(discovery_data['datasets'])
        logger.info(f"Found {len(discovery_data['datasets'])} datasets")
        
        # Discover running instances (sample)
        logger.info("Discovering running instances...")
        instance_limit = self.config.get('instance_limit', 100)
        
        # Get process instances
        for process in discovery_data['processes'][:5]:  # Sample first 5 processes
            instances = self.kissflow_client.get_process_instances(
                process['Id'], limit=instance_limit
            )
            discovery_data['instances'].extend(instances)
        
        # Get board cards
        for board in discovery_data['boards'][:5]:  # Sample first 5 boards
            cards = self.kissflow_client.get_board_cards(
                board['Id'], limit=instance_limit
            )
            discovery_data['instances'].extend(cards)
        
        self.stats['instances']['total'] = len(discovery_data['instances'])
        logger.info(f"Found {len(discovery_data['instances'])} running instances (sample)")
        
        # Calculate statistics
        discovery_data['statistics'] = {
            'total_objects': sum([
                len(discovery_data['users']),
                len(discovery_data['processes']),
                len(discovery_data['boards']),
                len(discovery_data['apps']),
                len(discovery_data['datasets']),
                len(discovery_data['instances'])
            ]),
            'complexity_score': self._calculate_complexity(discovery_data)
        }
        
        return discovery_data
    
    def _migrate_users(self, users: List[Dict[str, Any]]) -> Dict[str, str]:
        """Migrate users and groups.
        
        Args:
            users: List of Kissflow users
            
        Returns:
            Mapping of Kissflow user IDs to Tallyfy member IDs
        """
        user_mapping = {}
        
        for user in users:
            try:
                # Check if already migrated
                existing_id = self.id_mapper.get_tallyfy_id('user', user['Id'])
                if existing_id:
                    user_mapping[user['Id']] = existing_id
                    continue
                
                # Transform user
                tallyfy_member = self.user_transformer.transform_user(user)
                
                if not self.dry_run:
                    # Create member in Tallyfy
                    created_member = self.tallyfy_client.create_member(
                        email=tallyfy_member["text"],
                        first_name=tallyfy_member['firstname'],
                        last_name=tallyfy_member['lastname'],
                        role=tallyfy_member['role']
                    )
                    
                    # Store mapping
                    self.id_mapper.add_mapping('user', user['Id'], created_member['id'])
                    user_mapping[user['Id']] = created_member['id']
                    
                    self.stats['users']['migrated'] += 1
                    logger.info(f"✓ Migrated user: {tallyfy_member["text"]}")
                else:
                    logger.info(f"[DRY RUN] Would migrate user: {tallyfy_member["text"]}")
                    user_mapping[user['Id']] = f"dry_run_{user['Id']}"
                
            except Exception as e:
                self.stats['users']['failed'] += 1
                self.error_handler.handle_error(e, context={'user': user})
                logger.error(f"✗ Failed to migrate user {user.get('Email')}: {str(e)}")
        
        logger.info(f"User migration complete: {self.stats['users']['migrated']}/{self.stats['users']['total']} successful")
        
        return user_mapping
    
    def _migrate_datasets(self, datasets: List[Dict[str, Any]]) -> Dict[str, str]:
        """Migrate datasets as reference data.
        
        Args:
            datasets: List of Kissflow datasets
            
        Returns:
            Mapping of dataset IDs
        """
        dataset_mapping = {}
        
        for dataset in datasets:
            try:
                # Get dataset records
                records = self.kissflow_client.get_dataset_records(dataset['Id'])
                
                # Transform dataset
                blueprint = self.dataset_transformer.transform_dataset_to_blueprint(
                    dataset, records
                )
                
                if not self.dry_run:
                    # Create blueprint for dataset management
                    created_blueprint = self.tallyfy_client.create_blueprint(
                        name=blueprint['name'],
                        description=blueprint['description'],
                        steps=blueprint['steps']
                    )
                    
                    # Store mapping
                    self.id_mapper.add_mapping('dataset', dataset['Id'], created_blueprint['id'])
                    dataset_mapping[dataset['Id']] = created_blueprint['id']
                    
                    # Store reference data
                    self._store_reference_data(created_blueprint['id'], blueprint['reference_data'])
                    
                    self.stats['datasets']['migrated'] += 1
                    logger.info(f"✓ Migrated dataset: {dataset['Name']} ({len(records)} records)")
                else:
                    logger.info(f"[DRY RUN] Would migrate dataset: {dataset['Name']} ({len(records)} records)")
                    dataset_mapping[dataset['Id']] = f"dry_run_{dataset['Id']}"
                
            except Exception as e:
                self.stats['datasets']['failed'] += 1
                self.error_handler.handle_error(e, context={'dataset': dataset})
                logger.error(f"✗ Failed to migrate dataset {dataset.get('Name')}: {str(e)}")
        
        return dataset_mapping
    
    def _migrate_templates(self, discovery_data: Dict[str, Any],
                          user_mapping: Dict[str, str]) -> Dict[str, str]:
        """Migrate all templates (processes, boards, apps).
        
        Args:
            discovery_data: All discovered objects
            user_mapping: User ID mapping
            
        Returns:
            Mapping of template IDs
        """
        template_mapping = {}
        
        # Migrate processes
        logger.info("Migrating processes...")
        for process in discovery_data['processes']:
            try:
                # Get process details
                fields = self.kissflow_client.get_process_fields(process['Id'])
                workflow = self.kissflow_client.get_process_workflow(process['Id'])
                
                # Transform process
                blueprint = self.process_transformer.transform_process_to_blueprint(
                    process, fields, workflow
                )
                
                if not self.dry_run:
                    # Create blueprint
                    created = self.tallyfy_client.create_blueprint(
                        name=blueprint['name'],
                        description=blueprint['description'],
                        steps=blueprint['steps']
                    )
                    
                    template_mapping[f"process:{process['Id']}"] = created['id']
                    self.id_mapper.add_mapping('process', process['Id'], created['id'])
                    self.stats['processes']['migrated'] += 1
                    logger.info(f"✓ Migrated process: {process['Name']}")
                else:
                    logger.info(f"[DRY RUN] Would migrate process: {process['Name']}")
                
            except Exception as e:
                self.stats['processes']['failed'] += 1
                self.error_handler.handle_error(e, context={'process': process})
                logger.error(f"✗ Failed to migrate process {process.get('Name')}: {str(e)}")
        
        # Migrate boards
        logger.info("Migrating boards...")
        for board in discovery_data['boards']:
            try:
                # Transform board (critical paradigm shift)
                blueprint = self.board_transformer.transform_board_to_blueprint(board)
                
                if not self.dry_run:
                    created = self.tallyfy_client.create_blueprint(
                        name=blueprint['name'],
                        description=blueprint['description'],
                        steps=blueprint['steps']
                    )
                    
                    template_mapping[f"board:{board['Id']}"] = created['id']
                    self.id_mapper.add_mapping('board', board['Id'], created['id'])
                    self.stats['boards']['migrated'] += 1
                    logger.info(f"✓ Migrated board: {board['Name']} (Kanban→Sequential)")
                else:
                    logger.info(f"[DRY RUN] Would migrate board: {board['Name']}")
                
            except Exception as e:
                self.stats['boards']['failed'] += 1
                self.error_handler.handle_error(e, context={'board': board})
                logger.error(f"✗ Failed to migrate board {board.get('Name')}: {str(e)}")
        
        # Migrate apps
        logger.info("Migrating apps...")
        for app in discovery_data['apps']:
            try:
                # Get app components
                forms = self.kissflow_client.get_app_forms(app['Id'])
                views = self.kissflow_client.get_app_views(app['Id'])
                workflows = self.kissflow_client.get_app_workflows(app['Id'])
                
                # Transform app
                blueprint = self.app_transformer.transform_app_to_blueprint(
                    app, forms, views, workflows
                )
                
                if not self.dry_run:
                    created = self.tallyfy_client.create_blueprint(
                        name=blueprint['name'],
                        description=blueprint['description'],
                        steps=blueprint['steps']
                    )
                    
                    template_mapping[f"app:{app['Id']}"] = created['id']
                    self.id_mapper.add_mapping('app', app['Id'], created['id'])
                    self.stats['apps']['migrated'] += 1
                    logger.info(f"✓ Migrated app: {app['Name']}")
                else:
                    logger.info(f"[DRY RUN] Would migrate app: {app['Name']}")
                
            except Exception as e:
                self.stats['apps']['failed'] += 1
                self.error_handler.handle_error(e, context={'app': app})
                logger.error(f"✗ Failed to migrate app {app.get('Name')}: {str(e)}")
        
        return template_mapping
    
    def _migrate_instances(self, instances: List[Dict[str, Any]],
                          template_mapping: Dict[str, str],
                          user_mapping: Dict[str, str]):
        """Migrate running instances.
        
        Args:
            instances: List of running instances
            template_mapping: Template ID mapping
            user_mapping: User ID mapping
        """
        for instance in instances:
            try:
                # Determine instance type and blueprint
                instance_type = instance.get('Type', 'process')
                source_id = instance.get('ProcessId') or instance.get('BoardId') or instance.get('AppId')
                
                blueprint_key = f"{instance_type}:{source_id}"
                checklist_id = template_mapping.get(blueprint_key)
                
                if not checklist_id:
                    logger.warning(f"No blueprint found for instance {instance.get('Id')}")
                    continue
                
                # Transform instance based on type
                if instance_type == 'process':
                    process = self.instance_transformer.transform_process_instance(
                        instance, checklist_id, user_mapping
                    )
                elif instance_type == 'board':
                    process = self.instance_transformer.transform_board_card(
                        instance, checklist_id, user_mapping
                    )
                else:
                    process = self.instance_transformer.transform_app_record(
                        instance, checklist_id, user_mapping
                    )
                
                if not self.dry_run:
                    # Create process in Tallyfy
                    created = self.tallyfy_client.create_process(
                        checklist_id=process['checklist_id'],
                        name=process['name'],
                        data=process.get('data', {})
                    )
                    
                    self.id_mapper.add_mapping('instance', instance['Id'], created['id'])
                    self.stats['instances']['migrated'] += 1
                    logger.info(f"✓ Migrated instance: {process['name']}")
                else:
                    logger.info(f"[DRY RUN] Would migrate instance: {process['name']}")
                
            except Exception as e:
                self.stats['instances']['failed'] += 1
                self.error_handler.handle_error(e, context={'instance': instance})
                logger.error(f"✗ Failed to migrate instance {instance.get('Id')}: {str(e)}")
    
    def _run_validation(self) -> Dict[str, Any]:
        """Run post-migration validation.
        
        Returns:
            Validation results
        """
        logger.info("Running validation checks...")
        
        validation_results = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': []
        }
        
        # Validate user migration
        user_validation = self.validator.validate_users(self.id_mapper)
        validation_results['users'] = user_validation
        
        # Validate template migration
        template_validation = self.validator.validate_templates(self.id_mapper)
        validation_results['templates'] = template_validation
        
        # Validate instance migration
        instance_validation = self.validator.validate_instances(self.id_mapper)
        validation_results['instances'] = instance_validation
        
        return validation_results
    
    def _calculate_complexity(self, discovery_data: Dict[str, Any]) -> int:
        """Calculate migration complexity score.
        
        Args:
            discovery_data: Discovery data
            
        Returns:
            Complexity score (0-100)
        """
        score = 0
        
        # User complexity
        score += min(20, len(discovery_data['users']) / 10)
        
        # Process complexity
        score += min(20, len(discovery_data['processes']) / 5)
        
        # Board complexity (paradigm shift adds complexity)
        score += min(30, len(discovery_data['boards']) * 3)
        
        # App complexity (highest complexity)
        score += min(30, len(discovery_data['apps']) * 5)
        
        return min(100, score)
    
    def _store_reference_data(self, checklist_id: str, reference_data: Dict[str, Any]):
        """Store reference data for datasets.
        
        Args:
            checklist_id: Blueprint ID
            reference_data: Reference data to store
        """
        # Store in a JSON file_upload for now
        filename = f"reference_data_{checklist_id}.json"
        with open(filename, 'w') as f:
            json.dump(reference_data, f, indent=2)
        logger.info(f"Stored reference data in {filename}")
    
    def _generate_report(self, discovery_data: Dict[str, Any]):
        """Generate discovery report.
        
        Args:
            discovery_data: Discovery data
        """
        report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("KISSFLOW TO TALLYFY MIGRATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}\n\n")
            
            f.write("DISCOVERY SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Users: {len(discovery_data['users'])}\n")
            f.write(f"Groups: {len(discovery_data['groups'])}\n")
            f.write(f"Processes: {len(discovery_data['processes'])}\n")
            f.write(f"Boards: {len(discovery_data['boards'])}\n")
            f.write(f"Apps: {len(discovery_data['apps'])}\n")
            f.write(f"Datasets: {len(discovery_data['datasets'])}\n")
            f.write(f"Running Instances: {len(discovery_data['instances'])}\n")
            f.write(f"\nTotal Objects: {discovery_data['statistics']['total_objects']}\n")
            f.write(f"Complexity Score: {discovery_data['statistics']['complexity_score']}/100\n")
            
            # Add detailed sections
            f.write("\n\nDETAILED ANALYSIS\n")
            f.write("=" * 80 + "\n")
            
            # Processes
            f.write("\nPROCESSES:\n")
            for process in discovery_data['processes'][:10]:
                f.write(f"  • {process.get('Name')} (ID: {process.get('Id')})\n")
            if len(discovery_data['processes']) > 10:
                f.write(f"  ... and {len(discovery_data['processes']) - 10} more\n")
            
            # Boards (with paradigm shift warning)
            f.write("\nBOARDS (⚠️ Kanban→Sequential Paradigm Shift):\n")
            for board in discovery_data['boards'][:10]:
                f.write(f"  • {board.get('Name')} - {len(board.get('Columns', []))} columns → {len(board.get('Columns', [])) * 3} steps\n")
            if len(discovery_data['boards']) > 10:
                f.write(f"  ... and {len(discovery_data['boards']) - 10} more\n")
            
            # Apps
            f.write("\nAPPS (Complex Migration):\n")
            for app in discovery_data['apps'][:10]:
                f.write(f"  • {app.get('Name')} (Type: {app.get('Type', 'custom')})\n")
            if len(discovery_data['apps']) > 10:
                f.write(f"  ... and {len(discovery_data['apps']) - 10} more\n")
        
        logger.info(f"Report generated: {report_file}")
    
    def _generate_final_report(self):
        """Generate final migration report."""
        report_file = f"migration_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("KISSFLOW TO TALLYFY MIGRATION - FINAL REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Start Time: {self.stats['start_time'].isoformat()}\n")
            f.write(f"End Time: {self.stats.get('end_time', datetime.now()).isoformat()}\n")
            f.write(f"Duration: {self.stats.get('duration', 'N/A')}\n\n")
            
            f.write("MIGRATION RESULTS\n")
            f.write("-" * 40 + "\n")
            
            for obj_type in ['users', 'processes', 'boards', 'apps', 'datasets', 'instances']:
                stats = self.stats[obj_type]
                f.write(f"\n{obj_type.upper()}:\n")
                f.write(f"  Total: {stats['total']}\n")
                f.write(f"  Migrated: {stats['migrated']}\n")
                f.write(f"  Failed: {stats['failed']}\n")
                if stats['total'] > 0:
                    success_rate = (stats['migrated'] / stats['total']) * 100
                    f.write(f"  Success Rate: {success_rate:.1f}%\n")
            
            if self.stats['errors']:
                f.write("\n\nERRORS ENCOUNTERED\n")
                f.write("-" * 40 + "\n")
                for error in self.stats['errors'][:20]:
                    f.write(f"\n{error['timestamp']}: {error['error']}\n")
                if len(self.stats['errors']) > 20:
                    f.write(f"\n... and {len(self.stats['errors']) - 20} more errors\n")
            
            if 'validation' in self.stats:
                f.write("\n\nVALIDATION RESULTS\n")
                f.write("-" * 40 + "\n")
                f.write(json.dumps(self.stats['validation'], indent=2))
        
        logger.info(f"Final report generated: {report_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate from Kissflow to Tallyfy')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--report-only', action='store_true', help='Generate report without migration')
    parser.add_argument('--instance-limit', type=int, default=100, help='Limit instances to migrate')
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Override with command line arguments
    config['dry_run'] = args.dry_run
    config['report_only'] = args.report_only
    config['instance_limit'] = args.instance_limit
    
    # Run migration
    migrator = KissflowMigrator(config)
    results = migrator.run()
    
    # Print summary
    print("\nMigration Summary:")
    print("=" * 40)
    for obj_type in ['users', 'processes', 'boards', 'apps', 'datasets', 'instances']:
        stats = results[obj_type]
        print(f"{obj_type.capitalize()}: {stats['migrated']}/{stats['total']} migrated")
    
    sys.exit(0 if results.get('errors', []) == [] else 1)


if __name__ == '__main__':
    main()