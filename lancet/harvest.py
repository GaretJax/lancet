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

    def _get(self, url):
        r = requests.get(urljoin(self.server, url), auth=self.auth,
                         headers={'accept': 'application/json'})
        payload = r.json()
        if r.status_code != 200:
            raise HarvestError(payload['message'])
        return payload

    def _post(self, url, data):
        return requests.post(urljoin(self.server, url), auth=self.auth,
                             headers={'accept': 'application/json'}).json()

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

    def daily(self):
        return self._get('daily')['day_entries']


class HarvestPlatform(HarvestAPI):
    platform_url = 'https://platform.harvestapp.com'

    def __init__(self, server, basic_auth, project_id_getter, task_id):
        self.session = requests.Session()
        self.task_id = task_id
        self.get_project_id = project_id_getter
        self._csrf_token = None
        super().__init__(server, basic_auth)

    def _get_csrf_token(self):
        if not self._csrf_token:
            r = self.session.get(urljoin(self.server, '/account/login'))
            self._csrf_token = get_meta_content(r.text, 'csrf-token')
        return self._csrf_token

    def _login(self):
        # TODO: Cache the harvest session across commands invocations
        if '_harvest_sess' in self.session.cookies:
            return
        data = {
            'utf8': '✓',
            'authenticity_token': self._get_csrf_token(),
            'user[email]': self.auth[0],
            'user[password]': self.auth[1],
        }
        self.session.post(
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
            'project_id': self.get_project_id(issue),
            'task_id': self.task_id,
            'notes': name,
            'hours': '',
            'button': '',
        }
        headers = {
            'x-csrf-token': self._get_csrf_token(),
            'x-requested-with': 'XMLHttpRequest',
        }
        r = self.session.post(
            urljoin(self.platform_url, '/platform/timer?{}'.format(qs)),
            data=data,
            headers=headers,
        )
        assert r.status_code == 200
        assert 'message' in r.json()
