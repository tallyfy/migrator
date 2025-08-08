"""
Migration Validator for RocketLane to Tallyfy
Validates data integrity and migration success
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validate migration data and integrity"""
    
    def __init__(self, rocketlane_client, tallyfy_client):
        """
        Initialize validator
        
        Args:
            rocketlane_client: RocketLane API client
            tallyfy_client: Tallyfy API client
        """
        self.rocketlane_client = rocketlane_client
        self.tallyfy_client = tallyfy_client
        
        self.validation_results = {
            'users': {'total': 0, 'validated': 0, 'errors': []},
            'templates': {'total': 0, 'validated': 0, 'errors': []},
            'processes': {'total': 0, 'validated': 0, 'errors': []},
            'fields': {'total': 0, 'validated': 0, 'errors': []},
            'assignments': {'total': 0, 'validated': 0, 'errors': []},
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
        
        # Validate users and teams
        self._validate_users(migration_data.get('user_mappings', {}))
        
        # Validate templates
        self._validate_templates(migration_data.get('template_mappings', {}))
        
        # Validate processes
        self._validate_processes(migration_data.get('process_mappings', {}))
        
        # Validate field mappings
        self._validate_fields(migration_data.get('field_mappings', {}))
        
        # Validate assignments
        self._validate_assignments(migration_data.get('assignment_mappings', {}))
        
        # Check data integrity
        self._check_data_integrity(migration_data)
        
        # Generate summary
        self._generate_summary()
        
        return self.validation_results
    
    def _validate_users(self, user_mappings: Dict[str, str]):
        """Validate user migrations"""
        logger.info("Validating user migrations...")
        
        for source_id, target_id in user_mappings.items():
            self.validation_results['users']['total'] += 1
            
            try:
                # Check if user exists in Tallyfy
                if target_id.startswith('guest_'):
                    # Validate guest user
                    exists = self._validate_guest_user(target_id)
                elif target_id.startswith('org_'):
                    # Validate organization
                    exists = self._validate_organization(target_id)
                else:
                    # Validate regular user
                    exists = self._validate_regular_user(target_id)
                
                if exists:
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
                # Verify template exists in Tallyfy
                if self.tallyfy_client.validate_checklist(target_id):
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
                # Verify process exists in Tallyfy
                if self.tallyfy_client.validate_run(target_id):
                    self.validation_results['processes']['validated'] += 1
                    
                    # Check process state
                    issues = self._validate_process_state(source_id, target_id)
                    if issues:
                        self.validation_results['processes']['errors'].extend(issues)
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
            
            # Check field type compatibility
            source_type = mapping.get('source_type')
            target_type = mapping.get('target_type')
            confidence = mapping.get('confidence', 1.0)
            
            if confidence < 0.7:
                # Flag for manual review
                self.validation_results['manual_review'].append({
                    'type': 'field_mapping',
                    'field_id': field_id,
                    'source_type': source_type,
                    'target_type': target_type,
                    'confidence': confidence,
                    'reason': 'Low confidence AI mapping'
                })
            
            # Validate field type compatibility
            if self._is_field_compatible(source_type, target_type):
                self.validation_results['fields']['validated'] += 1
            else:
                self.validation_results['fields']['errors'].append({
                    'field_id': field_id,
                    'source_type': source_type,
                    'target_type': target_type,
                    'error': 'Incompatible field types'
                })
    
    def _validate_assignments(self, assignment_mappings: Dict[str, Dict[str, Any]]):
        """Validate task assignments"""
        logger.info("Validating task assignments...")
        
        for task_id, assignment in assignment_mappings.items():
            self.validation_results['assignments']['total'] += 1
            
            source_assignee = assignment.get('source_assignee')
            target_assignee = assignment.get('target_assignee')
            
            if target_assignee:
                # Check if assignee exists
                if self._validate_assignee_exists(target_assignee):
                    self.validation_results['assignments']['validated'] += 1
                else:
                    self.validation_results['assignments']['errors'].append({
                        'task_id': task_id,
                        'source_assignee': source_assignee,
                        'target_assignee': target_assignee,
                        'error': 'Assignee not found in Tallyfy'
                    })
            else:
                # No target assignee - flag for review
                self.validation_results['manual_review'].append({
                    'type': 'unassigned_task',
                    'task_id': task_id,
                    'source_assignee': source_assignee,
                    'reason': 'Could not map assignee'
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
        
        # Check paradigm shift impacts
        self._check_paradigm_shifts(migration_data)
    
    def _check_orphaned_references(self, migration_data: Dict[str, Any]):
        """Check for orphaned references"""
        user_mappings = migration_data.get('user_mappings', {})
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
        
        # Check tasks reference valid users
        for task in migration_data.get('tasks', []):
            assignee_id = task.get('assigned_to')
            if assignee_id and assignee_id not in user_mappings:
                self.validation_results['data_integrity']['issues'].append({
                    'type': 'orphaned_user_reference',
                    'task_id': task.get('id'),
                    'user_id': assignee_id,
                    'severity': 'medium'
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
        # Check templates have required fields
        for template in migration_data.get('templates', []):
            if not template.get('name'):
                self.validation_results['data_integrity']['issues'].append({
                    'type': 'missing_required_field',
                    'entity': 'template',
                    'entity_id': template.get('id'),
                    'field': 'name',
                    'severity': 'high'
                })
            
            # Check for at least one step
            if not template.get('steps'):
                self.validation_results['data_integrity']['issues'].append({
                    'type': 'missing_steps',
                    'entity': 'template',
                    'entity_id': template.get('id'),
                    'severity': 'high'
                })
    
    def _check_paradigm_shifts(self, migration_data: Dict[str, Any]):
        """Check paradigm shift impacts"""
        paradigm_shifts = migration_data.get('paradigm_shifts', [])
        
        for shift in paradigm_shifts:
            if shift.get('type') == 'customer_portal_removed':
                # Flag all customer-visible items for review
                self.validation_results['manual_review'].append({
                    'type': 'paradigm_shift',
                    'shift_type': 'customer_portal_removed',
                    'affected_count': shift.get('affected_count', 0),
                    'reason': 'Customer portal access removed - verify guest access'
                })
            
            elif shift.get('type') == 'resource_management_simplified':
                # Flag resource allocations for review
                self.validation_results['manual_review'].append({
                    'type': 'paradigm_shift',
                    'shift_type': 'resource_management_simplified',
                    'affected_count': shift.get('affected_count', 0),
                    'reason': 'Resource management simplified - verify assignments'
                })
    
    def _validate_guest_user(self, guest_id: str) -> bool:
        """Validate guest user exists"""
        # Implementation depends on Tallyfy API
        return True  # Placeholder
    
    def _validate_organization(self, org_id: str) -> bool:
        """Validate organization exists"""
        # Implementation depends on Tallyfy API
        return True  # Placeholder
    
    def _validate_regular_user(self, user_id: str) -> bool:
        """Validate regular user exists"""
        # Implementation depends on Tallyfy API
        return True  # Placeholder
    
    def _validate_template_structure(self, source_id: str, target_id: str) -> List[Dict]:
        """Validate template structure preservation"""
        issues = []
        
        try:
            # Get source template
            source_template = self.rocketlane_client.get_template(source_id)
            
            # Get target template - would need actual API call
            # target_template = self.tallyfy_client.get_template(target_id)
            
            # Compare structures
            # This is a placeholder - actual implementation would compare:
            # - Number of phases/steps
            # - Form fields
            # - Dependencies
            
        except Exception as e:
            logger.warning(f"Could not validate template structure: {e}")
        
        return issues
    
    def _validate_process_state(self, source_id: str, target_id: str) -> List[Dict]:
        """Validate process state preservation"""
        issues = []
        
        try:
            # Get source project
            source_project = self.rocketlane_client.get_project(source_id)
            
            # Get target process - would need actual API call
            # target_process = self.tallyfy_client.get_process(target_id)
            
            # Compare states
            # This is a placeholder - actual implementation would compare:
            # - Task completion status
            # - Current phase
            # - Assignments
            
        except Exception as e:
            logger.warning(f"Could not validate process state: {e}")
        
        return issues
    
    def _is_field_compatible(self, source_type: str, target_type: str) -> bool:
        """Check if field types are compatible"""
        # Define compatibility rules
        compatible_mappings = {
            'text': ['text', 'textarea'],
            'number': ['text'],
            'boolean': ['radio'],
            'select': ['dropdown', 'radio'],
            'multiselect': ['multiselect'],
            'date': ['date'],
            'file': ['file'],
            'user': ['assignees_form']
        }
        
        source_category = self._get_field_category(source_type)
        return target_type in compatible_mappings.get(source_category, [])
    
    def _get_field_category(self, field_type: str) -> str:
        """Get field category for compatibility checking"""
        text_types = ['text', 'shorttext', 'longtext', 'string', 'varchar']
        number_types = ['number', 'integer', 'float', 'decimal', 'currency']
        boolean_types = ['boolean', 'bool', 'checkbox', 'yesno']
        select_types = ['select', 'dropdown', 'choice', 'radio']
        multiselect_types = ['multiselect', 'multichoice', 'checkboxes', 'tags']
        date_types = ['date', 'datetime', 'time', 'timestamp']
        file_types = ['file', 'attachment', 'document', 'image']
        user_types = ['user', 'assignee', 'team', 'group']
        
        field_type_lower = field_type.lower()
        
        if field_type_lower in text_types:
            return 'text'
        elif field_type_lower in number_types:
            return 'number'
        elif field_type_lower in boolean_types:
            return 'boolean'
        elif field_type_lower in select_types:
            return 'select'
        elif field_type_lower in multiselect_types:
            return 'multiselect'
        elif field_type_lower in date_types:
            return 'date'
        elif field_type_lower in file_types:
            return 'file'
        elif field_type_lower in user_types:
            return 'user'
        else:
            return 'text'  # Default fallback
    
    def _validate_assignee_exists(self, assignee_id: str) -> bool:
        """Check if assignee exists in Tallyfy"""
        # Implementation depends on Tallyfy API
        return True  # Placeholder
    
    def _generate_summary(self):
        """Generate validation summary"""
        total_validated = sum([
            self.validation_results['users']['validated'],
            self.validation_results['templates']['validated'],
            self.validation_results['processes']['validated'],
            self.validation_results['fields']['validated'],
            self.validation_results['assignments']['validated']
        ])
        
        total_items = sum([
            self.validation_results['users']['total'],
            self.validation_results['templates']['total'],
            self.validation_results['processes']['total'],
            self.validation_results['fields']['total'],
            self.validation_results['assignments']['total']
        ])
        
        total_errors = sum([
            len(self.validation_results['users']['errors']),
            len(self.validation_results['templates']['errors']),
            len(self.validation_results['processes']['errors']),
            len(self.validation_results['fields']['errors']),
            len(self.validation_results['assignments']['errors'])
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
            json.dumps(report, f, indent=2)
        
        logger.info(f"Validation report saved to {output_path}")