import click
import os
import sys
import subprocess
from patchbox.utils import do_go_back_if_ineractive
import socket

REMOTE_SERVER = "www.google.com"

def is_connected():
  try:
    host = socket.gethostbyname(REMOTE_SERVER)
    socket.create_connection((host, 80), 2)
    return True
  except:
     return False

@click.command()
@click.pass_context
def cli(ctx):
    """Update Patchbox OS"""
    if not is_connected():
        raise click.ClickException('no internet connection')

    subprocess.call(['sudo', 'chmod', '+x', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/update.sh')])
    error = subprocess.call(['sudo', 'sh', '-c', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/update.sh')])

    if error != 0:
        raise click.ClickException('update script error code: {}'.format(error))
    
    args = sys.argv
    if not 'update' in args:
        if ctx.meta.get('wizard'):
            if not 'wizard' in args:
                args.append('wizard')
            args.append('--postupdate')
        os.execl(sys.executable, *([sys.executable] + args))
