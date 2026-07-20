"""
Contract test across every vendor's Tallyfy client.

The API reads the kick-off payload from the `prerun` request key
(RunRequestValidator reads `prerun` and `prerun.<timeline_id>`). A body that
carries `prerun_data` is silently ignored: every kick-off value is discarded,
and any required kick-off field fails the launch with a 422.

These tests drive each client's real process-creation method and assert on the
body it would put on the wire.
"""

import importlib.util
import os
import sys
from unittest.mock import patch

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Clients exposing create_run(checklist_id, name, prerun_data) and posting via _make_request.
CREATE_RUN_VENDORS = [
    'wrike', 'clickup', 'rocketlane', 'surveymonkey', 'cognito-forms', 'jotform',
    'typeform', 'google-forms', 'basecamp', 'trello', 'nextmatter',
]

# Clients exposing create_process(checklist_id, name, data) and posting via session.post.
CREATE_PROCESS_VENDORS = ['asana', 'monday', 'kissflow']

# Clients exposing create_process(process_data) and posting via _make_request.
PROCESS_DATA_VENDORS = ['bpmn', 'pipefy', 'process-street']

TIMELINE_ID = 'a1b2c3d4e5f60718293a4b5c6d7e8f90'


def load_client(vendor):
    """Import a vendor's tallyfy_client module under a unique name."""
    path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
    module_name = f'tallyfy_client_{vendor.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.TallyfyClient


def assert_prerun_contract(body):
    """The body must carry `prerun` as a timeline_id-keyed object, never `prerun_data`."""
    assert 'prerun_data' not in body, (
        "client sent `prerun_data`, which the API never reads -- "
        "every kick-off value would be silently discarded"
    )
    assert 'prerun' in body, 'client did not send the `prerun` request key'
    assert isinstance(body['prerun'], dict), (
        f'prerun must be an object keyed by timeline_id, got {type(body["prerun"]).__name__}'
    )
    assert body['prerun'] == {TIMELINE_ID: 'Acme Corp'}


@pytest.mark.parametrize('vendor', CREATE_RUN_VENDORS)
def test_create_run_sends_prerun_key(vendor):
    client_cls = load_client(vendor)
    client = client_cls(api_key='test-key', organization='test-org')

    with patch.object(client_cls, '_make_request', return_value={}) as mock_request:
        client.create_run('checklist-1', 'My Process', {TIMELINE_ID: 'Acme Corp'})

    assert_prerun_contract(mock_request.call_args.kwargs['json'])


@pytest.mark.parametrize('vendor', CREATE_RUN_VENDORS)
def test_create_run_converts_a_list_into_an_object(vendor):
    """The API never accepts a list for prerun."""
    client_cls = load_client(vendor)
    client = client_cls(api_key='test-key', organization='test-org')

    with patch.object(client_cls, '_make_request', return_value={}) as mock_request:
        client.create_run(
            'checklist-1', 'My Process',
            [{'field_id': TIMELINE_ID, 'value': 'Acme Corp'}],
        )

    assert_prerun_contract(mock_request.call_args.kwargs['json'])


@pytest.mark.parametrize('vendor', CREATE_PROCESS_VENDORS)
def test_create_process_sends_prerun_key(vendor):
    client_cls = load_client(vendor)
    client = client_cls(api_token='test-token', organization_id='test-org')

    with patch.object(client.session, 'post') as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {}
        client.create_process('checklist-1', 'My Process', {TIMELINE_ID: 'Acme Corp'})

    assert_prerun_contract(mock_post.call_args.kwargs['json'])


@pytest.mark.parametrize('vendor', CREATE_PROCESS_VENDORS)
def test_create_process_converts_a_list_into_an_object(vendor):
    client_cls = load_client(vendor)
    client = client_cls(api_token='test-token', organization_id='test-org')

    with patch.object(client.session, 'post') as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {}
        client.create_process(
            'checklist-1', 'My Process',
            [{'field_id': TIMELINE_ID, 'value': 'Acme Corp'}],
        )

    assert_prerun_contract(mock_post.call_args.kwargs['json'])


@pytest.mark.parametrize('vendor', PROCESS_DATA_VENDORS)
def test_process_data_client_sends_prerun_key(vendor):
    client_cls = load_client(vendor)
    with patch.object(client_cls, '_authenticate', return_value=None):
        client = client_cls('https://api.example.com', 'id', 'secret', 'org', 'slug')

    with patch.object(client_cls, '_make_request', return_value={}) as mock_request:
        client.create_process({
            'checklist_id': 'checklist-1',
            'prerun': {TIMELINE_ID: 'Acme Corp'},
        })

    assert_prerun_contract(mock_request.call_args.kwargs['json'])


@pytest.mark.parametrize('vendor', PROCESS_DATA_VENDORS)
def test_process_data_client_rewrites_the_legacy_key(vendor):
    """A transformer still emitting `prerun_data` must be rewritten, not double-sent."""
    client_cls = load_client(vendor)
    with patch.object(client_cls, '_authenticate', return_value=None):
        client = client_cls('https://api.example.com', 'id', 'secret', 'org', 'slug')

    with patch.object(client_cls, '_make_request', return_value={}) as mock_request:
        client.create_process({
            'checklist_id': 'checklist-1',
            'prerun_data': {TIMELINE_ID: 'Acme Corp'},
        })

    assert_prerun_contract(mock_request.call_args.kwargs['json'])


@pytest.mark.parametrize('vendor', PROCESS_DATA_VENDORS)
def test_process_data_client_converts_a_list_into_an_object(vendor):
    client_cls = load_client(vendor)
    with patch.object(client_cls, '_authenticate', return_value=None):
        client = client_cls('https://api.example.com', 'id', 'secret', 'org', 'slug')

    with patch.object(client_cls, '_make_request', return_value={}) as mock_request:
        client.create_process({
            'checklist_id': 'checklist-1',
            'prerun': [{'field_id': TIMELINE_ID, 'value': 'Acme Corp'}],
        })

    assert_prerun_contract(mock_request.call_args.kwargs['json'])
