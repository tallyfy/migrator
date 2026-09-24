"""
Contract test for bpmn's process-optimization reply (issue #21).

WHY THIS FILE EXISTS
--------------------
`bpmn/src/migration_assistant.py` `suggest_process_optimization` asked Haiku 4.5
for "recommendations in JSON format" and parsed the reply by slicing from the
first '{' to the last '}'. Haiku answered with a fenced JSON block followed by
prose, and sometimes the JSON itself was invalid. Two live calls on SDK 1.8.0
both finished on their own; one parsed and one failed with "Expecting ','
delimiter", so the method returned its error result for a reply that was
complete.

The call now asks for structured output (`output_config.format` with a JSON
schema), which Haiku 4.5 supports, so the reply is schema-valid JSON. The parser
reads the first JSON object instead of slicing, the four lists are validated,
and an unusable reply gets one retry.

Separately, `migrate_bpmn_file` iterated `elements_analyzed`, which is a count,
so with an API key set every migration raised "'int' object is not iterable"
before the optimization call and returned with no statistics.

These tests drive the real method through a fake client and assert on what goes
on the wire and on what comes back.
"""

import importlib.util
import json
import os
import sys
import types
import xml.etree.ElementTree as ET

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSISTANT = os.path.join(REPO_ROOT, 'bpmn', 'src', 'migration_assistant.py')
SAMPLE_BPMN = os.path.join(REPO_ROOT, 'bpmn', 'tests', 'sample_order_process.bpmn')

MODEL = 'claude-haiku-4-5-20251001'
KEYS = ('optimizations', 'complexity_reduction',
        'unsupported_pattern_alternatives', 'tallyfy_best_practices')
VALID = {key: [f'{key} one', f'{key} two'] for key in KEYS}
VALID_JSON = json.dumps(VALID, indent=2)
ERROR_RESULT = 'Manual optimization recommended'

# The shape of the live failure: a fenced block whose JSON is missing a comma.
INVALID_JSON = '```json\n{\n  "optimizations": ["a"]\n  "complexity_reduction": []\n}\n```'

ELEMENT_REPLY = json.dumps({
    'confidence': 0.9, 'strategy': 'direct', 'tallyfy_mapping': {'type': 'task'},
    'manual_steps': [], 'warnings': [], 'reasoning': 'probe',
})


def _stub_anthropic_if_absent():
    if 'anthropic' in sys.modules:
        return
    try:
        import anthropic  # noqa: F401
    except ImportError:
        stub = types.ModuleType('anthropic')
        stub.Anthropic = object
        stub.APIError = Exception
        sys.modules['anthropic'] = stub


@pytest.fixture(scope='module')
def module():
    _stub_anthropic_if_absent()
    name = '_bpmn_optimization_reply_assistant'
    spec = importlib.util.spec_from_file_location(name, ASSISTANT)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded  # dataclasses look the module up by name
    spec.loader.exec_module(loaded)
    return loaded


class _Messages:
    """Returns the queued replies in order. An Exception in the queue is raised."""

    def __init__(self, replies):
        self.calls = []
        self._replies = list(replies)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type='text', text=reply)],
            stop_reason='end_turn',
        )


def _assistant(module, monkeypatch, replies):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    assistant = module.ClaudeAIMigrationAssistant()
    assert assistant.client is None, 'no key is configured, so there must be no client'
    fake = _Messages(replies)
    assistant.client = types.SimpleNamespace(messages=fake)
    return assistant, fake


def test_the_call_asks_for_structured_output_and_no_effort(module, monkeypatch):
    assistant, fake = _assistant(module, monkeypatch, [VALID_JSON])

    assistant.suggest_process_optimization({'task_count': 3})

    assert len(fake.calls) == 1
    kwargs = fake.calls[0]
    assert kwargs.get('model') == MODEL
    assert kwargs.get('max_tokens') == 8000
    assert kwargs.get('extra_body') == {'output_config': {'format': {
        'type': 'json_schema', 'schema': {
            'type': 'object',
            'properties': {key: {'type': 'array', 'items': {'type': 'string'}} for key in KEYS},
            'required': list(KEYS),
            'additionalProperties': False,
        },
    }}}
    assert 'effort' not in json.dumps(kwargs), 'Haiku 4.5 returns a 400 for effort'
    for param in ('temperature', 'top_p', 'top_k', 'thinking', 'output_config'):
        assert param not in kwargs


def test_the_schema_follows_the_structured_output_rules(module):
    """Every object must close additionalProperties and require all its keys, or the API 400s."""
    objects = []

    def walk(node):
        if isinstance(node, dict):
            if node.get('type') == 'object':
                objects.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(module._OPTIMIZATION_SCHEMA)
    assert objects, 'the schema has no object at all'
    for node in objects:
        assert node.get('additionalProperties') is False
        assert sorted(node.get('required', [])) == sorted(node.get('properties', {}))
    unsupported = {'minimum', 'maximum', 'multipleOf', 'minLength', 'maxLength'}
    assert not unsupported & set(json.dumps(module._OPTIMIZATION_SCHEMA).replace('"', ' ').split())


def test_bare_json_is_used_on_the_first_call(module, monkeypatch):
    assistant, fake = _assistant(module, monkeypatch, [VALID_JSON])
    assert assistant.suggest_process_optimization({'task_count': 3}) == VALID
    assert len(fake.calls) == 1


@pytest.mark.parametrize('reply', [
    # The live shape: a fenced block, then prose. Braces in the prose broke the
    # old first-'{'-to-last-'}' slice.
    f'Here is the plan:\n```json\n{VALID_JSON}\n```\n\nNote: steps like {{Review}} stay manual.',
    # No fence, prose on both sides, a stray closing brace after the object.
    f'Summary first.\n{VALID_JSON}\nThen one more thought }} and a {{ brace.',
])
def test_prose_around_the_json_is_parsed(module, monkeypatch, reply):
    assistant, fake = _assistant(module, monkeypatch, [reply])
    assert assistant.suggest_process_optimization({'task_count': 3}) == VALID
    assert len(fake.calls) == 1


def test_invalid_json_gets_one_retry_and_the_retry_is_used(module, monkeypatch):
    assistant, fake = _assistant(module, monkeypatch, [INVALID_JSON, VALID_JSON])
    assert assistant.suggest_process_optimization({'task_count': 3}) == VALID
    assert len(fake.calls) == 2
    assert fake.calls[0] == fake.calls[1], 'the retry must resend the same request'


def test_invalid_json_twice_returns_the_error_result(module, monkeypatch):
    assistant, fake = _assistant(module, monkeypatch, [INVALID_JSON, INVALID_JSON])
    result = assistant.suggest_process_optimization({'task_count': 3})
    assert len(fake.calls) == 2, 'one retry, not more'
    assert 'error' in result
    assert result.get('recommendations') == ERROR_RESULT


@pytest.mark.parametrize('bad', [
    {key: [] for key in KEYS[:3]},                      # a required key missing
    dict(VALID, optimizations=[1, 2]),                  # items that are not strings
    dict(VALID, tallyfy_best_practices='do it'),        # a string, not a list
    ['not', 'an', 'object'],                            # JSON, but not an object
])
def test_json_that_breaks_the_schema_is_retried(module, monkeypatch, bad):
    assistant, fake = _assistant(module, monkeypatch, [json.dumps(bad), VALID_JSON])
    assert assistant.suggest_process_optimization({'task_count': 3}) == VALID
    assert len(fake.calls) == 2


def test_an_api_error_is_not_retried(module, monkeypatch):
    assistant, fake = _assistant(module, monkeypatch, [RuntimeError('HTTP 400')])
    result = assistant.suggest_process_optimization({'task_count': 3})
    assert len(fake.calls) == 1
    assert result == {'error': 'HTTP 400', 'recommendations': ERROR_RESULT}


def test_without_ai_the_result_has_the_same_four_keys(module, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    result = module.ClaudeAIMigrationAssistant().suggest_process_optimization({})
    assert tuple(result) == KEYS


def test_element_analysis_reads_json_wrapped_in_prose(module, monkeypatch):
    reply = f'Analysis:\n```json\n{ELEMENT_REPLY}\n```\nThe {{userTask}} maps directly.'
    assistant, fake = _assistant(module, monkeypatch, [reply])
    element = {'type': 'serviceTask', 'id': 's1', 'name': 'Charge'}
    decision = assistant._ai_analyze_element(element, {})
    assert decision.ai_reasoning == 'probe' and decision.strategy == 'direct'
    assert decision != assistant._fallback_analyze_element(element, {})


class _ByPurpose:
    """Element calls get an element reply; the optimization call gets VALID_JSON."""

    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        optimization = 'optimization expert' in str(kwargs.get('system', ''))
        text = VALID_JSON if optimization else ELEMENT_REPLY
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type='text', text=text)], stop_reason='end_turn')


def test_migrate_bpmn_file_reaches_the_optimization_call(module, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    migrator = module.BPMNToTallyfyMigrationAssistant()
    fake = _ByPurpose()
    migrator.ai_assistant.client = types.SimpleNamespace(messages=fake)

    results = migrator.migrate_bpmn_file(SAMPLE_BPMN)

    assert 'error' not in results, f'migration failed: {results.get("error")}'
    assert results['optimization_suggestions'] == VALID
    assert results['statistics'].get('total_elements') == results['elements_analyzed'] > 0

    # The prompt reports the real gateway and event counts, read independently.
    tags = [child.tag.split('}')[-1]
            for process in ET.parse(SAMPLE_BPMN).getroot().iter()
            if process.tag.endswith('}process')
            for child in process]
    gateways = sum(1 for tag in tags if 'gateway' in tag.lower())
    events = sum(1 for tag in tags if tag.lower().endswith('event'))
    assert gateways > 0 and events > 0, 'the sample file must exercise both counts'
    prompt = fake.calls[-1]['messages'][0]['content']
    assert f'- Gateways: {gateways}\n' in prompt
    assert f'- Events: {events}\n' in prompt
