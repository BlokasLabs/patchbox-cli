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
def cli(ctx, in_wizard=False):
    """Update Patchbox OS"""
    if is_connected():
        raise click.ClickException('Please connect your Raspberry Pi to the internet.')
    click.echo('Launching an update script')
    subprocess.call(['sudo', 'chmod', '+x', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/update.sh')])
    print(sys.executable)
    print(sys.argv)
    print('in_wizard', in_wizard)
    # subprocess.call(['sudo', 'sh', '-c', os.path.join(os.path.dirname(os.path.realpath(__file__)) + 'scripts/update.sh')])
    # ctx.meta['resume'] = True
    runner = sys.executable
    args = sys.argv
    if in_wizard:
        args.append('--postupdate')
    os.execl(sys.executable, *([runner] + args))
    do_go_back_if_ineractive()
