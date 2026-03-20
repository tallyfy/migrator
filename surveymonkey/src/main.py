#!/usr/bin/env python3
"""
SurveyMonkey to Tallyfy Migration Orchestrator
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

from src.api.surveymonkey_client import SurveyMonkeyClient
from src.api.tallyfy_client import TallyfyClient
from src.api.ai_client import AIClient
from src.transformers.field_transformer import FieldTransformer
from src.transformers.template_transformer import TemplateTransformer
from src.transformers.instance_transformer import InstanceTransformer
from src.transformers.user_transformer import UserTransformer
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.validator import MigrationValidator
from src.utils.error_handler import ErrorHandler
from src.utils.logger_config import setup_logger

logger = setup_logger(__name__)


class SurveyMonkeyMigrator:
    """Main orchestrator for SurveyMonkey to Tallyfy migration"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize migrator with configuration"""
        self.config = config
        self.dry_run = config.get('dry_run', False)

        # Initialize clients
        self.surveymonkey = SurveyMonkeyClient(config['surveymonkey_access_token'])
        self.tallyfy = TallyfyClient(
            api_key=config['tallyfy_api_key'],
            organization=config['tallyfy_org_id']
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
        self.checkpoint = CheckpointManager(
            config.get('migration_id', f"sm_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            config.get('checkpoint_file', 'checkpoints/surveymonkey_migration.db')
        )
        self.validator = MigrationValidator(self.surveymonkey, self.tallyfy)
        self.error_handler = ErrorHandler()

        # Migration state
        self.migration_id = f"surveymonkey_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.stats = {
            'start_time': datetime.now(),
            'surveys_migrated': 0,
            'responses_migrated': 0,
            'users_migrated': 0,
            'errors': []
        }

        logger.info(f"SurveyMonkey migrator initialized - Migration ID: {self.migration_id}")

    def migrate(self) -> Dict[str, Any]:
        """Execute full 5-phase migration"""
        logger.info("="*50)
        logger.info("Starting SurveyMonkey to Tallyfy Migration")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info(f"AI Enhancement: {'ENABLED' if self.ai_client else 'DISABLED'}")
        logger.info("="*50)

        try:
            # Phase 1: Discovery
            discovery_data = self.phase1_discovery()

            # Phase 2: Users
            user_mapping = self.phase2_users(discovery_data)

            # Phase 3: Templates (Surveys)
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
        """Phase 1: Discover SurveyMonkey account"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 1: DISCOVERY")
        logger.info("="*50)

        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('discovery', 'account', 'full')
        if checkpoint_data and checkpoint_data.get('data'):
            logger.info("Resuming from discovery checkpoint")
            return checkpoint_data['data']

        discovery = {
            'timestamp': datetime.now().isoformat(),
            'account': {},
            'surveys': [],
            'total_responses': 0,
            'groups': [],
            'group_members': [],
            'statistics': {}
        }

        try:
            # Get account info
            logger.info("Fetching account info...")
            account = self.surveymonkey.get_me()
            discovery['account'] = account
            logger.info(f"Account: {account.get('username', 'N/A')} ({account.get('account_type', 'N/A')})")

            # Get groups/teams
            logger.info("Fetching groups...")
            try:
                groups_response = self.surveymonkey.get_groups()
                groups = groups_response.get('data', [])
                discovery['groups'] = groups
                logger.info(f"Found {len(groups)} groups")

                # Get members for each group
                for group in groups:
                    try:
                        members_response = self.surveymonkey.get_group_members(group['id'])
                        members = members_response.get('data', [])
                        for member in members:
                            member['group_id'] = group['id']
                        discovery['group_members'].extend(members)
                    except Exception as e:
                        logger.warning(f"Could not fetch members for group {group['id']}: {e}")
            except Exception as e:
                logger.warning(f"Could not fetch groups: {e}")

            # Get all surveys
            logger.info("Fetching surveys...")
            surveys_response = self.surveymonkey.get_surveys()
            all_surveys = surveys_response.get('data', [])

            # Get detailed info for each survey
            for survey_summary in all_surveys:
                logger.info(f"Fetching details for survey: {survey_summary.get('title')}")

                try:
                    # Get full survey details (includes pages and questions)
                    survey = self.surveymonkey.get_survey_details(survey_summary['id'])

                    # Get response count
                    responses = self.surveymonkey.get_survey_responses(survey_summary['id'], per_page=1)
                    response_count = responses.get('total', 0)

                    survey['response_count'] = response_count
                    discovery['total_responses'] += response_count

                    # Count questions
                    question_count = 0
                    for page in survey.get('pages', []):
                        question_count += len(page.get('questions', []))

                    discovery['surveys'].append(survey)

                    logger.info(f"  - {len(survey.get('pages', []))} pages, {question_count} questions, {response_count} responses")

                except Exception as e:
                    logger.error(f"Failed to get details for survey {survey_summary['id']}: {e}")

                # Rate limiting
                time.sleep(0.5)

            # Calculate statistics
            total_questions = 0
            total_pages = 0
            for survey in discovery['surveys']:
                for page in survey.get('pages', []):
                    total_pages += 1
                    total_questions += len(page.get('questions', []))

            discovery['statistics'] = {
                'surveys': len(discovery['surveys']),
                'total_responses': discovery['total_responses'],
                'total_pages': total_pages,
                'total_questions': total_questions,
                'users': len(discovery['group_members']),
                'groups': len(discovery['groups']),
                'avg_questions_per_survey': total_questions / max(len(discovery['surveys']), 1),
                'avg_pages_per_survey': total_pages / max(len(discovery['surveys']), 1)
            }

            logger.info(f"\nDiscovery Summary:")
            for key, value in discovery['statistics'].items():
                logger.info(f"  - {key}: {value}")

            # Save checkpoint
            self.checkpoint.save_checkpoint('discovery', 'account', 'full', data=discovery)

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
        checkpoint_data = self.checkpoint.get_checkpoint('users', 'mapping', 'all')
        if checkpoint_data and checkpoint_data.get('data'):
            logger.info("Resuming from users checkpoint")
            return checkpoint_data['data']

        user_mapping = {}

        # Transform account to organization
        account = discovery_data.get('account', {})
        if account:
            logger.info(f"Transforming account: {account.get('username')}")
            org_config = self.user_transformer.transform_account(account)
            logger.info(f"Organization config: {org_config['name']}")

            # Create primary user from account owner
            primary_email = account.get('email', '')
            if primary_email:
                user = {
                    'email': primary_email,
                    'first_name': account.get('first_name', 'Account'),
                    'last_name': account.get('last_name', 'Owner'),
                    'role': 'admin',
                    'status': 'active'
                }

                logger.info(f"Processing primary user: {primary_email}")

                if not self.dry_run:
                    try:
                        result = self.tallyfy.create_user(
                            user['email'], user['first_name'], user['last_name'], user['role']
                        )
                        if result:
                            user_mapping[primary_email] = result.get('id', '')
                            logger.info(f"  Created primary user: {primary_email}")
                    except Exception as e:
                        logger.error(f"Failed to create primary user: {e}")
                else:
                    user_mapping[primary_email] = f"dry_run_user_0"
                    logger.info(f"  [DRY RUN] Would create primary user: {primary_email}")

        # Transform group members
        members = discovery_data.get('group_members', [])
        logger.info(f"Transforming {len(members)} group members...")

        for member in members:
            try:
                user = self.user_transformer.transform(member)

                if 'email' not in user or not user['email']:
                    user['email'] = member.get('email', f"user_{member.get('id')}@surveymonkey.migrated")
                if 'first_name' not in user:
                    user['first_name'] = user.get('name', user['email'].split('@')[0])

                logger.info(f"Processing user: {user['email']} ({user['role']})")

                if not self.dry_run:
                    try:
                        result = self.tallyfy.create_user(
                            user['email'], user['first_name'], user.get('last_name', ''), user['role']
                        )
                        if result:
                            user_mapping[user['email']] = result.get('id', '')
                            logger.info(f"  Created user: {user['email']}")
                    except Exception as e:
                        logger.error(f"Failed to create user {user['email']}: {e}")
                else:
                    user_mapping[user['email']] = f"dry_run_user_{len(user_mapping)}"
                    logger.info(f"  [DRY RUN] Would create user: {user['email']}")

                self.stats['users_migrated'] += 1

            except Exception as e:
                logger.error(f"Failed to migrate user {member.get('email')}: {e}")
                self.stats['errors'].append(f"User migration: {e}")
                continue

        # Extract respondent emails from survey responses
        logger.info("\nExtracting respondent users from survey responses...")
        all_responses = []
        for survey in discovery_data.get('surveys', [])[:5]:  # Sample first 5 surveys
            try:
                responses = self.surveymonkey.get_survey_responses(survey['id'], per_page=50)
                all_responses.extend(responses.get('data', []))
            except Exception as e:
                logger.warning(f"Could not fetch responses from survey {survey['id']}: {e}")

        if all_responses:
            respondent_users = self.user_transformer.extract_respondent_users(all_responses)
            logger.info(f"Found {len(respondent_users)} unique respondents")

            for user in respondent_users[:20]:  # Limit guest users
                if user['email'] not in user_mapping:
                    if not self.dry_run:
                        try:
                            result = self.tallyfy.create_guest(user['email'], f"{user['first_name']} {user.get('last_name', '')}")
                            if result:
                                user_mapping[user['email']] = result.get('id', '')
                                logger.info(f"  Created guest: {user['email']}")
                        except Exception as e:
                            logger.warning(f"Could not create guest user {user['email']}: {e}")
                    else:
                        user_mapping[user['email']] = f"dry_run_guest_{len(user_mapping)}"

        logger.info(f"\nUser migration complete: {len(user_mapping)} users mapped")

        # Save checkpoint
        self.checkpoint.save_checkpoint('users', 'mapping', 'all', data=user_mapping)

        return user_mapping

    def phase3_templates(self, discovery_data: Dict[str, Any]) -> Dict[str, str]:
        """Phase 3: Migrate surveys as templates"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 3: TEMPLATE (SURVEY) MIGRATION")
        logger.info("="*50)

        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('templates', 'mapping', 'all')
        if checkpoint_data and checkpoint_data.get('data'):
            logger.info("Resuming from templates checkpoint")
            return checkpoint_data['data']

        template_mapping = {}
        surveys = discovery_data.get('surveys', [])

        logger.info(f"Migrating {len(surveys)} surveys as blueprints...\n")

        for survey in surveys:
            try:
                survey_id = survey.get('id')
                survey_title = survey.get('title', 'Untitled')

                # Count questions
                question_count = 0
                for page in survey.get('pages', []):
                    question_count += len(page.get('questions', []))

                page_count = len(survey.get('pages', []))

                logger.info(f"Processing survey: {survey_title}")
                logger.info(f"  - ID: {survey_id}")
                logger.info(f"  - Pages: {page_count}")
                logger.info(f"  - Questions: {question_count}")
                logger.info(f"  - Responses: {survey.get('response_count', 0)}")

                # Check if already processed
                if self.checkpoint.is_item_processed('templates', 'survey', survey_id):
                    logger.info(f"  - Already processed, skipping")
                    continue

                # Transform to blueprint
                blueprint = self.template_transformer.transform(survey)
                logger.info(f"  - Complexity: {blueprint['metadata'].get('complexity', 'unknown')}")
                logger.info(f"  - Steps: {len(blueprint.get('steps', []))}")

                if not self.dry_run:
                    # Create blueprint in Tallyfy
                    result = self.tallyfy.create_checklist(
                        blueprint['name'],
                        blueprint.get('description', ''),
                        blueprint.get('steps')
                    )

                    if result:
                        template_mapping[survey_id] = result.get('id', '')
                        logger.info(f"  Created blueprint: {result.get('id', '')}")

                        # Save checkpoint for this survey
                        self.checkpoint.save_checkpoint('templates', 'survey', survey_id,
                                                       data={'blueprint_id': result.get('id', '')})
                else:
                    template_mapping[survey_id] = f"dry_run_template_{len(template_mapping)}"
                    logger.info(f"  [DRY RUN] Would create blueprint")
                    self.checkpoint.save_checkpoint('templates', 'survey', survey_id,
                                                   data={'dry_run': True})

                self.stats['surveys_migrated'] += 1

            except Exception as e:
                logger.error(f"Failed to migrate survey {survey.get('title')}: {e}")
                self.stats['errors'].append(f"Survey migration: {e}")
                self.checkpoint.log_error('templates', 'survey', survey.get('id', ''),
                                         type(e).__name__, str(e))

            # Add delay to avoid rate limits
            time.sleep(1)

        logger.info(f"\nTemplate migration complete: {len(template_mapping)} surveys migrated")

        # Save checkpoint
        self.checkpoint.save_checkpoint('templates', 'mapping', 'all', data=template_mapping)

        return template_mapping

    def phase4_instances(self, discovery_data: Dict[str, Any],
                        template_mapping: Dict[str, str]) -> Dict[str, str]:
        """Phase 4: Migrate survey responses as instances"""
        logger.info("\n" + "="*50)
        logger.info("PHASE 4: INSTANCE (RESPONSE) MIGRATION")
        logger.info("="*50)

        # Check for checkpoint
        checkpoint_data = self.checkpoint.get_checkpoint('instances', 'mapping', 'all')
        if checkpoint_data and checkpoint_data.get('data'):
            logger.info("Resuming from instances checkpoint")
            return checkpoint_data['data']

        instance_mapping = {}
        surveys = discovery_data.get('surveys', [])

        # Limit responses per survey for performance
        max_responses_per_survey = self.config.get('max_responses_per_survey', 50)

        logger.info(f"Migrating responses (max {max_responses_per_survey} per survey)...\n")

        for survey in surveys:
            survey_id = survey.get('id')
            survey_title = survey.get('title', 'Untitled')

            # Skip if no blueprint mapping
            if survey_id not in template_mapping:
                logger.warning(f"Skipping responses for unmapped survey: {survey_title}")
                continue

            blueprint_id = template_mapping[survey_id]

            try:
                # Get responses
                logger.info(f"Fetching responses for: {survey_title}")
                responses = self.surveymonkey.get_survey_responses(
                    survey_id, per_page=max_responses_per_survey
                )
                response_items = responses.get('data', [])

                if not response_items:
                    logger.info(f"  - No responses to migrate")
                    continue

                logger.info(f"  - Found {len(response_items)} responses")

                # Transform responses
                processes = self.instance_transformer.transform_batch(
                    response_items,
                    blueprint_id,
                    survey  # Pass full survey structure for question mapping
                )

                # Create processes in Tallyfy
                for idx, process in enumerate(processes):
                    response_id = response_items[idx].get('id', f"response_{idx}")

                    if not self.dry_run:
                        try:
                            result = self.tallyfy.create_run(
                                process['checklist_id'],
                                process['name'],
                                process.get('prerun_data')
                            )

                            if result:
                                instance_mapping[response_id] = result.get('id', '')
                                logger.info(f"    Created process for response {response_id[:8]}")
                        except Exception as e:
                            logger.error(f"    Failed to create process: {e}")
                    else:
                        instance_mapping[response_id] = f"dry_run_instance_{len(instance_mapping)}"
                        logger.info(f"    [DRY RUN] Would create process for response {response_id[:8]}")

                    self.stats['responses_migrated'] += 1

                    # Add delay to avoid rate limits
                    if idx % 10 == 0:
                        time.sleep(1)

            except Exception as e:
                logger.error(f"Failed to migrate responses for {survey_title}: {e}")
                self.stats['errors'].append(f"Response migration: {e}")

        logger.info(f"\nInstance migration complete: {len(instance_mapping)} responses migrated")

        # Save checkpoint
        self.checkpoint.save_checkpoint('instances', 'mapping', 'all', data=instance_mapping)

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
        for survey_id, blueprint_id in template_mapping.items():
            if self.validator.validate_template(blueprint_id):
                validation_results['templates']['validated'] += 1
            else:
                validation_results['issues'].append(f"Template validation failed: {survey_id}")

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
                logger.warning(f"    - {issue}")

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
                'surveys_migrated': self.stats['surveys_migrated'],
                'responses_migrated': self.stats['responses_migrated'],
                'users_migrated': self.stats['users_migrated']
            },
            'validation': validation_results,
            'errors': self.stats['errors'],
            'ai_enhanced': bool(self.ai_client)
        }

        # Save report
        report_file = f"data/surveymonkey_migration_report_{self.migration_id}.json"
        os.makedirs('data', exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"\nReport saved to: {report_file}")

        return report


def main():
    """Main entry point"""
    # Load configuration from environment
    config = {
        'surveymonkey_access_token': os.getenv('SURVEYMONKEY_ACCESS_TOKEN'),
        'tallyfy_api_key': os.getenv('TALLYFY_API_KEY'),
        'tallyfy_org_id': os.getenv('TALLYFY_ORG_ID'),
        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
        'dry_run': os.getenv('DRY_RUN', 'false').lower() == 'true',
        'max_responses_per_survey': int(os.getenv('MAX_RESPONSES_PER_SURVEY', '50'))
    }

    # Validate required configuration
    if not config['surveymonkey_access_token']:
        logger.error("SURVEYMONKEY_ACCESS_TOKEN environment variable is required")
        sys.exit(1)

    if not config['tallyfy_api_key']:
        logger.error("TALLYFY_API_KEY environment variable is required")
        sys.exit(1)

    if not config['tallyfy_org_id']:
        logger.error("TALLYFY_ORG_ID environment variable is required")
        sys.exit(1)

    # Create and run migrator
    migrator = SurveyMonkeyMigrator(config)

    try:
        report = migrator.migrate()

        # Print summary
        print("\n" + "="*50)
        print("MIGRATION SUMMARY")
        print("="*50)
        print(f"Status: {report['status']}")
        print(f"Duration: {report['duration_seconds']:.2f} seconds")
        print(f"Surveys Migrated: {report['statistics']['surveys_migrated']}")
        print(f"Responses Migrated: {report['statistics']['responses_migrated']}")
        print(f"Users Migrated: {report['statistics']['users_migrated']}")
        print(f"Errors: {len(report['errors'])}")

        sys.exit(0 if report['status'] == 'completed' else 1)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
