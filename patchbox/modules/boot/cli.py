import subprocess
import click
import os
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage Boot options"""
    do_group_menu(ctx)


@cli.command()
@click.argument('option', type=click.Choice(['desktop', 'console']))
@click.pass_context
def environment(ctx, option):
    """Choose Boot environment (Desktop or Console)"""
    option = do_ensure_param(ctx, 'option')
    if option == 'desktop':
        subprocess.call(['sudo', 'sh', '-c', os.path.dirname(os.path.realpath(__file__)) + '/scripts/set_boot_to_desktop.sh'])
    if option == 'console':
        subprocess.call(['sudo', 'sh', '-c', os.path.dirname(os.path.realpath(__file__)) + '/scripts/set_boot_to_console.sh'])
    do_go_back_if_ineractive()
