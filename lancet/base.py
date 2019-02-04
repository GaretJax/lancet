import shlex
import click
import subprocess

import attr
import keyring
from keyring.backend import KeyringBackend

from .utils import cached_property, taskstatus
from .git import Repository


class NullIntegrationHelper:
    def register(self, *args, **kwargs):
        pass

    def close(self):
        pass


class PasswordstoreKeyring(KeyringBackend):
    priority = 1

    def get_password(self, servicename, username):
        result = subprocess.run(
            ["pass", "show", servicename.rstrip("/")], stdout=subprocess.PIPE
        )
        if result.returncode != 0:
            return None
        password, login, *other = result.stdout.decode("utf-8").split("\n")
        if login != f'login: {username}':
            return None
        return password

    def set_password(self, servicename, username, password):
        subprocess.run(
            ["pass", "insert", "--force", "--multiline", servicename],
            stdout=subprocess.PIPE,
            input=f"{password}\nlogin: {username}".encode("utf-8"),
            check=True,
        )

    def delete_password(self, servicename, username, password):
        pass

# keyring.set_keyring(PasswordstoreKeyring())


class WarnIntegrationHelper(NullIntegrationHelper):
    def __init__(self):
        self._shown = False

    def register(self, *args, **kwargs):
        if not self._shown:
            self._shown = True
            click.secho("")
            click.secho("  Lancet executable called directly", fg="yellow")
            click.secho("  ---------------------------------", fg="yellow")
            click.secho("")
            click.secho("  Setup the shell integration to enjoy some of the")
            click.secho("  super powers we built right into lancet.")
            click.secho("")
            click.secho("  This basically means to add the following snippet")
            click.secho("  to your shell initialization file:")
            click.secho("")
            click.secho("    lancet _setup_helper | source /dev/stdin")
            click.secho("")
            click.secho(
                "  See {} for additional details.".format(
                    click.style("https://lancet.rtd.org", fg="green")
                )
            )
            click.secho("")


class ShellIntegrationHelper(NullIntegrationHelper):
    def __init__(self, filename):
        self.filename = filename
        self.fh = open(filename, "w")

    def register(self, *args, raw=False):
        cmd = args[0] if raw else " ".join(shlex.quote(a) for a in args)
        self.fh.write(cmd)
        self.fh.write("\n")

    def close(self):
        self.fh.close()


@attr.s(frozen=True, cmp=False)
class Lancet:
    config = attr.ib()
    integration_helper = attr.ib()
    call_on_close = attr.ib(default=lambda: None)
    keyring = attr.ib(factory=keyring.get_keyring)

    def defer_to_shell(self, *args, **kwargs):
        return self.integration_helper.register(*args, **kwargs)

    def get_credentials(self, service, checker=None):
        url = self.config.get(service, "url")
        username = self.config.get(service, "username")
        key = "lancet+{}".format(url)
        if username:
            password = self.keyring.get_password(key, username)
            if password:
                return url, username, password

        with taskstatus.suspend():
            while True:
                click.echo(
                    "Please provide your authentication information for {}".format(
                        url
                    )
                )
                if not username:
                    username = click.prompt("Username")
                else:
                    click.echo("Username: {}".format(username))
                password = click.prompt("Password", hide_input=True)

                if checker:
                    with taskstatus("Checking provided credentials") as ts:
                        if not checker(url, username, password):
                            ts.fail("Login failed")
                            username, password = None, None
                            continue
                        else:
                            ts.ok("Correctly authenticated to {}", url)

                self.keyring.set_password(key, username, password)
                return url, username, password

#    def get_issue(self, key=None):
#        # TODO: Move this method to the JIRA class
#
#        if key is None:
#            name_getter = self.get_instance_from_config(
#                "repository", "branch_name_getter"
#            )
#            key = name_getter.get_issue_key(self.repo.head.name)
#        elif key.isdigit():
#            project_key = self.config.get("tracker", "default_project")
#            if project_key:
#                key = "{}-{}".format(project_key, key)
#        return self.tracker.issue(key)

#    @cached_property
#    def remote_repo(self):
#        pass
#
#    @cached_property
#    def github(self):
#        url = self.config.get("github", "url")
#        # TODO: This is only used to create the key, but we shall add support
#        # github enterprise as well
#        key = "lancet+{}".format(url)
#        username = self.config.get("github", "username")
#        token = self.keyring.get_password(key, username)
#
#        if not token:
#
#            def two_factor_callback():
#                with taskstatus.suspend():
#                    return click.prompt("2-factor auth code")
#
#            with taskstatus.suspend():
#                while True:
#                    click.echo(
#                        "Please provide your authentication information for {}".format(
#                            url
#                        )
#                    )
#                    if not username:
#                        username = click.prompt("Username")
#                    else:
#                        click.echo("Username: {}".format(username))
#                    password = click.prompt("Password", hide_input=True)
#
#                    with taskstatus("Getting authorization token") as ts:
#                        scopes = ["user", "repo"]
#                        try:
#                            auth = github3.authorize(
#                                username,
#                                password,
#                                scopes,
#                                "Lancet",
#                                __url__,
#                                two_factor_callback=two_factor_callback,
#                            )
#                        except github3.GitHubError as e:
#                            ts.fail("Login failed ({})", e)
#                            username, password = None, None
#                            continue
#                        else:
#                            ts.ok("New token correctly generated")
#                            break
#
#                token = "{}:{}".format(auth.id, auth.token)
#                self.keyring.set_password(key, username, token)
#
#        id, token = token.split(":", 1)
#        gh = github3.login(token=token)
#        self.call_on_close(gh._session.close)
#        return gh

    def get_config_section(self, key):
        section = self.config.get("lancet", key)
        section = f"{key}:{section}"
        return section

    def get_instance_from_config(self, section, key, *args, **kwargs):
        factory = self.config.getclass(section, key)
        return factory(*args, **kwargs)

    def _load_from_configurable_factory(self, key):
        section = self.get_config_section(key)
        return self.get_instance_from_config(section, "factory", self, section)

    @cached_property
    def repo(self):
        # TODO: Make path more dynamic
        return Repository("./.git")

    @cached_property
    def scm_manager(self):
        return self._load_from_configurable_factory("scm-manager")

    @cached_property
    def tracker(self):
        return self._load_from_configurable_factory("tracker")

    @cached_property
    def timer(self):
        return self._load_from_configurable_factory("timer")
