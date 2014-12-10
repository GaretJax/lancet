import sys
import click

from .settings import load_config
from .git import SlugBranchGetter
from .base import Lancet
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


def get_transition(lancet, issue, to_status):
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
            sys.exit(1)
        elif len(transitions) > 1:
            click.secho(
                'Multiple transitions found from "{}" to "{}", aborting.'
                .format(current_status, to_status),
                fg='red', bold=True
            )
            sys.exit(1)
        else:
            transition_id = transitions[0]
    else:
        transition_id = None
    return transition_id


def assign_issue(lancet, issue, username, active_status=None):
    with taskstatus('Assigning issue to you') as ts:
        if issue.fields.assignee.key != username:
            if issue.fields.status.name == active_status:
                ts.fail('Issue already active and not assigned to you',
                        abort=True)
            else:
                lancet.tracker.assign_issue(issue, username)
                ts.ok('Issue assigned to you')
        else:
            ts.ok('Issue already assigned to you')


def set_issue_status(lancet, issue, to_status, transition):
    with taskstatus(
            'Setting issue status to "{}"'.format(to_status)) as ts:
        if transition is not None:
            lancet.tracker.transition_issue(issue, transition)
            ts.ok('Issue status set to "{}"'.format(to_status))
        else:
            ts.ok('Issue already "{}"'.format(to_status))


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def main(ctx):
    # TODO: Remove me once not needed anymore
    import warnings
    warnings.simplefilter('ignore', ImportWarning, 2150)
    warnings.simplefilter('ignore', ResourceWarning)

    ctx.obj = Lancet(load_config())


@click.command()
@click.option('--base', '-b', 'base_branch')
@click.argument('issue')
@click.pass_obj
def workon(lancet, issue, base_branch):
    username = lancet.config.get('tracker', 'username')
    if not base_branch:
        base_branch = lancet.config.get('repository', 'base_branch')
    active_status = lancet.config.get('tracker', 'active_status')
    branch_getter = SlugBranchGetter(base_branch)

    # Get the issue
    issue = get_issue(lancet, issue)

    # Get the working branch
    branch = branch_getter(lancet.repo, issue)

    # Make sure the issue is in a correct status
    transition = get_transition(lancet, issue, active_status)

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
    Just start a correctly linked Harvest timer for the given issue.
    """
    issue = get_issue(lancet, issue)

    with taskstatus('Starting harvest timer') as ts:
        lancet.timer.start(issue)
        ts.ok('Started harvest timer')

main.add_command(time)


@click.command()
@click.pass_obj
def pause(lancet):
    paused_status = lancet.config.get('tracker', 'paused_status')

    # Get the issue
    issue = get_issue(lancet)

    # Make sure the issue is in a correct status
    transition = get_transition(lancet, issue, paused_status)

    # Activate environment
    set_issue_status(lancet, issue, paused_status, transition)

    with taskstatus('Pausing harvest timer') as ts:
        lancet.timer.pause()
        ts.ok('Harvest timer paused')

main.add_command(pause)


@click.command()
@click.pass_obj
def resume(lancet):
    username = lancet.config.get('tracker', 'username')
    active_status = lancet.config.get('tracker', 'active_status')

    # Get the issue
    issue = get_issue(lancet)

    # Make sure the issue is in a correct status
    transition = get_transition(lancet, issue, active_status)

    # Make sure the issue is assigned to us
    assign_issue(lancet, issue, username, active_status)

    # Activate environment
    set_issue_status(lancet, issue, active_status, transition)

    with taskstatus('Resuming harvest timer') as ts:
        lancet.timer.start(issue)
        ts.ok('Resumed harvest timer')

main.add_command(resume)


@click.command()
@click.pass_obj
def browse(lancet):
    click.launch(lancet.get_issue().permalink())

main.add_command(browse)


# TODO:
# * pullrequest
#     push
#     pull-request
#     update JIRA issue (transition/assign/comment)
#     stop timer
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
