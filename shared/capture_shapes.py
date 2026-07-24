"""
Normalise migrator field definitions into Tallyfy's capture ("form field") shape.

This module covers field **creation** (the definition), which is a different
contract from field **values** -- those live in ``prerun_encoder`` (kick-off
payloads) and ``form_field_values`` (values on an existing process).

There are exactly two ways to create a form field on a template in api-v2, and
neither is a bare ``/{entity}s/{id}/captures`` route:

1. **Step fields** -- ``POST /organizations/{org}/checklists/{checklist_id}/steps/{step_id}/captures``
   (``routes/api.php`` registers this as ``Route::resource('captures', ...)->only(['store', ...])``
   nested under ``checklists/{checklist_id}/steps/{step_id}``, which is why a
   naive grep for ``post('captures'`` misses it). Handler:
   ``Checklists\\StepCapturesController::store``, validated by ``CreateCaptureRequest``.

2. **Kick-off fields** -- there is no ``preruns`` store route. Kick-off fields
   are sent as a ``prerun`` **array on the checklist itself**, accepted by
   ``POST /organizations/{org}/checklists`` (``CreateChecklistRequest``) and
   ``PUT /organizations/{org}/checklists/{id}`` (``UpdateChecklistRequest``).
   Both call ``addCapturesRules($rules, 'prerun')``, so each entry obeys exactly
   the same rules as a step capture.

The validation rules both paths share (``CaptureRequestValidator::addCapturesRules``):

    label       required
    field_type  required, in Capture::$field_types
    required    required, boolean          <- required to be PRESENT, not required to be true
    options     required_if field_type in (radio, dropdown, multiselect)
    options.*.id    required, INTEGER      <- a string id is a 422
    options.*.text  required, string
    columns     required_if field_type = table
    columns.*.id    required, integer
    columns.*.label required, string
    position    integer

The migrator's own ``FieldTransformer`` emits a different shape -- ``type``
rather than ``field_type``, ``select`` rather than ``dropdown``, and options
nested under ``config.options`` as ``{value, label}``. Normalising here keeps
that transformer untouched while still producing a payload the API accepts.
"""

from typing import Any, Dict, Iterable, List, Optional

__all__ = [
    'CAPTURE_FIELD_TYPES',
    'OPTION_BEARING_FIELD_TYPES',
    'normalize_capture',
    'normalize_captures',
]

#: Mirrors ``Capture::$field_types`` in api-v2.
CAPTURE_FIELD_TYPES = frozenset({
    'text',
    'textarea',
    'radio',
    'dropdown',
    'multiselect',
    'date',
    'email',
    'file',
    'table',
    'assignees_form',
})

#: Field types for which api-v2 makes ``options`` mandatory.
OPTION_BEARING_FIELD_TYPES = frozenset({'radio', 'dropdown', 'multiselect'})

#: Source ``type`` values that do not match a Tallyfy field type 1:1.
_FIELD_TYPE_ALIASES = {
    'select': 'dropdown',
    'dropdown_select': 'dropdown',
    'single_select': 'dropdown',
    'multi_select': 'multiselect',
    'multiselect_list': 'multiselect',
    'checkbox': 'multiselect',
    'long_text': 'textarea',
    'short_text': 'text',
    'number': 'text',
    'phone': 'text',
    'url': 'text',
    'datetime': 'date',
    'due_date': 'date',
    'user': 'assignees_form',
    'users': 'assignees_form',
    'member': 'assignees_form',
    'members': 'assignees_form',
    'assignee_select': 'assignees_form',
    'files': 'file',
}


def _coerce_option_id(raw: Any, position: int) -> int:
    """
    api-v2 requires ``options.*.id`` to be an integer. Source systems routinely
    key options by slug or UUID, so fall back to the option's position rather
    than sending a string and taking a 422.
    """
    if isinstance(raw, bool):
        return position
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except (TypeError, ValueError):
            return position
    return position


def _normalize_options(raw_options: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(raw_options, Iterable) or isinstance(raw_options, (str, bytes, dict)):
        return normalized

    for index, option in enumerate(raw_options, start=1):
        if isinstance(option, dict):
            text = option.get('text', option.get('label', option.get('name', option.get('value'))))
            raw_id = option.get('id', option.get('value'))
        else:
            # Some transformers emit a bare list of strings.
            text = option
            raw_id = None

        if text is None:
            continue

        entry: Dict[str, Any] = {
            'id': _coerce_option_id(raw_id, index),
            'text': str(text),
        }
        if isinstance(option, dict) and option.get('description'):
            entry['description'] = str(option['description'])
        normalized.append(entry)

    return normalized


def _normalize_columns(raw_columns: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(raw_columns, Iterable) or isinstance(raw_columns, (str, bytes, dict)):
        return normalized

    for index, column in enumerate(raw_columns, start=1):
        if isinstance(column, dict):
            label = column.get('label', column.get('text', column.get('name')))
            raw_id = column.get('id')
        else:
            label = column
            raw_id = None

        if label is None:
            continue

        normalized.append({
            'id': _coerce_option_id(raw_id, index),
            'label': str(label),
        })

    return normalized


def normalize_capture(capture: Dict[str, Any], position: Optional[int] = None) -> Dict[str, Any]:
    """
    Return a copy of ``capture`` in the shape ``CreateCaptureRequest`` accepts.

    Args:
        capture: A field definition as emitted by a migrator ``FieldTransformer``.
        position: Optional 1-based position to stamp onto the field.

    Returns:
        A new dict safe to send as a step-capture body or as one entry of a
        checklist ``prerun`` array.

    Raises:
        TypeError: If ``capture`` is not a dict. Bare strings reaching this
            function mean an upstream transformer is malformed, and silently
            coercing them would recreate the class of bug this module exists to
            prevent.
    """
    if not isinstance(capture, dict):
        raise TypeError(
            'capture must be a dict describing a form field, got '
            f'{type(capture).__name__}: {capture!r}. An upstream transformer is '
            'emitting a malformed field definition.'
        )

    normalized = dict(capture)

    # ``type`` -> ``field_type``, honouring aliases such as select -> dropdown.
    raw_type = normalized.pop('type', None)
    field_type = normalized.get('field_type', raw_type)
    if isinstance(field_type, str):
        field_type = _FIELD_TYPE_ALIASES.get(field_type, field_type)
    if field_type not in CAPTURE_FIELD_TYPES:
        field_type = 'text'
    normalized['field_type'] = field_type

    # ``label`` is required.
    label = normalized.get('label') or normalized.get('name') or normalized.get('title')
    normalized['label'] = str(label) if label is not None else 'Untitled field'

    # ``required`` must be PRESENT and boolean.  Some transformers (Pipefy,
    # Process Street) emit ``is_required`` instead of ``required``.
    normalized['required'] = bool(
        normalized.get('required', normalized.get('is_required', False))
    )

    # Options may arrive nested under ``config``.
    config = normalized.get('config')
    raw_options = normalized.get('options')
    raw_columns = normalized.get('columns')
    if isinstance(config, dict):
        config = dict(config)
        if raw_options is None and 'options' in config:
            raw_options = config.pop('options')
        if raw_columns is None and 'columns' in config:
            raw_columns = config.pop('columns')
        normalized['config'] = config

    if field_type in OPTION_BEARING_FIELD_TYPES:
        options = _normalize_options(raw_options)
        if not options:
            # api-v2 rejects an option-bearing field with no options. A single
            # placeholder keeps the field (and therefore its values) migrating
            # instead of failing the whole template.
            options = [{'id': 1, 'text': str(normalized['label'])}]
        normalized['options'] = options
    elif raw_options is not None:
        normalized.pop('options', None)

    if field_type == 'table':
        columns = _normalize_columns(raw_columns)
        if not columns:
            columns = [{'id': 1, 'label': str(normalized['label'])}]
        normalized['columns'] = columns
    elif raw_columns is not None:
        normalized.pop('columns', None)

    if position is not None:
        normalized['position'] = int(position)

    return normalized


def normalize_captures(captures: Any) -> List[Dict[str, Any]]:
    """
    Normalise a list of field definitions, stamping 1-based positions.

    Non-dict entries raise ``TypeError`` via :func:`normalize_capture` rather
    than being skipped, so a malformed transformer surfaces loudly.
    """
    if captures is None:
        return []
    if not isinstance(captures, list):
        raise TypeError(
            f'captures must be a list of field definitions, got {type(captures).__name__}: '
            f'{captures!r}. An upstream transformer is emitting a malformed value.'
        )
    return [normalize_capture(capture, position=index) for index, capture in enumerate(captures, start=1)]
