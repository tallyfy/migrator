#!/usr/bin/env python3
"""
BPMN to Tallyfy Migration - Main Entry Point
Complete migration pipeline with all components integrated
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from migrator import BPMNToTallyfyMigrator
from tallyfy_generator import TallyfyTemplateGenerator
from analyzer.bpmn_complexity_analyzer import BPMNComplexityAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteBPMNMigrator:
    """
    Complete BPMN to Tallyfy migration pipeline
    Integrates all components for production use
    """
    
    def __init__(self):
        """Initialize all components"""
        self.migrator = BPMNToTallyfyMigrator()
        self.generator = TallyfyTemplateGenerator()
        self.analyzer = BPMNComplexityAnalyzer()
    
    def analyze(self, bpmn_file: str) -> Dict[str, Any]:
        """
        Analyze BPMN file complexity before migration
        
        Args:
            bpmn_file: Path to BPMN file
            
        Returns:
            Complexity analysis results
        """
        logger.info(f"Analyzing complexity of {bpmn_file}")
        return self.analyzer.analyze_file(bpmn_file)
    
    def migrate(self, 
                bpmn_file: str,
                output_file: Optional[str] = None,
                config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete migration pipeline
        
        Args:
            bpmn_file: Path to BPMN file
            output_file: Optional output JSON file
            config: Optional configuration
            
        Returns:
            Migration results with Tallyfy template
        """
        results = {
            'status': 'started',
            'bpmn_file': bpmn_file,
            'complexity': None,
            'migration': None,
            'template': None,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: Analyze complexity
            logger.info("Step 1: Analyzing BPMN complexity...")
            complexity = self.analyze(bpmn_file)
            results['complexity'] = complexity
            
            # Warn if too complex
            if complexity.get('recommendation') == 'NOT_RECOMMENDED':
                results['warnings'].append(
                    "This BPMN is too complex for automatic migration. "
                    "Manual redesign recommended."
                )
            
            # Step 2: Parse and migrate BPMN
            logger.info("Step 2: Parsing and migrating BPMN elements...")
            migration_results = self.migrator.migrate_file(bpmn_file)
            results['migration'] = migration_results
            
            if migration_results.get('errors'):
                results['errors'].extend(migration_results['errors'])
                results['status'] = 'failed'
                return results
            
            # Step 3: Generate Tallyfy template
            logger.info("Step 3: Generating Tallyfy template...")
            templates = []
            
            for process in migration_results.get('processes', []):
                template = self.generator.generate_template(
                    process,
                    migration_results.get('migration_report', {}),
                    config
                )
                templates.append(template)
            
            results['template'] = templates[0] if len(templates) == 1 else templates
            
            # Step 4: Save output if requested
            if output_file and results['template']:
                logger.info(f"Step 4: Saving template to {output_file}")
                with open(output_file, 'w') as f:
                    json.dump(results['template'], f, indent=2)
                results['output_file'] = output_file
            
            # Step 5: Generate summary
            results['summary'] = self._generate_summary(results)
            results['status'] = 'completed'
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            results['errors'].append(str(e))
            results['status'] = 'failed'
        
        return results
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate migration summary"""
        summary = {
            'total_elements': 0,
            'migrated': 0,
            'partial': 0,
            'failed': 0,
            'success_rate': 0,
            'manual_work_required': False,
            'estimated_effort': 'Unknown'
        }
        
        if results.get('migration'):
            report = results['migration'].get('migration_report', {})
            stats = report.get('statistics', {})
            
            summary['total_elements'] = stats.get('elements_processed', 0)
            summary['migrated'] = stats.get('successful_migrations', 0)
            summary['partial'] = stats.get('partial_migrations', 0)
            summary['failed'] = stats.get('failed_migrations', 0)
            
            if summary['total_elements'] > 0:
                summary['success_rate'] = (summary['migrated'] / summary['total_elements']) * 100
            
            summary['manual_work_required'] = summary['partial'] > 0 or summary['failed'] > 0
            summary['estimated_effort'] = report.get('estimated_work', 'Unknown')
        
        return summary
    
    def print_report(self, results: Dict[str, Any]):
        """Print human-readable report"""
        print("\n" + "="*70)
        print(" BPMN TO TALLYFY MIGRATION REPORT")
        print("="*70)
        
        print(f"\nFile: {results['bpmn_file']}")
        print(f"Status: {results['status'].upper()}")
        
        # Complexity analysis
        if results.get('complexity'):
            comp = results['complexity']
            print(f"\n📊 Complexity Analysis:")
            print(f"  Score: {comp.get('score', 0)}")
            print(f"  Recommendation: {comp.get('recommendation', 'Unknown')}")
            
            if comp.get('unsupported_elements'):
                print(f"  ⚠️ Unsupported elements found: {len(comp['unsupported_elements'])}")
        
        # Migration summary
        if results.get('summary'):
            summary = results['summary']
            print(f"\n📈 Migration Results:")
            print(f"  Total Elements: {summary['total_elements']}")
            print(f"  Successfully Migrated: {summary['migrated']}")
            print(f"  Partial Migration: {summary['partial']}")
            print(f"  Failed: {summary['failed']}")
            print(f"  Success Rate: {summary['success_rate']:.1f}%")
            
            if summary['manual_work_required']:
                print(f"\n⚠️ Manual Work Required!")
                print(f"  Estimated Effort: {summary['estimated_effort']}")
        
        # Template info
        if results.get('template'):
            template = results['template']
            if isinstance(template, list):
                print(f"\n📋 Generated {len(template)} Templates")
            else:
                print(f"\n📋 Generated Template:")
                print(f"  Title: {template.get('title')}")
                print(f"  Steps: {len(template.get('steps', []))}")
                print(f"  Automations: {len(template.get('automated_actions', []))}")
                print(f"  Form Fields: {sum(len(s.get('captures', [])) for s in template.get('steps', []))}")
        
        # Warnings
        if results.get('warnings'):
            print(f"\n⚠️ Warnings:")
            for warning in results['warnings']:
                print(f"  • {warning}")
        
        # Errors
        if results.get('errors'):
            print(f"\n❌ Errors:")
            for error in results['errors']:
                print(f"  • {error}")
        
        # Output file
        if results.get('output_file'):
            print(f"\n💾 Template saved to: {results['output_file']}")
        
        print("\n" + "="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='BPMN to Tallyfy Migration Tool - Complete Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze complexity only
  %(prog)s --analyze process.bpmn
  
  # Full migration with output
  %(prog)s process.bpmn -o template.json
  
  # Migration with custom config
  %(prog)s process.bpmn --tags automation bpmn --public

Note: This tool can migrate ~20-30%% of BPMN patterns automatically.
      Complex patterns require manual configuration.
      See MIGRATION_GAPS_AND_ISSUES.md for details.
        """
    )
    
    parser.add_argument(
        'bpmn_file',
        help='BPMN 2.0 XML file to migrate'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output JSON file for Tallyfy template'
    )
    
    parser.add_argument(
        '-a', '--analyze',
        action='store_true',
        help='Only analyze complexity, don\'t migrate'
    )
    
    parser.add_argument(
        '--tags',
        nargs='+',
        help='Tags for the template',
        default=['bpmn-migration']
    )
    
    parser.add_argument(
        '--public',
        action='store_true',
        help='Make template public'
    )
    
    parser.add_argument(
        '--allow-guests',
        action='store_true',
        help='Allow guest access'
    )
    
    parser.add_argument(
        '--archive-days',
        type=int,
        default=30,
        help='Auto-archive after days (default: 30)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check file exists
    if not os.path.exists(args.bpmn_file):
        print(f"❌ Error: File '{args.bpmn_file}' not found")
        sys.exit(1)
    
    # Create migrator
    migrator = CompleteBPMNMigrator()
    
    # Analyze only?
    if args.analyze:
        print(f"🔍 Analyzing {args.bpmn_file}...")
        analysis = migrator.analyze(args.bpmn_file)
        
        print("\n📊 Complexity Analysis Results:")
        print(f"  Score: {analysis.get('score', 0)}")
        print(f"  Recommendation: {analysis.get('recommendation', 'Unknown')}")
        
        if analysis.get('unsupported_elements'):
            print(f"\n⚠️ Unsupported Elements:")
            for elem in analysis['unsupported_elements'][:10]:
                print(f"  • {elem['type']}: {elem.get('name', 'Unnamed')}")
        
        if analysis.get('estimated_effort'):
            print(f"\n⏱️ Estimated Effort: {analysis['estimated_effort']}")
        
        sys.exit(0)
    
    # Full migration
    print(f"🚀 Starting migration of {args.bpmn_file}...")
    
    # Build config
    config = {
        'tags': args.tags,
        'is_public': args.public,
        'allow_guests': args.allow_guests,
        'auto_archive_days': args.archive_days
    }
    
    # Run migration
    results = migrator.migrate(args.bpmn_file, args.output, config)
    
    # Print report
    migrator.print_report(results)
    
    # Exit code based on status
    if results['status'] == 'completed':
        if results.get('summary', {}).get('manual_work_required'):
            print("\n⚠️ Migration completed with warnings. Manual work required.")
            sys.exit(0)
        else:
            print("\n✅ Migration completed successfully!")
            sys.exit(0)
    else:
        print("\n❌ Migration failed. Check errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()