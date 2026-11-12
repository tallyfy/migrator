#!/usr/bin/env python3
"""
BPMN edge cases: what the migrator and the template generator do with each
BPMN construct.

This file used to be a print-only script with no asserts, so it passed
whatever the code returned (tallyfy/migrator#30, item 3). Each test now asserts
the outcome it used to print, and fails if the migration reported an error.

A few current behaviours look wrong and are deliberately not asserted either
way, so this suite does not lock them in. Each is named in a comment where it
shows up.
"""

import os
import sys

import pytest

BPMN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BPMN_DIR, 'src'))

from migrator import BPMNToTallyfyMigrator  # noqa: E402
from tallyfy_generator import TallyfyTemplateGenerator  # noqa: E402


def migrate(tmp_path, name, content):
    """Migrate one BPMN document and return (results, its single process).

    migrate_file catches parse and migration errors and returns them in
    results['errors'], so without this check an unparseable file reads as a
    process with no elements.
    """
    bpmn_file = tmp_path / f"{name}.bpmn"
    bpmn_file.write_text(content)

    results = BPMNToTallyfyMigrator().migrate_file(str(bpmn_file))

    assert results['errors'] == []
    assert len(results['processes']) == 1
    return results, results['processes'][0]


def generate(results, process):
    return TallyfyTemplateGenerator().generate_template(
        process,
        results.get('migration_report', {})
    )


def step_for(template, bpmn_id):
    matches = [s for s in template['steps'] if s['bpmn_element_id'] == bpmn_id]
    assert len(matches) == 1, f"expected one step for {bpmn_id}, got {len(matches)}"
    return matches[0]


def detail_ids(results, outcome):
    details = results['tallyfy_templates'][0]['migration_details']
    return [d['bpmn_element'] for d in details[outcome]]


def test_simple_sequential(tmp_path):
    """A simple sequential process becomes one step per task."""
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

    results, process = migrate(tmp_path, 'simple', bpmn)
    template = generate(results, process)

    # Basic parsing
    assert [t['id'] for t in process['elements']['tasks']] == ['task1', 'task2']
    assert [s['title'] for s in template['steps']] == ['First Task', 'Second Task']
    assert [s['position'] for s in template['steps']] == [0, 1]

    # Tallyfy template structure
    for field in ['title', 'steps', 'type', 'summary']:
        assert field in template, f"template missing {field}"
    assert template['title'] == 'Simple Process'
    assert template['type'] == 'template'

    # Step structure, for every step rather than only the first
    for step in template['steps']:
        for field in ['id', 'title', 'position', 'task_type']:
            assert field in step, f"step {step.get('title')} missing {field}"
        assert step['task_type'] == 'task'
    assert len({s['id'] for s in template['steps']}) == 2

    # Not asserted: the start and end events (no event definition) land in
    # migration_details['failed'] with "Event type not supported", because
    # _migrate_process files any event that produces no step as failed, even
    # when the rule engine supported it.


def test_exclusive_gateway(tmp_path):
    """An XOR gateway becomes show rules, one route per outgoing path."""
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

    results, process = migrate(tmp_path, 'xor', bpmn)
    template = generate(results, process)

    # Gateway parsing
    gateways = process['elements']['gateways']
    assert [(g['id'], g['type']) for g in gateways] == [('decision', 'exclusiveGateway')]

    # Automation rules were generated, and every one is complete
    automations = template.get('automated_actions', [])
    assert automations
    for automation in automations:
        assert automation['rules'], f"{automation['name']} has no conditions"
        assert automation['actions'], f"{automation['name']} has no actions"

    # Each rule shows the step its flow targets, under that flow's own condition
    approve_id = step_for(template, 'approve')['id']
    reject_id = step_for(template, 'reject')['id']
    expected_value = {approve_id: 'true', reject_id: 'false'}
    shown = set()
    for automation in automations:
        for action in automation['actions']:
            assert action['type'] == 'show'
            assert action['step_id'] in expected_value
            shown.add(action['step_id'])
            for rule in automation['rules']:
                assert rule['operator'] == 'equals'
                assert rule['value'] == expected_value[action['step_id']]
    assert shown == {approve_id, reject_id}

    # A decision field was put on the kick-off form
    assert template['prerun']['enabled'] is True
    fields = template['prerun']['fields']
    assert len(fields) == 1
    assert fields[0]['name'] == 'gateway_decision_decision'
    assert fields[0]['label'] == 'Approved?'
    assert fields[0]['type'] == 'radio'

    # Not asserted: that radio field has no options, because the generator
    # counts paths from the gateway's <outgoing> children, which this BPMN
    # (like many) leaves out. Each path also yields two automations, one from
    # the gateway and one from the flow's condition, and their conditions key
    # on 'approved', which no step or kick-off field defines.


def test_parallel_gateway(tmp_path):
    """Parallel gateways are detected and flagged as visual only."""
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

    results, process = migrate(tmp_path, 'parallel', bpmn)

    gateways = process['elements']['gateways']
    assert [(g['id'], g['type']) for g in gateways] == [
        ('split', 'parallelGateway'),
        ('join', 'parallelGateway'),
    ]

    # The migration report accounts for every task and gateway and tells the
    # reader that parallel execution needs review.
    report = results['migration_report']
    stats = report['statistics']
    assert stats['elements_processed'] == 4
    assert stats['elements_processed'] == (
        stats['successful_migrations']
        + stats['partial_migrations']
        + stats['failed_migrations']
    )
    assert 'Review parallel execution requirements' in report['recommendations']

    # Parallel execution is visual only in Tallyfy: the split shows both
    # branches at once, with no condition.
    template = generate(results, process)
    automations = template.get('automated_actions', [])
    assert len(automations) == 1
    assert automations[0]['rules'] == []
    assert 'visual only' in automations[0]['description']
    assert {a['step_id'] for a in automations[0]['actions']} == {
        step_for(template, 'task1')['id'],
        step_for(template, 'task2')['id'],
    }


def test_loops(tmp_path):
    """Loop and multi-instance markers are detected; Tallyfy cannot loop."""
    # The loop condition's "<" is escaped. Unescaped, as this fixture used to
    # be, the file is not well-formed XML, the migrator returns no processes,
    # and the old script crashed with an IndexError instead of testing loops.
    bpmn = '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1">
    <bpmn:userTask id="task1" name="Repeating Task">
      <bpmn:standardLoopCharacteristics testBefore="false">
        <bpmn:loopCondition>${count &lt; 5}</bpmn:loopCondition>
      </bpmn:standardLoopCharacteristics>
    </bpmn:userTask>
    <bpmn:userTask id="task2" name="Multi-Instance">
      <bpmn:multiInstanceLoopCharacteristics isSequential="true">
        <bpmn:loopCardinality>3</bpmn:loopCardinality>
      </bpmn:multiInstanceLoopCharacteristics>
    </bpmn:userTask>
  </bpmn:process>
</bpmn:definitions>'''

    results, process = migrate(tmp_path, 'loops', bpmn)

    tasks = {t['id']: t for t in process['elements']['tasks']}
    assert set(tasks) == {'task1', 'task2'}
    assert tasks['task1']['properties'].get('loop') is True
    assert tasks['task2']['properties'].get('multiInstance') is True

    # Not supported in Tallyfy: the report says to use external scheduling,
    # and each generated step carries a note saying so.
    report = results['migration_report']
    assert 'Remove loops - use external scheduling instead' in report['recommendations']

    template = generate(results, process)
    assert 'external scheduling' in step_for(template, 'task1')['note']
    assert 'Multi-instance' in step_for(template, 'task2')['note']


def test_boundary_events(tmp_path):
    """A boundary timer is detected and reported as not migratable."""
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

    results, process = migrate(tmp_path, 'boundary', bpmn)

    boundary_events = [
        e for e in process['elements']['events']
        if e.get('category') == 'boundary'
    ]
    assert len(boundary_events) == 1
    assert boundary_events[0]['id'] == 'timer'
    assert boundary_events[0]['attachedTo'] == 'task1'
    assert boundary_events[0]['eventType'] == 'timer'

    # Not supported: it is filed as failed, and nowhere else
    assert 'timer' in detail_ids(results, 'failed')
    assert 'timer' not in detail_ids(results, 'successful')
    assert 'timer' not in detail_ids(results, 'partial')


def test_forms(tmp_path):
    """Form fields on a task are extracted and attached to its step."""
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

    results, process = migrate(tmp_path, 'forms', bpmn)

    # Form extraction
    tasks_with_forms = [t for t in process['elements']['tasks'] if t.get('forms')]
    assert [t['id'] for t in tasks_with_forms] == ['task1']
    assert [f['id'] for f in tasks_with_forms[0]['forms']] == ['name', 'amount']

    # Form attachment
    template = generate(results, process)
    steps_with_captures = [s for s in template['steps'] if s.get('captures')]
    assert len(steps_with_captures) == 1
    captures = steps_with_captures[0]['captures']
    assert [c['label'] for c in captures] == ['Name', 'Amount']
    assert [c['name'] for c in captures] == ['name', 'amount']
    assert captures[1]['validation'] == {'min': '0', 'max': '10000'}

    # Not asserted: the "required" constraint on Name does not reach the
    # capture's required flag, which reads only the formField's own
    # required attribute.


def test_data_objects(tmp_path):
    """Data objects and their references are extracted."""
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

    results, process = migrate(tmp_path, 'data', bpmn)

    data_objects = {d['id']: d for d in process['elements'].get('dataObjects', [])}
    assert set(data_objects) == {'data1', 'dataRef1'}
    assert data_objects['data1']['type'] == 'dataObject'
    assert data_objects['data1']['name'] == 'Customer Data'
    assert data_objects['dataRef1']['type'] == 'dataObjectReference'
    assert data_objects['dataRef1']['dataObjectRef'] == 'data1'

    # Data associations are not mapped to form fields or variables yet, so
    # there is nothing further to assert here.


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-q']))
