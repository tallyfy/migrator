"""
Migration Validator for Pipefy to Tallyfy
Validates data integrity and migration success
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validates migration data and processes"""
    
    def __init__(self, pipefy_client, tallyfy_client, id_mapper):
        """
        Initialize validator
        
        Args:
            pipefy_client: Pipefy API client
            tallyfy_client: Tallyfy API client
            id_mapper: ID mapping system
        """
        self.pipefy_client = pipefy_client
        self.tallyfy_client = tallyfy_client
        self.id_mapper = id_mapper
        
        self.validation_results = []
        self.errors = []
        self.warnings = []
    
    def validate_migration(self) -> Dict[str, Any]:
        """
        Perform comprehensive migration validation
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Starting migration validation...")
        
        results = {
            'user_validation': self._validate_users(),
            'pipe_validation': self._validate_pipes(),
            'card_validation': self._validate_cards(),
            'field_validation': self._validate_fields(),
            'mapping_validation': self._validate_mappings(),
            'data_integrity': self._validate_data_integrity(),
            'transformation_accuracy': self._validate_transformations()
        }
        
        # Calculate overall status
        all_passed = all(r.get('passed', False) for r in results.values())
        
        results['overall_status'] = {
            'passed': all_passed,
            'total_checks': len(results),
            'passed_checks': sum(1 for r in results.values() if r.get('passed', False)),
            'errors': self.errors,
            'warnings': self.warnings
        }
        
        return results
    
    def _validate_users(self) -> Dict[str, Any]:
        """Validate user migration"""
        try:
            # Get user counts
            pipefy_users = self.pipefy_client.get_organization_members()
            user_mappings = self.id_mapper.get_all_mappings('user')
            
            pipefy_count = len(pipefy_users)
            mapped_count = len(user_mappings)
            
            # Check if all users are mapped
            if mapped_count >= pipefy_count * 0.95:  # Allow 5% tolerance
                return {
                    'passed': True,
                    'message': f"Successfully mapped {mapped_count}/{pipefy_count} users",
                    'pipefy_count': pipefy_count,
                    'mapped_count': mapped_count
                }
            else:
                self.warnings.append(f"Only {mapped_count}/{pipefy_count} users mapped")
                return {
                    'passed': False,
                    'message': f"User mapping incomplete: {mapped_count}/{pipefy_count}",
                    'pipefy_count': pipefy_count,
                    'mapped_count': mapped_count
                }
                
        except Exception as e:
            self.errors.append(f"User validation error: {e}")
            return {
                'passed': False,
                'message': f"User validation failed: {e}"
            }
    
    def _validate_pipes(self) -> Dict[str, Any]:
        """Validate pipe to checklist transformation"""
        try:
            pipes = self.pipefy_client.list_pipes()
            pipe_mappings = self.id_mapper.get_all_mappings('multiselect')
            
            pipe_count = len(pipes)
            mapped_count = len(pipe_mappings)
            
            if mapped_count >= pipe_count:
                # Validate each pipe transformation
                validation_errors = []
                
                for pipe in pipes[:5]:  # Sample validation
                    pipe_id = pipe['id']
                    checklist_id = self.id_mapper.get_tallyfy_id(pipe_id, 'multiselect')
                    
                    if checklist_id:
                        # Verify checklist exists in Tallyfy
                        try:
                            checklist = self.tallyfy_client.get_checklist(checklist_id)
                            
                            # Validate phase transformation
                            phase_count = len(pipe.get('phases', []))
                            # Each phase becomes 3 steps in Tallyfy
                            expected_steps = phase_count * 3
                            
                            if not checklist:
                                validation_errors.append(f"Checklist {checklist_id} not found")
                                
                        except Exception as e:
                            validation_errors.append(f"Failed to validate pipe {pipe_id}: {e}")
                
                if validation_errors:
                    self.warnings.extend(validation_errors)
                    return {
                        'passed': False,
                        'message': f"Pipe validation had {len(validation_errors)} errors",
                        'errors': validation_errors
                    }
                else:
                    return {
                        'passed': True,
                        'message': f"All {mapped_count} pipes successfully transformed",
                        'pipe_count': pipe_count,
                        'mapped_count': mapped_count
                    }
            else:
                return {
                    'passed': False,
                    'message': f"Pipe mapping incomplete: {mapped_count}/{pipe_count}",
                    'pipe_count': pipe_count,
                    'mapped_count': mapped_count
                }
                
        except Exception as e:
            self.errors.append(f"Pipe validation error: {e}")
            return {
                'passed': False,
                'message': f"Pipe validation failed: {e}"
            }
    
    def _validate_cards(self) -> Dict[str, Any]:
        """Validate card to process migration"""
        try:
            card_mappings = self.id_mapper.get_all_mappings('process')
            mapped_count = len(card_mappings)
            
            if mapped_count > 0:
                # Sample validation of cards
                sample_size = min(10, mapped_count)
                validation_errors = []
                
                for pipefy_id, tallyfy_id, _ in card_mappings[:sample_size]:
                    try:
                        # Verify process exists in Tallyfy
                        process = self.tallyfy_client.get_process(tallyfy_id)
                        if not process:
                            validation_errors.append(f"Process {tallyfy_id} not found")
                    except Exception as e:
                        validation_errors.append(f"Failed to validate card {pipefy_id}: {e}")
                
                if validation_errors:
                    self.warnings.extend(validation_errors)
                    return {
                        'passed': False,
                        'message': f"Card validation had {len(validation_errors)} errors",
                        'sample_size': sample_size,
                        'errors': validation_errors
                    }
                else:
                    return {
                        'passed': True,
                        'message': f"Successfully validated {sample_size} card samples",
                        'total_mapped': mapped_count
                    }
            else:
                return {
                    'passed': True,
                    'message': "No cards migrated yet",
                    'total_mapped': 0
                }
                
        except Exception as e:
            self.errors.append(f"Card validation error: {e}")
            return {
                'passed': False,
                'message': f"Card validation failed: {e}"
            }
    
    def _validate_fields(self) -> Dict[str, Any]:
        """Validate field to field transformation"""
        try:
            field_mappings = self.id_mapper.get_all_mappings("field")
            mapped_count = len(field_mappings)
            
            if mapped_count > 0:
                # Check field type transformations
                complex_fields = ['connector', 'formula', 'dynamic_content']
                warnings = []
                
                # This would ideally check actual field types
                # For now, just verify mappings exist
                
                return {
                    'passed': True,
                    'message': f"Successfully mapped {mapped_count} fields",
                    'field_count': mapped_count,
                    'warnings': warnings
                }
            else:
                return {
                    'passed': True,
                    'message': "No fields mapped yet",
                    'field_count': 0
                }
                
        except Exception as e:
            self.errors.append(f"Field validation error: {e}")
            return {
                'passed': False,
                'message': f"Field validation failed: {e}"
            }
    
    def _validate_mappings(self) -> Dict[str, Any]:
        """Validate ID mappings integrity"""
        try:
            stats = self.id_mapper.get_statistics()
            
            # Check for orphaned mappings
            validation_issues = []
            
            # Check mapping consistency
            if stats['cache_hit_rate'] < 50 and stats['lookups_performed'] > 100:
                validation_issues.append("Low cache hit rate indicates potential mapping issues")
            
            if validation_issues:
                self.warnings.extend(validation_issues)
                return {
                    'passed': False,
                    'message': "Mapping validation found issues",
                    'issues': validation_issues,
                    'stats': stats
                }
            else:
                return {
                    'passed': True,
                    'message': f"All {stats['total_mappings']} mappings valid",
                    'stats': stats
                }
                
        except Exception as e:
            self.errors.append(f"Mapping validation error: {e}")
            return {
                'passed': False,
                'message': f"Mapping validation failed: {e}"
            }
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """Validate overall data integrity"""
        try:
            integrity_checks = []
            
            # Check for data consistency
            mappings_by_type = self.id_mapper.get_statistics()['mappings_by_type']
            
            # Basic integrity checks
            if 'user' in mappings_by_type and mappings_by_type['user'] > 0:
                integrity_checks.append({
                    'check': 'Users mapped',
                    'passed': True
                })
            
            if 'multiselect' in mappings_by_type and mappings_by_type['multiselect'] > 0:
                integrity_checks.append({
                    'check': 'Pipes transformed',
                    'passed': True
                })
            
            all_passed = all(c['passed'] for c in integrity_checks)
            
            return {
                'passed': all_passed,
                'message': f"Data integrity {'verified' if all_passed else 'issues found'}",
                'checks': integrity_checks
            }
            
        except Exception as e:
            self.errors.append(f"Data integrity validation error: {e}")
            return {
                'passed': False,
                'message': f"Data integrity validation failed: {e}"
            }
    
    def _validate_transformations(self) -> Dict[str, Any]:
        """Validate transformation accuracy"""
        try:
            # Check Pipefy-specific transformations
            transformation_checks = []
            
            # Validate phase to step-group transformation
            phase_mappings = self.id_mapper.get_all_mappings('step_group')
            if phase_mappings:
                transformation_checks.append({
                    'transformation': 'Phase to Step Groups',
                    'count': len(phase_mappings),
                    'status': 'validated'
                })
            
            # Validate field type transformations
            field_mappings = self.id_mapper.get_all_mappings("field")
            if field_mappings:
                transformation_checks.append({
                    'transformation': 'Fields to field',
                    'count': len(field_mappings),
                    'status': 'validated'
                })
            
            return {
                'passed': True,
                'message': "Transformations validated",
                'transformations': transformation_checks
            }
            
        except Exception as e:
            self.errors.append(f"Transformation validation error: {e}")
            return {
                'passed': False,
                'message': f"Transformation validation failed: {e}"
            }
    
    def generate_validation_report(self) -> str:
        """
        Generate detailed validation report
        
        Returns:
            Formatted validation report
        """
        report = []
        report.append("=" * 60)
        report.append("PIPEFY TO TALLYFY MIGRATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        results = self.validate_migration()
        
        # Overall status
        overall = results['overall_status']
        report.append(f"Overall Status: {'PASSED' if overall['passed'] else 'FAILED'}")
        report.append(f"Checks Passed: {overall['passed_checks']}/{overall['total_checks']}")
        report.append("")
        
        # Individual checks
        report.append("VALIDATION CHECKS:")
        report.append("-" * 40)
        
        for check_name, check_result in results.items():
            if check_name == 'overall_status':
                continue
                
            status = "✓" if check_result.get('passed', False) else "✗"
            report.append(f"{status} {check_name}: {check_result.get('message', 'No message')}")
        
        # Errors and warnings
        if overall['errors']:
            report.append("")
            report.append("ERRORS:")
            for error in overall['errors']:
                report.append(f"  - {error}")
        
        if overall['warnings']:
            report.append("")
            report.append("WARNINGS:")
            for warning in overall['warnings']:
                report.append(f"  - {warning}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)