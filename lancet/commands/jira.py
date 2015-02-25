import click

from ..helpers import get_issue


@click.command()
@click.argument('issue', required=False)
@click.pass_obj
def browse(lancet, issue):
    """
    Open the issue tracker page for the given issue in your default browser.

    If no issue is provided, the one linked to the current branch is assumed.
    """
    click.launch(get_issue(lancet, issue).permalink())
