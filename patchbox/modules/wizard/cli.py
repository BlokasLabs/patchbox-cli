import subprocess
import click
from patchbox.utils import do_go_back_if_ineractive, run_interactive_cmd
from patchbox.views import do_msgbox
from patchbox.modules.jack.cli import config as jack_config
from patchbox.modules.password.cli import cli as password_config
from patchbox.modules.wifi.cli import connect as wifi_connect
from patchbox.modules.boot.cli import environment as boot_config
from patchbox.modules.module.cli import config as module_config


@click.command()
@click.pass_context
def cli(ctx):
    """Initial setup wizard"""

    ctx.meta['interactive'] = True
    ctx.meta['wizard'] = True

    do_msgbox('Howdy, stranger!\n\nLet\'s begin the Patchbox OS initial setup wizard!')

    run_interactive_cmd(
        ctx, 
        command=password_config, 
        message='Security first!\n\nYou have to change the default system password.\nPress OK and follow the terminal instructions.',
        required=True
    )
    run_interactive_cmd(
        ctx, 
        command=jack_config, 
        message='Now pick the system sound card to use.\nClick OK and follow the instructions.', 
        error="It seems that the settings provided are not supported by your soundcard.\nLet's try again.",
        required=True
    )
    run_interactive_cmd(
        ctx, 
        command=boot_config, 
        message="Let's decide which boot environment you want use. Desktop vs Console.",
        required=True
    )
    run_interactive_cmd(
        ctx, 
        command=wifi_connect, 
        message='Do you want to connect to WiFi network?'
    )
    run_interactive_cmd(
        ctx, 
        command=module_config, 
        message='Meet Patchbox Modules! \n\nPatchbox Modules are different environments that are activated on boot \nand will allow you to use your Raspberry Pi box in many different ways. \n\nWe have prepared few modules already and together with Patchbox community hope to introduce many more in the future! \n\nNow you will be able to choose one.',
        required=True
    )

    do_msgbox("That's it!\n\nYou can re-run this wizard any time by running 'sudo patchbox-config wizard'.\n\nSee ya!")

    subprocess.call(['cat', '/etc/motd'])
