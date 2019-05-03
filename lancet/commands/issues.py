import click

from ..helpers import get_issue, assign_issue, create_issue


@click.command()
@click.argument("issue", required=False)
@click.pass_obj
def browse(lancet, issue):
    """
    Open the issue tracker page for the given issue in your default browser.

    If no issue is provided, the one linked to the current branch is assumed.
    """
    click.launch(get_issue(lancet, issue).permalink())


@click.group()
def issue():
    """
    Utilities to manage issues.
    """
    pass


@issue.command(name="add")
@click.pass_obj
@click.option("--assign", "-a")
@click.option("-s", "--add-to-sprint/--no-add-to-sprint")
@click.argument("summary", nargs=-1)
def issue_add(lancet, assign, add_to_sprint, summary):
    """
    Create a new issue on the issue tracker.
    """
    summary = " ".join(summary)
    issue = create_issue(
        lancet,
        summary,
        # project_id=project_id,
        add_to_active_sprint=add_to_sprint,
    )
    if assign:
        if assign == "me":
            username = lancet.tracker.whoami()
        else:
            username = assign
        assign_issue(lancet, issue, username)
