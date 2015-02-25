import os
import sys
import pdb
import importlib

import click

from . import __version__
from .settings import load_config, PROJECT_CONFIG
from .base import Lancet, WarnIntegrationHelper, ShellIntegrationHelper
from .utils import hr


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def setup_helper(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    base = os.path.abspath(os.path.dirname(__file__))
    helper = os.path.join(base, 'helper.sh')
    with open(helper) as fh:
        click.echo(fh.read())
    ctx.exit()


class ConfigurableLoader(click.Group):

    @classmethod
    def get_config(cls):
        if os.path.exists(PROJECT_CONFIG):
            return load_config(PROJECT_CONFIG)
        else:
            return load_config()

    @classmethod
    def get_configured_commands(cls, config=None):
        if config is None:
            config = cls.get_config()
        return config.options('commands')

    def list_commands(self, ctx):
        commands = set(super().list_commands(ctx))
        commands = commands.union(self.get_configured_commands())
        return sorted(commands)

    def get_command(self, ctx, name):
        if name in self.get_configured_commands():
            path = self.get_config().get('commands', name)
            module_path, attr_name = path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, attr_name)
        else:
            return super().get_command(ctx, name)


@click.command(context_settings=CONTEXT_SETTINGS, cls=ConfigurableLoader)
@click.version_option(version=__version__, message='%(prog)s %(version)s')
@click.option('-d', '--debug/--no-debug', default=False)
@click.option('--setup-helper', callback=setup_helper, is_flag=True,
              expose_value=False, is_eager=True,
              help='Print the shell integration code and exit.')
@click.pass_context
def main(ctx, debug):
    # TODO: Enable this using a command line switch
    # import logging
    # logging.basicConfig(level=logging.DEBUG)

    if debug:
        def exception_handler(type, value, traceback):
            click.secho('\nAn exception occurred while executing the '
                        'requested command:', fg='red')
            hr(fg='red')
            sys.__excepthook__(type, value, traceback)

            click.secho('\nAs requested I will now drop you inside an '
                        'interactive debugging session:', fg='red')
            hr(fg='red')

            pdb.post_mortem(traceback)
        sys.excepthook = exception_handler

    try:
        integration_helper = ShellIntegrationHelper(
            os.environ['LANCET_SHELL_HELPER'])
    except KeyError:
        integration_helper = WarnIntegrationHelper()

    if os.path.exists(PROJECT_CONFIG):
        config = load_config(PROJECT_CONFIG)
    else:
        config = load_config()

    ctx.obj = Lancet(config, integration_helper)
    ctx.obj.call_on_close = ctx.call_on_close
    ctx.call_on_close(integration_helper.close)


# TODO:
# * review
#     pull
#     ci-status
#     pep8
#     diff
#     mergeability (rebase is of the submitter responsibility)
# * merge
#     pull, merge, delete
# * issues
#     list all open/assigned issues (or by filter)
# * comment
#     adds a comment to the currently active issue
