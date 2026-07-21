"""
Fetch, cache and resolve a Tallyfy template's kick-off ("prerun") field definitions.

WHY THIS EXISTS
---------------
When launching a process, kick-off values are sent as an OBJECT keyed by each
kick-off field's ``timeline_id``::

    {"prerun": {"<timeline_id>": <value>, ...}}

A migrator cannot know a ``timeline_id`` from the source system -- it is minted
by Tallyfy when the field is created. Any key a migrator invents from a source
identifier (``field_abc123``, a Monday column id, a Typeform field ref) is
silently DISCARDED by the API: the launch returns 201 and every kick-off value
is lost. That failure is invisible unless you re-read the created process.

So the definitions must be fetched from the target template and every source
value resolved to a real ``timeline_id`` before the launch. This module does the
fetching and caching; :mod:`shared.prerun_encoder` does the per-type encoding.

WHERE timeline_id COMES FROM
----------------------------
The API returns a template's kick-off fields as an inlined ``prerun`` array on
the checklist. ``PrerunTransformer`` maps ``'id' => $prerun->timeline_id``, so
each entry's ``id`` IS the timeline_id this module needs.

The adjacent ``alias`` is a TRAP. Keying the launch payload by ``alias`` yields a
201 with ``prerun: {}`` -- accepted, and silently empty. Only ``id``
(= timeline_id) is read.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class KickoffFieldError(RuntimeError):
    """Base class for kick-off field resolution failures."""


class KickoffFieldsUnavailable(KickoffFieldError):
    """
    The target template's kick-off field definitions could not be fetched.

    Raised rather than falling back to source-system keys: those keys are
    discarded server-side, so a "successful" launch would silently lose every
    kick-off value.
    """


class NoKickoffFieldsDefined(KickoffFieldError):
    """
    The target template has NO kick-off fields, but the migration has values to
    put in them.

    This almost always means the template was created without its kick-off form.
    Launching anyway would discard every value, so this is raised instead.
    """


class UnresolvedKickoffValues(KickoffFieldError):
    """
    One or more source values could not be matched to a kick-off field.

    Carries the offending keys so the caller can report exactly what would have
    been lost.
    """

    def __init__(self, message: str, unresolved: Sequence[Any]):
        super().__init__(message)
        self.unresolved = list(unresolved)


def extract_kickoff_fields(checklist: Any) -> List[Dict[str, Any]]:
    """
    Pull the kick-off field definitions out of a checklist API response.

    Tolerates the envelope shapes these clients return: the raw checklist object,
    a ``{"data": {...}}`` wrapper, or the ``prerun`` array on its own.
    """
    if checklist is None:
        return []

    if isinstance(checklist, list):
        # Already the prerun array.
        return [field for field in checklist if isinstance(field, dict)]

    if not isinstance(checklist, dict):
        return []

    # Unwrap a {"data": ...} envelope.
    if 'prerun' not in checklist and isinstance(checklist.get('data'), (dict, list)):
        return extract_kickoff_fields(checklist['data'])

    prerun = checklist.get('prerun')
    if isinstance(prerun, list):
        return [field for field in prerun if isinstance(field, dict)]

    return []


def _fetch_checklist(client: Any, checklist_id: str) -> Any:
    """
    Fetch a checklist through whichever accessor the vendor's client exposes.

    The clients in this repo are near-copies that drifted: some define
    ``get_checklist``, the rest only have the private ``_make_request`` helper.
    Both are supported so no vendor needs a bespoke fetch path.
    """
    getter = getattr(client, 'get_checklist', None)
    if callable(getter):
        return getter(checklist_id)

    request = getattr(client, '_make_request', None)
    if callable(request):
        return request('GET', f'/checklists/{checklist_id}')

    raise KickoffFieldsUnavailable(
        f"{type(client).__name__} exposes no way to fetch a checklist "
        "(neither get_checklist nor _make_request); cannot resolve kick-off "
        "field timeline_ids"
    )


class KickoffFieldCache:
    """
    Fetches a template's kick-off field definitions once and reuses them.

    A migration launches many processes against the same handful of templates,
    so the definitions are fetched per template, not per process.

    Usage::

        cache = KickoffFieldCache(tallyfy_client)
        fields = cache.get(blueprint_id)          # [] when none are defined
        fields = cache.require(blueprint_id)      # raises when none are defined
    """

    def __init__(self, client: Any):
        self.client = client
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, checklist_id: str) -> List[Dict[str, Any]]:
        """
        Return the template's kick-off field definitions, fetching on first use.

        Returns an empty list when the template defines no kick-off fields.
        Raises :class:`KickoffFieldsUnavailable` when the fetch itself fails --
        an empty list would be indistinguishable from "template has none", and
        proceeding on that assumption loses data silently.
        """
        if checklist_id in self._cache:
            return self._cache[checklist_id]

        try:
            checklist = _fetch_checklist(self.client, checklist_id)
        except KickoffFieldError:
            raise
        except Exception as exc:
            raise KickoffFieldsUnavailable(
                f"Could not fetch template {checklist_id} to resolve kick-off "
                f"field timeline_ids: {exc}"
            ) from exc

        fields = extract_kickoff_fields(checklist)
        self._cache[checklist_id] = fields

        if fields:
            logger.info(
                "Template %s has %d kick-off field(s) available for prerun data",
                checklist_id,
                len(fields),
            )
        else:
            logger.warning(
                "Template %s defines NO kick-off fields; any kick-off values "
                "would be discarded by the API",
                checklist_id,
            )

        return fields

    def require(self, checklist_id: str) -> List[Dict[str, Any]]:
        """
        Like :meth:`get`, but raises when the template has no kick-off fields.

        Use this on a path that HAS values to migrate -- launching without
        somewhere to put them discards them silently.
        """
        fields = self.get(checklist_id)
        if not fields:
            raise NoKickoffFieldsDefined(
                f"Template {checklist_id} has no kick-off fields, so kick-off "
                "values cannot be migrated. The template was most likely created "
                "without its kick-off form. Create the kick-off fields on the "
                "template first, then re-run the instance migration."
            )
        return fields

    def clear(self, checklist_id: Optional[str] = None) -> None:
        """Drop cached definitions (all, or one template)."""
        if checklist_id is None:
            self._cache.clear()
        else:
            self._cache.pop(checklist_id, None)
