import functools

from html.parser import HTMLParser
from urllib.parse import urljoin, urlencode
import requests


class MetaRetriever(HTMLParser):
    def __init__(self, name, *args, **kwargs):
        self.meta_name = name
        self.meta_content = ''
        kwargs['convert_charrefs'] = True
        super().__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name', None) == self.meta_name:
            self.meta_content = attrs.get('content', '')


def get_meta_content(html, name):
    retriever = MetaRetriever(name)
    retriever.feed(html)
    return retriever.meta_content


def requires_login(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self._login()
        return func(self, *args, **kwargs)
    return wrapper


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
        return self._session.post(urljoin(self.server, url)).json()

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
    platform_url = 'https://platform.harvestapp.com'

    def __init__(self, server, basic_auth, project_id_getter, task_id_getter):
        self._web_session = requests.Session()
        self.get_project_id = project_id_getter
        self.get_task_id = task_id_getter
        self._csrf_token = None
        super().__init__(server, basic_auth)

    def _get_csrf_token(self):
        if not self._csrf_token:
            r = self._web_session.get(urljoin(self.server, '/account/login'))
            self._csrf_token = get_meta_content(r.text, 'csrf-token')
        return self._csrf_token

    def _login(self):
        # TODO: Cache the harvest session across commands invocations
        if '_harvest_sess' in self._web_session.cookies:
            return
        data = {
            'utf8': '✓',
            'authenticity_token': self._get_csrf_token(),
            'user[email]': self.auth[0],
            'user[password]': self.auth[1],
        }
        self._web_session.post(
            urljoin(self.server, '/account/create_session'),
            data=data,
        )
        self._csrf_token = None

    @requires_login
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

        qs = urlencode({
            'app_name': 'JIRA',
            'base_url': issue.permalink(),
            'external_account_id': 1,  # ID of the JIRA instance
            'external_group_id': project.id,
            'external_group_name': project.name,
            'external_item_id': issue.id,
            'external_item_name': name,
            'service': 'divio-ch.atlassian.net',
        })
        data = {
            'utf8': '✓',
            'project_id': project_id,
            'task_id': task_id,
            'notes': name,
            'hours': '',
            'button': '',
        }
        headers = {
            'x-csrf-token': self._get_csrf_token(),
            'x-requested-with': 'XMLHttpRequest',
        }
        r = self._web_session.post(
            urljoin(self.platform_url, '/platform/timer?{}'.format(qs)),
            data=data,
            headers=headers,
        )
        assert r.status_code == 200
        assert 'message' in r.json()

    def close(self):
        self._web_session.close()
        super(HarvestPlatform, self).close()


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

    def __call__(self, timer, issue):
        try:
            return self._project_ids[str(issue.fields.issuetype)]
        except KeyError:
            pass

        try:
            return self._project_ids[None]
        except KeyError:
            pass

        raise ValueError('Could not find a project ID for issue type "{}"'
                         .format(issue.fields.issuetype))


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
        from jira.resources import Issue
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
