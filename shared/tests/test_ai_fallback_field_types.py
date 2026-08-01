"""
Contract test for the AI field-mapping fallback.

WHY THIS FILE EXISTS
--------------------
`AIClient._fallback_field_mapping` is the deterministic path taken whenever no
Anthropic key is configured -- which is the default, and therefore the path most
migrations actually run. It decides which Tallyfy field type a source field
becomes.

The same mass find-replace that broke the user transformers reached this
function too, and it survived in thirteen byte-identical copies:

    elif "text" in field_type or 'link' in field_name:
        tallyfy_type = 'link'          # branch keyed on "text", body returns a link
        validation = "text"
    elif "text" in field_type:         # PROVABLY UNREACHABLE
        tallyfy_type = "text"

Two defects in one place. The first branch subsumes the second, so every field
type containing "text" -- the single most common type in every vendor -- was
typed as `link`. And `link` is not a Tallyfy field type at all, nor were the
`member` and `tag` the neighbouring branches returned.

None of that needed the original source tokens to diagnose or to fix. The output
side is hard ground truth: `Capture::$field_types` is a closed set, mirrored in
this repo as `shared.capture_shapes.CAPTURE_FIELD_TYPES`, and the canonical
mapping for a type with no Tallyfy equivalent is in `_FIELD_TYPE_ALIASES`
('member' -> 'assignees_form', 'url' -> 'text').

So this test asserts the property, not the history: whatever the branches are
keyed on, the value they produce must be a field type the API will accept.
"""

import importlib.util
import os
import sys
import types

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.capture_shapes import CAPTURE_FIELD_TYPES

# Every vendor carrying this AIClient. bpmn, pipefy, process-street and
# surveymonkey have their own divergent copies and are covered by the same
# property test where they define the method.
VENDORS = [
    'asana', 'basecamp', 'bpmn', 'clickup', 'cognito-forms', 'google-forms',
    'jotform', 'kissflow', 'monday', 'nextmatter', 'pipefy', 'process-street',
    'rocketlane', 'surveymonkey', 'trello', 'typeform', 'wrike',
]

# Deliberately wide: every branch of the fallback, plus inputs that hit the
# sample-values and default arms.
CONTEXTS = [
    {'field_type': 'text'},
    {'field_type': 'short_text'},
    {'field_type': 'long_text'},
    {'field_type': 'url'},
    {'field_type': 'date'},
    {'field_type': 'priority'},
    {'field_type': 'number'},
    {'field_type': ''},
    {'field_name': 'customer name'},
    {'field_name': 'client'},
    {'field_name': 'resource'},
    {'field_name': 'skill'},
    {'field_name': 'budget'},
    {'field_name': 'cost'},
    {'field_name': 'deadline'},
    {'field_name': 'link'},
    {'field_name': 'website link', 'field_type': 'text'},
    {'sample_values': ['x' * 200]},
    {},
]


def _stub_anthropic_if_absent():
    """Let this run without the Anthropic SDK installed.

    Every `ai_client.py` imports `anthropic` at module level, but the function
    under test is pure branching logic that never touches the SDK -- and it is
    specifically the path taken when no API key is configured. Requiring the
    real package would mean this gate only runs where someone happens to have
    it installed, which is exactly how the defect survived: it lived in the
    no-key fallback that nothing exercised.
    """
    if 'anthropic' in sys.modules:
        return
    try:
        import anthropic  # noqa: F401
    except ImportError:
        stub = types.ModuleType('anthropic')
        stub.Anthropic = object
        stub.APIError = Exception
        sys.modules['anthropic'] = stub


def _load_ai_client(vendor):
    path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'ai_client.py')
    if not os.path.exists(path):
        pytest.skip(f'{vendor} has no ai_client.py')
    _stub_anthropic_if_absent()
    module_name = f'_ai_client_{vendor.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.AIClient


class TestFallbackOnlyEmitsRealTallyfyFieldTypes:

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_every_branch_returns_an_accepted_field_type(self, vendor):
        client_cls = _load_ai_client(vendor)
        if not hasattr(client_cls, '_fallback_field_mapping'):
            pytest.skip(f'{vendor} has no _fallback_field_mapping')
        # Bypass __init__: it reads env and may construct an Anthropic client.
        client = client_cls.__new__(client_cls)

        for context in CONTEXTS:
            result = client_cls._fallback_field_mapping(client, context)
            field_type = result['tallyfy_type']
            assert field_type in CAPTURE_FIELD_TYPES, (
                f'{vendor} maps {context} to {field_type!r}, which is not a '
                f'Tallyfy field type. CreateCaptureRequest rejects it with a '
                f'422. Accepted: {sorted(CAPTURE_FIELD_TYPES)}'
            )

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_a_text_field_is_not_swallowed_by_the_link_branch(self, vendor):
        """Regression: the link branch was keyed on "text" and shadowed this.

        `text` is the most common field type in every vendor, so this single
        misplaced branch mis-typed the bulk of every migration's fields.
        """
        client_cls = _load_ai_client(vendor)
        if not hasattr(client_cls, '_fallback_field_mapping'):
            pytest.skip(f'{vendor} has no _fallback_field_mapping')
        client = client_cls.__new__(client_cls)

        result = client_cls._fallback_field_mapping(client, {'field_type': 'text'})
        assert result['tallyfy_type'] == 'text', (
            f'{vendor} maps a plain text field to '
            f'{result["tallyfy_type"]!r} instead of text'
        )

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_no_branch_is_shadowed_by_an_identical_earlier_condition(self, vendor):
        """An unreachable `elif` is dead logic that reads as live coverage."""
        import ast

        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'ai_client.py')
        if not os.path.exists(path):
            pytest.skip(f'{vendor} has no ai_client.py')
        tree = ast.parse(open(path).read())

        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            seen = []
            current = node
            while isinstance(current, ast.If):
                test = ast.dump(current.test)
                # A bare repeat of an earlier condition can never fire. An
                # earlier OR-clause containing this exact test shadows it too.
                for earlier in seen:
                    assert test != earlier, (
                        f'{vendor}: unreachable branch at line {current.lineno} '
                        f'-- an identical condition appears earlier in the chain'
                    )
                    if isinstance(current.test, ast.Compare):
                        assert ast.dump(current.test) not in earlier, (
                            f'{vendor}: shadowed branch at line {current.lineno} '
                            f'-- an earlier OR-clause already covers this condition'
                        )
                seen.append(test)
                current = current.orelse[0] if (
                    len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If)
                ) else None

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_membership_lists_carry_no_duplicate_entries(self, vendor):
        """`x not in ["text", "text", 'date']` lost a distinct third value."""
        import ast

        path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'ai_client.py')
        if not os.path.exists(path):
            pytest.skip(f'{vendor} has no ai_client.py')
        tree = ast.parse(open(path).read())

        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                continue
            constants = [
                element.value for element in node.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if len(constants) < 2:
                continue
            assert len(constants) == len(set(constants)), (
                f'{vendor}: duplicate entry in the literal at line {node.lineno} '
                f'({constants}) -- a distinct value was overwritten'
            )


class TestNoUnreachableBranchAnywhereInVendorSource:
    """The same defect appeared far outside `ai_client.py`.

    Scoping the shadowing check to one file was a mistake. The identical
    corruption -- several consecutive branches collapsed onto the same literal,
    so only the first can ever run -- was also sitting in:

      process-street/src/transformers/form_transformer.py
          four consecutive `elif field_type == "text"`, whose bodies set
          email_format, url_format, phone_format and min/max. Every validated
          Process Street field got email_format, and the url, phone and numeric
          rules were dead.

      kissflow/src/transformers/process_transformer.py
          `elif step_type == "text"` emitting "text" as a Tallyfy STEP type
          (the set is task/approval/expiring/email), which left
          `_create_email_template` unreachable.

    In every case the branch BODY identifies what the condition must have been,
    so this is a mechanical check, not a judgement call.
    """

    @staticmethod
    def _shadowed_branches(path):
        import ast

        findings = []
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            seen = []
            current = node
            while isinstance(current, ast.If):
                dumped = ast.dump(current.test)
                if dumped in seen:
                    findings.append(current.lineno)
                seen.append(dumped)
                current = current.orelse[0] if (
                    len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If)
                ) else None
        return findings

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_no_vendor_source_file_has_a_shadowed_branch(self, vendor):
        import glob

        vendor_root = os.path.join(REPO_ROOT, vendor, 'src')
        if not os.path.isdir(vendor_root):
            pytest.skip(f'{vendor} has no src/')

        offenders = {}
        for path in glob.glob(os.path.join(vendor_root, '**', '*.py'), recursive=True):
            lines = self._shadowed_branches(path)
            if lines:
                offenders[os.path.relpath(path, REPO_ROOT)] = lines

        assert not offenders, (
            f'{vendor} has branches that can never execute -- an earlier branch '
            f'in the same chain tests exactly the same thing: {offenders}'
        )


class TestNoCollapsedMembershipTests:
    """`x in [...]` hides the same corruption, and the AST gates above miss it.

    Two shapes, both found in kissflow's field transformer after the earlier
    gates passed clean:

        if field_type in ["text", "textarea", 'rich_text', "text", "text", "text"]:
            return str(value)
        elif field_type in ["text", 'currency', 'rating', 'slider']:
            return float(value)

    Three distinct source types collapsed into the first list, and the second
    branch could never run for "text" because the first already matched it --
    so numeric values were stringified instead of coerced.
    """

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_no_membership_literal_repeats_a_value(self, vendor):
        import ast
        import glob

        vendor_root = os.path.join(REPO_ROOT, vendor, 'src')
        if not os.path.isdir(vendor_root):
            pytest.skip(f'{vendor} has no src/')

        offenders = {}
        for path in glob.glob(os.path.join(vendor_root, '**', '*.py'), recursive=True):
            tree = ast.parse(open(path).read())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                    continue
                # An empty-string pair (`['', '']`) is a legitimate default
                # for a name split, not a collapsed literal.
                values = [
                    e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value
                ]
                if len(values) > 1 and len(values) != len(set(values)):
                    offenders.setdefault(os.path.relpath(path, REPO_ROOT), []).append(node.lineno)

        assert not offenders, (
            f'{vendor} repeats a value inside a literal, so a distinct entry was '
            f'overwritten: {offenders}'
        )
