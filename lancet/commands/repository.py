import click
import github3
from giturlparse import parse as giturlparse
from jinja2 import Template

from ..utils import taskstatus, content_from_path
from ..helpers import get_issue, get_transition, set_issue_status, get_branch


@click.command()
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
        if not assignee or assignee.name != username:
            ts.abort('Issue currently not assigned to you')

        # TODO: Check mergeability

    # TODO: Check remote status (PR does not already exist)

    # Push to remote
    with taskstatus('Pushing to "{}"', remote_name) as ts:
        remote = lancet.repo.lookup_remote(remote_name)
        if not remote:
            ts.abort('Remote "{}" not found', remote_name)

        remote.credentials = lancet.repo.get_credentials_for_remote(remote)
        remote.push(branch.name)

        ts.ok('Pushed latest changes to "{}"', remote_name)

    # Create pull request
    with taskstatus('Creating pull request') as ts:
        p = giturlparse(remote.url)
        gh_repo = lancet.github.repository(p.owner, p.repo)

        template_content = content_from_path(
            lancet.config.get('repository', 'pr_template'))
        template = Template(template_content)
        message_template = template.render(issue=issue)
        message = click.edit(message_template)

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


@click.command()
@click.argument('issue')
@click.pass_obj
def checkout(lancet, issue):
    """
    Checkout the branch for the given issue.

    It is an error if the branch does no exist yet.
    """
    issue = get_issue(lancet, issue)

    # Get the working branch
    branch = get_branch(lancet, issue, create=False)

    with taskstatus('Checking out working branch') as ts:
        lancet.repo.checkout(branch.name)
        ts.ok('Checked out "{}"', branch.name)
