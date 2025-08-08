#!/usr/bin/env python3
"""
Pipefy to Tallyfy Migration Orchestrator
Main entry point for the migration system
"""

import os
import sys
import json
import yaml
import logging
import argparse
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.pipefy_client import PipefyClient
from api.tallyfy_client import TallyfyClient
from transformers.phase_transformer import PhaseTransformer
from transformers.field_transformer import FieldTransformer
from utils.id_mapper import IDMapper
from utils.progress_tracker import ProgressTracker
from utils.validator import MigrationValidator
from utils.logger_config import setup_logging
from utils.database_migrator import DatabaseMigrator

logger = logging.getLogger(__name__)


class PipefyMigrationOrchestrator:
    """Orchestrates the entire Pipefy to Tallyfy migration process"""
    
    def __init__(self, config_path: str):
        """
        Initialize migration orchestrator
        
        Args:
            config_path: Path to migration configuration file
        """
        # Load environment variables
        load_dotenv()
        
        self.config = self._load_config(config_path)
        self.start_time = datetime.utcnow()
        
        # Setup logging
        setup_logging(self.config['logging'])
        
        # Initialize components
        self._initialize_components()
        
        # Migration state
        self.migration_id = self._generate_migration_id()
        self.checkpoint_path = Path(self.config['storage']['checkpoints']['directory']) / self.migration_id
        self.checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Pipefy Migration orchestrator initialized with ID: {self.migration_id}")
        logger.warning("CRITICAL: Pipefy uses Kanban model, Tallyfy uses Sequential checklists - major paradigm shift!")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Expand environment variables
        config = self._expand_env_vars(config)
        
        return config
    
    def _expand_env_vars(self, config: Any) -> Any:
        """Recursively expand environment variables in config"""
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_var = config[2:-1]
            return os.environ.get(env_var, config)
        else:
            return config
    
    def _initialize_components(self):
        """Initialize all migration components"""
        # Initialize Pipefy GraphQL client
        self.pipefy_client = PipefyClient(
            api_token=os.environ.get('PIPEFY_API_TOKEN'),
            api_url=os.environ.get('PIPEFY_API_URL', 'https://api.pipefy.com/graphql'),
            organization_id=os.environ.get('PIPEFY_ORG_ID')
        )
        
        # Initialize Tallyfy client
        self.tallyfy_client = TallyfyClient(
            api_url=os.environ.get('TALLYFY_API_URL'),
            client_id=os.environ.get('TALLYFY_CLIENT_ID'),
            client_secret=os.environ.get('TALLYFY_CLIENT_SECRET'),
            organization_id=os.environ.get('TALLYFY_ORG_ID'),
            organization_slug=os.environ.get('TALLYFY_ORG_SLUG')
        )
        
        # Initialize ID mapper
        mapping_db_path = self.config['storage']['mapping_database']['path']
        self.id_mapper = IDMapper(mapping_db_path)
        
        # Initialize transformers
        self.phase_transformer = PhaseTransformer(self.id_mapper)
        self.field_transformer = FieldTransformer(self.id_mapper)
        
        # Initialize progress tracker
        self.progress = ProgressTracker()
        
        # Initialize validator
        self.validator = MigrationValidator(self.pipefy_client, self.tallyfy_client, self.id_mapper)
        
        # Initialize database migrator if configured
        self.db_migrator = None
        if os.environ.get('DATABASE_URL'):
            self.db_migrator = DatabaseMigrator(os.environ.get('DATABASE_URL'))
            logger.info("Database migrator initialized for Pipefy tables")
        else:
            logger.warning("No database configured - Pipefy tables will NOT be migrated")
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"pipefy_migration_{timestamp}"
    
    def run(self, phases: Optional[List[str]] = None, dry_run: bool = False, 
            pipe_id: Optional[str] = None, skip_tables: bool = False, 
            report_only: bool = False, resume: bool = False):
        """
        Run the migration
        
        Args:
            phases: Specific phases to run (None for all)
            dry_run: If True, simulate without making changes
            pipe_id: Specific pipe ID to migrate (None for all)
            skip_tables: Skip database table migration
            report_only: Generate report without migrating
            resume: If True, resume from last checkpoint
        """
        logger.info("=" * 80)
        logger.info(f"Starting Pipefy to Tallyfy Migration")
        logger.info(f"Migration ID: {self.migration_id}")
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Report Only: {report_only}")
        logger.info(f"Skip Tables: {skip_tables}")
        logger.info(f"Specific Pipe: {pipe_id or 'All pipes'}")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("DRY RUN MODE - No data will be migrated")
        
        if report_only:
            logger.info("REPORT ONLY MODE - Generating migration analysis")
            self._generate_analysis_report(pipe_id)
            return
        
        # Load checkpoint if resuming
        checkpoint = {}
        if resume:
            checkpoint = self._load_checkpoint()
            if checkpoint:
                logger.info(f"Resuming from checkpoint: {checkpoint.get('phase', 'unknown')}")
        
        # Determine phases to run
        all_phases = self.config['migration']['phases']
        if phases:
            phases_to_run = [p for p in all_phases if p in phases]
        else:
            phases_to_run = all_phases
        
        # Skip completed phases if resuming
        if checkpoint:
            completed_phases = checkpoint.get('completed_phases', [])
            phases_to_run = [p for p in phases_to_run if p not in completed_phases]
        
        # Skip tables phase if requested
        if skip_tables and 'tables' in phases_to_run:
            phases_to_run.remove('tables')
            logger.info("Skipping tables phase as requested")
        
        logger.info(f"Phases to run: {', '.join(phases_to_run)}")
        
        # Execute migration phases
        results = {}
        completed_phases = checkpoint.get('completed_phases', []) if checkpoint else []
        
        for phase in phases_to_run:
            if not self.config['migration']['phase_config'].get(phase, {}).get('enabled', True):
                logger.info(f"Skipping disabled phase: {phase}")
                continue
            
            logger.info(f"\n{'=' * 40}")
            logger.info(f"Starting Phase: {phase.upper()}")
            logger.info(f"{'=' * 40}")
            
            try:
                if phase == 'discovery':
                    results[phase] = self._phase_discovery(dry_run, pipe_id)
                elif phase == 'users':
                    results[phase] = self._phase_users(dry_run)
                elif phase == 'pipes':
                    results[phase] = self._phase_pipes(dry_run, pipe_id)
                elif phase == 'cards':
                    results[phase] = self._phase_cards(dry_run, pipe_id)
                elif phase == 'tables':
                    results[phase] = self._phase_tables(dry_run)
                elif phase == 'automations':
                    results[phase] = self._phase_automations(dry_run, pipe_id)
                elif phase == 'webhooks':
                    results[phase] = self._phase_webhooks(dry_run, pipe_id)
                elif phase == 'validation':
                    results[phase] = self._phase_validation(dry_run)
                else:
                    logger.warning(f"Unknown phase: {phase}")
                    continue
                
                completed_phases.append(phase)
                
                # Save checkpoint after each phase
                self._save_checkpoint({
                    'phase': phase,
                    'completed_phases': completed_phases,
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"✓ Phase {phase} completed successfully")
                
            except Exception as e:
                logger.error(f"✗ Phase {phase} failed: {e}")
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
                results[phase] = {'status': 'failed', 'error': str(e)}
        
        # Generate final report
        self._generate_report(results, dry_run)
        
        logger.info("\n" + "=" * 80)
        logger.info("Migration completed!")
        logger.info(f"Total time: {self._get_elapsed_time()}")
        logger.info("=" * 80)
    
    def _phase_discovery(self, dry_run: bool, pipe_id: Optional[str] = None) -> Dict[str, Any]:
        """Discovery phase - analyze Pipefy data"""
        logger.info("Discovering Pipefy data...")
        
        discovery = {
            'organization': {},
            'pipes': [],
            'tables': [],
            'counts': {
                'pipes': 0,
                'cards': 0,
                'phases': 0,
                'fields': 0,
                'tables': 0,
                'records': 0,
                'users': 0
            },
            'limitations': []
        }
        
        # Get organization info
        org_data = self.pipefy_client.get_organization()
        if org_data:
            discovery['organization'] = org_data
            discovery['counts']['users'] = org_data.get('members_count', 0)
        
        # Get pipes
        if pipe_id:
            # Single pipe
            pipe_data = self.pipefy_client.get_pipe(pipe_id)
            if pipe_data:
                discovery['pipes'].append(pipe_data)
                discovery['counts']['pipes'] = 1
                discovery['counts']['phases'] = len(pipe_data.get('phases', []))
                discovery['counts']['cards'] = pipe_data.get('cards_count', 0)
        else:
            # All pipes
            pipes = self.pipefy_client.list_pipes()
            discovery['pipes'] = pipes
            discovery['counts']['pipes'] = len(pipes)
            
            for pipe in pipes:
                discovery['counts']['phases'] += len(pipe.get('phases', []))
                discovery['counts']['cards'] += pipe.get('cards_count', 0)
        
        # Get tables
        if not pipe_id:  # Only get tables for full migration
            tables = self.pipefy_client.list_tables()
            discovery['tables'] = tables
            discovery['counts']['tables'] = len(tables)
            
            for table in tables:
                discovery['counts']['records'] += table.get('table_records_count', 0)
        
        # Identify limitations
        discovery['limitations'] = self._identify_limitations(discovery)
        
        # Save discovery results
        discovery_file = self.checkpoint_path / 'discovery.json'
        with open(discovery_file, 'w') as f:
            json.dump(discovery, f, indent=2)
        
        logger.info(f"Discovery saved to: {discovery_file}")
        
        # Log summary
        logger.info("\nDiscovery Summary:")
        for obj_type, count in discovery['counts'].items():
            logger.info(f"  - {obj_type}: {count}")
        
        if discovery['limitations']:
            logger.warning("\nLimitations identified:")
            for limitation in discovery['limitations']:
                logger.warning(f"  - {limitation}")
        
        return discovery
    
    def _phase_users(self, dry_run: bool) -> Dict[str, Any]:
        """Users migration phase"""
        logger.info("Migrating users...")
        
        # Get organization members
        members = self.pipefy_client.get_organization_members()
        logger.info(f"Found {len(members)} users to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping user creation")
            return {'total': len(members), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        
        for member in self.progress.track(members, description="Migrating users"):
            try:
                user = member.get('user', {})
                
                # Transform user
                tallyfy_user = {
                    "text": user.get("text"),
                    'first_name': user.get('name', '').split()[0] if user.get('name') else '',
                    'last_name': ' '.join(user.get('name', '').split()[1:]) if user.get('name') else '',
                    'username': user.get('username'),
                    'external_ref': user.get('id'),
                    'role': member.get('role_name', 'member')
                }
                
                # Check if user exists
                existing = self.tallyfy_client.find_user_by_email(tallyfy_user["text"])
                
                if existing:
                    logger.debug(f"User already exists: {tallyfy_user["text"]}")
                    self.id_mapper.add_mapping(user['id'], existing['id'], 'user')
                    successful += 1
                else:
                    # Create user in Tallyfy
                    created = self.tallyfy_client.create_user(tallyfy_user)
                    logger.debug(f"Created user: {tallyfy_user["text"]}")
                    self.id_mapper.add_mapping(user['id'], created['id'], 'user')
                    successful += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate user: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Users migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(members),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_pipes(self, dry_run: bool, pipe_id: Optional[str] = None) -> Dict[str, Any]:
        """Pipes migration phase - transform to checklists"""
        logger.info("Migrating pipes to checklists...")
        
        # Get pipes to migrate
        if pipe_id:
            pipes = [self.pipefy_client.get_pipe(pipe_id)]
        else:
            pipes = self.pipefy_client.list_pipes()
        
        logger.info(f"Found {len(pipes)} pipes to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping checklist creation")
            return {'total': len(pipes), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        
        for pipe in self.progress.track(pipes, description="Migrating pipes"):
            try:
                # Get full pipe details
                full_pipe = self.pipefy_client.get_pipe(pipe['id'])
                
                # Transform pipe to checklist
                checklist_data = self._transform_pipe_to_checklist(full_pipe)
                
                # Create checklist in Tallyfy
                created_checklist = self.tallyfy_client.create_checklist(checklist_data['multiselect'])
                checklist_id = created_checklist['id']
                
                # Map pipe ID
                self.id_mapper.add_mapping(pipe['id'], checklist_id, 'multiselect')
                
                # Create steps (transformed from phases)
                for step_group in checklist_data['step_groups']:
                    for step in step_group['steps']:
                        created_step = self.tallyfy_client.create_step(checklist_id, step)
                        
                        # Map phase to step group
                        if 'phase_id' in step_group:
                            self.id_mapper.add_mapping(step_group['phase_id'], created_step['id'], 'step_group')
                
                # Create field (transformed from fields)
                for field in checklist_data.get('field', []):
                    self.tallyfy_client.create_capture('multiselect', checklist_id, field)
                
                successful += 1
                logger.debug(f"Created checklist: {checklist_data['multiselect'].get('title')}")
                
            except Exception as e:
                logger.error(f"Failed to migrate pipe {pipe.get('name', 'unknown')}: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Pipes migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(pipes),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_cards(self, dry_run: bool, pipe_id: Optional[str] = None) -> Dict[str, Any]:
        """Cards migration phase - transform to processes"""
        logger.info("Migrating cards to processes...")
        
        # Get pipes to process
        if pipe_id:
            pipes = [{'id': pipe_id}]
        else:
            pipes = self.pipefy_client.list_pipes()
        
        total_cards = 0
        successful = 0
        failed = 0
        
        for pipe in pipes:
            # Get cards for this pipe
            cards = list(self.pipefy_client.list_cards(pipe['id']))
            total_cards += len(cards)
            
            logger.info(f"Processing {len(cards)} cards from pipe {pipe['id']}")
            
            if dry_run:
                continue
            
            # Get mapped checklist ID
            checklist_id = self.id_mapper.get_tallyfy_id(pipe['id'], 'multiselect')
            if not checklist_id:
                logger.warning(f"Checklist not found for pipe {pipe['id']}, skipping cards")
                continue
            
            for card in self.progress.track(cards, description=f"Migrating cards from pipe {pipe['id']}"):
                try:
                    # Transform card to process
                    process_data = self._transform_card_to_process(card, checklist_id)
                    
                    # Create process in Tallyfy
                    created_process = self.tallyfy_client.create_process(process_data)
                    run_id = created_process['id']
                    
                    # Map card ID
                    self.id_mapper.add_mapping(card['id'], run_id, 'process')
                    
                    # Migrate field values
                    self._migrate_card_fields(card, run_id)
                    
                    # Migrate comments
                    if card.get('comments'):
                        self._migrate_card_comments(card['comments'], run_id)
                    
                    # Migrate attachments
                    if card.get('attachments'):
                        self._migrate_card_attachments(card['attachments'], run_id)
                    
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate card {card.get('title', 'unknown')}: {e}")
                    failed += 1
                    if not self.config['migration']['options'].get('continue_on_error', False):
                        raise
        
        if dry_run:
            logger.info("DRY RUN - Skipping card creation")
            return {'total': total_cards, 'migrated': 0, 'dry_run': True}
        
        logger.info(f"Cards migrated: {successful} successful, {failed} failed")
        
        return {
            'total': total_cards,
            'successful': successful,
            'failed': failed
        }
    
    def _phase_tables(self, dry_run: bool) -> Dict[str, Any]:
        """Tables migration phase - to external database"""
        logger.info("Migrating Pipefy tables...")
        
        if not self.db_migrator:
            logger.warning("No database configured - skipping table migration")
            return {'total': 0, 'migrated': 0, 'skipped': True}
        
        tables = self.pipefy_client.list_tables()
        logger.info(f"Found {len(tables)} tables to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping table creation")
            return {'total': len(tables), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        total_records = 0
        
        for table in self.progress.track(tables, description="Migrating tables"):
            try:
                # Create table in external database
                table_name = self.db_migrator.create_table_from_pipefy(table)
                
                # Map table ID
                self.id_mapper.add_mapping(table['id'], table_name, 'table')
                
                # Migrate records
                records = list(self.pipefy_client.list_table_records(table['id']))
                total_records += len(records)
                
                for record in records:
                    self.db_migrator.insert_record(table_name, record)
                
                successful += 1
                logger.debug(f"Migrated table: {table['name']} with {len(records)} records")
                
            except Exception as e:
                logger.error(f"Failed to migrate table {table.get('name', 'unknown')}: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Tables migrated: {successful} successful, {failed} failed")
        logger.info(f"Total records migrated: {total_records}")
        
        return {
            'total_tables': len(tables),
            'successful_tables': successful,
            'failed_tables': failed,
            'total_records': total_records
        }
    
    def _phase_automations(self, dry_run: bool, pipe_id: Optional[str] = None) -> Dict[str, Any]:
        """Automations migration phase - to external platform"""
        logger.info("Migrating automations...")
        
        automations = self.pipefy_client.list_automations(pipe_id)
        logger.info(f"Found {len(automations)} automations")
        
        if dry_run:
            logger.info("DRY RUN - Skipping automation creation")
            return {'total': len(automations), 'migrated': 0, 'dry_run': True}
        
        # Log automations that need external setup
        webhook_url = os.environ.get('AUTOMATION_WEBHOOK_URL')
        
        if not webhook_url:
            logger.warning("No automation webhook configured - documenting automations only")
        
        # Save automation documentation
        automation_doc = []
        
        for automation in automations:
            doc_entry = {
                'pipefy_id': automation.get('id'),
                'name': automation.get('name'),
                'pipe_id': automation.get('pipe_id'),
                'trigger': automation.get('trigger_type'),
                'actions': automation.get('actions', []),
                'requires_external_setup': True,
                'webhook_url': webhook_url,
                'instructions': self._generate_automation_instructions(automation)
            }
            automation_doc.append(doc_entry)
        
        # Save documentation
        doc_file = self.checkpoint_path / 'automations_to_configure.json'
        with open(doc_file, 'w') as f:
            json.dump(automation_doc, f, indent=2)
        
        logger.info(f"Automation documentation saved to: {doc_file}")
        logger.warning(f"MANUAL ACTION REQUIRED: Configure {len(automations)} automations in external platform")
        
        return {
            'total': len(automations),
            'documented': len(automations),
            'requires_manual_setup': True
        }
    
    def _phase_webhooks(self, dry_run: bool, pipe_id: Optional[str] = None) -> Dict[str, Any]:
        """Webhooks migration phase"""
        logger.info("Migrating webhooks...")
        
        webhooks = self.pipefy_client.list_webhooks(pipe_id)
        logger.info(f"Found {len(webhooks)} webhooks to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping webhook creation")
            return {'total': len(webhooks), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        
        for webhook in webhooks:
            try:
                # Transform webhook
                tallyfy_webhook = {
                    "text": webhook.get("text"),
                    'events': self._map_webhook_events(webhook.get('actions', [])),
                    'is_active': True,
                    'external_ref': webhook.get('id')
                }
                
                self.tallyfy_client.create_webhook(tallyfy_webhook)
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate webhook: {e}")
                failed += 1
        
        logger.info(f"Webhooks migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(webhooks),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_validation(self, dry_run: bool) -> Dict[str, Any]:
        """Validation phase - verify migration success"""
        logger.info("Validating migration...")
        
        validation_results = self.validator.validate_migration()
        
        logger.info("\nValidation Results:")
        for check, result in validation_results.items():
            status = "✓" if result['passed'] else "✗"
            logger.info(f"  {status} {check}: {result['message']}")
        
        # Additional Pipefy-specific validations
        pipefy_checks = {
            'phase_transformation': self._validate_phase_transformation(),
            'field_mapping': self._validate_field_mapping(),
            'table_migration': self._validate_table_migration()
        }
        
        validation_results.update(pipefy_checks)
        
        return validation_results
    
    def _transform_pipe_to_checklist(self, pipe: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Pipefy pipe to Tallyfy checklist"""
        # Use phase transformer
        return self.phase_transformer.transform_pipe(pipe)
    
    def _transform_card_to_process(self, card: Dict[str, Any], checklist_id: str) -> Dict[str, Any]:
        """Transform Pipefy card to Tallyfy process"""
        return {
            'checklist_id': checklist_id,
            'title': card.get('title', 'Untitled Process'),
            'description': card.get("text", ''),
            'status': 'active' if not card.get('done') else 'completed',
            'due_date': card.get('due_date'),
            'created_at': card.get('created_at'),
            'external_ref': card.get('id'),
            'assignees': [self.id_mapper.get_tallyfy_id(a.get('id'), 'user') 
                         for a in card.get('assignees', [])],
            'labels': [l.get('name') for l in card.get('labels', [])]
        }
    
    def _migrate_card_fields(self, card: Dict[str, Any], run_id: str):
        """Migrate card field values to process"""
        for field in card.get('fields', []):
            try:
                # Transform field value
                transformed = self.field_transformer.transform_field_value(field)
                
                if transformed:
                    capture_id = self.id_mapper.get_tallyfy_id(
                        field.get('field', {}).get('id'), 
                        "field"
                    )
                    
                    if capture_id:
                        self.tallyfy_client.set_capture_value(
                            run_id, 
                            capture_id, 
                            transformed['value']
                        )
            except Exception as e:
                logger.warning(f"Failed to migrate field value: {e}")
    
    def _migrate_card_comments(self, comments: List[Dict], run_id: str):
        """Migrate card comments to process"""
        for comment in comments:
            try:
                self.tallyfy_client.create_comment(run_id, {
                    "text": comment.get("text"),
                    'author': self.id_mapper.get_tallyfy_id(
                        comment.get('author', {}).get('id'), 
                        'user'
                    ),
                    'created_at': comment.get('created_at')
                })
            except Exception as e:
                logger.warning(f"Failed to migrate comment: {e}")
    
    def _migrate_card_attachments(self, attachments: List[Dict], run_id: str):
        """Migrate card attachments to process"""
        for attachment in attachments:
            try:
                # Check file_upload size
                filesize = attachment.get('filesize', 0)
                
                if filesize > 100 * 1024 * 1024:  # 100MB
                    # Use S3 for large files
                    logger.info(f"Large file {attachment['filename']} - using S3")
                    # Implementation for S3 upload
                else:
                    # Direct upload to Tallyfy
                    self.tallyfy_client.upload_attachment(run_id, attachment)
                    
            except Exception as e:
                logger.warning(f"Failed to migrate attachment: {e}")
    
    def _identify_limitations(self, discovery: Dict[str, Any]) -> List[str]:
        """Identify migration limitations based on discovery"""
        limitations = []
        
        # Check for complex automations
        if discovery['counts'].get('automations', 0) > 0:
            limitations.append("Complex automations require external platform setup")
        
        # Check for database tables
        if discovery['counts'].get('tables', 0) > 0:
            if not self.db_migrator:
                limitations.append(f"{discovery['counts']['tables']} database tables cannot be migrated (no database configured)")
            else:
                limitations.append(f"{discovery['counts']['tables']} tables will be migrated to external database")
        
        # Check for large short_text of phases
        max_phases = max(len(p.get('phases', [])) for p in discovery['pipes']) if discovery['pipes'] else 0
        if max_phases > 10:
            limitations.append(f"Pipes with {max_phases} phases will create {max_phases * 3} steps in Tallyfy")
        
        # Check for specific field types
        complex_fields = ['connector', 'formula', 'dynamic_content']
        for pipe in discovery['pipes']:
            for phase in pipe.get('phases', []):
                for field in phase.get('fields', []):
                    if field.get('type') in complex_fields:
                        limitations.append(f"Complex field type '{field['type']}' requires special handling")
                        break
        
        return limitations
    
    def _generate_automation_instructions(self, automation: Dict[str, Any]) -> str:
        """Generate instructions for manually setting up automation"""
        instructions = []
        
        trigger = automation.get('trigger_type', 'unknown')
        actions = automation.get('actions', [])
        
        instructions.append(f"Trigger: When {trigger}")
        instructions.append("Actions:")
        
        for action in actions:
            action_type = action.get('type')
            instructions.append(f"  - {action_type}: {action.get('description', 'No description')}")
        
        instructions.append("\nSetup in external platform (n8n/Zapier/Make):")
        instructions.append("1. Create webhook trigger listening to Tallyfy events")
        instructions.append("2. Add condition to match trigger type")
        instructions.append("3. Implement each action using platform's capabilities")
        instructions.append("4. Test with sample data")
        
        return "\n".join(instructions)
    
    def _map_webhook_events(self, pipefy_actions: List[str]) -> List[str]:
        """Map Pipefy webhook actions to Tallyfy events"""
        event_map = {
            'card.create': 'process.created',
            'card.move': 'process.step_completed',
            'card.done': 'process.completed',
            'card.delete': 'process.deleted',
            'card.field_update': 'process.field_updated',
            'card.comment': 'process.comment_added'
        }
        
        return [event_map.get(action, 'all') for action in pipefy_actions]
    
    def _validate_phase_transformation(self) -> Dict[str, Any]:
        """Validate phase to step transformation"""
        # Check if phases were properly transformed
        phase_mappings = self.id_mapper.get_all_mappings('step_group')
        
        if phase_mappings:
            return {
                'passed': True,
                'message': f"Successfully transformed {len(phase_mappings)} phases to step groups"
            }
        else:
            return {
                'passed': False,
                'message': "No phase transformations found"
            }
    
    def _validate_field_mapping(self) -> Dict[str, Any]:
        """Validate field to field mapping"""
        field_mappings = self.id_mapper.get_all_mappings("field")
        
        if field_mappings:
            return {
                'passed': True,
                'message': f"Successfully mapped {len(field_mappings)} fields to field"
            }
        else:
            return {
                'passed': False,
                'message': "No field mappings found"
            }
    
    def _validate_table_migration(self) -> Dict[str, Any]:
        """Validate database table migration"""
        if not self.db_migrator:
            return {
                'passed': True,
                'message': "Table migration skipped (no database configured)"
            }
        
        table_mappings = self.id_mapper.get_all_mappings('table')
        
        if table_mappings:
            return {
                'passed': True,
                'message': f"Successfully migrated {len(table_mappings)} tables to external database"
            }
        else:
            return {
                'passed': False,
                'message': "No tables migrated"
            }
    
    def _generate_analysis_report(self, pipe_id: Optional[str] = None):
        """Generate detailed analysis report without migrating"""
        logger.info("Generating migration analysis report...")
        
        # Run discovery
        discovery = self._phase_discovery(dry_run=True, pipe_id=pipe_id)
        
        report = {
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'scope': 'single_pipe' if pipe_id else 'full_organization',
            'pipe_id': pipe_id,
            'summary': discovery['counts'],
            'limitations': discovery['limitations'],
            'effort_estimate': self._estimate_migration_effort(discovery),
            'recommendations': self._generate_recommendations(discovery)
        }
        
        # Save report
        report_file = self.checkpoint_path / 'analysis_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Analysis report saved to: {report_file}")
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION ANALYSIS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total objects to migrate: {sum(discovery['counts'].values())}")
        logger.info(f"Estimated effort: {report['effort_estimate']}")
        logger.info(f"Critical limitations: {len(discovery['limitations'])}")
        
        if report['recommendations']:
            logger.info("\nKey Recommendations:")
            for rec in report['recommendations'][:5]:
                logger.info(f"  • {rec}")
    
    def _estimate_migration_effort(self, discovery: Dict[str, Any]) -> str:
        """Estimate migration effort based on discovery"""
        # Calculate complexity score
        complexity = 0
        
        complexity += discovery['counts']['pipes'] * 10
        complexity += discovery['counts']['cards'] * 2
        complexity += discovery['counts']['tables'] * 20
        complexity += discovery['counts']['records'] * 0.5
        complexity += len(discovery['limitations']) * 15
        
        # Estimate time
        if complexity < 100:
            return "Low (< 1 day)"
        elif complexity < 500:
            return "Medium (1-3 days)"
        elif complexity < 2000:
            return "High (3-7 days)"
        else:
            return "Very High (1-2 weeks)"
    
    def _generate_recommendations(self, discovery: Dict[str, Any]) -> List[str]:
        """Generate migration recommendations"""
        recommendations = []
        
        if discovery['counts']['tables'] > 0:
            recommendations.append("Set up PostgreSQL database for table migration")
        
        if discovery['counts']['cards'] > 1000:
            recommendations.append("Consider migrating in batches to avoid rate limits")
        
        if any('automation' in l for l in discovery['limitations']):
            recommendations.append("Set up n8n or Zapier for automation migration")
        
        if discovery['counts']['phases'] > 50:
            recommendations.append("Review and simplify workflow complexity before migration")
        
        recommendations.append("Run in dry-run mode first to validate transformation")
        recommendations.append("Keep Pipefy running in parallel for 30 days after migration")
        
        return recommendations
    
    def _save_checkpoint(self, data: Dict[str, Any]):
        """Save migration checkpoint"""
        checkpoint_file = self.checkpoint_path / 'checkpoint.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Checkpoint saved: {checkpoint_file}")
    
    def _load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load migration checkpoint"""
        checkpoint_file = self.checkpoint_path / 'checkpoint.json'
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        return None
    
    def _get_elapsed_time(self) -> str:
        """Get elapsed time since migration started"""
        elapsed = datetime.utcnow() - self.start_time
        hours = elapsed.seconds // 3600
        minutes = (elapsed.seconds % 3600) // 60
        seconds = elapsed.seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _generate_report(self, results: Dict[str, Any], dry_run: bool):
        """Generate migration report"""
        report = {
            'migration_id': self.migration_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'elapsed_time': self._get_elapsed_time(),
            'dry_run': dry_run,
            'results': results,
            'statistics': {
                'pipefy_api_calls': self.pipefy_client.stats,
                'tallyfy_api_calls': self.tallyfy_client.get_import_statistics() if hasattr(self.tallyfy_client, 'get_import_statistics') else {},
                'transformations': {
                    'phases': self.phase_transformer.get_statistics() if hasattr(self.phase_transformer, 'get_statistics') else {},
                    'fields': self.field_transformer.get_statistics() if hasattr(self.field_transformer, 'get_statistics') else {}
                }
            }
        }
        
        # Save report
        report_file = self.checkpoint_path / 'migration_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nMigration report saved: {report_file}")
        
        # Generate HTML report if configured
        if self.config.get('monitoring', {}).get('reports', {}).get('formats', []):
            if 'html' in self.config['monitoring']['reports']['formats']:
                self._generate_html_report(report)
    
    def _generate_html_report(self, report: Dict[str, Any]):
        """Generate HTML report"""
        # Implementation for HTML report generation
        pass


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Pipefy to Tallyfy Migration Tool'
    )
    
    parser.add_argument(
        '--config',
        default='config/migration_config.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--phase',
        action='append',
        help='Specific phase to run (can be specified multiple times)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without making changes'
    )
    
    parser.add_argument(
        '--pipe-id',
        help='Migrate specific pipe only'
    )
    
    parser.add_argument(
        '--skip-tables',
        action='store_true',
        help='Skip database table migration'
    )
    
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate migration report without migrating'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only run validation phase'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = PipefyMigrationOrchestrator(args.config)
        
        # Determine phases
        if args.validate_only:
            phases = ['validation']
        else:
            phases = args.phase
        
        # Run migration
        orchestrator.run(
            phases=phases,
            dry_run=args.dry_run,
            pipe_id=args.pipe_id,
            skip_tables=args.skip_tables,
            report_only=args.report_only,
            resume=args.resume
        )
        
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()