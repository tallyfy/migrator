"""
A client must build its URLs one way, not two.

THE BUG
-------
Three clients defaulted `base_url` to `https://go.tallyfy.com/api` and then
built *some* endpoints as `f"{self.base_url}/api/..."`, appending a second
`/api`. Those requests went to `https://go.tallyfy.com/api/api/...` and 404.

It is provable rather than a judgement call, because both shapes appear in the
same file for the same resource:

    kissflow/src/api/tallyfy_client.py:100
        f"{self.base_url}/organizations/{self.organization_id}"
    kissflow/src/api/tallyfy_client.py:210
        f"{self.base_url}/api/organizations/{self.organization_id}/checklists"

One of those is wrong, and the majority shape is the correct one: 10 endpoints
without the extra `/api` against 2 with it in kissflow, 9 against 2 in monday,
7 against 3 in asana.

WHY IT MATTERED
---------------
The doubled endpoints were not incidental. In all three clients they were
`POST .../checklists` and `POST .../runs` -- template creation and process
launch, the two most important writes a migration performs. Everything else
(members, groups, tags) used the correct shape, so a migration would create
its users and then fail to create a single template.

Found by sweeping the pattern after Cursor Bugbot flagged the same doubling in
rocketlane's .env.example, which is a different instance of the same mistake.
"""

import glob
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CLIENTS = sorted(glob.glob(os.path.join(REPO_ROOT, '*', 'src', 'api', 'tallyfy_client.py')))
IDS = [os.path.relpath(p, REPO_ROOT).split(os.sep)[0] for p in CLIENTS]


def _default_base_url(source):
    match = re.search(r'base_url:\s*str\s*=\s*["\']([^"\']+)', source)
    return match.group(1) if match else None


class TestBaseUrlIsAppliedConsistently:

    @pytest.mark.parametrize('path', CLIENTS, ids=IDS)
    def test_no_endpoint_doubles_the_api_prefix(self, path):
        source = open(path).read()
        default = _default_base_url(source)
        if not default or not default.rstrip('/').endswith('/api'):
            pytest.skip('base_url default does not already end in /api')

        doubled = [
            source.count('\n', 0, m.start()) + 1
            for m in re.finditer(r'\{self\.base_url\}/api/', source)
        ]
        assert not doubled, (
            f'{os.path.relpath(path, REPO_ROOT)} defaults base_url to {default!r}, '
            f'which already ends in /api, and then appends another one at lines '
            f'{doubled}. Those requests go to .../api/api/... and 404.'
        )

    @pytest.mark.parametrize('path', CLIENTS, ids=IDS)
    def test_one_file_does_not_use_both_url_shapes(self, path):
        """Two shapes in one file means one of them is wrong, whatever the default."""
        source = open(path).read()
        with_prefix = len(re.findall(r'\{self\.base_url\}/api/', source))
        without_prefix = len(re.findall(r'\{self\.base_url\}/(?!api/)', source))
        assert not (with_prefix and without_prefix), (
            f'{os.path.relpath(path, REPO_ROOT)} builds {with_prefix} endpoint(s) as '
            f'{{base_url}}/api/... and {without_prefix} as {{base_url}}/... . '
            f'The same client cannot need both.'
        )

    def test_the_check_would_catch_a_reintroduced_double(self):
        """Guard the guard."""
        sample = 'base_url: str = "https://go.tallyfy.com/api"\nf"{self.base_url}/api/runs"\n'
        assert _default_base_url(sample).endswith('/api')
        assert re.search(r'\{self\.base_url\}/api/', sample)
