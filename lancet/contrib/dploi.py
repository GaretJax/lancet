from shlex import quote

import click


@click.command()
@click.option('-p', '--print/--exec', 'print_cmd', default=False,
              help='Print the command instead of executing it.')
@click.argument('environment')
@click.pass_obj
def ssh(lancet, print_cmd, environment):
    """
    SSH into the given environment, based on the dploi configuration.
    """
    namespace = {}

    with open('deployment.py') as fh:
        code = compile(fh.read(), 'deployment.py', 'exec')
        exec(code, {}, namespace)

    config = namespace['settings'][environment]
    host = '{}@{}'.format(config['user'], config['hosts'][0])
    cmd = ['ssh', '-p', str(config.get('port', 20)), host]

    if print_cmd:
        click.echo(' '.join(quote(s) for s in cmd))
    else:
        lancet.defer_to_shell(*cmd)
