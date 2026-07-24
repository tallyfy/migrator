"""
Contract tests for creating form fields (captures) on a migrated template.

WHY THIS FILE EXISTS
--------------------
Creating a field is a different contract from writing its value, and it was
broken in its own way: every client posted to ``/{entity}s/{entity_id}/field``
(later ``/{entity}s/{entity_id}/captures``), and ``main.py`` called it as
``create_capture('step', step_id, ...)`` and ``create_capture('multiselect',
checklist_id, ...)``. None of those are routes api-v2 serves, so a pipe with
any field aborted on a 404.

Ground truth, read from ``api-v2/routes/api.php``:

* Step fields  -> ``POST /organizations/{org}/checklists/{checklist_id}/steps/{step_id}/captures``
  Registered via ``Route::resource('captures', StepCapturesController::class)->only(['store', ...])``
  nested under ``checklists/{checklist_id}/steps/{step_id}``. It needs BOTH ids.
  (A grep for ``post('captures'`` misses it -- which is how the wrong endpoint
  survived. The earlier audit in this repo concluded no such route existed; it
  was wrong.)
* Kick-off fields -> no ``preruns`` store route exists. They ride a ``prerun``
  array on the checklist create/update payload, validated by the SAME capture
  rules (``addCapturesRules($rules, 'prerun')``).

And the body must satisfy ``CreateCaptureRequest``: ``label`` required,
``field_type`` required and in ``Capture::$field_types``, ``required`` present
and boolean, ``options`` required for radio/dropdown/multiselect with INTEGER
``id`` plus string ``text``, ``columns`` required for table.

The migrator's ``FieldTransformer`` emits none of that -- it emits ``type``,
``select``, and options nested under ``config.options`` as ``{value, label}``.
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.capture_shapes import (  # noqa: E402
    CAPTURE_FIELD_TYPES,
    normalize_capture,
    normalize_captures,
)

# Clients that expose the capture-creation surface.
CAPTURE_CLIENT_VENDORS = ['bpmn', 'pipefy', 'process-street']

OPTIONAL_IMPORTS = (
    'colorlog',
    'sqlalchemy', 'sqlalchemy.exc',
    'psycopg2', 'psycopg2.extras',
)


def _stub_optional_dependencies():
    """Stand in for absent optional packages so these tests RUN, never skip."""
    import logging
    import types

    for name in OPTIONAL_IMPORTS:
        if name in sys.modules:
            continue
        try:
            __import__(name)
            continue
        except ImportError:
            pass

        stub = types.ModuleType(name)
        if name == 'colorlog':
            stub.ColoredFormatter = logging.Formatter
            stub.StreamHandler = logging.StreamHandler
            stub.getLogger = logging.getLogger
        else:
            stub.__getattr__ = lambda attr: MagicMock()
        sys.modules[name] = stub

    for name in OPTIONAL_IMPORTS:
        if '.' in name:
            parent, _, child = name.rpartition('.')
            if parent in sys.modules and not hasattr(sys.modules[parent], child):
                setattr(sys.modules[parent], child, sys.modules[name])


def load_client(vendor):
    path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
    module_name = f'cap_tallyfy_client_{vendor.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.TallyfyClient


def build_client(vendor):
    client_cls = load_client(vendor)
    with patch.object(client_cls, '_authenticate', return_value=None):
        return client_cls, client_cls(
            'https://api.example.com', 'id', 'secret', 'org', 'slug'
        )


# ---------------------------------------------------------------------------
# The normaliser
# ---------------------------------------------------------------------------

class TestNormalizeCapture:

    def test_maps_transformer_type_to_field_type(self):
        out = normalize_capture({'label': 'X', 'type': 'textarea'})
        assert out['field_type'] == 'textarea'
        assert 'type' not in out, 'the API has no `type` key on a capture'

    def test_select_becomes_dropdown(self):
        out = normalize_capture({'label': 'Plan', 'type': 'select',
                                 'config': {'options': [{'value': 1, 'label': 'Pro'}]}})
        assert out['field_type'] == 'dropdown'

    def test_unknown_field_type_falls_back_to_text(self):
        out = normalize_capture({'label': 'X', 'type': 'signature_pad'})
        assert out['field_type'] == 'text'

    def test_every_declared_field_type_survives(self):
        for field_type in CAPTURE_FIELD_TYPES:
            out = normalize_capture({'label': 'X', 'field_type': field_type})
            assert out['field_type'] == field_type

    def test_label_is_always_present(self):
        """`label` is `required` -- a missing one is a 422, not a default."""
        assert normalize_capture({'name': 'From name'})['label'] == 'From name'
        assert normalize_capture({'title': 'From title'})['label'] == 'From title'
        assert normalize_capture({})['label']

    def test_required_is_always_present_and_boolean(self):
        """`required` is `required|boolean`: it must be SENT, not merely truthy."""
        assert normalize_capture({'label': 'X'})['required'] is False
        assert normalize_capture({'label': 'X', 'required': 1})['required'] is True

    def test_options_are_lifted_from_config_and_rekeyed(self):
        out = normalize_capture({
            'label': 'Plan', 'type': 'select',
            'config': {'options': [{'value': 7, 'label': 'Pro'},
                                   {'value': 8, 'label': 'Enterprise'}]},
        })
        assert out['options'] == [{'id': 7, 'text': 'Pro'}, {'id': 8, 'text': 'Enterprise'}]
        assert 'options' not in out['config'], 'options must not be sent twice'

    def test_option_ids_are_integers_even_when_the_source_uses_slugs(self):
        """`options.*.id` is `required|integer`; a slug id is a 422."""
        out = normalize_capture({
            'label': 'Plan', 'field_type': 'dropdown',
            'options': [{'id': 'pro-plan', 'text': 'Pro'},
                        {'id': 'ent-plan', 'text': 'Enterprise'}],
        })
        assert [o['id'] for o in out['options']] == [1, 2]
        assert all(isinstance(o['id'], int) for o in out['options'])
        assert [o['text'] for o in out['options']] == ['Pro', 'Enterprise']

    def test_numeric_string_option_ids_are_preserved(self):
        out = normalize_capture({
            'label': 'Plan', 'field_type': 'radio',
            'options': [{'id': '4', 'text': 'Pro'}],
        })
        assert out['options'] == [{'id': 4, 'text': 'Pro'}]

    def test_bare_string_options_are_accepted(self):
        out = normalize_capture({'label': 'Plan', 'field_type': 'radio',
                                 'options': ['Pro', 'Enterprise']})
        assert out['options'] == [{'id': 1, 'text': 'Pro'}, {'id': 2, 'text': 'Enterprise'}]

    @pytest.mark.parametrize('field_type', ['radio', 'dropdown', 'multiselect'])
    def test_option_bearing_types_never_ship_without_options(self, field_type):
        """`options` is `required_if` these types -- an empty list is a 422."""
        out = normalize_capture({'label': 'Plan', 'field_type': field_type})
        assert out['options'], f'{field_type} must carry at least one option'
        assert out['options'][0]['text'] == 'Plan'

    def test_table_always_carries_columns(self):
        out = normalize_capture({'label': 'Line items', 'field_type': 'table'})
        assert out['columns'] == [{'id': 1, 'label': 'Line items'}]

    def test_table_columns_are_rekeyed(self):
        out = normalize_capture({
            'label': 'Items', 'field_type': 'table',
            'columns': [{'id': 'sku', 'label': 'SKU'}, {'id': 'qty', 'label': 'Qty'}],
        })
        assert out['columns'] == [{'id': 1, 'label': 'SKU'}, {'id': 2, 'label': 'Qty'}]

    def test_options_are_dropped_from_types_that_reject_them(self):
        out = normalize_capture({'label': 'Notes', 'field_type': 'text',
                                 'options': [{'id': 1, 'text': 'x'}]})
        assert 'options' not in out

    def test_input_is_not_mutated(self):
        source = {'label': 'Plan', 'type': 'select',
                  'config': {'options': [{'value': 1, 'label': 'Pro'}]}}
        normalize_capture(source)
        assert source['type'] == 'select'
        assert source['config']['options'] == [{'value': 1, 'label': 'Pro'}]

    def test_position_is_stamped_only_when_given(self):
        assert 'position' not in normalize_capture({'label': 'X'})
        assert normalize_capture({'label': 'X'}, position=3)['position'] == 3

    def test_a_bare_string_raises_rather_than_being_coerced(self):
        """
        A malformed transformer must surface, not be quietly turned into a
        field named after its own error.
        """
        with pytest.raises(TypeError):
            normalize_capture('Preferred plan')


class TestNormalizeCaptures:

    def test_stamps_one_based_positions(self):
        out = normalize_captures([{'label': 'A'}, {'label': 'B'}, {'label': 'C'}])
        assert [c['position'] for c in out] == [1, 2, 3]

    def test_none_is_empty(self):
        assert normalize_captures(None) == []

    def test_a_dict_raises_rather_than_being_iterated(self):
        """
        `_transform_start_form_fields` returns a dict when it misbehaves.
        Iterating it would silently migrate its KEYS as fields.
        """
        with pytest.raises(TypeError):
            normalize_captures({'label': 'Preferred plan'})


# ---------------------------------------------------------------------------
# Wire contract
# ---------------------------------------------------------------------------

class TestStepCaptureWireContract:

    @pytest.mark.parametrize('vendor', CAPTURE_CLIENT_VENDORS)
    def test_posts_to_the_route_nested_under_both_ids(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.create_step_capture('chk_1', 'step_9', {'label': 'Notes', 'type': 'textarea'})

        method, endpoint = request.call_args.args[:2]
        assert method == 'POST'
        assert endpoint == '/checklists/chk_1/steps/step_9/captures', (
            f'{vendor} posts to {endpoint!r}; the route is nested under BOTH the '
            'checklist and the step'
        )

    @pytest.mark.parametrize('vendor', CAPTURE_CLIENT_VENDORS)
    def test_body_satisfies_create_capture_request(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.create_step_capture(
                'chk_1', 'step_9',
                {'label': 'Plan', 'type': 'select',
                 'config': {'options': [{'value': 3, 'label': 'Pro'}]}},
                position=2,
            )

        body = request.call_args.kwargs['json']
        assert body['label'] == 'Plan'
        assert body['field_type'] == 'dropdown'
        assert body['required'] is False
        assert body['options'] == [{'id': 3, 'text': 'Pro'}]
        assert body['position'] == 2

    @pytest.mark.parametrize('vendor', CAPTURE_CLIENT_VENDORS)
    def test_missing_ids_raise_before_any_request(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            with pytest.raises(ValueError):
                client.create_step_capture('', 'step_9', {'label': 'X'})
            with pytest.raises(ValueError):
                client.create_step_capture('chk_1', '', {'label': 'X'})
        request.assert_not_called()

    @pytest.mark.parametrize('vendor', CAPTURE_CLIENT_VENDORS)
    def test_the_dead_capture_routes_are_gone(self, vendor):
        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
        with open(path) as handle:
            source = handle.read()

        assert "def create_capture(" not in source, (
            f'{vendor} still defines create_capture, whose entity_type-based '
            'endpoint has no route'
        )
        for dead in ("s/{entity_id}/field'", "s/{entity_id}/captures'"):
            assert dead not in source, f'{vendor} still builds the dead endpoint {dead}'

    @pytest.mark.parametrize('vendor', CAPTURE_CLIENT_VENDORS)
    def test_build_prerun_fields_returns_api_shaped_entries(self, vendor):
        _, client = build_client(vendor)

        prerun = client.build_prerun_fields([
            {'label': 'Plan', 'type': 'select',
             'config': {'options': [{'value': 'gold', 'label': 'Gold'}]}},
        ])

        assert prerun == [{
            'label': 'Plan',
            'config': {},
            'field_type': 'dropdown',
            'required': False,
            'options': [{'id': 1, 'text': 'Gold'}],
            'position': 1,
        }]


# ---------------------------------------------------------------------------
# The two migration paths
# ---------------------------------------------------------------------------

def load_orchestrator(vendor, class_name):
    _stub_optional_dependencies()
    vendor_src = os.path.join(REPO_ROOT, vendor, 'src')
    if vendor_src not in sys.path:
        sys.path.insert(0, vendor_src)
    path = os.path.join(vendor_src, 'main.py')
    module_name = f'cap_main_{vendor.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return getattr(module, class_name)


class TestKickOffFieldsRideTheChecklistPayload:
    """
    There is no preruns store route. If kick-off fields are not attached to the
    checklist create body, they are never created at all -- and every kick-off
    value then has nothing to resolve against.
    """

    @pytest.mark.parametrize('vendor,source_file', [
        ('pipefy', 'pipefy/src/main.py'),
        ('process-street', 'process-street/src/main.py'),
    ])
    def test_prerun_is_set_before_the_checklist_is_created(self, vendor, source_file):
        with open(os.path.join(REPO_ROOT, source_file)) as handle:
            source = handle.read()

        assert "build_prerun_fields(" in source, (
            f'{vendor} never builds a prerun array, so kick-off fields are lost'
        )
        assert source.index("build_prerun_fields(") < source.index("create_checklist("), (
            'prerun must be attached BEFORE the checklist is created -- there is '
            'no route to add kick-off fields afterwards'
        )

    @pytest.mark.parametrize('vendor,source_file', [
        ('pipefy', 'pipefy/src/main.py'),
        ('process-street', 'process-street/src/main.py'),
    ])
    def test_step_fields_are_created_with_both_ids(self, vendor, source_file):
        with open(os.path.join(REPO_ROOT, source_file)) as handle:
            source = handle.read()

        assert "create_step_capture(" in source, (
            f'{vendor} never creates step fields, so every step value is orphaned'
        )
        assert "create_capture(" not in source, (
            f'{vendor} still calls create_capture, which targets a dead route'
        )
