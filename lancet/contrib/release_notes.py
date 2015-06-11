import click

from tabulate import tabulate

from lancet.utils import taskstatus, edit_template


VERSION_FILTER_QUERY = (
    'project = {project_key} and fixVersion = {version_name}')


def get_version(lancet, project_key, version_name):
    project = lancet.tracker.project(project_key)
    versions = lancet.tracker.project_versions(project)
    for v in versions:
        if v.name == version_name:
            return v


def get_issues_fixed_in_version(lancet, project_key, version_name):
    return lancet.tracker.search_issues(VERSION_FILTER_QUERY.format(
        project_key=project_key, version_name=version_name))


@click.command()
@click.pass_obj
def list_versions(lancet):
    project_key = lancet.config.get('tracker', 'default_project')

    project = lancet.tracker.project(project_key)
    versions = lancet.tracker.project_versions(project)

    table = [(
        (click.style(' ✓', fg='green') if v.released
         else click.style(' •', 'yellow')),
        v.name,
        v.description,
    ) for v in reversed(versions)]

    headers = ['Rel', 'Name', 'Description']
    click.echo(tabulate(table, headers, tablefmt='simple'))


@click.command()
@click.option('-t', '--target',
              help='Target of the release (either a commit or a branch name).')
@click.option('-d', '--draft/--no-draft', default=True,
              help='Creates the release in draft mode (default to true).')
@click.option('-p', '--prerelease/--no-prerelease', default=False,
              help='Creates a prerelease.')
@click.option('-o', '--open/--no-open', 'open_link', default=False,
              help='Opens the link with the release.')
@click.argument('version_name', metavar='version')
@click.pass_obj
def release_notes(lancet, version_name, target, draft, prerelease, open_link):
    project_key = lancet.config.get('tracker', 'default_project')

    with taskstatus('Getting version') as ts:
        version = get_version(lancet, project_key, version_name)
        if not version:
            ts.abort('Version {} not found for project {}',
                     version_name, project_key)

        ts.ok('Got version {}', version.name)

    with taskstatus('Getting issues fixed in version {}', version.name) as ts:
        issues = get_issues_fixed_in_version(lancet, project_key, version_name)
        ts.ok('Found {} issues', len(issues))

    with taskstatus('Creating release') as ts:
        notes = edit_template(
            lancet.config.get('tracker', 'release_notes_template'),
            issues=issues,
            version=version
        )
        if not notes:
            ts.abort('No release notes provided')

        name, notes = notes.split('\n\n', 1)

        if target is None:
            target = lancet.config.get('repository', 'base_branch')

        release = lancet.github_repo.create_release(
            version_name,
            target_commitish=target,
            name=name.strip(),
            body=notes.strip(),
            draft=draft,
            prerelease=prerelease,
        )

        ts.ok('Release created at {}', release.html_url)

    if open_link:
        click.launch(release.html_url)


# TODO: Add commands to:
# * Release versions (both GH + Jira)
# * Set fixVersion to closed issues in the current sprint
# * ...
#
# @click.command()
# @click.argument('version')
# @click.argument('issues', nargs=-1, required=True)
# @click.pass_obj
# def set_version(lancet, version, issues):
#     for issue_key in issues:
#         set_issue_version(lancet, issue_key, version)
#
#
# def set_issue_version(lancet, issue_key, version):
#     issue = get_issue(lancet, issue_key)
#     issue.update(fields={
#         'fixVersion': [{'add': [{'id': 10301}]}]
#     })
