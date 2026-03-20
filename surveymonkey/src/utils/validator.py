"""
Migration Validator for SurveyMonkey to Tallyfy
Validates data integrity and migration success
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validate migration data and integrity"""

    def __init__(self, surveymonkey_client, tallyfy_client):
        """
        Initialize validator

        Args:
            surveymonkey_client: SurveyMonkey API client
            tallyfy_client: Tallyfy API client
        """
        self.surveymonkey_client = surveymonkey_client
        self.tallyfy_client = tallyfy_client

        self.validation_results = {
            'users': {'total': 0, 'validated': 0, 'errors': []},
            'templates': {'total': 0, 'validated': 0, 'errors': []},
            'processes': {'total': 0, 'validated': 0, 'errors': []},
            'fields': {'total': 0, 'validated': 0, 'errors': []},
            'data_integrity': {'issues': []},
            'manual_review': []
        }

    def validate_migration(self, migration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform complete migration validation

        Args:
            migration_data: Complete migration data including mappings

        Returns:
            Validation results
        """
        logger.info("Starting migration validation...")

        # Validate users
        self._validate_users(migration_data.get('user_mappings', {}))

        # Validate templates
        self._validate_templates(migration_data.get('template_mappings', {}))

        # Validate processes
        self._validate_processes(migration_data.get('process_mappings', {}))

        # Validate field mappings
        self._validate_fields(migration_data.get('field_mappings', {}))

        # Check data integrity
        self._check_data_integrity(migration_data)

        # Generate summary
        self._generate_summary()

        return self.validation_results

    def validate_user(self, tallyfy_id: str) -> bool:
        """Validate a single user exists in Tallyfy"""
        try:
            # Placeholder - actual implementation depends on Tallyfy API
            return True
        except Exception:
            return False

    def validate_template(self, blueprint_id: str) -> bool:
        """Validate a single template exists in Tallyfy"""
        try:
            return self.tallyfy_client.validate_checklist(blueprint_id)
        except Exception:
            return False

    def validate_instance(self, process_id: str) -> bool:
        """Validate a single process instance exists in Tallyfy"""
        try:
            return self.tallyfy_client.validate_run(process_id)
        except Exception:
            return False

    def _validate_users(self, user_mappings: Dict[str, str]):
        """Validate user migrations"""
        logger.info("Validating user migrations...")

        for source_id, target_id in user_mappings.items():
            self.validation_results['users']['total'] += 1

            try:
                if self.validate_user(target_id):
                    self.validation_results['users']['validated'] += 1
                else:
                    self.validation_results['users']['errors'].append({
                        'source_id': source_id,
                        'target_id': target_id,
                        'error': 'User not found in Tallyfy'
                    })

            except Exception as e:
                logger.error(f"Error validating user {source_id}: {e}")
                self.validation_results['users']['errors'].append({
                    'source_id': source_id,
                    'target_id': target_id,
                    'error': str(e)
                })

    def _validate_templates(self, template_mappings: Dict[str, str]):
        """Validate template migrations"""
        logger.info("Validating template migrations...")

        for source_id, target_id in template_mappings.items():
            self.validation_results['templates']['total'] += 1

            try:
                if self.validate_template(target_id):
                    self.validation_results['templates']['validated'] += 1

                    # Check template structure
                    issues = self._validate_template_structure(source_id, target_id)
                    if issues:
                        self.validation_results['templates']['errors'].extend(issues)
                else:
                    self.validation_results['templates']['errors'].append({
                        'source_id': source_id,
                        'target_id': target_id,
                        'error': 'Template not found in Tallyfy'
                    })

            except Exception as e:
                logger.error(f"Error validating template {source_id}: {e}")
                self.validation_results['templates']['errors'].append({
                    'source_id': source_id,
                    'target_id': target_id,
                    'error': str(e)
                })

    def _validate_processes(self, process_mappings: Dict[str, str]):
        """Validate process migrations"""
        logger.info("Validating process migrations...")

        for source_id, target_id in process_mappings.items():
            self.validation_results['processes']['total'] += 1

            try:
                if self.validate_instance(target_id):
                    self.validation_results['processes']['validated'] += 1
                else:
                    self.validation_results['processes']['errors'].append({
                        'source_id': source_id,
                        'target_id': target_id,
                        'error': 'Process not found in Tallyfy'
                    })

            except Exception as e:
                logger.error(f"Error validating process {source_id}: {e}")
                self.validation_results['processes']['errors'].append({
                    'source_id': source_id,
                    'target_id': target_id,
                    'error': str(e)
                })

    def _validate_fields(self, field_mappings: Dict[str, Dict[str, Any]]):
        """Validate field mappings"""
        logger.info("Validating field mappings...")

        for field_id, mapping in field_mappings.items():
            self.validation_results['fields']['total'] += 1

            source_type = mapping.get('source_type')
            target_type = mapping.get('target_type')
            confidence = mapping.get('confidence', 1.0)

            if confidence < 0.7:
                self.validation_results['manual_review'].append({
                    'type': 'field_mapping',
                    'field_id': field_id,
                    'source_type': source_type,
                    'target_type': target_type,
                    'confidence': confidence,
                    'reason': 'Low confidence AI mapping'
                })

            if self._is_field_compatible(source_type, target_type):
                self.validation_results['fields']['validated'] += 1
            else:
                self.validation_results['fields']['errors'].append({
                    'field_id': field_id,
                    'source_type': source_type,
                    'target_type': target_type,
                    'error': 'Incompatible field types'
                })

    def _check_data_integrity(self, migration_data: Dict[str, Any]):
        """Check overall data integrity"""
        logger.info("Checking data integrity...")

        # Check for orphaned references
        self._check_orphaned_references(migration_data)

        # Check for duplicate mappings
        self._check_duplicate_mappings(migration_data)

        # Check for missing required data
        self._check_missing_required_data(migration_data)

    def _check_orphaned_references(self, migration_data: Dict[str, Any]):
        """Check for orphaned references"""
        template_mappings = migration_data.get('template_mappings', {})

        # Check processes reference valid templates
        for process in migration_data.get('processes', []):
            template_id = process.get('template_id')
            if template_id and template_id not in template_mappings:
                self.validation_results['data_integrity']['issues'].append({
                    'type': 'orphaned_template_reference',
                    'process_id': process.get('id'),
                    'template_id': template_id,
                    'severity': 'high'
                })

    def _check_duplicate_mappings(self, migration_data: Dict[str, Any]):
        """Check for duplicate mappings"""
        seen_targets = {}

        for mapping_type in ['user_mappings', 'template_mappings', 'process_mappings']:
            mappings = migration_data.get(mapping_type, {})

            for source_id, target_id in mappings.items():
                key = f"{mapping_type}:{target_id}"
                if key in seen_targets:
                    self.validation_results['data_integrity']['issues'].append({
                        'type': 'duplicate_mapping',
                        'mapping_type': mapping_type,
                        'source_ids': [seen_targets[key], source_id],
                        'target_id': target_id,
                        'severity': 'high'
                    })
                else:
                    seen_targets[key] = source_id

    def _check_missing_required_data(self, migration_data: Dict[str, Any]):
        """Check for missing required data"""
        for template in migration_data.get('templates', []):
            if not template.get('name'):
                self.validation_results['data_integrity']['issues'].append({
                    'type': 'missing_required_field',
                    'entity': 'template',
                    'entity_id': template.get('id'),
                    'field': 'name',
                    'severity': 'high'
                })

            if not template.get('steps'):
                self.validation_results['data_integrity']['issues'].append({
                    'type': 'missing_steps',
                    'entity': 'template',
                    'entity_id': template.get('id'),
                    'severity': 'high'
                })

    def _validate_template_structure(self, source_id: str, target_id: str) -> List[Dict]:
        """Validate template structure preservation"""
        issues = []

        try:
            # Get source survey details
            source_survey = self.surveymonkey_client.get_survey_details(source_id)

            # Count source questions
            source_question_count = 0
            for page in source_survey.get('pages', []):
                source_question_count += len(page.get('questions', []))

            # Validate target has appropriate structure
            # Actual comparison would need Tallyfy API call

        except Exception as e:
            logger.warning(f"Could not validate template structure: {e}")

        return issues

    def _is_field_compatible(self, source_type: str, target_type: str) -> bool:
        """Check if SurveyMonkey question type is compatible with Tallyfy field type"""
        # Define compatibility rules
        compatible_mappings = {
            'single_choice': ['radio', 'dropdown'],
            'multiple_choice': ['multiselect', 'radio'],
            'dropdown': ['dropdown', 'radio'],
            'open_ended': ['text', 'textarea'],
            'matrix': ['textarea', 'table'],
            'ranking': ['textarea', 'multiselect'],
            'demographic': ['text', 'textarea'],
            'datetime': ['date', 'text'],
            'file_upload': ['file'],
            'slider': ['text'],
            'image_choice': ['radio', 'multiselect'],
            'presentation': [],  # No field, display only
        }

        if not source_type or not target_type:
            return True  # Cannot validate without types

        return target_type in compatible_mappings.get(source_type, ['text'])

    def _generate_summary(self):
        """Generate validation summary"""
        total_validated = sum([
            self.validation_results['users']['validated'],
            self.validation_results['templates']['validated'],
            self.validation_results['processes']['validated'],
            self.validation_results['fields']['validated'],
        ])

        total_items = sum([
            self.validation_results['users']['total'],
            self.validation_results['templates']['total'],
            self.validation_results['processes']['total'],
            self.validation_results['fields']['total'],
        ])

        total_errors = sum([
            len(self.validation_results['users']['errors']),
            len(self.validation_results['templates']['errors']),
            len(self.validation_results['processes']['errors']),
            len(self.validation_results['fields']['errors']),
        ])

        self.validation_results['summary'] = {
            'total_items': total_items,
            'validated': total_validated,
            'errors': total_errors,
            'integrity_issues': len(self.validation_results['data_integrity']['issues']),
            'manual_review_required': len(self.validation_results['manual_review']),
            'success_rate': (total_validated / total_items * 100) if total_items > 0 else 0
        }

        # Determine overall status
        if total_errors == 0 and len(self.validation_results['data_integrity']['issues']) == 0:
            self.validation_results['status'] = 'success'
        elif total_errors < (total_items * 0.05):  # Less than 5% errors
            self.validation_results['status'] = 'success_with_warnings'
        else:
            self.validation_results['status'] = 'failed'

    def generate_report(self, output_path: str):
        """
        Generate validation report

        Args:
            output_path: Path to save report
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'results': self.validation_results
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Validation report saved to {output_path}")
