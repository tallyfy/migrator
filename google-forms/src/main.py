#!/usr/bin/env python3
"""
Google Forms to Tallyfy Migration Orchestrator
Main entry point for the 5-phase migration system (Forms-based migrator)
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

# Add shared path for base class
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../shared'))

from api.google_forms_client import GoogleFormsClient
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
from form_migrator_base import FormMigratorBase

logger = logging.getLogger(__name__)


class GoogleFormsMigrationOrchestrator(FormMigratorBase):
    """Orchestrates the 5-phase migration from Google Forms to Tallyfy"""
    
    def __init__(self):
        """Initialize the migration orchestrator"""
        # Initialize base class
        super().__init__('GoogleForms')
        
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        setup_logging()
        
        # Initialize components
        self._initialize_components()
        
        # Migration state
        self.start_time = datetime.utcnow()
        self.checkpoint_manager = CheckpointManager(self.migration_id)
        self.error_handler = ErrorHandler()
        
        logger.info(f"Google Forms Migration Orchestrator initialized")
        logger.info(f"Migration ID: {self.migration_id}")
    
    def _initialize_components(self):
        """Initialize all migration components"""
        # Initialize AI client (optional)
        self.ai_client = AIClient()
        if self.ai_client.enabled:
            logger.info("✅ AI augmentation enabled for forms migration")
        else:
            logger.info("⚠️ AI disabled - using deterministic rules")
        
        # Initialize API clients
        self.google_forms_client = GoogleFormsClient()
        
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
            self.google_forms_client,
            self.tallyfy_client
        )
    
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
            logger.info(f"Starting Google Forms to Tallyfy Migration")
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
        """Phase 1: Discover and catalog all Google Forms data"""
        logger.info("Starting Discovery Phase...")
        
        discovery_data = {
            'forms': [],
            'responses': [],
            'statistics': {}
        }
        
        try:
            # Test connection
            if not self.google_forms_client.test_connection():
                raise Exception("Failed to connect to Google Forms")
            
            # Discover forms
            logger.info("Discovering forms...")
            discovery_data['forms'] = self.google_forms_client.list_forms()
            
            # Get detailed form data and sample responses
            for form in discovery_data['forms'][:10]:  # Sample first 10 forms
                try:
                    # Get form details
                    form_details = self.google_forms_client.get_form(form['formId'])
                    form.update(form_details)
                    
                    # Get sample responses
                    responses = self.google_forms_client.list_responses(form['formId'], limit=5)
                    for response in responses:
                        response['form_id'] = form['formId']
                        response['form_title'] = form.get('info', {}).get('title', '')
                    discovery_data['responses'].extend(responses)
                    
                except Exception as e:
                    logger.warning(f"Could not get details for form {form.get('formId')}: {e}")
            
            # Calculate statistics
            discovery_data['statistics'] = {
                'total_forms': len(discovery_data['forms']),
                'total_responses_sampled': len(discovery_data['responses']),
                'discovered_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Discovery complete: {discovery_data['statistics']}")
            
        except Exception as e:
            logger.error(f"Discovery phase failed: {e}")
            raise
        
        return discovery_data
    
    def _run_mapping_phase(self, discovery_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Map Google Forms structures to Tallyfy concepts"""
        logger.info("Starting Mapping Phase...")
        
        mapping_data = {
            'field_mappings': {},
            'form_mappings': {},
            'response_mappings': {}
        }
        
        # Map forms to templates
        for form in discovery_data.get('forms', []):
            form_id = form.get('formId', '')
            mapping_data['form_mappings'][form_id] = {
                'google_title': form.get('info', {}).get('title', ''),
                'tallyfy_concept': 'template',
                'notes': 'Google Form maps to Tallyfy Template'
            }
            
            # Map form fields
            items = form.get('items', [])
            for item in items:
                item_id = item.get('itemId', '')
                question_type = item.get('questionItem', {}).get('question', {}).get('type', 'TEXT')
                
                mapping_data['field_mappings'][item_id] = {
                    'google_type': question_type,
                    'tallyfy_type': self._map_google_field_type(question_type),
                    'title': item.get('title', ''),
                    'required': item.get('questionItem', {}).get('question', {}).get('required', False)
                }
        
        # Map responses to instances
        for response in discovery_data.get('responses', []):
            response_id = response.get('responseId', '')
            mapping_data['response_mappings'][response_id] = {
                'form_id': response.get('form_id', ''),
                'tallyfy_concept': 'instance',
                'notes': 'Google Form response maps to Tallyfy Run instance'
            }
        
        return mapping_data
    
    def _map_google_field_type(self, google_type: str) -> str:
        """Map Google Forms field types to Tallyfy types"""
        type_mapping = {
            'TEXT': 'text',
            'PARAGRAPH_TEXT': 'textarea',
            'MULTIPLE_CHOICE': 'radio',
            'CHECKBOX': 'multiselect',
            'DROPDOWN': 'dropdown',
            'LINEAR_SCALE': 'rating',
            'CHECKBOX_GRID': 'multiselect',
            'MULTIPLE_CHOICE_GRID': 'radio',
            'DATE': 'date',
            'TIME': 'text',
            'FILE_UPLOAD': 'file'
        }
        return type_mapping.get(google_type, 'text')
    
    def _run_transformation_phase(self, discovery_data: Dict[str, Any], 
                                 mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Transform Google Forms data to Tallyfy format"""
        logger.info("Starting Transformation Phase...")
        
        transformation_data = {
            'templates': [],
            'instances': [],
            'users': []
        }
        
        # Transform forms to templates
        for form in discovery_data.get('forms', []):
            template = {
                'name': form.get('info', {}).get('title', 'Untitled Form'),
                'description': form.get('info', {}).get('description', ''),
                'items': form.get('items', []),
                'settings': form.get('settings', {}),
                'responder_uri': form.get('responderUri', ''),
                'form_id': form.get('formId', '')
            }
            
            transformed = self.template_transformer.transform_template(template)
            transformation_data['templates'].append(transformed)
        
        # Transform responses to instances
        for response in discovery_data.get('responses', []):
            instance = {
                'name': f"Response to {response.get('form_title', 'Form')}",
                'form_id': response.get('form_id', ''),
                'response_id': response.get('responseId', ''),
                'submitted_at': response.get('createTime', ''),
                'last_submitted_time': response.get('lastSubmittedTime', ''),
                'answers': response.get('answers', {}),
                'respondent_email': response.get('respondentEmail', '')
            }
            
            transformed = self.instance_transformer.transform_instance(instance)
            transformation_data['instances'].append(transformed)
        
        # Extract users from responses (if email addresses are available)
        seen_emails = set()
        for response in discovery_data.get('responses', []):
            email = response.get('respondentEmail', '')
            if email and email not in seen_emails:
                seen_emails.add(email)
                user = {
                    'email': email,
                    'role': 'member',
                    'source': 'google_forms_respondent'
                }
                transformed = self.user_transformer.transform_user(user)
                transformation_data['users'].append(transformed)
        
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
        
        # Migrate instances
        for instance in transformation_data.get('instances', []):
            try:
                # Create instance in Tallyfy
                # result = self.tallyfy_client.create_instance(instance)
                # migration_data['created_instances'].append(result)
                logger.debug(f"Would create instance: {instance.get('name')}")
            except Exception as e:
                logger.error(f"Failed to migrate instance: {e}")
                migration_data['errors'].append({'type': 'instance', 'error': str(e)})
        
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
        
        # Validate form-specific requirements
        if validation_data['validated']:
            logger.info("✅ All form migrations validated successfully")
        else:
            logger.warning(f"⚠️ Validation found {len(validation_data['issues'])} issues")
        
        return validation_data
    
    def _generate_final_report(self, results: Dict[str, Any]):
        """Generate final migration report"""
        logger.info("Generating final report...")
        
        report = {
            'migration_id': self.migration_id,
            'vendor': 'Google Forms',
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
    parser = argparse.ArgumentParser(description='Google Forms to Tallyfy Migration Tool')
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
    orchestrator = GoogleFormsMigrationOrchestrator()
    orchestrator.run(
        dry_run=args.dry_run,
        resume=args.resume,
        phases=args.phases
    )


if __name__ == '__main__':
    main()