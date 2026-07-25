"""
Contract + wiring tests for writing form-field values onto migrated processes.

WHY THIS FILE EXISTS
--------------------
Three independent failures all produced the same symptom -- a migration that
prints a success summary while every field value is gone:

1. ``pipefy`` called ``transform_field_value(field)`` with one argument against
   a two-argument signature, so EVERY field raised ``TypeError``, which a
   blanket ``except Exception`` downgraded to ``logger.warning``.
2. Both live callers PUT to endpoints that do not exist
   (``/runs/{run}/field/{capture}/value``, ``/runs/{run}/captures/{capture}/value``),
   wrapping the value in ``{"value": ...}`` -- a body shape the API never reads.
3. Neither routed values through the shared typed encoder, so choice, table and
   assignee fields would have been flattened to strings even had the call
   landed.

So these tests assert the properties that actually matter at runtime: the wire
contract of every vendor client, and that the two live migration paths encode
per type, key by ``timeline_id``, and fail LOUDLY rather than dropping a value.
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.form_field_values import (  # noqa: E402
    MissingTaskBindingError,
    UnresolvedFormFieldError,
    build_task_form_field_payloads,
    extract_run_form_fields,
    reshape_assignee_values,
)

# 32-char hex timeline_ids -- the only keys the API reads for form-field writes.
TL_NOTES = 'a1b2c3d4e5f60718293a4b5c6d7e8f90'
TL_PLAN = 'ffeeddccbbaa99887766554433221100'
TL_TAGS = '00112233445566778899aabbccddeeff'
TL_PRIORITY = '0f1e2d3c4b5a69788796a5b4c3d2e1f0'

TASK_ONE = 'task_1111'
TASK_TWO = 'task_2222'

# Every vendor client that exposes a single-value form-field writer.
ALL_CLIENT_VENDORS = [
    'basecamp', 'bpmn', 'clickup', 'cognito-forms', 'google-forms', 'jotform',
    'nextmatter', 'pipefy', 'process-street', 'rocketlane', 'surveymonkey',
    'trello', 'typeform', 'wrike',
]

# Clients built as TallyfyClient(api_url, client_id, client_secret, org, slug)
# and authenticating in __init__.
OAUTH_CLIENT_VENDORS = ['bpmn', 'pipefy', 'process-street']

# The two vendors whose migration path actually writes form-field values.
LIVE_WRITER_VENDORS = ['pipefy', 'process-street']


def load_client(vendor):
    """Import a vendor's tallyfy_client module under a unique name."""
    path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
    module_name = f'ffv_tallyfy_client_{vendor.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.TallyfyClient


def build_client(vendor):
    """Instantiate a vendor client without touching the network."""
    client_cls = load_client(vendor)
    if vendor in OAUTH_CLIENT_VENDORS:
        with patch.object(client_cls, '_authenticate', return_value=None):
            return client_cls, client_cls(
                'https://api.example.com', 'id', 'secret', 'org', 'slug'
            )
    return client_cls, client_cls(api_key='test-key', organization='test-org')


def run_form_fields_response():
    """A runs/{id}/form-fields response, shaped exactly as the API returns it."""
    return {'data': {
        'id': 'run_1',
        'form_fields': [
            {'id': TL_NOTES, 'alias': 'notes', 'label': 'Notes',
             'field_type': 'textarea', 'task_id': TASK_ONE},
            {'id': TL_PLAN, 'alias': 'preferred_plan', 'label': 'Preferred Plan',
             'field_type': 'dropdown', 'task_id': TASK_ONE,
             'options': [{'id': 1, 'text': 'Pro'}, {'id': 2, 'text': 'Enterprise'}]},
            {'id': TL_TAGS, 'alias': 'tags', 'label': 'Tags',
             'field_type': 'multiselect', 'task_id': TASK_TWO,
             'options': [{'id': 1, 'text': 'Urgent'}, {'id': 2, 'text': 'Billing'}]},
            {'id': TL_PRIORITY, 'alias': 'priority', 'label': 'Priority',
             'field_type': 'radio', 'task_id': TASK_TWO,
             'options': [{'id': 1, 'text': 'High'}, {'id': 2, 'text': 'Low'}]},
        ],
        'ko_form_fields': [],
    }}


# ---------------------------------------------------------------------------
# Wire contract: every vendor client
# ---------------------------------------------------------------------------

class TestSingleValueWireContract:
    """PUT /organizations/{org}/form-field/value with {"id", "form_value"}."""

    @pytest.mark.parametrize('vendor', ALL_CLIENT_VENDORS)
    def test_uses_the_real_endpoint_and_body(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.set_form_field_value('cv_123', 'Hello')

        method, endpoint = request.call_args.args[:2]
        assert method == 'PUT'
        assert endpoint == '/form-field/value', (
            f'{vendor} PUT to {endpoint!r}, which is not a route the API serves'
        )
        assert request.call_args.kwargs['json'] == {
            'id': 'cv_123', 'form_value': 'Hello',
        }

    @pytest.mark.parametrize('vendor', ALL_CLIENT_VENDORS)
    def test_does_not_wrap_the_value(self, vendor):
        """`{"value": ...}` is a shape the API never reads."""
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.set_form_field_value('cv_123', 'Hello')

        body = request.call_args.kwargs['json']
        assert 'value' not in body, f'{vendor} still wraps the value in `value`'
        assert 'form_value' in body

    @pytest.mark.parametrize('vendor', ALL_CLIENT_VENDORS)
    def test_dead_endpoints_and_their_methods_are_gone(self, vendor):
        """The routes that never existed, and the methods that targeted them."""
        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'tallyfy_client.py')
        with open(path) as handle:
            source = handle.read()

        for dead in ('/fields/{field_id}/value',
                     '/captures/{capture_id}/value',
                     '/field/{capture_id}/value'):
            assert dead not in source, f'{vendor} still targets the dead route {dead}'

        # Asserted on the CLASS, not on a mock: `hasattr` on a MagicMock is
        # always True, so a mock-based version of this check proves nothing.
        client_cls = load_client(vendor)
        for gone in ('set_capture_value', 'set_field_value'):
            assert not hasattr(client_cls, gone), (
                f'{vendor} still exposes {gone}(), which PUT to a route the API '
                'does not serve and wrapped the value in `value`'
            )

    @pytest.mark.parametrize('vendor', ALL_CLIENT_VENDORS)
    def test_a_missing_id_is_rejected_not_sent(self, vendor):
        """The API resolves the capture value by id; it cannot infer it."""
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request') as request:
            with pytest.raises(ValueError):
                client.set_form_field_value('', 'Hello')
        request.assert_not_called()

    @pytest.mark.parametrize('vendor', ALL_CLIENT_VENDORS)
    def test_typed_values_pass_through_unflattened(self, vendor):
        """A dropdown must arrive as {id, text}, not as a string."""
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.set_form_field_value('cv_1', {'id': 2, 'text': 'Enterprise'})

        assert request.call_args.kwargs['json']['form_value'] == {
            'id': 2, 'text': 'Enterprise',
        }


class TestBulkWriterWireContract:
    """PUT /organizations/{org}/runs/{run}/tasks/{task} with {"taskdata": {...}}."""

    @pytest.mark.parametrize('vendor', LIVE_WRITER_VENDORS)
    def test_reads_form_fields_from_the_run(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.get_run_form_fields('run_1')

        assert request.call_args.args == ('GET', '/runs/run_1/form-fields')

    @pytest.mark.parametrize('vendor', LIVE_WRITER_VENDORS)
    def test_writes_taskdata_keyed_by_timeline_id(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request', return_value={}) as request:
            client.update_task_form_field_values(
                'run_1', TASK_ONE, {TL_NOTES: 'Some notes'}
            )

        assert request.call_args.args == ('PUT', f'/runs/run_1/tasks/{TASK_ONE}')
        assert request.call_args.kwargs['json'] == {
            'taskdata': {TL_NOTES: 'Some notes'},
        }

    @pytest.mark.parametrize('vendor', LIVE_WRITER_VENDORS)
    def test_an_empty_write_is_rejected(self, vendor):
        client_cls, client = build_client(vendor)

        with patch.object(client_cls, '_make_request') as request:
            with pytest.raises(ValueError):
                client.update_task_form_field_values('run_1', TASK_ONE, {})
        request.assert_not_called()


# ---------------------------------------------------------------------------
# The shared resolver / grouper
# ---------------------------------------------------------------------------

class TestExtractRunFormFields:

    def test_merges_step_fields_and_kickoff_fields(self):
        response = {'data': {
            'form_fields': [{'id': TL_NOTES}],
            'ko_form_fields': [{'id': TL_PLAN}],
        }}
        assert [f['id'] for f in extract_run_form_fields(response)] == [TL_NOTES, TL_PLAN]

    def test_accepts_a_bare_list(self):
        assert extract_run_form_fields([{'id': TL_NOTES}]) == [{'id': TL_NOTES}]

    def test_an_empty_response_yields_no_fields(self):
        assert extract_run_form_fields(None) == []
        assert extract_run_form_fields({}) == []


class TestReshapeAssigneeValues:
    """
    Source systems key assignee fields by their OWN user ids. Those must be
    mapped to Tallyfy users, and an unmapped one must never be invented.
    """

    TL_OWNER = 'aabbccddeeff00112233445566778899'

    def fields(self):
        return [{'id': self.TL_OWNER, 'alias': 'owner', 'label': 'Owner',
                 'field_type': 'assignees_form', 'task_id': TASK_ONE}]

    def test_source_ids_are_mapped_to_tallyfy_users(self):
        values = {'owner': 'ps_user_42'}
        reshape_assignee_values(
            values, self.fields(),
            user_id_mapper=lambda uid: 7 if uid == 'ps_user_42' else None,
        )
        assert values['owner'] == {'users': [7], 'guests': [], 'groups': []}

    def test_an_unmapped_id_is_never_coerced_into_a_tallyfy_user_id(self):
        """
        `int('12345')` would assign the task to whichever unrelated Tallyfy user
        holds id 12345. Silently wrong is worse than loudly missing.
        """
        values = {'owner': '12345'}
        reshape_assignee_values(values, self.fields(), user_id_mapper=lambda uid: None)
        assert values['owner'] == {'users': [], 'guests': [], 'groups': []}, (
            'an unmapped source id was coerced into a Tallyfy user id'
        )

    def test_an_unmapped_id_then_raises_in_strict_mode(self):
        """The two halves compose: unmapped -> encodes to nobody -> reported."""
        values = {'owner': '12345'}
        reshape_assignee_values(values, self.fields(), user_id_mapper=lambda uid: None)
        with pytest.raises(UnresolvedFormFieldError):
            build_task_form_field_payloads(values, self.fields(), strict=True)

    def test_emails_still_become_guests(self):
        values = {'owner': 'outsider@example.com'}
        reshape_assignee_values(values, self.fields(), user_id_mapper=lambda uid: None)
        assert values['owner'] == {
            'users': [], 'guests': ['outsider@example.com'], 'groups': [],
        }

    def test_a_preshaped_value_is_left_alone(self):
        values = {'owner': {'users': [3], 'guests': [], 'groups': []}}
        reshape_assignee_values(values, self.fields(), user_id_mapper=lambda uid: 99)
        assert values['owner'] == {'users': [3], 'guests': [], 'groups': []}

    def test_non_assignee_fields_are_untouched(self):
        fields = [{'id': TL_NOTES, 'alias': 'notes', 'field_type': 'textarea',
                   'task_id': TASK_ONE}]
        values = {'notes': '12345'}
        reshape_assignee_values(values, fields, user_id_mapper=lambda uid: 7)
        assert values['notes'] == '12345'

    @pytest.mark.parametrize('vendor,source_file', [
        ('pipefy', 'pipefy/src/main.py'),
        ('process-street', 'process-street/src/main.py'),
    ])
    def test_live_paths_reshape_before_building_payloads(self, vendor, source_file):
        with open(os.path.join(REPO_ROOT, source_file)) as handle:
            source = handle.read()
        assert 'reshape_assignee_values(' in source, f'{vendor} never reshapes assignees'
        assert source.index('reshape_assignee_values(') < source.index(
            'build_task_form_field_payloads('
        ), 'assignees must be reshaped BEFORE payloads are built'
        assert "'user'" in source, f'{vendor} must map through the user id space'


class TestEncoderDoesNotInventUserIds:

    def test_a_bare_number_is_not_treated_as_a_tallyfy_user_id(self):
        """
        Source-system ids and Tallyfy ids are unrelated id spaces. Mapping
        happens upstream in reshape_assignee_values; the encoder must not guess.
        """
        from shared.prerun_encoder import encode_assignees_form
        assert encode_assignees_form('12345', [], current_user_id=None) == {
            'users': [], 'guests': [], 'groups': [],
        }

    def test_emails_still_resolve_against_members(self):
        from shared.prerun_encoder import encode_assignees_form
        encoded = encode_assignees_form(
            'member@example.com', [{'id': 7, 'email': 'member@example.com'}]
        )
        assert encoded == {'users': [7], 'guests': [], 'groups': []}


class TestAssigneeValuesNeverWriteNobodySilently:
    """
    `assignees_form` resolves only email-shaped candidates. Source systems key
    assignee fields by user ID or display name, so a non-empty source value can
    encode to an EMPTY assignee payload -- a 200 with the assignees gone.
    """

    TL_OWNER = 'aabbccddeeff00112233445566778899'

    def fields(self):
        return [{'id': self.TL_OWNER, 'alias': 'owner', 'label': 'Owner',
                 'field_type': 'assignees_form', 'task_id': TASK_ONE}]

    @pytest.mark.parametrize('raw', [12345, 'Jane Doe', ['7', '8']])
    def test_unresolvable_assignees_raise_in_strict_mode(self, raw):
        with pytest.raises(UnresolvedFormFieldError):
            build_task_form_field_payloads({'owner': raw}, self.fields(), strict=True)

    @pytest.mark.parametrize('raw', [12345, 'Jane Doe'])
    def test_unresolvable_assignees_are_omitted_not_written_empty(self, raw):
        payloads = build_task_form_field_payloads(
            {'owner': raw}, self.fields(), strict=False
        )
        written = payloads.get(TASK_ONE, {})
        assert self.TL_OWNER not in written, (
            f'wrote {written.get(self.TL_OWNER)!r} -- an empty assignee payload '
            'is silent data loss'
        )

    def test_an_email_still_encodes_normally(self):
        payloads = build_task_form_field_payloads(
            {'owner': 'someone@example.com'}, self.fields(), strict=True
        )
        assert payloads[TASK_ONE][self.TL_OWNER] == {
            'users': [], 'guests': ['someone@example.com'], 'groups': [],
        }

    def test_a_preshaped_dict_still_encodes_normally(self):
        payloads = build_task_form_field_payloads(
            {'owner': {'users': [7]}}, self.fields(), strict=True
        )
        assert payloads[TASK_ONE][self.TL_OWNER]['users'] == [7]

    @pytest.mark.parametrize('raw', [None, '', [], {}])
    def test_a_legitimately_empty_assignee_field_is_not_flagged(self, raw):
        """An empty source value encoding to no assignees is correct, not loss."""
        payloads = build_task_form_field_payloads(
            {'owner': raw}, self.fields(), strict=True
        )
        assert payloads[TASK_ONE][self.TL_OWNER] == {
            'users': [], 'guests': [], 'groups': [],
        }

    def test_other_field_types_are_untouched_by_the_guard(self):
        fields = [{'id': TL_NOTES, 'alias': 'notes', 'label': 'Notes',
                   'field_type': 'textarea', 'task_id': TASK_ONE}]
        payloads = build_task_form_field_payloads({'notes': ''}, fields, strict=True)
        assert TL_NOTES in payloads[TASK_ONE]


class TestBuildTaskFormFieldPayloads:

    FIELDS = extract_run_form_fields(run_form_fields_response())

    def test_groups_values_by_task(self):
        payloads = build_task_form_field_payloads(
            {'notes': 'Hello', 'tags': ['Urgent']}, self.FIELDS
        )
        assert set(payloads) == {TASK_ONE, TASK_TWO}
        assert set(payloads[TASK_ONE]) == {TL_NOTES}
        assert set(payloads[TASK_TWO]) == {TL_TAGS}

    def test_keys_are_timeline_ids_never_source_keys(self):
        payloads = build_task_form_field_payloads({'notes': 'Hello'}, self.FIELDS)
        assert list(payloads[TASK_ONE]) == [TL_NOTES]
        assert 'notes' not in payloads[TASK_ONE]

    def test_dropdown_keeps_both_id_and_text(self):
        payloads = build_task_form_field_payloads(
            {'preferred_plan': 'Enterprise'}, self.FIELDS
        )
        assert payloads[TASK_ONE][TL_PLAN] == {'id': 2, 'text': 'Enterprise'}

    def test_radio_is_bare_text_not_an_object(self):
        """dropdown and radio are deliberately asymmetric."""
        payloads = build_task_form_field_payloads({'priority': 'High'}, self.FIELDS)
        assert payloads[TASK_TWO][TL_PRIORITY] == 'High'

    def test_multiselect_entries_carry_selected_true(self):
        # Without `selected: true` the value stores but renders EMPTY wherever
        # the field is used as a {{variable}}.
        payloads = build_task_form_field_payloads(
            {'tags': ['Urgent', 'Billing']}, self.FIELDS
        )
        assert payloads[TASK_TWO][TL_TAGS] == [
            {'id': 1, 'text': 'Urgent', 'selected': True},
            {'id': 2, 'text': 'Billing', 'selected': True},
        ]

    def test_resolves_by_timeline_id_alias_and_label(self):
        for key in (TL_NOTES, 'notes', 'Notes'):
            payloads = build_task_form_field_payloads({key: 'Hello'}, self.FIELDS)
            assert payloads[TASK_ONE][TL_NOTES] == 'Hello', key

    def test_fallback_keys_rescue_an_unmapped_source_id(self):
        payloads = build_task_form_field_payloads(
            {'pipefy_field_77': 'Hello'}, self.FIELDS,
            fallback_keys={'pipefy_field_77': ['Notes']},
        )
        assert payloads[TASK_ONE][TL_NOTES] == 'Hello'

    def test_an_unresolved_value_raises_by_default(self):
        # The write would still return 200 with the value discarded, so a quiet
        # skip here is silent data loss.
        with pytest.raises(UnresolvedFormFieldError) as excinfo:
            build_task_form_field_payloads({'nope': 'Hello'}, self.FIELDS)
        assert 'nope' in excinfo.value.unresolved

    def test_a_process_with_no_fields_raises(self):
        with pytest.raises(UnresolvedFormFieldError):
            build_task_form_field_payloads({'notes': 'Hello'}, [])

    def test_non_strict_mode_skips_instead_of_raising(self):
        payloads = build_task_form_field_payloads(
            {'notes': 'Hello', 'nope': 'x'}, self.FIELDS, strict=False
        )
        assert payloads[TASK_ONE][TL_NOTES] == 'Hello'
        assert all('nope' not in v for v in payloads.values())

    def test_a_field_without_a_task_raises(self):
        """taskdata is written per task, so a field with no task has nowhere to go."""
        fields = [{'id': TL_NOTES, 'alias': 'notes', 'field_type': 'text'}]
        with pytest.raises(MissingTaskBindingError):
            build_task_form_field_payloads({'notes': 'Hello'}, fields)

    def test_no_values_is_a_no_op(self):
        assert build_task_form_field_payloads({}, self.FIELDS) == {}


# ---------------------------------------------------------------------------
# Live migration paths -- the orchestrators themselves
# ---------------------------------------------------------------------------

# Third-party packages the orchestrators import transitively but that the code
# path under test never touches: console colouring and the optional external
# database migrator (only used when DATABASE_URL is set). The list is explicit
# so a stub can never mask a missing import in the code actually under test.
OPTIONAL_IMPORTS = (
    'colorlog',
    'sqlalchemy', 'sqlalchemy.exc',
    'psycopg2', 'psycopg2.extras',
)


def _stub_optional_dependencies():
    """
    Provide no-op stand-ins for absent optional third-party packages.

    These tests must RUN, not skip. A skipped test is how an unreachable code
    path stays green for months -- exactly the failure mode this file exists to
    catch. Each stub is installed only when the real package is genuinely
    absent, and only for the names listed in ``OPTIONAL_IMPORTS``.
    """
    import logging
    import types
    from unittest.mock import MagicMock

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
            # Attribute access on an unused module must not explode at import.
            stub.__getattr__ = lambda attr: MagicMock()
        sys.modules[name] = stub

    # `from pkg.sub import Name` also needs the submodule bound on its parent.
    for name in OPTIONAL_IMPORTS:
        if '.' not in name:
            continue
        parent_name, _, child = name.rpartition('.')
        parent = sys.modules.get(parent_name)
        if parent is not None and not hasattr(parent, child):
            setattr(parent, child, sys.modules[name])


def load_orchestrator(vendor, module_name):
    """
    Import a vendor's main.py with its own src dir on sys.path.

    The orchestrators are imported, never constructed: their __init__ reads
    config files, dotenv and a checkpoint directory, none of which this test
    needs. Instances are made with __new__ and given mock collaborators, so the
    REAL method under test runs against a fake client.
    """
    _stub_optional_dependencies()
    src = os.path.join(REPO_ROOT, vendor, 'src')
    if src not in sys.path:
        sys.path.insert(0, src)
    path = os.path.join(src, 'main.py')
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_orchestrator(orchestrator_cls, mapped_ids=None):
    """Build an orchestrator with a mock Tallyfy client and id mapper."""
    orchestrator = object.__new__(orchestrator_cls)
    orchestrator.tallyfy_client = MagicMock()
    orchestrator.tallyfy_client.get_run_form_fields.return_value = (
        run_form_fields_response()
    )
    orchestrator.id_mapper = MagicMock()
    lookup = mapped_ids or {}
    orchestrator.id_mapper.get_tallyfy_id.side_effect = (
        lambda source_id, kind: lookup.get(source_id)
    )
    return orchestrator


def written_taskdata(orchestrator):
    """Collapse every taskdata write into one {task_id: {timeline_id: value}}."""
    writes = {}
    for call in orchestrator.tallyfy_client.update_task_form_field_values.call_args_list:
        _run_id, task_id, taskdata = call.args
        writes.setdefault(task_id, {}).update(taskdata)
    return writes


class TestPipefyCardFields:
    """`_migrate_card_fields` used to raise TypeError on EVERY field."""

    CARD = {'id': 'card_1', 'fields': [
        {'field': {'id': 'pf_notes', 'label': 'Notes', 'type': 'long_text'},
         'value': 'Some notes'},
        {'field': {'id': 'pf_plan', 'label': 'Preferred Plan', 'type': 'select'},
         'value': 'Enterprise'},
        {'field': {'id': 'pf_tags', 'label': 'Tags', 'type': 'checklist_horizontal'},
         'value': None, 'array_value': ['Urgent', 'Billing']},
    ]}

    MAPPED = {'pf_notes': TL_NOTES, 'pf_plan': TL_PLAN, 'pf_tags': TL_TAGS}

    def build(self, mapped_ids=None):
        module = load_orchestrator('pipefy', 'ffv_pipefy_main')
        return make_orchestrator(
            module.PipefyMigrationOrchestrator,
            self.MAPPED if mapped_ids is None else mapped_ids,
        )

    def test_every_field_value_reaches_the_api(self):
        # The regression: a one-argument call against a two-argument signature
        # raised TypeError per field, swallowed into a warning, so NOTHING was
        # ever written while the migration reported success.
        orchestrator = self.build()
        orchestrator._migrate_card_fields(self.CARD, 'run_1')

        writes = written_taskdata(orchestrator)
        assert writes[TASK_ONE][TL_NOTES] == 'Some notes'
        assert writes[TASK_ONE][TL_PLAN] == {'id': 2, 'text': 'Enterprise'}
        assert writes[TASK_TWO][TL_TAGS] == [
            {'id': 1, 'text': 'Urgent', 'selected': True},
            {'id': 2, 'text': 'Billing', 'selected': True},
        ]

    def test_the_dead_single_value_writer_is_not_used(self):
        # `hasattr`/`.called` on a MagicMock proves nothing, so assert on the
        # calls that were actually recorded: the only writes must be taskdata.
        orchestrator = self.build()
        orchestrator._migrate_card_fields(self.CARD, 'run_1')

        called = {
            name.split('.')[0]
            for name, _args, _kwargs in orchestrator.tallyfy_client.mock_calls
        }
        assert called == {'get_run_form_fields', 'update_task_form_field_values'}, (
            f'unexpected client calls: {sorted(called)}'
        )

    def test_array_value_wins_so_multiselects_keep_their_shape(self):
        orchestrator = self.build()
        orchestrator._migrate_card_fields(self.CARD, 'run_1')
        assert isinstance(written_taskdata(orchestrator)[TASK_TWO][TL_TAGS], list)

    def test_an_unmapped_field_still_resolves_by_label(self):
        orchestrator = self.build(mapped_ids={})
        orchestrator._migrate_card_fields(self.CARD, 'run_1')
        assert written_taskdata(orchestrator)[TASK_ONE][TL_NOTES] == 'Some notes'

    def test_a_field_missing_from_the_template_fails_loudly(self):
        orchestrator = self.build()
        card = {'id': 'card_2', 'fields': [
            {'field': {'id': 'pf_ghost', 'label': 'Not On The Template',
                       'type': 'short_text'}, 'value': 'x'},
        ]}
        with pytest.raises(UnresolvedFormFieldError):
            orchestrator._migrate_card_fields(card, 'run_1')

    def test_nothing_is_written_when_a_value_cannot_be_placed(self):
        """A partial write would leave the process half-migrated and look fine."""
        orchestrator = self.build()
        card = {'id': 'card_3', 'fields': [
            {'field': {'id': 'pf_notes', 'label': 'Notes', 'type': 'long_text'},
             'value': 'Some notes'},
            {'field': {'id': 'pf_ghost', 'label': 'Ghost', 'type': 'short_text'},
             'value': 'x'},
        ]}
        with pytest.raises(UnresolvedFormFieldError):
            orchestrator._migrate_card_fields(card, 'run_1')
        orchestrator.tallyfy_client.update_task_form_field_values.assert_not_called()

    def test_a_card_with_no_fields_makes_no_api_calls(self):
        orchestrator = self.build()
        orchestrator._migrate_card_fields({'id': 'card_4', 'fields': []}, 'run_1')
        orchestrator.tallyfy_client.get_run_form_fields.assert_not_called()

    def test_an_api_failure_is_not_swallowed(self):
        # The blanket `except Exception -> logger.warning` made every hard
        # failure invisible.
        orchestrator = self.build()
        orchestrator.tallyfy_client.update_task_form_field_values.side_effect = (
            RuntimeError('500 from the API')
        )
        with pytest.raises(RuntimeError):
            orchestrator._migrate_card_fields(self.CARD, 'run_1')


class TestPipefyPipePhaseShape:
    """
    The pipe phase must read the shape the transformer actually returns.

    `transform_pipe_to_checklist` returns the checklist itself, with a FLAT
    `steps` list and each step's phase under `config.phase_metadata`. The phase
    used to read `checklist_data['multiselect']` and `['step_groups']`, neither
    of which exists -- a KeyError that aborted every pipe before any card, and
    so before any field value, could be migrated.
    """

    PIPE = {'id': 'pipe_1', 'name': 'Onboarding'}

    CHECKLIST = {
        'id': 'chk_1',
        'title': 'Onboarding',
        'steps': [
            {'id': 'stp_1', 'title': 'Enter Intake',
             'config': {'phase_metadata': {'phase_id': 'phase_1'}}},
            {'id': 'stp_2', 'title': 'Complete Intake',
             'config': {'phase_metadata': {'phase_id': 'phase_1'}}},
        ],
        'field': [{'id': 'cap_1', 'label': 'Company Name'}],
    }

    def build(self):
        module = load_orchestrator('pipefy', 'ffv_pipefy_main')
        orchestrator = make_orchestrator(module.PipefyMigrationOrchestrator)
        orchestrator.pipefy_client = MagicMock()
        orchestrator.pipefy_client.list_pipes.return_value = [self.PIPE]
        orchestrator.pipefy_client.get_pipe.return_value = self.PIPE
        orchestrator.phase_transformer = MagicMock()
        orchestrator.phase_transformer.transform_pipe_to_checklist.return_value = (
            dict(self.CHECKLIST)
        )
        orchestrator.tallyfy_client.create_checklist.return_value = {'id': 'chk_live'}
        orchestrator.tallyfy_client.create_step.side_effect = (
            lambda _cid, step: {'id': f"live_{step['id']}"}
        )
        orchestrator.progress = MagicMock()
        orchestrator.progress.track.side_effect = lambda items, **_kw: items
        orchestrator.config = {'migration': {'options': {'continue_on_error': False}}}
        return orchestrator

    def test_the_pipe_phase_completes(self):
        orchestrator = self.build()
        result = orchestrator._phase_pipes(dry_run=False)
        assert result['successful'] == 1, f'pipe phase failed: {result}'

    def test_the_checklist_itself_is_posted(self):
        orchestrator = self.build()
        orchestrator._phase_pipes(dry_run=False)
        posted = orchestrator.tallyfy_client.create_checklist.call_args.args[0]
        assert posted['title'] == 'Onboarding'

    def test_every_step_in_the_flat_list_is_created(self):
        orchestrator = self.build()
        orchestrator._phase_pipes(dry_run=False)
        assert orchestrator.tallyfy_client.create_step.call_count == 2

    def test_phase_ids_are_read_from_step_config(self):
        orchestrator = self.build()
        orchestrator._phase_pipes(dry_run=False)
        mapped = [
            call.args for call in orchestrator.id_mapper.add_mapping.call_args_list
            if call.args[2] == 'step_group'
        ]
        assert [m[0] for m in mapped] == ['phase_1', 'phase_1']

    def test_a_malformed_start_form_list_is_skipped_not_fed_to_the_api(self):
        # _transform_start_form_fields returns a dict when it misfires; iterating
        # one would migrate its KEYS as kick-off fields.
        orchestrator = self.build()
        broken = dict(self.CHECKLIST)
        broken['field'] = {'id': 'cap_1', 'label': 'Company Name'}
        orchestrator.phase_transformer.transform_pipe_to_checklist.return_value = broken

        result = orchestrator._phase_pipes(dry_run=False)
        assert result['successful'] == 1
        orchestrator.tallyfy_client.build_prerun_fields.assert_not_called()
        posted = orchestrator.tallyfy_client.create_checklist.call_args.args[0]
        assert 'prerun' not in posted

    def test_a_well_formed_start_form_becomes_the_checklist_prerun(self):
        """
        There is no route to add kick-off fields after creation, so they must
        be on the create payload or they are lost outright.
        """
        orchestrator = self.build()
        with_start_form = dict(self.CHECKLIST)
        with_start_form['field'] = [{'label': 'Company Name', 'type': 'text'}]
        orchestrator.phase_transformer.transform_pipe_to_checklist.return_value = with_start_form

        result = orchestrator._phase_pipes(dry_run=False)
        assert result['successful'] == 1

        orchestrator.tallyfy_client.build_prerun_fields.assert_called_once_with(
            [{'label': 'Company Name', 'type': 'text'}]
        )
        posted = orchestrator.tallyfy_client.create_checklist.call_args.args[0]
        assert 'prerun' in posted, 'kick-off fields never reached the create payload'

    def test_step_fields_are_created_against_both_ids(self):
        orchestrator = self.build()
        with_step_fields = dict(self.CHECKLIST)
        with_step_fields['steps'] = [
            dict(step, field=[{'label': 'Notes', 'type': 'textarea'}])
            for step in self.CHECKLIST['steps']
        ]
        orchestrator.phase_transformer.transform_pipe_to_checklist.return_value = with_step_fields

        orchestrator._phase_pipes(dry_run=False)

        calls = orchestrator.tallyfy_client.create_step_capture.call_args_list
        assert calls, 'step fields were never created; every step value is orphaned'
        for call in calls:
            checklist_id, step_id, capture = call.args[:3]
            assert checklist_id, 'step captures need the checklist id'
            assert step_id, 'step captures need the step id'
            assert capture['label'] == 'Notes'


class TestProcessStreetFormValues:
    """`_migrate_form_values` PUT to a route that does not exist."""

    RUN = {'id': 'ps_run_1', 'formValues': {
        'ps_notes': 'Some notes',
        'ps_plan': 'Enterprise',
        'ps_priority': 'High',
    }}

    MAPPED = {'ps_notes': TL_NOTES, 'ps_plan': TL_PLAN, 'ps_priority': TL_PRIORITY}

    def build(self, mapped_ids=None):
        module = load_orchestrator('process-street', 'ffv_ps_main')
        return make_orchestrator(
            module.MigrationOrchestrator,
            self.MAPPED if mapped_ids is None else mapped_ids,
        )

    def test_values_are_encoded_per_type_and_keyed_by_timeline_id(self):
        orchestrator = self.build()
        orchestrator._migrate_form_values(self.RUN, 'run_1')

        writes = written_taskdata(orchestrator)
        assert writes[TASK_ONE][TL_NOTES] == 'Some notes'
        assert writes[TASK_ONE][TL_PLAN] == {'id': 2, 'text': 'Enterprise'}
        # radio takes the option TEXT as a bare scalar, unlike dropdown.
        assert writes[TASK_TWO][TL_PRIORITY] == 'High'

    def test_writes_are_grouped_one_call_per_task(self):
        orchestrator = self.build()
        orchestrator._migrate_form_values(self.RUN, 'run_1')
        assert orchestrator.tallyfy_client.update_task_form_field_values.call_count == 2

    def test_a_value_with_no_matching_field_fails_loudly(self):
        orchestrator = self.build(mapped_ids={})
        with pytest.raises(UnresolvedFormFieldError):
            orchestrator._migrate_form_values(
                {'id': 'r', 'formValues': {'ps_ghost': 'x'}}, 'run_1'
            )

    def test_a_run_with_no_form_values_makes_no_api_calls(self):
        orchestrator = self.build()
        orchestrator._migrate_form_values({'id': 'r', 'formValues': {}}, 'run_1')
        orchestrator.tallyfy_client.get_run_form_fields.assert_not_called()

    def test_an_api_failure_is_not_swallowed(self):
        orchestrator = self.build()
        orchestrator.tallyfy_client.update_task_form_field_values.side_effect = (
            RuntimeError('500 from the API')
        )
        with pytest.raises(RuntimeError):
            orchestrator._migrate_form_values(self.RUN, 'run_1')

    def test_a_stored_label_rescues_a_value_whose_mapped_id_does_not_match(self):
        """
        Pins the `field_label` fallback.

        Process Street form values are keyed by an opaque PS field id. Nothing
        on the target process is keyed that way, so without the label recorded
        at template time (`_store_field_label`) every value would fail to
        resolve and the whole run would raise. This is the only thing making PS
        value migration work, and it arrived with no test of its own.
        """
        module = load_orchestrator('process-street', 'ffv_ps_main')
        orchestrator = make_orchestrator(module.MigrationOrchestrator)

        # The capture id recorded at template time is stale/unmatched; only the
        # label matches a live field on the process.
        stored = {
            ('ps_notes', 'field'): 'stale_capture_id',
            ('ps_notes', 'field_label'): 'Notes',
        }
        orchestrator.id_mapper.get_tallyfy_id.side_effect = (
            lambda source_id, kind: stored.get((source_id, kind))
        )

        orchestrator._migrate_form_values(
            {'id': 'r', 'formValues': {'ps_notes': 'Some notes'}}, 'run_1'
        )

        assert written_taskdata(orchestrator)[TASK_ONE][TL_NOTES] == 'Some notes'

    def test_template_migration_records_the_label_for_each_capture(self):
        """`_store_field_label` must record external_ref -> label under `field_label`."""
        module = load_orchestrator('process-street', 'ffv_ps_main')
        orchestrator = make_orchestrator(module.MigrationOrchestrator)

        orchestrator._store_field_label(
            {'id': 'cap_1', 'external_ref': 'ps_notes', 'label': 'Notes'}
        )

        orchestrator.id_mapper.add_mapping.assert_called_once_with(
            'ps_notes', 'Notes', 'field_label'
        )

    def test_a_capture_without_a_source_ref_records_nothing(self):
        module = load_orchestrator('process-street', 'ffv_ps_main')
        orchestrator = make_orchestrator(module.MigrationOrchestrator)

        orchestrator._store_field_label({'id': 'cap_1', 'label': 'Notes'})

        orchestrator.id_mapper.add_mapping.assert_not_called()
