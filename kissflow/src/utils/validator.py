"""Validate migrated data for completeness and accuracy."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class Validator:
    """Validate migration results."""
    
    def __init__(self):
        """Initialize validator."""
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'summary': {}
        }
    
    def validate_users(self, id_mapper) -> Dict[str, Any]:
        """Validate user migration.
        
        Args:
            id_mapper: IDMapper instance
            
        Returns:
            Validation results for users
        """
        logger.info("Validating user migration...")
        
        results = {
            'total_mappings': 0,
            'valid': 0,
            'invalid': 0,
            'warnings': [],
            'errors': []
        }
        
        # Get all user mappings
        user_mappings = id_mapper.get_all_mappings('user')
        results['total_mappings'] = len(user_mappings)
        
        for mapping in user_mappings:
            object_type, kissflow_id, tallyfy_id, created_at, metadata = mapping
            
            # Basic validation
            if tallyfy_id and tallyfy_id != 'dry_run_' + kissflow_id:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                results['errors'].append(f"Invalid mapping for user {kissflow_id}")
        
        # Check for duplicate mappings
        tallyfy_ids = [m[2] for m in user_mappings]
        duplicates = [id for id in tallyfy_ids if tallyfy_ids.count(id) > 1]
        if duplicates:
            results['warnings'].append(f"Duplicate Tallyfy IDs found: {set(duplicates)}")
        
        logger.info(f"User validation complete: {results['valid']}/{results['total_mappings']} valid")
        
        return results
    
    def validate_templates(self, id_mapper) -> Dict[str, Any]:
        """Validate template migration (processes, boards, apps).
        
        Args:
            id_mapper: IDMapper instance
            
        Returns:
            Validation results for templates
        """
        logger.info("Validating template migration...")
        
        results = {
            'processes': {'total': 0, 'valid': 0, 'invalid': 0},
            'boards': {'total': 0, 'valid': 0, 'invalid': 0},
            'apps': {'total': 0, 'valid': 0, 'invalid': 0},
            'warnings': [],
            'errors': []
        }
        
        # Validate each template type
        for template_type in ['process', 'board', 'app']:
            mappings = id_mapper.get_all_mappings(template_type)
            results[f"{template_type}s"]['total'] = len(mappings)
            
            for mapping in mappings:
                object_type, kissflow_id, tallyfy_id, created_at, metadata = mapping
                
                if tallyfy_id and not tallyfy_id.startswith('dry_run_'):
                    results[f"{template_type}s"]['valid'] += 1
                    
                    # Additional validation for boards (paradigm shift)
                    if template_type == 'board':
                        self._validate_board_transformation(kissflow_id, results)
                else:
                    results[f"{template_type}s"]['invalid'] += 1
                    results['errors'].append(f"Invalid {template_type} mapping: {kissflow_id}")
        
        # Summary
        total_valid = sum(results[t]['valid'] for t in ['processes', 'boards', 'apps'])
        total_mappings = sum(results[t]['total'] for t in ['processes', 'boards', 'apps'])
        
        logger.info(f"Template validation complete: {total_valid}/{total_mappings} valid")
        
        return results
    
    def validate_instances(self, id_mapper) -> Dict[str, Any]:
        """Validate instance migration.
        
        Args:
            id_mapper: IDMapper instance
            
        Returns:
            Validation results for instances
        """
        logger.info("Validating instance migration...")
        
        results = {
            'total_mappings': 0,
            'valid': 0,
            'invalid': 0,
            'orphaned': 0,  # Instances without valid template
            'warnings': [],
            'errors': []
        }
        
        instance_mappings = id_mapper.get_all_mappings('instance')
        results['total_mappings'] = len(instance_mappings)
        
        # Get template mappings for validation
        checklist_ids = set()
        for template_type in ['process', 'board', 'app']:
            template_mappings = id_mapper.get_all_mappings(template_type)
            checklist_ids.update([m[2] for m in template_mappings])
        
        for mapping in instance_mappings:
            object_type, kissflow_id, tallyfy_id, created_at, metadata = mapping
            
            if tallyfy_id and not tallyfy_id.startswith('dry_run_'):
                results['valid'] += 1
                
                # Check if instance has valid template
                # This would require additional metadata parsing
                # For now, we'll just count valid mappings
            else:
                results['invalid'] += 1
                results['errors'].append(f"Invalid instance mapping: {kissflow_id}")
        
        logger.info(f"Instance validation complete: {results['valid']}/{results['total_mappings']} valid")
        
        return results
    
    def validate_data_integrity(self, source_data: Dict[str, Any],
                              migrated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data integrity between source and migrated data.
        
        Args:
            source_data: Original Kissflow data
            migrated_data: Migrated Tallyfy data
            
        Returns:
            Integrity validation results
        """
        logger.info("Validating data integrity...")
        
        results = {
            'field_mappings': {'matched': 0, 'missing': 0, 'extra': 0},
            'data_types': {'matched': 0, 'mismatched': 0},
            'required_fields': {'preserved': 0, 'lost': 0},
            'warnings': [],
            'errors': []
        }
        
        # Compare field mappings
        source_fields = set(source_data.keys())
        migrated_fields = set(migrated_data.keys())
        
        matched_fields = source_fields & migrated_fields
        missing_fields = source_fields - migrated_fields
        extra_fields = migrated_fields - source_fields
        
        results['field_mappings']['matched'] = len(matched_fields)
        results['field_mappings']['missing'] = len(missing_fields)
        results['field_mappings']['extra'] = len(extra_fields)
        
        if missing_fields:
            results['warnings'].append(f"Missing fields: {missing_fields}")
        
        # Validate data types for matched fields
        for field in matched_fields:
            source_value = source_data[field]
            migrated_value = migrated_data[field]
            
            if type(source_value) == type(migrated_value):
                results['data_types']['matched'] += 1
            else:
                results['data_types']['mismatched'] += 1
                results['warnings'].append(
                    f"Type mismatch for {field}: {type(source_value).__name__} -> {type(migrated_value).__name__}"
                )
        
        logger.info("Data integrity validation complete")
        
        return results
    
    def validate_workflow_logic(self, source_workflow: Dict[str, Any],
                              migrated_workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow logic preservation.
        
        Args:
            source_workflow: Kissflow workflow
            migrated_workflow: Tallyfy workflow
            
        Returns:
            Workflow validation results
        """
        logger.info("Validating workflow logic...")
        
        results = {
            'steps': {'source': 0, 'migrated': 0, 'ratio': 0},
            'conditions': {'preserved': 0, 'lost': 0},
            'assignments': {'preserved': 0, 'changed': 0},
            'warnings': [],
            'errors': []
        }
        
        # Count steps
        source_steps = len(source_workflow.get('steps', []))
        migrated_steps = len(migrated_workflow.get('steps', []))
        
        results['steps']['source'] = source_steps
        results['steps']['migrated'] = migrated_steps
        
        if source_steps > 0:
            results['steps']['ratio'] = migrated_steps / source_steps
            
            # Warning for significant step count changes
            if results['steps']['ratio'] < 0.8:
                results['warnings'].append(
                    f"Significant step reduction: {source_steps} -> {migrated_steps}"
                )
            elif results['steps']['ratio'] > 2.0:
                results['warnings'].append(
                    f"Significant step increase: {source_steps} -> {migrated_steps} "
                    "(likely due to paradigm shift)"
                )
        
        # Validate conditions and assignments
        # This would require deeper workflow analysis
        # Simplified for now
        
        logger.info("Workflow validation complete")
        
        return results
    
    def validate_permissions(self, source_perms: Dict[str, Any],
                           migrated_perms: Dict[str, Any]) -> Dict[str, Any]:
        """Validate permission preservation.
        
        Args:
            source_perms: Kissflow permissions
            migrated_perms: Tallyfy permissions
            
        Returns:
            Permission validation results
        """
        logger.info("Validating permissions...")
        
        results = {
            'roles': {'matched': 0, 'changed': 0},
            'access_levels': {'preserved': 0, 'modified': 0},
            'warnings': [],
            'errors': []
        }
        
        # Compare admin permissions
        source_admins = set(source_perms.get('admins', []))
        migrated_admins = set(migrated_perms.get('admins', []))
        
        if source_admins == migrated_admins:
            results['roles']['matched'] += 1
        else:
            results['roles']['changed'] += 1
            results['warnings'].append("Admin permissions changed during migration")
        
        # Compare member permissions
        source_members = set(source_perms.get('members', []))
        migrated_members = set(migrated_perms.get('members', []))
        
        if source_members == migrated_members:
            results['roles']['matched'] += 1
        else:
            results['roles']['changed'] += 1
            results['warnings'].append("Member permissions changed during migration")
        
        logger.info("Permission validation complete")
        
        return results
    
    def _validate_board_transformation(self, board_id: str,
                                      results: Dict[str, Any]):
        """Validate board to sequential transformation.
        
        Args:
            board_id: Board ID
            results: Results dictionary to update
        """
        # Board-specific validation for paradigm shift
        results['warnings'].append(
            f"Board {board_id}: Verify Kanban→Sequential transformation "
            "preserved business logic"
        )
    
    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report.
        
        Returns:
            Formatted validation report
        """
        report = []
        report.append("=" * 60)
        report.append("MIGRATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary section
        report.append("SUMMARY")
        report.append("-" * 40)
        
        total_passed = len(self.validation_results['passed'])
        total_failed = len(self.validation_results['failed'])
        total_warnings = len(self.validation_results['warnings'])
        
        report.append(f"Checks Passed: {total_passed}")
        report.append(f"Checks Failed: {total_failed}")
        report.append(f"Warnings: {total_warnings}")
        
        if total_failed == 0:
            report.append("\n✓ All validation checks passed!")
        else:
            report.append(f"\n✗ {total_failed} validation checks failed")
        
        # Failed checks
        if self.validation_results['failed']:
            report.append("\nFAILED CHECKS")
            report.append("-" * 40)
            for check in self.validation_results['failed']:
                report.append(f"  ✗ {check}")
        
        # Warnings
        if self.validation_results['warnings']:
            report.append("\nWARNINGS")
            report.append("-" * 40)
            for warning in self.validation_results['warnings']:
                report.append(f"  ⚠ {warning}")
        
        # Passed checks
        if self.validation_results['passed']:
            report.append("\nPASSED CHECKS")
            report.append("-" * 40)
            for check in self.validation_results['passed']:
                report.append(f"  ✓ {check}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def add_check(self, name: str, passed: bool, message: Optional[str] = None):
        """Add a validation check result.
        
        Args:
            name: Check name
            passed: Whether check passed
            message: Optional message
        """
        if passed:
            self.validation_results['passed'].append(f"{name}: {message or 'Passed'}")
        else:
            self.validation_results['failed'].append(f"{name}: {message or 'Failed'}")
    
    def add_warning(self, warning: str):
        """Add a validation warning.
        
        Args:
            warning: Warning message
        """
        self.validation_results['warnings'].append(warning)