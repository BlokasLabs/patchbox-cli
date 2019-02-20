import os
import sys
import click
from pyfiglet import Figlet
from patchbox import views
from patchbox.utils import do_group_root


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


class PatchboxDynamicGroup(click.MultiCommand):

    def __init__(self, *args, **kwargs):
        self.root_check()
        super(PatchboxDynamicGroup, self).__init__(invoke_without_command=True, *args, **kwargs)
    
    def root_check(self):
        if os.getuid() != 0:
            click.echo("Must be run as root. Try 'sudo patchbox'")
            sys.exit()

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

@click.command(cls=PatchboxDynamicGroup, context_settings=CONTEXT_SETTINGS)
@click.option('--no-input', is_flag=True, default=False, help='No input mode.')
@click.option('--verbose', is_flag=True, help='Enables verbose mode.')
@click.pass_context
@click.version_option()
def cli(ctx, no_input, verbose):
    """Patchbox Configuration Utility"""
    if ctx.invoked_subcommand is None:
        ctx.meta['show_ui'] = True
    do_group_root(ctx)

