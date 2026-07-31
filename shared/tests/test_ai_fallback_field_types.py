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


def _load_ai_client(vendor):
    path = os.path.join(REPO_ROOT, vendor, 'src', 'api', 'ai_client.py')
    if not os.path.exists(path):
        pytest.skip(f'{vendor} has no ai_client.py')
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
