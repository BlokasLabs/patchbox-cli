import click
from patchbox.utils import do_go_back_if_ineractive
from patchbox.views import do_msgbox, do_yesno
from patchbox.modules.jack.cli import config as jack_config
from patchbox.modules.password.cli import cli as password_config
from patchbox.modules.wifi.cli import connect as wifi_connect
from patchbox.modules.boot.cli import environment as boot_config

def run_wizard_cmd(ctx, command=None, message='Let\'s begin!', error="Uups! Something ain\'t right. Let\'s try again.", required=False):
    if required:
        do_msgbox(message)
    while command:
        if not required:
            no, output = do_yesno(message)
            if no:
                break
        try:
            ctx.invoke(command)
            break
        except:
            do_msgbox(error)

@click.command()
@click.pass_context
def cli(ctx):
    """Initial setup wizard"""

    ctx.meta['interactive'] = True
    ctx.meta['wizard'] = True

    do_msgbox('Howdy, stranger!\n\nLet\'s begin the Patchbox OS initial setup wizard!')

    run_wizard_cmd(
        ctx, 
        command=password_config, 
        message='Security first!\n\nYou need to change the default system password.\nPress OK and follow the terminal instructions.',
        required=True
    )
    run_wizard_cmd(
        ctx, 
        command=jack_config, 
        message='Great! Now you need to set your default system soundcard.\nClik OK and follow the instructions.', 
        error="It seems that the settings provided are not supported by your soundcard.\nLet's try again.",
        required=True
    )
    run_wizard_cmd(
        ctx, 
        command=boot_config, 
        message="Let's decide which boot environment you want use. Desktop vs Console.",
        required=True
    )
    run_wizard_cmd(
        ctx, 
        command=wifi_connect, 
        message='Do you want to connect to WiFi network?'
    )

    do_msgbox("That's it!\n\nYou can re-run this wizard any time by running 'sudo patchbox wizard'.\n\nSee ya!")
