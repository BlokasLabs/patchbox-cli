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
@click.argument('option', type=click.Choice(['desktop', 'desktop-autologin', 'console', 'console-autologin']))
@click.pass_context
def environment(ctx, option):
    """Choose Boot environment (Desktop or Console)"""
    option = do_ensure_param(ctx, 'option')
    options = {
        'desktop': '/scripts/set_boot_to_desktop.sh',
        'desktop-autologin': '/scripts/set_boot_to_desktop_autologin.sh',
        'console': '/scripts/set_boot_to_console.sh',
        'console-autologin': '/scripts/set_boot_to_console_autologin.sh'
    }
    if options.get(option):
        subprocess.call(['sudo', 'chmod', '+x', os.path.dirname(os.path.realpath(__file__)) + options[option]])
        subprocess.call(['sudo', 'sh', os.path.dirname(os.path.realpath(__file__)) + options[option], os.environ['SUDO_USER']])    
    do_go_back_if_ineractive()
