#!/usr/bin/env python3
"""
Typeform to Tallyfy Migration Orchestrator
Coordinates the 5-phase migration process
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.typeform_client import TypeformClient
from src.api.tallyfy_client import TallyfyClient
from src.api.ai_client import AIClient
from src.transformers.field_transformer import FieldTransformer
from src.transformers.template_transformer import TemplateTransformer
from src.transformers.instance_transformer import InstanceTransformer
from src.transformers.user_transformer import UserTransformer
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.validator import Validator
from src.utils.error_handler import ErrorHandler
from src.utils.logger_config import setup_logger

logger = setup_logger(__name__)


class TypeformMigrator:
    """Main orchestrator for Typeform to Tallyfy migration"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize migrator with configuration"""
        self.config = config
        self.dry_run = config.get('dry_run', False)
        
        # Initialize clients
        self.typeform = TypeformClient(config['typeform_api_key'])
        self.tallyfy = TallyfyClient(
            api_key=config['tallyfy_api_key'],
            organization_id=config['tallyfy_org_id']
        )
        
        # Initialize AI client (optional)
        self.ai_client = None
        if config.get('anthropic_api_key'):
            self.ai_client = AIClient(config['anthropic_api_key'])
        
        # Initialize transformers
        self.field_transformer = FieldTransformer(self.ai_client)
        self.template_transformer = TemplateTransformer(
            self.field_transformer,
            self.ai_client
        )
        self.instance_transformer = InstanceTransformer(self.ai_client)
        self.user_transformer = UserTransformer()
        
        # Initialize utilities
        self.checkpoint = CheckpointManager(config.get('checkpoint_file', 'typeform_migration.db'))
        self.validator = Validator(self.typeform, self.tallyfy)
        self.error_handler = ErrorHandler()
        
        # Migration state
        self.migration_id = f"typeform_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.stats = {
            'start_time': datetime.now(),
            'forms_migrated': 0,
            'responses_migrated': 0,
            'users_migrated': 0,
            'errors': []
        }
        
        logger.info(f"Typeform migrator initialized - Migration ID: {self.migration_id}")
    
    def migrate(self) -> Dict[str, Any]:
        """Execute full 5-phase migration"""
        logger.info("="*50)
        logger.info("Starting Typeform to Tallyfy Migration")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info(f"AI Enhancement: {'ENABLED' if self.ai_client else 'DISABLED'}")
        logger.info("="*50)
        
        try:
            # Phase 1: Discovery
            discovery_data = self.phase1_discovery()
            
            # Phase 2: Users
            user_mapping = self.phase2_users(discovery_data)
            
            # Phase 3: Templates (Forms)
            template_mapping = self.phase3_templates(discovery_data)
            
            # Phase 4: Instances (Responses)
            instance_mapping = self.phase4_instances(discovery_data, template_mapping)
            
            # Phase 5: Validation
            validation_results = self.phase5_validation(
                user_mapping,
                template_mapping,
                instance_mapping
            )
            
            # Generate final report
            report = self.generate_report(validation_results)
            
            logger.info("="*50)
            logger.info("Migration Completed Successfully!")
            logger.info("="*50)
            
            return report
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.stats['errors'].append(str(e))
            raise
    
    def phase1_discovery(self) -> Dict[str, Any]:
        """Phase 1: Discover Typeform workspace"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 1: DISCOVERY")
        logger.info("="*50)
        
        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('discovery')
        if checkpoint_data:
            logger.info("Resuming from discovery checkpoint")
            return checkpoint_data
        
        discovery = {
            'timestamp': datetime.now().isoformat(),
            'workspaces': [],
            'forms': [],
            'total_responses': 0,
            'workspace_members': [],
            'themes': [],
            'images': [],
            'webhooks': [],
            'statistics': {}
        }
        
        try:
            # Get workspaces
            logger.info("Fetching workspaces...")
            workspaces = self.typeform.get_workspaces()
            discovery['workspaces'] = workspaces.get('items', [])
            logger.info(f"Found {len(discovery['workspaces'])} workspaces")
            
            # Get themes (for styling reference)
            logger.info("Fetching themes...")
            try:
                themes = self.typeform.get_themes()
                discovery['themes'] = themes.get('items', [])
                logger.info(f"Found {len(discovery['themes'])} themes")
            except Exception as e:
                logger.warning(f"Could not fetch themes: {e}")
            
            # Get workspace members (for first workspace)
            if discovery['workspaces']:
                workspace_id = discovery['workspaces'][0]['id']
                logger.info(f"Fetching members for workspace {workspace_id}...")
                members = self.typeform.get_workspace_members(workspace_id)
                discovery['workspace_members'] = members
                logger.info(f"Found {len(members)} workspace members")
            
            # Get all forms
            logger.info("Fetching forms...")
            forms_response = self.typeform.get_forms()
            all_forms = forms_response.get('items', [])
            
            # Get detailed info for each form
            for form_summary in all_forms:
                logger.info(f"Fetching details for form: {form_summary.get('title')}")
                
                try:
                    # Get full form details
                    form = self.typeform.get_form(form_summary['id'])
                    
                    # Get response count
                    responses = self.typeform.get_responses(form_summary['id'], page_size=1)
                    response_count = responses.get('total_items', 0)
                    
                    form['response_count'] = response_count
                    discovery['total_responses'] += response_count
                    discovery['forms'].append(form)
                    
                    logger.info(f"  - {len(form.get('fields', []))} fields, {response_count} responses")
                    
                except Exception as e:
                    logger.error(f"Failed to get details for form {form_summary['id']}: {e}")
            
            # Calculate statistics
            discovery['statistics'] = {
                'workspaces': len(discovery['workspaces']),
                'forms': len(discovery['forms']),
                'total_responses': discovery['total_responses'],
                'users': len(discovery['workspace_members']),
                'themes': len(discovery['themes']),
                'total_fields': sum(len(f.get('fields', [])) for f in discovery['forms']),
                'avg_fields_per_form': sum(len(f.get('fields', [])) for f in discovery['forms']) / max(len(discovery['forms']), 1)
            }
            
            logger.info(f"\nDiscovery Summary:")
            for key, value in discovery['statistics'].items():
                logger.info(f"  - {key}: {value}")
            
            # Save checkpoint
            self.checkpoint.save_checkpoint('discovery', discovery)
            
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            raise
        
        return discovery
    
    def phase2_users(self, discovery_data: Dict[str, Any]) -> Dict[str, str]:
        """Phase 2: Migrate users"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 2: USER MIGRATION")
        logger.info("="*50)
        
        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('users')
        if checkpoint_data:
            logger.info("Resuming from users checkpoint")
            return checkpoint_data
        
        user_mapping = {}
        
        # Transform workspace
        if discovery_data['workspaces']:
            workspace = discovery_data['workspaces'][0]
            logger.info(f"Transforming workspace: {workspace.get('name')}")
            org_config = self.user_transformer.transform_workspace(workspace)
            logger.info(f"Organization config: {org_config['name']}")
        
        # Transform members
        members = discovery_data.get('workspace_members', [])
        logger.info(f"Transforming {len(members)} workspace members...")
        
        for member in members:
            try:
                # Transform user
                user = self.user_transformer.transform(member)
                
                # Ensure required fields
                if 'email' not in user:
                    user['email'] = member.get('email') or f"user_{member.get('user_id')}@typeform.migrated"
                if 'name' not in user:
                    user['name'] = member.get('name') or user['email'].split('@')[0]
                
                logger.info(f"Processing user: {user['email']} ({user['role']})")
                
                if not self.dry_run:
                    # Create/update user in Tallyfy
                    result = self.error_handler.with_retry(
                        lambda: self.tallyfy.create_user(user)
                    )
                    
                    if result:
                        user_mapping[member.get('email', member.get('user_id'))] = result['id']
                        logger.info(f"  ✓ Created user: {user['email']}")
                else:
                    # Dry run - generate fake ID
                    user_mapping[member.get('email', member.get('user_id'))] = f"dry_run_user_{len(user_mapping)}"
                    logger.info(f"  [DRY RUN] Would create user: {user['email']}")
                
                self.stats['users_migrated'] += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate user {member.get('email')}: {e}")
                self.stats['errors'].append(f"User migration: {e}")
                continue
        
        # Also extract respondent emails as guest users
        logger.info("\nExtracting respondent users from form responses...")
        respondent_emails = set()
        
        # Sample responses to find unique respondent emails
        for form in discovery_data.get('forms', [])[:5]:  # Sample first 5 forms
            try:
                responses = self.typeform.get_responses(form['id'], page_size=50)
                for response in responses.get('items', []):
                    # Check for email fields in answers
                    for answer in response.get('answers', []):
                        if answer.get('type') == 'email':
                            respondent_emails.add(answer.get('email'))
                    # Check hidden fields
                    hidden = response.get('hidden', {})
                    if 'email' in hidden:
                        respondent_emails.add(hidden['email'])
            except Exception as e:
                logger.warning(f"Could not extract respondents from form {form['id']}: {e}")
        
        logger.info(f"Found {len(respondent_emails)} unique respondent emails")
        
        # Create guest users for respondents
        for email in respondent_emails:
            if email and email not in user_mapping:
                try:
                    guest_user = {
                        'email': email,
                        'name': email.split('@')[0],
                        'role': 'guest'
                    }
                    
                    if not self.dry_run:
                        result = self.error_handler.with_retry(
                            lambda: self.tallyfy.create_user(guest_user)
                        )
                        if result:
                            user_mapping[email] = result['id']
                            logger.info(f"  ✓ Created guest user: {email}")
                    else:
                        user_mapping[email] = f"dry_run_guest_{len(user_mapping)}"
                        logger.info(f"  [DRY RUN] Would create guest user: {email}")
                        
                except Exception as e:
                    logger.warning(f"Could not create guest user {email}: {e}")
        all_responses = []
        for form in discovery_data['forms'][:5]:  # Limit for performance
            try:
                responses = self.typeform.get_responses(form['id'], page_size=100)
                all_responses.extend(responses.get('items', []))
            except:
                pass
        
        if all_responses:
            respondent_users = self.user_transformer.extract_respondent_users(all_responses)
            logger.info(f"Found {len(respondent_users)} unique respondents")
            
            for user in respondent_users[:20]:  # Limit guest users
                if user['email'] not in user_mapping:
                    if not self.dry_run:
                        try:
                            result = self.tallyfy.create_user(user)
                            user_mapping[user['email']] = result['id']
                            logger.info(f"  ✓ Created guest: {user['email']}")
                        except:
                            pass
                    else:
                        user_mapping[user['email']] = f"dry_run_guest_{len(user_mapping)}"
        
        logger.info(f"\nUser migration complete: {len(user_mapping)} users mapped")
        
        # Save checkpoint
        self.checkpoint.save_checkpoint('users', user_mapping)
        
        return user_mapping
    
    def phase3_templates(self, discovery_data: Dict[str, Any]) -> Dict[str, str]:
        """Phase 3: Migrate forms as templates"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 3: TEMPLATE (FORM) MIGRATION")
        logger.info("="*50)
        
        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('templates')
        if checkpoint_data:
            logger.info("Resuming from templates checkpoint")
            return checkpoint_data
        
        template_mapping = {}
        forms = discovery_data.get('forms', [])
        
        logger.info(f"Migrating {len(forms)} forms as blueprints...\n")
        
        for form in forms:
            try:
                form_id = form.get('id')
                form_title = form.get('title', 'Untitled')
                field_count = len(form.get('fields', []))
                
                logger.info(f"Processing form: {form_title}")
                logger.info(f"  - ID: {form_id}")
                logger.info(f"  - Fields: {field_count}")
                logger.info(f"  - Responses: {form.get('response_count', 0)}")
                
                # Transform to blueprint
                blueprint = self.template_transformer.transform(form)
                logger.info(f"  - Complexity: {blueprint['metadata'].get('complexity', 'unknown')}")
                logger.info(f"  - Steps: {len(blueprint.get('steps', []))}")
                
                if not self.dry_run:
                    # Create blueprint in Tallyfy
                    result = self.error_handler.with_retry(
                        lambda: self.tallyfy.create_checklist(blueprint)
                    )
                    
                    if result:
                        template_mapping[form_id] = result['id']
                        logger.info(f"  ✓ Created blueprint: {result['id']}")
                else:
                    # Dry run - generate fake ID
                    template_mapping[form_id] = f"dry_run_template_{len(template_mapping)}"
                    logger.info(f"  [DRY RUN] Would create blueprint")
                
                self.stats['forms_migrated'] += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate form {form.get('title')}: {e}")
                self.stats['errors'].append(f"Form migration: {e}")
            
            # Add delay to avoid rate limits
            time.sleep(1)
        
        logger.info(f"\nTemplate migration complete: {len(template_mapping)} forms migrated")
        
        # Save checkpoint
        self.checkpoint.save_checkpoint('templates', template_mapping)
        
        return template_mapping
    
    def phase4_instances(self, discovery_data: Dict[str, Any], 
                        template_mapping: Dict[str, str]) -> Dict[str, str]:
        """Phase 4: Migrate form responses as instances"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 4: INSTANCE (RESPONSE) MIGRATION")
        logger.info("="*50)
        
        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('instances')
        if checkpoint_data:
            logger.info("Resuming from instances checkpoint")
            return checkpoint_data
        
        instance_mapping = {}
        forms = discovery_data.get('forms', [])
        
        # Limit responses per form for performance
        max_responses_per_form = self.config.get('max_responses_per_form', 50)
        
        logger.info(f"Migrating responses (max {max_responses_per_form} per form)...\n")
        
        for form in forms:
            form_id = form.get('id')
            form_title = form.get('title', 'Untitled')
            
            # Skip if no blueprint mapping
            if form_id not in template_mapping:
                logger.warning(f"Skipping responses for unmapped form: {form_title}")
                continue
            
            blueprint_id = template_mapping[form_id]
            
            try:
                # Get responses
                logger.info(f"Fetching responses for: {form_title}")
                responses = self.typeform.get_responses(form_id, page_size=max_responses_per_form)
                response_items = responses.get('items', [])
                
                if not response_items:
                    logger.info(f"  - No responses to migrate")
                    continue
                
                logger.info(f"  - Found {len(response_items)} responses")
                
                # Transform responses
                processes = self.instance_transformer.transform_batch(
                    response_items,
                    blueprint_id,
                    form
                )
                
                # Create processes in Tallyfy
                for idx, process in enumerate(processes):
                    response_id = response_items[idx].get('response_id', f"response_{idx}")
                    
                    if not self.dry_run:
                        try:
                            result = self.error_handler.with_retry(
                                lambda: self.tallyfy.create_run(process)
                            )
                            
                            if result:
                                instance_mapping[response_id] = result['id']
                                logger.info(f"    ✓ Created process for response {response_id[:8]}")
                        except Exception as e:
                            logger.error(f"    ✗ Failed to create process: {e}")
                    else:
                        instance_mapping[response_id] = f"dry_run_instance_{len(instance_mapping)}"
                        logger.info(f"    [DRY RUN] Would create process for response {response_id[:8]}")
                    
                    self.stats['responses_migrated'] += 1
                    
                    # Add delay to avoid rate limits
                    if idx % 10 == 0:
                        time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to migrate responses for {form_title}: {e}")
                self.stats['errors'].append(f"Response migration: {e}")
        
        logger.info(f"\nInstance migration complete: {len(instance_mapping)} responses migrated")
        
        # Save checkpoint
        self.checkpoint.save_checkpoint('instances', instance_mapping)
        
        return instance_mapping
    
    def phase5_validation(self, user_mapping: Dict[str, str],
                         template_mapping: Dict[str, str],
                         instance_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Phase 5: Validate migration"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 5: VALIDATION")
        logger.info("="*50)
        
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'users': {'expected': len(user_mapping), 'validated': 0},
            'templates': {'expected': len(template_mapping), 'validated': 0},
            'instances': {'expected': len(instance_mapping), 'validated': 0},
            'issues': []
        }
        
        if self.dry_run:
            logger.info("[DRY RUN] Skipping validation")
            return validation_results
        
        # Validate users
        logger.info("Validating users...")
        for email, tallyfy_id in list(user_mapping.items())[:10]:  # Sample validation
            if self.validator.validate_user(tallyfy_id):
                validation_results['users']['validated'] += 1
            else:
                validation_results['issues'].append(f"User validation failed: {email}")
        
        # Validate templates
        logger.info("Validating templates...")
        for form_id, blueprint_id in template_mapping.items():
            if self.validator.validate_template(blueprint_id):
                validation_results['templates']['validated'] += 1
            else:
                validation_results['issues'].append(f"Template validation failed: {form_id}")
        
        # Validate instances
        logger.info("Validating instances...")
        for response_id, process_id in list(instance_mapping.items())[:10]:  # Sample
            if self.validator.validate_instance(process_id):
                validation_results['instances']['validated'] += 1
            else:
                validation_results['issues'].append(f"Instance validation failed: {response_id}")
        
        # Summary
        logger.info(f"\nValidation Summary:")
        logger.info(f"  - Users: {validation_results['users']['validated']}/{validation_results['users']['expected']}")
        logger.info(f"  - Templates: {validation_results['templates']['validated']}/{validation_results['templates']['expected']}")
        logger.info(f"  - Instances: {validation_results['instances']['validated']}/{validation_results['instances']['expected']}")
        
        if validation_results['issues']:
            logger.warning(f"  - Issues found: {len(validation_results['issues'])}")
            for issue in validation_results['issues'][:5]:
                logger.warning(f"    • {issue}")
        
        return validation_results
    
    def generate_report(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final migration report"""
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        report = {
            'migration_id': self.migration_id,
            'status': 'completed' if not self.stats['errors'] else 'completed_with_errors',
            'mode': 'dry_run' if self.dry_run else 'live',
            'duration_seconds': duration,
            'statistics': {
                'forms_migrated': self.stats['forms_migrated'],
                'responses_migrated': self.stats['responses_migrated'],
                'users_migrated': self.stats['users_migrated']
            },
            'validation': validation_results,
            'errors': self.stats['errors'],
            'ai_enhanced': bool(self.ai_client)
        }
        
        # Save report
        report_file = f"typeform_migration_report_{self.migration_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nReport saved to: {report_file}")
        
        return report


def main():
    """Main entry point"""
    # Load configuration from environment
    config = {
        'typeform_api_key': os.getenv('TYPEFORM_API_KEY'),
        'tallyfy_api_key': os.getenv('TALLYFY_API_KEY'),
        'tallyfy_org_id': os.getenv('TALLYFY_ORG_ID'),
        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
        'dry_run': os.getenv('DRY_RUN', 'false').lower() == 'true',
        'max_responses_per_form': int(os.getenv('MAX_RESPONSES_PER_FORM', '50'))
    }
    
    # Validate required configuration
    if not config['typeform_api_key']:
        logger.error("TYPEFORM_API_KEY environment variable is required")
        sys.exit(1)
    
    if not config['tallyfy_api_key']:
        logger.error("TALLYFY_API_KEY environment variable is required")
        sys.exit(1)
    
    if not config['tallyfy_org_id']:
        logger.error("TALLYFY_ORG_ID environment variable is required")
        sys.exit(1)
    
    # Create and run migrator
    migrator = TypeformMigrator(config)
    
    try:
        report = migrator.migrate()
        
        # Print summary
        print("\n" + "="*50)
        print("MIGRATION SUMMARY")
        print("="*50)
        print(f"Status: {report['status']}")
        print(f"Duration: {report['duration_seconds']:.2f} seconds")
        print(f"Forms Migrated: {report['statistics']['forms_migrated']}")
        print(f"Responses Migrated: {report['statistics']['responses_migrated']}")
        print(f"Users Migrated: {report['statistics']['users_migrated']}")
        print(f"Errors: {len(report['errors'])}")
        
        sys.exit(0 if report['status'] == 'completed' else 1)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()