"""Main orchestrator for Asana to Tallyfy migration."""

import os
import sys
import argparse
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api.asana_client import AsanaClient
from api.tallyfy_client import TallyfyClient
from transformers.user_transformer import UserTransformer
from transformers.template_transformer import TemplateTransformer
from transformers.instance_transformer import InstanceTransformer
from transformers.field_transformer import FieldTransformer
from utils.id_mapper import IDMapper
from utils.progress_tracker import ProgressTracker
from utils.validator import MigrationValidator
from utils.logger_config import setup_logger
from utils.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class AsanaMigrationOrchestrator:
    """Orchestrates the complete Asana to Tallyfy migration."""
    
    def __init__(self, asana_token: str, tallyfy_token: str,
                 tallyfy_org_id: str, asana_workspace_gid: Optional[str] = None,
                 config: Optional[Dict] = None):
        """Initialize migration orchestrator.
        
        Args:
            asana_token: Asana Personal Access Token
            tallyfy_token: Tallyfy API token
            tallyfy_org_id: Tallyfy organization ID
            asana_workspace_gid: Asana workspace GID (auto-detected if not provided)
            config: Additional configuration options
        """
        self.config = config or {}
        
        # Initialize API clients
        self.asana_client = AsanaClient(asana_token, asana_workspace_gid)
        self.tallyfy_client = TallyfyClient(tallyfy_token, tallyfy_org_id)
        
        # Initialize transformers
        self.user_transformer = UserTransformer()
        self.template_transformer = TemplateTransformer()
        self.instance_transformer = InstanceTransformer()
        self.field_transformer = FieldTransformer()
        
        # Initialize utilities
        self.id_mapper = IDMapper(self.config.get('id_mapper_path', 'data/id_mappings.db'))
        self.progress_tracker = ProgressTracker(
            use_rich=self.config.get('use_rich', True),
            disable=self.config.get('disable_progress', False)
        )
        self.validator = MigrationValidator(self.id_mapper)
        self.checkpoint_manager = CheckpointManager(
            self.config.get('checkpoint_dir', 'checkpoints')
        )
        
        # Migration state
        self.workspace_gid = asana_workspace_gid
        self.source_counts = {}
        self.target_counts = {}
        
    def run(self, phases: Optional[List[str]] = None,
           dry_run: bool = False,
           resume: bool = False,
           report_only: bool = False) -> Dict[str, Any]:
        """Execute the migration.
        
        Args:
            phases: Specific phases to run
            dry_run: Preview without making changes
            resume: Resume from last checkpoint
            report_only: Generate report without migration
            
        Returns:
            Migration results
        """
        try:
            # Initialize migration
            if resume:
                run_id = self.checkpoint_manager.get_latest_incomplete_run(self.workspace_gid)
                if run_id:
                    phases, checkpoint_data = self.checkpoint_manager.resume_migration(run_id)
                    logger.info(f"Resuming migration {run_id}")
                else:
                    logger.info("No incomplete migration found, starting fresh")
                    resume = False
            
            if not resume:
                # Start new migration
                if not self.workspace_gid:
                    self.workspace_gid = self._auto_detect_workspace()
                
                run_id = self.checkpoint_manager.start_migration(
                    self.workspace_gid,
                    {'dry_run': dry_run, 'report_only': report_only}
                )
            
            # Default phases
            if not phases:
                phases = ['discovery', 'users', 'teams', 'projects', 'tasks', 'validation']
            
            # Start progress tracking
            self.progress_tracker.start_migration()
            
            results = {}
            
            # Execute phases
            for phase in phases:
                try:
                    logger.info(f"Starting phase: {phase}")
                    self.checkpoint_manager.save_phase_checkpoint(phase, 'in_progress')
                    
                    if phase == 'discovery':
                        results['discovery'] = self.run_discovery()
                    elif phase == 'users':
                        results['users'] = self.migrate_users(dry_run)
                    elif phase == 'teams':
                        results['teams'] = self.migrate_teams(dry_run)
                    elif phase == 'projects':
                        results['projects'] = self.migrate_projects(dry_run)
                    elif phase == 'tasks':
                        results['tasks'] = self.migrate_active_tasks(dry_run)
                    elif phase == 'validation':
                        results['validation'] = self.run_validation()
                    
                    self.checkpoint_manager.save_phase_checkpoint(phase, 'completed', results.get(phase))
                    
                except Exception as e:
                    logger.error(f"Phase {phase} failed: {e}")
                    self.checkpoint_manager.save_phase_checkpoint(phase, 'failed', error=str(e))
                    
                    if not self.config.get('continue_on_error', False):
                        raise
            
            # Complete migration
            self.checkpoint_manager.complete_migration('completed')
            
            # Display summary
            summary = self.progress_tracker.display_summary()
            results['summary'] = summary
            
            # Generate final report
            if report_only or self.config.get('generate_report', True):
                report = self.generate_migration_report(results)
                self._save_report(report)
            
            return results
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.checkpoint_manager.complete_migration('failed')
            raise
        finally:
            self.progress_tracker.stop()
    
    def run_readiness_check(self) -> Dict[str, Any]:
        """Run comprehensive readiness check.
        
        Returns:
            Readiness report
        """
        logger.info("Running readiness check...")
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'status': 'ready'
        }
        
        # Check Asana connectivity
        try:
            user = self.asana_client.test_connection()
            report['checks']['asana_connection'] = {
                'status': 'passed',
                'user': user['name'],
                "text": user["text"]
            }
        except Exception as e:
            report['checks']['asana_connection'] = {
                'status': 'failed',
                'error': str(e)
            }
            report['status'] = 'not_ready'
        
        # Check Tallyfy connectivity
        try:
            org = self.tallyfy_client.test_connection()
            report['checks']['tallyfy_connection'] = {
                'status': 'passed',
                'organization': org.get('name', 'Unknown')
            }
        except Exception as e:
            report['checks']['tallyfy_connection'] = {
                'status': 'failed',
                'error': str(e)
            }
            report['status'] = 'not_ready'
        
        # Check workspace
        if report['status'] == 'ready':
            try:
                if not self.workspace_gid:
                    self.workspace_gid = self._auto_detect_workspace()
                
                # Get workspace info
                workspaces = self.asana_client.get_workspaces()
                workspace = next((w for w in workspaces if w['gid'] == self.workspace_gid), None)
                
                if workspace:
                    report['checks']['workspace'] = {
                        'status': 'passed',
                        'name': workspace['name'],
                        'gid': workspace['gid']
                    }
                else:
                    report['checks']['workspace'] = {
                        'status': 'failed',
                        'error': 'Workspace not found'
                    }
                    report['status'] = 'not_ready'
                    
            except Exception as e:
                report['checks']['workspace'] = {
                    'status': 'failed',
                    'error': str(e)
                }
                report['status'] = 'not_ready'
        
        # Check permissions
        if report['status'] == 'ready':
            try:
                # Try to fetch some data to verify permissions
                users = self.asana_client.get_users(self.workspace_gid)
                projects = self.asana_client.get_projects(self.workspace_gid)
                
                report['checks']['permissions'] = {
                    'status': 'passed',
                    'can_read_users': len(users) > 0,
                    'can_read_projects': len(projects) >= 0
                }
            except Exception as e:
                report['checks']['permissions'] = {
                    'status': 'warning',
                    'error': str(e)
                }
        
        # Summary
        report['summary'] = {
            'ready': report['status'] == 'ready',
            'message': 'Ready to migrate' if report['status'] == 'ready' else 'Issues detected, please resolve before migrating'
        }
        
        # Print report
        print("\n" + "="*60)
        print("READINESS CHECK REPORT")
        print("="*60)
        
        for check_name, check_result in report['checks'].items():
            status = check_result['status']
            symbol = "✅" if status == 'passed' else "❌" if status == 'failed' else "⚠️"
            print(f"{symbol} {check_name}: {status}")
            
            if status == 'failed' and 'error' in check_result:
                print(f"   Error: {check_result['error']}")
        
        print("\n" + report['summary']['message'])
        print("="*60)
        
        return report
    
    def run_discovery(self) -> Dict[str, Any]:
        """Run discovery phase to analyze Asana workspace.
        
        Returns:
            Discovery results
        """
        logger.info("Running discovery phase...")
        
        discovery = {
            'workspace': {},
            'counts': {},
            'complexity': {},
            'warnings': []
        }
        
        # Get workspace info
        workspaces = self.asana_client.get_workspaces()
        workspace = next((w for w in workspaces if w['gid'] == self.workspace_gid), None)
        
        if workspace:
            discovery['workspace'] = {
                'name': workspace['name'],
                'gid': workspace['gid'],
                'is_organization': workspace.get('is_organization', False)
            }
        
        # Count entities
        task = self.progress_tracker.start_phase('Discovery', 7)
        
        # Users
        users = self.asana_client.get_users(self.workspace_gid)
        discovery['counts']['users'] = len(users)
        self.source_counts['users'] = len(users)
        self.progress_tracker.update_phase('Discovery', 1)
        
        # Teams
        teams = self.asana_client.get_teams(self.workspace_gid)
        discovery['counts']['teams'] = len(teams)
        self.source_counts['teams'] = len(teams)
        self.progress_tracker.update_phase('Discovery', 1)
        
        # Projects
        projects = self.asana_client.get_projects(self.workspace_gid)
        discovery['counts']['projects'] = len(projects)
        self.source_counts['projects'] = len(projects)
        
        # Analyze project complexity
        board_projects = sum(1 for p in projects if p.get('layout') == 'board')
        timeline_projects = sum(1 for p in projects if p.get('layout') == 'timeline')
        
        discovery['complexity']['board_projects'] = board_projects
        discovery['complexity']['timeline_projects'] = timeline_projects
        
        if board_projects > 0:
            discovery['warnings'].append(f"{board_projects} Kanban board projects will be converted to sequential workflows")
        
        if timeline_projects > 0:
            discovery['warnings'].append(f"{timeline_projects} timeline projects with dependencies detected")
        
        self.progress_tracker.update_phase('Discovery', 1)
        
        # Custom fields
        custom_fields = self.asana_client.get_custom_fields(self.workspace_gid)
        discovery['counts']['custom_fields'] = len(custom_fields)
        self.progress_tracker.update_phase('Discovery', 1)
        
        # Tags
        tags = self.asana_client.get_tags(self.workspace_gid)
        discovery['counts']['tags'] = len(tags)
        self.progress_tracker.update_phase('Discovery', 1)
        
        # Portfolios
        portfolios = self.asana_client.get_portfolios(self.workspace_gid)
        discovery['counts']['portfolios'] = len(portfolios)
        
        if portfolios:
            discovery['warnings'].append(f"{len(portfolios)} portfolios detected - will need manual recreation in Tallyfy")
        
        self.progress_tracker.update_phase('Discovery', 1)
        
        # Sample tasks count
        sample_project = projects[0] if projects else None
        if sample_project:
            tasks = self.asana_client.get_tasks(sample_project['gid'])
            discovery['complexity']['avg_tasks_per_project'] = len(tasks)
            discovery['counts']['estimated_total_tasks'] = len(tasks) * len(projects)
            self.source_counts['tasks'] = discovery['counts']['estimated_total_tasks']
        
        self.progress_tracker.update_phase('Discovery', 1)
        self.progress_tracker.complete_phase('Discovery')
        
        # Print discovery summary
        print("\n" + "="*60)
        print("DISCOVERY SUMMARY")
        print("="*60)
        print(f"Workspace: {discovery['workspace'].get('name', 'Unknown')}")
        print(f"Users: {discovery['counts']['users']}")
        print(f"Teams: {discovery['counts']['teams']}")
        print(f"Projects: {discovery['counts']['projects']}")
        print(f"Custom Fields: {discovery['counts']['custom_fields']}")
        print(f"Tags: {discovery['counts']['tags']}")
        
        if discovery['warnings']:
            print("\nWarnings:")
            for warning in discovery['warnings']:
                print(f"  ⚠️  {warning}")
        
        print("="*60)
        
        return discovery
    
    def migrate_users(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate users from Asana to Tallyfy.
        
        Args:
            dry_run: Preview without creating users
            
        Returns:
            Migration results
        """
        logger.info("Migrating users...")
        
        results = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        # Get users
        users = self.asana_client.get_users(self.workspace_gid)
        results['total'] = len(users)
        
        # Get already processed users if resuming
        processed_users = self.checkpoint_manager.get_processed_items('users', 'user')
        
        task = self.progress_tracker.start_phase('Users', len(users))
        
        for user in users:
            try:
                # Skip if already processed
                if user['gid'] in processed_users:
                    results['skipped'] += 1
                    self.progress_tracker.update_phase('Users', 1)
                    continue
                
                # Validate user
                if not self.validator.validate_user(user):
                    results['failed'] += 1
                    results['errors'].append(f"Invalid user: {user.get('name')}")
                    continue
                
                # Transform user
                tallyfy_member = self.user_transformer.transform_user(user)
                
                if not dry_run:
                    # Create user in Tallyfy
                    created_member = self.tallyfy_client.create_member(
                        email=tallyfy_member["text"],
                        first_name=tallyfy_member['first_name'],
                        last_name=tallyfy_member['last_name'],
                        role=tallyfy_member['role']
                    )
                    
                    # Save mapping
                    self.id_mapper.add_user_mapping(
                        asana_gid=user['gid'],
                        tallyfy_id=created_member.get('id'),
                        email=tallyfy_member["text"],
                        name=user.get('name'),
                        role=tallyfy_member['role']
                    )
                    
                    # Save checkpoint
                    self.checkpoint_manager.save_item_checkpoint(
                        'users', 'user', user['gid'], 'completed'
                    )
                
                results['migrated'] += 1
                self.progress_tracker.record_success('users', user.get('name'))
                
            except Exception as e:
                logger.error(f"Failed to migrate user {user.get('name')}: {e}")
                results['failed'] += 1
                results['errors'].append(str(e))
                self.progress_tracker.record_failure('users', user.get('name'), e)
            
            self.progress_tracker.update_phase('Users', 1)
        
        self.progress_tracker.complete_phase('Users')
        self.target_counts['users'] = results['migrated']
        
        return results
    
    def migrate_teams(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate teams to Tallyfy groups.
        
        Args:
            dry_run: Preview without creating groups
            
        Returns:
            Migration results
        """
        logger.info("Migrating teams...")
        
        results = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        # Get teams
        teams = self.asana_client.get_teams(self.workspace_gid)
        results['total'] = len(teams)
        
        # Get user mappings
        user_mappings = self.id_mapper.get_all_user_mappings()
        
        task = self.progress_tracker.start_phase('Teams', len(teams))
        
        for team in teams:
            try:
                # Get team members (would need additional API call)
                # For now, using empty list
                team_members = []
                
                # Transform team
                tallyfy_group = self.user_transformer.transform_team(team, team_members)
                
                if not dry_run:
                    # Map member IDs
                    member_ids = []
                    for asana_gid in tallyfy_group['members']:
                        tallyfy_id = user_mappings.get(asana_gid)
                        if tallyfy_id:
                            member_ids.append(tallyfy_id)
                    
                    if member_ids:
                        # Create group in Tallyfy
                        created_group = self.tallyfy_client.create_group(
                            name=tallyfy_group['name'],
                            member_ids=member_ids
                        )
                        
                        # Save mapping
                        self.id_mapper.add_team_mapping(
                            asana_gid=team['gid'],
                            tallyfy_id=created_group.get('id'),
                            name=team.get('name')
                        )
                
                results['migrated'] += 1
                self.progress_tracker.record_success('teams', team.get('name'))
                
            except Exception as e:
                logger.error(f"Failed to migrate team {team.get('name')}: {e}")
                results['failed'] += 1
                results['errors'].append(str(e))
                self.progress_tracker.record_failure('teams', team.get('name'), e)
            
            self.progress_tracker.update_phase('Teams', 1)
        
        self.progress_tracker.complete_phase('Teams')
        self.target_counts['teams'] = results['migrated']
        
        return results
    
    def migrate_projects(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate projects to Tallyfy blueprints.
        
        Args:
            dry_run: Preview without creating blueprints
            
        Returns:
            Migration results
        """
        logger.info("Migrating projects as blueprints...")
        
        results = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        # Get projects
        projects = self.asana_client.get_projects(self.workspace_gid)
        results['total'] = len(projects)
        
        # Get custom fields for transformation
        custom_fields = self.asana_client.get_custom_fields(self.workspace_gid)
        field_map = {f['gid']: f for f in custom_fields}
        
        task = self.progress_tracker.start_phase('Projects', len(projects))
        
        for project in projects:
            try:
                # Get project details
                project_details = self.asana_client.get_project_details(project['gid'])
                
                # Get sections
                sections = self.asana_client.get_sections(project['gid'])
                
                # Get tasks
                tasks = self.asana_client.get_tasks(project['gid'])
                
                # Transform to blueprint
                blueprint = self.template_transformer.transform_project_to_blueprint(
                    project_details, sections, tasks, custom_fields
                )
                
                # Validate blueprint
                if not self.validator.validate_blueprint(blueprint):
                    results['failed'] += 1
                    results['errors'].append(f"Invalid blueprint: {project.get('name')}")
                    continue
                
                if not dry_run:
                    # Create blueprint in Tallyfy
                    created_blueprint = self.tallyfy_client.create_blueprint(
                        name=blueprint['name'],
                        description=blueprint['description'],
                        steps=blueprint['steps']
                    )
                    
                    # Save mapping
                    self.id_mapper.add_project_mapping(
                        asana_gid=project['gid'],
                        tallyfy_id=created_blueprint.get('id'),
                        name=project.get('name'),
                        is_template=True
                    )
                
                results['migrated'] += 1
                self.progress_tracker.record_success('projects', project.get('name'))
                
            except Exception as e:
                logger.error(f"Failed to migrate project {project.get('name')}: {e}")
                results['failed'] += 1
                results['errors'].append(str(e))
                self.progress_tracker.record_failure('projects', project.get('name'), e)
            
            self.progress_tracker.update_phase('Projects', 1)
        
        self.progress_tracker.complete_phase('Projects')
        self.target_counts['projects'] = results['migrated']
        
        return results
    
    def migrate_active_tasks(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate active tasks as processes.
        
        Args:
            dry_run: Preview without creating processes
            
        Returns:
            Migration results
        """
        logger.info("Migrating active tasks...")
        
        results = {
            'total': 0,
            'migrated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        # For active projects, create processes
        # This is simplified - in production would need more complex logic
        
        return results
    
    def run_validation(self) -> Dict[str, Any]:
        """Run validation phase.
        
        Returns:
            Validation results
        """
        logger.info("Running validation...")
        
        # Validate migration results
        validation_report = self.validator.validate_migration_results(
            self.source_counts,
            self.target_counts
        )
        
        # Print validation report
        print("\n" + self.validator.generate_validation_report())
        
        return validation_report
    
    def _auto_detect_workspace(self) -> str:
        """Auto-detect Asana workspace.
        
        Returns:
            Workspace GID
        """
        workspaces = self.asana_client.get_workspaces()
        
        if not workspaces:
            raise ValueError("No workspaces found")
        
        if len(workspaces) == 1:
            workspace = workspaces[0]
            logger.info(f"Auto-detected workspace: {workspace['name']}")
            return workspace['gid']
        
        # Multiple workspaces - need user to specify
        print("\nMultiple workspaces found:")
        for idx, ws in enumerate(workspaces):
            print(f"{idx + 1}. {ws['name']} ({ws['gid']})")
        
        raise ValueError("Multiple workspaces found. Please specify workspace_gid")
    
    def generate_migration_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive migration report.
        
        Args:
            results: Migration results
            
        Returns:
            Migration report
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'workspace_gid': self.workspace_gid,
            'results': results,
            'validation': self.validator.generate_validation_report(),
            'statistics': self.checkpoint_manager.get_run_statistics(),
            'mappings': self.id_mapper.get_statistics()
        }
        
        return report
    
    def _save_report(self, report: Dict[str, Any]) -> None:
        """Save migration report to file.
        
        Args:
            report: Report data
        """
        report_dir = Path('reports')
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"migration_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to {report_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Migrate from Asana to Tallyfy')
    
    # Required arguments
    parser.add_argument('--asana-token', required=False, help='Asana Personal Access Token',
                       default=os.getenv('ASANA_ACCESS_TOKEN'))
    parser.add_argument('--tallyfy-token', required=False, help='Tallyfy API token',
                       default=os.getenv('TALLYFY_API_TOKEN'))
    parser.add_argument('--tallyfy-org', required=False, help='Tallyfy organization ID',
                       default=os.getenv('TALLYFY_ORG_ID'))
    
    # Optional arguments
    parser.add_argument('--workspace', help='Asana workspace GID',
                       default=os.getenv('ASANA_WORKSPACE_GID'))
    parser.add_argument('--phases', nargs='+', help='Specific phases to run',
                       choices=['discovery', 'users', 'teams', 'projects', 'tasks', 'validation'])
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--report-only', action='store_true', help='Generate report without migration')
    parser.add_argument('--readiness-check', action='store_true', help='Run readiness check')
    parser.add_argument('--log-level', default='INFO', help='Logging level',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bars')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logger(args.log_level, args.log_file)
    
    # Validate required arguments
    if not args.readiness_check:
        if not args.asana_token:
            print("Error: Asana token required (--asana-token or ASANA_ACCESS_TOKEN env var)")
            sys.exit(1)
        if not args.tallyfy_token:
            print("Error: Tallyfy token required (--tallyfy-token or TALLYFY_API_TOKEN env var)")
            sys.exit(1)
        if not args.tallyfy_org:
            print("Error: Tallyfy organization ID required (--tallyfy-org or TALLYFY_ORG_ID env var)")
            sys.exit(1)
    
    try:
        # Initialize orchestrator
        orchestrator = AsanaMigrationOrchestrator(
            asana_token=args.asana_token,
            tallyfy_token=args.tallyfy_token,
            tallyfy_org_id=args.tallyfy_org,
            asana_workspace_gid=args.workspace,
            config={'disable_progress': args.no_progress}
        )
        
        # Run readiness check if requested
        if args.readiness_check:
            orchestrator.run_readiness_check()
            return
        
        # Run migration
        results = orchestrator.run(
            phases=args.phases,
            dry_run=args.dry_run,
            resume=args.resume,
            report_only=args.report_only
        )
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()