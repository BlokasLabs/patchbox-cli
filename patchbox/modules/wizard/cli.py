import click
from patchbox.utils import run_interactive_cmd
from patchbox.views import do_msgbox
from patchbox.modules.jack.cli import config as jack_config
from patchbox.modules.password.cli import cli as password_config
from patchbox.modules.wifi.cli import connect as wifi_connect
from patchbox.modules.boot.cli import environment as boot_config
from patchbox.modules.module.cli import config as module_config
from patchbox.modules.update.cli import cli as update_sysem


@click.command()
@click.option('--postupdate', default=False, is_flag=True)
@click.pass_context
def cli(ctx, postupdate):
    """Initial setup wizard"""

    ctx.meta['interactive'] = True
    ctx.meta['wizard'] = True

    if not postupdate:

        do_msgbox("Howdy, stranger! \n\nLet's begin the Patchbox OS initial setup wizard! \n\nYou can re-run this wizard any time by typing 'patchbox' in a terminal window and choosing the 'wizard' option.")

        run_interactive_cmd(
            ctx,
            command=update_sysem,
            message="Let's check for Patchbox OS updates first. \n\nChoose NO if you want to do this later via 'patchbox > update' option.",
            error="Oops! Something ain't right. Is your Raspberry Pi connected to the internet? \n\nConnect it or skip the updates step for now."
        )

    run_interactive_cmd(
        ctx, 
        command=password_config, 
        message="Security part! \n\nChange the default system password. \n\nChoose YES and follow the terminal instructions."
    )
    run_interactive_cmd(
        ctx, 
        command=jack_config, 
        message='Now pick the default system sound card. You may use external USB audio cards and HAT-type cards. \n\nIf your HAT card is not listed, most likely you have to enable it by editing /boot/firmware/config.txt and reboot,\nrefer to the support pages of your card.\n\nChoose OK and follow the instructions. This step is required. \n\nYou will be able to change these settings later via \'patchbox > jack > config\' option.',
        error="It seems that the Jack server is busy or the settings provided are not supported by your sound card. \n\nLet's try again.",
        required=True
    )
    run_interactive_cmd(
        ctx, 
        command=boot_config, 
        message="Let's decide which boot environment you want to use. Desktop vs Console. \n\nYou can change this any time via 'patchbox > boot > environment' option.",
        required=True
    )
    run_interactive_cmd(
        ctx, 
        command=wifi_connect, 
        message='Do you want to connect to WiFi network? \n\nNote: the Patchbox WiFi hotspot will be disabled!'
    )
    run_interactive_cmd(
        ctx, 
        command=module_config, 
        message='Meet Patchbox Modules! \n\nPatchbox Modules are different environments that are activated on boot \nand will allow you to use your Raspberry Pi box in many different ways. \n\nWe have a couple modules already and together with the Patchbox community\nwe hope to introduce many more in the future! \n\nNext step is to choose one.',
        required=True
    )

    do_msgbox("That's it!\n\nOnce again, you can re-run this wizard any time by typing 'patchbox' in a terminal window and choosing the 'wizard' option. \n\nSee ya!")
