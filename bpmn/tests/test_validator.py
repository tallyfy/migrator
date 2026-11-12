#!/usr/bin/env python3
"""
Validator.validate_bpmn must read the shape BPMNClient actually emits.

It used to read process['elements']['tasks'], elements['flows'] and
flow['sourceRef'], while BPMNClient.to_dict() puts tasks, events and
sequence_flows directly on each process, marks events with 'position', and
gives flows 'source_ref' and 'target_ref' (tallyfy/migrator#30, item 4). Fed
real client output it saw no tasks, no events and no flows, so it warned that
every process had no tasks and no start or end event, and its connectivity
check never ran.

Every test here parses BPMN XML with BPMNClient, so the validator always sees
the real client shape, never a hand-built dict.
"""

import os
import sys

import pytest

BPMN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BPMN_DIR, 'src'))

from api.bpmn_client import BPMNClient  # noqa: E402
from utils.validator import Validator  # noqa: E402

SAMPLE_BPMN = os.path.join(BPMN_DIR, 'tests', 'sample_order_process.bpmn')

NS = 'xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"'


def client_output_for(xml):
    client = BPMNClient()
    client.load_string(xml)
    return client.to_dict()


def test_sample_file_validates_clean():
    data = BPMNClient(SAMPLE_BPMN).to_dict()

    # Control: the sample really does carry tasks, start and end events and
    # flows in the client's shape, so a clean result below means the validator
    # read them, not that there was nothing to read.
    assert len(data['processes']) == 2
    for process in data['processes']:
        assert process['tasks']
        assert any(e['position'] == 'start' for e in process['events'])
        assert any(e['position'] == 'end' for e in process['events'])
        assert process['sequence_flows']
        assert all(f['source_ref'] and f['target_ref'] for f in process['sequence_flows'])

    is_valid, issues = Validator().validate_bpmn(data)

    assert is_valid is True
    assert issues == []


def test_disconnected_task_is_reported():
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<definitions {NS}>
  <process id="P1" name="With an orphan">
    <startEvent id="start"/>
    <userTask id="t1" name="Connected Task"/>
    <userTask id="t2" name="Orphan Task"/>
    <endEvent id="end"/>
    <sequenceFlow id="f1" sourceRef="start" targetRef="t1"/>
    <sequenceFlow id="f2" sourceRef="t1" targetRef="end"/>
  </process>
</definitions>'''

    is_valid, issues = Validator().validate_bpmn(client_output_for(xml))

    assert is_valid is True  # connectivity problems are warnings, not errors
    assert issues == ["Task 'Orphan Task' in process P1 is not connected"]


def test_missing_start_and_end_events_are_reported():
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<definitions {NS}>
  <process id="P2" name="No events">
    <userTask id="t1" name="Only Task"/>
    <userTask id="t2" name="Next Task"/>
    <sequenceFlow id="f1" sourceRef="t1" targetRef="t2"/>
  </process>
</definitions>'''

    is_valid, issues = Validator().validate_bpmn(client_output_for(xml))

    assert is_valid is True
    assert issues == [
        'Process P2 has no start event',
        'Process P2 has no end event',
    ]


def test_process_without_tasks_is_reported():
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<definitions {NS}>
  <process id="P3" name="Empty">
    <startEvent id="start"/>
    <endEvent id="end"/>
    <sequenceFlow id="f1" sourceRef="start" targetRef="end"/>
  </process>
</definitions>'''

    is_valid, issues = Validator().validate_bpmn(client_output_for(xml))

    assert is_valid is True
    assert issues == ['Process P3 has no tasks']


def test_no_processes_is_an_error():
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<definitions {NS}/>'''

    is_valid, issues = Validator().validate_bpmn(client_output_for(xml))

    assert is_valid is False
    assert issues == ['No processes found in BPMN']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-q']))
