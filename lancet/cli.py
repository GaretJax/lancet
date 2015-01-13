import os
import re
import glob
import configparser

import click
import github3
import keyring
import pygit2
from giturlparse import parse as giturlparse

from . import __version__
from .settings import load_config, USER_CONFIG, LOCAL_CONFIG, PROJECT_CONFIG
from .git import SlugBranchGetter
from .base import Lancet, WarnIntegrationHelper, ShellIntegrationHelper
from .utils import taskstatus


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def get_issue(lancet, key=None):
    with taskstatus('Looking up issue on the issue tracker') as ts:
        issue = lancet.get_issue(key)
        summary = issue.fields.summary
        crop = len(summary) > 40
        if crop:
            summary = summary[:40] + '...'
        ts.ok('Retrieved issue {}: {}'.format(issue.key, summary))
    return issue


def get_transition(ctx, lancet, issue, to_status):
    current_status = issue.fields.status.name
    if current_status != to_status:
        transitions = [t['id'] for t in lancet.tracker.transitions(issue)
                       if t['to']['name'] == to_status]
        if not transitions:
            click.secho(
                'No transition from "{}" to "{}" found, aborting.'
                .format(current_status, to_status),
                fg='red', bold=True
            )
            ctx.exit(1)
        elif len(transitions) > 1:
            click.secho(
                'Multiple transitions found from "{}" to "{}", aborting.'
                .format(current_status, to_status),
                fg='red', bold=True
            )
            ctx.exit(1)
        else:
            transition_id = transitions[0]
    else:
        transition_id = None
    return transition_id


def assign_issue(lancet, issue, username, active_status=None):
    with taskstatus('Assigning issue to you') as ts:
        assignee = issue.fields.assignee
        if not assignee or assignee.key != username:
            if issue.fields.status.name == active_status:
                ts.abort('Issue already active and not assigned to you')
            else:
                lancet.tracker.assign_issue(issue, username)
                ts.ok('Issue assigned to you')
        else:
            ts.ok('Issue already assigned to you')


def set_issue_status(lancet, issue, to_status, transition):
    with taskstatus('Setting issue status to "{}"'.format(to_status)) as ts:
        if transition is not None:
            lancet.tracker.transition_issue(issue, transition)
            ts.ok('Issue status set to "{}"'.format(to_status))
        else:
            ts.ok('Issue already "{}"'.format(to_status))


def setup_helper(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    base = os.path.abspath(os.path.dirname(__file__))
    helper = os.path.join(base, 'helper.sh')
    with open(helper) as fh:
        click.echo(fh.read())
    ctx.exit()


def get_credentials_for_remote(remote):
    if not remote:
        return
    p = giturlparse(remote.url)
    remote_username = p._user

    if p.protocol == 'ssh':
        credentials = pygit2.KeypairFromAgent(remote_username)
    elif p.protocol == 'https':
        # TODO: What if this fails? (platform, pwd not stored,...)
        try:
            import subprocess
            out = subprocess.check_output([
                'security', 'find-internet-password',
                '-r', 'htps',
                '-s', 'github.com',
            ])
            match = re.search(rb'"acct"<blob>="([0-9a-f]+)"', out)
            token = match.group(1)
        except:
            raise NotImplementedError('No authentication support.')
        credentials = pygit2.UserPass('x-oauth-basic', token)

    return credentials


def get_branch(lancet, issue, base_branch=None, create=True):
    if not base_branch:
        base_branch = lancet.config.get('repository', 'base_branch')
    remote_name = lancet.config.get('repository', 'remote_name')

    remote = lancet.repo.lookup_remote(remote_name)
    credentials = get_credentials_for_remote(remote)

    branch_getter = SlugBranchGetter(base_branch, credentials, remote_name)

    return branch_getter(lancet.repo, issue, create=create)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, message='%(prog)s %(version)s')
@click.option('--setup-helper', callback=setup_helper, is_flag=True,
              expose_value=False, is_eager=True,
              help='Print the shell integration code and exit.')
@click.pass_context
def main(ctx):
    # TODO: Enable this using a command line switch
    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    try:
        integration_helper = ShellIntegrationHelper(
            os.environ['LANCET_SHELL_HELPER'])
    except KeyError:
        integration_helper = WarnIntegrationHelper()

    if os.path.exists(PROJECT_CONFIG):
        config = load_config(PROJECT_CONFIG)
    else:
        config = load_config()

    ctx.obj = Lancet(config, integration_helper)
    ctx.obj.call_on_close = ctx.call_on_close

    ctx.call_on_close(integration_helper.close)


@click.command()
@click.option('-k', '--key', 'method', flag_value='key', default=True)
@click.option('-d', '--dir', 'method', flag_value='dir')
@click.argument('project')
@click.pass_obj
def activate(lancet, method, project):
    """Switch to this project."""
    workspace = os.path.expanduser(lancet.config.get('lancet', 'workspace'))
    project_path = None

    with taskstatus('Looking up project') as ts:
        if method == 'key':
            config_files = glob.glob(
                os.path.join(workspace, '*', LOCAL_CONFIG))

            for path in config_files:
                config = load_config(path)
                key = config.get('tracker', 'default_project', fallback=None)

                if key.lower() == project.lower():
                    project_path = os.path.dirname(path)
        elif method == 'dir':
            project_path = os.path.join(workspace, project)

        if not project_path or not os.path.exists(project_path):
            ts.abort('Project "{}" not found (using {}-based lookup)',
                     project, method)

    # Load the configuration
    config = load_config(os.path.join(project_path, LOCAL_CONFIG))

    # cd to the project directory
    lancet.defer_to_shell('cd', project_path)

    # Activate virtualenv
    venv = config.get('lancet', 'virtualenv', fallback=None)
    if venv:
        venv_path = os.path.join(project_path, os.path.expanduser(venv))
        activate_script = os.path.join(venv_path, 'bin', 'activate')
        lancet.defer_to_shell('source', activate_script)
    else:
        if 'VIRTUAL_ENV' in os.environ:
            lancet.defer_to_shell('deactivate')

main.add_command(activate)


@click.command()
@click.option('--base', '-b', 'base_branch')
@click.argument('issue')
@click.pass_context
def workon(ctx, issue, base_branch):
    """
    Start work on a given issue.

    This command retrieves the issue from the issue tracker, creates and checks
    out a new aptly-named branch, puts the issue in the configured active,
    status, assigns it to you and starts a correctly linked Harvest timer.

    If a branch with the same name as the one to be created already exists, it
    is checked out instead. Variations in the branch name occuring after the
    issue ID are accounted for and the branch renamed to match the new issue
    summary.

    If the `default_project` directive is correctly configured, it is enough to
    give the issue ID (instead of the full project prefix + issue ID).
    """
    lancet = ctx.obj

    username = lancet.config.get('tracker', 'username')
    active_status = lancet.config.get('tracker', 'active_status')
    if not base_branch:
        base_branch = lancet.config.get('repository', 'base_branch')

    # Get the issue
    issue = get_issue(lancet, issue)

    # Get the working branch
    branch = get_branch(lancet, issue, base_branch)

    # Make sure the issue is in a correct status
    transition = get_transition(ctx, lancet, issue, active_status)

    # Make sure the issue is assigned to us
    assign_issue(lancet, issue, username, active_status)

    # Activate environment
    set_issue_status(lancet, issue, active_status, transition)

    with taskstatus('Checking out working branch') as ts:
        lancet.repo.checkout(branch.name)
        ts.ok('Checked out working branch based on "{}"'.format(base_branch))

    with taskstatus('Starting harvest timer') as ts:
        lancet.timer.start(issue)
        ts.ok('Started harvest timer')

main.add_command(workon)


@click.command()
@click.argument('issue')
@click.pass_obj
def time(lancet, issue):
    """
    Start an Harvest timer for the given issue.

    This command takes care of linking the timer with the issue tracker page
    for the given issue.
    """
    issue = get_issue(lancet, issue)

    with taskstatus('Starting harvest timer') as ts:
        lancet.timer.start(issue)
        ts.ok('Started harvest timer')

main.add_command(time)


@click.command()
@click.pass_context
def pause(ctx):
    """
    Pause work on the current issue.

    This command puts the issue in the configured paused status and stops the
    current Harvest timer.
    """
    lancet = ctx.obj
    paused_status = lancet.config.get('tracker', 'paused_status')

    # Get the issue
    issue = get_issue(lancet)

    # Make sure the issue is in a correct status
    transition = get_transition(ctx, lancet, issue, paused_status)

    # Activate environment
    set_issue_status(lancet, issue, paused_status, transition)

    with taskstatus('Pausing harvest timer') as ts:
        lancet.timer.pause()
        ts.ok('Harvest timer paused')

main.add_command(pause)


@click.command()
@click.pass_context
def resume(ctx):
    """
    Resume work on the currently active issue.

    The issue is retrieved from the currently active branch name.
    """
    lancet = ctx.obj

    username = lancet.config.get('tracker', 'username')
    active_status = lancet.config.get('tracker', 'active_status')

    # Get the issue
    issue = get_issue(lancet)

    # Make sure the issue is in a correct status
    transition = get_transition(ctx, lancet, issue, active_status)

    # Make sure the issue is assigned to us
    assign_issue(lancet, issue, username, active_status)

    # Activate environment
    set_issue_status(lancet, issue, active_status, transition)

    with taskstatus('Resuming harvest timer') as ts:
        lancet.timer.start(issue)
        ts.ok('Resumed harvest timer')

main.add_command(resume)


@click.command(name='pr')
@click.option('--base', '-b', 'base_branch')
@click.option('-o', '--open-pr/--no-open-pr', default=False)
@click.pass_context
def pull_request(ctx, base_branch, open_pr):
    """Create a new pull request for this issue."""
    lancet = ctx.obj

    username = lancet.config.get('tracker', 'username')
    review_status = lancet.config.get('tracker', 'review_status')
    remote_name = lancet.config.get('repository', 'remote_name')

    if not base_branch:
        base_branch = lancet.config.get('repository', 'base_branch')

    # Get the issue
    issue = get_issue(lancet)

    transition = get_transition(ctx, lancet, issue, review_status)

    # Get the working branch
    branch = get_branch(lancet, issue, create=False)

    with taskstatus('Checking pre-requisites') as ts:
        if not branch:
            ts.abort('No working branch found')

        assignee = issue.fields.assignee
        if not assignee or assignee.key != username:
            ts.abort('Issue currently not assigned to you')

        # TODO: Check mergeability

    # TODO: Check remote status (PR does not already exist)

    # Push to remote
    with taskstatus('Pushing to "{}"', remote_name) as ts:
        remote = lancet.repo.lookup_remote(remote_name)
        if not remote:
            ts.abort('Remote "{}" not found', remote_name)

        remote.credentials = get_credentials_for_remote(remote)
        remote.push(branch.name)

        ts.ok('Pushed latest changes to "{}"', remote_name)

    # Create pull request
    with taskstatus('Creating pull request') as ts:
        p = giturlparse(remote.url)
        gh_repo = lancet.github.repository(p.owner, p.repo)

        message = click.edit("{} – {}\n\n{}".format(
            issue.key, issue.fields.summary, issue.permalink()))

        if not message:
            ts.abort('You didn\'t provide a title for the pull request')

        title, body = message.split('\n', 1)
        title = title.strip()

        if not title:
            ts.abort('You didn\'t provide a title for the pull request')

        try:
            pr = gh_repo.create_pull(title, base_branch, branch.branch_name,
                                     body.strip('\n'))
        except github3.GitHubError as e:
            if len(e.errors) == 1:
                error = e.errors[0]
                if 'pull request already exists' in error['message']:
                    ts.ok('Pull request does already exist')
                else:
                    ts.abort('Could not create pull request ({})',
                             error['message'])
            else:
                raise
        else:
            ts.ok('Pull request created at {}', pr.html_url)

    # Update issue
    set_issue_status(lancet, issue, review_status, transition)

    # TODO: Post to activity stream on JIRA
    # TODO: Post to HipChat?

    # Stop harvest timer
    with taskstatus('Pausing harvest timer') as ts:
        lancet.timer.pause()
        ts.ok('Harvest timer paused')

    # Open the pull request page in the browser if requested
    if open_pr:
        click.launch(pr.html_url)

main.add_command(pull_request)


@click.command()
@click.argument('issue', required=False)
@click.pass_obj
def browse(lancet, issue):
    """
    Open the issue tracker page for the given issue in your default browser.

    If no issue is provided, the one linked to the current branch is assumed.
    """
    click.launch(get_issue(lancet, issue).permalink())

main.add_command(browse)


@click.command()
@click.option('-f', '--force/--no-force', default=False)
@click.pass_context
def setup(ctx, force):
    """Wizard to create the user-level configuration file."""
    if os.path.exists(USER_CONFIG) and not force:
        click.secho(
            'An existing configuration file was found at "{}".\n'
            .format(USER_CONFIG),
            fg='red', bold=True
        )
        click.secho(
            'Please remove it before in order to run the setup wizard or use\n'
            'the --force flag to overwrite it.'
        )
        ctx.exit(1)

    tracker_url = click.prompt('URL of the issue tracker')
    tracker_user = click.prompt('Username for {}'.format(tracker_url))
    timer_url = click.prompt('URL of the time tracker')
    timer_user = click.prompt('Username for {}'.format(timer_url))

    config = configparser.ConfigParser()

    config.add_section('tracker')
    config.set('tracker', 'url', tracker_url)
    config.set('tracker', 'username', tracker_user)

    config.add_section('harvest')
    config.set('harvest', 'url', timer_url)
    config.set('harvest', 'username', timer_user)

    with open(USER_CONFIG, 'w') as fh:
        config.write(fh)

    click.secho('\nConfiguration correctly written to "{}".'
                .format(USER_CONFIG), fg='green')

    # TODO: Add wizard to setup shell integration

main.add_command(setup)


@click.command()
@click.option('-f', '--force/--no-force', default=False)
@click.pass_context
def init(ctx, force):
    """Wizard to create a project-level configuration file."""
    if os.path.exists(PROJECT_CONFIG) and not force:
        click.secho(
            'An existing configuration file was found at "{}".\n'
            .format(PROJECT_CONFIG),
            fg='red', bold=True
        )
        click.secho(
            'Please remove it before in order to run the setup wizard or use\n'
            'the --force flag to overwrite it.'
        )
        ctx.exit(1)

    project_key = click.prompt('Project key on the issue tracker')
    base_branch = click.prompt('Integration branch', default='master')

    virtualenvs = ('.venv', '.env', 'venv', 'env')
    for p in virtualenvs:
        if os.path.exists(os.path.join(p, 'bin', 'activate')):
            venv = p
            break
    else:
        venv = ''
    venv_path = click.prompt('Path to virtual environment', default=venv)

    project_id = click.prompt('Project ID on Harvest', type=int)
    task_id = click.prompt('Task id on Harvest', type=int)

    config = configparser.ConfigParser()

    config.add_section('lancet')
    config.set('lancet', 'virtualenv', venv_path)

    config.add_section('tracker')
    config.set('tracker', 'default_project', project_key)

    config.add_section('harvest')
    config.set('harvest', 'project_id', str(project_id))
    config.set('harvest', 'task_id', str(task_id))

    config.add_section('repository')
    config.set('repository', 'base_branch', base_branch)

    with open(PROJECT_CONFIG, 'w') as fh:
        config.write(fh)

    click.secho('\nConfiguration correctly written to "{}".'
                .format(PROJECT_CONFIG), fg='green')

main.add_command(init)


@click.command()
@click.argument('service', required=False)
@click.pass_obj
def logout(lancet, service):
    """Forget saved passwords for the web services."""
    if service:
        services = [service]
    else:
        services = ['tracker', 'harvest']

    for service in services:
        url = lancet.config.get(service, 'url')
        key = 'lancet+{}'.format(url)
        username = lancet.config.get(service, 'username')
        with taskstatus('Logging out from {}', url) as ts:
            if keyring.get_password(key, username):
                keyring.delete_password(key, username)
                ts.ok('Logged out from {}', url)
            else:
                ts.ok('Already logged out from {}', url)

main.add_command(logout)


@click.command(name='harvest-projects')
@click.argument('query', required=False)
@click.pass_obj
def harvest_projects(lancet, query):
    """List Harvest projects, optionally filtered with a regexp."""
    projects = lancet.timer.projects()

    if query:
        regexp = re.compile(query, flags=re.IGNORECASE)

        def match(project):
            match = regexp.search(project['name'])
            if match is None:
                return False
            project['match'] = match
            return True
        projects = (p for p in projects if match(p))

    for project in sorted(projects, key=lambda p: p['name'].lower()):
        name = project['name']

        if 'match' in project:
            m = project['match']
            s, e = m.start(), m.end()
            match = click.style(name[s:e], fg='green')
            name = name[:s] + match + name[e:]

        click.echo('{:>9d} {} {}'.format(
            project['id'], click.style('‣', fg='yellow'), name))

main.add_command(harvest_projects)


@click.command(name='harvest-tasks')
@click.argument('project_id', type=int)
@click.pass_obj
def harvest_tasks(lancet, project_id):
    """List Harvest tasks for the given project ID."""
    projects = lancet.timer.projects()

    for project in projects:
        if project['id'] == project_id:
            click.echo('{:>9d} {} {}'.format(
                project['id'], click.style('‣', fg='yellow'), project['name']))
            click.echo('─' * click.get_terminal_size()[0])

            for task in project['tasks']:
                click.echo('{:>9d} {} {}'.format(
                    task['id'], click.style('‣', fg='yellow'), task['name']))
            break

main.add_command(harvest_tasks)


# TODO:
# * review
#     pull
#     ci-status
#     pep8
#     diff
#     mergeability (rebase is of the submitter responsibility)
# * merge
#     pull, merge, delete
# * issues
#     list all open/assigned issues (or by filter)
# * comment
#     adds a comment to the currently active issue
