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
    subprocess.call(['sudo', 'sh', '-c', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/update.sh')])
    runner = sys.executable
    args = sys.argv
    if ctx.meta['wizard']:
        args.append('--postupdate')
    os.execl(sys.executable, *([runner] + args))
    do_go_back_if_ineractive()
