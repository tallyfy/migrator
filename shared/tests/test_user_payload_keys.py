"""
A user-create payload must carry the address under `email`.

THE RENAME, ONE MORE TIME
-------------------------
The same mass find-replace that produced `"text": 'text'` everywhere also hit
the user payloads, and this is the third distinct live instance found:

  kissflow/src/transformers/user_transformer.py
      set `text` to the email, then twenty lines later overwrote it with the
      phone number

  kissflow/src/transformers/user_transformer.py (preferences)
      keyed the email notification channel `text`, beside in_app/daily_digest

  pipefy/src/main.py
      built {"text": member.get('email'), ...} and handed it to
      `create_user`, which POSTs the dict VERBATIM (`json=user_data`) -- so
      the request carried no `email` key at all and every migrated user was
      created without an address

WHY IT SURVIVED
---------------
Nothing raises. `find_user_by_email(tallyfy_user["text"])` reads back the same
wrong key, so the lookup half works. And the client's success log is

    logger.info(f"Created user: {user_data.get('email', user_data.get('first_name', 'Unknown'))}")

which falls back to the first name -- so the migration printed
"Created user: Jane" and looked healthy.

THE WIRE KEY
------------
`email`. Every repaired client agrees: `create_member` builds
`{"email": email, 'firstname': .., 'lastname': .., 'role': ..}`, pipefy's own
`create_user` docstring says "including email, first_name, last_name, role",
and `find_user_by_email` compares `user.get('email')`.
"""

import ast
import glob
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ORCHESTRATORS = sorted(glob.glob(os.path.join(REPO_ROOT, '*', 'src', 'main.py')))
TRANSFORMERS = sorted(glob.glob(os.path.join(REPO_ROOT, '*', 'src', 'transformers', '*.py')))
IDS_ORCH = [os.path.relpath(p, REPO_ROOT) for p in ORCHESTRATORS]
IDS_TRANS = [os.path.relpath(p, REPO_ROOT) for p in TRANSFORMERS]


VERBATIM_CREATORS = {'create_user', 'create_member', 'create_guest'}


def _dicts_passed_verbatim(tree):
    """Names handed as the SOLE positional argument to a create_* call.

    This distinction is the whole gate. asana and kissflow also build a member
    dict keyed `text`, but they call

        create_member(email=tallyfy_member["text"], first_name=..., ...)

    -- discrete keyword arguments, so the dict never reaches the wire and
    `text` is just an internal name. pipefy and process-street instead call

        create_user(tallyfy_user)

    against `def create_user(self, user_data)` which does
    `self._make_request('POST', '/users', json=user_data)`. There the key IS
    the wire key, and `text` means the request carries no address.

    Flagging both shapes would have "fixed" asana and kissflow into breakage.
    """
    names = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in VERBATIM_CREATORS:
            continue
        if len(node.args) == 1 and isinstance(node.args[0], ast.Name) and not node.keywords:
            names.add(node.args[0].id)
    return names


def _emails_keyed_text(path, only_names=None):
    """`{'text': <an email>}` in a dict literal, optionally restricted to the
    dicts assigned to `only_names`."""
    tree = ast.parse(open(path).read())
    findings = []
    for node in ast.walk(tree):
        target_names = set()
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            target_names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            candidate = node.value
        elif isinstance(node, ast.Dict):
            candidate = node
        else:
            continue
        if only_names is not None and not (target_names & only_names):
            continue
        for key, value in zip(candidate.keys, candidate.values):
            if not (isinstance(key, ast.Constant) and key.value == 'text'):
                continue
            rendered = ast.dump(value)
            if 'email' in rendered.lower():
                findings.append(candidate.lineno)
    return sorted(set(findings))


class TestTheEmailIsNotKeyedText:

    @pytest.mark.parametrize('path', ORCHESTRATORS, ids=IDS_ORCH)
    def test_orchestrator_user_payloads_use_email(self, path):
        tree = ast.parse(open(path).read())
        offenders = _emails_keyed_text(path, _dicts_passed_verbatim(tree))
        assert not offenders, (
            f'{os.path.relpath(path, REPO_ROOT)} builds a payload keying an email '
            f'value under "text" at line(s) {offenders}. Clients POST these dicts '
            f'verbatim, so the request would carry no email key -- and the success '
            f'log falls back to the first name, so it prints "Created user: Jane" '
            f'and looks fine.'
        )

    @pytest.mark.parametrize('path', TRANSFORMERS, ids=IDS_TRANS)
    def test_transformer_output_matches_how_its_caller_sends_it(self, path):
        """A transformer whose dict is passed verbatim must use the wire key."""
        vendor = os.path.relpath(path, REPO_ROOT).split(os.sep)[0]
        main_path = os.path.join(REPO_ROOT, vendor, 'src', 'main.py')
        if not os.path.exists(main_path):
            pytest.skip(f'{vendor} has no orchestrator')

        main_tree = ast.parse(open(main_path).read())
        if not _dicts_passed_verbatim(main_tree):
            pytest.skip(f'{vendor} passes discrete kwargs, so `text` never reaches the wire')

        offenders = _emails_keyed_text(path)
        assert not offenders, (
            f'{os.path.relpath(path, REPO_ROOT)} keys an email value under "text" '
            f'at line(s) {offenders}, and {vendor}/src/main.py hands that dict '
            f'straight to a create call that POSTs it verbatim.'
        )

    def test_the_detector_separates_the_two_call_shapes(self):
        """Guard the guard. Flagging both shapes would break asana and kissflow."""
        verbatim = ast.parse(
            "payload = {'text': m.get('email')}\n"
            "client.create_user(payload)\n"
        )
        assert _dicts_passed_verbatim(verbatim) == {'payload'}

        discrete = ast.parse(
            "payload = {'text': m.get('email')}\n"
            "client.create_member(email=payload['text'], first_name='a')\n"
        )
        assert _dicts_passed_verbatim(discrete) == set(), (
            'a discrete-kwarg call must NOT be flagged -- the dict never '
            'reaches the wire'
        )
