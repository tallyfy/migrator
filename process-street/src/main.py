#!/usr/bin/env python3
"""
Process Street to Tallyfy Migration Orchestrator
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

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.ps_client import ProcessStreetClient
from api.tallyfy_client import TallyfyClient
from api.ai_client import AIClient
from transformers.user_transformer import UserTransformer
from transformers.template_transformer import TemplateTransformer
from transformers.form_transformer import FormTransformer
from utils.id_mapper import IDMapper
from utils.progress_tracker import ProgressTracker
from utils.validator import MigrationValidator
from utils.logger_config import setup_logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrates the entire migration process"""
    
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
        
        logger.info(f"Process Street Migration orchestrator initialized with ID: {self.migration_id}")
        logger.info(f"API Version: Process Street v1.1, Tallyfy v2")
    
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
        # Initialize AI client
        self.ai_client = AIClient()
        if self.ai_client.enabled:
            logger.info("✅ AI augmentation enabled - migration decisions will be enhanced")
        else:
            logger.info("⚠️ AI disabled - using deterministic fallbacks")
        
        # Initialize API clients with environment variables
        self.ps_client = ProcessStreetClient(
            api_key=os.environ.get('PROCESS_STREET_API_KEY') or self.config['source']['api_key'],
            base_url=self.config['source'].get('base_url', 'https://public-api.process.st/api/v1.1'),
            organization_id=os.environ.get('PS_ORGANIZATION_ID') or self.config['source'].get('organization_id')
        )
        
        self.tallyfy_client = TallyfyClient(
            api_url=self.config['target']['api_url'],
            client_id=self.config['target']['client_id'],
            client_secret=self.config['target']['client_secret'],
            organization_id=self.config['target']['organization_id'],
            organization_slug=self.config['target']['organization_slug']
        )
        
        # Initialize ID mapper
        mapping_db_path = self.config['storage']['mapping_database']['path']
        self.id_mapper = IDMapper(mapping_db_path)
        
        # Initialize transformers
        self.user_transformer = UserTransformer(self.id_mapper)
        self.template_transformer = TemplateTransformer(self.id_mapper)
        self.form_transformer = FormTransformer(self.id_mapper)
        
        # Initialize progress tracker
        self.progress = ProgressTracker()
        
        # Initialize validator
        self.validator = MigrationValidator(self.ps_client, self.tallyfy_client, self.id_mapper)
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"migration_{timestamp}"
    
    def run(self, phases: Optional[List[str]] = None, dry_run: bool = False, resume: bool = False, workflow_id: Optional[str] = None):
        """
        Run the migration
        
        Args:
            phases: Specific phases to run (None for all)
            dry_run: If True, simulate without making changes
            resume: If True, resume from last checkpoint
        """
        logger.info("=" * 80)
        logger.info(f"Starting Process Street to Tallyfy Migration")
        logger.info(f"Migration ID: {self.migration_id}")
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Resume: {resume}")
        if workflow_id:
            logger.info(f"Specific Workflow: {workflow_id}")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("DRY RUN MODE - No data will be migrated")
        
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
                    results[phase] = self._phase_discovery(dry_run)
                elif phase == 'users':
                    results[phase] = self._phase_users(dry_run)
                elif phase == 'groups':
                    results[phase] = self._phase_groups(dry_run)
                elif phase == 'templates':
                    results[phase] = self._phase_templates(dry_run)
                elif phase == 'instances':
                    results[phase] = self._phase_instances(dry_run)
                elif phase == 'comments':
                    results[phase] = self._phase_comments(dry_run)
                elif phase == 'files':
                    results[phase] = self._phase_files(dry_run)
                elif phase == 'webhooks':
                    results[phase] = self._phase_webhooks(dry_run)
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
    
    def _phase_discovery(self, dry_run: bool) -> Dict[str, Any]:
        """Discovery phase - analyze source data"""
        logger.info("Discovering Process Street data...")
        
        # Run comprehensive discovery with the enhanced client
        discovery = self.ps_client.discover_all_data()
        
        # Save discovery results
        discovery_file = self.checkpoint_path / 'discovery.json'
        with open(discovery_file, 'w') as f:
            json.dump(discovery, f, indent=2)
        
        logger.info(f"Discovery saved to: {discovery_file}")
        
        # Log summary
        logger.info("\nDiscovery Summary:")
        for obj_type, count in discovery['counts'].items():
            logger.info(f"  - {obj_type}: {count}")
        
        logger.info(f"\nTotal objects to migrate: {discovery['totals']['total_objects']}")
        
        # Estimate migration time
        estimated_time = self._estimate_migration_time(discovery['counts'])
        logger.info(f"Estimated migration time: {estimated_time}")
        
        return discovery
    
    def _phase_users(self, dry_run: bool) -> Dict[str, Any]:
        """Users migration phase"""
        logger.info("Migrating users...")
        
        # Fetch all users from Process Street
        ps_users = self.ps_client.list_users()
        logger.info(f"Found {len(ps_users)} users to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping user creation")
            return {'total': len(ps_users), 'migrated': 0, 'dry_run': True}
        
        # Transform and migrate users
        successful = 0
        failed = 0
        
        for ps_user in self.progress.track(ps_users, description="Migrating users"):
            try:
                # Transform user
                tallyfy_user = self.user_transformer.transform(ps_user)
                
                # Check if user exists
                existing = self.tallyfy_client.find_user_by_email(tallyfy_user["text"])
                
                if existing:
                    logger.debug(f"User already exists: {tallyfy_user["text"]}")
                    # Update ID mapping
                    self.id_mapper.add_mapping(ps_user['id'], existing['id'], 'user')
                    successful += 1
                else:
                    # Create user in Tallyfy
                    created = self.tallyfy_client.create_user(tallyfy_user)
                    logger.debug(f"Created user: {tallyfy_user["text"]}")
                    successful += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate user {ps_user.get("text", 'unknown')}: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Users migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(ps_users),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_groups(self, dry_run: bool) -> Dict[str, Any]:
        """Groups migration phase"""
        logger.info("Migrating groups...")
        
        # Fetch all groups from Process Street
        ps_groups = self.ps_client.list_groups()
        logger.info(f"Found {len(ps_groups)} groups to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping group creation")
            return {'total': len(ps_groups), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        
        for ps_group in self.progress.track(ps_groups, description="Migrating groups"):
            try:
                # Create group in Tallyfy
                tallyfy_group = {
                    'name': ps_group.get('name', 'Unnamed Group'),
                    'description': ps_group.get('description', ''),
                    'external_ref': ps_group.get('id')
                }
                
                created = self.tallyfy_client.create_group(tallyfy_group)
                
                # Map group ID
                self.id_mapper.add_mapping(ps_group['id'], created['id'], 'group')
                
                # Add members to group
                members = ps_group.get('members', [])
                for member in members:
                    member_id = member if isinstance(member, str) else member.get('id')
                    tallyfy_user_id = self.id_mapper.get_tallyfy_id(member_id, 'user')
                    
                    if tallyfy_user_id:
                        self.tallyfy_client.add_user_to_group(created['id'], tallyfy_user_id)
                
                successful += 1
                logger.debug(f"Created group: {tallyfy_group['name']}")
                
            except Exception as e:
                logger.error(f"Failed to migrate group {ps_group.get('name', 'unknown')}: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Groups migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(ps_groups),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_templates(self, dry_run: bool) -> Dict[str, Any]:
        """Templates migration phase"""
        logger.info("Migrating workflows to checklists...")
        
        # Fetch all workflows from Process Street (using updated API)
        ps_workflows = self.ps_client.list_workflows(active_only=True)
        logger.info(f"Found {len(ps_workflows)} workflows to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping template creation")
            return {'total': len(ps_workflows), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        
        for ps_workflow in self.progress.track(ps_workflows, description="Migrating templates"):
            try:
                # Get full workflow details with tasks and form fields
                workflow_id = ps_workflow.get('id')
                full_workflow = self.ps_client.get_workflow(workflow_id)
                
                # Transform workflow to checklist
                tallyfy_checklist = self.template_transformer.transform(full_workflow)
                
                # Extract steps for separate creation
                steps = tallyfy_checklist.pop('steps', [])
                field = tallyfy_checklist.pop('field', [])
                
                # Create checklist in Tallyfy
                created_checklist = self.tallyfy_client.create_checklist(tallyfy_checklist)
                checklist_id = created_checklist['id']
                
                # Create steps
                for step in steps:
                    step_captures = step.pop('field', [])
                    created_step = self.tallyfy_client.create_step(checklist_id, step)
                    
                    # Create field for step
                    for field in step_captures:
                        self.tallyfy_client.create_capture('step', created_step['id'], field)
                
                # Create template-level field
                for field in field:
                    self.tallyfy_client.create_capture('multiselect', checklist_id, field)
                
                successful += 1
                logger.debug(f"Created template: {tallyfy_checklist.get('title', 'Untitled')}")
                
            except Exception as e:
                logger.error(f"Failed to migrate workflow {ps_workflow.get('name', 'unknown')}: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Templates migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(ps_workflows),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_instances(self, dry_run: bool) -> Dict[str, Any]:
        """Instances migration phase"""
        logger.info("Migrating checklists (workflow runs)...")
        
        # Fetch all checklists from Process Street (using correct API terminology)
        ps_runs = self.ps_client.list_checklists(status='active')
        logger.info(f"Found {len(ps_runs)} workflow runs to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping instance creation")
            return {'total': len(ps_runs), 'migrated': 0, 'dry_run': True}
        
        # Filter based on configuration
        config = self.config['migration']['phase_config']['instances']
        if not config.get('include_completed', True):
            ps_runs = [r for r in ps_runs if r.get('status') != 'completed']
        if not config.get('include_active', True):
            ps_runs = [r for r in ps_runs if r.get('status') != 'active']
        
        successful = 0
        failed = 0
        
        for ps_run in self.progress.track(ps_runs, description="Migrating instances"):
            try:
                # Get mapped checklist ID (handle different response formats)
                workflow_id = ps_run.get('attributes', {}).get('workflowId') or ps_run.get('workflowId')
                checklist_id = self.id_mapper.get_tallyfy_id(workflow_id, 'multiselect')
                
                if not checklist_id:
                    logger.warning(f"Checklist not found for workflow {workflow_id}, skipping run")
                    continue
                
                # Create process in Tallyfy
                process_data = {
                    'checklist_id': checklist_id,
                    'title': ps_run.get('name', 'Process Instance'),
                    'status': self._map_run_status(ps_run.get('status')),
                    'created_at': self.user_transformer.convert_datetime(ps_run.get('created_at')),
                    'external_ref': ps_run.get('id')
                }
                
                created_process = self.tallyfy_client.create_process(process_data)
                run_id = created_process['id']
                
                # Map process ID
                self.id_mapper.add_mapping(ps_run['id'], run_id, 'process')
                
                # Update step instances with completion status
                if config.get('preserve_progress', True):
                    self._migrate_step_progress(ps_run, run_id)
                
                # Migrate form values
                self._migrate_form_values(ps_run, run_id)
                
                successful += 1
                logger.debug(f"Created process: {process_data['title']}")
                
            except Exception as e:
                logger.error(f"Failed to migrate run {ps_run.get('id', 'unknown')}: {e}")
                failed += 1
                if not self.config['migration']['options'].get('continue_on_error', False):
                    raise
        
        logger.info(f"Instances migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(ps_runs),
            'successful': successful,
            'failed': failed
        }
    
    def _phase_comments(self, dry_run: bool) -> Dict[str, Any]:
        """Comments migration phase"""
        logger.info("Migrating comments...")
        
        if dry_run:
            logger.info("DRY RUN - Skipping comment creation")
            return {'total': 0, 'migrated': 0, 'dry_run': True}
        
        # Implementation for comments migration
        # This would iterate through all entities and migrate their comments
        
        return {'total': 0, 'successful': 0, 'failed': 0}
    
    def _phase_files(self, dry_run: bool) -> Dict[str, Any]:
        """Files migration phase"""
        logger.info("Migrating files...")
        
        if dry_run:
            logger.info("DRY RUN - Skipping file upload")
            return {'total': 0, 'migrated': 0, 'dry_run': True}
        
        # Implementation for file_upload migration
        # This would download files from Process Street and upload to Tallyfy
        
        return {'total': 0, 'successful': 0, 'failed': 0}
    
    def _phase_webhooks(self, dry_run: bool) -> Dict[str, Any]:
        """Webhooks migration phase"""
        logger.info("Migrating webhooks...")
        
        ps_webhooks = self.ps_client.list_webhooks()
        logger.info(f"Found {len(ps_webhooks)} webhooks to migrate")
        
        if dry_run:
            logger.info("DRY RUN - Skipping webhook creation")
            return {'total': len(ps_webhooks), 'migrated': 0, 'dry_run': True}
        
        successful = 0
        failed = 0
        
        for ps_webhook in ps_webhooks:
            try:
                webhook_data = {
                    "text": ps_webhook.get("text"),
                    'events': ps_webhook.get('events', ['all']),
                    'is_active': ps_webhook.get('active', True),
                    'external_ref': ps_webhook.get('id')
                }
                
                self.tallyfy_client.create_webhook(webhook_data)
                successful += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate webhook: {e}")
                failed += 1
        
        logger.info(f"Webhooks migrated: {successful} successful, {failed} failed")
        
        return {
            'total': len(ps_webhooks),
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
        
        return validation_results
    
    def _map_run_status(self, ps_status: str) -> str:
        """Map Process Street run status to Tallyfy process status"""
        status_map = {
            'active': 'active',
            'in_progress': 'active',
            'completed': 'completed',
            'cancelled': 'cancelled',
            'archived': 'archived'
        }
        return status_map.get(ps_status, 'active')
    
    def _migrate_step_progress(self, ps_run: Dict, run_id: str):
        """Migrate step completion progress"""
        tasks = ps_run.get('tasks', [])
        
        for task in tasks:
            if task.get('completed'):
                step_id = self.id_mapper.get_tallyfy_id(task.get('taskId'), 'step')
                if step_id:
                    completed_by = self.id_mapper.get_tallyfy_id(
                        task.get('completedBy'), 'user'
                    ) or 'system'
                    
                    self.tallyfy_client.complete_step(run_id, step_id, completed_by)
    
    def _migrate_form_values(self, ps_run: Dict, run_id: str):
        """Migrate form field values"""
        form_values = ps_run.get('formValues', {})
        
        for field_id, value in form_values.items():
            capture_id = self.id_mapper.get_tallyfy_id(field_id, "field")
            if capture_id:
                self.tallyfy_client.set_capture_value(run_id, capture_id, value)
    
    def _estimate_migration_time(self, counts: Dict[str, int]) -> str:
        """Estimate total migration time based on object counts"""
        # Rough estimates per object type (seconds)
        time_per_object = {
            'users': 2,
            'groups': 3,
            'workflows': 10,
            'workflow_runs': 5,
            'comments': 1,
            'files': 5,
            'webhooks': 2
        }
        
        total_seconds = sum(
            counts.get(obj_type, 0) * time_estimate
            for obj_type, time_estimate in time_per_object.items()
        )
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours} hours {minutes} minutes"
        else:
            return f"{minutes} minutes"
    
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
    
    def _generate_migration_plan(self, discovery: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed migration plan based on discovery"""
        plan = {
            'estimated_duration': self._estimate_migration_time(discovery['counts']),
            'phases': [],
            'recommendations': [],
            'warnings': []
        }
        
        # Plan phases based on discovery
        if discovery['counts'].get('users', 0) > 0:
            plan['phases'].append({
                'name': 'users',
                'items': discovery['counts']['users'],
                'estimated_time': f"{discovery['counts']['users'] * 2} seconds"
            })
        
        if discovery['counts'].get('workflows', 0) > 0:
            plan['phases'].append({
                'name': 'workflows',
                'items': discovery['counts']['workflows'],
                'estimated_time': f"{discovery['counts']['workflows'] * 10} seconds"
            })
        
        if discovery['counts'].get('checklists', 0) > 0:
            plan['phases'].append({
                'name': 'active_processes',
                'items': discovery['counts']['checklists'],
                'estimated_time': f"{discovery['counts']['checklists'] * 5} seconds"
            })
        
        # Add recommendations
        if discovery['counts'].get('checklists', 0) > 50:
            plan['recommendations'].append("Consider migrating in batches due to high number of active processes")
        
        if discovery['counts'].get('completed_checklists', 0) > 100:
            plan['recommendations'].append("Consider archiving completed processes before migration")
        
        return plan
    
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
                'ps_api_calls': self.ps_client.get_statistics(),
                'tallyfy_api_calls': self.tallyfy_client.get_import_statistics(),
                'transformations': {
                    'users': self.user_transformer.get_statistics(),
                    'templates': self.template_transformer.get_statistics(),
                    'forms': self.form_transformer.get_statistics()
                }
            }
        }
        
        # Save report
        report_file = self.checkpoint_path / 'migration_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nMigration report saved: {report_file}")
        
        # Generate HTML report if configured
        if 'html' in self.config['monitoring']['reports']['formats']:
            self._generate_html_report(report)
    
    def _generate_html_report(self, report: Dict[str, Any]):
        """Generate HTML report"""
        # Implementation for HTML report generation
        pass
    
    def run_readiness_check(self) -> Dict[str, Any]:
        """Run comprehensive readiness check before migration"""
        logger.info("Running readiness check...")
        
        readiness = self.ps_client.validate_migration_readiness()
        
        # Additional checks
        try:
            # Check Tallyfy connectivity
            self.tallyfy_client._authenticate()
            readiness['checks'].append({
                'name': 'Tallyfy API Access',
                'status': 'passed',
                'details': 'Successfully authenticated with Tallyfy'
            })
        except Exception as e:
            readiness['ready'] = False
            readiness['blockers'].append(f"Tallyfy API access failed: {e}")
            readiness['checks'].append({
                'name': 'Tallyfy API Access',
                'status': 'failed',
                'details': str(e)
            })
        
        # Print readiness report
        logger.info("\n" + "=" * 60)
        logger.info("READINESS CHECK REPORT")
        logger.info("=" * 60)
        
        for check in readiness['checks']:
            status_symbol = "✓" if check['status'] == 'passed' else "✗" if check['status'] == 'failed' else "⚠"
            logger.info(f"{status_symbol} {check['name']}: {check['details']}")
        
        if readiness['warnings']:
            logger.warning("\nWarnings:")
            for warning in readiness['warnings']:
                logger.warning(f"  - {warning}")
        
        if readiness['blockers']:
            logger.error("\nBlockers:")
            for blocker in readiness['blockers']:
                logger.error(f"  - {blocker}")
        
        logger.info("\n" + "=" * 60)
        logger.info(f"Overall Status: {'READY' if readiness['ready'] else 'NOT READY'}")
        logger.info("=" * 60)
        
        return readiness


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Process Street to Tallyfy Migration Tool'
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
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only run validation phase'
    )
    
    parser.add_argument(
        '--workflow-id',
        help='Migrate specific workflow only'
    )
    
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate migration report without migrating'
    )
    
    parser.add_argument(
        '--readiness-check',
        action='store_true',
        help='Check migration readiness only'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = MigrationOrchestrator(args.config)
        
        # Run readiness check if requested
        if args.readiness_check:
            readiness = orchestrator.run_readiness_check()
            sys.exit(0 if readiness['ready'] else 1)
        
        # Generate report only if requested
        if args.report_only:
            discovery = orchestrator._phase_discovery(dry_run=True)
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'discovery': discovery,
                'migration_plan': orchestrator._generate_migration_plan(discovery)
            }
            report_file = orchestrator.checkpoint_path / 'migration_analysis.json'
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to: {report_file}")
            sys.exit(0)
        
        # Determine phases
        if args.validate_only:
            phases = ['validation']
        else:
            phases = args.phase
        
        # Run migration
        orchestrator.run(
            phases=phases,
            dry_run=args.dry_run,
            resume=args.resume,
            workflow_id=args.workflow_id
        )
        
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()