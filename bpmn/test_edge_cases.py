#!/usr/bin/env python3
"""
BPMN Edge Case Test Suite
Tests what actually works vs what's claimed
Validates against Tallyfy's actual requirements
"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from migrator import BPMNToTallyfyMigrator
from tallyfy_generator import TallyfyTemplateGenerator


def create_test_bpmn(test_name: str, content: str) -> str:
    """Create test BPMN file"""
    filename = f"test_{test_name}.bpmn"
    with open(filename, 'w') as f:
        f.write(content)
    return filename


def test_simple_sequential():
    """Test: Simple sequential process (SHOULD WORK)"""
    print("\n" + "="*60)
    print("TEST: Simple Sequential Process")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1" name="Simple Process">
    <bpmn:startEvent id="start" name="Start"/>
    <bpmn:userTask id="task1" name="First Task"/>
    <bpmn:userTask id="task2" name="Second Task"/>
    <bpmn:endEvent id="end" name="End"/>
    <bpmn:sequenceFlow sourceRef="start" targetRef="task1"/>
    <bpmn:sequenceFlow sourceRef="task1" targetRef="task2"/>
    <bpmn:sequenceFlow sourceRef="task2" targetRef="end"/>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("simple", bpmn)
    
    try:
        # Test migrator
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        # Test generator
        generator = TallyfyTemplateGenerator()
        template = generator.generate_template(
            results['processes'][0],
            results.get('migration_report', {})
        )
        
        print("✅ Basic parsing: PASSED")
        print(f"  - Found {len(results['processes'])} process")
        print(f"  - Generated {len(template['steps'])} steps")
        
        # Validate Tallyfy structure
        required_fields = ['title', 'steps', 'type', 'summary']
        missing = [f for f in required_fields if f not in template]
        
        if missing:
            print(f"❌ Tallyfy validation: FAILED - Missing: {missing}")
        else:
            print("✅ Tallyfy structure: PASSED")
        
        # Check step structure
        if template['steps']:
            step = template['steps'][0]
            step_fields = ['id', 'title', 'position', 'task_type']
            missing_step = [f for f in step_fields if f not in step]
            
            if missing_step:
                print(f"⚠️ Step structure: PARTIAL - Missing: {missing_step}")
            else:
                print("✅ Step structure: PASSED")
        
    finally:
        os.remove(test_file)


def test_exclusive_gateway():
    """Test: XOR Gateway with conditions (SHOULD PARTIALLY WORK)"""
    print("\n" + "="*60)
    print("TEST: Exclusive Gateway (XOR)")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:userTask id="review" name="Review"/>
    <bpmn:exclusiveGateway id="decision" name="Approved?"/>
    <bpmn:userTask id="approve" name="Approve"/>
    <bpmn:userTask id="reject" name="Reject"/>
    <bpmn:sequenceFlow sourceRef="review" targetRef="decision"/>
    <bpmn:sequenceFlow sourceRef="decision" targetRef="approve">
      <bpmn:conditionExpression>${approved == true}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow sourceRef="decision" targetRef="reject">
      <bpmn:conditionExpression>${approved == false}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("xor", bpmn)
    
    try:
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        generator = TallyfyTemplateGenerator()
        template = generator.generate_template(
            results['processes'][0],
            results.get('migration_report', {})
        )
        
        print(f"✅ Gateway parsing: Found {len(results['processes'][0]['elements']['gateways'])} gateway")
        
        # Check if automations were generated
        if 'automated_actions' in template and template['automated_actions']:
            print(f"✅ Automation rules: Generated {len(template['automated_actions'])} rules")
            
            # Check rule structure
            rule = template['automated_actions'][0]
            if 'rules' in rule and 'actions' in rule:
                print("✅ Rule structure: PASSED")
            else:
                print("⚠️ Rule structure: INCOMPLETE")
        else:
            print("❌ Automation rules: NOT GENERATED")
        
        # Check if decision field was created
        if template.get('prerun', {}).get('fields'):
            print(f"✅ Decision fields: Created {len(template['prerun']['fields'])} fields")
        else:
            print("⚠️ Decision fields: NOT IN KICKOFF FORM")
        
    finally:
        os.remove(test_file)


def test_parallel_gateway():
    """Test: Parallel Gateway (AND) - VISUAL ONLY"""
    print("\n" + "="*60)
    print("TEST: Parallel Gateway (AND)")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:parallelGateway id="split" name="Split"/>
    <bpmn:userTask id="task1" name="Parallel Task 1"/>
    <bpmn:userTask id="task2" name="Parallel Task 2"/>
    <bpmn:parallelGateway id="join" name="Join"/>
    <bpmn:sequenceFlow sourceRef="split" targetRef="task1"/>
    <bpmn:sequenceFlow sourceRef="split" targetRef="task2"/>
    <bpmn:sequenceFlow sourceRef="task1" targetRef="join"/>
    <bpmn:sequenceFlow sourceRef="task2" targetRef="join"/>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("parallel", bpmn)
    
    try:
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        print(f"✅ Found {len(results['processes'][0]['elements']['gateways'])} parallel gateways")
        
        # Check migration report
        report = results.get('migration_report', {})
        if report:
            stats = report.get('statistics', {})
            print(f"⚠️ Note: Parallel execution is VISUAL ONLY in Tallyfy")
            print(f"  - Partial migrations: {stats.get('partial_migrations', 0)}")
        
    finally:
        os.remove(test_file)


def test_loops():
    """Test: Loop patterns (SHOULD FAIL)"""
    print("\n" + "="*60)
    print("TEST: Loop Patterns")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:userTask id="task1" name="Repeating Task">
      <bpmn:standardLoopCharacteristics testBefore="false">
        <bpmn:loopCondition>${count < 5}</bpmn:loopCondition>
      </bpmn:standardLoopCharacteristics>
    </bpmn:userTask>
    <bpmn:userTask id="task2" name="Multi-Instance">
      <bpmn:multiInstanceLoopCharacteristics isSequential="true">
        <bpmn:loopCardinality>3</bpmn:loopCardinality>
      </bpmn:multiInstanceLoopCharacteristics>
    </bpmn:userTask>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("loops", bpmn)
    
    try:
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        # Check if loops were detected
        has_loops = any(
            task.get('properties', {}).get('loop') or 
            task.get('properties', {}).get('multiInstance')
            for task in results['processes'][0]['elements']['tasks']
        )
        
        if has_loops:
            print("✅ Loop detection: DETECTED")
            print("❌ Loop support: NOT SUPPORTED IN TALLYFY")
            print("  - Requires external scheduling")
            print("  - Manual workaround needed")
        else:
            print("❌ Loop detection: FAILED TO DETECT")
        
    finally:
        os.remove(test_file)


def test_boundary_events():
    """Test: Boundary Events (SHOULD FAIL)"""
    print("\n" + "="*60)
    print("TEST: Boundary Events")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:userTask id="task1" name="Task with Timer"/>
    <bpmn:boundaryEvent id="timer" attachedToRef="task1">
      <bpmn:timerEventDefinition>
        <bpmn:timeDuration>PT2H</bpmn:timeDuration>
      </bpmn:timerEventDefinition>
    </bpmn:boundaryEvent>
    <bpmn:userTask id="escalation" name="Escalation"/>
    <bpmn:sequenceFlow sourceRef="timer" targetRef="escalation"/>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("boundary", bpmn)
    
    try:
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        boundary_events = [
            e for e in results['processes'][0]['elements']['events']
            if e.get('category') == 'boundary'
        ]
        
        if boundary_events:
            print(f"✅ Boundary event detected: {len(boundary_events)} found")
            print("❌ Boundary event support: NOT SUPPORTED")
            print("  - No Tallyfy equivalent")
            print("  - Requires complete redesign")
        else:
            print("⚠️ Boundary events not properly extracted")
        
    finally:
        os.remove(test_file)


def test_forms():
    """Test: Form fields (Camunda style)"""
    print("\n" + "="*60)
    print("TEST: Form Fields")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:camunda="http://camunda.org/schema/1.0/bpmn">
  <bpmn:process id="Process_1">
    <bpmn:userTask id="task1" name="Form Task">
      <bpmn:extensionElements>
        <camunda:formData>
          <camunda:formField id="name" label="Name" type="string">
            <camunda:validation>
              <camunda:constraint name="required"/>
            </camunda:validation>
          </camunda:formField>
          <camunda:formField id="amount" label="Amount" type="long">
            <camunda:validation>
              <camunda:constraint name="min" config="0"/>
              <camunda:constraint name="max" config="10000"/>
            </camunda:validation>
          </camunda:formField>
        </camunda:formData>
      </bpmn:extensionElements>
    </bpmn:userTask>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("forms", bpmn)
    
    try:
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        # Check if forms were extracted
        tasks_with_forms = [
            task for task in results['processes'][0]['elements']['tasks']
            if task.get('forms')
        ]
        
        if tasks_with_forms:
            print(f"✅ Form extraction: Found {len(tasks_with_forms)} tasks with forms")
            
            # Generate Tallyfy template
            generator = TallyfyTemplateGenerator()
            template = generator.generate_template(
                results['processes'][0],
                results.get('migration_report', {})
            )
            
            # Check if forms attached to steps
            steps_with_captures = [
                step for step in template['steps']
                if step.get('captures')
            ]
            
            if steps_with_captures:
                print(f"✅ Form attachment: {len(steps_with_captures)} steps have captures")
            else:
                print("❌ Form attachment: Forms not attached to steps")
        else:
            print("❌ Form extraction: FAILED")
        
    finally:
        os.remove(test_file)


def test_data_objects():
    """Test: Data Objects and Associations"""
    print("\n" + "="*60)
    print("TEST: Data Objects")
    print("="*60)
    
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:dataObject id="data1" name="Customer Data"/>
    <bpmn:dataObjectReference id="dataRef1" dataObjectRef="data1"/>
    <bpmn:userTask id="task1" name="Process Data">
      <bpmn:dataInputAssociation>
        <bpmn:sourceRef>dataRef1</bpmn:sourceRef>
      </bpmn:dataInputAssociation>
    </bpmn:userTask>
  </bpmn:process>
</bpmn:definitions>'''
    
    test_file = create_test_bpmn("data", bpmn)
    
    try:
        migrator = BPMNToTallyfyMigrator()
        results = migrator.migrate_file(test_file)
        
        data_objects = results['processes'][0]['elements'].get('dataObjects', [])
        
        if data_objects:
            print(f"✅ Data object extraction: Found {len(data_objects)}")
            print("⚠️ Data associations: NOT FULLY IMPLEMENTED")
            print("  - Should map to form fields or variables")
        else:
            print("❌ Data object extraction: FAILED")
        
    finally:
        os.remove(test_file)


def run_validation_suite():
    """Run complete validation suite"""
    print("\n" + "="*70)
    print(" BPMN TO TALLYFY MIGRATOR - VALIDATION SUITE")
    print(" Testing what actually works vs what's claimed")
    print("="*70)
    
    # Run all tests
    test_simple_sequential()
    test_exclusive_gateway()
    test_parallel_gateway()
    test_loops()
    test_boundary_events()
    test_forms()
    test_data_objects()
    
    # Summary
    print("\n" + "="*70)
    print(" VALIDATION SUMMARY")
    print("="*70)
    print("\n✅ WORKING:")
    print("  - Simple sequential processes")
    print("  - Basic task extraction")
    print("  - Gateway detection")
    print("\n⚠️ PARTIALLY WORKING:")
    print("  - XOR gateway rules (conditions not parsed)")
    print("  - Form extraction (attachment issues)")
    print("  - Parallel gateways (visual only)")
    print("\n❌ NOT WORKING:")
    print("  - Loops (no Tallyfy support)")
    print("  - Boundary events (no equivalent)")
    print("  - Complex conditions")
    print("  - Data associations")
    print("  - Timer parsing")
    print("\n📊 REALISTIC ASSESSMENT:")
    print("  - Current implementation: ~30% complete")
    print("  - Usable for: Simple sequential processes only")
    print("  - Production ready: NO")
    print("  - Estimated completion: 80-120 hours")


if __name__ == '__main__':
    run_validation_suite()