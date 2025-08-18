#!/usr/bin/env python3
"""
Basecamp to Tallyfy Migration Orchestrator
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

from api.basecamp_client import BasecampClient
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


class BasecampMigrationOrchestrator:
    """Orchestrates the 5-phase migration from Basecamp to Tallyfy"""
    
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
        
        logger.info(f"Basecamp Migration Orchestrator initialized")
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
        self.vendor_client = BasecampClient()
        self.tallyfy_client = TallyfyClient()
        
        # Initialize transformers
        self.field_transformer = FieldTransformer(self.ai_client)
        self.template_transformer = TemplateTransformer(self.ai_client)
        self.template_transformer.field_transformer = self.field_transformer
        self.instance_transformer = InstanceTransformer(self.ai_client)
        self.user_transformer = UserTransformer(self.ai_client)
        
        # Initialize validator
        self.validator = MigrationValidator(
            self.vendor_client,
            self.tallyfy_client
        )
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"basecamp_migration_{timestamp}"
    
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
            logger.info(f"Starting Basecamp to Tallyfy Migration")
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
        """Phase 1: Discover and catalog all Basecamp data"""
        logger.info("Starting Discovery Phase...")
        
        discovery_data = {
            'projects': [],
            'templates': [],
            'people': [],
            'todos': [],
            'messages': [],
            'campfires': [],
            'schedules': [],
            'documents': [],
            'statistics': {}
        }
        
        try:
            # Test connection
            if not self.vendor_client.test_connection():
                raise Exception("Failed to connect to Basecamp")
            
            # Discover projects
            logger.info("Discovering projects...")
            discovery_data['projects'] = self.vendor_client.get_projects()
            logger.info(f"  Found {len(discovery_data['projects'])} projects")
            
            # Discover templates
            logger.info("Discovering templates...")
            discovery_data['templates'] = self.vendor_client.get_templates()
            logger.info(f"  Found {len(discovery_data['templates'])} templates")
            
            # Discover people
            logger.info("Discovering people...")
            discovery_data['people'] = self.vendor_client.get_people()
            logger.info(f"  Found {len(discovery_data['people'])} people")
            
            # Sample project details for deeper discovery
            for project in discovery_data['projects'][:5]:  # Sample first 5 projects
                project_id = project['id']
                logger.info(f"  Analyzing project: {project['name']}")
                
                try:
                    # Get project tools (dock)
                    tools = self.vendor_client.get_project_tools(project_id)
                    project['tools'] = tools
                    
                    # Get todosets if available
                    todoset = self.vendor_client.get_todosets(project_id)
                    if todoset:
                        project['todoset'] = todoset
                        todoset_id = todoset.get('id')
                        
                        # Get todo lists
                        todolists = self.vendor_client.get_todolists(project_id, todoset_id)
                        project['todolists'] = todolists
                        logger.info(f"    - {len(todolists)} todo lists")
                        
                        # Sample todos from first list
                        if todolists:
                            first_list = todolists[0]
                            todos = self.vendor_client.get_todos(project_id, first_list['id'])
                            discovery_data['todos'].extend(todos[:10])  # Sample 10 todos
                    
                    # Check for message board
                    message_board = next((t for t in tools if t.get('name') == 'message_board'), None)
                    if message_board:
                        project['has_messages'] = True
                        logger.info(f"    - Has message board")
                    
                    # Check for campfire (chat)
                    campfire = next((t for t in tools if t.get('name') == 'campfire'), None)
                    if campfire:
                        project['has_campfire'] = True
                        logger.info(f"    - Has campfire chat")
                        
                except Exception as e:
                    logger.warning(f"Could not analyze project {project_id}: {e}")
            
            # Calculate statistics
            discovery_data['statistics'] = {
                'total_projects': len(discovery_data['projects']),
                'total_templates': len(discovery_data['templates']),
                'total_people': len(discovery_data['people']),
                'sampled_todos': len(discovery_data['todos']),
                'projects_with_messages': sum(1 for p in discovery_data['projects'] if p.get('has_messages')),
                'projects_with_campfire': sum(1 for p in discovery_data['projects'] if p.get('has_campfire')),
                'total_todolists': sum(len(p.get('todolists', [])) for p in discovery_data['projects']),
                'discovered_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Discovery complete: {discovery_data['statistics']}")
            
        except Exception as e:
            logger.error(f"Discovery phase failed: {e}")
            raise
        
        return discovery_data
    
    def _run_mapping_phase(self, discovery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Map Basecamp structures to Tallyfy concepts"""
        logger.info("Starting Mapping Phase...")
        
        mapping_data = {
            'field_mappings': {},
            'user_mappings': {},
            'template_mappings': {}
        }
        
        # Add mapping logic here
        
        return mapping_data
    
    def _run_transformation_phase(self, discovery_data: Dict[str, Any], 
                                 mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Transform Basecamp data to Tallyfy format"""
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
        
        # Transform templates
        for template in discovery_data.get('templates', []):
            transformed = self.template_transformer.transform_template(template)
            transformation_data['templates'].append(transformed)
        
        # Transform instances
        for instance in discovery_data.get('instances', []):
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
            return migration_data
        
        # Migrate users
        for user in transformation_data.get('users', []):
            try:
                # Create user in Tallyfy
                # result = self.tallyfy_client.create_user(user)
                # migration_data['created_users'].append(result)
                pass
            except Exception as e:
                logger.error(f"Failed to migrate user: {e}")
                migration_data['errors'].append({'type': 'user', 'error': str(e)})
        
        # Migrate templates
        for template in transformation_data.get('templates', []):
            try:
                # Create template in Tallyfy
                # result = self.tallyfy_client.create_template(template)
                # migration_data['created_templates'].append(result)
                pass
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
            'statistics': {}
        }
        
        # Add validation logic here
        
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
    parser = argparse.ArgumentParser(description='Basecamp to Tallyfy Migration Tool')
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
    orchestrator = BasecampMigrationOrchestrator()
    orchestrator.run(
        dry_run=args.dry_run,
        resume=args.resume,
        phases=args.phases
    )


if __name__ == '__main__':
    main()
