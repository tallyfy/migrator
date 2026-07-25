"""
Typed encoder for Tallyfy kick-off ("prerun") form values.

WHY THIS EXISTS
---------------
When launching a process, Tallyfy expects the kick-off form data under the
request key ``prerun`` -- NOT ``prerun_data``. The API reads
``$this->get('prerun')`` and ``$this->get('prerun.'.$timeline_id)``, so a body
that carries ``prerun_data`` is silently ignored and every kick-off value is
discarded. Any required kick-off field then fails the launch with a 422.

The value of ``prerun`` is an OBJECT keyed by each kick-off field's
``timeline_id`` (32-char hex) -- not a list, and not field names or labels::

    {"prerun": {"<timeline_id>": <value>, ...}}

Per-field value shapes are type-dependent and are validated server-side. This
module mirrors the proven production implementation used by the Tallyfy
Zapier/Power Automate middleware (``processFieldValue``) so migrators emit
exactly the shapes the API accepts:

===============  ==========================================================
field_type       encoded value
===============  ==========================================================
text             bare scalar (string)
textarea         bare scalar (string)
email            bare scalar (string)
date             bare scalar, ISO-8601 string
radio            the chosen option's TEXT, as a bare scalar
dropdown         {"id": <option id>, "text": "<exact option text>"}
multiselect      list of {"id":.., "text":.., "selected": true}
table            list with exactly one entry per defined column
assignees_form   {"users": [int], "guests": ["email"], "groups": [id]}
file             list of file descriptors
===============  ==========================================================

``dropdown`` and ``radio`` are deliberately ASYMMETRIC -- dropdown needs the
full {id, text} object, radio needs the bare text. Do not "harmonise" them.
"""

import json
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

# The API request key for kick-off data. The legacy key below was never read
# by the API and is only accepted on INPUT so older callers keep working.
PRERUN_KEY = 'prerun'
LEGACY_PRERUN_KEY = 'prerun_data'

# Matches the middleware's email validation for assignees_form values.
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class PrerunEncodingError(ValueError):
    """Base class for kick-off value encoding failures."""


class TableShapeError(PrerunEncodingError):
    """
    A table value does not have exactly one entry per defined column.

    The API validates ``count($values) !== count($capture->columns)`` and returns
    422, so a mismatch can never be launched. It is raised here, where the
    offending field is known, rather than sent for the API to reject opaquely.
    """


class UnresolvedFieldError(PrerunEncodingError):
    """
    Source values could not be matched to any kick-off field on the template.

    Sending them anyway is not a safe fallback: the API keys strictly by
    timeline_id and silently discards everything else, returning 201 with the
    values gone.
    """

    def __init__(self, message: str, unresolved: Sequence[Any]):
        super().__init__(message)
        self.unresolved = list(unresolved)

# Date fields are rendered as ISO-8601 with milliseconds, mirroring the
# middleware default moment format 'YYYY-MM-DDTHH:mm:ss.SSS[Z]'.
SCALAR_FIELD_TYPES = frozenset({'text', 'textarea', 'email', 'short_text', 'long_text'})


def _capture_options(capture: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a capture's selectable options as a list of dicts."""
    options = capture.get('options') or []
    return [opt for opt in options if isinstance(opt, dict)]


def _find_option(options: Sequence[Dict[str, Any]], value: Any) -> Optional[Dict[str, Any]]:
    """
    Resolve a raw value to one of a capture's options.

    Matches on option text first (the middleware's behaviour, and what users'
    exported data usually contains), then falls back to matching on option id.
    """
    if value is None:
        return None

    for option in options:
        if option.get('text') == value:
            return option

    # Fall back to id matching, tolerating int/str drift between systems.
    for option in options:
        option_id = option.get('id')
        if option_id is not None and str(option_id) == str(value):
            return option

    return None


def _option_payload(option: Dict[str, Any], selected: Optional[bool] = None) -> Dict[str, Any]:
    """
    Build the {"id":.., "text":..} pair the API validates against.

    A copy is returned so the caller's capture definition is never mutated.
    """
    payload: Dict[str, Any] = {'id': option.get('id'), 'text': option.get('text')}
    if selected is not None:
        payload['selected'] = selected
    return payload


def _format_date(value: Any, date_format: Optional[str] = None) -> Any:
    """
    Render a date value as an ISO-8601 string.

    The API requires a string it can parse; datetime/date objects are rendered,
    strings are passed through unchanged (they are already serialisable and the
    API parses a wide range of formats).
    """
    if value is None or value == '':
        return value

    if isinstance(value, datetime):
        if date_format:
            return value.strftime(date_format)
        return value.strftime('%Y-%m-%dT%H:%M:%S.') + f'{value.microsecond // 1000:03d}Z'

    if isinstance(value, date):
        if date_format:
            return value.strftime(date_format)
        return value.strftime('%Y-%m-%dT00:00:00.000Z')

    return value


def _encode_table(value: Any, capture: Dict[str, Any]) -> Any:
    """
    Encode a table field.

    The API requires a list with exactly one entry per defined column. A JSON
    string is parsed first (mirrors the middleware). When the column count is
    known and the value cannot be aligned to it, the value is returned unchanged
    and a warning is logged -- it is better for the API to reject the row loudly
    than for this encoder to silently invent or drop cells.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            logger.warning(
                "Table field %r has a non-JSON string value; sending it unchanged",
                capture.get('label') or capture.get('alias') or capture.get('id'),
            )
            return value

    columns = capture.get('columns') or []
    if not columns:
        return value

    if isinstance(value, dict):
        # Keyed by column id/name -> project onto the declared column order.
        aligned = []
        for column in columns:
            if not isinstance(column, dict):
                aligned.append(value.get(column))
                continue
            for key in ('id', 'name', 'label', 'text'):
                if column.get(key) in value:
                    aligned.append(value[column[key]])
                    break
            else:
                aligned.append(None)
        return aligned

    if isinstance(value, list) and len(value) != len(columns):
        # The API validates count($values) !== count($capture->columns) and
        # returns 422. Sending it is a guaranteed failed launch, so fail here
        # where the field and both counts are known.
        raise TableShapeError(
            f"Table field {capture.get('label') or capture.get('alias') or capture.get('id')!r} "
            f"has {len(value)} entries but {len(columns)} columns are defined. "
            "The API requires exactly one entry per column and returns 422 otherwise."
        )

    return value


def encode_assignees_form(
    value: Any,
    org_members: Optional[Iterable[Dict[str, Any]]] = None,
    current_user_id: Any = None,
) -> Dict[str, List[Any]]:
    """
    Encode an assignees_form value as {"users": [...], "guests": [...], "groups": [...]}.

    Accepts a comma-separated email string, a list of emails, or an already
    shaped dict. Emails matching an org member become ``users`` (by member id);
    everything else becomes a ``guests`` email. Business rule carried over from
    the middleware: guests cannot be the sole assignees, so the current user is
    added when only guests were resolved.
    """
    if isinstance(value, dict):
        return {
            'users': list(value.get('users') or []),
            'guests': list(value.get('guests') or []),
            'groups': list(value.get('groups') or []),
        }

    if isinstance(value, str):
        candidates = value.split(',')
    elif isinstance(value, (list, tuple)):
        candidates = list(value)
    elif value is None:
        candidates = []
    else:
        candidates = [value]

    members = list(org_members or [])
    users: List[Any] = []
    guests: List[str] = []

    for candidate in candidates:
        raw = str(candidate).strip()
        if not raw:
            continue

        if not EMAIL_REGEX.match(raw):
            # Deliberately NOT treated as a Tallyfy user id. A bare number here
            # is a SOURCE-system user id, and the two id spaces are unrelated --
            # coercing one into the other assigns the task to whichever unrelated
            # Tallyfy user happens to hold that id, which is worse than dropping
            # it. Map ids to Tallyfy users upstream (see
            # ``form_field_values.reshape_assignee_values``); anything still
            # unmapped is reported by the strict layer rather than invented here.
            continue

        match = next((m for m in members if m.get('email') == raw), None)
        if match:
            member_id = match.get('id')
            if not any(str(u) == str(member_id) for u in users):
                users.append(member_id)
        elif raw not in guests:
            guests.append(raw)

    if guests and not users and current_user_id is not None:
        users.append(current_user_id)

    return {'users': users, 'guests': guests, 'groups': []}


def encode_field_value(
    value: Any,
    capture: Optional[Dict[str, Any]] = None,
    *,
    date_format: Optional[str] = None,
    file_subject: Optional[Dict[str, Any]] = None,
    uploaded_from: str = '',
    org_members: Optional[Iterable[Dict[str, Any]]] = None,
    current_user_id: Any = None,
) -> Any:
    """
    Encode a single kick-off value into the shape the Tallyfy API expects.

    Args:
        value: The raw value taken from the source system.
        capture: The Tallyfy kick-off field definition (needs ``field_type``,
            and ``options``/``columns`` for choice and table fields). When it is
            unknown the value is returned unchanged -- this encoder never
            guesses a type.
        date_format: Optional strftime format for date fields (ISO-8601 by default).
        file_subject: ``subject`` object attached to file descriptors.
        uploaded_from: ``uploaded_from`` marker attached to file descriptors.
        org_members: Org members used to resolve assignees_form emails to user ids.
        current_user_id: Fallback assignee when only guests were resolved.

    Returns:
        The encoded value, ready to be placed under ``prerun[timeline_id]``.
    """
    if capture is None:
        return value

    field_type = capture.get('field_type') or capture.get('type')

    # Scalar choice types can legitimately arrive wrapped in a one-element list:
    # several source systems return every choice field as an array (Pipefy's
    # `array_value` on a label field, for one). One element is unambiguous, so
    # unwrap it rather than failing to match. Two or more genuinely cannot fit a
    # single-choice field and are left to fail loudly.
    if field_type in ('dropdown', 'radio') and isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = value[0]

    if field_type == 'dropdown':
        option = _find_option(_capture_options(capture), value)
        if option is None:
            if value not in (None, ''):
                logger.warning(
                    "Dropdown value %r does not match any option of field %r; omitting it",
                    value,
                    capture.get('label') or capture.get('alias') or capture.get('id'),
                )
            return None
        return _option_payload(option)

    if field_type == 'multiselect':
        options = _capture_options(capture)
        if isinstance(value, (list, tuple, set)):
            raw_values = list(value)
        elif value in (None, ''):
            raw_values = []
        else:
            raw_values = [value]

        encoded: List[Dict[str, Any]] = []
        for raw in raw_values:
            option = _find_option(options, raw)
            if option is None:
                logger.warning(
                    "Multi-select value %r does not match any option of field %r; omitting it",
                    raw,
                    capture.get('label') or capture.get('alias') or capture.get('id'),
                )
                continue
            encoded.append(_option_payload(option, selected=True))
        return encoded

    if field_type == 'radio':
        option = _find_option(_capture_options(capture), value)
        if option is not None:
            # radio takes the option TEXT as a bare scalar (NOT an {id, text} object).
            return option.get('text')
        return value

    if field_type == 'date':
        return _format_date(value, date_format)

    if field_type == 'table':
        return _encode_table(value, capture)

    if field_type == 'assignees_form':
        return encode_assignees_form(value, org_members, current_user_id)

    if field_type == 'file':
        if value in (None, ''):
            return value
        if isinstance(value, list):
            encoded_files = []
            for item in value:
                if isinstance(item, dict):
                    encoded_files.append(item)
                else:
                    item_url = str(item)
                    encoded_files.append({
                        'filename': item_url.split('/')[-1],
                        'source': 'url',
                        'subject': file_subject or {},
                        'uploaded_from': uploaded_from,
                        'url': item_url,
                    })
            return encoded_files
        url = str(value)
        return [{
            'filename': url.split('/')[-1],
            'source': 'url',
            'subject': file_subject or {},
            'uploaded_from': uploaded_from,
            'url': url,
        }]

    if field_type in SCALAR_FIELD_TYPES:
        if value is None or isinstance(value, str):
            return value
        if isinstance(value, bool):
            return 'yes' if value else 'no'
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return str(value)

    return value


def resolve_capture(
    key: Any,
    captures: Optional[Sequence[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """
    Find the kick-off field a source key refers to.

    Keys are matched against ``timeline_id``, ``id``, ``alias`` and ``label``,
    in that order, so migrators can address fields by whichever identifier they
    happen to hold.
    """
    if not captures:
        return None

    for attribute in ('timeline_id', 'id', 'alias', 'label'):
        for capture in captures:
            if not isinstance(capture, dict):
                continue
            candidate = capture.get(attribute)
            if candidate is not None and str(candidate) == str(key):
                return capture

    return None


def normalize_prerun_object(value: Any) -> Dict[str, Any]:
    """
    Coerce prerun data into the object form the API requires.

    The API keys kick-off values by ``timeline_id``; a list is never accepted.
    A list of ``{"field_id": .., "value": ..}`` entries (the shape some
    migrators produced) is folded into an object.
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, list):
        normalized: Dict[str, Any] = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            field_id = item.get('field_id', item.get('id', item.get('timeline_id')))
            if field_id is None:
                continue
            normalized[str(field_id)] = item.get('value')
        return normalized

    logger.warning("Unsupported prerun payload of type %s; ignoring it", type(value).__name__)
    return {}


def build_prerun_payload(
    values: Any,
    captures: Optional[Sequence[Dict[str, Any]]] = None,
    *,
    strict: bool = False,
    **options: Any,
) -> Dict[str, Any]:
    """
    Build the ``prerun`` request object from raw source values.

    Args:
        values: Either an object keyed by a field identifier, or a list of
            ``{"field_id": .., "value": ..}`` entries.
        captures: The template's kick-off field definitions. When supplied,
            every key is resolved to its ``timeline_id`` and every value is
            typed correctly. When omitted the keys are passed through unchanged
            and a warning is logged -- the API keys strictly by ``timeline_id``,
            so unresolved keys are discarded server-side.
        strict: Raise instead of dropping values that cannot be resolved to a
            kick-off field. Live migration paths should pass ``strict=True``:
            a dropped value is invisible (the launch still returns 201), so
            silence there means silent data loss.
        **options: Forwarded to :func:`encode_field_value`.

    Returns:
        An object keyed by ``timeline_id``, ready to send as ``{"prerun": ...}``.

    Raises:
        UnresolvedFieldError: In strict mode, when definitions are missing or a
            value cannot be matched to a kick-off field.
        TableShapeError: When a table value does not match its column count.
    """
    normalized = normalize_prerun_object(values)
    if not normalized:
        return {}

    if not captures:
        if strict:
            raise UnresolvedFieldError(
                "Cannot build prerun data without the template's kick-off field "
                "definitions: the API keys strictly by timeline_id, so every "
                f"value would be discarded. Unresolvable keys: {sorted(map(str, normalized))}",
                list(normalized),
            )
        logger.warning(
            "Building prerun data without kick-off field definitions; keys are sent "
            "unchanged and the API will discard any that are not a timeline_id"
        )
        return normalized

    payload: Dict[str, Any] = {}
    unresolved: List[Any] = []

    for key, raw_value in normalized.items():
        capture = resolve_capture(key, captures)
        if capture is None:
            unresolved.append(key)
            logger.warning(
                "No kick-off field matches %r; its value will not be migrated", key
            )
            continue

        timeline_id = capture.get('timeline_id') or capture.get('id')
        if timeline_id is None:
            unresolved.append(key)
            logger.warning(
                "Kick-off field %r has no timeline_id; its value will not be migrated", key
            )
            continue

        encoded = encode_field_value(raw_value, capture, **options)

        if encoded in (None, []) and raw_value not in (None, '', [], {}):
            unresolved.append(key)
            logger.warning(
                "Kick-off value %r for %r could not be encoded for field_type %r; "
                "it will not be migrated rather than written as an empty value.",
                raw_value, key, capture.get('field_type') or capture.get('type'),
            )
            continue

        field_type = capture.get('field_type') or capture.get('type')
        if field_type == 'assignees_form' and raw_value not in (None, '', [], {}):
            # A pre-shaped dict with empty lists is legitimately empty, not loss.
            is_preshaped_empty = (
                isinstance(raw_value, dict)
                and any(k in raw_value for k in ('users', 'guests', 'groups'))
                and not any(raw_value.get(k) for k in ('users', 'guests', 'groups'))
            )
            if (
                not is_preshaped_empty
                and isinstance(encoded, dict)
                and not any(encoded.get(k) for k in ('users', 'guests', 'groups'))
            ):
                unresolved.append(key)
                logger.warning(
                    "Kick-off assignee value %r for %r resolved to nobody; "
                    "it will not be migrated rather than written as empty assignees.",
                    raw_value, key,
                )
                continue

        payload[str(timeline_id)] = encoded

    if unresolved and strict:
        available = [
            str(c.get('label') or c.get('alias') or c.get('id'))
            for c in captures if isinstance(c, dict)
        ]
        raise UnresolvedFieldError(
            f"{len(unresolved)} kick-off value(s) could not be matched to a field on "
            f"the target template and would be silently discarded: "
            f"{sorted(map(str, unresolved))}. Available kick-off fields: {available}",
            unresolved,
        )

    return payload
