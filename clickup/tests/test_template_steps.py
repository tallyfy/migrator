"""A ClickUp list's statuses must reach the template transformer as steps.

main.py turns each ClickUp list into a template, but the dict it built carried only
name, description, folder_id, space_id, statuses, priority and due_date, while the
template transformer reads 'steps' or 'tasks'. Every migrated template came out
with no steps at all (tallyfy/migrator#30, item 19).

A list's statuses are the stages its tasks move through, so each one becomes a
step. Get Lists and Get Folderless Lists leave statuses out of each list, and only
Get List returns them, so discovery has to fetch them too.

This drives main.py's own discovery, mapping and transformation phases through a
real ClickUpClient whose HTTP layer answers with payloads shaped like ClickUp's API
v2 reference, so it fails if main.py, the client or the transformer drifts.
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import main  # noqa: E402


WORKSPACE_ID = '9012345'
SPACE = {'id': '90120001', 'name': 'Client Services', 'access': True}

ONBOARDING_STATUSES = [
    {'status': 'to do', 'orderindex': 0, 'color': '#87909e', 'type': 'open'},
    {'status': 'kickoff call', 'orderindex': 1, 'color': '#5f55ee', 'type': 'custom'},
    {'status': 'collect documents', 'orderindex': 2, 'color': '#1090e0', 'type': 'custom'},
    {'status': 'account setup', 'orderindex': 3, 'color': '#e16b16', 'type': 'custom'},
    {'status': 'complete', 'orderindex': 4, 'color': '#008844', 'type': 'closed'},
]

REQUEST_STATUSES = [
    {'status': 'to do', 'orderindex': 0, 'color': '#d3d3d3', 'type': 'open'},
    {'status': 'in progress', 'orderindex': 1, 'color': '#4194f6', 'type': 'custom'},
    {'status': 'complete', 'orderindex': 2, 'color': '#6bc950', 'type': 'closed'},
]

# Each list as Get Lists (GET /folder/{id}/list) and Get Folderless Lists
# (GET /space/{id}/list) return it: no 'statuses' key.
ONBOARDING_LIST = {
    'id': '901500123456',
    'name': 'Client onboarding',
    'orderindex': 0,
    'content': 'Every new retainer client goes through this list.',
    'status': None,
    'priority': None,
    'assignee': None,
    'task_count': 1,
    'due_date': None,
    'start_date': None,
    'folder': {'id': '90150002', 'name': 'Accounts', 'hidden': False, 'access': True},
    'space': SPACE,
    'archived': False,
    'override_statuses': True,
    'permission_level': 'create',
}

REQUEST_LIST = {
    'id': '901500654321',
    'name': 'Change requests',
    'orderindex': 1,
    'content': '',
    'status': None,
    'priority': {'priority': 'high', 'color': '#f50000'},
    'assignee': None,
    'task_count': 1,
    'due_date': None,
    'start_date': None,
    'folder': {'id': '90150003', 'name': 'hidden', 'hidden': True, 'access': True},
    'space': SPACE,
    'archived': False,
    'override_statuses': False,
    'permission_level': 'create',
}


def _list_details(summary, statuses):
    """The same list as Get List (GET /list/{id}) returns it, statuses included."""
    details = dict(summary)
    details.update({
        'due_date_time': False,
        'start_date_time': None,
        'inbound_address': 'add.task.%s.ac725f@tasks.clickup.com' % summary['id'],
        'statuses': statuses,
    })
    return details


def _task(task_id, name, summary, status):
    """A task as Get Tasks (GET /list/{id}/task) returns it."""
    return {
        'id': task_id,
        'custom_id': None,
        'name': name,
        'text_content': '',
        'description': '',
        'status': dict(status, id='sc%s_%d' % (summary['id'], status['orderindex'])),
        'orderindex': '1.00000000000000000000000000000000',
        'date_created': '1760000000000',
        'date_updated': '1762000000000',
        'date_closed': None,
        'date_done': None,
        'archived': False,
        'creator': {
            'id': 183,
            'username': 'Dana Ruiz',
            'color': '#827718',
            'email': 'dana@example.com',
            'profilePicture': None,
        },
        'assignees': [],
        'watchers': [],
        'checklists': [],
        'tags': [],
        'parent': None,
        'priority': None,
        'due_date': None,
        'start_date': None,
        'points': None,
        'time_estimate': None,
        'custom_fields': [],
        'dependencies': [],
        'linked_tasks': [],
        'team_id': WORKSPACE_ID,
        'url': 'https://app.clickup.com/t/%s' % task_id,
        'permission_level': 'create',
        'list': {'id': summary['id'], 'name': summary['name'], 'access': True},
        'folder': {'id': summary['folder']['id'], 'name': summary['folder']['name'],
                   'hidden': summary['folder']['hidden'], 'access': True},
        'space': {'id': SPACE['id']},
    }


ONBOARDING_TASK = _task('86b1abcd1', 'Harbor Dental retainer', ONBOARDING_LIST,
                        ONBOARDING_STATUSES[1])
REQUEST_TASK = _task('86b1abcd2', 'Swap the invoice logo', REQUEST_LIST,
                     REQUEST_STATUSES[1])

# Endpoint -> response body, for every request discovery makes that exists in
# ClickUp's API v2 reference.
RESPONSES = {
    '/team': {'teams': [{'id': WORKSPACE_ID, 'name': 'Northwind Studio',
                         'color': '#536cfe', 'avatar': None, 'members': []}]},
    '/team/%s/space' % WORKSPACE_ID: {'spaces': [dict(
        SPACE, private=False, statuses=REQUEST_STATUSES, multiple_assignees=True,
        archived=False)]},
    '/space/%s/folder' % SPACE['id']: {'folders': [{
        'id': '90150002', 'name': 'Accounts', 'orderindex': 0,
        'override_statuses': True, 'hidden': False, 'space': SPACE,
        'task_count': '1', 'archived': False, 'statuses': [], 'lists': [],
        'permission_level': 'create'}]},
    '/folder/90150002/list': {'lists': [ONBOARDING_LIST]},
    '/space/%s/list' % SPACE['id']: {'lists': [REQUEST_LIST]},
    '/list/%s' % ONBOARDING_LIST['id']: _list_details(ONBOARDING_LIST, ONBOARDING_STATUSES),
    '/list/%s' % REQUEST_LIST['id']: _list_details(REQUEST_LIST, REQUEST_STATUSES),
    '/list/%s/task' % ONBOARDING_LIST['id']: {'tasks': [ONBOARDING_TASK], 'last_page': True},
    '/list/%s/task' % REQUEST_LIST['id']: {'tasks': [REQUEST_TASK], 'last_page': True},
}


def _clickup_client(requests_made):
    """A real ClickUpClient whose HTTP layer answers from RESPONSES."""
    client = main.ClickUpClient(api_key='not-a-real-token', workspace_id=WORKSPACE_ID)

    def make_request(method, endpoint, **kwargs):
        requests_made.append((method, endpoint))
        if method != 'GET' or endpoint not in RESPONSES:
            raise AssertionError('unexpected request: %s %s' % (method, endpoint))
        return RESPONSES[endpoint]

    client._make_request = make_request
    # Two discovery calls cannot work against the real API and are not what this
    # test is about, so they answer empty here. get_views is defined on no
    # ClickUpClient (a known ghost method, #30 item 1), and get_users asks for
    # GET /team/{id}/user, which the API v2 reference does not list.
    client.get_views = lambda *args, **kwargs: []
    client.get_users = lambda: []
    return client


def _orchestrator(clickup_client):
    """The components main.py's _initialize_components wires, with no Tallyfy client."""
    field_transformer = main.FieldTransformer()
    template_transformer = main.TemplateTransformer()
    template_transformer.field_transformer = field_transformer
    return types.SimpleNamespace(
        clickup_client=clickup_client,
        field_transformer=field_transformer,
        template_transformer=template_transformer,
        instance_transformer=main.InstanceTransformer(),
        user_transformer=main.UserTransformer(),
    )


class TestListStatusesBecomeSteps(unittest.TestCase):

    def setUp(self):
        self.requests_made = []
        orchestrator = _orchestrator(_clickup_client(self.requests_made))
        cls = main.ClickUpMigrationOrchestrator
        self.discovery = cls._run_discovery_phase(orchestrator)
        mapping = cls._run_mapping_phase(orchestrator, self.discovery)
        self.result = cls._run_transformation_phase(orchestrator, self.discovery, mapping)
        self.templates = {t['name']: t for t in self.result['templates']}

    def test_discovery_reads_each_lists_statuses_from_get_list(self):
        for list_id in (ONBOARDING_LIST['id'], REQUEST_LIST['id']):
            self.assertIn(('GET', '/list/%s' % list_id), self.requests_made)
        self.assertEqual(
            {lst['id']: lst.get('statuses') for lst in self.discovery['lists']},
            {
                ONBOARDING_LIST['id']: ONBOARDING_STATUSES,
                REQUEST_LIST['id']: REQUEST_STATUSES,
            },
        )

    def test_every_status_becomes_a_step_in_order(self):
        self.assertEqual(sorted(self.templates), ['Change requests', 'Client onboarding'])
        self.assertEqual(
            [s['name'] for s in self.templates['Client onboarding']['steps']],
            ['to do', 'kickoff call', 'collect documents', 'account setup', 'complete'],
        )
        self.assertEqual(
            [s['name'] for s in self.templates['Change requests']['steps']],
            ['to do', 'in progress', 'complete'],
        )

    def test_steps_are_tasks_with_no_invented_detail(self):
        steps = [s for t in self.result['templates'] for s in t['steps']]
        self.assertEqual(len(steps), len(ONBOARDING_STATUSES) + len(REQUEST_STATUSES))
        for step in steps:
            self.assertEqual(step['type'], 'task')
            self.assertEqual(step['description'], '')
            self.assertEqual(step['fields'], [])
            self.assertIsNone(step['assignee'])
            self.assertIsNone(step['due_date'])

    def test_template_is_not_the_fallback(self):
        onboarding = self.templates['Client onboarding']
        self.assertEqual(
            onboarding['description'],
            'Every new retainer client goes through this list.',
        )
        self.assertEqual(onboarding['vendor_metadata']['original_data']['space_id'], SPACE['id'])

    def test_tasks_stay_instances_and_are_not_steps(self):
        self.assertEqual(
            sorted(i['name'] for i in self.result['instances']),
            ['Harbor Dental retainer', 'Swap the invoice logo'],
        )
        step_names = {s['name'] for t in self.result['templates'] for s in t['steps']}
        self.assertFalse(step_names & {ONBOARDING_TASK['name'], REQUEST_TASK['name']})


if __name__ == '__main__':
    unittest.main()
