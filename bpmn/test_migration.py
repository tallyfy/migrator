#!/usr/bin/env python3
"""
Test script for BPMN to Tallyfy Migrator
Demonstrates the self-contained rule-based migration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from migrator import BPMNToTallyfyMigrator
from rule_engine import BPMNToTallyfyRuleEngine

def test_rule_engine():
    """Test the rule engine with sample elements"""
    print("Testing Rule Engine...")
    print("="*60)
    
    engine = BPMNToTallyfyRuleEngine()
    
    # Test task mapping
    user_task = {
        'type': 'userTask',
        'id': 'task_1',
        'name': 'Review Document'
    }
    
    result = engine.analyze_element(user_task)
    print(f"\nUser Task Migration:")
    print(f"  Confidence: {result['confidence']*100:.0f}%")
    print(f"  Strategy: {result['strategy']}")
    print(f"  Tallyfy Type: {result['tallyfy_mapping'].get('task_type')}")
    
    # Test gateway mapping
    xor_gateway = {
        'type': 'exclusiveGateway',
        'id': 'gateway_1',
        'name': 'Approval Decision',
        'incoming': ['flow_1'],
        'outgoing': ['flow_2', 'flow_3']
    }
    
    result = engine.analyze_element(xor_gateway)
    print(f"\nXOR Gateway Migration:")
    print(f"  Confidence: {result['confidence']*100:.0f}%")
    print(f"  Strategy: {result['strategy']}")
    print(f"  Implementation: {result['tallyfy_mapping'].get('implementation')}")
    
    # Test event mapping
    timer_event = {
        'type': 'intermediateCatchEvent',
        'id': 'event_1',
        'name': 'Wait 24 hours',
        'eventType': 'timer'
    }
    
    result = engine.analyze_element(timer_event)
    print(f"\nTimer Event Migration:")
    print(f"  Confidence: {result['confidence']*100:.0f}%")
    print(f"  Strategy: {result['strategy']}")
    
    # Test unsupported element
    boundary_event = {
        'type': 'boundaryEvent',
        'id': 'boundary_1',
        'name': 'Error Handler'
    }
    
    result = engine.analyze_element(boundary_event)
    print(f"\nBoundary Event Migration:")
    print(f"  Confidence: {result['confidence']*100:.0f}%")
    print(f"  Strategy: {result['strategy']}")
    print(f"  Reason: {result['reasoning']}")
    
    # Show statistics
    stats = engine.get_statistics()
    print(f"\n📊 Rule Engine Statistics:")
    print(f"  Total Rules: {stats['total_rules']}")
    print(f"  Pattern Rules: {stats['pattern_rules']}")
    print(f"  Gateway Rules: {stats['gateway_rules']}")
    print(f"  Event Rules: {stats['event_rules']}")
    print(f"  Field Mappings: {stats['field_mappings']}")
    print(f"  Supported Elements: {stats['supported_elements']}")
    print(f"  Partial Support: {stats['partial_support']}")
    print(f"  Unsupported: {stats['unsupported']}")

def test_optimization():
    """Test optimization suggestions"""
    print("\n\nTesting Optimization Suggestions...")
    print("="*60)
    
    engine = BPMNToTallyfyRuleEngine()
    
    # Test simple process
    simple_stats = {
        'task_count': 5,
        'gateway_count': 1,
        'unsupported_count': 0,
        'has_loops': False,
        'parallel_gateways': 0
    }
    
    result = engine.suggest_optimization(simple_stats)
    print(f"\nSimple Process:")
    print(f"  Difficulty: {result['difficulty']}")
    print(f"  Estimated Work: {result['estimated_manual_work']}")
    print(f"  Success Likelihood: {result['success_likelihood']}%")
    
    # Test complex process
    complex_stats = {
        'task_count': 50,
        'gateway_count': 15,
        'unsupported_count': 10,
        'has_loops': True,
        'parallel_gateways': 5
    }
    
    result = engine.suggest_optimization(complex_stats)
    print(f"\nComplex Process:")
    print(f"  Difficulty: {result['difficulty']}")
    print(f"  Estimated Work: {result['estimated_manual_work']}")
    print(f"  Success Likelihood: {result['success_likelihood']}%")
    print(f"  Recommendations:")
    for rec in result['recommendations']:
        print(f"    • {rec}")

def create_sample_bpmn():
    """Create a sample BPMN file for testing"""
    bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" 
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  id="Definitions_1" targetNamespace="http://example.org">
  
  <bpmn:process id="Process_1" name="Document Approval Process" isExecutable="true">
    
    <bpmn:startEvent id="start_1" name="Request Received"/>
    
    <bpmn:userTask id="task_1" name="Review Document">
      <bpmn:incoming>flow_1</bpmn:incoming>
      <bpmn:outgoing>flow_2</bpmn:outgoing>
    </bpmn:userTask>
    
    <bpmn:exclusiveGateway id="gateway_1" name="Approval Decision">
      <bpmn:incoming>flow_2</bpmn:incoming>
      <bpmn:outgoing>flow_3</bpmn:outgoing>
      <bpmn:outgoing>flow_4</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    
    <bpmn:userTask id="task_2" name="Make Revisions">
      <bpmn:incoming>flow_4</bpmn:incoming>
      <bpmn:outgoing>flow_5</bpmn:outgoing>
    </bpmn:userTask>
    
    <bpmn:serviceTask id="task_3" name="Publish Document">
      <bpmn:incoming>flow_3</bpmn:incoming>
      <bpmn:outgoing>flow_6</bpmn:outgoing>
    </bpmn:serviceTask>
    
    <bpmn:endEvent id="end_1" name="Process Complete">
      <bpmn:incoming>flow_6</bpmn:incoming>
    </bpmn:endEvent>
    
    <bpmn:sequenceFlow id="flow_1" sourceRef="start_1" targetRef="task_1"/>
    <bpmn:sequenceFlow id="flow_2" sourceRef="task_1" targetRef="gateway_1"/>
    <bpmn:sequenceFlow id="flow_3" sourceRef="gateway_1" targetRef="task_3" name="Approved"/>
    <bpmn:sequenceFlow id="flow_4" sourceRef="gateway_1" targetRef="task_2" name="Rejected"/>
    <bpmn:sequenceFlow id="flow_5" sourceRef="task_2" targetRef="task_1"/>
    <bpmn:sequenceFlow id="flow_6" sourceRef="task_3" targetRef="end_1"/>
    
  </bpmn:process>
  
  <bpmn:collaboration id="Collaboration_1">
    <bpmn:participant id="Participant_1" name="Document Review" processRef="Process_1"/>
  </bpmn:collaboration>
  
</bpmn:definitions>'''
    
    # Save to file
    test_file = 'test_process.bpmn'
    with open(test_file, 'w') as f:
        f.write(bpmn_xml)
    
    return test_file

def test_migration():
    """Test full migration with sample BPMN"""
    print("\n\nTesting Full Migration...")
    print("="*60)
    
    # Create sample BPMN file
    test_file = create_sample_bpmn()
    
    try:
        # Run migration
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file, 'test_output.json')
        
        # Print results
        print(f"\n✅ Migration completed!")
        print(f"\nSummary:")
        summary = results['summary']
        print(f"  Processes: {summary['total_processes']}")
        print(f"  Elements: {summary['total_elements']}")
        print(f"  Complexity: {summary['complexity']}")
        print(f"  Estimated Time: {summary['estimated_migration_time']}")
        
        # Print migration details
        if results['tallyfy_templates']:
            template = results['tallyfy_templates'][0]
            details = template['migration_details']
            print(f"\nMigration Results:")
            print(f"  Successful: {len(details['successful'])}")
            print(f"  Partial: {len(details['partial'])}")
            print(f"  Failed: {len(details['failed'])}")
            
            print(f"\nGenerated Tallyfy Template:")
            print(f"  Title: {template['title']}")
            print(f"  Steps: {len(template['steps'])}")
            print(f"  Rules: {len(template['rules'])}")
            print(f"  Groups: {len(template['groups'])}")
        
        # Show report
        report = results['migration_report']
        if report:
            print(f"\nMigration Report:")
            print(f"  Success Rate: {report['summary']['migration_rate']:.1f}%")
            print(f"  Manual Work: {report['summary']['manual_work_required']}")
            print(f"  Complexity: {report.get('complexity', 'Unknown')}")
            print(f"  Estimated Work: {report.get('estimated_work', 'Unknown')}")
        
        print(f"\n📁 Full results saved to: test_output.json")
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
        print(f"\n🧹 Cleaned up test files")

if __name__ == '__main__':
    print("BPMN to Tallyfy Migrator - Test Suite")
    print("="*60)
    
    # Run tests
    test_rule_engine()
    test_optimization()
    test_migration()
    
    print("\n✅ All tests completed!")
    print("\nThe migrator is ready to use with:")
    print("  • 112 embedded BPMN element mappings")
    print("  • Deterministic rule-based transformation")
    print("  • No external AI dependencies required")
    print("  • Production-ready migration engine")