import os
import configparser

import click
import keyring

from ..settings import USER_CONFIG, PROJECT_CONFIG
from ..utils import taskstatus


@click.command()
@click.option('-f', '--force/--no-force', default=False)
@click.pass_context
def setup(ctx, force):
    """Wizard to create the user-level configuration file."""
    if os.path.exists(USER_CONFIG) and not force:
        click.secho(
            'An existing configuration file was found at "{}".\n'
            .format(USER_CONFIG),
            fg='red', bold=True
        )
        click.secho(
            'Please remove it before in order to run the setup wizard or use\n'
            'the --force flag to overwrite it.'
        )
        ctx.exit(1)

    click.echo('Address of the issue tracker (your JIRA instance). \n'
               'Normally in the form https://<company>.atlassian.net.')
    tracker_url = click.prompt('URL')
    tracker_user = click.prompt('Username for {}'.format(tracker_url))
    click.echo()

    click.echo('Address of the time tracker (your Harvest instance). \n'
               'Normally in the form https://<company>.harvestapp.com.')
    timer_url = click.prompt('URL')
    timer_user = click.prompt('Username for {}'.format(timer_url))
    click.echo()

    config = configparser.ConfigParser()

    config.add_section('tracker')
    config.set('tracker', 'url', tracker_url)
    config.set('tracker', 'username', tracker_user)

    config.add_section('harvest')
    config.set('harvest', 'url', timer_url)
    config.set('harvest', 'username', timer_user)

    with open(USER_CONFIG, 'w') as fh:
        config.write(fh)

    click.secho('Configuration correctly written to "{}".'
                .format(USER_CONFIG), fg='green')

    # TODO: Add wizard to setup shell integration


@click.command()
@click.option('-f', '--force/--no-force', default=False)
@click.pass_context
def init(ctx, force):
    """Wizard to create a project-level configuration file."""
    if os.path.exists(PROJECT_CONFIG) and not force:
        click.secho(
            'An existing configuration file was found at "{}".\n'
            .format(PROJECT_CONFIG),
            fg='red', bold=True
        )
        click.secho(
            'Please remove it before in order to run the setup wizard or use\n'
            'the --force flag to overwrite it.'
        )
        ctx.exit(1)

    project_key = click.prompt('Project key on the issue tracker')
    base_branch = click.prompt('Integration branch', default='master')

    virtualenvs = ('.venv', '.env', 'venv', 'env')
    for p in virtualenvs:
        if os.path.exists(os.path.join(p, 'bin', 'activate')):
            venv = p
            break
    else:
        venv = ''
    venv_path = click.prompt('Path to virtual environment', default=venv)

    project_id = click.prompt('Project ID on Harvest', type=int)
    task_id = click.prompt('Task id on Harvest', type=int)

    config = configparser.ConfigParser()

    config.add_section('lancet')
    config.set('lancet', 'virtualenv', venv_path)

    config.add_section('tracker')
    config.set('tracker', 'default_project', project_key)

    config.add_section('harvest')
    config.set('harvest', 'project_id', str(project_id))
    config.set('harvest', 'task_id', str(task_id))

    config.add_section('repository')
    config.set('repository', 'base_branch', base_branch)

    with open(PROJECT_CONFIG, 'w') as fh:
        config.write(fh)

    click.secho('\nConfiguration correctly written to "{}".'
                .format(PROJECT_CONFIG), fg='green')


@click.command()
@click.argument('service', required=False)
@click.pass_obj
def logout(lancet, service):
    """Forget saved passwords for the web services."""
    if service:
        services = [service]
    else:
        services = ['tracker', 'harvest']

    for service in services:
        url = lancet.config.get(service, 'url')
        key = 'lancet+{}'.format(url)
        username = lancet.config.get(service, 'username')
        with taskstatus('Logging out from {}', url) as ts:
            if keyring.get_password(key, username):
                keyring.delete_password(key, username)
                ts.ok('Logged out from {}', url)
            else:
                ts.ok('Already logged out from {}', url)
