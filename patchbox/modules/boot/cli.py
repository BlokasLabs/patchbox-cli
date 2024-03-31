import subprocess
import click
import os
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive, do_yesno, do_msgbox


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage Boot options"""
    do_group_menu(ctx)


@cli.command()
@click.argument('option', type=click.Choice(['desktop', 'desktop autologin', 'console', 'console autologin']))
@click.pass_context
def environment(ctx, option):
    """Choose Boot environment (Desktop or Console)"""

    if option is None:
        ctx.meta['interactive'] = True

    option = do_ensure_param(ctx, 'option')
    if option == 'desktop':
        subprocess.call([os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/set_boot_to_desktop.sh')])
    elif option == 'desktop autologin':
        subprocess.call([os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/set_boot_to_desktop.sh'), 'autologin'])
    elif option == 'console':
        subprocess.call([os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/set_boot_to_console.sh')])
    elif option == 'console autologin':
        subprocess.call([os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/set_boot_to_console.sh'), 'autologin'])

    ctx.meta['reboot_required'] = True
    if ctx.meta.get('interactive') and not ctx.meta.get('wizard'):
        no, output = do_yesno('A system restart is required to activate the new boot behavior. Reboot now?')
        if not no:
            subprocess.call('reboot')
    else:
        click.echo('A system restart is required to activate the new boot behavior. You may do so by executing `sudo reboot`.')

    do_go_back_if_ineractive(silent=True)
