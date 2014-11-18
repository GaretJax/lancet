import click


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    pass


# To add a new subcommand, copy, paste, and uncomment the following lines:
# from .... import command
# main.add_command(command)
