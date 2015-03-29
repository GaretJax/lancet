import click


@click.command()
@click.argument('environment')
@click.pass_obj
def ssh(lancet, environment):
    """
    SSH into the given environment, based on the dploi configuration.
    """
    namespace = {}

    with open('deployment.py') as fh:
        code = compile(fh.read(), 'deployment.py', 'exec')
        exec(code, {}, namespace)

    config = namespace['settings'][environment]
    host = '{}@{}'.format(config['user'], config['hosts'][0])
    lancet.defer_to_shell('ssh', '-p', str(config.get('port', 20)), host)
