import click
from patchbox.utils import PatchboxHomeGroup, PatchboxChoice, do_group_menu
from patchbox import settings
from dotenv import load_dotenv
import os
import sys
import shutil

click.Choice = PatchboxChoice

def migrate_state():
    if not os.path.exists(settings.PATCHBOX_STATE_DIR) and os.path.exists('/root/.patchbox'):
        shutil.move('/root/.patchbox', settings.PATCHBOX_STATE_DIR)

def root_fix():
    if os.getuid() != 0:
        args = sys.argv
        args.insert(0, 'sudo')
        args.insert(1, '-E')
        os.execvp('sudo', args)
    else:
        load_dotenv(dotenv_path='/etc/environment')

@click.command(cls=PatchboxHomeGroup, context_settings=dict(help_option_names=['--help']))
@click.option('--verbose', is_flag=True, help='Enables verbose mode.')
@click.option('--interactive', is_flag=True, help='Enables interactive mode.')
@click.option('--user', is_flag=True, help='Runs as current user instead of root', default=False)
@click.version_option("1.3.3")
@click.pass_context
def cli(ctx, verbose, interactive, user):
    """Patchbox Configuration Utility"""
    if not user:
        root_fix()
        migrate_state()

    ctx.meta['is_user'] = user

    if ctx.invoked_subcommand is None or interactive:
        ctx.meta['interactive'] = True
    do_group_menu(ctx, cancel='Exit')

if __name__ == '__main__':
    cli()
