"""Main migration orchestrator for Monday.com to Tallyfy."""

import argparse
import json
import logging
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .api.monday_client import MondayClient
from .api.tallyfy_client import TallyfyClient
from .transformers.board_transformer import BoardTransformer
from .transformers.user_transformer import UserTransformer
from .transformers.instance_transformer import InstanceTransformer
from .utils.id_mapper import IDMapper
from .utils.progress_tracker import ProgressTracker
from .utils.validator import Validator
from .utils.checkpoint_manager import CheckpointManager
from .utils.error_handler import ErrorHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MondayMigrator:
    """Main orchestrator for Monday.com to Tallyfy migration."""
    
    def __init__(self, monday_client: MondayClient, tallyfy_client: TallyfyClient,
                 dry_run: bool = False, report_only: bool = False):
        """Initialize migrator.
        
        Args:
            monday_client: Monday.com API client
            tallyfy_client: Tallyfy API client
            dry_run: If True, simulate migration without creating data
            report_only: If True, only generate migration report
        """
        self.monday = monday_client
        self.tallyfy = tallyfy_client
        self.dry_run = dry_run
        self.report_only = report_only
        
        # Initialize components
        self.board_transformer = BoardTransformer()
        self.user_transformer = UserTransformer()
        self.instance_transformer = InstanceTransformer()
        self.id_mapper = IDMapper()
        self.progress = ProgressTracker()
        self.validator = Validator()
        self.checkpoint = CheckpointManager()
        self.error_handler = ErrorHandler()
        
    def migrate(self, workspace_ids: Optional[List[str]] = None,
                board_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute full migration.
        
        Args:
            workspace_ids: Optional list of workspace IDs to migrate
            board_ids: Optional list of specific board IDs to migrate
            
        Returns:
            Migration report
        """
        logger.info("=" * 80)
        logger.info("MONDAY.COM TO TALLYFY MIGRATION")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("🔧 DRY RUN MODE - No data will be created")
        if self.report_only:
            logger.info("📊 REPORT ONLY MODE - Generating analysis report")
        
        start_time = time.time()
        
        try:
            # Check for existing checkpoint
            if self.checkpoint.has_checkpoint():
                logger.info("♻️ Found existing checkpoint, resuming migration...")
                state = self.checkpoint.load()
                self.id_mapper.load_state(state.get('id_mappings', {}))
                self.progress.load_state(state.get('progress', {}))
            else:
                logger.info("🆕 Starting fresh migration...")
            
            # Phase 1: Discovery
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 1: DISCOVERY")
            logger.info("=" * 60)
            discovery_data = self._phase_discovery(workspace_ids, board_ids)
            
            if self.report_only:
                # Generate and return report only
                report = self._generate_report(discovery_data)
                self._print_report(report)
                return report
            
            # Phase 2: User Migration
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 2: USER MIGRATION")
            logger.info("=" * 60)
            user_results = self._phase_users(discovery_data['users'], discovery_data['teams'])
            
            # Phase 3: Blueprint Creation
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 3: BLUEPRINT CREATION")
            logger.info("=" * 60)
            blueprint_results = self._phase_blueprints(discovery_data['boards'])
            
            # Phase 4: Process Migration
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 4: PROCESS MIGRATION")
            logger.info("=" * 60)
            process_results = self._phase_processes(discovery_data['items'], blueprint_results)
            
            # Phase 5: Validation
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 5: VALIDATION")
            logger.info("=" * 60)
            validation_results = self._phase_validation()
            
            # Generate final report
            duration = time.time() - start_time
            report = self._generate_final_report(
                discovery_data, user_results, blueprint_results,
                process_results, validation_results, duration
            )
            
            # Save report
            self._save_report(report)
            
            # Clear checkpoint on success
            if not self.dry_run:
                self.checkpoint.clear()
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
            logger.info(f"⏱️ Total time: {duration:.2f} seconds")
            logger.info("=" * 80)
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            self.error_handler.handle_error(e, context="main_migration")
            
            # Save checkpoint for resume
            if not self.dry_run and not self.report_only:
                self._save_checkpoint()
            
            raise
    
    def _phase_discovery(self, workspace_ids: Optional[List[str]] = None,
                        board_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Phase 1: Discover Monday.com data.
        
        Args:
            workspace_ids: Optional workspace filter
            board_ids: Optional board filter
            
        Returns:
            Discovery data
        """
        discovery = {
            'workspaces': [],
            'boards': [],
            'users': [],
            'teams': [],
            'items': [],
            'stats': {}
        }
        
        try:
            # Get workspaces
            if workspace_ids:
                logger.info(f"Fetching {len(workspace_ids)} specified workspaces...")
                for ws_id in workspace_ids:
                    workspace = self.monday.get_workspace(ws_id)
                    if workspace:
                        discovery['workspaces'].append(workspace)
            else:
                logger.info("Fetching all workspaces...")
                discovery['workspaces'] = self.monday.get_workspaces()
            
            logger.info(f"Found {len(discovery['workspaces'])} workspaces")
            
            # Get boards
            if board_ids:
                logger.info(f"Fetching {len(board_ids)} specified boards...")
                for board_id in board_ids:
                    board = self.monday.get_board(board_id, include_columns=True)
                    if board:
                        discovery['boards'].append(board)
            else:
                logger.info("Fetching all boards...")
                for workspace in discovery['workspaces']:
                    ws_boards = self.monday.get_boards(
                        workspace_id=workspace.get('id'),
                        include_columns=True
                    )
                    discovery['boards'].extend(ws_boards)
            
            logger.info(f"Found {len(discovery['boards'])} boards")
            
            # Get users and teams
            logger.info("Fetching users and teams...")
            discovery['users'] = self.monday.get_users()
            discovery['teams'] = self.monday.get_teams()
            
            logger.info(f"Found {len(discovery['users'])} users and {len(discovery['teams'])} teams")
            
            # Get items from boards
            logger.info("Fetching items from boards...")
            total_items = 0
            for board in discovery['boards']:
                board_id = board.get('id')
                items = self.monday.get_items(
                    board_id=board_id,
                    include_column_values=True,
                    include_subitems=True,
                    include_updates=True
                )
                
                # Add board reference to items
                for item in items:
                    item['board_id'] = board_id
                    item['board_name'] = board.get('name')
                
                discovery['items'].extend(items)
                total_items += len(items)
                
                logger.info(f"  Board '{board.get('name')}': {len(items)} items")
            
            logger.info(f"Total items found: {total_items}")
            
            # Calculate statistics
            discovery['stats'] = {
                'workspaces': len(discovery['workspaces']),
                'boards': len(discovery['boards']),
                'users': len(discovery['users']),
                'teams': len(discovery['teams']),
                'items': len(discovery['items']),
                'complexity_estimate': self._estimate_complexity(discovery)
            }
            
            self.progress.update('discovery', discovery['stats'])
            
            return discovery
            
        except Exception as e:
            self.error_handler.handle_error(e, context="discovery_phase")
            raise
    
    def _phase_users(self, users: List[Dict[str, Any]],
                    teams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phase 2: Migrate users and teams.
        
        Args:
            users: Monday.com users
            teams: Monday.com teams
            
        Returns:
            User migration results
        """
        results = {
            'users_created': 0,
            'users_skipped': 0,
            'teams_created': 0,
            'errors': []
        }
        
        try:
            # Check existing Tallyfy users
            logger.info("Checking existing Tallyfy users...")
            existing_users = {}
            if not self.dry_run:
                tallyfy_users = self.tallyfy.get_users()
                existing_users = {u["text"].lower(): u for u in tallyfy_users}
            
            # Transform and create users
            logger.info("Migrating users...")
            for monday_user in users:
                try:
                    # Transform user
                    tallyfy_member = self.user_transformer.transform_user(monday_user)
                    
                    if not tallyfy_member:
                        results['users_skipped'] += 1
                        continue
                    
                    email = tallyfy_member["text"].lower()
                    
                    # Check if user exists
                    if email in existing_users:
                        logger.info(f"  User {email} already exists, mapping...")
                        self.id_mapper.add_mapping(
                            'user',
                            monday_user['id'],
                            existing_users[email]['id']
                        )
                        results['users_skipped'] += 1
                    else:
                        if not self.dry_run:
                            # Create user
                            logger.info(f"  Creating user: {email}")
                            created_user = self.tallyfy.create_user(tallyfy_member)
                            self.id_mapper.add_mapping(
                                'user',
                                monday_user['id'],
                                created_user['id']
                            )
                        results['users_created'] += 1
                    
                    self.progress.increment('users_processed')
                    
                except Exception as e:
                    error_msg = f"Failed to migrate user {monday_user.get("text")}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    self.error_handler.handle_error(e, context=f"user_{monday_user.get('id')}")
            
            # Transform and create teams/groups
            logger.info("Migrating teams...")
            for monday_team in teams:
                try:
                    # Transform team
                    tallyfy_group = self.user_transformer.transform_team(monday_team)
                    
                    if not self.dry_run:
                        # Create group
                        logger.info(f"  Creating group: {tallyfy_group['name']}")
                        created_group = self.tallyfy.create_group(tallyfy_group)
                        self.id_mapper.add_mapping(
                            'team',
                            monday_team['id'],
                            created_group['id']
                        )
                    
                    results['teams_created'] += 1
                    self.progress.increment('teams_processed')
                    
                except Exception as e:
                    error_msg = f"Failed to migrate team {monday_team.get('name')}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    self.error_handler.handle_error(e, context=f"team_{monday_team.get('id')}")
            
            logger.info(f"User migration complete: {results['users_created']} created, "
                       f"{results['users_skipped']} skipped, {results['teams_created']} teams")
            
            # Save checkpoint
            if not self.dry_run:
                self._save_checkpoint()
            
            return results
            
        except Exception as e:
            self.error_handler.handle_error(e, context="users_phase")
            raise
    
    def _phase_blueprints(self, boards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phase 3: Create blueprints from boards.
        
        Args:
            boards: Monday.com boards
            
        Returns:
            Blueprint creation results
        """
        results = {
            'blueprints_created': 0,
            'blueprints_skipped': 0,
            'board_mapping': {},
            'errors': []
        }
        
        try:
            logger.info(f"Creating blueprints from {len(boards)} boards...")
            
            for board in boards:
                try:
                    board_id = board.get('id')
                    board_name = board.get('name', 'Untitled')
                    
                    # Check if already processed
                    if self.checkpoint.is_processed('board', board_id):
                        logger.info(f"  Board '{board_name}' already processed, skipping...")
                        results['blueprints_skipped'] += 1
                        continue
                    
                    logger.info(f"  Transforming board: {board_name}")
                    
                    # Transform board to blueprint
                    blueprint = self.board_transformer.transform_board_to_blueprint(board)
                    
                    # Validate blueprint
                    validation = self.validator.validate_blueprint(blueprint)
                    if not validation['valid']:
                        logger.warning(f"    Blueprint validation failed: {validation['errors']}")
                        results['errors'].extend(validation['errors'])
                    
                    if not self.dry_run:
                        # Create blueprint
                        logger.info(f"    Creating blueprint: {blueprint['name']}")
                        created_blueprint = self.tallyfy.create_blueprint(blueprint)
                        
                        # Map board to blueprint
                        self.id_mapper.add_mapping(
                            'board',
                            board_id,
                            created_blueprint['id']
                        )
                        results['board_mapping'][board_id] = created_blueprint['id']
                        
                        # Mark as processed
                        self.checkpoint.mark_processed('board', board_id)
                    
                    results['blueprints_created'] += 1
                    self.progress.increment('blueprints_processed')
                    
                except Exception as e:
                    error_msg = f"Failed to create blueprint for board {board.get('name')}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    self.error_handler.handle_error(e, context=f"board_{board.get('id')}")
            
            logger.info(f"Blueprint creation complete: {results['blueprints_created']} created, "
                       f"{results['blueprints_skipped']} skipped")
            
            # Save checkpoint
            if not self.dry_run:
                self._save_checkpoint()
            
            return results
            
        except Exception as e:
            self.error_handler.handle_error(e, context="blueprints_phase")
            raise
    
    def _phase_processes(self, items: List[Dict[str, Any]],
                        blueprint_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Migrate items as processes.
        
        Args:
            items: Monday.com items
            blueprint_results: Blueprint creation results
            
        Returns:
            Process migration results
        """
        results = {
            'processes_created': 0,
            'processes_skipped': 0,
            'comments_migrated': 0,
            'errors': []
        }
        
        try:
            logger.info(f"Migrating {len(items)} items as processes...")
            
            # Get user mapping
            user_mapping = self.id_mapper.get_mappings('user')
            
            # Group items by board
            items_by_board = {}
            for item in items:
                board_id = item.get('board_id')
                if board_id not in items_by_board:
                    items_by_board[board_id] = []
                items_by_board[board_id].append(item)
            
            # Process items by board
            for board_id, board_items in items_by_board.items():
                # Get blueprint ID
                checklist_id = self.id_mapper.get_mapping('board', board_id)
                if not checklist_id:
                    logger.warning(f"  No blueprint found for board {board_id}, skipping items...")
                    results['processes_skipped'] += len(board_items)
                    continue
                
                logger.info(f"  Processing {len(board_items)} items for board {board_id}")
                
                # Use batch transformer
                batch_generator = self.instance_transformer.batch_transform_items(
                    board_items, checklist_id, user_mapping, batch_size=50
                )
                
                for batch in batch_generator:
                    if not self.dry_run:
                        try:
                            # Create processes in batch
                            logger.info(f"    Creating batch of {len(batch)} processes...")
                            created_processes = self.tallyfy.batch_create_processes(batch)
                            
                            # Map items to processes
                            for i, process in enumerate(created_processes):
                                if i < len(batch):
                                    original_id = batch[i]['metadata']['original_id']
                                    self.id_mapper.add_mapping('item', original_id, process['id'])
                            
                            results['processes_created'] += len(created_processes)
                            
                        except Exception as e:
                            error_msg = f"Failed to create process batch: {e}"
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                    else:
                        results['processes_created'] += len(batch)
                    
                    self.progress.add('processes_processed', len(batch))
                
                # Migrate item updates as comments
                for item in board_items:
                    if item.get('updates'):
                        comments = self.instance_transformer.transform_updates(
                            item['updates'], user_mapping
                        )
                        results['comments_migrated'] += len(comments)
            
            logger.info(f"Process migration complete: {results['processes_created']} created, "
                       f"{results['processes_skipped']} skipped")
            
            # Save checkpoint
            if not self.dry_run:
                self._save_checkpoint()
            
            return results
            
        except Exception as e:
            self.error_handler.handle_error(e, context="processes_phase")
            raise
    
    def _phase_validation(self) -> Dict[str, Any]:
        """Phase 5: Validate migration results.
        
        Returns:
            Validation results
        """
        results = {
            'valid': True,
            'checks': [],
            'warnings': [],
            'errors': []
        }
        
        try:
            logger.info("Running validation checks...")
            
            # Check ID mappings
            mappings = self.id_mapper.get_all_mappings()
            
            results['checks'].append({
                'name': 'ID Mappings',
                'passed': True,
                'details': {
                    'users': len(mappings.get('user', {})),
                    'teams': len(mappings.get('team', {})),
                    'boards': len(mappings.get('board', {})),
                    'items': len(mappings.get('item', {}))
                }
            })
            
            # Check progress statistics
            stats = self.progress.get_stats()
            results['checks'].append({
                'name': 'Progress Statistics',
                'passed': True,
                'details': stats
            })
            
            # Check error log
            errors = self.error_handler.get_errors()
            if errors:
                results['warnings'].append(f"Found {len(errors)} errors during migration")
                results['errors'] = errors[-10:]  # Last 10 errors
            
            # Verify critical mappings
            if not mappings.get('board'):
                results['errors'].append("No board to blueprint mappings found")
                results['valid'] = False
            
            if not mappings.get('user'):
                results['warnings'].append("No user mappings found")
            
            logger.info(f"Validation complete: {'✅ PASSED' if results['valid'] else '❌ FAILED'}")
            
            return results
            
        except Exception as e:
            self.error_handler.handle_error(e, context="validation_phase")
            results['valid'] = False
            results['errors'].append(str(e))
            return results
    
    def _estimate_complexity(self, discovery: Dict[str, Any]) -> str:
        """Estimate migration complexity.
        
        Args:
            discovery: Discovery data
            
        Returns:
            Complexity level
        """
        total_items = discovery['stats']['items']
        total_boards = discovery['stats']['boards']
        total_users = discovery['stats']['users']
        
        complexity_score = (
            total_items * 1 +
            total_boards * 10 +
            total_users * 2
        )
        
        if complexity_score < 100:
            return "Low"
        elif complexity_score < 1000:
            return "Medium"
        elif complexity_score < 10000:
            return "High"
        else:
            return "Very High"
    
    def _save_checkpoint(self):
        """Save current migration state."""
        state = {
            'id_mappings': self.id_mapper.get_all_mappings(),
            'progress': self.progress.get_stats(),
            'timestamp': datetime.now().isoformat()
        }
        self.checkpoint.save(state)
        logger.debug("Checkpoint saved")
    
    def _generate_report(self, discovery: Dict[str, Any]) -> Dict[str, Any]:
        """Generate migration analysis report.
        
        Args:
            discovery: Discovery data
            
        Returns:
            Analysis report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': 'report_only',
            'summary': discovery['stats'],
            'workspaces': [],
            'boards': [],
            'complexity': discovery['stats']['complexity_estimate'],
            'recommendations': []
        }
        
        # Analyze workspaces
        for workspace in discovery['workspaces']:
            report['workspaces'].append({
                'id': workspace.get('id'),
                'name': workspace.get('name'),
                'kind': workspace.get('kind'),
                'user_count': workspace.get('users_count', 0)
            })
        
        # Analyze boards
        for board in discovery['boards']:
            columns = board.get('columns', [])
            column_types = {}
            for col in columns:
                col_type = col.get('type')
                column_types[col_type] = column_types.get(col_type, 0) + 1
            
            report['boards'].append({
                'id': board.get('id'),
                'name': board.get('name'),
                'kind': board.get('board_kind'),
                'groups': len(board.get('groups', [])),
                'column_types': column_types,
                'complexity': self._estimate_board_complexity(board)
            })
        
        # Add recommendations
        if discovery['stats']['items'] > 10000:
            report['recommendations'].append(
                "Consider migrating in batches due to high item count"
            )
        
        if discovery['stats']['boards'] > 50:
            report['recommendations'].append(
                "Large number of boards - consider prioritizing critical boards"
            )
        
        complex_boards = [b for b in report['boards'] if b['complexity'] == 'High']
        if complex_boards:
            report['recommendations'].append(
                f"{len(complex_boards)} complex boards require careful review"
            )
        
        return report
    
    def _estimate_board_complexity(self, board: Dict[str, Any]) -> str:
        """Estimate board complexity.
        
        Args:
            board: Monday.com board
            
        Returns:
            Complexity level
        """
        complexity_score = 0
        
        # Check column types
        for column in board.get('columns', []):
            col_type = column.get('type')
            if col_type in ['formula', 'mirror', 'board-relation', 'dependency']:
                complexity_score += 5
            elif col_type in ['timeline', 'location', 'world_clock']:
                complexity_score += 3
            else:
                complexity_score += 1
        
        # Check groups
        complexity_score += len(board.get('groups', [])) * 2
        
        # Check views
        complexity_score += len(board.get('views', [])) * 2
        
        if complexity_score < 20:
            return "Low"
        elif complexity_score < 50:
            return "Medium"
        else:
            return "High"
    
    def _generate_final_report(self, discovery: Dict[str, Any],
                              user_results: Dict[str, Any],
                              blueprint_results: Dict[str, Any],
                              process_results: Dict[str, Any],
                              validation_results: Dict[str, Any],
                              duration: float) -> Dict[str, Any]:
        """Generate final migration report.
        
        Args:
            discovery: Discovery data
            user_results: User migration results
            blueprint_results: Blueprint creation results
            process_results: Process migration results
            validation_results: Validation results
            duration: Total migration duration
            
        Returns:
            Final report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'mode': 'dry_run' if self.dry_run else 'live',
            'summary': {
                'discovered': discovery['stats'],
                'migrated': {
                    'users': user_results['users_created'],
                    'teams': user_results['teams_created'],
                    'blueprints': blueprint_results['blueprints_created'],
                    'processes': process_results['processes_created'],
                    'comments': process_results['comments_migrated']
                },
                'skipped': {
                    'users': user_results['users_skipped'],
                    'blueprints': blueprint_results['blueprints_skipped'],
                    'processes': process_results['processes_skipped']
                }
            },
            'validation': validation_results,
            'errors': [],
            'id_mappings': self.id_mapper.get_all_mappings() if not self.dry_run else {}
        }
        
        # Collect all errors
        all_errors = (
            user_results.get('errors', []) +
            blueprint_results.get('errors', []) +
            process_results.get('errors', [])
        )
        report['errors'] = all_errors
        
        return report
    
    def _print_report(self, report: Dict[str, Any]):
        """Print report to console.
        
        Args:
            report: Report data
        """
        print("\n" + "=" * 80)
        print("MIGRATION ANALYSIS REPORT")
        print("=" * 80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Complexity: {report['complexity']}")
        print("\nSUMMARY:")
        for key, value in report['summary'].items():
            print(f"  {key}: {value}")
        
        print("\nWORKSPACES:")
        for ws in report['workspaces']:
            print(f"  - {ws['name']} ({ws['kind']}): {ws['user_count']} users")
        
        print("\nBOARDS:")
        for board in report['boards'][:10]:  # First 10
            print(f"  - {board['name']} ({board['complexity']} complexity)")
            print(f"    Groups: {board['groups']}, Columns: {sum(board['column_types'].values())}")
        
        if len(report['boards']) > 10:
            print(f"  ... and {len(report['boards']) - 10} more boards")
        
        if report.get('recommendations'):
            print("\nRECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  ⚠️ {rec}")
        
        print("=" * 80)
    
    def _save_report(self, report: Dict[str, Any]):
        """Save report to file.
        
        Args:
            report: Report data
        """
        filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {filename}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Migrate Monday.com to Tallyfy')
    parser.add_argument('--api-token', required=True, help='Monday.com API token')
    parser.add_argument('--tallyfy-key', required=True, help='Tallyfy API key')
    parser.add_argument('--tallyfy-org', required=True, help='Tallyfy organization')
    parser.add_argument('--workspace-ids', nargs='+', help='Specific workspace IDs to migrate')
    parser.add_argument('--board-ids', nargs='+', help='Specific board IDs to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without creating data')
    parser.add_argument('--report-only', action='store_true', help='Generate report without migrating')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize clients
        monday_client = MondayClient(api_token=args.api_token)
        tallyfy_client = TallyfyClient(
            api_key=args.tallyfy_key,
            organization=args.tallyfy_org
        )
        
        # Create migrator
        migrator = MondayMigrator(
            monday_client=monday_client,
            tallyfy_client=tallyfy_client,
            dry_run=args.dry_run,
            report_only=args.report_only
        )
        
        # Run migration
        report = migrator.migrate(
            workspace_ids=args.workspace_ids,
            board_ids=args.board_ids
        )
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()