"""
A method an orchestrator calls must exist on the class it holds.

WHAT A GHOST IS
---------------
`main.py` does `self.vendor_client = VendorClient(...)` and later calls
`self.vendor_client.list_forms()`. If `VendorClient` defines `get_forms` and
not `list_forms`, that is an `AttributeError` at runtime -- and nothing catches
it before then, because nothing imports a `main.py` (they are entry points),
`py_compile` only checks syntax, and pyflakes resolves names, not attributes.

WHY IT MATTERS MORE THAN IT LOOKS
---------------------------------
Most of these sit inside `except Exception` blocks, so the phase is skipped
and the migration reports success on zero work. Kissflow's app-template
migration is the clearest case: three consecutive ghost calls, all swallowed,
so it migrates nothing and says it worked.

Worse, in the eight-vendor copy-paste family the RECOVERY path is itself a
ghost -- the handler's first statement calls `error_handler.handle_critical_error`,
which does not exist -- so the second AttributeError replaces the first and the
true failure never reaches the log.

The same shape appeared in `shared/rollback_manager.py`, where the dispatch
dicts held bound methods (`self.tallyfy_client.delete_user`) rather than names.
A dict literal is built eagerly, so all four lookups ran before `.get()` chose
one, and none of those four methods exists on any of the 17 clients -- so every
rollback of every resource type failed on that line, and the guard below it was
unreachable. It now resolves lazily by name and raises NotImplementedError
naming the missing method.

THIS IS A RATCHET, NOT A CLEAN BILL OF HEALTH
---------------------------------------------
Fourteen ghosts had an unambiguous target -- a method on the same class with a
compatible signature -- and are fixed. The rest need a method that exists
nowhere in this repo, so fixing them means writing new API code against vendor
documentation, not renaming. Inventing those is what produced this mess.

They are listed below so the gate can assert two things:

  1. no NEW ghost is ever introduced, and
  2. the list cannot rot -- if a listed ghost gets fixed, the gate FAILS until
     the entry is deleted, so the inventory can never overstate the problem.

Tracked on issue #6.
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

# (vendor, class the attribute holds, method called that does not exist).
# Every entry needs a method written from vendor API docs -- none is a rename.
KNOWN_MISSING = [
    ('basecamp', 'CheckpointManager', 'get_last_completed_phase'),
    ('basecamp', 'CheckpointManager', 'save_phase_checkpoint'),
    ('basecamp', 'ErrorHandler', 'handle_critical_error'),
    ('bpmn', 'Validator', 'validate_migration'),
    ('clickup', 'CheckpointManager', 'get_last_completed_phase'),
    ('clickup', 'CheckpointManager', 'save_phase_checkpoint'),
    ('clickup', 'ClickUpClient', 'get_views'),
    ('clickup', 'ErrorHandler', 'handle_critical_error'),
    ('cognito-forms', 'CheckpointManager', 'get_last_completed_phase'),
    ('cognito-forms', 'CheckpointManager', 'save_phase_checkpoint'),
    ('cognito-forms', 'ErrorHandler', 'handle_critical_error'),
    ('google-forms', 'CheckpointManager', 'get_last_completed_phase'),
    ('google-forms', 'CheckpointManager', 'save_phase_checkpoint'),
    ('google-forms', 'ErrorHandler', 'handle_critical_error'),
    ('google-forms', 'GoogleFormsClient', 'list_responses'),
    ('jotform', 'CheckpointManager', 'get_last_completed_phase'),
    ('jotform', 'CheckpointManager', 'save_phase_checkpoint'),
    ('jotform', 'ErrorHandler', 'handle_critical_error'),
    ('jotform', 'JotformClient', 'get_users'),
    ('kissflow', 'KissflowClient', 'get_app_forms'),
    ('kissflow', 'KissflowClient', 'get_app_views'),
    ('kissflow', 'KissflowClient', 'get_app_workflows'),
    ('kissflow', 'KissflowClient', 'get_board_cards'),
    ('monday', 'MondayClient', 'get_board'),
    ('monday', 'MondayClient', 'get_items'),
    ('monday', 'MondayClient', 'get_workspace'),
    ('monday', 'TallyfyClient', 'batch_create_processes'),
    ('monday', 'TallyfyClient', 'get_users'),
    ('nextmatter', 'CheckpointManager', 'get_last_completed_phase'),
    ('nextmatter', 'CheckpointManager', 'save_phase_checkpoint'),
    ('nextmatter', 'ErrorHandler', 'handle_critical_error'),
    ('pipefy', 'PipefyClient', 'list_automations'),
    ('pipefy', 'TallyfyClient', 'upload_attachment'),
    ('process-street', 'FormTransformer', 'get_statistics'),
    ('process-street', 'TemplateTransformer', 'get_statistics'),
    ('process-street', 'UserTransformer', 'convert_datetime'),
    ('process-street', 'UserTransformer', 'get_statistics'),
    ('rocketlane', 'AIClient', 'assess_form_complexity'),
    ('rocketlane', 'AIClient', 'test_connection'),
    ('rocketlane', 'CheckpointManager', 'get_all_mappings'),
    ('rocketlane', 'CheckpointManager', 'get_mapping_summary'),
    ('rocketlane', 'CheckpointManager', 'load_checkpoint'),
    ('rocketlane', 'ErrorHandler', 'get_error_count'),
    ('rocketlane', 'ErrorHandler', 'handle_error'),
    ('rocketlane', 'InstanceTransformer', 'transform_time_entry_to_comment'),
    ('rocketlane', 'RocketLaneClient', 'get_project_template'),
    ('rocketlane', 'TallyfyClient', 'create_comment'),
    ('rocketlane', 'TallyfyClient', 'create_kickoff_form'),
    ('rocketlane', 'TallyfyClient', 'create_organization'),
    ('rocketlane', 'TallyfyClient', 'test_connection'),
    ('rocketlane', 'TemplateTransformer', 'transform_complex_form_to_workflow'),
    ('rocketlane', 'TemplateTransformer', 'transform_simple_form'),
    ('rocketlane', 'UserTransformer', 'transform_customer_to_guest'),
    ('rocketlane', 'UserTransformer', 'transform_customer_to_organization'),
    ('rocketlane', 'UserTransformer', 'transform_user'),
    ('trello', 'CheckpointManager', 'get_last_completed_phase'),
    ('trello', 'CheckpointManager', 'save_phase_checkpoint'),
    ('trello', 'ErrorHandler', 'handle_critical_error'),
    ('trello', 'TrelloClient', 'get_users'),
    ('wrike', 'CheckpointManager', 'get_last_completed_phase'),
    ('wrike', 'CheckpointManager', 'save_phase_checkpoint'),
    ('wrike', 'ErrorHandler', 'handle_critical_error'),
]


def _methods_of(path, class_name):
    if not os.path.exists(path):
        return None
    for node in ast.walk(ast.parse(open(path).read())):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {m.name for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return None


def _class_methods(vendor):
    """Resolve each class through main.py's imports where possible.

    A plain scan unions same-named classes, and process-street defines
    ProcessStreetClient twice with different method sets -- so a union would
    report a method as present because the OTHER, unimported copy has it, and
    a real ghost would go missing. (The sibling constructor gate hit the
    mirror-image of this: it picked one copy by glob order and invented a bug
    that did not exist, passing locally and failing on CI.)
    """
    main_path = os.path.join(REPO_ROOT, vendor, 'src', 'main.py')
    tree = ast.parse(open(main_path).read())

    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = [p for p in node.module.split('.') if p and p != 'src']
            module_path = os.path.join(REPO_ROOT, vendor, 'src', *parts) + '.py'
            for alias in node.names:
                imported[alias.asname or alias.name] = module_path

    methods = {}
    for name, module_path in imported.items():
        found = _methods_of(module_path, name)
        if found is not None:
            methods[name] = found

    # Anything not imported by name (defined in main.py, or star-imported)
    # falls back to a scan, deterministically ordered.
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, vendor, 'src', '**', '*.py'), recursive=True)):
        for node in ast.walk(ast.parse(open(path).read())):
            if isinstance(node, ast.ClassDef) and node.name not in methods:
                methods.setdefault(node.name, set()).update(
                    m.name for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
    return methods


def _ghosts(vendor):
    """Every self.<attr>.<method>() where <attr> holds a class we can resolve."""
    defined = _class_methods(vendor)
    tree = ast.parse(open(os.path.join(REPO_ROOT, vendor, 'src', 'main.py')).read())

    attr_to_class = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
                and isinstance(node.value.func, ast.Name):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) \
                        and target.value.id == 'self':
                    attr_to_class[target.attr] = node.value.func.id
                elif isinstance(target, ast.Name):
                    attr_to_class[target.id] = node.value.func.id

    # Second pass: `self.tallyfy = tallyfy_client`, where the local was built
    # elsewhere in the file (typically in main(), then handed to the
    # orchestrator's __init__). Without this the whole attribute is invisible
    # -- monday assigns every one of its clients this way, so it had zero
    # entries here while calling a create_user() that does not exist.
    for _ in range(3):  # resolve short chains, e.g. a = b; self.c = a
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)):
                continue
            source_class = attr_to_class.get(node.value.id)
            if source_class is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) \
                        and target.value.id == 'self':
                    attr_to_class.setdefault(target.attr, source_class)
                elif isinstance(target, ast.Name):
                    attr_to_class.setdefault(target.id, source_class)

    found = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        base = node.func.value
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name) \
                and base.value.id == 'self':
            key = base.attr
        elif isinstance(base, ast.Name):
            key = base.id
        else:
            continue
        cls = attr_to_class.get(key)
        if cls is None or cls not in defined:
            continue  # class defined outside this vendor's src/; not resolvable here
        if node.func.attr in defined[cls]:
            continue
        found.setdefault((vendor, cls, node.func.attr), []).append(node.lineno)
    return found


class TestNoNewGhostMethods:

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_no_unlisted_ghost_method(self, vendor):
        known = {k for k in KNOWN_MISSING if k[0] == vendor}
        new = {k: lines for k, lines in _ghosts(vendor).items() if k not in known}
        assert not new, (
            f'{vendor} calls a method that does not exist on the class it holds. '
            f'This is an AttributeError at runtime, and most of these sit inside '
            f'`except Exception` so the phase is silently skipped and the '
            f'migration still reports success:\n  ' +
            '\n  '.join(f'main.py:{lines} {c}.{m}()' for (_, c, m), lines in sorted(new.items()))
        )

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_the_inventory_does_not_rot(self, vendor):
        """A fixed ghost must leave the list, or the list overstates the problem."""
        actual = set(_ghosts(vendor))
        stale = [k for k in KNOWN_MISSING if k[0] == vendor and k not in actual]
        assert not stale, (
            f'{vendor}: these are listed in KNOWN_MISSING but now resolve. '
            f'Delete them from the list: {stale}'
        )


class TestRollbackDispatchResolvesLazily:
    """The eager-dict bug, pinned at the source.

    `{ResourceType.USER: self.tallyfy_client.delete_user, ...}` evaluates every
    attribute before `.get()` picks one, so one missing method breaks every
    resource type -- and makes the `if not method` guard below unreachable.
    """

    def test_dispatch_dicts_hold_names_not_bound_methods(self):
        path = os.path.join(REPO_ROOT, 'shared', 'rollback_manager.py')
        tree = ast.parse(open(path).read())

        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for value in node.values:
                if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Attribute) \
                        and isinstance(value.value.value, ast.Name) and value.value.value.id == 'self':
                    offenders.append(f'line {node.lineno}: self.{value.value.attr}.{value.attr}')

        assert not offenders, (
            'A dict literal is built eagerly, so these attribute lookups all run '
            'before the dict is indexed -- one missing method breaks every case: '
            f'{offenders}'
        )

    def test_a_client_missing_the_method_gets_a_named_error(self):
        source = open(os.path.join(REPO_ROOT, 'shared', 'rollback_manager.py')).read()
        assert 'NotImplementedError' in source, (
            'A client that cannot delete should say which method is missing, '
            'not raise a bare AttributeError from a dict literal.'
        )
