#!/usr/bin/env python3
"""
BPMN to Tallyfy Migration Assistant
AI-powered migration tool using Claude API for intelligent transformation decisions
"""

import os
import sys
import json
import logging
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationDecision:
    """Represents an AI migration decision"""
    element_type: str
    element_id: str
    element_name: str
    confidence: float
    strategy: str
    tallyfy_mapping: Dict[str, Any]
    manual_steps: List[str]
    warnings: List[str]
    ai_reasoning: str


class ClaudeAIMigrationAssistant:
    """AI-powered migration assistant using Claude API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Claude API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            logger.warning("No Anthropic API key provided. AI features will be limited.")
            self.client = None
        else:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Claude AI assistant initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude API: {e}")
                self.client = None
        
        self.decisions_cache = {}
        self.stats = {
            'ai_calls': 0,
            'cached_decisions': 0,
            'fallback_decisions': 0
        }
    
    def analyze_bpmn_element(self, element: Dict[str, Any], context: Dict[str, Any]) -> MigrationDecision:
        """
        Analyze a BPMN element and determine migration strategy using AI
        
        Args:
            element: BPMN element data
            context: Surrounding process context
            
        Returns:
            MigrationDecision with AI recommendations
        """
        # Check cache first
        cache_key = f"{element.get('type')}_{element.get('id')}"
        if cache_key in self.decisions_cache:
            self.stats['cached_decisions'] += 1
            return self.decisions_cache[cache_key]
        
        # Use AI if available
        if self.client:
            decision = self._ai_analyze_element(element, context)
        else:
            decision = self._fallback_analyze_element(element, context)
            self.stats['fallback_decisions'] += 1
        
        # Cache decision
        self.decisions_cache[cache_key] = decision
        return decision
    
    def _ai_analyze_element(self, element: Dict[str, Any], context: Dict[str, Any]) -> MigrationDecision:
        """Use Claude AI to analyze element"""
        
        self.stats['ai_calls'] += 1
        
        # Prepare prompt
        prompt = self._create_analysis_prompt(element, context)
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                system="""You are an expert in BPMN to Tallyfy migration. Analyze BPMN elements and provide migration strategies.
                
Tallyfy supports:
- 5 task types: task, approval, expiring, email, expiring_email
- 10 field types: text, textarea, radio, dropdown, multiselect, date, email, file, table, assignees_form
- Conditional rules: IF-THEN with show/hide actions
- No true parallelism, loops, or complex events

Respond with JSON only, following this structure:
{
    "confidence": 0.0-1.0,
    "strategy": "direct|transform|partial|unsupported",
    "tallyfy_mapping": {...},
    "manual_steps": [...],
    "warnings": [...],
    "reasoning": "..."
}""",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse AI response
            result = self._parse_ai_response(response.content[0].text, element)
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_analyze_element(element, context)
    
    def _create_analysis_prompt(self, element: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create detailed prompt for AI analysis"""
        
        return f"""Analyze this BPMN element for Tallyfy migration:

Element Type: {element.get('type')}
Element ID: {element.get('id')}
Element Name: {element.get('name', 'Unnamed')}

Element Details:
{json.dumps(element, indent=2)}

Context:
- Previous element: {context.get('previous', 'None')}
- Next elements: {context.get('next', [])}
- Lane/Pool: {context.get('lane', 'None')}
- Process complexity: {context.get('complexity', 'Unknown')}

Determine the best migration strategy and provide specific Tallyfy mapping."""
    
    def _parse_ai_response(self, response_text: str, element: Dict[str, Any]) -> MigrationDecision:
        """Parse AI response into MigrationDecision"""
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)
            
            return MigrationDecision(
                element_type=element.get('type'),
                element_id=element.get('id'),
                element_name=element.get('name', 'Unnamed'),
                confidence=float(data.get('confidence', 0.5)),
                strategy=data.get('strategy', 'unsupported'),
                tallyfy_mapping=data.get('tallyfy_mapping', {}),
                manual_steps=data.get('manual_steps', []),
                warnings=data.get('warnings', []),
                ai_reasoning=data.get('reasoning', 'No reasoning provided')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return self._fallback_analyze_element(element, {})
    
    def _fallback_analyze_element(self, element: Dict[str, Any], context: Dict[str, Any]) -> MigrationDecision:
        """Fallback analysis without AI"""
        
        element_type = element.get('type', '')
        
        # Simple mapping rules
        if element_type == 'userTask':
            return MigrationDecision(
                element_type=element_type,
                element_id=element.get('id'),
                element_name=element.get('name', 'User Task'),
                confidence=0.9,
                strategy='direct',
                tallyfy_mapping={
                    'type': 'task',
                    'task_type': 'task',
                    'title': element.get('name', 'Task')
                },
                manual_steps=[],
                warnings=[],
                ai_reasoning='Direct mapping: userTask to task'
            )
        
        elif element_type == 'exclusiveGateway':
            return MigrationDecision(
                element_type=element_type,
                element_id=element.get('id'),
                element_name=element.get('name', 'Decision'),
                confidence=0.8,
                strategy='transform',
                tallyfy_mapping={
                    'type': 'rules',
                    'rule_type': 'conditional',
                    'conditions': []
                },
                manual_steps=['Configure gateway conditions as IF-THEN rules'],
                warnings=['Gateway conditions need manual configuration'],
                ai_reasoning='Transform XOR gateway to conditional rules'
            )
        
        elif element_type == 'parallelGateway':
            return MigrationDecision(
                element_type=element_type,
                element_id=element.get('id'),
                element_name=element.get('name', 'Parallel'),
                confidence=0.5,
                strategy='partial',
                tallyfy_mapping={
                    'type': 'parallel_visual',
                    'note': 'Steps at same position'
                },
                manual_steps=['Create steps at same position for visual parallelism'],
                warnings=['No true parallel execution in Tallyfy'],
                ai_reasoning='Simulate parallel with same position'
            )
        
        else:
            return MigrationDecision(
                element_type=element_type,
                element_id=element.get('id'),
                element_name=element.get('name', 'Unknown'),
                confidence=0.1,
                strategy='unsupported',
                tallyfy_mapping={},
                manual_steps=['Element cannot be migrated automatically'],
                warnings=[f'{element_type} has no Tallyfy equivalent'],
                ai_reasoning='Element type not supported'
            )
    
    def suggest_process_optimization(self, bpmn_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to suggest process optimizations for Tallyfy"""
        
        if not self.client:
            return {
                'optimizations': ['AI not available - manual optimization recommended'],
                'complexity_reduction': [],
                'tallyfy_best_practices': []
            }
        
        prompt = f"""Analyze this BPMN process and suggest optimizations for Tallyfy migration:

Process Statistics:
- Tasks: {bpmn_data.get('task_count', 0)}
- Gateways: {bpmn_data.get('gateway_count', 0)}
- Events: {bpmn_data.get('event_count', 0)}
- Unsupported elements: {bpmn_data.get('unsupported_count', 0)}

Suggest:
1. How to simplify the process for Tallyfy
2. Which elements to combine or remove
3. Alternative approaches for unsupported patterns
4. Tallyfy best practices to follow

Respond with specific, actionable recommendations in JSON format."""
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1500,
                temperature=0.3,
                system="You are a process optimization expert specializing in BPMN to Tallyfy migration.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            text = response.content[0].text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {'recommendations': text}
                
        except Exception as e:
            logger.error(f"Optimization suggestion failed: {e}")
            return {
                'error': str(e),
                'recommendations': 'Manual optimization recommended'
            }


class BPMNToTallyfyMigrationAssistant:
    """Main migration assistant combining analysis and transformation"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize migration assistant"""
        self.ai_assistant = ClaudeAIMigrationAssistant(api_key)
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI'
        }
        self.migration_results = {
            'source_file': None,
            'timestamp': datetime.utcnow().isoformat(),
            'elements_analyzed': 0,
            'successful_migrations': [],
            'partial_migrations': [],
            'failed_migrations': [],
            'tallyfy_template': {},
            'statistics': {},
            'ai_stats': {}
        }
    
    def migrate_bpmn_file(self, file_path: str) -> Dict[str, Any]:
        """
        Main migration method
        
        Args:
            file_path: Path to BPMN file
            
        Returns:
            Migration results with Tallyfy template
        """
        logger.info(f"Starting migration of {file_path}")
        self.migration_results['source_file'] = file_path
        
        try:
            # Parse BPMN
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract processes
            processes = self._extract_processes(root)
            
            # Analyze and migrate each process
            for process in processes:
                self._migrate_process(process)
            
            # Generate Tallyfy template
            self.migration_results['tallyfy_template'] = self._generate_tallyfy_template()
            
            # Get AI optimization suggestions
            if self.ai_assistant.client:
                optimization = self.ai_assistant.suggest_process_optimization({
                    'task_count': len(self.migration_results['successful_migrations']),
                    'gateway_count': sum(1 for e in self.migration_results['elements_analyzed'] 
                                        if 'gateway' in str(e).lower()),
                    'unsupported_count': len(self.migration_results['failed_migrations'])
                })
                self.migration_results['optimization_suggestions'] = optimization
            
            # Add statistics
            self.migration_results['statistics'] = self._calculate_statistics()
            self.migration_results['ai_stats'] = self.ai_assistant.stats
            
            return self.migration_results
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.migration_results['error'] = str(e)
            return self.migration_results
    
    def _extract_processes(self, root) -> List[Dict[str, Any]]:
        """Extract all processes from BPMN"""
        processes = []
        
        for process in root.findall('.//bpmn:process', self.namespaces):
            process_data = {
                'id': process.get('id'),
                'name': process.get('name', 'Unnamed Process'),
                'elements': []
            }
            
            # Extract all elements
            for child in process:
                element_type = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                element_data = {
                    'type': element_type,
                    'id': child.get('id'),
                    'name': child.get('name'),
                    'attributes': dict(child.attrib)
                }
                process_data['elements'].append(element_data)
            
            processes.append(process_data)
        
        return processes
    
    def _migrate_process(self, process: Dict[str, Any]):
        """Migrate a single process"""
        logger.info(f"Migrating process: {process['name']}")
        
        for element in process['elements']:
            self.migration_results['elements_analyzed'] += 1
            
            # Get context for AI
            context = self._build_element_context(element, process)
            
            # Get migration decision from AI
            decision = self.ai_assistant.analyze_bpmn_element(element, context)
            
            # Categorize result
            if decision.strategy == 'direct':
                self.migration_results['successful_migrations'].append(decision)
            elif decision.strategy in ['transform', 'partial']:
                self.migration_results['partial_migrations'].append(decision)
            else:
                self.migration_results['failed_migrations'].append(decision)
    
    def _build_element_context(self, element: Dict[str, Any], process: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for element analysis"""
        return {
            'process_name': process['name'],
            'process_id': process['id'],
            'total_elements': len(process['elements']),
            'element_position': process['elements'].index(element)
        }
    
    def _generate_tallyfy_template(self) -> Dict[str, Any]:
        """Generate Tallyfy template from migration decisions"""
        
        template = {
            'title': 'Migrated Process',
            'description': 'Automatically migrated from BPMN',
            'steps': [],
            'rules': [],
            'groups': [],
            'captures': []
        }
        
        position = 0
        
        # Add successful migrations as steps
        for decision in self.migration_results['successful_migrations']:
            if decision.tallyfy_mapping.get('type') == 'task':
                step = {
                    'position': position,
                    'title': decision.tallyfy_mapping.get('title', decision.element_name),
                    'task_type': decision.tallyfy_mapping.get('task_type', 'task'),
                    'bpmn_ref': decision.element_id
                }
                template['steps'].append(step)
                position += 1
            elif decision.tallyfy_mapping.get('type') == 'rules':
                template['rules'].append(decision.tallyfy_mapping)
        
        # Add partial migrations with warnings
        for decision in self.migration_results['partial_migrations']:
            if decision.tallyfy_mapping:
                if 'type' in decision.tallyfy_mapping:
                    mapping = decision.tallyfy_mapping.copy()
                    mapping['warnings'] = decision.warnings
                    mapping['manual_steps'] = decision.manual_steps
                    
                    if mapping['type'] == 'parallel_visual':
                        # Create steps at same position
                        for i in range(2):  # Placeholder for parallel branches
                            step = {
                                'position': position,
                                'title': f"Parallel Branch {i+1}",
                                'task_type': 'task',
                                'note': 'Configure parallel tasks',
                                'bpmn_ref': decision.element_id
                            }
                            template['steps'].append(step)
                    else:
                        template['steps'].append(mapping)
                        position += 1
        
        return template
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate migration statistics"""
        
        total = self.migration_results['elements_analyzed']
        if total == 0:
            return {'success_rate': 0}
        
        return {
            'total_elements': total,
            'success_rate': len(self.migration_results['successful_migrations']) / total * 100,
            'partial_rate': len(self.migration_results['partial_migrations']) / total * 100,
            'failure_rate': len(self.migration_results['failed_migrations']) / total * 100,
            'ai_used': self.ai_assistant.client is not None,
            'manual_work_required': len(self.migration_results['partial_migrations']) > 0 or 
                                   len(self.migration_results['failed_migrations']) > 0
        }
    
    def generate_report(self) -> str:
        """Generate human-readable migration report"""
        
        report = []
        report.append("="*60)
        report.append("BPMN TO TALLYFY MIGRATION REPORT")
        report.append("="*60)
        report.append(f"\nSource File: {self.migration_results['source_file']}")
        report.append(f"Timestamp: {self.migration_results['timestamp']}")
        
        stats = self.migration_results.get('statistics', {})
        report.append(f"\n📊 Statistics:")
        report.append(f"  Total Elements: {stats.get('total_elements', 0)}")
        report.append(f"  Success Rate: {stats.get('success_rate', 0):.1f}%")
        report.append(f"  Partial Success: {stats.get('partial_rate', 0):.1f}%")
        report.append(f"  Failed: {stats.get('failure_rate', 0):.1f}%")
        report.append(f"  AI Assistance: {'Yes' if stats.get('ai_used') else 'No'}")
        
        if self.migration_results.get('successful_migrations'):
            report.append(f"\n✅ Successfully Migrated ({len(self.migration_results['successful_migrations'])}):")
            for decision in self.migration_results['successful_migrations'][:5]:
                report.append(f"  • {decision.element_name} ({decision.element_type}) - {decision.confidence*100:.0f}% confidence")
        
        if self.migration_results.get('partial_migrations'):
            report.append(f"\n⚠️ Partially Migrated ({len(self.migration_results['partial_migrations'])}):")
            for decision in self.migration_results['partial_migrations'][:5]:
                report.append(f"  • {decision.element_name} ({decision.element_type})")
                for step in decision.manual_steps[:2]:
                    report.append(f"    → {step}")
        
        if self.migration_results.get('failed_migrations'):
            report.append(f"\n❌ Failed to Migrate ({len(self.migration_results['failed_migrations'])}):")
            for decision in self.migration_results['failed_migrations'][:5]:
                report.append(f"  • {decision.element_name} ({decision.element_type})")
                for warning in decision.warnings[:1]:
                    report.append(f"    ⚠ {warning}")
        
        if self.migration_results.get('optimization_suggestions'):
            report.append(f"\n💡 AI Optimization Suggestions:")
            opt = self.migration_results['optimization_suggestions']
            if isinstance(opt, dict):
                for key, value in opt.items():
                    if isinstance(value, list):
                        report.append(f"  {key}:")
                        for item in value[:3]:
                            report.append(f"    • {item}")
                    else:
                        report.append(f"  • {value}")
        
        report.append(f"\n🤖 AI Usage Statistics:")
        ai_stats = self.migration_results.get('ai_stats', {})
        report.append(f"  API Calls: {ai_stats.get('ai_calls', 0)}")
        report.append(f"  Cached Decisions: {ai_stats.get('cached_decisions', 0)}")
        report.append(f"  Fallback Decisions: {ai_stats.get('fallback_decisions', 0)}")
        
        report.append("\n" + "="*60)
        
        return "\n".join(report)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='BPMN to Tallyfy Migration Assistant with AI'
    )
    
    parser.add_argument(
        'bpmn_file',
        help='Path to BPMN file to migrate'
    )
    
    parser.add_argument(
        '--api-key',
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)',
        default=None
    )
    
    parser.add_argument(
        '--output',
        help='Output file for Tallyfy template JSON',
        default=None
    )
    
    parser.add_argument(
        '--report',
        help='Generate detailed report',
        action='store_true'
    )
    
    parser.add_argument(
        '--verbose',
        help='Verbose output',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check for API key
    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  Warning: No Anthropic API key provided. AI features will be limited.")
        print("   Set ANTHROPIC_API_KEY environment variable or use --api-key flag")
        response = input("Continue without AI? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Create migration assistant
    assistant = BPMNToTallyfyMigrationAssistant(api_key)
    
    # Perform migration
    print(f"\n🚀 Starting migration of {args.bpmn_file}...")
    results = assistant.migrate_bpmn_file(args.bpmn_file)
    
    # Save output if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"✅ Migration results saved to {output_path}")
    
    # Generate report
    if args.report or not args.output:
        report = assistant.generate_report()
        print(report)
    
    # Print summary
    stats = results.get('statistics', {})
    if stats.get('success_rate', 0) >= 70:
        print("\n✅ Migration completed successfully!")
    elif stats.get('success_rate', 0) >= 40:
        print("\n⚠️  Migration completed with warnings. Manual configuration required.")
    else:
        print("\n❌ Migration has significant issues. Consider process redesign for Tallyfy.")
    
    sys.exit(0)


if __name__ == '__main__':
    main()