import re
import shlex
import click

import keyring
import github3

from . import __url__
from .jira import JIRA, JIRAError
from .harvest import HarvestPlatform, HarvestAPI, HarvestError
from .utils import cached_property, taskstatus
from .git import Repository


class MappedProjectID:
    def __init__(self, project_ids):
        self._project_ids = project_ids

    @classmethod
    def fromstring(cls, string):
        project_ids = string.split(',')
        project_ids = (p.split(':') for p in project_ids)
        project_ids = ((None, p) if len(p) == 1 else p for p in project_ids)
        project_ids = dict(project_ids)
        return cls(project_ids)

    def __call__(self, issue):
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


class NullIntegrationHelper:
    def register(self, *args, **kwargs):
        pass

    def close(self):
        pass


class WarnIntegrationHelper(NullIntegrationHelper):
    def __init__(self):
        self._shown = False

    def register(self, *args, **kwargs):
        if not self._shown:
            self._shown = True
            click.secho('')
            click.secho('  Lancet executable called directly', fg='yellow')
            click.secho('  ---------------------------------', fg='yellow')
            click.secho('')
            click.secho('  Setup the shell integration to enjoy some of the')
            click.secho('  super powers we built right into lancet.')
            click.secho('')
            click.secho('  This basically means to add the following snippet')
            click.secho('  to your shell initialization file:')
            click.secho('')
            click.secho('    lancet --setup-helper | source /dev/stdin')
            click.secho('')
            click.secho('  See {} for addtional details.'.format(
                click.style('https://lancet.rtd.org', fg='green')))
            click.secho('')


class ShellIntegrationHelper(NullIntegrationHelper):
    def __init__(self, filename):
        self.filename = filename
        self.fh = open(filename, 'w')

    def register(self, *args, raw=False):
        cmd = args[0] if raw else ' '.join(shlex.quote(a) for a in args)
        self.fh.write(cmd)
        self.fh.write('\n')

    def close(self):
        self.fh.close()


class Lancet:
    def __init__(self, config, integration_helper):
        self.config = config
        self.integration_helper = integration_helper

    def defer_to_shell(self, *args, **kwargs):
        return self.integration_helper.register(*args, **kwargs)

    def get_credentials(self, service, checker=None):
        url = self.config.get(service, 'url')
        username = self.config.get(service, 'username')
        key = 'lancet+{}'.format(url)
        if username:
            password = keyring.get_password(key, username)
            if password:
                return url, username, password

        with taskstatus.suspend():
            while True:
                click.echo(
                    'Please provide your authentication information for {}'
                    .format(url)
                )
                if not username:
                    username = click.prompt('Username')
                else:
                    click.echo('Username: {}'.format(username))
                password = click.prompt('Password', hide_input=True)

                if checker:
                    with taskstatus('Checking provided credentials') as ts:
                        if not checker(url, username, password):
                            ts.fail('Login failed')
                            username, password = None, None
                            continue
                        else:
                            ts.ok('Correctly authenticated to {}', url)

                keyring.set_password(key, username, password)
                return url, username, password

    def get_issue(self, key=None):
        # TODO: Move this method to the JIRA class

        if key is None:
            # TODO: This should be factored out of here
            match = re.search(r'feature/([A-Z]{2,}-[0-9]+)',
                              self.repo.head.name)
            if match is None:
                raise Exception('Unable to find current issue.')
            key = match.group(1)
        elif key.isdigit():
            project_key = self.config.get('tracker', 'default_project')
            if project_key:
                key = '{}-{}'.format(project_key, key)
        return self.tracker.issue(key)

    @cached_property
    def repo(self):
        # Can be cleared like this: self.__class__.repo.fget.cache_clear()
        return Repository('./.git')

    @cached_property
    def github(self):
        url = self.config.get('github', 'url')
        # TODO: This is only used to create the key, but we shall add support
        # github enterprise as well
        key = 'lancet+{}'.format(url)
        username = self.config.get('github', 'username')
        token = keyring.get_password(key, username)

        if not token:
            def two_factor_callback():
                with taskstatus.suspend():
                    return click.prompt('2-factor auth code')

            with taskstatus.suspend():
                while True:
                    click.echo(
                        'Please provide your authentication information for {}'
                        .format(url)
                    )
                    if not username:
                        username = click.prompt('Username')
                    else:
                        click.echo('Username: {}'.format(username))
                    password = click.prompt('Password', hide_input=True)

                    with taskstatus('Getting authorization token') as ts:
                        scopes = ['user', 'repo']
                        try:
                            auth = github3.authorize(
                                username, password, scopes, 'Lancet', __url__,
                                two_factor_callback=two_factor_callback
                            )
                        except github3.GitHubError as e:
                            ts.fail('Login failed ({})', e)
                            username, password = None, None
                            continue
                        else:
                            ts.ok('New token correctly generated')
                            break

                token = '{}:{}'.format(auth.id, auth.token)
                keyring.set_password(key, username, token)

        id, token = token.split(':', 1)
        gh = github3.login(token=token)
        self.call_on_close(gh._session.close)
        return gh

    @cached_property
    def tracker(self):
        def checker(url, username, password):
            try:
                JIRA(server=url, basic_auth=(username, password))
            except JIRAError:
                return False
            else:
                return True

        url, username, password = self.get_credentials('tracker', checker)
        tracker = JIRA(server=url, basic_auth=(username, password))
        self.call_on_close(tracker.close)
        return tracker

    @cached_property
    def timer(self):
        def checker(url, username, password):
            api = HarvestAPI(url, (username, password))
            try:
                api.whoami()
            except HarvestError:
                return False
            else:
                return True

        url, username, password = self.get_credentials('harvest', checker)
        task_id = self.config.get('harvest', 'task_id')
        project_id_getter = MappedProjectID.fromstring(
            self.config.get('harvest', 'project_id'))
        timer = HarvestPlatform(server=url,
                                basic_auth=(username, password),
                                project_id_getter=project_id_getter,
                                task_id=task_id)
        self.call_on_close(timer.close)
        return timer
