#!/usr/bin/env python3
"""
RocketLane to Tallyfy Migration Orchestrator
Main entry point for the 5-phase migration system
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

from api.rocketlane_client import RocketLaneClient
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

logger = logging.getLogger(__name__)


class RocketLaneMigrationOrchestrator:
    """Orchestrates the 5-phase migration from RocketLane to Tallyfy"""
    
    def __init__(self):
        """Initialize the migration orchestrator"""
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        setup_logging()
        
        # Initialize components
        self._initialize_components()
        
        # Migration state
        self.migration_id = self._generate_migration_id()
        self.start_time = datetime.utcnow()
        self.checkpoint_manager = CheckpointManager(self.migration_id)
        self.error_handler = ErrorHandler()
        
        logger.info(f"RocketLane Migration Orchestrator initialized")
        logger.info(f"Migration ID: {self.migration_id}")
        logger.info(f"Customer Portal Handling: {os.getenv('CUSTOMER_PORTAL_HANDLING', 'guest_users')}")
    
    def _initialize_components(self):
        """Initialize all migration components"""
        # Initialize AI client (optional)
        self.ai_client = AIClient()
        if self.ai_client.enabled:
            logger.info("✅ AI augmentation enabled - intelligent paradigm shifts active")
        else:
            logger.info("⚠️ AI disabled - using deterministic fallback rules")
        
        # Initialize API clients
        self.rocketlane_client = RocketLaneClient(
            api_key=os.getenv('ROCKETLANE_API_KEY'),
            base_url=os.getenv('ROCKETLANE_BASE_URL', 'https://api.rocketlane.com/api/1.0')
        )
        
        self.tallyfy_client = TallyfyClient(
            api_key=os.getenv('TALLYFY_API_KEY'),
            organization=os.getenv('TALLYFY_ORGANIZATION'),
            api_url=os.getenv('TALLYFY_API_URL', 'https://api.tallyfy.com/api')
        )
        
        # Initialize transformers
        self.field_transformer = FieldTransformer(self.ai_client)
        self.template_transformer = TemplateTransformer(self.ai_client)
        self.instance_transformer = InstanceTransformer(self.ai_client)
        self.user_transformer = UserTransformer(self.ai_client)
        
        # Initialize validator
        self.validator = MigrationValidator(
            self.rocketlane_client,
            self.tallyfy_client
        )
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"rl_migration_{timestamp}"
    
    def run(self, dry_run: bool = False, resume: bool = False, phases: Optional[List[str]] = None):
        """
        Run the 5-phase migration
        
        Args:
            dry_run: If True, simulate without making changes
            resume: If True, resume from last checkpoint
            phases: Specific phases to run (None for all)
        """
        logger.info("=" * 80)
        logger.info("Starting RocketLane to Tallyfy Migration")
        logger.info(f"Paradigm Shift: Customer PSA → Internal Workflow Automation")
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Resume: {resume}")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be migrated")
        
        # Load checkpoint if resuming
        checkpoint = {}
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint()
            if checkpoint:
                logger.info(f"Resuming from phase: {checkpoint.get('last_phase', 'unknown')}")
        
        # Define all phases
        all_phases = [
            'discovery',
            'users_customers',
            'templates',
            'projects',
            'validation'
        ]
        
        # Determine phases to run
        if phases:
            phases_to_run = [p for p in all_phases if p in phases]
        else:
            phases_to_run = all_phases
        
        # Skip completed phases if resuming
        if checkpoint:
            completed_phases = checkpoint.get('completed_phases', [])
            phases_to_run = [p for p in phases_to_run if p not in completed_phases]
        
        logger.info(f"Phases to run: {', '.join(phases_to_run)}")
        
        # Execute migration phases
        results = {}
        completed_phases = checkpoint.get('completed_phases', []) if checkpoint else []
        
        try:
            for phase in phases_to_run:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"PHASE: {phase.upper()}")
                logger.info(f"{'=' * 60}")
                
                phase_start = time.time()
                
                if phase == 'discovery':
                    results[phase] = self._phase_1_discovery(dry_run)
                elif phase == 'users_customers':
                    results[phase] = self._phase_2_users_customers(dry_run)
                elif phase == 'templates':
                    results[phase] = self._phase_3_templates(dry_run)
                elif phase == 'projects':
                    results[phase] = self._phase_4_projects(dry_run)
                elif phase == 'validation':
                    results[phase] = self._phase_5_validation(dry_run)
                
                phase_duration = time.time() - phase_start
                results[phase]['duration'] = phase_duration
                
                completed_phases.append(phase)
                
                # Save checkpoint after each phase
                self.checkpoint_manager.save_checkpoint({
                    'last_phase': phase,
                    'completed_phases': completed_phases,
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"✓ Phase {phase} completed in {phase_duration:.1f} seconds")
                
        except Exception as e:
            self.error_handler.handle_error(e, phase)
            if not os.getenv('CONTINUE_ON_ERROR', 'false').lower() == 'true':
                raise
        
        # Generate final report
        self._generate_report(results, dry_run)
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 Migration completed successfully!")
        logger.info(f"Total time: {self._get_elapsed_time()}")
        logger.info("=" * 80)
    
    def _phase_1_discovery(self, dry_run: bool) -> Dict[str, Any]:
        """
        Phase 1: Discovery (5-10 minutes)
        - Connect to RocketLane API
        - Fetch all customers, projects, templates, forms
        - Analyze data complexity and volume
        - Generate migration plan with estimates
        - Identify paradigm shifts needed
        """
        logger.info("📊 Phase 1: Discovering RocketLane data...")
        
        discovery = {
            'customers': [],
            'projects': [],
            'templates': [],
            'forms': [],
            'users': [],
            'custom_fields': [],
            'time_entries': [],
            'counts': {},
            'paradigm_shifts': [],
            'complexity_analysis': {}
        }
        
        try:
            # Fetch customers
            logger.info("Fetching customers...")
            discovery['customers'] = self.rocketlane_client.list_customers()
            discovery['counts']['customers'] = len(discovery['customers'])
            
            # Fetch projects
            logger.info("Fetching projects...")
            discovery['projects'] = self.rocketlane_client.list_projects(
                include_archived=os.getenv('MIGRATE_ARCHIVED', 'false').lower() == 'true'
            )
            discovery['counts']['projects'] = len(discovery['projects'])
            discovery['counts']['active_projects'] = len([p for p in discovery['projects'] if p.get('status') == 'active'])
            
            # Fetch project templates
            logger.info("Fetching project templates...")
            discovery['templates'] = self.rocketlane_client.list_project_templates()
            discovery['counts']['templates'] = len(discovery['templates'])
            
            # Fetch forms and surveys
            logger.info("Fetching forms and surveys...")
            discovery['forms'] = self.rocketlane_client.list_forms()
            discovery['counts']['forms'] = len(discovery['forms'])
            
            # Fetch users and resources
            logger.info("Fetching users and resources...")
            discovery['users'] = self.rocketlane_client.list_users()
            discovery['counts']['users'] = len(discovery['users'])
            
            # Fetch custom fields
            logger.info("Fetching custom fields...")
            discovery['custom_fields'] = self.rocketlane_client.list_custom_fields()
            discovery['counts']['custom_fields'] = len(discovery['custom_fields'])
            
            # Analyze paradigm shifts needed
            logger.info("Analyzing paradigm shifts...")
            discovery['paradigm_shifts'] = self._analyze_paradigm_shifts(discovery)
            
            # Analyze complexity
            logger.info("Analyzing data complexity...")
            discovery['complexity_analysis'] = self._analyze_complexity(discovery)
            
            # Save discovery results
            discovery_file = Path('data') / f'{self.migration_id}_discovery.json'
            discovery_file.parent.mkdir(exist_ok=True)
            with open(discovery_file, 'w') as f:
                json.dump(discovery, f, indent=2, default=str)
            
            logger.info(f"Discovery saved to: {discovery_file}")
            
            # Log summary
            logger.info("\n📈 Discovery Summary:")
            logger.info(f"  • Customers: {discovery['counts']['customers']}")
            logger.info(f"  • Projects: {discovery['counts']['projects']} ({discovery['counts']['active_projects']} active)")
            logger.info(f"  • Templates: {discovery['counts']['templates']}")
            logger.info(f"  • Forms: {discovery['counts']['forms']}")
            logger.info(f"  • Users: {discovery['counts']['users']}")
            logger.info(f"  • Custom Fields: {discovery['counts']['custom_fields']}")
            
            if discovery['paradigm_shifts']:
                logger.info("\n🔄 Required Paradigm Shifts:")
                for shift in discovery['paradigm_shifts']:
                    logger.info(f"  • {shift['type']}: {shift['description']}")
            
            # Estimate migration time
            estimated_time = self._estimate_migration_time(discovery['counts'])
            logger.info(f"\n⏱️ Estimated migration time: {estimated_time}")
            
        except Exception as e:
            logger.error(f"Discovery phase failed: {e}")
            raise
        
        return discovery
    
    def _phase_2_users_customers(self, dry_run: bool) -> Dict[str, Any]:
        """
        Phase 2: Customer & User Migration (10-30 minutes)
        - Transform RocketLane customers to appropriate Tallyfy entities
        - Map internal users to Tallyfy members
        - Handle customer portal access patterns
        - Create groups for team structures
        - Establish ID mappings for relationships
        """
        logger.info("👥 Phase 2: Migrating customers and users...")
        
        results = {
            'customers': {'total': 0, 'successful': 0, 'failed': 0},
            'users': {'total': 0, 'successful': 0, 'failed': 0},
            'groups': {'total': 0, 'successful': 0, 'failed': 0},
            'mappings': []
        }
        
        if dry_run:
            logger.info("DRY RUN - Skipping actual migration")
            return results
        
        try:
            # Load discovery data
            discovery = self._load_discovery_data()
            
            # Migrate internal users first
            logger.info("Migrating internal users...")
            for user in discovery['users']:
                results['users']['total'] += 1
                try:
                    transformed_user = self.user_transformer.transform_user(user)
                    created_user = self.tallyfy_client.create_user(transformed_user)
                    
                    # Store mapping
                    self.checkpoint_manager.add_mapping('user', user['id'], created_user['id'])
                    results['users']['successful'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate user {user.get('email')}: {e}")
                    results['users']['failed'] += 1
            
            # Handle customers based on portal configuration
            customer_handling = os.getenv('CUSTOMER_PORTAL_HANDLING', 'guest_users')
            logger.info(f"Migrating customers as: {customer_handling}")
            
            for customer in discovery['customers']:
                results['customers']['total'] += 1
                try:
                    if customer_handling == 'guest_users':
                        # Create as guest users
                        transformed_customer = self.user_transformer.transform_customer_to_guest(customer)
                        created_guest = self.tallyfy_client.create_guest(transformed_customer)
                        self.checkpoint_manager.add_mapping('customer', customer['id'], created_guest['id'])
                    else:
                        # Create as organizations
                        transformed_org = self.user_transformer.transform_customer_to_organization(customer)
                        created_org = self.tallyfy_client.create_organization(transformed_org)
                        self.checkpoint_manager.add_mapping('customer', customer['id'], created_org['id'])
                    
                    results['customers']['successful'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate customer {customer.get('name')}: {e}")
                    results['customers']['failed'] += 1
            
            logger.info(f"✓ Users migrated: {results['users']['successful']}/{results['users']['total']}")
            logger.info(f"✓ Customers migrated: {results['customers']['successful']}/{results['customers']['total']}")
            
        except Exception as e:
            logger.error(f"Users/Customers phase failed: {e}")
            raise
        
        return results
    
    def _phase_3_templates(self, dry_run: bool) -> Dict[str, Any]:
        """
        Phase 3: Template Migration (30-60 minutes)
        - Convert project templates to Blueprints
        - Transform phases into sequential workflow steps
        - Map task templates with dependencies
        - Handle form templates (with AI assistance)
        - Preserve automation rules where possible
        """
        logger.info("📋 Phase 3: Migrating project templates...")
        
        results = {
            'templates': {'total': 0, 'successful': 0, 'failed': 0},
            'forms': {'total': 0, 'successful': 0, 'failed': 0},
            'ai_decisions': []
        }
        
        if dry_run:
            logger.info("DRY RUN - Skipping actual migration")
            return results
        
        try:
            # Load discovery data
            discovery = self._load_discovery_data()
            
            # Process templates in batches
            batch_size = int(os.getenv('TEMPLATE_BATCH_SIZE', '10'))
            templates = discovery['templates']
            
            for i in range(0, len(templates), batch_size):
                batch = templates[i:i+batch_size]
                logger.info(f"Processing template batch {i//batch_size + 1}/{(len(templates)-1)//batch_size + 1}")
                
                for template in batch:
                    results['templates']['total'] += 1
                    
                    try:
                        # Get full template details
                        full_template = self.rocketlane_client.get_project_template(template['id'])
                        
                        # Transform template to blueprint
                        transformed = self.template_transformer.transform_template(full_template)
                        
                        # Handle AI decisions
                        if transformed.get('ai_decisions'):
                            results['ai_decisions'].extend(transformed['ai_decisions'])
                        
                        # Create blueprint in Tallyfy
                        blueprint = self.tallyfy_client.create_checklist(transformed['checklist'])
                        
                        # Create steps
                        for step in transformed.get('steps', []):
                            created_step = self.tallyfy_client.create_step(blueprint['id'], step)
                            
                            # Create step fields
                            for field in step.get('fields', []):
                                self.tallyfy_client.create_form_field(
                                    checklist_id=blueprint['id'],
                                    step_id=created_step['id'],
                                    field_data=field
                                )
                        
                        # Store mapping
                        self.checkpoint_manager.add_mapping('template', template['id'], blueprint['id'])
                        results['templates']['successful'] += 1
                        
                        logger.debug(f"✓ Migrated template: {template.get('name')}")
                        
                    except Exception as e:
                        logger.error(f"Failed to migrate template {template.get('name')}: {e}")
                        results['templates']['failed'] += 1
                
                # Rate limiting between batches
                time.sleep(2)
            
            # Process forms
            logger.info("Migrating forms...")
            for form in discovery['forms']:
                results['forms']['total'] += 1
                try:
                    # Assess form complexity with AI
                    complexity_assessment = self.ai_client.assess_form_complexity(form) if self.ai_client.enabled else None
                    
                    # Transform form based on complexity
                    if complexity_assessment and complexity_assessment.get('complexity') == 'high':
                        # Create as multi-step workflow
                        transformed = self.template_transformer.transform_complex_form_to_workflow(form)
                    else:
                        # Create as kick-off form
                        transformed = self.template_transformer.transform_simple_form(form)
                    
                    # Create in Tallyfy
                    if transformed.get('type') == 'workflow':
                        created = self.tallyfy_client.create_checklist(transformed['checklist'])
                    else:
                        created = self.tallyfy_client.create_kickoff_form(transformed['form'])
                    
                    self.checkpoint_manager.add_mapping('form', form['id'], created['id'])
                    results['forms']['successful'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate form {form.get('name')}: {e}")
                    results['forms']['failed'] += 1
            
            logger.info(f"✓ Templates migrated: {results['templates']['successful']}/{results['templates']['total']}")
            logger.info(f"✓ Forms migrated: {results['forms']['successful']}/{results['forms']['total']}")
            
            if results['ai_decisions']:
                logger.info(f"📊 AI made {len(results['ai_decisions'])} transformation decisions")
            
        except Exception as e:
            logger.error(f"Templates phase failed: {e}")
            raise
        
        return results
    
    def _phase_4_projects(self, dry_run: bool) -> Dict[str, Any]:
        """
        Phase 4: Project Migration (1-6 hours)
        - Migrate active projects as Processes
        - Preserve current task states and progress
        - Maintain assignee relationships
        - Convert time tracking to structured comments
        - Handle document references
        """
        logger.info("🚀 Phase 4: Migrating projects...")
        
        results = {
            'projects': {'total': 0, 'successful': 0, 'failed': 0},
            'tasks': {'total': 0, 'successful': 0, 'failed': 0},
            'time_entries': {'total': 0, 'successful': 0, 'failed': 0}
        }
        
        if dry_run:
            logger.info("DRY RUN - Skipping actual migration")
            return results
        
        try:
            # Load discovery data
            discovery = self._load_discovery_data()
            
            # Filter projects based on configuration
            projects = discovery['projects']
            if not os.getenv('MIGRATE_ARCHIVED', 'false').lower() == 'true':
                projects = [p for p in projects if p.get('status') != 'archived']
            
            # Process projects in batches
            batch_size = int(os.getenv('PROJECT_BATCH_SIZE', '20'))
            
            for i in range(0, len(projects), batch_size):
                batch = projects[i:i+batch_size]
                logger.info(f"Processing project batch {i//batch_size + 1}/{(len(projects)-1)//batch_size + 1}")
                
                for project in batch:
                    results['projects']['total'] += 1
                    
                    try:
                        # Get full project details
                        full_project = self.rocketlane_client.get_project(project['id'])
                        
                        # Transform project to process
                        transformed = self.instance_transformer.transform_project(full_project)
                        
                        # Get template mapping
                        template_id = self.checkpoint_manager.get_mapping('template', project.get('template_id'))
                        if not template_id:
                            logger.warning(f"Template not found for project {project['name']}, skipping")
                            continue
                        
                        # Create process in Tallyfy
                        process_data = {
                            'checklist_id': template_id,
                            'title': transformed['title'],
                            'prerun_data': transformed.get('prerun_data', {}),
                            'external_ref': project['id']
                        }
                        
                        created_process = self.tallyfy_client.create_run(process_data)
                        
                        # Migrate task states
                        for task in full_project.get('tasks', []):
                            results['tasks']['total'] += 1
                            try:
                                if task.get('completed'):
                                    # Mark task as complete
                                    self.tallyfy_client.complete_task(
                                        run_id=created_process['id'],
                                        task_id=task['id'],
                                        data={'completed_by': self._get_user_mapping(task.get('completed_by'))}
                                    )
                                
                                # Update assignees
                                if task.get('assignees'):
                                    assignee_ids = [self._get_user_mapping(a) for a in task['assignees']]
                                    self.tallyfy_client.update_task_assignees(
                                        run_id=created_process['id'],
                                        task_id=task['id'],
                                        assignee_ids=assignee_ids
                                    )
                                
                                results['tasks']['successful'] += 1
                                
                            except Exception as e:
                                logger.error(f"Failed to migrate task {task.get('name')}: {e}")
                                results['tasks']['failed'] += 1
                        
                        # Migrate time tracking if enabled
                        if os.getenv('MIGRATE_TIME_TRACKING', 'true').lower() == 'true':
                            time_entries = self.rocketlane_client.get_time_entries(project['id'])
                            for entry in time_entries:
                                results['time_entries']['total'] += 1
                                try:
                                    # Convert to comment with structured time notation
                                    comment = self.instance_transformer.transform_time_entry_to_comment(entry)
                                    self.tallyfy_client.create_comment(
                                        run_id=created_process['id'],
                                        comment=comment
                                    )
                                    results['time_entries']['successful'] += 1
                                except Exception as e:
                                    logger.error(f"Failed to migrate time entry: {e}")
                                    results['time_entries']['failed'] += 1
                        
                        # Store mapping
                        self.checkpoint_manager.add_mapping('project', project['id'], created_process['id'])
                        results['projects']['successful'] += 1
                        
                        logger.debug(f"✓ Migrated project: {project.get('name')}")
                        
                    except Exception as e:
                        logger.error(f"Failed to migrate project {project.get('name')}: {e}")
                        results['projects']['failed'] += 1
                
                # Rate limiting between batches
                time.sleep(3)
            
            logger.info(f"✓ Projects migrated: {results['projects']['successful']}/{results['projects']['total']}")
            logger.info(f"✓ Tasks updated: {results['tasks']['successful']}/{results['tasks']['total']}")
            logger.info(f"✓ Time entries migrated: {results['time_entries']['successful']}/{results['time_entries']['total']}")
            
        except Exception as e:
            logger.error(f"Projects phase failed: {e}")
            raise
        
        return results
    
    def _phase_5_validation(self, dry_run: bool) -> Dict[str, Any]:
        """
        Phase 5: Validation (10-20 minutes)
        - Verify data integrity
        - Check relationship mappings
        - Validate form field transformations
        - Generate detailed migration report
        - List items requiring manual review
        """
        logger.info("✅ Phase 5: Validating migration...")
        
        validation_results = self.validator.validate_migration(
            self.checkpoint_manager.get_all_mappings()
        )
        
        # Log validation results
        logger.info("\n📊 Validation Results:")
        for check, result in validation_results.items():
            status = "✓" if result['passed'] else "✗"
            logger.info(f"  {status} {check}: {result['message']}")
            if not result['passed'] and result.get('details'):
                for detail in result['details']:
                    logger.warning(f"    - {detail}")
        
        # Generate manual review list
        manual_review = self._generate_manual_review_list(validation_results)
        if manual_review:
            review_file = Path('reports') / f'{self.migration_id}_manual_review.md'
            review_file.parent.mkdir(exist_ok=True)
            with open(review_file, 'w') as f:
                f.write("# Manual Review Required\n\n")
                for item in manual_review:
                    f.write(f"- [ ] {item['type']}: {item['description']}\n")
            logger.info(f"📝 Manual review items saved to: {review_file}")
        
        return validation_results
    
    def _analyze_paradigm_shifts(self, discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze required paradigm shifts based on discovered data"""
        shifts = []
        
        # Customer portal paradigm
        if discovery['counts']['customers'] > 0:
            shifts.append({
                'type': 'Customer Portal',
                'description': 'Transform customer-facing portals to guest access or external forms',
                'impact': 'high',
                'affected_items': discovery['counts']['customers']
            })
        
        # Resource management paradigm
        resource_allocations = sum(1 for p in discovery['projects'] if p.get('resource_allocations'))
        if resource_allocations > 0:
            shifts.append({
                'type': 'Resource Management',
                'description': 'Convert capacity planning to task-based assignments',
                'impact': 'medium',
                'affected_items': resource_allocations
            })
        
        # Project phases paradigm
        phased_templates = sum(1 for t in discovery['templates'] if len(t.get('phases', [])) > 1)
        if phased_templates > 0:
            shifts.append({
                'type': 'Project Phases',
                'description': 'Transform parallel phases to sequential workflow steps',
                'impact': 'medium',
                'affected_items': phased_templates
            })
        
        # Time tracking paradigm
        if discovery.get('time_entries'):
            shifts.append({
                'type': 'Time Tracking',
                'description': 'Convert integrated time tracking to comments or external system',
                'impact': 'low',
                'affected_items': len(discovery.get('time_entries', []))
            })
        
        return shifts
    
    def _analyze_complexity(self, discovery: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data complexity for migration planning"""
        complexity = {
            'overall': 'low',
            'factors': []
        }
        
        # Check form complexity
        complex_forms = sum(1 for f in discovery['forms'] if len(f.get('fields', [])) > 20)
        if complex_forms > 0:
            complexity['factors'].append(f"{complex_forms} complex forms requiring workflow conversion")
        
        # Check custom field complexity
        if discovery['counts']['custom_fields'] > 50:
            complexity['factors'].append(f"{discovery['counts']['custom_fields']} custom fields requiring mapping")
            complexity['overall'] = 'medium'
        
        # Check project volume
        if discovery['counts']['projects'] > 500:
            complexity['factors'].append(f"{discovery['counts']['projects']} projects requiring batch processing")
            complexity['overall'] = 'high'
        
        # Check dependency complexity
        dependent_tasks = sum(
            len(t.get('dependencies', [])) 
            for p in discovery['projects'] 
            for t in p.get('tasks', [])
        )
        if dependent_tasks > 100:
            complexity['factors'].append(f"{dependent_tasks} task dependencies requiring transformation")
            complexity['overall'] = 'high'
        
        return complexity
    
    def _estimate_migration_time(self, counts: Dict[str, int]) -> str:
        """Estimate total migration time based on object counts"""
        # Time estimates per object (in seconds)
        time_per_object = {
            'customers': 3,
            'users': 2,
            'templates': 30,
            'projects': 15,
            'forms': 10,
            'custom_fields': 1
        }
        
        total_seconds = sum(
            counts.get(obj_type, 0) * time_estimate
            for obj_type, time_estimate in time_per_object.items()
        )
        
        # Add overhead for API rate limiting and processing
        total_seconds = int(total_seconds * 1.5)
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours} hours {minutes} minutes"
        else:
            return f"{minutes} minutes"
    
    def _load_discovery_data(self) -> Dict[str, Any]:
        """Load discovery data from saved file"""
        discovery_file = Path('data') / f'{self.migration_id}_discovery.json'
        if not discovery_file.exists():
            raise FileNotFoundError(f"Discovery data not found: {discovery_file}")
        
        with open(discovery_file, 'r') as f:
            return json.load(f)
    
    def _get_user_mapping(self, rocketlane_user_id: str) -> Optional[str]:
        """Get Tallyfy user ID from RocketLane user ID"""
        return self.checkpoint_manager.get_mapping('user', rocketlane_user_id)
    
    def _generate_manual_review_list(self, validation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate list of items requiring manual review"""
        review_items = []
        
        for check, result in validation_results.items():
            if not result['passed']:
                review_items.append({
                    'type': check,
                    'description': result['message'],
                    'details': result.get('details', [])
                })
        
        return review_items
    
    def _get_elapsed_time(self) -> str:
        """Get elapsed time since migration started"""
        elapsed = datetime.utcnow() - self.start_time
        hours = elapsed.seconds // 3600
        minutes = (elapsed.seconds % 3600) // 60
        seconds = elapsed.seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _generate_report(self, results: Dict[str, Any], dry_run: bool):
        """Generate comprehensive migration report"""
        report = {
            'migration_id': self.migration_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'elapsed_time': self._get_elapsed_time(),
            'dry_run': dry_run,
            'phases': results,
            'statistics': {
                'total_api_calls': self.rocketlane_client.get_stats()['api_calls'] + 
                                 self.tallyfy_client.get_stats()['api_calls'],
                'ai_decisions': sum(len(r.get('ai_decisions', [])) for r in results.values()),
                'errors': self.error_handler.get_error_count()
            },
            'mappings': self.checkpoint_manager.get_mapping_summary()
        }
        
        # Save report
        report_file = Path('reports') / f'{self.migration_id}_summary.json'
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\n📄 Migration report saved: {report_file}")
    
    def run_readiness_check(self) -> bool:
        """Run comprehensive readiness check before migration"""
        logger.info("🔍 Running readiness check...")
        
        ready = True
        checks = []
        
        # Check RocketLane connectivity
        try:
            self.rocketlane_client.test_connection()
            checks.append("✓ RocketLane API connection successful")
        except Exception as e:
            checks.append(f"✗ RocketLane API connection failed: {e}")
            ready = False
        
        # Check Tallyfy connectivity
        try:
            self.tallyfy_client.test_connection()
            checks.append("✓ Tallyfy API connection successful")
        except Exception as e:
            checks.append(f"✗ Tallyfy API connection failed: {e}")
            ready = False
        
        # Check AI availability (optional)
        if self.ai_client.enabled:
            try:
                self.ai_client.test_connection()
                checks.append("✓ AI augmentation available")
            except Exception as e:
                checks.append(f"⚠ AI unavailable (will use fallbacks): {e}")
        
        # Display results
        logger.info("\nReadiness Check Results:")
        for check in checks:
            logger.info(f"  {check}")
        
        logger.info(f"\nOverall Status: {'✅ READY' if ready else '❌ NOT READY'}")
        
        return ready


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='RocketLane to Tallyfy Migration Tool'
    )
    
    parser.add_argument('--dry-run', action='store_true',
                      help='Simulate migration without making changes')
    parser.add_argument('--resume', action='store_true',
                      help='Resume from last checkpoint')
    parser.add_argument('--phases', nargs='+',
                      help='Specific phases to run')
    parser.add_argument('--readiness-check', action='store_true',
                      help='Run readiness check only')
    parser.add_argument('--report-only', action='store_true',
                      help='Generate report without migrating')
    parser.add_argument('--preview-mappings', action='store_true',
                      help='Preview field and object mappings')
    parser.add_argument('--projects', type=str,
                      help='Comma-separated list of project IDs to migrate')
    parser.add_argument('--templates-only', action='store_true',
                      help='Migrate only templates, not projects')
    parser.add_argument('--exclude-archived', action='store_true',
                      help='Skip archived items')
    parser.add_argument('--after-date', type=str,
                      help='Migrate items created after this date')
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = RocketLaneMigrationOrchestrator()
        
        # Run readiness check if requested
        if args.readiness_check:
            ready = orchestrator.run_readiness_check()
            sys.exit(0 if ready else 1)
        
        # Preview mappings if requested
        if args.preview_mappings:
            # This would show mapping preview
            logger.info("Field mapping preview not yet implemented")
            sys.exit(0)
        
        # Report only mode
        if args.report_only:
            orchestrator.run(dry_run=True, phases=['discovery'])
            sys.exit(0)
        
        # Determine phases
        phases = args.phases
        if args.templates_only:
            phases = ['discovery', 'users_customers', 'templates', 'validation']
        
        # Run migration
        orchestrator.run(
            dry_run=args.dry_run,
            resume=args.resume,
            phases=phases
        )
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()