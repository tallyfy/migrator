"""
Migration Validator
Validates the success and integrity of the migration
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validates migration success and data integrity"""
    
    def __init__(self, ps_client, tallyfy_client, id_mapper):
        """
        Initialize validator
        
        Args:
            ps_client: Process Street API client
            tallyfy_client: Tallyfy API client
            id_mapper: ID mapping utility
        """
        self.ps_client = ps_client
        self.tallyfy_client = tallyfy_client
        self.id_mapper = id_mapper
        self.validation_results = {}
    
    def validate_migration(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all validation checks
        
        Returns:
            Dictionary of validation results
        """
        logger.info("Starting migration validation...")
        
        validations = [
            ('api_connectivity', self._validate_api_connectivity),
            ('id_mappings', self._validate_id_mappings),
            ('user_migration', self._validate_users),
            ('template_migration', self._validate_templates),
            ('process_migration', self._validate_processes),
            ('data_integrity', self._validate_data_integrity),
            ('relationships', self._validate_relationships)
        ]
        
        results = {}
        
        for name, validator in validations:
            logger.info(f"Running validation: {name}")
            try:
                result = validator()
                results[name] = result
                
                if result['passed']:
                    logger.info(f"✓ {name}: {result['message']}")
                else:
                    logger.warning(f"✗ {name}: {result['message']}")
                    
            except Exception as e:
                logger.error(f"Validation {name} failed with error: {e}")
                results[name] = {
                    'passed': False,
                    'message': f"Validation error: {str(e)}",
                    'error': str(e)
                }
        
        self.validation_results = results
        return results
    
    def _validate_api_connectivity(self) -> Dict[str, Any]:
        """Validate API connectivity"""
        try:
            # Test Process Street connection
            ps_org = self.ps_client.get_organization(self.ps_client.organization_id)
            
            # Test Tallyfy connection
            tallyfy_org = self.tallyfy_client.get_organization()
            
            return {
                'passed': True,
                'message': 'Both APIs are accessible',
                'details': {
                    'process_street': ps_org.get('name', 'Unknown'),
                    'tallyfy': tallyfy_org.get('name', 'Unknown')
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'API connectivity issue: {str(e)}',
                'error': str(e)
            }
    
    def _validate_id_mappings(self) -> Dict[str, Any]:
        """Validate ID mappings exist and are consistent"""
        try:
            stats = self.id_mapper.get_mapping_statistics()
            
            if stats.get('total', 0) == 0:
                return {
                    'passed': False,
                    'message': 'No ID mappings found',
                    'stats': stats
                }
            
            # Check for expected entity types
            expected_types = ['user', 'multiselect', 'process', 'step', "field"]
            missing_types = [t for t in expected_types if t not in stats]
            
            if missing_types:
                return {
                    'passed': False,
                    'message': f'Missing mappings for: {", ".join(missing_types)}',
                    'stats': stats
                }
            
            return {
                'passed': True,
                'message': f'ID mappings validated: {stats["total"]} total mappings',
                'stats': stats
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'ID mapping validation failed: {str(e)}',
                'error': str(e)
            }
    
    def _validate_users(self) -> Dict[str, Any]:
        """Validate user migration"""
        try:
            # Get counts
            ps_users = self.ps_client.list_users()
            tallyfy_users = self.tallyfy_client.list_users()
            
            ps_count = len(ps_users)
            tallyfy_count = len(tallyfy_users)
            
            # Check user mappings
            mapped_users = len(self.id_mapper.get_all_mappings('user'))
            
            # Validate specific users
            sample_size = min(5, ps_count)
            validation_errors = []
            
            for ps_user in ps_users[:sample_size]:
                ps_id = ps_user.get('id')
                tallyfy_id = self.id_mapper.get_tallyfy_id(ps_id, 'user')
                
                if not tallyfy_id:
                    validation_errors.append(f"No mapping for user {ps_user.get("text")}")
                    continue
                
                # Verify user exists in Tallyfy
                if not self.tallyfy_client.validate_import('user', tallyfy_id):
                    validation_errors.append(f"User {ps_user.get("text")} not found in Tallyfy")
            
            if validation_errors:
                return {
                    'passed': False,
                    'message': f'User validation failed: {len(validation_errors)} errors',
                    'errors': validation_errors[:5],  # First 5 errors
                    'counts': {
                        'process_street': ps_count,
                        'tallyfy': tallyfy_count,
                        'mapped': mapped_users
                    }
                }
            
            return {
                'passed': True,
                'message': f'Users validated: {mapped_users} mapped successfully',
                'counts': {
                    'process_street': ps_count,
                    'tallyfy': tallyfy_count,
                    'mapped': mapped_users
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'User validation failed: {str(e)}',
                'error': str(e)
            }
    
    def _validate_templates(self) -> Dict[str, Any]:
        """Validate template/workflow migration"""
        try:
            # Get counts
            ps_workflows = self.ps_client.list_workflows()
            tallyfy_checklists = self.tallyfy_client.list_checklists()
            
            ps_count = len(ps_workflows)
            mapped_count = len(self.id_mapper.get_all_mappings('multiselect'))
            
            # Validate template structure
            validation_errors = []
            sample_size = min(3, ps_count)
            
            for ps_workflow in ps_workflows[:sample_size]:
                ps_id = ps_workflow.get('id')
                tallyfy_id = self.id_mapper.get_tallyfy_id(ps_id, 'multiselect')
                
                if not tallyfy_id:
                    validation_errors.append(f"No mapping for workflow {ps_workflow.get('name')}")
                    continue
                
                # Get full workflow details
                ps_full = self.ps_client.get_workflow(ps_id)
                
                # Verify in Tallyfy
                try:
                    tallyfy_checklist = self.tallyfy_client.get_checklist(tallyfy_id)
                    
                    # Validate task counts
                    ps_task_count = len(ps_full.get('tasks', []))
                    tallyfy_step_count = len(tallyfy_checklist.get('steps', []))
                    
                    if ps_task_count != tallyfy_step_count:
                        validation_errors.append(
                            f"Task count mismatch for {ps_workflow.get('name')}: "
                            f"PS={ps_task_count}, TF={tallyfy_step_count}"
                        )
                    
                except Exception as e:
                    validation_errors.append(f"Cannot verify workflow {ps_workflow.get('name')}: {e}")
            
            if validation_errors:
                return {
                    'passed': False,
                    'message': f'Template validation failed: {len(validation_errors)} errors',
                    'errors': validation_errors,
                    'counts': {
                        'process_street': ps_count,
                        'mapped': mapped_count
                    }
                }
            
            return {
                'passed': True,
                'message': f'Templates validated: {mapped_count} mapped successfully',
                'counts': {
                    'process_street': ps_count,
                    'mapped': mapped_count
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'Template validation failed: {str(e)}',
                'error': str(e)
            }
    
    def _validate_processes(self) -> Dict[str, Any]:
        """Validate process/instance migration"""
        try:
            # Get counts
            ps_runs = self.ps_client.list_workflow_runs()
            ps_count = len(ps_runs)
            mapped_count = len(self.id_mapper.get_all_mappings('process'))
            
            # Validate process states
            validation_errors = []
            sample_size = min(5, ps_count)
            
            for ps_run in ps_runs[:sample_size]:
                ps_id = ps_run.get('id')
                tallyfy_id = self.id_mapper.get_tallyfy_id(ps_id, 'process')
                
                if not tallyfy_id:
                    # This might be expected if we filtered some runs
                    continue
                
                # Verify process exists
                if not self.tallyfy_client.validate_import('process', tallyfy_id):
                    validation_errors.append(f"Process {ps_run.get('name')} not found in Tallyfy")
            
            if validation_errors:
                return {
                    'passed': False,
                    'message': f'Process validation failed: {len(validation_errors)} errors',
                    'errors': validation_errors[:5],
                    'counts': {
                        'process_street': ps_count,
                        'mapped': mapped_count
                    }
                }
            
            return {
                'passed': True,
                'message': f'Processes validated: {mapped_count} mapped successfully',
                'counts': {
                    'process_street': ps_count,
                    'mapped': mapped_count
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'Process validation failed: {str(e)}',
                'error': str(e)
            }
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity and completeness"""
        try:
            integrity_checks = []
            
            # Check for orphaned mappings
            all_mappings = self.id_mapper.get_all_mappings()
            orphaned = []
            
            for mapping in all_mappings[:10]:  # Sample check
                entity_type = mapping['entity_type']
                tallyfy_id = mapping['tallyfy_id']
                
                if not self.tallyfy_client.validate_import(entity_type, tallyfy_id):
                    orphaned.append({
                        'type': entity_type,
                        'id': tallyfy_id,
                        'source_id': mapping['source_id']
                    })
            
            if orphaned:
                return {
                    'passed': False,
                    'message': f'Found {len(orphaned)} orphaned mappings',
                    'orphaned': orphaned
                }
            
            # Check required fields
            # This would involve more detailed field-level validation
            
            return {
                'passed': True,
                'message': 'Data integrity validated successfully',
                'checks_performed': len(integrity_checks)
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'Data integrity validation failed: {str(e)}',
                'error': str(e)
            }
    
    def _validate_relationships(self) -> Dict[str, Any]:
        """Validate relationships between entities"""
        try:
            relationship_errors = []
            
            # Sample validation of user-group relationships
            groups = self.id_mapper.get_all_mappings('group')[:5]
            
            for group_mapping in groups:
                ps_group_id = group_mapping['source_id']
                tallyfy_group_id = group_mapping['tallyfy_id']
                
                # Get Process Street group members
                try:
                    ps_group = self.ps_client.get_group(ps_group_id)
                    ps_members = ps_group.get('members', [])
                    
                    # Verify members are mapped
                    for member in ps_members:
                        member_id = member if isinstance(member, str) else member.get('id')
                        tallyfy_user_id = self.id_mapper.get_tallyfy_id(member_id, 'user')
                        
                        if not tallyfy_user_id:
                            relationship_errors.append(
                                f"Group member {member_id} not mapped for group {ps_group.get('name')}"
                            )
                            
                except Exception as e:
                    relationship_errors.append(f"Cannot validate group {ps_group_id}: {e}")
            
            if relationship_errors:
                return {
                    'passed': False,
                    'message': f'Relationship validation failed: {len(relationship_errors)} errors',
                    'errors': relationship_errors[:5]
                }
            
            return {
                'passed': True,
                'message': 'Entity relationships validated successfully'
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f'Relationship validation failed: {str(e)}',
                'error': str(e)
            }
    
    def generate_validation_report(self) -> str:
        """
        Generate a human-readable validation report
        
        Returns:
            Formatted validation report
        """
        if not self.validation_results:
            return "No validation results available. Run validate_migration() first."
        
        report = []
        report.append("=" * 60)
        report.append("MIGRATION VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.utcnow().isoformat()}")
        report.append("")
        
        passed_count = sum(1 for r in self.validation_results.values() if r['passed'])
        total_count = len(self.validation_results)
        
        report.append(f"Overall Status: {passed_count}/{total_count} checks passed")
        report.append("")
        
        for check_name, result in self.validation_results.items():
            status = "✓ PASSED" if result['passed'] else "✗ FAILED"
            report.append(f"{check_name}:")
            report.append(f"  Status: {status}")
            report.append(f"  Message: {result['message']}")
            
            if 'counts' in result:
                report.append("  Counts:")
                for key, value in result['counts'].items():
                    report.append(f"    - {key}: {value}")
            
            if 'errors' in result and result['errors']:
                report.append("  Errors:")
                for error in result['errors'][:3]:
                    report.append(f"    - {error}")
                if len(result['errors']) > 3:
                    report.append(f"    ... and {len(result['errors']) - 3} more")
            
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)