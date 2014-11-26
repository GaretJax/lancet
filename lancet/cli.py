import sys
import click

from .settings import load_config
from .git import SlugBranchGetter
from .base import Lancet
from .utils import taskstatus


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


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
    with taskstatus('Looking up issue on the issue tracker') as ts:
        issue = lancet.get_issue(issue)
        summary = issue.fields.summary
        crop = len(summary) > 40
        if crop:
            summary = summary[:40] + '...'
        ts.ok('Retrieved issue {}: {}'.format(issue.key, summary))

    # Get the working branch
    branch = branch_getter(lancet.repo, issue)

    # Make sure the issue is in a correct status
    current_status = issue.fields.status.name
    if current_status != active_status:
        transitions = [t['id'] for t in lancet.tracker.transitions(issue)
                       if t['to']['name'] == active_status]
        if not transitions:
            click.secho(
                'No transition from "{}" to "{}" found, aborting.'
                .format(current_status, active_status),
                fg='red', bold=True
            )
            sys.exit(1)
        elif len(transitions) > 1:
            click.secho(
                'Multiple transitions found from "{}" to "{}", aborting.'
                .format(current_status, active_status),
                fg='red', bold=True
            )
            sys.exit(1)
        else:
            transition_id = transitions[0]
    else:
        transition_id = None

    # Make sure the issue is assigned to us
    with taskstatus('Assigning issue to you') as ts:
        if issue.fields.assignee.key != username:
            if current_status == active_status:
                ts.fail('Issue already active and not assigned to you',
                        abort=True)
            else:
                lancet.tracker.assign_issue(issue, username)
                ts.ok('Issue assigned to you')
        else:
            ts.ok('Issue already assigned to you')

    # Activate environment
    with taskstatus(
            'Setting issue status to "{}"'.format(active_status)) as ts:
        if transition_id is not None:
            lancet.tracker.transition_issue(issue, transitions[0])
            ts.ok('Issue status set to "{}"'.format(active_status))
        else:
            ts.ok('Issue already in the correct status')

    with taskstatus('Checking out working branch') as ts:
        lancet.repo.checkout(branch.name)
        ts.ok('Checked out working branch based on "{}"'.format(base_branch))

    with taskstatus('Starting harvest timer') as ts:
        lancet.timer.start(issue)
        ts.ok('Started harvest timer')

main.add_command(workon)


@click.command()
@click.pass_obj
def pause(lancet):
    with taskstatus('Putting issue on hold') as ts:
        ts.fail('Putting issue on hold not implemented yet')
    with taskstatus('Pausing harvest timer') as ts:
        lancet.timer.pause()
        ts.ok('Harvest timer paused')
main.add_command(pause)


@click.command()
@click.pass_obj
def resume(lancet):
    pass


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
