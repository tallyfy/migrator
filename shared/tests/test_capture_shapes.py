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

    def test_downgrading_an_unsupported_type_is_logged_not_silent(self, caplog):
        """
        Process Street emits signature/location/rating/slider/time, none of which
        Tallyfy has. Migrating them as text is correct; doing it silently is how
        a downgrade goes unnoticed.
        """
        with caplog.at_level('WARNING'):
            normalize_capture({'label': 'Sign here', 'type': 'signature'})

        assert any('signature' in r.getMessage() for r in caplog.records), (
            'an unsupported field type was downgraded to text without a warning'
        )

    def test_a_supported_type_does_not_warn(self, caplog):
        with caplog.at_level('WARNING'):
            normalize_capture({'label': 'Notes', 'type': 'textarea'})
            normalize_capture({'label': 'Who', 'type': 'user'})
            normalize_capture({'label': 'Docs', 'type': 'files'})
        assert not caplog.records, f'unexpected warnings: {[r.message for r in caplog.records]}'

    def test_a_field_with_no_type_at_all_does_not_warn(self, caplog):
        with caplog.at_level('WARNING'):
            out = normalize_capture({'label': 'X'})
        assert out['field_type'] == 'text'
        assert not caplog.records

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

    def test_is_required_alias_is_honoured(self):
        """Pipefy and Process Street emit ``is_required`` instead of ``required``."""
        assert normalize_capture({'label': 'X', 'is_required': True})['required'] is True
        assert normalize_capture({'label': 'X', 'is_required': False})['required'] is False

    def test_explicit_required_takes_precedence_over_is_required(self):
        out = normalize_capture({'label': 'X', 'required': True, 'is_required': False})
        assert out['required'] is True

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

    def test_mixed_numeric_and_slug_ids_never_collide(self):
        """
        A numeric source id is kept as-is; a slug id falls back to a generated
        one. Generating from the positional index collided with a kept id --
        `[{id:2},{id:'slug'}]` produced two options both numbered 2, which makes
        value resolution by option id ambiguous.
        """
        out = normalize_capture({
            'label': 'Plan', 'field_type': 'dropdown',
            'options': [{'id': 2, 'text': 'A'}, {'id': 'slug', 'text': 'B'}],
        })
        ids = [o['id'] for o in out['options']]
        assert len(set(ids)) == len(ids), f'duplicate option ids: {out["options"]}'
        assert out['options'][0] == {'id': 2, 'text': 'A'}, 'a numeric source id must be preserved'

    def test_generated_ids_skip_every_taken_numeric_id(self):
        out = normalize_capture({
            'label': 'Plan', 'field_type': 'multiselect',
            'options': [{'id': 1, 'text': 'A'}, {'id': 'x', 'text': 'B'},
                        {'id': 2, 'text': 'C'}, {'id': 'y', 'text': 'D'}],
        })
        ids = [o['id'] for o in out['options']]
        assert len(set(ids)) == len(ids), f'duplicate option ids: {ids}'
        assert all(isinstance(i, int) for i in ids)
        # The two numeric source ids survive untouched.
        assert out['options'][0]['id'] == 1 and out['options'][2]['id'] == 2

    def test_table_column_ids_are_unique_too(self):
        out = normalize_capture({
            'label': 'Items', 'field_type': 'table',
            'columns': [{'id': 2, 'label': 'SKU'}, {'id': 'qty', 'label': 'Qty'}],
        })
        ids = [c['id'] for c in out['columns']]
        assert len(set(ids)) == len(ids), f'duplicate column ids: {out["columns"]}'

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


class TestAliasesCoverWhatTheTransformersActuallyEmit:
    """
    The alias table is only correct relative to the values the vendor
    FieldTransformers really produce. `user` and `files` were missing from the
    first version of this module and silently became `text`; this reads the
    real FIELD_TYPE_MAPPING and fails if that regresses.
    """

    EMITTERS = [
        ('pipefy', 'pipefy/src/transformers/field_transformer.py', 'FieldTransformer'),
        ('process-street', 'process-street/src/transformers/form_transformer.py', 'FormTransformer'),
    ]

    # Types Tallyfy genuinely has no equivalent for. These SHOULD become text.
    KNOWN_UNSUPPORTED = {'time', 'signature', 'location', 'rating', 'slider'}

    def emitted_types(self, rel_path, class_name):
        """
        Read FIELD_TYPE_MAPPING statically. These modules use relative imports,
        so importing one standalone fails; parsing sidesteps that and keeps the
        test honest about what is literally in the source.
        """
        import ast

        with open(os.path.join(REPO_ROOT, rel_path)) as handle:
            tree = ast.parse(handle.read())

        for node in ast.walk(tree):
            if not (isinstance(node, ast.ClassDef) and node.name == class_name):
                continue
            for stmt in node.body:
                targets = getattr(stmt, 'targets', [])
                if (isinstance(stmt, ast.Assign) and targets
                        and isinstance(targets[0], ast.Name)
                        and targets[0].id == 'FIELD_TYPE_MAPPING'):
                    mapping = ast.literal_eval(stmt.value)
                    return set(mapping.values())

        raise AssertionError(f'{class_name}.FIELD_TYPE_MAPPING not found in {rel_path}')

    @pytest.mark.parametrize('vendor,rel_path,class_name', EMITTERS)
    def test_every_emitted_type_maps_to_a_real_tallyfy_type(self, vendor, rel_path, class_name):
        emitted = self.emitted_types(rel_path, class_name)

        downgraded = {
            source for source in emitted
            if normalize_capture({'label': 'X', 'type': source})['field_type'] == 'text'
            and source != 'text'
        }

        unexpected = downgraded - self.KNOWN_UNSUPPORTED
        assert not unexpected, (
            f'{vendor} emits {sorted(unexpected)}, which silently become `text`. '
            'Add an alias in shared/capture_shapes.py or add them to '
            'KNOWN_UNSUPPORTED with a reason.'
        )

    # Pipefy's real Field.type identifiers, per
    # https://developers.pipefy.com/reference/fields
    PIPEFY_SOURCE_TYPES = [
        'short_text', 'long_text', 'checklist_horizontal', 'checklist_vertical',
        'radio_horizontal', 'radio_vertical', 'select', 'email', 'phone',
        'number', 'date', 'datetime', 'due_date', 'attachment', 'label_select',
        'assignee_select', 'connector', 'statement', 'cpf', 'cnpj', 'currency',
        'id',
    ]

    def test_every_real_pipefy_source_type_is_mapped_not_defaulted(self):
        """
        `_map_field_type` falls back to "text" for anything not in the map, so a
        MISSING key is silent: a Pipefy long_text became a 255-char text field
        and checklists lost their multi-select shape. The map's keys must be
        Pipefy's identifiers, not Tallyfy's.
        """
        import ast
        path = os.path.join(REPO_ROOT, 'pipefy/src/transformers/field_transformer.py')
        with open(path) as handle:
            tree = ast.parse(handle.read())

        mapping = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'FieldTransformer':
                for stmt in node.body:
                    targets = getattr(stmt, 'targets', [])
                    if (isinstance(stmt, ast.Assign) and targets
                            and isinstance(targets[0], ast.Name)
                            and targets[0].id == 'FIELD_TYPE_MAPPING'):
                        mapping = ast.literal_eval(stmt.value)
        assert mapping is not None

        missing = [t for t in self.PIPEFY_SOURCE_TYPES if t not in mapping]
        assert not missing, (
            f'Pipefy source types {missing} are not in FIELD_TYPE_MAPPING, so they '
            'silently default to `text`'
        )

    @pytest.mark.parametrize('source,expected', [
        ('long_text', 'textarea'),
        ('checklist_vertical', 'multiselect'),
        ('checklist_horizontal', 'multiselect'),
        ('radio_vertical', 'radio'),
        ('radio_horizontal', 'radio'),
        ('email', 'email'),
        ('label_select', 'dropdown'),
        ('assignee_select', 'assignees_form'),
        ('attachment', 'file'),
    ])
    def test_pipefy_types_survive_end_to_end(self, source, expected):
        """Transformer map + capture_shapes aliases, composed."""
        import ast
        path = os.path.join(REPO_ROOT, 'pipefy/src/transformers/field_transformer.py')
        with open(path) as handle:
            tree = ast.parse(handle.read())
        mapping = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'FieldTransformer':
                for stmt in node.body:
                    targets = getattr(stmt, 'targets', [])
                    if (isinstance(stmt, ast.Assign) and targets
                            and isinstance(targets[0], ast.Name)
                            and targets[0].id == 'FIELD_TYPE_MAPPING'):
                        mapping = ast.literal_eval(stmt.value)

        emitted = mapping.get(source, 'text')
        final = normalize_capture({'label': 'X', 'type': emitted})['field_type']
        assert final == expected, (
            f'Pipefy {source!r} -> transformer {emitted!r} -> Tallyfy {final!r}, '
            f'expected {expected!r}'
        )

    # Pipefy source types that carry options. `_create_field_config` receives the
    # SOURCE type (`transform()` calls `_map_field_type` separately for `type`),
    # so a source type missing from its list gets NO options transformed --
    # and normalize_capture then has to invent a placeholder option.
    OPTION_BEARING_SOURCE_TYPES = [
        'select', 'radio_horizontal', 'radio_vertical',
        'checklist_horizontal', 'checklist_vertical', 'label_select',
    ]

    @pytest.mark.parametrize('source_type', OPTION_BEARING_SOURCE_TYPES)
    def test_option_bearing_source_types_get_their_options_transformed(self, source_type):
        import ast
        path = os.path.join(REPO_ROOT, 'pipefy/src/transformers/field_transformer.py')
        with open(path) as handle:
            tree = ast.parse(handle.read())

        listed = set()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef)
                    and node.name == '_create_field_config'):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and isinstance(sub.ops[0], ast.In):
                    try:
                        listed |= set(ast.literal_eval(sub.comparators[0]))
                    except (ValueError, TypeError):
                        continue

        assert source_type in listed, (
            f'{source_type!r} carries options in Pipefy but is not in '
            "_create_field_config's option-bearing list, so its options are "
            'dropped and the field is created with a placeholder option'
        )

    def test_assignee_and_file_types_survive(self):
        """The two that regressed. `user`/`users` -> assignees_form, `files` -> file."""
        assert normalize_capture({'label': 'X', 'type': 'user'})['field_type'] == 'assignees_form'
        assert normalize_capture({'label': 'X', 'type': 'users'})['field_type'] == 'assignees_form'
        assert normalize_capture({'label': 'X', 'type': 'files'})['field_type'] == 'file'


class TestRequiredFlagSurvivesTheTransformers:
    """
    pipefy/field_transformer.py and process-street/form_transformer.py both emit
    `is_required`, not `required`. Reading only `required` marked every migrated
    field optional regardless of the source.
    """

    def test_is_required_is_honoured(self):
        assert normalize_capture({'label': 'X', 'is_required': True})['required'] is True
        assert normalize_capture({'label': 'X', 'is_required': False})['required'] is False

    def test_required_wins_when_both_are_present(self):
        out = normalize_capture({'label': 'X', 'required': True, 'is_required': False})
        assert out['required'] is True

    @pytest.mark.parametrize('rel_path', [
        'pipefy/src/transformers/field_transformer.py',
        'process-street/src/transformers/form_transformer.py',
    ])
    def test_the_transformers_really_do_emit_is_required(self, rel_path):
        """Pins the premise. If a transformer switches key, this test tells you."""
        with open(os.path.join(REPO_ROOT, rel_path)) as handle:
            assert "'is_required'" in handle.read(), (
                f'{rel_path} no longer emits is_required; revisit the fallback'
            )


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


# ---------------------------------------------------------------------------
# Repo-wide kick-off delivery gate
# ---------------------------------------------------------------------------
#
# The two tests above pinned pipefy and process-street. Everyone else was
# unpinned, and everyone else was broken -- in three distinct ways:
#
#   1. Eleven clients define `add_kickoff_form`, which POSTs to
#      `/checklists/{id}/preruns`. That route does not exist, and the method
#      has zero callers in any orchestrator. It is dead code pointing at a
#      dead route, and its presence is why the gap looked "nearly done".
#
#   2. Those same eleven expose `create_checklist(name, description, steps)`
#      -- three positional parameters that build a fixed six-key body inside
#      the method. There is no parameter a kick-off array could travel in, so
#      the fix is not a call-site change; the signature itself forecloses it.
#
#   3. asana, kissflow and monday have no `create_checklist` at all. They call
#      `create_blueprint`, which DOES take a `kick_off_form` argument -- but no
#      orchestrator passes it, and `kick_off_form` is not the key the API
#      reads. Their template transformers build the kick-off form and then it
#      is dropped on the floor.
#
# So: every vendor except pipefy and process-street builds kick-off fields and
# delivers none of them.

ALL_VENDORS = [
    'asana', 'basecamp', 'bpmn', 'clickup', 'cognito-forms', 'google-forms',
    'jotform', 'kissflow', 'monday', 'nextmatter', 'pipefy', 'process-street',
    'rocketlane', 'surveymonkey', 'trello', 'typeform', 'wrike',
]


class TestNoVendorTargetsTheDeadPrerunsRoute:
    """`POST /checklists/{id}/preruns` is not a route api-v2 serves."""

    @pytest.mark.parametrize('vendor', ALL_VENDORS)
    def test_add_kickoff_form_is_gone(self, vendor):
        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
        if not os.path.exists(path):
            pytest.skip(f'{vendor} has no tallyfy_client.py')
        with open(path) as handle:
            source = handle.read()

        assert 'def add_kickoff_form' not in source, (
            f'{vendor} still defines add_kickoff_form, which POSTs to the '
            f'non-existent /checklists/{{id}}/preruns route. Kick-off fields '
            f'ride a `prerun` array on the checklist create body instead.'
        )

    @pytest.mark.parametrize('vendor', ALL_VENDORS)
    def test_no_client_posts_to_a_preruns_path(self, vendor):
        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
        if not os.path.exists(path):
            pytest.skip(f'{vendor} has no tallyfy_client.py')
        with open(path) as handle:
            source = handle.read()

        assert '/preruns' not in source, (
            f'{vendor} references a /preruns path; no such route exists'
        )


class TestEveryVendorCanCarryKickOffFields:
    """A client whose signature cannot accept `prerun` can never deliver one."""

    @pytest.mark.parametrize('vendor', ALL_VENDORS)
    def test_the_template_creator_accepts_a_prerun_array(self, vendor):
        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
        if not os.path.exists(path):
            pytest.skip(f'{vendor} has no tallyfy_client.py')
        with open(path) as handle:
            source = handle.read()

        assert 'def build_prerun_fields' in source, (
            f'{vendor} cannot normalise kick-off fields into the shape '
            f'CreateCaptureRequest accepts'
        )
        assert "'prerun'" in source or '"prerun"' in source, (
            f'{vendor} never names the `prerun` key, so whatever its template '
            f'transformer builds is dropped before the request is sent'
        )


# Vendors whose orchestrator reaches a live template-creation call. The rest
# either have that call commented out (basecamp, clickup, cognito-forms,
# google-forms, jotform, nextmatter, trello, wrike -- all eight reference
# `create_template`, a method that exists nowhere in this repo) or call other
# methods that do not exist (bpmn, rocketlane). Wiring a `prerun` into a call
# that never runs would be theatre, so those are tracked on the issue instead
# of being pinned here.
WIRED_VENDORS = [
    ('asana', 'asana/src/main.py'),
    ('kissflow', 'kissflow/src/main.py'),
    ('monday', 'monday/src/main.py'),
    ('pipefy', 'pipefy/src/main.py'),
    ('process-street', 'process-street/src/main.py'),
    ('surveymonkey', 'surveymonkey/src/main.py'),
    ('typeform', 'typeform/src/main.py'),
]


class TestWiredOrchestratorsActuallySendKickOffFields:
    """A client that CAN carry `prerun` still delivers nothing unless asked to.

    The repo-wide gate above only inspects `tallyfy_client.py`. It went green
    while all seventeen orchestrators still created templates with no kick-off
    fields at all -- which is exactly the shape of the original bug.
    """

    @pytest.mark.parametrize('vendor,source_file', WIRED_VENDORS)
    def test_kick_off_fields_reach_the_create_call(self, vendor, source_file):
        with open(os.path.join(REPO_ROOT, source_file)) as handle:
            source = handle.read()

        sends_prerun = "prerun=" in source or "['prerun']" in source
        assert sends_prerun, (
            f'{vendor} creates a template without passing kick-off fields, so '
            f'they are never created and every kick-off value at launch has '
            f'nothing to resolve against'
        )

    @pytest.mark.parametrize('vendor,source_file', WIRED_VENDORS)
    def test_the_whole_blueprint_is_not_passed_as_the_title(self, vendor, source_file):
        """Regression: two orchestrators handed the blueprint dict to a
        positional `name` parameter.

        monday sent `{'name': <the entire blueprint>, 'steps': []}`, dropping
        every step and field; typeform's client then sliced that dict
        (`name[:250]`), so its template creation could never succeed at all.
        """
        with open(os.path.join(REPO_ROOT, source_file)) as handle:
            source = handle.read()

        for bad in ('create_checklist(blueprint)', 'create_blueprint(blueprint)'):
            assert bad not in source, (
                f'{vendor} passes the whole blueprint dict into a positional '
                f'`name` parameter'
            )
