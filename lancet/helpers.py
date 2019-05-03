import os
import glob

import click

from .settings import LOCAL_CONFIG, load_config
from .git import BranchGetter
from .utils import taskstatus


def get_issue(lancet, issue_id=None):
    with taskstatus("Looking up issue on the issue tracker") as ts:
        project_id = lancet.config.get("tracker", "project_id")
        if issue_id is None:
            name_getter = lancet.get_instance_from_config(
                "repository", "branch_name_getter", lancet
            )
            issue_id = name_getter.get_issue_key(lancet.repo.head.name)
        issue = lancet.tracker.get_issue(project_id, issue_id)
        summary = issue.summary
        if len(summary) > 40:
            summary = summary[:40] + "..."
        ts.ok("Retrieved issue {}: {}".format(issue.id, summary))
    return issue


def get_transition(ctx, lancet, issue, to_status):
    current_status = issue.status
    if current_status != to_status:
        transitions = issue.get_transitions(to_status)
        if not transitions:
            click.secho(
                'No transition from "{}" to "{}" found, aborting.'.format(
                    current_status, to_status
                ),
                fg="red",
                bold=True,
            )
            ctx.exit(1)
        elif len(transitions) > 1:
            click.secho(
                'Multiple transitions found from "{}" to "{}", aborting.'.format(
                    current_status, to_status
                ),
                fg="red",
                bold=True,
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
            issue.apply_transition(transition)
            ts.ok('Issue status set to "{}"'.format(to_status))
        else:
            ts.ok('Issue already "{}"'.format(to_status))


def create_issue(
    lancet, summary, *, project_id=None, add_to_active_sprint=False
):
    with taskstatus("Creating issue") as ts:
        if project_id is None:
            project_id = lancet.config.get("tracker", "project_id")
        issue = lancet.tracker.create_issue(
            project_id=project_id,
            summary=summary,
            add_to_active_sprint=add_to_active_sprint,
        )
        ts.ok(f"Created issue {issue.id}: {issue.link}")
    return issue


def assign_issue(lancet, issue, username, active_status):
    with taskstatus("Assigning issue to you") as ts:
        if not issue.assignees or username not in issue.assignees:
            if issue.status == active_status:
                ts.abort("Issue already active and not assigned to you")
            else:
                issue.assign_to(username)
                ts.ok("Issue assigned to you")
        else:
            ts.ok("Issue already assigned to you")


def get_branch(lancet, issue, base_branch=None, create=True):
    if not base_branch:
        base_branch = lancet.config.get("repository", "base_branch")
    remote_name = lancet.config.get("repository", "remote_name")

    name_getter = lancet.get_instance_from_config(
        "repository", "branch_name_getter", lancet
    )
    branch_getter = BranchGetter(base_branch, name_getter, remote_name)

    return branch_getter(lancet.repo, issue, create=create)


def get_project_keys(lancet):
    workspace = os.path.expanduser(lancet.config.get("lancet", "workspace"))
    config_files = glob.glob(os.path.join(workspace, "*", LOCAL_CONFIG))

    for path in config_files:
        config = load_config(path)
        key = config.get("tracker", "default_project", fallback=None)
        if key:
            yield key, os.path.dirname(path)


def get_project_dirs(lancet):
    workspace = os.path.expanduser(lancet.config.get("lancet", "workspace"))
    for path in glob.glob(os.path.join(workspace, "*", ".lancet")):
        path = os.path.dirname(path)
        yield os.path.basename(path), path
