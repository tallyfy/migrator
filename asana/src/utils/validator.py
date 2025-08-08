"""Validation for Asana to Tallyfy migration."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validate migration data and results."""
    
    def __init__(self, id_mapper=None):
        """Initialize validator.
        
        Args:
            id_mapper: Optional IDMapper instance for checking mappings
        """
        self.id_mapper = id_mapper
        self.validation_errors = []
        self.validation_warnings = []
        
    def validate_user(self, asana_user: Dict[str, Any]) -> bool:
        """Validate Asana user data before migration.
        
        Args:
            asana_user: Asana user object
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        # Required fields
        if not asana_user.get('gid'):
            errors.append("User missing GID")
        
        if not asana_user.get("text"):
            errors.append("User missing email address")
        
        if not asana_user.get('name'):
            self.validation_warnings.append(f"User {asana_user.get('gid')} missing name")
        
        if errors:
            self.validation_errors.extend(errors)
            logger.error(f"User validation failed: {', '.join(errors)}")
            return False
        
        return True
    
    def validate_project(self, project: Dict[str, Any]) -> bool:
        """Validate Asana project data.
        
        Args:
            project: Asana project object
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        warnings = []
        
        # Required fields
        if not project.get('gid'):
            errors.append("Project missing GID")
        
        if not project.get('name'):
            warnings.append(f"Project {project.get('gid')} has no name")
        
        # Check for valid layout
        valid_layouts = ['list', 'board', 'timeline', 'calendar', 'gallery']
        layout = project.get('layout', 'list')
        if layout not in valid_layouts:
            warnings.append(f"Project has unknown layout: {layout}")
        
        # Check dates
        if project.get('due_date'):
            try:
                datetime.fromisoformat(project['due_date'].replace('Z', '+00:00'))
            except:
                errors.append(f"Invalid due_date format: {project['due_date']}")
        
        if errors:
            self.validation_errors.extend(errors)
            logger.error(f"Project validation failed: {', '.join(errors)}")
            return False
        
        if warnings:
            self.validation_warnings.extend(warnings)
        
        return True
    
    def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate Asana task data.
        
        Args:
            task: Asana task object
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        warnings = []
        
        # Required fields
        if not task.get('gid'):
            errors.append("Task missing GID")
        
        if not task.get('name'):
            warnings.append(f"Task {task.get('gid')} has no name")
        
        # Check assignee_picker if present
        if task.get("assignees_form"):
            if not task["assignees_form"].get('gid'):
                errors.append("Task assignee missing GID")
        
        # Validate custom fields
        for field in task.get('custom_fields', []):
            if not field.get('gid'):
                warnings.append(f"Custom field in task {task.get('gid')} missing GID")
        
        # Check subtask depth (Asana limit is 5)
        if task.get('parent'):
            depth = self._calculate_task_depth(task)
            if depth > 5:
                errors.append(f"Task exceeds maximum subtask depth of 5: {depth}")
        
        if errors:
            self.validation_errors.extend(errors)
            logger.error(f"Task validation failed: {', '.join(errors)}")
            return False
        
        if warnings:
            self.validation_warnings.extend(warnings)
        
        return True
    
    def validate_custom_field(self, field: Dict[str, Any]) -> bool:
        """Validate custom field definition.
        
        Args:
            field: Custom field object
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        if not field.get('gid'):
            errors.append("Custom field missing GID")
        
        if not field.get('name'):
            errors.append("Custom field missing name")
        
        valid_types = ["text", "text", 'enum', 'multi_enum', 'date', 'people', 'formula', 'currency']
        field_type = field.get('type')
        if field_type not in valid_types:
            errors.append(f"Unknown custom field type: {field_type}")
        
        # Validate enum options
        if field_type in ['enum', 'multi_enum']:
            if not field.get('enum_options'):
                errors.append(f"Enum field {field.get('name')} has no options")
        
        if errors:
            self.validation_errors.extend(errors)
            logger.error(f"Custom field validation failed: {', '.join(errors)}")
            return False
        
        return True
    
    def validate_migration_results(self, source_counts: Dict[str, int],
                                  target_counts: Dict[str, int]) -> Dict[str, Any]:
        """Validate migration results by comparing counts.
        
        Args:
            source_counts: Count of entities in Asana
            target_counts: Count of entities in Tallyfy
            
        Returns:
            Validation report
        """
        report = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'source_counts': source_counts,
            'target_counts': target_counts,
            'discrepancies': {},
            'errors': self.validation_errors,
            'warnings': self.validation_warnings
        }
        
        # Check for count mismatches
        for entity_type in source_counts:
            source_count = source_counts[entity_type]
            target_count = target_counts.get(entity_type, 0)
            
            if source_count != target_count:
                discrepancy = {
                    'source': source_count,
                    'target': target_count,
                    'difference': source_count - target_count,
                    'percentage': ((source_count - target_count) / source_count * 100) if source_count > 0 else 0
                }
                report['discrepancies'][entity_type] = discrepancy
                
                if discrepancy['percentage'] > 10:
                    report['status'] = 'warning'
                    logger.warning(f"Significant discrepancy in {entity_type}: {discrepancy['percentage']:.1f}% missing")
        
        # Check ID mappings if available
        if self.id_mapper:
            mapping_stats = self.id_mapper.get_statistics()
            report['mapping_statistics'] = mapping_stats
        
        # Set overall status
        if self.validation_errors:
            report['status'] = 'failed'
        elif report['discrepancies']:
            report['status'] = 'warning'
        
        return report
    
    def validate_blueprint(self, blueprint: Dict[str, Any]) -> bool:
        """Validate Tallyfy blueprint structure.
        
        Args:
            blueprint: Tallyfy blueprint object
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        if not blueprint.get('name'):
            errors.append("Blueprint missing name")
        
        if not blueprint.get('steps'):
            self.validation_warnings.append(f"Blueprint {blueprint.get('name')} has no steps")
        
        # Validate steps
        for idx, step in enumerate(blueprint.get('steps', [])):
            if not step.get('name'):
                errors.append(f"Step {idx + 1} missing name")
            
            if not step.get('type'):
                errors.append(f"Step {idx + 1} missing type")
            elif step['type'] not in ['task', 'approval', "text", 'email_draft']:
                self.validation_warnings.append(f"Step {idx + 1} has unknown type: {step['type']}")
        
        if errors:
            self.validation_errors.extend(errors)
            logger.error(f"Blueprint validation failed: {', '.join(errors)}")
            return False
        
        return True
    
    def validate_process(self, process: Dict[str, Any]) -> bool:
        """Validate Tallyfy process structure.
        
        Args:
            process: Tallyfy process object
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        if not process.get('checklist_id'):
            errors.append("Process missing checklist_id")
        
        if not process.get('name'):
            errors.append("Process missing name")
        
        # Validate tasks
        for task in process.get('tasks', []):
            if not task.get('name'):
                errors.append(f"Task in process missing name")
            
            if task.get('status') not in ['pending', 'in_progress', 'completed', 'skipped']:
                self.validation_warnings.append(f"Task has invalid status: {task.get('status')}")
        
        if errors:
            self.validation_errors.extend(errors)
            logger.error(f"Process validation failed: {', '.join(errors)}")
            return False
        
        return True
    
    def _calculate_task_depth(self, task: Dict[str, Any], depth: int = 0) -> int:
        """Calculate subtask depth recursively.
        
        Args:
            task: Task object
            depth: Current depth
            
        Returns:
            Maximum depth
        """
        if not task.get('parent'):
            return depth
        
        # Would need parent task data to continue recursion
        # For now, return current depth + 1
        return depth + 1
    
    def generate_validation_report(self) -> str:
        """Generate human-readable validation report.
        
        Returns:
            Formatted report string
        """
        report_lines = [
            "="*60,
            "MIGRATION VALIDATION REPORT",
            "="*60,
            f"Generated: {datetime.now().isoformat()}",
            ""
        ]
        
        if self.validation_errors:
            report_lines.extend([
                "ERRORS:",
                "-"*30
            ])
            for error in self.validation_errors:
                report_lines.append(f"❌ {error}")
            report_lines.append("")
        
        if self.validation_warnings:
            report_lines.extend([
                "WARNINGS:",
                "-"*30
            ])
            for warning in self.validation_warnings:
                report_lines.append(f"⚠️  {warning}")
            report_lines.append("")
        
        if not self.validation_errors and not self.validation_warnings:
            report_lines.append("✅ All validations passed successfully!")
        
        report_lines.extend([
            "",
            "="*60
        ])
        
        return "\n".join(report_lines)
    
    def clear_errors(self) -> None:
        """Clear validation errors and warnings."""
        self.validation_errors = []
        self.validation_warnings = []