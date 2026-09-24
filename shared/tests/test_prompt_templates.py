"""
Gate: every prompt template an AI client loads exists and fills (issue #23).

WHY THIS FILE EXISTS
--------------------
Each vendor's `src/api/ai_client.py` loads its prompt from `src/prompts/<name>.txt`
and fills it with `str.format(**context)`. Any failure along that path is caught
and turned into the deterministic fallback, so a broken template is invisible: the
migration runs, and the AI step never reaches the model.

Three versions of that were live at once:

- eleven vendors shipped a client whose templates did not exist (their clients
  were removed in #23, because nothing called them);
- surveymonkey's migration code loaded two templates that did not exist;
- 11 of the 17 templates on disk had unescaped JSON braces, so `str.format`
  raised before any call.

WHAT COUNTS AS A LOAD
---------------------
A call whose first argument is a literal `*.txt` name, made on any method the
vendor's AI client defines (`make_decision`, `batch_decisions`, `_load_prompt`,
or one added later), anywhere in that vendor's `src/` tree. Vendors, methods,
calls and templates are all discovered from the tree, never listed. bpmn builds
its prompts in code, so a name with an in-code default (a dict key in the client
whose value is the prompt text) counts as present.

The fallback maps name templates too, but they are dispatch keys for the no-AI
path, not loads, so they are not checked here.
"""

import ast
import glob
import os
import random
import string

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _clients(root):
    return sorted(glob.glob(os.path.join(root, '*', 'src', 'api', 'ai_client.py')))


def _vendor(client_path, root):
    return os.path.relpath(client_path, root).split(os.sep)[0]


def _client_methods_and_defaults(client_path):
    """The method names the client defines, and the template names it has in-code text for."""
    tree = ast.parse(open(client_path).read())
    methods, defaults = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods.update(item.name for item in node.body
                           if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)))
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and key.value.endswith('.txt')
                        and isinstance(value, (ast.Constant, ast.JoinedStr))
                        and not (isinstance(value, ast.Constant) and not isinstance(value.value, str))):
                    defaults.add(key.value)
    return methods, defaults


def _context_keys(call, func):
    """The keys of the context dict passed to a load, or None if they cannot be read statically."""
    arg = call.args[1] if len(call.args) > 1 else next(
        (kw.value for kw in call.keywords if kw.arg == 'context'), None)
    if isinstance(arg, ast.Name) and func is not None:
        bound = [node.value for node in ast.walk(func)
                 if isinstance(node, ast.Assign) and node.lineno < call.lineno
                 and any(isinstance(t, ast.Name) and t.id == arg.id for t in node.targets)]
        arg = bound[-1] if bound else None
    if isinstance(arg, ast.Dict) and all(isinstance(k, ast.Constant) for k in arg.keys):
        return {k.value for k in arg.keys}
    return None


def find_loads(root):
    """Every template load in every vendor that ships an AI client."""
    loads = []
    for client_path in _clients(root):
        vendor = _vendor(client_path, root)
        methods, defaults = _client_methods_and_defaults(client_path)
        src = os.path.join(root, vendor, 'src')
        for path in sorted(glob.glob(os.path.join(src, '**', '*.py'), recursive=True)):
            tree = ast.parse(open(path).read())
            parents = {}
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    parents[child] = node
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                        and node.args[0].value.endswith('.txt')):
                    continue
                name = (node.func.attr if isinstance(node.func, ast.Attribute)
                        else getattr(node.func, 'id', None))
                if name not in methods:
                    continue
                func = parents.get(node)
                while func is not None and not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func = parents.get(func)
                loads.append({
                    'vendor': vendor,
                    'template': node.args[0].value,
                    'where': f'{os.path.relpath(path, root)}:{node.lineno}',
                    'file': os.path.join(src, 'prompts', node.args[0].value),
                    'in_code_default': node.args[0].value in defaults,
                    'context_keys': _context_keys(node, func),
                })
    return loads


def template_problem(text):
    """Why str.format cannot fill this template, or None if it can."""
    try:
        fields = [f for _, f, _, _ in string.Formatter().parse(text) if f is not None]
    except ValueError as error:
        return f'str.format cannot parse it: {error}'
    bad = [f for f in fields if not f.isidentifier()]
    if bad:
        return f'unescaped braces make these placeholders: {bad}'
    return None


def placeholders(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f is not None}


LOADS = find_loads(REPO_ROOT)
TEMPLATES = sorted(glob.glob(os.path.join(REPO_ROOT, '*', 'src', 'prompts', '*.txt')))


def _id(load):
    return f"{load['vendor']}:{load['template']}@{load['where'].split(':')[-1]}"


def test_discovery_is_not_empty():
    # A sweep that discovers nothing passes every assertion made about it.
    assert len(_clients(REPO_ROOT)) >= 6, 'found fewer than 6 ai_client.py files'
    assert len(LOADS) >= 10, f'found only {len(LOADS)} template loads'
    assert len(TEMPLATES) >= 20, f'found only {len(TEMPLATES)} template files'
    checked = [load for load in LOADS if load['context_keys'] is not None]
    assert len(checked) >= 5, f'only {len(checked)} loads have a readable context'


@pytest.mark.parametrize('load', LOADS, ids=_id)
def test_every_loaded_template_exists(load):
    assert load['in_code_default'] or os.path.isfile(load['file']), (
        f"{load['where']} loads {load['template']!r}, which is not in "
        f"{os.path.relpath(os.path.dirname(load['file']), REPO_ROOT)}/. make_decision "
        f"would fall back on every call."
    )


@pytest.mark.parametrize('path', TEMPLATES, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_every_template_fills_with_str_format(path):
    text = open(path).read()
    problem = template_problem(text)
    assert problem is None, f'{os.path.relpath(path, REPO_ROOT)}: {problem}. Double any literal brace.'
    text.format(**{name: 'x' for name in placeholders(text)})


@pytest.mark.parametrize('load', [load for load in LOADS if load['context_keys'] is not None
                                  and os.path.isfile(load['file'])], ids=_id)
def test_the_call_site_supplies_every_placeholder(load):
    missing = placeholders(open(load['file']).read()) - load['context_keys']
    assert not missing, (
        f"{load['where']} passes no {sorted(missing)} for {load['template']!r}, so "
        f"str.format raises KeyError and the call falls back."
    )


def test_the_gate_catches_each_failure_on_a_planted_tree(tmp_path):
    """The finders above, run on a tree built to fail, must report each planted fault."""
    absent = f'absent_{random.randrange(10**6)}.txt'
    client_dir = tmp_path / 'probe' / 'src' / 'api'
    client_dir.mkdir(parents=True)
    (client_dir / 'ai_client.py').write_text(
        "class AIClient:\n"
        "    def make_decision(self, prompt_file, context):\n"
        "        return {}\n"
        "    def other(self):\n"
        "        return self.make_decision('from_client.txt', {'a': 1})\n"
    )
    transformers = tmp_path / 'probe' / 'src' / 'transformers'
    transformers.mkdir()
    (transformers / 't.py').write_text(
        "def run(ai_client):\n"
        "    context = {'a': 1}\n"
        f"    ai_client.make_decision('{absent}', context)\n"
        "    ai_client.make_decision('needs_b.txt', {'a': 1})\n"
        "    open('not_a_template.txt')\n"
    )
    prompts = tmp_path / 'probe' / 'src' / 'prompts'
    prompts.mkdir()
    (prompts / 'from_client.txt').write_text('Use {a}.\nRespond with JSON: {"k": 1}\n')
    (prompts / 'needs_b.txt').write_text('Use {a} and {b}.\nRespond with JSON: {{"k": 1}}\n')

    loads = {load['template']: load for load in find_loads(str(tmp_path))}
    assert set(loads) == {absent, 'from_client.txt', 'needs_b.txt'}, sorted(loads)
    assert not os.path.isfile(loads[absent]['file']) and not loads[absent]['in_code_default']
    assert os.path.isfile(loads['from_client.txt']['file'])
    assert loads[absent]['context_keys'] == {'a'}, 'a context bound to a name must be read'
    assert template_problem((prompts / 'from_client.txt').read_text()) is not None
    assert template_problem((prompts / 'needs_b.txt').read_text()) is None
    assert placeholders((prompts / 'needs_b.txt').read_text()) - loads['needs_b.txt']['context_keys'] == {'b'}
