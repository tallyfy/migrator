"""
BPMN Complexity Analyzer
Realistic assessment of BPMN to Tallyfy migration feasibility
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class BPMNComplexityAnalyzer:
    """
    Analyzes BPMN diagrams to determine migration complexity and feasibility
    """
    
    # Elements we can fully support
    FULLY_SUPPORTED = {
        'userTask': 1,           # User tasks map directly
        'manualTask': 1,          # Manual tasks map directly  
        'startEvent': 0.5,        # Only 'none' type
        'endEvent': 0.5,          # Only 'none' type
        'exclusiveGateway': 2,    # XOR maps to conditional rules
        'sequenceFlow': 0.5,      # Basic flow
        'lane': 1,                # Maps to groups
    }
    
    # Elements we can partially support
    PARTIALLY_SUPPORTED = {
        'serviceTask': 3,         # Can map to webhook
        'sendTask': 2,            # Can map to email
        'receiveTask': 3,         # Limited support via approval
        'parallelGateway': 4,     # Visual grouping only
        'businessRuleTask': 3,    # Requires manual config
        'scriptTask': 4,          # No direct equivalent
        'callActivity': 5,        # No subprocess support
        'subProcess': 6,          # Must inline if simple
        'intermediateCatchEvent': 4,  # Limited support
        'intermediateThrowEvent': 4,  # Limited support
    }
    
    # Elements we cannot support
    NOT_SUPPORTED = {
        'inclusiveGateway': 10,       # Complex synchronization
        'eventBasedGateway': 10,      # Race conditions
        'complexGateway': 15,         # Custom logic
        'boundaryEvent': 8,           # No boundary event support
        'eventSubProcess': 12,        # No event subprocess
        'transaction': 15,            # No transaction support
        'compensationEvent': 10,      # No compensation
        'escalationEvent': 8,         # No escalation
        'errorEvent': 8,              # Limited error handling
        'signalEvent': 8,             # No signal broadcasting
        'messageEvent': 6,            # Limited message support
        'conditionalEvent': 8,        # No conditional events
        'multiInstanceLoopCharacteristics': 12,  # No multi-instance
        'standardLoopCharacteristics': 10,       # No loops
        'adHocSubProcess': 15,        # No ad-hoc support
        'dataObject': 4,              # Limited data modeling
        'dataStore': 5,               # No persistent data
        'messageFlow': 6,             # Limited cross-pool
    }
    
    def __init__(self):
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        }
        self.reset()
    
    def reset(self):
        """Reset analysis state"""
        self.elements_found = {
            'supported': [],
            'partial': [],
            'unsupported': []
        }
        self.complexity_score = 0
        self.element_count = 0
        self.warnings = []
        self.recommendations = []
        self.critical_issues = []
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a BPMN file and return feasibility assessment
        
        Returns:
            Dictionary with analysis results
        """
        self.reset()
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Register namespaces
            for prefix, uri in self.namespaces.items():
                ET.register_namespace(prefix, uri)
            
            # Analyze all processes
            for process in root.findall('.//bpmn:process', self.namespaces):
                self._analyze_process(process)
            
            # Analyze collaborations (pools, message flows)
            for collab in root.findall('.//bpmn:collaboration', self.namespaces):
                self._analyze_collaboration(collab)
            
            # Calculate final metrics
            return self._generate_report()
            
        except Exception as e:
            logger.error(f"Failed to analyze BPMN file: {e}")
            return {
                'error': str(e),
                'feasibility': 0,
                'complexity': 'error'
            }
    
    def _analyze_process(self, process_elem):
        """Analyze a single process"""
        
        # Check all element types
        for elem_type, complexity in self.FULLY_SUPPORTED.items():
            elements = process_elem.findall(f'.//bpmn:{elem_type}', self.namespaces)
            for elem in elements:
                self.elements_found['supported'].append({
                    'type': elem_type,
                    'id': elem.get('id'),
                    'name': elem.get('name'),
                    'complexity': complexity
                })
                self.complexity_score += complexity
                self.element_count += 1
        
        for elem_type, complexity in self.PARTIALLY_SUPPORTED.items():
            elements = process_elem.findall(f'.//bpmn:{elem_type}', self.namespaces)
            for elem in elements:
                self.elements_found['partial'].append({
                    'type': elem_type,
                    'id': elem.get('id'),
                    'name': elem.get('name'),
                    'complexity': complexity
                })
                self.complexity_score += complexity
                self.element_count += 1
                self.warnings.append(
                    f"Partial support for {elem_type}: '{elem.get('name', elem.get('id'))}' - manual configuration required"
                )
        
        for elem_type, complexity in self.NOT_SUPPORTED.items():
            elements = process_elem.findall(f'.//bpmn:{elem_type}', self.namespaces)
            for elem in elements:
                self.elements_found['unsupported'].append({
                    'type': elem_type,
                    'id': elem.get('id'),
                    'name': elem.get('name'),
                    'complexity': complexity
                })
                self.complexity_score += complexity
                self.element_count += 1
                self.critical_issues.append(
                    f"UNSUPPORTED: {elem_type} '{elem.get('name', elem.get('id'))}' cannot be migrated"
                )
        
        # Check for complex patterns
        self._check_complex_patterns(process_elem)
    
    def _analyze_collaboration(self, collab_elem):
        """Analyze collaboration elements"""
        
        # Check for multiple pools (complexity indicator)
        participants = collab_elem.findall('bpmn:participant', self.namespaces)
        if len(participants) > 1:
            self.warnings.append(f"Multiple pools detected ({len(participants)}). Each pool should be migrated as a separate Tallyfy template.")
            self.complexity_score += 5 * (len(participants) - 1)
        
        # Check message flows
        message_flows = collab_elem.findall('bpmn:messageFlow', self.namespaces)
        if message_flows:
            self.warnings.append(f"{len(message_flows)} message flows detected. These will need webhook configuration in Tallyfy.")
            self.complexity_score += 3 * len(message_flows)
    
    def _check_complex_patterns(self, process_elem):
        """Check for complex patterns that are hard to migrate"""
        
        # Check for loops (back edges in flow)
        sequence_flows = process_elem.findall('.//bpmn:sequenceFlow', self.namespaces)
        flow_graph = {}
        for flow in sequence_flows:
            source = flow.get('sourceRef')
            target = flow.get('targetRef')
            if source not in flow_graph:
                flow_graph[source] = []
            flow_graph[source].append(target)
        
        if self._has_cycles(flow_graph):
            self.critical_issues.append("LOOP DETECTED: Process contains loops which cannot be directly migrated to Tallyfy")
            self.complexity_score += 20
        
        # Check for event subprocesses
        event_subs = process_elem.findall(".//bpmn:subProcess[@triggeredByEvent='true']", self.namespaces)
        if event_subs:
            self.critical_issues.append(f"EVENT SUBPROCESS: {len(event_subs)} event subprocess(es) found - these have no Tallyfy equivalent")
            self.complexity_score += 15 * len(event_subs)
        
        # Check for boundary events
        boundary_events = process_elem.findall('.//bpmn:boundaryEvent', self.namespaces)
        if boundary_events:
            self.critical_issues.append(f"BOUNDARY EVENTS: {len(boundary_events)} boundary event(s) found - manual workarounds required")
            self.complexity_score += 8 * len(boundary_events)
        
        # Check for complex conditions
        conditions = process_elem.findall('.//bpmn:conditionExpression', self.namespaces)
        complex_conditions = [c for c in conditions if c.text and ('&&' in c.text or '||' in c.text or 'function' in c.text)]
        if complex_conditions:
            self.warnings.append(f"Complex condition expressions found ({len(complex_conditions)}). These will need simplification.")
            self.complexity_score += 2 * len(complex_conditions)
    
    def _has_cycles(self, graph: Dict[str, List[str]]) -> bool:
        """Simple cycle detection"""
        visited = set()
        rec_stack = set()
        
        def visit(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if visit(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if visit(node):
                    return True
        return False
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate analysis report"""
        
        # Calculate feasibility percentage
        if self.element_count == 0:
            feasibility = 0
        else:
            supported_count = len(self.elements_found['supported'])
            partial_count = len(self.elements_found['partial'])
            unsupported_count = len(self.elements_found['unsupported'])
            
            # Weighted feasibility
            feasibility = (
                (supported_count * 100) +
                (partial_count * 50) +
                (unsupported_count * 0)
            ) / self.element_count
        
        # Determine complexity category
        if self.complexity_score < 10:
            complexity = 'simple'
            effort_hours = 1
        elif self.complexity_score < 30:
            complexity = 'moderate'
            effort_hours = 4
        elif self.complexity_score < 60:
            complexity = 'complex'
            effort_hours = 8
        else:
            complexity = 'very_complex'
            effort_hours = 16
        
        # Generate recommendations
        if feasibility < 30:
            self.recommendations.append("This process is too complex for automated migration. Consider redesigning for Tallyfy.")
        elif feasibility < 60:
            self.recommendations.append("Partial migration possible. Significant manual configuration will be required.")
        else:
            self.recommendations.append("Good candidate for migration. Most elements can be transformed.")
        
        if self.critical_issues:
            self.recommendations.append("Critical issues must be addressed through process redesign.")
        
        if len(self.elements_found['unsupported']) > 5:
            self.recommendations.append("Consider breaking this process into smaller, simpler templates.")
        
        return {
            'feasibility_percentage': round(feasibility, 1),
            'complexity': complexity,
            'complexity_score': self.complexity_score,
            'element_count': self.element_count,
            'supported_elements': len(self.elements_found['supported']),
            'partial_elements': len(self.elements_found['partial']),
            'unsupported_elements': len(self.elements_found['unsupported']),
            'estimated_manual_effort_hours': effort_hours,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'element_breakdown': self.elements_found
        }
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted report"""
        
        print("\n" + "="*60)
        print("BPMN MIGRATION FEASIBILITY ANALYSIS")
        print("="*60)
        
        print(f"\n📊 Overall Assessment:")
        print(f"  Feasibility: {report['feasibility_percentage']}%")
        print(f"  Complexity: {report['complexity'].upper()}")
        print(f"  Manual Effort: ~{report['estimated_manual_effort_hours']} hours")
        
        print(f"\n📈 Element Breakdown ({report['element_count']} total):")
        print(f"  ✅ Fully Supported: {report['supported_elements']}")
        print(f"  ⚠️  Partially Supported: {report['partial_elements']}")
        print(f"  ❌ Not Supported: {report['unsupported_elements']}")
        
        if report['critical_issues']:
            print(f"\n🚨 Critical Issues:")
            for issue in report['critical_issues']:
                print(f"  • {issue}")
        
        if report['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in report['warnings'][:5]:  # Show first 5
                print(f"  • {warning}")
            if len(report['warnings']) > 5:
                print(f"  ... and {len(report['warnings']) - 5} more")
        
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print("\n" + "="*60)


def main():
    """Command line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python bpmn_complexity_analyzer.py <bpmn_file>")
        sys.exit(1)
    
    analyzer = BPMNComplexityAnalyzer()
    report = analyzer.analyze_file(sys.argv[1])
    
    if 'error' in report:
        print(f"Error analyzing file: {report['error']}")
        sys.exit(1)
    
    analyzer.print_report(report)
    
    # Return exit code based on feasibility
    if report['feasibility_percentage'] < 30:
        sys.exit(2)  # Not feasible
    elif report['feasibility_percentage'] < 60:
        sys.exit(1)  # Partially feasible
    else:
        sys.exit(0)  # Feasible


if __name__ == '__main__':
    main()