"""
Gate for the Independence Rule (CLAUDE.md, "Critical Rules for All Migrators").

    EACH MIGRATOR FOLDER IS COMPLETELY INDEPENDENT
    NEVER mention other vendors in README or documentation

Every migrator ships to a customer on its own. A Kissflow customer reading
their migrator should never find RocketLane in it.

WHY THIS IS A TEST AND NOT A STYLE NOTE
---------------------------------------
The leak was not cosmetic everywhere. All 17 vendors were cloned from one
skeleton, and the clone carried live values, not just prose:

    checkpoint_manager.py   source_system: str = 'rocketlane'   (x12 vendors)
        Written into id_mappings.source_system on save and matched on read.
        Both defaults have to agree or resume lookups return None.

    logger_config.py        'api.rocketlane_client': logging.DEBUG   (x11)
        A logger name is a MODULE PATH. `api.rocketlane_client` matches no
        logger in any of those vendors, so the setLevel was a silent no-op --
        while its neighbour 'api.tallyfy_client' worked. The correct value is
        NOT derivable from the vendor slug: cognito-forms imports
        `api.cognito_forms_client`, and kissflow/typeform/monday carry a
        `src.` or relative prefix.

    instance/user transformers   'source': 'rocketlane'   (x6)
        Emitted into migrated records. monday/src/utils/validator.py:345
        warns when metadata['source'] != its own vendor, and
        asana/tests/test_migration.py:79 asserts it equals 'asana' -- so the
        convention is the owning vendor, and these were wrong.

THE TRAP THIS GATE MUST NOT FALL INTO
-------------------------------------
`rocketlane/src/transformers/template_transformer.py` contains

    'business_hours': {'monday': '09:00-17:00', 'tuesday': ..., ...}

That `monday` is a WEEKDAY, not the vendor. A case-insensitive sweep that
rewrites it silently drops Monday from every migrated SLA schedule. Any
vendor name that is also an ordinary word needs a discriminator, which is
what `_is_weekday_context` is for.
"""

import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VENDORS = [
    'asana', 'basecamp', 'bpmn', 'clickup', 'cognito-forms', 'google-forms',
    'jotform', 'kissflow', 'monday', 'nextmatter', 'pipefy', 'process-street',
    'rocketlane', 'surveymonkey', 'trello', 'typeform', 'wrike',
]

# Slug -> the regexes that identify a reference to THAT vendor.
_ALIASES = {
    'cognito-forms': [r'cognito[-_ ]?forms'],
    'google-forms': [r'google[-_ ]?forms'],
    'process-street': [r'process[-_ ]?street'],
    'nextmatter': [r'next[-_ ]?matter'],
    'surveymonkey': [r'survey[-_ ]?monkey'],
    'rocketlane': [r'rocket[-_ ]?lane', r'\brl_'],
    'monday': [r'\bmonday(?:\.com)?\b'],
}


def _patterns(vendor):
    return _ALIASES.get(vendor, [r'\b' + re.escape(vendor) + r'\b'])


def _is_weekday_context(source):
    """`monday` beside other weekdays is a calendar, not a vendor.

    A file that genuinely references Monday.com does not also say "tuesday".
    """
    return bool(re.search(r'\b(tuesday|wednesday|thursday)\b', source, re.I))


def _iter_sources(vendor):
    for sub in ('src', 'tests'):
        root = os.path.join(REPO_ROOT, vendor, sub)
        for dirpath, _, names in os.walk(root):
            for name in names:
                if name.endswith('.py'):
                    yield os.path.join(dirpath, name)


class TestNoMigratorNamesAnotherVendor:

    @pytest.mark.parametrize('vendor', VENDORS)
    def test_vendor_source_names_no_other_vendor(self, vendor):
        offenders = {}
        others = [v for v in VENDORS if v != vendor]

        for path in _iter_sources(vendor):
            source = open(path).read()
            weekdayish = _is_weekday_context(source)
            for other in others:
                if other == 'monday' and weekdayish:
                    continue
                for pattern in _patterns(other):
                    for match in re.finditer(pattern, source, re.I):
                        line = source.count('\n', 0, match.start()) + 1
                        rel = os.path.relpath(path, REPO_ROOT)
                        offenders.setdefault(rel, []).append((line, other))

        assert not offenders, (
            f'{vendor} names another vendor. Each migrator ships standalone, '
            f'and these are not all cosmetic -- source_system defaults and '
            f'logger module paths were wrong too: {offenders}'
        )


class TestTheWeekdayIsNotMistakenForTheVendor:
    """Pins the discriminator itself, so the gate above cannot be "fixed" by
    rewriting a calendar."""

    def test_business_hours_weekdays_survive(self):
        path = os.path.join(
            REPO_ROOT, 'rocketlane', 'src', 'transformers', 'template_transformer.py'
        )
        source = open(path).read()
        for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday'):
            assert f"'{day}': '09:00-17:00'" in source, (
                f'{day} is missing from the default business_hours schedule. '
                f'A case-insensitive vendor rename over this dict drops it '
                f'silently from every migrated SLA.'
            )

    def test_the_discriminator_actually_discriminates(self):
        assert _is_weekday_context("{'monday': '09:00', 'tuesday': '09:00'}")
        assert not _is_weekday_context('from api.monday_client import MondayClient')
