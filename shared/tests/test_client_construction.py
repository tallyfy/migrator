"""
Every `SomethingClient(...)` an orchestrator writes must actually bind.

WHY
---
`_initialize_components()` is called unguarded from `__init__`, so a
constructor that cannot bind raises `TypeError` before phase 1 runs. Thirteen
call sites across eleven vendors could not bind. Four shapes:

    TallyfyClient()                      6 vendors, against
        __init__(self, api_key: str, organization: str, base_url=...)
        -- two required arguments, none supplied

    api_url=os.getenv(...)               3 vendors, parameter is `base_url`

    organization_id=...                  typeform, parameter is `organization`

    api_key=/organization=               monday, whose own client takes
                                         api_token=/organization_id=

Plus `TrelloClient()` (needs api_key + api_token) and `GoogleFormsClient()`
(needs credentials_path).

None of this could be caught by the existing gates. Nothing imports these
`main.py` files -- they are entry points -- so no test ever executed the line,
and `py_compile` and pyflakes both pass happily: the call is syntactically
fine and every name in it is defined. It is only wrong at bind time.

An `api_url` variant deserves a specific note. The client stores
`self.base_url = base_url.rstrip('/')` and then builds
`f"{self.base_url}/api/users"`, so it appends `/api` itself. Those three call
sites also passed a default of `https://api.tallyfy.com/api`, which would have
produced `/api/api/...` had the keyword been right. The signature's own
default is the bare root, which is the value now passed.

HOW
---
Static bind: parse the call in `main.py`, parse the matching `__init__` in
that vendor's `src/api/`, and check the arguments against the parameters.
Static rather than runtime because importing a vendor `main.py` pulls in
`anthropic`, `google.oauth2` and friends.
"""

import ast
import glob
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VENDORS = sorted(
    os.path.basename(os.path.dirname(os.path.dirname(p)))
    for p in glob.glob(os.path.join(REPO_ROOT, '*', 'src', 'main.py'))
)


def _signature(fn):
    args = fn.args
    positional = [a.arg for a in args.posonlyargs + args.args if a.arg != 'self']
    keyword_only = [a.arg for a in args.kwonlyargs]
    n_defaults = len(args.defaults)
    required = positional[:len(positional) - n_defaults] if n_defaults else list(positional)
    required += [
        a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is None
    ]
    return positional, keyword_only, required, args.vararg is not None, args.kwarg is not None


def _imported_from(vendor, class_name):
    """Which module does main.py actually import this class from?

    This has to be import-aware, and the reason is concrete: process-street
    defines ProcessStreetClient TWICE --

        src/api/ps_client.py             __init__(api_key, base_url, organization_id)
        src/api/process_street_client.py __init__(api_key, base_url)

    -- and main.py imports the first. An earlier version of this gate scanned
    src/api/*.py with glob and took whichever matched first. glob order is
    filesystem-dependent, so it resolved to ps_client.py on macOS and to
    process_street_client.py on CI, and reported a bug that does not exist.
    A gate whose verdict depends on directory ordering is worse than no gate.
    """
    main_path = os.path.join(REPO_ROOT, vendor, 'src', 'main.py')
    tree = ast.parse(open(main_path).read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if not any(a.name == class_name for a in node.names):
            continue
        # `api.ps_client`, `src.api.ps_client` and `.api.ps_client` all mean
        # <vendor>/src/api/ps_client.py.
        parts = [p for p in node.module.split('.') if p and p != 'src']
        return os.path.join(REPO_ROOT, vendor, 'src', *parts) + '.py'
    return None


def _find_init(vendor, class_name):
    path = _imported_from(vendor, class_name)
    candidates = [path] if path and os.path.exists(path) else []
    if not candidates:
        # Not imported by name (defined in main.py itself, or a star import).
        candidates = sorted(glob.glob(os.path.join(REPO_ROOT, vendor, 'src', '**', '*.py'), recursive=True))

    for candidate in candidates:
        tree = ast.parse(open(candidate).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        return item, os.path.relpath(candidate, REPO_ROOT)
    return None, None


def _bind_failures(vendor):
    main_path = os.path.join(REPO_ROOT, vendor, 'src', 'main.py')
    tree = ast.parse(open(main_path).read())
    failures = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id.endswith('Client')):
            continue

        class_name = node.func.id
        init, defined_in = _find_init(vendor, class_name)
        if init is None:
            continue  # class lives outside src/api/ (e.g. AIClient); not this gate's job

        positional, keyword_only, required, has_varargs, has_kwargs = _signature(init)
        given_positional = len(node.args)
        given_keywords = {k.arg for k in node.keywords if k.arg is not None}
        splatted = any(k.arg is None for k in node.keywords)  # **kwargs at the call site

        problems = []
        if not has_kwargs:
            for name in sorted(given_keywords):
                if name not in positional and name not in keyword_only:
                    problems.append(f'unexpected keyword {name!r}')
        if not (has_varargs or splatted):
            bound = set(positional[:given_positional]) | given_keywords
            for name in required:
                if name not in bound:
                    problems.append(f'missing required {name!r}')

        if problems:
            failures.append(
                f'{vendor}/src/main.py:{node.lineno} {class_name}(...) '
                f'-- {"; ".join(problems)} '
                f'(defined in {defined_in}: {class_name}({", ".join(positional)}))'
            )
    return failures


class TestEveryClientConstructionBinds:

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_client_constructors_bind(self, vendor):
        failures = _bind_failures(vendor)
        assert not failures, (
            'These raise TypeError before phase 1 runs -- _initialize_components() '
            'is called unguarded from __init__:\n  ' + '\n  '.join(failures)
        )

    def test_the_checker_detects_a_real_arity_error(self):
        """Guard the guard: a gate that never fires is worse than none."""
        source = 'class C:\n    def __init__(self, a, b=1):\n        pass\n'
        tree = ast.parse(source)
        init = tree.body[0].body[0]
        positional, keyword_only, required, _, _ = _signature(init)
        assert positional == ['a', 'b']
        assert required == ['a'], 'a parameter with a default must not count as required'


class TestTheResolverFollowsImportsNotGlobOrder:
    """process-street defines ProcessStreetClient twice, with DIFFERENT
    signatures. Resolving by scan order made this gate's verdict depend on
    the filesystem: it passed on macOS and failed on CI, on identical code."""

    def test_both_definitions_still_exist(self):
        a = os.path.join(REPO_ROOT, 'process-street', 'src', 'api', 'ps_client.py')
        b = os.path.join(REPO_ROOT, 'process-street', 'src', 'api', 'process_street_client.py')
        assert 'class ProcessStreetClient' in open(a).read()
        assert 'class ProcessStreetClient' in open(b).read()

    def test_the_resolver_picks_the_imported_one(self):
        _, defined_in = _find_init('process-street', 'ProcessStreetClient')
        assert defined_in == 'process-street/src/api/ps_client.py', (
            f'main.py does `from api.ps_client import ProcessStreetClient`, but '
            f'the resolver chose {defined_in}. Only ps_client.py takes '
            f'organization_id, so picking the other one invents a bug.'
        )
