"""
Contract test for how every vendor's AIClient calls Claude (issue #19).

WHY THIS FILE EXISTS
--------------------
All seventeen `*/src/api/ai_client.py` files call `claude-opus-5-5`. That model
differs from the Opus 4.6 the clients were written for in three ways that break a
bare model-ID swap:

- it rejects sampling parameters, so a request carrying one returns a 400;
- it always thinks, and thinking counts toward `max_tokens`, so the old 500-token
  budget can be spent before any answer is written;
- a reply can open with thinking blocks, so reading the first block as text reads
  the wrong block.

Each client swallows every exception and falls back to a deterministic answer, so
none of those failures would ever be visible: the migration would quietly stop
using AI.

Effort is sent only to models that accept it. Haiku returns a 400 for effort, so
an AI_MODEL override to a Haiku model must get no effort rather than a fallback
on every call. These tests drive every call site through a fake client and assert on
what goes on the wire and on what comes back, so a regression turns a test red
instead of silently turning the AI path off.

The fake response blocks carry only `type` and `text` (or `thinking`), which is
the shape the real SDK's TextBlock and ThinkingBlock expose. A live call against
the API confirmed that shape when this file was written.
"""

import ast
import glob
import importlib.util
import os
import shutil
import sys
import types

import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODEL = 'claude-opus-5-5'
MAX_TOKENS = 16000
EFFORT_BODY = {'output_config': {'effort': 'medium'}}
SAMPLING_PARAMS = ('temperature', 'top_p', 'top_k')

# Model IDs are checked against what the API says about effort: accepted by Opus 4.5
# and later, Sonnet 4.6 and later, and Fable; a 400 on Haiku 4.5 and older models.
TAKES_EFFORT = [
    'claude-opus-5-5', 'claude-opus-5', 'claude-opus-4-8', 'claude-opus-4-6',
    'claude-opus-4-5', 'claude-opus-4-5-20251101', 'claude-sonnet-5',
    'claude-sonnet-4-6', 'claude-fable-5', 'claude-fable-5-1',
]
REJECTS_EFFORT = [
    'claude-haiku-4-5', 'claude-haiku-4-5-20251001', 'claude-3-haiku-20240307',
    'claude-3-opus-20240229', 'claude-opus-4-1-20250805', 'claude-opus-4-20250514',
    'claude-sonnet-4-5', 'claude-sonnet-4-5-20250929', 'claude-sonnet-4-20250514',
    '', None,
]
HAIKU = 'claude-haiku-4-5'

# Discovered, never listed, so a new vendor is covered the day it lands.
AI_CLIENTS = sorted(glob.glob(os.path.join(REPO_ROOT, '*', 'src', 'api', 'ai_client.py')))
VENDORS = [p.split(os.sep)[-4] for p in AI_CLIENTS]

# bpmn has no make_decision; it has five purpose-built methods, one per call site.
BPMN_CALLS = [
    ('analyze_gateway_complexity', (
        {'id': 'g1', 'type': 'exclusiveGateway', 'name': 'G',
         'incoming': ['a'], 'outgoing': ['b', 'c']},
        [{'source_ref': 'g1', 'target_ref': 'b', 'condition': 'x > 1'}],
    )),
    ('transform_complex_process', (
        {'name': 'P', 'tasks': [], 'gateways': [], 'events': [], 'lanes': [],
         'sequence_flows': []},
    )),
    ('map_complex_event', ({'type': 'signal', 'position': 'intermediate', 'name': 'E'},)),
    ('optimize_lane_to_role_mapping', (
        [{'name': 'L1', 'flow_node_refs': []}, {'name': 'L2', 'flow_node_refs': []}],
        [],
    )),
    ('handle_loop_pattern', ([{'id': 't1'}],)),
]

REPLY_JSON = '{"decision": "probe", "confidence": 0.9}'


def _thinking():
    return types.SimpleNamespace(type='thinking', thinking='', signature='sig')


def _text(value):
    return types.SimpleNamespace(type='text', text=value)


class _FakeMessages:
    def __init__(self, content, stop_reason='end_turn'):
        self.calls = []
        self._content = content
        self._stop_reason = stop_reason

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(content=list(self._content), stop_reason=self._stop_reason)


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


def _load_copy(vendor, tmp_path):
    """Load a vendor's ai_client from a copy under tmp_path.

    A copy, because bpmn's constructor creates a prompts directory next to its
    own file, and make_decision needs a prompt file that most vendors do not ship.
    Neither should touch the repository.
    """
    src = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'ai_client.py')
    dst_dir = tmp_path / vendor / 'src' / 'api'
    dst_dir.mkdir(parents=True)
    shutil.copy(src, dst_dir / 'ai_client.py')
    prompts = tmp_path / vendor / 'src' / 'prompts'
    prompts.mkdir()
    (prompts / 'probe.txt').write_text('Classify this probe.')
    _stub_anthropic_if_absent()
    name = f'_ai_call_shape_{vendor.replace("-", "_")}_{abs(hash(str(tmp_path)))}'
    spec = importlib.util.spec_from_file_location(name, dst_dir / 'ai_client.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _client(module, monkeypatch, fake, model=None):
    for var in ('ANTHROPIC_API_KEY', 'AI_MODEL', 'AI_MAX_TOKENS'):
        monkeypatch.delenv(var, raising=False)
    if model is not None:
        monkeypatch.setenv('AI_MODEL', model)
    client = module.AIClient()
    assert client.enabled is False, 'no key is configured, so the client must start disabled'
    client.client = types.SimpleNamespace(messages=fake)
    client.enabled = True
    return client


def _drive(vendor, client):
    """Call every messages.create site once; return the results."""
    if vendor == 'bpmn':
        return [getattr(client, name)(*args) for name, args in BPMN_CALLS]
    return [client.make_decision('probe.txt', {})]


def _assert_wire_shape(vendor, kwargs):
    assert kwargs.get('model') == MODEL, f'{vendor} calls {kwargs.get("model")!r}'
    assert kwargs.get('max_tokens') == MAX_TOKENS, (
        f'{vendor} sends max_tokens={kwargs.get("max_tokens")!r}; thinking counts '
        f'toward it, so a small budget can end the reply before any text'
    )
    for param in SAMPLING_PARAMS:
        assert param not in kwargs, f'{vendor} sends {param}, which {MODEL} rejects with a 400'
    assert 'thinking' not in kwargs, f'{vendor} configures thinking; {MODEL} 400s on disabled'
    assert kwargs.get('extra_body') == EFFORT_BODY, (
        f'{vendor} sends extra_body={kwargs.get("extra_body")!r}, expected {EFFORT_BODY!r}'
    )


def test_discovery_found_every_vendor():
    # A sweep that discovers nothing passes every assertion made about it.
    assert len(AI_CLIENTS) >= 17, f'found only {len(AI_CLIENTS)} ai_client.py files'


def test_every_messages_create_call_in_every_client_has_the_new_shape():
    """Static sweep, so a call site added later cannot dodge the behavioural tests."""
    total = 0
    for path in AI_CLIENTS:
        with open(path) as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'create'
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == 'messages'):
                continue
            total += 1
            keywords = {kw.arg: kw.value for kw in node.keywords}
            where = f'{os.path.relpath(path, REPO_ROOT)}:{node.lineno}'
            for param in SAMPLING_PARAMS:
                assert param not in keywords, f'{where} sends {param}'
            assert 'extra_body' in keywords, f'{where} does not send the effort'
            body, model = keywords['extra_body'], keywords.get('model')
            if isinstance(body, ast.Call):
                # The effort helper must be asked about the model actually sent.
                assert isinstance(body.func, ast.Name) and body.func.id == '_effort_body', where
                assert model is not None and len(body.args) == 1, where
                assert ast.dump(body.args[0]) == ast.dump(model), (
                    f'{where} asks _effort_body about a different model than it sends'
                )
            else:
                # A literal effort is only safe beside a literal model that takes it.
                assert ast.literal_eval(body) == EFFORT_BODY, where
                assert isinstance(model, ast.Constant) and model.value == MODEL, where
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and re.fullmatch(r'claude-[a-z0-9-]+', node.value):
                assert node.value == MODEL, (
                    f'{os.path.relpath(path, REPO_ROOT)}:{node.lineno} names {node.value!r}'
                )
    # 16 clients with one call plus bpmn with five.
    assert total >= 21, f'found only {total} messages.create calls'


@pytest.mark.parametrize('vendor', VENDORS)
def test_response_text_reads_text_blocks_and_refuses_an_empty_answer(vendor, tmp_path):
    module = _load_copy(vendor, tmp_path)
    read = module._response_text

    reply = types.SimpleNamespace(content=[_thinking(), _text('a'), _text('b')],
                                  stop_reason='end_turn')
    assert read(reply) == 'ab'

    for content, stop_reason in (
        ([_thinking()], 'max_tokens'),  # the whole budget went on thinking
        ([], 'refusal'),                # a classifier decline carries no text
        ([_thinking(), _text('  ')], 'end_turn'),
    ):
        with pytest.raises(ValueError):
            read(types.SimpleNamespace(content=content, stop_reason=stop_reason))


@pytest.mark.parametrize('vendor', [v for v in VENDORS if v != 'bpmn'])
def test_effort_is_sent_only_to_models_that_accept_it(vendor, tmp_path):
    module = _load_copy(vendor, tmp_path)
    for model in TAKES_EFFORT:
        assert module._effort_body(model) == EFFORT_BODY, f'{vendor}: {model} takes effort'
    for model in REJECTS_EFFORT:
        assert module._effort_body(model) is None, f'{vendor}: {model} 400s on effort'


@pytest.mark.parametrize('vendor', [v for v in VENDORS if v != 'bpmn'])
def test_a_haiku_override_sends_no_effort_and_still_parses(vendor, tmp_path, monkeypatch):
    module = _load_copy(vendor, tmp_path)
    fake = _FakeMessages([_text(REPLY_JSON)])
    client = _client(module, monkeypatch, fake, model=HAIKU)

    result = client.make_decision('probe.txt', {})

    assert len(fake.calls) == 1
    kwargs = fake.calls[0]
    assert kwargs.get('model') == HAIKU
    assert kwargs.get('extra_body') is None, (
        f'{vendor} sends {kwargs.get("extra_body")!r} to {HAIKU}, which returns a 400'
    )
    for param in SAMPLING_PARAMS:
        assert param not in kwargs
    assert result.get('decision') == 'probe', f'{vendor} did not use the reply: {result!r}'


@pytest.mark.parametrize('vendor', [v for v in VENDORS if v != 'bpmn'])
def test_defaults_are_the_new_model_and_budget(vendor, tmp_path, monkeypatch):
    module = _load_copy(vendor, tmp_path)
    client = _client(module, monkeypatch, _FakeMessages([_text(REPLY_JSON)]))
    assert client.model == MODEL
    assert client.max_tokens == MAX_TOKENS
    assert not hasattr(client, 'temperature')


@pytest.mark.parametrize('vendor', VENDORS)
def test_a_reply_that_opens_with_thinking_is_parsed(vendor, tmp_path, monkeypatch):
    module = _load_copy(vendor, tmp_path)
    fake = _FakeMessages([_thinking(), _text(REPLY_JSON)])
    client = _client(module, monkeypatch, fake)

    results = _drive(vendor, client)

    expected_calls = len(BPMN_CALLS) if vendor == 'bpmn' else 1
    assert len(fake.calls) == expected_calls, f'{vendor} made {len(fake.calls)} calls'
    for kwargs in fake.calls:
        _assert_wire_shape(vendor, kwargs)
    for result in results:
        assert result.get('decision') == 'probe', (
            f'{vendor} did not use the model reply: {result!r}'
        )


@pytest.mark.parametrize('vendor', VENDORS)
def test_a_reply_with_no_text_takes_the_fallback(vendor, tmp_path, monkeypatch):
    module = _load_copy(vendor, tmp_path)
    fake = _FakeMessages([_thinking()], stop_reason='max_tokens')
    client = _client(module, monkeypatch, fake)

    if vendor == 'bpmn':
        event = {'type': 'signal', 'position': 'intermediate', 'name': 'E'}
        result = client.map_complex_event(event)
        assert len(fake.calls) == 1
        assert result == client._event_mapping_fallback(event), (
            f'bpmn treated an answer with no text as content: {result!r}'
        )
        assert client.stats['fallbacks_used'] == 1
        return

    result = client.make_decision('probe.txt', {})
    assert len(fake.calls) == 1
    assert result.get('ai_powered') is False, (
        f'{vendor} treated an answer with no text as content: {result!r}'
    )
