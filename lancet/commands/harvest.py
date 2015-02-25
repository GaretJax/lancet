import re

import click


@click.command()
@click.argument('query', required=False)
@click.pass_obj
def projects(lancet, query):
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


@click.command()
@click.argument('project_id', type=int)
@click.pass_obj
def tasks(lancet, project_id):
    """List Harvest tasks for the given project ID."""
    projects = lancet.timer.projects()

    for project in projects:
        if project['id'] == project_id:
            click.echo('{:>9d} {} {}'.format(
                project['id'], click.style('‣', fg='yellow'), project['name']))
            hr()

            for task in project['tasks']:
                click.echo('{:>9d} {} {}'.format(
                    task['id'], click.style('‣', fg='yellow'), task['name']))
            break
