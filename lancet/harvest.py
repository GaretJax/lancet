import json
from urllib.parse import urljoin, urlparse

import requests
from jira.resources import Issue


class HarvestError(Exception):
    pass


class HarvestAPI:
    def __init__(self, server, basic_auth):
        self.server = server
        self.auth = basic_auth
        self._projects = None
        self._session = requests.Session()
        self._session.auth = basic_auth
        self._session.headers = {
            'accept': 'application/json'
        }

    def _get(self, url):
        r = self._session.get(urljoin(self.server, url))
        payload = r.json()
        if r.status_code != 200:
            raise HarvestError(payload['message'])
        return payload

    def _post(self, url, data):
        r = self._session.post(
            urljoin(self.server, url),
            data=json.dumps(data),
            headers={
                'content-type': 'application/json',
                'accept': 'application/json',
            },
        )
        payload = r.json()
        if r.status_code not in [200, 201]:
            raise HarvestError(payload['message'])
        return payload

    def toggle(self, id):
        return self._get('daily/timer/{}'.format(id))

    def pause(self, id=None):
        for entry in self.daily():
            if 'timer_started_at' in entry:
                if id is None or id == entry['id']:
                    self.toggle(entry['id'])
                break
        else:
            # No running timers
            pass

    def whoami(self):
        return self._get('account/who_am_i')

    def projects(self):
        if not self._projects:
            self._projects = self._get('daily')['projects']
        return self._projects

    def tasks(self, project_id):
        project_id = int(project_id)
        for project in self.projects():
            if project['id'] == int(project_id):
                return project['tasks']

    def daily(self):
        daily = self._get('daily')
        self._projects = daily['projects']
        return daily['day_entries']

    def close(self):
        self._session.close()


class HarvestPlatform(HarvestAPI):
    def __init__(self, server, basic_auth, project_id_getter, task_id_getter):
        self.get_project_id = project_id_getter
        self.get_task_id = task_id_getter
        super().__init__(server, basic_auth)

    def start(self, issue, resume=True):
        project = issue.fields.project

        if resume:
            for entry in reversed(self.daily()):
                ext = entry.get('external_ref', None)
                if not ext:
                    continue
                if ext['group_id'] != str(project.id):
                    continue
                if ext['id'] != str(issue.id):
                    continue
                if 'timer_started_at' not in entry:
                    self.toggle(entry['id'])
                return

        name = '{} - {}'.format(issue.key, issue.fields.summary)
        project_id = self.get_project_id(self, issue)
        task_id = self.get_task_id(self, project_id, issue)
        permalink = issue.permalink()
        host = urlparse(permalink).hostname

        data = {
            # 'adjustment_record': False,
            # 'created_at': None,
            'external_ref': {
                'group_id': project.id,
                'group_name': project.name,
                'id': issue.id,
                'namespace': permalink,
                'service': host,
                'account_id': 1,
            },
            'hours': 0,
            # 'id': None,
            # 'is_billed': False,
            # 'is_closed': False,
            'notes': name,
            'project_id': project_id,
            # 'spent_at': None,
            # 'started_at': "1:23",
            'task_id': task_id,
            # 'timer_started_at': None,
            # 'updated_at': None,
            # 'user_id': 123456,
        }
        self._post('daily/add', data)


class MappedProjectID:
    def __init__(self, project_ids):
        self._project_ids = project_ids

    @classmethod
    def fromstring(cls, string):
        if not string:
            return cls({})
        project_ids = string.split(',')
        project_ids = (p.split(':') for p in project_ids)
        project_ids = ((None, p[0]) if len(p) == 1 else p for p in project_ids)
        project_ids = ((k, int(v)) for k, v in project_ids if v)
        project_ids = dict(project_ids)
        return cls(project_ids)

    def get_issue_project_id(self, issue):
        return self._project_ids.get(str(issue.fields.issuetype))

    def __call__(self, timer, issue):
        project_id = self.get_issue_project_id(issue)

        # If the issue did not match any explicitly defined project and it is
        # a subtask, get the parent issue
        if not project_id and issue.fields.issuetype.subtask:
            parent = Issue(issue._options, issue._session)
            parent.find(issue.fields.parent.key)
            project_id = self.get_issue_project_id(parent)

        # If no project was found yet, get the default project
        if not project_id:
            project_id = self._project_ids.get(None)

        # At this point, if we didn't get a project, then it's an error
        if not project_id:
            raise ValueError('Could not find a project ID for issue type "{}"'
                             .format(issue.fields.issuetype))

        return project_id


def mapped_project_id_getter(lancet):
    return MappedProjectID.fromstring(
        lancet.config.get('harvest', 'project_id'))


def fixed_task_id_getter(lancet):
    def getter(timer, project_id, issue):
        return int(lancet.config.get('harvest', 'task_id'))
    return getter


class EpicTaskMapper:
    def __init__(self, epic_link_field, epic_name_field):
        self.epic_link_field = epic_link_field
        self.epic_name_field = epic_name_field

    def get_epic(self, issue):
        if issue.fields.issuetype.subtask:
            parent = Issue(issue._options, issue._session)
            parent.find(issue.fields.parent.key)
            issue = parent
        epic = Issue(issue._options, issue._session)
        epic.find(getattr(issue.fields, self.epic_link_field))
        return epic

    def __call__(self, timer, project_id, issue):
        try:
            epic = self.get_epic(issue)
        except:
            raise ValueError('Could not find the epic for task {}'.format(
                issue.key))
        epic_name = getattr(epic.fields, self.epic_name_field)

        for t in timer.tasks(project_id):
            if t['name'] == epic_name:
                return t['id']

        raise ValueError(
            'Could not find a task with the name "{}" in the Harvest project '
            'with ID {}'.format(epic_name, project_id))


def epic_task_id_getter(lancet):
    return EpicTaskMapper(lancet.config.get('harvest', 'epic_link_field'),
                          lancet.config.get('harvest', 'epic_name_field'))


def credentials_checker(url, username, password):
    """Check the provided credentials using the Harvest API."""
    api = HarvestAPI(url, (username, password))
    try:
        api.whoami()
    except HarvestError:
        return False
    else:
        return True


def client_factory(lancet):
    """Construct a new Harvest client."""
    url, username, password = lancet.get_credentials(
        'harvest', credentials_checker)

    project_id_getter = lancet.get_instance_from_config(
        'harvest', 'project_id_getter')
    task_id_getter = lancet.get_instance_from_config(
        'harvest', 'task_id_getter')

    client = HarvestPlatform(
        server=url,
        basic_auth=(username, password),
        project_id_getter=project_id_getter,
        task_id_getter=task_id_getter
    )
    lancet.call_on_close(client.close)
    return client
