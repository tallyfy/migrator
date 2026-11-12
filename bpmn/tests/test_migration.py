#!/usr/bin/env python3
"""
Tests for the self-contained, rule-based BPMN to Tallyfy migrator: the rule
engine, its optimization advice, and a full migration of one sample process.

This file used to be a print-only script with no asserts, so it passed
whatever the code returned (tallyfy/migrator#30, item 3). Each test now asserts
the outcome it used to print. A few current behaviours look wrong and are
deliberately not asserted either way; each is named in a comment.
"""

import json
import os
import sys

import pytest

BPMN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BPMN_DIR, 'src'))

from migrator import BPMNToTallyfyMigrator  # noqa: E402
from rule_engine import BPMNToTallyfyRuleEngine  # noqa: E402

# The rule engine's own threshold: get_statistics() counts a rule as a
# supported element when its confidence is above 0.5.
SUPPORTED = 0.5


def test_rule_engine():
    """The rule engine maps each element type to the right strategy."""
    engine = BPMNToTallyfyRuleEngine()

    # User task: a direct mapping to a standard Tallyfy task
    result = engine.analyze_element({
        'type': 'userTask',
        'id': 'task_1',
        'name': 'Review Document'
    })
    assert result['strategy'] == 'direct'
    assert result['confidence'] > SUPPORTED
    assert result['tallyfy_mapping'].get('task_type') == 'task'

    # XOR gateway: if-then-else rules
    result = engine.analyze_element({
        'type': 'exclusiveGateway',
        'id': 'gateway_1',
        'name': 'Approval Decision',
        'incoming': ['flow_1'],
        'outgoing': ['flow_2', 'flow_3']
    })
    assert result['strategy'] == 'direct'
    assert result['confidence'] > SUPPORTED
    assert result['tallyfy_mapping'].get('implementation') == 'if_then_else'

    # Timer event: a decision comes back for it. Not asserted: it comes back
    # 'unsupported', because _get_event_definition never reads 'eventType',
    # the key the migrator itself writes, so the intermediateCatchEvent_timer
    # rule is never reached.
    result = engine.analyze_element({
        'type': 'intermediateCatchEvent',
        'id': 'event_1',
        'name': 'Wait 24 hours',
        'eventType': 'timer'
    })
    assert result['element_type'] == 'intermediateCatchEvent'
    assert 0.0 <= result['confidence'] <= 1.0
    assert result['strategy'] in ('direct', 'partial', 'transform', 'unsupported')

    # Boundary event: has no Tallyfy equivalent
    result = engine.analyze_element({
        'type': 'boundaryEvent',
        'id': 'boundary_1',
        'name': 'Error Handler'
    })
    assert result['strategy'] == 'unsupported'
    assert result['confidence'] == 0.0
    assert result['reasoning'] == 'Boundary events cannot be mapped'

    # Statistics: every count is present, and the three support levels
    # partition the rule set.
    stats = engine.get_statistics()
    for key in ['total_rules', 'pattern_rules', 'gateway_rules', 'event_rules',
                'field_mappings', 'supported_elements', 'partial_support',
                'unsupported']:
        assert isinstance(stats[key], int), key
    for key in ['total_rules', 'pattern_rules', 'gateway_rules', 'event_rules',
                'field_mappings']:
        assert stats[key] > 0, key
    assert stats['total_rules'] == (
        stats['supported_elements'] + stats['partial_support'] + stats['unsupported']
    )


def test_optimization():
    """Optimization advice scales with process complexity."""
    engine = BPMNToTallyfyRuleEngine()

    simple = engine.suggest_optimization({
        'task_count': 5,
        'gateway_count': 1,
        'unsupported_count': 0,
        'has_loops': False,
        'parallel_gateways': 0
    })
    assert simple['difficulty'] == 'Simple'
    assert simple['estimated_manual_work'] == '1-2 hours'
    assert simple['success_likelihood'] == 100
    assert simple['recommendations'] == []

    complex_result = engine.suggest_optimization({
        'task_count': 50,
        'gateway_count': 15,
        'unsupported_count': 10,
        'has_loops': True,
        'parallel_gateways': 5
    })
    assert complex_result['difficulty'] == 'Very Complex'
    assert complex_result['estimated_manual_work'] == '8+ hours'
    assert complex_result['success_likelihood'] == 0
    assert complex_result['recommendations'] == [
        'Consider breaking into multiple templates',
        'Simplify decision logic where possible',
        'Redesign 10 unsupported elements',
        'Remove loops - use external scheduling instead',
        'Review parallel execution requirements',
    ]


SAMPLE_BPMN = '''<?xml version="1.0" encoding="UTF-8"?>
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


def test_migration(tmp_path):
    """A full migration of the sample process, written to an output file."""
    bpmn_file = tmp_path / 'test_process.bpmn'
    bpmn_file.write_text(SAMPLE_BPMN)
    output_file = tmp_path / 'test_output.json'

    results = BPMNToTallyfyMigrator().migrate_file(str(bpmn_file), str(output_file))

    # migrate_file catches its own exceptions and returns them in this list
    assert results['errors'] == []

    # Summary: 3 tasks + 1 gateway + 2 events + 6 flows
    summary = results['summary']
    assert summary['total_processes'] == 1
    assert summary['total_elements'] == 12
    assert summary['complexity'] == 'Simple'
    assert summary['estimated_migration_time'] == '1-2 hours'

    # Generated Tallyfy template
    assert len(results['tallyfy_templates']) == 1
    template = results['tallyfy_templates'][0]
    assert template['title'] == 'Document Approval Process'
    assert sorted(s['title'] for s in template['steps']) == [
        'Make Revisions', 'Publish Document', 'Review Document'
    ]
    assert sorted(s['position'] for s in template['steps']) == [0, 1, 2]
    assert template['groups'] == []  # the process has no lanes

    # The XOR gateway becomes one conditional rule per outgoing path
    assert [(r['type'], r['bpmn_gateway_id'], r['condition']['value'])
            for r in template['rules']] == [
        ('conditional', 'gateway_1', 'path_1'),
        ('conditional', 'gateway_1', 'path_2'),
    ]

    # The service task becomes a webhook step that still needs configuring
    publish = next(s for s in template['steps'] if s['bpmn_task_id'] == 'task_3')
    assert publish['webhook']['method'] == 'POST'

    # Migration details account for every task, gateway and event exactly once
    details = template['migration_details']
    accounted = [d['bpmn_element']
                 for outcome in ('successful', 'partial', 'failed')
                 for d in details[outcome]]
    assert sorted(accounted) == sorted(
        ['task_1', 'task_2', 'task_3', 'gateway_1', 'start_1', 'end_1']
    )
    successful = [d['bpmn_element'] for d in details['successful']]
    assert {'task_1', 'task_2', 'gateway_1'} <= set(successful)
    assert [(d['bpmn_element'], d['warnings']) for d in details['partial']] == [
        ('task_3', ['Service task requires webhook configuration'])
    ]
    # Not asserted: start_1 and end_1 are filed as failed, because
    # _migrate_process treats any event that produces no step as failed.

    # Migration report
    report = results['migration_report']
    assert report['summary']['migration_rate'] == pytest.approx(
        100.0 * len(details['successful']) / len(accounted)
    )
    assert report['summary']['manual_work_required'] is True
    assert report['complexity'] == 'Simple'
    assert report['estimated_work'] == '1-2 hours'

    # The full results were written to the output file
    with open(output_file) as f:
        saved = json.load(f)
    assert saved['summary'] == results['summary']
    assert saved['tallyfy_templates'][0]['title'] == 'Document Approval Process'
    assert saved['migration_report'] == results['migration_report']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-q']))
