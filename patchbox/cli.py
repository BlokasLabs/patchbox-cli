import os
import sys
import click
from pyfiglet import Figlet


class Store(object):

    def __init__(self):
        self.verbose = False

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

pass_store = click.make_pass_decorator(Store, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))
CONTEXT_SETTINGS = dict(help_option_names=['--help'])


class DynamicGroup(click.MultiCommand):

    def __init__(self, *args, **kwargs):
        self.root_check()
        super(DynamicGroup, self).__init__(invoke_without_command=True, *args, **kwargs)
    
    def root_check(self):
        if os.getuid() != 0:
            print("Must be run as root. Try 'sudo patchbox'")
            exit() 

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and \
               filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            if sys.version_info[0] == 2:
                name = name.encode('ascii', 'replace')
            mod = __import__('patchbox.commands.cmd_' + name,
                             None, None, ['cli'])
        except ImportError:
            return
        return mod.cli

@click.command(cls=DynamicGroup, context_settings=CONTEXT_SETTINGS)
@click.option('--verbose', is_flag=True,
              help='Enables verbose mode.')
@pass_store
@click.pass_context
@click.version_option()
def cli(ctx, store, verbose):
    """Patchbox Configuration Utility"""
    if ctx.invoked_subcommand is None:
        click.echo(Figlet(font='slant').renderText('patchbox'))
        click.echo('Available commands:')
        for command in ctx.command.list_commands(ctx):
            click.echo(command)
