import os
import sys
import click
from PyInquirer import style_from_dict, Token, prompt, Separator
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
        super(DynamicGroup, self).__init__(invoke_without_command=True, *args, **kwargs)

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
    """Patchbox OS Configuration Utility."""
    if ctx.invoked_subcommand is None:
        click.echo(Figlet(font='slant').renderText('patchbox'))
        click.echo('Press Ctrl + C to Exit\n')
        questions = [
            {
                'type': 'list',
                'name': 'command',
                'message': 'Choose a command:',
                'choices': ctx.command.list_commands(ctx),
            },
        ]

        answers = prompt(questions)
        # commands = ctx.command.list_commands(ctx)
        # options = []
        # for i, name in enumerate(commands, start=1):
        #     options.append(i)
        #     click.echo('{}. {}'.format(i, name))
        # click.echo()
        # command_no = None
        # while command_no not in options:
        #     command_no = click.prompt('Enter a command number', type=int)
        # command = ctx.command.get_command(ctx, commands[command_no - 1])
        command = answers.get('command')
        if command:
            click.echo()
            ctx.invoke(ctx.command.get_command(ctx, command))
    # click.echo(dir(ctx))
