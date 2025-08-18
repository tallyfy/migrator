#!/usr/bin/env python3
"""
Universal Migration Validation Script
Can be used by any migrator to validate migration completeness and accuracy
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class ValidationResult:
    """Validation result for a single check"""
    check_name: str
    status: str  # passed, failed, warning
    message: str
    details: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class UniversalMigrationValidator:
    """Universal validator for any vendor migration to Tallyfy"""
    
    def __init__(self, vendor_name: str, migration_id: str):
        """
        Initialize validator
        
        Args:
            vendor_name: Name of source vendor (e.g., 'trello', 'clickup')
            migration_id: Unique migration identifier
        """
        self.vendor_name = vendor_name
        self.migration_id = migration_id
        self.results: List[ValidationResult] = []
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup validation logging"""
        logger = logging.getLogger(f"{self.vendor_name}_validator")
        logger.setLevel(logging.INFO)
        
        # Create logs directory
        log_dir = Path(f"validation_logs/{self.vendor_name}")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler
        fh = logging.FileHandler(
            log_dir / f"{self.migration_id}_validation.log"
        )
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    # ============= DATA INTEGRITY CHECKS =============
    
    def validate_user_migration(self, 
                               source_users: List[Dict],
                               migrated_users: List[Dict]) -> ValidationResult:
        """Validate user migration completeness"""
        self.logger.info("Validating user migration...")
        
        source_emails = {u.get('email') for u in source_users if u.get('email')}
        migrated_emails = {u.get('email') for u in migrated_users if u.get('email')}
        
        missing_users = source_emails - migrated_emails
        extra_users = migrated_emails - source_emails
        
        if not missing_users and not extra_users:
            result = ValidationResult(
                check_name="user_migration",
                status="passed",
                message=f"All {len(source_users)} users migrated successfully",
                details={
                    'source_count': len(source_users),
                    'migrated_count': len(migrated_users),
                    'match_rate': 1.0
                }
            )
        elif missing_users:
            result = ValidationResult(
                check_name="user_migration",
                status="failed",
                message=f"{len(missing_users)} users failed to migrate",
                details={
                    'missing_users': list(missing_users),
                    'source_count': len(source_users),
                    'migrated_count': len(migrated_users),
                    'match_rate': len(migrated_emails) / len(source_emails)
                }
            )
        else:
            result = ValidationResult(
                check_name="user_migration",
                status="warning",
                message=f"Extra users found in migration",
                details={
                    'extra_users': list(extra_users),
                    'source_count': len(source_users),
                    'migrated_count': len(migrated_users)
                }
            )
        
        self.results.append(result)
        self.logger.info(f"User validation: {result.status}")
        return result
    
    def validate_field_mappings(self,
                               source_fields: List[Dict],
                               migrated_fields: List[Dict]) -> ValidationResult:
        """Validate field type mappings"""
        self.logger.info("Validating field mappings...")
        
        total_fields = len(source_fields)
        mapped_fields = 0
        unmapped_fields = []
        type_mismatches = []
        
        for source_field in source_fields:
            field_name = source_field.get('name', source_field.get('id'))
            field_type = source_field.get('type')
            
            # Find corresponding migrated field
            migrated_field = next(
                (f for f in migrated_fields 
                 if f.get('name') == field_name or f.get('source_id') == source_field.get('id')),
                None
            )
            
            if migrated_field:
                mapped_fields += 1
                
                # Check type compatibility
                if not self._are_types_compatible(field_type, migrated_field.get('type')):
                    type_mismatches.append({
                        'field': field_name,
                        'source_type': field_type,
                        'migrated_type': migrated_field.get('type')
                    })
            else:
                unmapped_fields.append(field_name)
        
        mapping_rate = mapped_fields / total_fields if total_fields > 0 else 0
        
        if mapping_rate >= 0.95 and not type_mismatches:
            status = "passed"
            message = f"Field mapping successful: {mapping_rate:.1%} mapped correctly"
        elif mapping_rate >= 0.80:
            status = "warning"
            message = f"Field mapping partial: {mapping_rate:.1%} mapped"
        else:
            status = "failed"
            message = f"Field mapping insufficient: only {mapping_rate:.1%} mapped"
        
        result = ValidationResult(
            check_name="field_mappings",
            status=status,
            message=message,
            details={
                'total_fields': total_fields,
                'mapped_fields': mapped_fields,
                'unmapped_fields': unmapped_fields,
                'type_mismatches': type_mismatches,
                'mapping_rate': mapping_rate
            }
        )
        
        self.results.append(result)
        self.logger.info(f"Field mapping validation: {result.status}")
        return result
    
    def validate_data_completeness(self,
                                  source_data: Dict[str, Any],
                                  migrated_data: Dict[str, Any]) -> ValidationResult:
        """Validate overall data completeness"""
        self.logger.info("Validating data completeness...")
        
        completeness_checks = []
        
        # Check each data category
        for category in source_data:
            if category in migrated_data:
                source_count = len(source_data[category]) if isinstance(source_data[category], list) else 1
                migrated_count = len(migrated_data[category]) if isinstance(migrated_data[category], list) else 1
                
                completeness = migrated_count / source_count if source_count > 0 else 0
                
                completeness_checks.append({
                    'category': category,
                    'source_count': source_count,
                    'migrated_count': migrated_count,
                    'completeness': completeness
                })
        
        avg_completeness = sum(c['completeness'] for c in completeness_checks) / len(completeness_checks) if completeness_checks else 0
        
        if avg_completeness >= 0.98:
            status = "passed"
            message = f"Data migration complete: {avg_completeness:.1%} preserved"
        elif avg_completeness >= 0.90:
            status = "warning"
            message = f"Data migration mostly complete: {avg_completeness:.1%} preserved"
        else:
            status = "failed"
            message = f"Data migration incomplete: only {avg_completeness:.1%} preserved"
        
        result = ValidationResult(
            check_name="data_completeness",
            status=status,
            message=message,
            details={
                'categories_checked': len(completeness_checks),
                'completeness_by_category': completeness_checks,
                'average_completeness': avg_completeness
            }
        )
        
        self.results.append(result)
        return result
    
    # ============= PROCESS INTEGRITY CHECKS =============
    
    def validate_workflow_logic(self,
                               source_workflow: Dict,
                               migrated_process: Dict) -> ValidationResult:
        """Validate workflow logic preservation"""
        self.logger.info("Validating workflow logic...")
        
        issues = []
        
        # Check step count
        source_steps = source_workflow.get('steps', source_workflow.get('tasks', []))
        migrated_steps = migrated_process.get('steps', [])
        
        if abs(len(source_steps) - len(migrated_steps)) > len(source_steps) * 0.2:
            issues.append(f"Step count mismatch: {len(source_steps)} → {len(migrated_steps)}")
        
        # Check conditional logic
        source_conditions = self._extract_conditions(source_workflow)
        migrated_conditions = self._extract_conditions(migrated_process)
        
        if len(source_conditions) > 0:
            condition_preservation = len(migrated_conditions) / len(source_conditions)
            if condition_preservation < 0.8:
                issues.append(f"Conditional logic loss: {(1-condition_preservation):.0%} conditions lost")
        
        # Check dependencies
        source_deps = self._extract_dependencies(source_workflow)
        migrated_deps = self._extract_dependencies(migrated_process)
        
        if len(source_deps) > 0:
            dep_preservation = len(migrated_deps) / len(source_deps)
            if dep_preservation < 0.9:
                issues.append(f"Dependency loss: {(1-dep_preservation):.0%} dependencies lost")
        
        if not issues:
            status = "passed"
            message = "Workflow logic fully preserved"
        elif len(issues) <= 2:
            status = "warning"
            message = f"Workflow logic mostly preserved with {len(issues)} issues"
        else:
            status = "failed"
            message = f"Workflow logic compromised: {len(issues)} critical issues"
        
        result = ValidationResult(
            check_name="workflow_logic",
            status=status,
            message=message,
            details={
                'issues': issues,
                'source_steps': len(source_steps),
                'migrated_steps': len(migrated_steps),
                'conditions_preserved': len(migrated_conditions),
                'dependencies_preserved': len(migrated_deps)
            }
        )
        
        self.results.append(result)
        return result
    
    def validate_paradigm_shifts(self,
                                vendor_type: str,
                                transformation_log: List[Dict]) -> ValidationResult:
        """Validate paradigm shift transformations"""
        self.logger.info("Validating paradigm shifts...")
        
        known_paradigms = {
            'kanban': ['kanban_to_sequential', 'board_to_process'],
            'form': ['form_to_workflow', 'multi_page_to_steps'],
            'project': ['project_to_process', 'tasks_to_steps'],
            'workflow': ['technical_to_business', 'complex_to_simple']
        }
        
        expected_shifts = known_paradigms.get(vendor_type, [])
        documented_shifts = [t.get('type') for t in transformation_log]
        
        missing_documentation = []
        for expected in expected_shifts:
            if not any(expected in doc for doc in documented_shifts):
                missing_documentation.append(expected)
        
        if not missing_documentation:
            status = "passed"
            message = "All paradigm shifts properly documented"
        else:
            status = "warning"
            message = f"Some paradigm shifts not documented: {missing_documentation}"
        
        result = ValidationResult(
            check_name="paradigm_shifts",
            status=status,
            message=message,
            details={
                'vendor_type': vendor_type,
                'expected_shifts': expected_shifts,
                'documented_shifts': documented_shifts,
                'missing': missing_documentation
            }
        )
        
        self.results.append(result)
        return result
    
    # ============= ID MAPPING CHECKS =============
    
    def validate_id_mappings(self, db_path: str = "migration_checkpoint.db") -> ValidationResult:
        """Validate ID mapping integrity"""
        self.logger.info("Validating ID mappings...")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check for orphaned mappings
            cursor.execute("""
                SELECT COUNT(*) FROM id_mappings 
                WHERE source_id IS NULL OR target_id IS NULL
            """)
            orphaned_count = cursor.fetchone()[0]
            
            # Check for duplicates
            cursor.execute("""
                SELECT source_id, COUNT(*) as count 
                FROM id_mappings 
                GROUP BY source_id 
                HAVING count > 1
            """)
            duplicates = cursor.fetchall()
            
            # Get total mappings
            cursor.execute("SELECT COUNT(*) FROM id_mappings")
            total_mappings = cursor.fetchone()[0]
            
            conn.close()
            
            if orphaned_count == 0 and len(duplicates) == 0:
                status = "passed"
                message = f"ID mappings valid: {total_mappings} mappings verified"
            elif orphaned_count > 0:
                status = "failed"
                message = f"ID mapping errors: {orphaned_count} orphaned mappings"
            else:
                status = "warning"
                message = f"ID mapping warnings: {len(duplicates)} duplicate mappings"
            
            result = ValidationResult(
                check_name="id_mappings",
                status=status,
                message=message,
                details={
                    'total_mappings': total_mappings,
                    'orphaned_mappings': orphaned_count,
                    'duplicate_mappings': len(duplicates),
                    'duplicates': duplicates[:10]  # First 10 duplicates
                }
            )
            
        except Exception as e:
            result = ValidationResult(
                check_name="id_mappings",
                status="failed",
                message=f"Could not validate ID mappings: {str(e)}",
                details={'error': str(e)}
            )
        
        self.results.append(result)
        return result
    
    # ============= PERFORMANCE CHECKS =============
    
    def validate_migration_performance(self,
                                      start_time: datetime,
                                      end_time: datetime,
                                      item_count: int,
                                      expected_rate: float = 100) -> ValidationResult:
        """Validate migration performance"""
        self.logger.info("Validating migration performance...")
        
        duration = (end_time - start_time).total_seconds()
        hours = duration / 3600
        
        if item_count > 0 and hours > 0:
            actual_rate = item_count / hours
            efficiency = actual_rate / expected_rate
            
            if efficiency >= 0.8:
                status = "passed"
                message = f"Migration performance acceptable: {actual_rate:.0f} items/hour"
            elif efficiency >= 0.5:
                status = "warning"
                message = f"Migration performance below target: {actual_rate:.0f} items/hour"
            else:
                status = "failed"
                message = f"Migration performance poor: {actual_rate:.0f} items/hour"
        else:
            status = "failed"
            message = "Could not calculate performance"
            actual_rate = 0
            efficiency = 0
        
        result = ValidationResult(
            check_name="migration_performance",
            status=status,
            message=message,
            details={
                'duration_hours': hours,
                'item_count': item_count,
                'actual_rate': actual_rate,
                'expected_rate': expected_rate,
                'efficiency': efficiency
            }
        )
        
        self.results.append(result)
        return result
    
    # ============= BUSINESS RULE CHECKS =============
    
    def validate_business_rules(self,
                               rules: List[Dict],
                               test_data: Dict) -> ValidationResult:
        """Validate business rules are preserved"""
        self.logger.info("Validating business rules...")
        
        passed_rules = []
        failed_rules = []
        
        for rule in rules:
            rule_name = rule.get('name')
            condition = rule.get('condition')
            expected_result = rule.get('expected')
            
            # Test the rule
            actual_result = self._test_business_rule(condition, test_data)
            
            if actual_result == expected_result:
                passed_rules.append(rule_name)
            else:
                failed_rules.append({
                    'rule': rule_name,
                    'expected': expected_result,
                    'actual': actual_result
                })
        
        pass_rate = len(passed_rules) / len(rules) if rules else 0
        
        if pass_rate >= 0.95:
            status = "passed"
            message = f"Business rules validated: {pass_rate:.0%} passed"
        elif pass_rate >= 0.80:
            status = "warning"
            message = f"Some business rules failed: {pass_rate:.0%} passed"
        else:
            status = "failed"
            message = f"Business rule validation failed: only {pass_rate:.0%} passed"
        
        result = ValidationResult(
            check_name="business_rules",
            status=status,
            message=message,
            details={
                'total_rules': len(rules),
                'passed': len(passed_rules),
                'failed': len(failed_rules),
                'failed_rules': failed_rules,
                'pass_rate': pass_rate
            }
        )
        
        self.results.append(result)
        return result
    
    # ============= HELPER METHODS =============
    
    def _are_types_compatible(self, source_type: str, target_type: str) -> bool:
        """Check if field types are compatible"""
        compatibility_map = {
            'text': ['short_text', 'long_text', 'text'],
            'email': ['email', 'text'],
            'number': ['number', 'currency', 'percent'],
            'date': ['date', 'datetime'],
            'select': ['dropdown', 'radio', 'select'],
            'multiselect': ['multi_select', 'checkbox', 'tags'],
            'file': ['file_attachment', 'document', 'file'],
            'user': ['member_select', 'user', 'assignee']
        }
        
        for source_group, compatible_types in compatibility_map.items():
            if source_type in source_group or source_type in compatible_types:
                return target_type in compatible_types
        
        return source_type == target_type
    
    def _extract_conditions(self, workflow: Dict) -> List[Dict]:
        """Extract conditional logic from workflow"""
        conditions = []
        
        # Look for conditions in various places
        for step in workflow.get('steps', workflow.get('tasks', [])):
            if step.get('conditions'):
                conditions.extend(step['conditions'])
            if step.get('conditional'):
                conditions.append({'step': step.get('name'), 'conditional': True})
        
        return conditions
    
    def _extract_dependencies(self, workflow: Dict) -> List[Tuple[str, str]]:
        """Extract step dependencies from workflow"""
        dependencies = []
        
        for step in workflow.get('steps', workflow.get('tasks', [])):
            if step.get('dependencies'):
                for dep in step['dependencies']:
                    dependencies.append((dep, step.get('id', step.get('name'))))
            if step.get('depends_on'):
                dependencies.append((step['depends_on'], step.get('id', step.get('name'))))
        
        return dependencies
    
    def _test_business_rule(self, condition: Dict, test_data: Dict) -> bool:
        """Test a business rule against data"""
        # Simplified rule testing - would be more complex in production
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if field not in test_data:
            return False
        
        field_value = test_data[field]
        
        if operator == 'equals':
            return field_value == value
        elif operator == 'greater_than':
            return field_value > value
        elif operator == 'less_than':
            return field_value < value
        elif operator == 'contains':
            return value in field_value
        elif operator == 'not_empty':
            return bool(field_value)
        
        return False
    
    # ============= REPORT GENERATION =============
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        self.logger.info("Generating validation report...")
        
        passed = [r for r in self.results if r.status == "passed"]
        warnings = [r for r in self.results if r.status == "warning"]
        failed = [r for r in self.results if r.status == "failed"]
        
        overall_status = "passed"
        if failed:
            overall_status = "failed"
        elif warnings:
            overall_status = "warning"
        
        report = {
            'migration_id': self.migration_id,
            'vendor': self.vendor_name,
            'validation_timestamp': datetime.utcnow().isoformat(),
            'overall_status': overall_status,
            'summary': {
                'total_checks': len(self.results),
                'passed': len(passed),
                'warnings': len(warnings),
                'failed': len(failed),
                'pass_rate': len(passed) / len(self.results) if self.results else 0
            },
            'results': [asdict(r) for r in self.results],
            'critical_issues': [asdict(r) for r in failed],
            'warnings': [asdict(r) for r in warnings],
            'recommendations': self._generate_recommendations()
        }
        
        # Save report
        report_path = Path(f"validation_reports/{self.vendor_name}")
        report_path.mkdir(parents=True, exist_ok=True)
        
        with open(report_path / f"{self.migration_id}_validation.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Validation report saved: {overall_status}")
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        for result in self.results:
            if result.status == "failed":
                if "user" in result.check_name:
                    recommendations.append("Review user migration logic and retry failed users")
                elif "field" in result.check_name:
                    recommendations.append("Manual field mapping review required for unmapped fields")
                elif "workflow" in result.check_name:
                    recommendations.append("Workflow logic needs manual verification")
                elif "performance" in result.check_name:
                    recommendations.append("Consider optimizing batch sizes and API calls")
            elif result.status == "warning":
                if "paradigm" in result.check_name:
                    recommendations.append("Document paradigm shifts for user training")
                elif "completeness" in result.check_name:
                    recommendations.append("Review missing data categories for manual migration")
        
        return list(set(recommendations))  # Remove duplicates
    
    def print_summary(self):
        """Print validation summary to console"""
        print("\n" + "="*60)
        print(f"VALIDATION SUMMARY - {self.vendor_name}")
        print("="*60)
        
        for result in self.results:
            status_symbol = {
                "passed": "✅",
                "warning": "⚠️",
                "failed": "❌"
            }.get(result.status, "❓")
            
            print(f"{status_symbol} {result.check_name}: {result.message}")
        
        print("\n" + "-"*60)
        passed = len([r for r in self.results if r.status == "passed"])
        total = len(self.results)
        print(f"Overall: {passed}/{total} checks passed")
        print("="*60 + "\n")


# Example usage
if __name__ == "__main__":
    # Example validation for a Trello migration
    validator = UniversalMigrationValidator("trello", "trello_migration_20240101_120000")
    
    # Sample data for testing
    source_users = [
        {"email": "user1@example.com", "name": "User 1"},
        {"email": "user2@example.com", "name": "User 2"}
    ]
    
    migrated_users = [
        {"email": "user1@example.com", "name": "User 1"},
        {"email": "user2@example.com", "name": "User 2"}
    ]
    
    # Run validations
    validator.validate_user_migration(source_users, migrated_users)
    
    # Generate report
    report = validator.generate_validation_report()
    validator.print_summary()
    
    print(f"Validation complete. Report saved to validation_reports/")