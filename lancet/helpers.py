import click

from .git import BranchGetter
from .utils import taskstatus


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


def set_issue_status(lancet, issue, to_status, transition):
    with taskstatus('Setting issue status to "{}"'.format(to_status)) as ts:
        if transition is not None:
            lancet.tracker.transition_issue(issue, transition)
            ts.ok('Issue status set to "{}"'.format(to_status))
        else:
            ts.ok('Issue already "{}"'.format(to_status))


def assign_issue(lancet, issue, username, active_status=None):
    with taskstatus('Assigning issue to you') as ts:
        assignee = issue.fields.assignee
        if not assignee or assignee.name != username:
            if issue.fields.status.name == active_status:
                ts.abort('Issue already active and not assigned to you')
            else:
                lancet.tracker.assign_issue(issue, username)
                ts.ok('Issue assigned to you')
        else:
            ts.ok('Issue already assigned to you')


def get_branch(lancet, issue, base_branch=None, create=True):
    if not base_branch:
        base_branch = lancet.config.get('repository', 'base_branch')
    remote_name = lancet.config.get('repository', 'remote_name')

    remote = lancet.repo.lookup_remote(remote_name)
    credentials = lancet.repo.get_credentials_for_remote(remote)

    name_getter = lancet.get_instance_from_config(
        'repository', 'branch_name_getter')
    branch_getter = BranchGetter(base_branch, credentials, name_getter,
                                 remote_name)

    return branch_getter(lancet.repo, issue, create=create)
