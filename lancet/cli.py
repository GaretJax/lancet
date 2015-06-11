import os
import sys
import bdb
import pdb
import importlib
import shlex
import subprocess

import click
from click.utils import make_str

try:
    import raven
except ImportError:
    raven = None

from . import __version__
from .settings import load_config, diff_config, as_dict
from .settings import PROJECT_CONFIG, DEFAULT_CONFIG
from .base import Lancet, WarnIntegrationHelper, ShellIntegrationHelper
from .utils import hr


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
IGNORED_EXCEPTIONS = set([
    bdb.BdbQuit,
])


def get_sentry_client(sentry_dsn):
    return raven.Client(
        sentry_dsn,
        release=__version__,
        processors=(
            'raven.processors.SanitizePasswordsProcessor',
        )
    )


class SubprocessExecuter(click.BaseCommand):
    def parse_args(self, ctx, args):
        ctx.args = args
        return args

    def invoke(self, ctx):
        ctx.exit(subprocess.call(ctx.args[0], shell=True))


class ConfigurableLoader(click.Group):

    _config = None
    _path_setup_complete = False

    def __init__(self, *args, **kwargs):
        self.__class__.setup_path()
        super().__init__(*args, **kwargs)

    @classmethod
    def setup_path(cls):
        if not cls._path_setup_complete:
            paths = cls.get_config().getlist('lancet', 'add_to_path')
            for p in reversed(paths):
                sys.path.insert(0, os.path.expanduser(p))

    @classmethod
    def get_config(cls):
        if not cls._config:
            if os.path.exists(PROJECT_CONFIG):
                cls._config = load_config(PROJECT_CONFIG)
            else:
                cls._config = load_config()
        return cls._config

    @classmethod
    def get_configured_commands(cls, config=None):
        if config is None:
            config = cls.get_config()
        return config.options('commands')

    @classmethod
    def get_configured_aliases(cls, config=None):
        if config is None:
            config = cls.get_config()
        return config.options('alias')

    @staticmethod
    def show_help_all(ctx, param, value):
        if value and not ctx.resilient_parsing:
            # Explicitly set the flag to show hidden subcommands, otherwise
            # the code in the `get_help` method would set it to False.
            ctx.show_hidden_subcommands = True
            click.echo(ctx.get_help())
            ctx.exit()

    def list_commands(self, ctx):
        commands = set(super().list_commands(ctx))
        commands = commands.union(self.get_configured_commands())

        # Do not list hidden subcommands if the flag is explicitly set on the
        # context. By default include all commands.
        if not getattr(ctx, 'show_hidden_subcommands', True):
            commands = [c for c in commands if not c.startswith('_')]
        return sorted(commands)

    def list_aliases(self, ctx):
        return sorted(self.get_configured_aliases())

    def get_help(self, ctx):
        # By default do not list hidden subcommands.
        ctx.show_hidden_subcommands = getattr(
            ctx, 'show_hidden_subcommands', False)
        return super().get_help(ctx)

    def format_options(self, ctx, formatter):
        super().format_options(ctx, formatter)
        self.format_aliases(ctx, formatter)

    def format_aliases(self, ctx, formatter):
        rows = []
        for alias in self.list_aliases(ctx):
            rows.append((alias, self.get_config().get('alias', alias)))

        if rows:
            with formatter.section('Aliases'):
                formatter.write_dl(rows)

    def resolve_command(self, ctx, args):
        cmd_name = make_str(args[0])

        if cmd_name in self.get_configured_aliases():
            if cmd_name in self.list_commands(ctx):
                # Shadowing of existing commands is explicitly disabled.
                click.secho('"{}" references an existing command. I am '
                            'ignoring the alias definition.'.format(cmd_name),
                            fg='yellow')
            else:
                # If the command references a configured alias, retrieve it
                # from the configuration.
                alias = self.get_config().get('alias', cmd_name)
                args = args[1:]
                if alias.startswith('!'):
                    cmd = SubprocessExecuter('')
                    additional_args = ' '.join(shlex.quote(a) for a in args)
                    return '', cmd, [alias[1:] + ' ' + additional_args]
                else:
                    args = shlex.split(alias) + args

        return super().resolve_command(ctx, args)

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
@click.option('-d', '--debug/--no-debug', default=False,
              help=('Drop into the debugger if the command execution raises '
                    'an exception.'))
@click.option('--help-all', is_flag=True, is_eager=True, expose_value=False,
              callback=ConfigurableLoader.show_help_all,
              help='Show this message including hidden subcommands.')
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

    sentry_dsn = config.get('lancet', 'sentry_dsn')
    if sentry_dsn and not debug:
        if not raven:
            click.secho('You provided a Sentry DSN but the raven module is '
                        'not installed. Sentry logging will not be enabled.',
                        fg='yellow')
        else:
            sentry_client = get_sentry_client(sentry_dsn)

            def exception_handler(type, value, traceback):
                settings_diff = diff_config(
                    load_config(DEFAULT_CONFIG, defaults=False),
                    config,
                    exclude=set([
                        ('lancet', 'sentry_dsn'),
                    ])
                )

                sys.__excepthook__(type, value, traceback)

                if type in IGNORED_EXCEPTIONS:
                    return

                click.echo()
                hr(fg='yellow')

                click.secho('\nAs requested, I am sending details about this '
                            'error to Sentry, please report the following ID '
                            'when seeking support:')

                error_id = sentry_client.captureException(
                    (type, value, traceback),
                    extra={
                        'settings': as_dict(settings_diff),
                        'working_dir': os.getcwd(),
                    },
                )[0]
                click.secho('\n    {}\n'.format(error_id), fg='yellow')
            sys.excepthook = exception_handler


@main.command()
def _setup_helper():
    """Print the shell integration code."""
    base = os.path.abspath(os.path.dirname(__file__))
    helper = os.path.join(base, 'helper.sh')
    with open(helper) as fh:
        click.echo(fh.read())


@main.command()
@click.pass_context
def _commands(ctx):
    """Prints a list of commands for shell completion hooks."""
    ctx = ctx.parent
    ctx.show_hidden_subcommands = False
    main = ctx.command

    for subcommand in main.list_commands(ctx):
        cmd = main.get_command(ctx, subcommand)
        if cmd is None:
            continue
        help = cmd.short_help or ''
        click.echo('{}:{}'.format(subcommand, help))


@main.command()
@click.argument('command_name', metavar='command', required=False)
@click.pass_context
def _arguments(ctx, command_name=None):
    """Prints a list of arguments for shell completion hooks.

    If a command name is given, returns the arguments for that subcommand.
    The command name has to refer to a command; aliases are not supported.
    """
    ctx = ctx.parent
    main = ctx.command
    if command_name:
        command = main.get_command(ctx, command_name)
        if not command:
            return
    else:
        command = main

    types = ['option', 'argument']
    all_params = sorted(command.get_params(ctx),
                        key=lambda p: types.index(p.param_type_name))

    def get_name(param):
        return max(param.opts, key=len)

    for param in all_params:
        if param.param_type_name == 'option':
            option = get_name(param)
            same_dest = [get_name(p) for p in all_params
                         if p.name == param.name]
            if same_dest:
                option = '({})'.format(' '.join(same_dest)) + option
            if param.help:
                option += '[{}]'.format(param.help or '')
            if not param.is_flag:
                option += '=:( )'
            click.echo(option)
        elif param.param_type_name == 'argument':
            option = get_name(param)
            click.echo(':{}'.format(option))


@main.command()
@click.argument('shell', required=False)
@click.pass_context
def _autocomplete(ctx, shell):
    """Print the shell autocompletion code."""
    if not shell:
        shell = os.environ.get('SHELL', '')
        shell = os.path.basename(shell).lower()
    if not shell:
        click.secho('Your shell could not be detected, please pass its name '
                    'as the argument.', fg='red')
        ctx.exit(-1)

    base = os.path.abspath(os.path.dirname(__file__))
    autocomplete = os.path.join(base, 'autocomplete', '{}.sh'.format(shell))

    if not os.path.exists(autocomplete):
        click.secho('Autocompletion for your shell ({}) is currently not '
                    'supported.', fg='red')
        ctx.exit(-1)

    with open(autocomplete) as fh:
        click.echo(fh.read())


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
