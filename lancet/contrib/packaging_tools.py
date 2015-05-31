from collections import OrderedDict
import subprocess

import click
import pygit2
from jinja2 import Template

from ..utils import content_from_path


@click.command()
@click.argument('output', type=click.File('wb'))
@click.pass_obj
def contributors(lancet, output):
    """
    List all contributors visible in the git history.
    """
    sorting = pygit2.GIT_SORT_TIME | pygit2.GIT_SORT_REVERSE
    commits = lancet.repo.walk(lancet.repo.head.target, sorting)
    contributors = ((c.author.name, c.author.email) for c in commits)
    contributors = OrderedDict(contributors)

    template_content = content_from_path(
        lancet.config.get('packaging', 'contributors_template'))
    template = Template(template_content)
    output.write(template.render(contributors=contributors).encode('utf-8'))


@click.command()
@click.argument('version', required=False)
@click.pass_obj
def tag_version(lancet, version):
    # NOTE: We're using a subprocess instead of interpreting the setup.py file
    # as the python version of the package may differ from the one which
    # executes lancet.
    if not version:
        version = subprocess.check_output(['python', 'setup.py', '--version'])
        version = version.strip().decode('ascii')

    name = subprocess.check_output(['python', 'setup.py', '--name'])
    name = name.strip().decode('ascii')

    tag_name = lancet.config.get('packaging', 'version_tag_name').format(
        name=name, version=version)
    tag_message = lancet.config.get('packaging', 'version_tag_message').format(
        name=name, version=version)

    click.echo('I am tagging the current commit with the version {}.'.format(
        click.style(tag_name, fg='green'),
    ))

    if click.confirm('Do you want to continue?'):
        lancet.repo.create_tag(
            tag_name,
            lancet.repo.head.target,
            pygit2.GIT_OBJ_COMMIT,
            lancet.repo.default_signature,
            tag_message
        )
