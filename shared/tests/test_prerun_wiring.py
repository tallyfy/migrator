"""
Tests that the typed prerun encoder is REACHED on live migration paths.

WHY THIS FILE EXISTS
--------------------
`test_prerun_request_key.py` pins that the request KEY is `prerun`, not
`prerun_data`. That test passed while every live path still sent source-system
ids as the prerun OBJECT KEYS -- which the API silently discards. The rename was
verified; the thing the rename was for was not.

So these tests assert the two properties that actually matter at runtime:

1. the encoder is genuinely invoked on the path a migration takes, and
2. the resulting keys are the target template's `timeline_id`s -- never a
   Typeform field id, a SurveyMonkey question id, or a Kissflow field name.

A test that only inspects the encoder in isolation cannot catch an unreachable
encoder, so each test here drives the VENDOR entry point, not the encoder.
"""

import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.kickoff_fields import (  # noqa: E402
    KickoffFieldCache,
    NoKickoffFieldsDefined,
    extract_kickoff_fields,
)
from shared.prerun_encoder import (  # noqa: E402
    TableShapeError,
    UnresolvedFieldError,
    build_prerun_payload,
)

# A 32-char hex timeline_id, the only key shape the API reads.
TL_COMPANY = 'a1b2c3d4e5f60718293a4b5c6d7e8f90'
TL_PLAN = 'ffeeddccbbaa99887766554433221100'


def load_vendor_module(vendor, relpath, name):
    """Import a vendor module by path, with its own src dir on sys.path."""
    src = os.path.join(REPO_ROOT, vendor, 'src')
    if src not in sys.path:
        sys.path.insert(0, src)
    path = os.path.join(src, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def kickoff_definitions():
    """Kick-off fields exactly as the API returns them (`id` IS the timeline_id)."""
    return [
        {'id': TL_COMPANY, 'alias': 'company_name', 'label': 'Company Name',
         'field_type': 'text'},
        {'id': TL_PLAN, 'alias': 'preferred_plan', 'label': 'Preferred Plan',
         'field_type': 'dropdown',
         'options': [{'id': 1, 'text': 'Pro'}, {'id': 2, 'text': 'Enterprise'}]},
    ]


class TestEncoderIsReachable:
    """The encoder must be importable from vendor code, not silently None."""

    @pytest.mark.parametrize('vendor', ['typeform', 'surveymonkey', 'rocketlane'])
    def test_vendor_transformer_has_a_live_encoder(self, vendor):
        # Vendors run as scripts with only <vendor>/src on sys.path, so `import
        # shared` used to fail and the encoder fell back to None -- making the
        # typed path unreachable even where it was wired.
        module = load_vendor_module(
            vendor, 'transformers/instance_transformer.py', f'{vendor}_it'
        )
        assert module.build_prerun_payload is not None, (
            f"{vendor} could not import the shared encoder; it would silently "
            "fall back to stringifying values under source-system keys"
        )


class TestTypeform:
    """Typeform answers must land under timeline_ids, once each."""

    def build(self):
        module = load_vendor_module(
            'typeform', 'transformers/instance_transformer.py', 'tf_it'
        )
        return module.InstanceTransformer()

    FORM = {'fields': [
        {'id': 'abc123', 'title': 'Company Name'},
        {'id': 'def456', 'title': 'Preferred Plan'},
    ]}

    RESPONSE = {'response_id': 'r1234567', 'answers': [
        {'field': {'id': 'abc123', 'ref': 'ref_company'}, 'type': 'text',
         'text': 'Acme Corp'},
        {'field': {'id': 'def456', 'ref': 'ref_plan'}, 'type': 'choice',
         'choice': {'label': 'Enterprise'}},
    ]}

    def test_keys_are_timeline_ids(self):
        process = self.build().transform(
            self.RESPONSE, 'chk_1', self.FORM, kickoff_definitions()
        )
        assert set(process['prerun']) == {TL_COMPANY, TL_PLAN}

    def test_source_ids_never_appear_as_keys(self):
        process = self.build().transform(
            self.RESPONSE, 'chk_1', self.FORM, kickoff_definitions()
        )
        for key in process['prerun']:
            assert not key.startswith('field_'), 'Typeform field id leaked as a key'
            assert not key.startswith('ref_'), 'Typeform ref leaked as a key'
            assert 'abc123' not in key and 'def456' not in key

    def test_no_duplicate_entry_per_answer(self):
        # Previously each answer was written twice: once as `field_<id>` and
        # again as `ref_<ref>`, doubling the payload.
        process = self.build().transform(
            self.RESPONSE, 'chk_1', self.FORM, kickoff_definitions()
        )
        assert len(process['prerun']) == 2, 'one entry per answered field'

    def test_values_are_typed_not_stringified(self):
        process = self.build().transform(
            self.RESPONSE, 'chk_1', self.FORM, kickoff_definitions()
        )
        # text stays a bare scalar; dropdown needs BOTH id and text.
        assert process['prerun'][TL_COMPANY] == 'Acme Corp'
        assert process['prerun'][TL_PLAN] == {'id': 2, 'text': 'Enterprise'}

    def test_missing_definitions_fail_loudly(self):
        # Launching without definitions returns 201 with the values discarded,
        # so silence here is silent data loss.
        with pytest.raises(ValueError):
            self.build().transform(self.RESPONSE, 'chk_1', self.FORM, None)

    def test_unmatched_answer_fails_loudly(self):
        response = {'response_id': 'r9', 'answers': [
            {'field': {'id': 'zzz', 'ref': 'r'}, 'type': 'text', 'text': 'x'},
        ]}
        form = {'fields': [{'id': 'zzz', 'title': 'Not On The Template'}]}
        with pytest.raises(UnresolvedFieldError):
            self.build().transform(response, 'chk_1', form, kickoff_definitions())


class TestSurveyMonkey:
    """SurveyMonkey answers must land under timeline_ids."""

    def build(self):
        module = load_vendor_module(
            'surveymonkey', 'transformers/instance_transformer.py', 'sm_it'
        )
        return module.InstanceTransformer()

    SURVEY = {'pages': [{'questions': [
        {'id': 'q1', 'headings': [{'heading': 'Company Name'}], 'family': 'open_ended'},
    ]}]}

    RESPONSE = {'id': 'resp1234', 'pages': [{'questions': [
        {'id': 'q1', 'answers': [{'text': 'Acme Corp'}]},
    ]}]}

    def test_keys_are_timeline_ids(self):
        process = self.build().transform(
            self.RESPONSE, 'chk_1', self.SURVEY, kickoff_definitions()
        )
        assert list(process['prerun']) == [TL_COMPANY]
        assert process['prerun'][TL_COMPANY] == 'Acme Corp'

    def test_question_id_never_appears_as_key(self):
        process = self.build().transform(
            self.RESPONSE, 'chk_1', self.SURVEY, kickoff_definitions()
        )
        for key in process['prerun']:
            assert not key.startswith('field_')
            assert 'q1' != key

    def test_missing_definitions_fail_loudly(self):
        with pytest.raises(ValueError):
            self.build().transform(self.RESPONSE, 'chk_1', self.SURVEY, None)


class TestKickoffFieldCache:
    """The cache turns an API checklist response into usable definitions."""

    class FakeClient:
        def __init__(self, payload):
            self.payload = payload
            self.calls = 0

        def get_checklist(self, checklist_id):
            self.calls += 1
            return self.payload

    def test_extracts_prerun_array(self):
        client = self.FakeClient({'id': 'chk_1', 'prerun': kickoff_definitions()})
        fields = KickoffFieldCache(client).get('chk_1')
        assert [f['id'] for f in fields] == [TL_COMPANY, TL_PLAN]

    def test_unwraps_data_envelope(self):
        client = self.FakeClient({'data': {'id': 'chk_1', 'prerun': kickoff_definitions()}})
        assert len(KickoffFieldCache(client).get('chk_1')) == 2

    def test_fetches_once_per_template(self):
        client = self.FakeClient({'prerun': kickoff_definitions()})
        cache = KickoffFieldCache(client)
        cache.get('chk_1')
        cache.get('chk_1')
        assert client.calls == 1

    def test_require_raises_when_template_has_no_kickoff_fields(self):
        # This is the common real-world case: the template was created without
        # its kick-off form, so there is nothing to key values against.
        client = self.FakeClient({'id': 'chk_1', 'prerun': []})
        with pytest.raises(NoKickoffFieldsDefined):
            KickoffFieldCache(client).require('chk_1')

    def test_falls_back_to_make_request(self):
        class MakeRequestClient:
            def __init__(self):
                self.endpoint = None

            def _make_request(self, method, endpoint, **kwargs):
                self.endpoint = (method, endpoint)
                return {'prerun': kickoff_definitions()}

        client = MakeRequestClient()
        assert len(KickoffFieldCache(client).get('chk_9')) == 2
        assert client.endpoint == ('GET', '/checklists/chk_9')

    def test_extract_handles_missing_prerun(self):
        assert extract_kickoff_fields({'id': 'chk'}) == []
        assert extract_kickoff_fields(None) == []


class TestStrictEncoding:
    """Strict mode converts silent server-side loss into a local failure."""

    def test_unresolved_key_raises(self):
        with pytest.raises(UnresolvedFieldError) as excinfo:
            build_prerun_payload(
                {'Company Name': 'Acme', 'Nope': 'x'},
                kickoff_definitions(),
                strict=True,
            )
        assert 'Nope' in str(excinfo.value)
        assert excinfo.value.unresolved == ['Nope']

    def test_no_definitions_raises(self):
        with pytest.raises(UnresolvedFieldError):
            build_prerun_payload({'Company Name': 'Acme'}, None, strict=True)

    def test_non_strict_still_drops_quietly(self):
        # Preserved for callers that genuinely want best-effort behaviour.
        payload = build_prerun_payload(
            {'Company Name': 'Acme', 'Nope': 'x'}, kickoff_definitions()
        )
        assert payload == {TL_COMPANY: 'Acme'}

    def test_table_column_mismatch_raises(self):
        # The API validates count($values) !== count($capture->columns) -> 422,
        # so a mismatch can never launch; fail where the field is known.
        captures = [{
            'id': TL_COMPANY, 'label': 'Items', 'field_type': 'table',
            'columns': [{'id': 'c1', 'name': 'Item'}, {'id': 'c2', 'name': 'Qty'}],
        }]
        with pytest.raises(TableShapeError):
            build_prerun_payload({'Items': ['a', 'b', 'c']}, captures, strict=True)

    def test_table_matching_column_count_passes(self):
        captures = [{
            'id': TL_COMPANY, 'label': 'Items', 'field_type': 'table',
            'columns': [{'id': 'c1', 'name': 'Item'}, {'id': 'c2', 'name': 'Qty'}],
        }]
        payload = build_prerun_payload({'Items': ['a', 'b']}, captures, strict=True)
        assert payload[TL_COMPANY] == ['a', 'b']


class TestRocketlaneCallShape:
    """transform_project must accept the arguments main.py actually passes."""

    def test_accepts_four_arguments(self):
        module = load_vendor_module(
            'rocketlane', 'transformers/instance_transformer.py', 'rl_it'
        )
        transformer = module.InstanceTransformer()
        project = {
            'id': 'p1', 'name': 'Onboard Acme', 'template_id': 't1',
            'custom_fields': {'Company Name': 'Acme Corp'},
        }
        # main.py previously called this with ONE argument, raising TypeError
        # before any prerun data could be produced.
        process = transformer.transform_project(
            project, {'t1': 'chk_1'}, {}, kickoff_definitions()
        )
        assert process['prerun'] == {TL_COMPANY: 'Acme Corp'}

    def test_custom_fields_without_definitions_fail_loudly(self):
        module = load_vendor_module(
            'rocketlane', 'transformers/instance_transformer.py', 'rl_it2'
        )
        transformer = module.InstanceTransformer()
        project = {'id': 'p1', 'name': 'X', 'template_id': 't1',
                   'custom_fields': {'Company Name': 'Acme'}}
        with pytest.raises(ValueError):
            transformer.transform_project(project, {'t1': 'chk_1'}, {}, None)


class TestKissflowClientResolvesPrerun:
    """Kissflow resolves at the client, the choke point every launch passes."""

    def build_client(self, prerun_fields):
        module = load_vendor_module('kissflow', 'api/tallyfy_client.py', 'kf_client')

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return self.payload

        class FakeSession:
            def __init__(self):
                self.headers = {}
                self.posted = []

            def mount(self, *a, **kw):
                pass

            def get(self, url, **kwargs):
                return FakeResponse({'id': 'chk_1', 'prerun': prerun_fields})

            def post(self, url, json=None, **kwargs):
                self.posted.append(json)
                return FakeResponse({'id': 'run_1'})

        client = module.TallyfyClient('token', 'org_1')
        client.session = FakeSession()
        return client

    def test_field_names_are_resolved_to_timeline_ids(self):
        client = self.build_client(kickoff_definitions())
        # Kissflow keys its values by field NAME.
        client.create_process('chk_1', 'Run 1', {'Company Name': 'Acme Corp'})
        sent = client.session.posted[0]
        assert sent['prerun'] == {TL_COMPANY: 'Acme Corp'}
        assert 'prerun_data' not in sent

    def test_template_without_kickoff_fields_fails_loudly(self):
        client = self.build_client([])
        with pytest.raises(NoKickoffFieldsDefined):
            client.create_process('chk_1', 'Run 1', {'Company Name': 'Acme Corp'})
