#!/usr/bin/env python3
"""
BPMN to Tallyfy Migration Orchestrator
Main entry point for migrating BPMN diagrams to Tallyfy templates
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.bpmn_client import BPMNClient
from api.tallyfy_client import TallyfyClient
from api.ai_client import AIClient
from transformers.process_transformer import ProcessTransformer
from utils.id_mapper import IDMapper
from utils.checkpoint_manager import CheckpointManager
from utils.progress_tracker import ProgressTracker
from utils.validator import Validator
from utils.logger_config import setup_logging

logger = logging.getLogger(__name__)


class BPMNMigrationOrchestrator:
    """Orchestrates the BPMN to Tallyfy migration process"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize migration orchestrator
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._load_default_config()
        self.start_time = datetime.now(timezone.utc)
        
        # Setup logging
        setup_logging(self.config.get('logging', {}))
        
        # Initialize components
        self._initialize_components()
        
        # Migration state
        self.migration_id = self._generate_migration_id()
        self.checkpoint_dir = Path('checkpoints') / self.migration_id
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BPMN Migration orchestrator initialized with ID: {self.migration_id}")
        logger.info("Ready to transform BPMN 2.0 diagrams to Tallyfy templates")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        
        return {
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'migration': {
                'batch_size': 10,
                'enable_ai': True,
                'validate_bpmn': True,
                'optimize_output': True
            },
            'tallyfy': {
                'api_url': os.getenv('TALLYFY_API_URL', 'https://api.tallyfy.com'),
                'client_id': os.getenv('TALLYFY_CLIENT_ID'),
                'client_secret': os.getenv('TALLYFY_CLIENT_SECRET'),
                'organization_id': os.getenv('TALLYFY_ORG_ID'),
                'organization_slug': os.getenv('TALLYFY_ORG_SLUG')
            }
        }
    
    def _initialize_components(self):
        """Initialize all migration components"""
        
        # Initialize AI client
        self.ai_client = AIClient()
        if self.ai_client.enabled:
            logger.info("✅ AI augmentation enabled - complex BPMN patterns will be intelligently transformed")
        else:
            logger.info("⚠️ AI disabled - using deterministic fallbacks for complex patterns")
        
        # Initialize Tallyfy client if credentials provided
        if self.config['tallyfy'].get('client_id'):
            self.tallyfy_client = TallyfyClient(
                api_url=self.config['tallyfy']['api_url'],
                client_id=self.config['tallyfy']['client_id'],
                client_secret=self.config['tallyfy']['client_secret'],
                organization_id=self.config['tallyfy']['organization_id'],
                organization_slug=self.config['tallyfy']['organization_slug']
            )
            logger.info("Tallyfy API client initialized")
        else:
            self.tallyfy_client = None
            logger.warning("Tallyfy credentials not provided - will export to JSON only")
        
        # Initialize utilities
        self.id_mapper = IDMapper()
        self.checkpoint_manager = CheckpointManager()  # Uses default checkpoint dir
        self.progress_tracker = ProgressTracker()
        self.validator = Validator()
        
        # Initialize transformer
        self.process_transformer = ProcessTransformer(
            ai_client=self.ai_client,
            id_mapper=self.id_mapper
        )
    
    def migrate_file(self, file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate a single BPMN file to Tallyfy
        
        Args:
            file_path: Path to BPMN XML file
            output_dir: Optional directory for output files
            
        Returns:
            Migration results
        """
        logger.info(f"Starting migration of BPMN file: {file_path}")
        
        # Create output directory
        if not output_dir:
            output_dir = Path('output') / self.migration_id
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'file': file_path,
            'status': 'pending',
            'templates_created': [],
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # Phase 1: Parse BPMN
            logger.info("Phase 1: Parsing BPMN file")
            bpmn_client = BPMNClient(file_path)
            
            # Validate BPMN if enabled
            if self.config['migration']['validate_bpmn']:
                is_valid, issues = bpmn_client.validate()
                if not is_valid:
                    logger.warning(f"BPMN validation issues: {issues}")
                    results['warnings'].extend(issues)
            
            # Get BPMN data
            bpmn_data = bpmn_client.to_dict()
            results['statistics']['bpmn'] = bpmn_client.stats
            
            # Save parsed BPMN data
            with open(output_dir / 'parsed_bpmn.json', 'w') as f:
                json.dump(bpmn_data, f, indent=2, default=str)
            
            # Phase 2: Transform processes
            logger.info("Phase 2: Transforming BPMN processes to Tallyfy templates")
            templates = []
            
            for process in bpmn_data['processes']:
                logger.info(f"Transforming process: {process.get('name', process['id'])}")
                
                # Find collaboration context if exists
                collaboration = None
                for collab in bpmn_data.get('collaborations', []):
                    for participant in collab.get('participants', []):
                        if participant.get('process_ref') == process['id']:
                            collaboration = collab
                            break
                
                # Transform process
                template = self.process_transformer.transform_process(process, collaboration)
                templates.append(template)
                
                # Save template JSON
                template_file = output_dir / f"template_{template['id']}.json"
                with open(template_file, 'w') as f:
                    json.dump(template, f, indent=2, default=str)
                
                results['templates_created'].append({
                    'id': template['id'],
                    'title': template['title'],
                    'file': str(template_file)
                })
            
            # Phase 3: Handle cross-process elements
            logger.info("Phase 3: Processing cross-process elements")
            
            # Handle message flows between processes
            if bpmn_data.get('collaborations'):
                for collab in bpmn_data['collaborations']:
                    for msg_flow in collab.get('message_flows', []):
                        # Add webhooks for message flows
                        logger.info(f"Message flow: {msg_flow['source_ref']} -> {msg_flow['target_ref']}")
            
            # Phase 4: Upload to Tallyfy (if client available)
            if self.tallyfy_client:
                logger.info("Phase 4: Uploading templates to Tallyfy")
                
                for template in templates:
                    try:
                        # Create template in Tallyfy
                        created = self.tallyfy_client.create_template(template)
                        logger.info(f"Created template in Tallyfy: {created['id']}")
                        
                        # Update results
                        for t in results['templates_created']:
                            if t['id'] == template['id']:
                                t['tallyfy_id'] = created['id']
                                t['tallyfy_url'] = created.get('url')
                    
                    except Exception as e:
                        logger.error(f"Failed to upload template {template['id']}: {e}")
                        results['errors'].append(f"Upload failed for {template['title']}: {str(e)}")
            else:
                logger.info("Phase 4: Skipping Tallyfy upload (no credentials)")
            
            # Phase 5: Validation
            logger.info("Phase 5: Validating migration")
            
            validation_results = self.validator.validate_migration(
                source_data=bpmn_data,
                target_data={'templates': templates},
                mappings=self.id_mapper.get_all_mappings()
            )
            
            results['validation'] = validation_results
            
            # Update statistics
            results['statistics']['transformation'] = self.process_transformer.get_stats()
            if self.ai_client:
                results['statistics']['ai'] = self.ai_client.get_stats()
            
            # Mark as successful
            results['status'] = 'success' if not results['errors'] else 'partial'
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            results['status'] = 'failed'
            results['errors'].append(str(e))
        
        # Save final results
        results_file = output_dir / 'migration_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Migration completed with status: {results['status']}")
        logger.info(f"Results saved to: {results_file}")
        
        return results
    
    def migrate_directory(self, directory: str, output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Migrate all BPMN files in a directory
        
        Args:
            directory: Directory containing BPMN files
            output_dir: Optional output directory
            
        Returns:
            List of migration results
        """
        logger.info(f"Migrating all BPMN files in directory: {directory}")
        
        # Find all BPMN files
        bpmn_files = []
        for ext in ['*.bpmn', '*.bpmn20.xml', '*.xml']:
            bpmn_files.extend(Path(directory).glob(ext))
        
        if not bpmn_files:
            logger.warning(f"No BPMN files found in {directory}")
            return []
        
        logger.info(f"Found {len(bpmn_files)} BPMN files")
        
        # Process each file
        all_results = []
        for i, file_path in enumerate(bpmn_files, 1):
            logger.info(f"Processing file {i}/{len(bpmn_files)}: {file_path.name}")
            
            # Create output subdirectory for each file
            if output_dir:
                file_output_dir = Path(output_dir) / file_path.stem
            else:
                file_output_dir = None
            
            # Migrate file
            results = self.migrate_file(str(file_path), str(file_output_dir) if file_output_dir else None)
            all_results.append(results)
            
            # Save checkpoint
            self.checkpoint_manager.save_checkpoint({
                'processed': i,
                'total': len(bpmn_files),
                'results': all_results
            })
        
        # Save summary
        summary = {
            'migration_id': self.migration_id,
            'total_files': len(bpmn_files),
            'successful': sum(1 for r in all_results if r['status'] == 'success'),
            'partial': sum(1 for r in all_results if r['status'] == 'partial'),
            'failed': sum(1 for r in all_results if r['status'] == 'failed'),
            'templates_created': sum(len(r['templates_created']) for r in all_results),
            'results': all_results
        }
        
        if output_dir:
            summary_file = Path(output_dir) / 'migration_summary.json'
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            logger.info(f"Summary saved to: {summary_file}")
        
        return all_results
    
    def _generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        
        return datetime.utcnow().strftime('%Y%m%d_%H%M%S')


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='Migrate BPMN 2.0 diagrams to Tallyfy templates'
    )
    
    parser.add_argument(
        'input',
        help='BPMN file or directory to migrate'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory for results',
        default=None
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI augmentation'
    )
    
    parser.add_argument(
        '--no-validation',
        action='store_true',
        help='Skip BPMN validation'
    )
    
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload templates to Tallyfy (requires credentials)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure based on arguments
    config = {
        'logging': {
            'level': 'DEBUG' if args.verbose else 'INFO'
        },
        'migration': {
            'enable_ai': not args.no_ai,
            'validate_bpmn': not args.no_validation
        }
    }
    
    # Add Tallyfy config if upload requested
    if args.upload:
        config['tallyfy'] = {
            'api_url': os.getenv('TALLYFY_API_URL', 'https://api.tallyfy.com'),
            'client_id': os.getenv('TALLYFY_CLIENT_ID'),
            'client_secret': os.getenv('TALLYFY_CLIENT_SECRET'),
            'organization_id': os.getenv('TALLYFY_ORG_ID'),
            'organization_slug': os.getenv('TALLYFY_ORG_SLUG')
        }
    else:
        config['tallyfy'] = {}
    
    # Initialize orchestrator
    orchestrator = BPMNMigrationOrchestrator(config)
    
    # Check if input is file or directory
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Migrate single file
        results = orchestrator.migrate_file(str(input_path), args.output)
        
        # Print summary
        print(f"\nMigration Status: {results['status']}")
        print(f"Templates Created: {len(results['templates_created'])}")
        
        if results['errors']:
            print(f"Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        if results['warnings']:
            print(f"Warnings: {len(results['warnings'])}")
            for warning in results['warnings'][:5]:  # Show first 5
                print(f"  - {warning}")
    
    elif input_path.is_dir():
        # Migrate directory
        all_results = orchestrator.migrate_directory(str(input_path), args.output)
        
        # Print summary
        successful = sum(1 for r in all_results if r['status'] == 'success')
        partial = sum(1 for r in all_results if r['status'] == 'partial')
        failed = sum(1 for r in all_results if r['status'] == 'failed')
        
        print(f"\nMigration Summary:")
        print(f"Total Files: {len(all_results)}")
        print(f"Successful: {successful}")
        print(f"Partial: {partial}")
        print(f"Failed: {failed}")
        print(f"Templates Created: {sum(len(r['templates_created']) for r in all_results)}")
    
    else:
        print(f"Error: {args.input} is not a valid file or directory")
        sys.exit(1)


# Utility imports that need to be created
class CheckpointManager:
    """Simple checkpoint manager"""
    def __init__(self, checkpoint_dir):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, data):
        checkpoint_file = self.checkpoint_dir / 'checkpoint.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)


class ProgressTracker:
    """Simple progress tracker"""
    def __init__(self):
        self.progress = {}
    
    def update(self, key, value):
        self.progress[key] = value


class MigrationValidator:
    """Simple migration validator"""
    def validate_migration(self, source_data, target_data, mappings):
        return {
            'valid': True,
            'source_elements': len(source_data.get('processes', [])),
            'target_elements': len(target_data.get('templates', [])),
            'mappings': len(mappings) if mappings else 0
        }


class IDMapper:
    """Simple ID mapper"""
    def __init__(self):
        self.mappings = {}
    
    def map_id(self, source_id, target_id, element_type):
        if element_type not in self.mappings:
            self.mappings[element_type] = {}
        self.mappings[element_type][source_id] = target_id
    
    def get_mapped_id(self, source_id, element_type):
        return self.mappings.get(element_type, {}).get(source_id)
    
    def get_all_mappings(self):
        return self.mappings


def setup_logging(config):
    """Setup logging configuration"""
    logging.basicConfig(
        level=config.get('level', 'INFO'),
        format=config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )


if __name__ == '__main__':
    main()