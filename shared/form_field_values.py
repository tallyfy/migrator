"""
Resolve and encode form-field values for ALREADY-LAUNCHED Tallyfy processes.

WHY THIS EXISTS
---------------
``prerun_encoder`` covers kick-off values sent at LAUNCH time (``POST /runs``).
This module covers the other half: writing form-field values onto a process that
already exists. It is a thin resolver/grouper on top of ``prerun_encoder`` -- the
per-type value encoding is NOT reimplemented here. ``encode_field_value`` and
``resolve_capture`` are imported and reused, so ``radio``/``dropdown``/
``multiselect``/``table``/``assignees_form`` behave identically on both paths.

THE TWO WRITE ENDPOINTS, AND WHY WE USE THE BULK ONE
----------------------------------------------------
Tallyfy exposes two ways to write a form-field value:

1. ``PUT /organizations/{org}/form-field/value``
   body ``{"id": <capture-value id>, "form_value": <typed value>}``

   ``id`` is the id of the *capture value row* (``core.leads``) -- NOT the
   capture/field definition id, and NOT a ``timeline_id``. The API resolves it
   with ``CaptureValue::find($data['id'])``.

   A migrator cannot use this endpoint as its main path, because capture-value
   ids are not discoverable through the API: the two places that would expose
   one (``Task::allFormFields()`` and ``RunTransformer::includeKoFormFields()``)
   have their ``$field->unique_id = $lead->id`` assignment commented out, so
   ``unique_id`` is always null in the responses. Use it only when you already
   hold a capture-value id from somewhere else.

2. ``PUT /organizations/{org}/runs/{run_id}/tasks/{task_id}``
   body ``{"taskdata": {"<capture timeline_id>": <typed value>, ...}}``

   This is the canonical bulk writer (``Task::setTaskdataAttribute`` ->
   ``Task::updateCaptureValues``), and it keys by ``timeline_id`` -- which IS
   discoverable, via ``GET /organizations/{org}/runs/{run_id}/form-fields``.
   That response gives ``id`` (the timeline_id), ``field_type``, ``options``,
   ``columns`` and ``task_id`` for every field on the process.

So the migration path is: read the run's live form fields, resolve each source
value to one of them, encode it for its type, group by ``task_id``, and send one
``taskdata`` write per task. That is what :func:`build_task_form_field_payloads`
produces.

FAILING LOUDLY IS THE POINT
---------------------------
An unresolved field is invisible at runtime -- the write still returns 200 for
the fields that did resolve, and the migration prints a success summary while
the value is gone. So unresolved values raise by default (``strict=True``)
rather than being logged and skipped.
"""

import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .prerun_encoder import EMAIL_REGEX, PrerunEncodingError, encode_field_value, resolve_capture

logger = logging.getLogger(__name__)


class FormFieldValueError(PrerunEncodingError):
    """Base class for form-field value migration failures."""


class UnresolvedFormFieldError(FormFieldValueError):
    """
    Source values could not be matched to a form field on the target process.

    Sending them anyway is not a safe fallback: the API keys ``taskdata``
    strictly by ``timeline_id`` and silently ignores anything else, so the write
    succeeds with the value discarded.
    """

    def __init__(self, message: str, unresolved: Sequence[Any]):
        super().__init__(message)
        self.unresolved = list(unresolved)


class MissingTaskBindingError(FormFieldValueError):
    """
    A resolved form field carried no ``task_id``.

    ``taskdata`` is written per task, so a field with no task binding has
    nowhere to be written. This is raised rather than guessed at.
    """


def _is_emptied_assignees(field: Dict[str, Any], raw_value: Any, encoded: Any) -> bool:
    """
    True when an assignees_form field had a source value but encoded to nobody.

    Distinguishes real loss from a legitimately empty field: a blank source value
    encoding to no assignees is correct and must NOT be reported.
    """
    if (field.get('field_type') or field.get('type')) != 'assignees_form':
        return False
    if raw_value in (None, '', [], {}):
        return False
    # `reshape_assignee_values` rewrites an empty source value into the shaped
    # `{"users": [], "guests": [], "groups": []}`. That is a legitimately EMPTY
    # field, not loss -- without this, an unselected member field (Process
    # Street keeps `[]` form values) would raise under strict=True and block
    # every other value on the run.
    if isinstance(raw_value, dict) and not any(
        raw_value.get(key) for key in ('users', 'guests', 'groups')
    ):
        return False
    if not isinstance(encoded, dict):
        return False
    return not any(encoded.get(key) for key in ('users', 'guests', 'groups'))


def extract_run_form_fields(response: Any) -> List[Dict[str, Any]]:
    """
    Pull the form-field definitions out of a ``runs/{id}/form-fields`` response.

    The endpoint returns ``{"data": {..., "form_fields": [...],
    "ko_form_fields": [...]}}``. Both lists are returned together: kick-off
    fields and step fields are both writable, and callers resolve against the
    union.

    A plain list is accepted too, so callers can pass definitions they already
    hold.
    """
    if response is None:
        return []

    if isinstance(response, list):
        return [f for f in response if isinstance(f, dict)]

    if not isinstance(response, Mapping):
        return []

    data = response.get('data', response)
    if isinstance(data, list):
        return [f for f in data if isinstance(f, dict)]
    if not isinstance(data, Mapping):
        return []

    fields: List[Dict[str, Any]] = []
    for key in ('form_fields', 'ko_form_fields'):
        for field in data.get(key) or []:
            if isinstance(field, dict):
                fields.append(field)
    return fields


def _candidate_keys(source_key: Any, *extra: Any) -> List[Any]:
    """Build an ordered, de-duplicated list of identifiers to resolve against."""
    keys: List[Any] = []
    for candidate in (source_key,) + extra:
        if candidate in (None, ''):
            continue
        if not any(str(candidate) == str(k) for k in keys):
            keys.append(candidate)
    return keys


def resolve_form_field(
    form_fields: Sequence[Dict[str, Any]],
    source_key: Any,
    *fallback_keys: Any,
) -> Optional[Dict[str, Any]]:
    """
    Find the form field a source value belongs to.

    Each candidate is matched against ``timeline_id``, ``id``, ``alias`` and
    ``label`` (``prerun_encoder.resolve_capture``). Candidates are tried in the
    order given, so callers should pass their most reliable identifier first
    (usually a mapped Tallyfy id), then fall back to the source label.
    """
    for key in _candidate_keys(source_key, *fallback_keys):
        field = resolve_capture(key, form_fields)
        if field is not None:
            return field
    return None


def reshape_assignee_values(
    raw_values: Dict[Any, Any],
    form_fields: Sequence[Dict[str, Any]],
    fallback_keys: Optional[Mapping[Any, Sequence[Any]]] = None,
    user_id_mapper: Any = None,
) -> None:
    """
    Pre-shape assignee field values so the encoder receives a dict it passes
    through, rather than raw source-system user IDs that would be silently
    dropped by :func:`~prerun_encoder.encode_assignees_form`.

    Source systems (Process Street, Pipefy, etc.) store member/assignee field
    values as user IDs.  The encoder only keeps email-shaped candidates and
    drops everything else, so those IDs vanish without a trace -- the write
    still succeeds and the migration reports success.

    This function resolves each value against the target form fields and, for
    any ``assignees_form`` field, maps the source IDs through
    ``user_id_mapper`` and wraps them in the ``{"users": [...], "guests": [],
    "groups": []}`` shape the encoder passes through unchanged.

    Mutates *raw_values* in place.  Call it between fetching form fields and
    calling :func:`build_task_form_field_payloads`.

    Args:
        raw_values: The mutable source-value dict that will later be fed to
            ``build_task_form_field_payloads``.
        form_fields: Live form fields from ``GET /runs/{id}/form-fields``.
        fallback_keys: Same as ``build_task_form_field_payloads``.
        user_id_mapper: ``callable(source_id) -> tallyfy_user_id | None``.
            Typically ``lambda uid: id_mapper.get_tallyfy_id(str(uid), 'user')``.
    """
    if not form_fields or not raw_values:
        return

    fallbacks = fallback_keys or {}

    for key in list(raw_values):
        field = resolve_form_field(
            form_fields, key, *(fallbacks.get(key) or ())
        )
        if field is None:
            continue
        field_type = field.get('field_type') or field.get('type')
        if field_type != 'assignees_form':
            continue

        value = raw_values[key]
        if isinstance(value, dict) and any(
            k in value for k in ('users', 'guests', 'groups')
        ):
            continue

        if isinstance(value, str):
            candidates = [v.strip() for v in value.split(',') if v.strip()]
        elif isinstance(value, (list, tuple)):
            candidates = list(value)
        elif value is None:
            raw_values[key] = {'users': [], 'guests': [], 'groups': []}
            continue
        else:
            candidates = [value]

        users: List[Any] = []
        guests: List[str] = []
        # Pipefy's CardField.assignee_values is typed `[[User]]` -- a list OF
        # LISTS -- so the candidates can arrive one level deeper than expected.
        # Flatten before unwrapping, or each inner list stringifies to a list
        # repr that maps to nothing and the assignees are lost.
        flattened: List[Any] = []
        for candidate in candidates:
            if isinstance(candidate, (list, tuple)):
                flattened.extend(candidate)
            else:
                flattened.append(candidate)
        candidates = flattened

        for candidate in candidates:
            # Source systems often return assignees as objects rather than bare
            # ids -- `{"id": 42, "email": ...}`. `str()` on one of those yields
            # the repr of a dict, which maps to nothing and is not an email, so
            # the assignee would be lost. Unwrap to the id (or email) first.
            if isinstance(candidate, dict):
                candidate = (
                    candidate.get('id')
                    or candidate.get('email')
                    or candidate.get('user_id')
                    or candidate.get('username')
                )
                if candidate is None:
                    continue

            cand_str = str(candidate).strip()
            if not cand_str:
                continue

            if user_id_mapper is not None:
                mapped = user_id_mapper(cand_str)
                if mapped is not None:
                    try:
                        users.append(int(mapped))
                    except (TypeError, ValueError):
                        users.append(mapped)
                    continue

            if EMAIL_REGEX.match(cand_str):
                if cand_str not in guests:
                    guests.append(cand_str)
            else:
                # An unmapped candidate is NOT coerced into a Tallyfy user id.
                # Source-system ids and Tallyfy ids are unrelated id spaces, so
                # `int(cand_str)` would assign the task to whichever unrelated
                # Tallyfy user holds that number -- silently wrong is worse than
                # loudly missing. Leaving it out means the value encodes to
                # nobody, which `build_task_form_field_payloads` reports (and
                # raises on under strict=True).
                logger.warning(
                    'Assignee candidate %r could not be mapped to a Tallyfy '
                    'user and is not an email; it will not be assigned. Ensure '
                    'the user migration phase ran before instances.',
                    candidate,
                )

        if not users and not guests and candidates:
            # There WERE candidates and none of them resolved. Leave the raw
            # value in place rather than rewriting it to a shaped-but-empty
            # dict: that dict is indistinguishable from a legitimately empty
            # field, and rewriting it would launder real data loss into
            # something the strict layer treats as fine.
            continue

        raw_values[key] = {'users': users, 'guests': guests, 'groups': []}


def build_task_form_field_payloads(
    values: Mapping[Any, Any],
    form_fields: Sequence[Dict[str, Any]],
    *,
    strict: bool = True,
    fallback_keys: Optional[Mapping[Any, Sequence[Any]]] = None,
    **options: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Group source values into per-task ``taskdata`` payloads.

    Args:
        values: Source values keyed by whatever identifier the migrator holds
            (a mapped Tallyfy capture id, a source field id, a label...).
        form_fields: The process's live form fields, as returned by
            ``GET /runs/{id}/form-fields`` (see :func:`extract_run_form_fields`).
        strict: Raise :class:`UnresolvedFormFieldError` when a value cannot be
            matched to a field on the process. Live migration paths must leave
            this on -- a dropped value is invisible, so a quiet skip is silent
            data loss.
        fallback_keys: Extra identifiers to try per source key, e.g.
            ``{source_field_id: [label]}``.
        **options: Forwarded to ``prerun_encoder.encode_field_value``.

    Returns:
        ``{task_id: {timeline_id: encoded_value}}`` -- one entry per task that
        has at least one value to write.

    Raises:
        UnresolvedFormFieldError: In strict mode, when a value has no matching
            field on the process.
        MissingTaskBindingError: When a matched field carries no ``task_id``.
        TableShapeError: When a table value does not match its column count.
    """
    if not values:
        return {}

    if not form_fields:
        if strict:
            raise UnresolvedFormFieldError(
                'The target process exposes no form fields, so none of these '
                'values can be written and all of them would be discarded: '
                f'{sorted(map(str, values))}',
                list(values),
            )
        logger.warning(
            'No form fields on the target process; %d value(s) will not be migrated',
            len(values),
        )
        return {}

    fallbacks = fallback_keys or {}
    payloads: Dict[str, Dict[str, Any]] = {}
    unresolved: List[Any] = []

    for source_key, raw_value in values.items():
        field = resolve_form_field(
            form_fields, source_key, *(fallbacks.get(source_key) or ())
        )
        if field is None:
            unresolved.append(source_key)
            logger.warning(
                'No form field on the process matches %r; its value will not be migrated',
                source_key,
            )
            continue

        timeline_id = field.get('timeline_id') or field.get('id')
        if timeline_id is None:
            unresolved.append(source_key)
            logger.warning(
                'Form field matching %r has no timeline_id; its value will not be migrated',
                source_key,
            )
            continue

        task_id = field.get('task_id')
        if task_id in (None, ''):
            raise MissingTaskBindingError(
                f'Form field {field.get("label") or field.get("alias") or timeline_id!r} '
                'has no task_id, so there is no task to write its value to. '
                'Fetch the fields from GET /runs/{run_id}/form-fields, which '
                'includes task_id for every field.'
            )

        encoded = encode_field_value(raw_value, field, **options)

        # The encoder returns None when it cannot represent the value -- a
        # choice value matching no option, for instance (a list handed to a
        # dropdown, which is what a Pipefy label field produces). Writing that
        # None stores an empty field and returns 200: silent loss, and the
        # encoder's own log line claims it is "omitting" a value it was in fact
        # still passing through. Treat it as unresolved so strict mode raises.
        # `[]` counts as unencodable too: a multiselect whose every entry failed
        # option matching returns an empty list, which would otherwise be
        # written and store the selections as empty with a 200.
        if encoded in (None, []) and raw_value not in (None, '', [], {}):
            unresolved.append(source_key)
            logger.warning(
                'Value %r for %r could not be encoded for field_type %r; it will '
                'not be migrated rather than written as an empty value.',
                raw_value, source_key, field.get('field_type') or field.get('type'),
            )
            continue

        # `assignees_form` resolves only email-shaped candidates (deliberately --
        # it mirrors the middleware). Source systems key assignee fields by user
        # ID or display name, so a non-empty source value can encode to an EMPTY
        # assignee payload. Writing that returns 200 with the assignees gone,
        # which is precisely the silent loss this module exists to prevent.
        if _is_emptied_assignees(field, raw_value, encoded):
            unresolved.append(source_key)
            logger.warning(
                'Assignee value %r for %r resolved to nobody. assignees_form '
                'matches on email; map source user IDs to emails (or to '
                '{"users": [...]}) before encoding.',
                raw_value, source_key,
            )
            continue

        payloads.setdefault(str(task_id), {})[str(timeline_id)] = encoded

    if unresolved and strict:
        available = [
            str(f.get('label') or f.get('alias') or f.get('id'))
            for f in form_fields if isinstance(f, dict)
        ]
        raise UnresolvedFormFieldError(
            f'{len(unresolved)} form-field value(s) could not be matched to a field on '
            f'the target process and would be silently discarded: '
            f'{sorted(map(str, unresolved))}. Available fields: {available}',
            unresolved,
        )

    return payloads
