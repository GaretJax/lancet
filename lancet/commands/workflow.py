import os
import glob

import click

from ..settings import LOCAL_CONFIG, load_config
from ..utils import taskstatus
from ..helpers import get_issue, get_transition, set_issue_status, assign_issue
from ..helpers import get_branch


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
