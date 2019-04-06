import click
import os
import subprocess
from patchbox.utils import do_go_back_if_ineractive


@click.command()
@click.pass_context
def cli(ctx):
    """Update Patchbox OS"""
    subprocess.call(['sudo', 'chmod', '+x', os.path.dirname(os.path.realpath(__file__)) + '/scripts/update.sh'])
    subprocess.call(['sudo', 'sh', '-c', os.path.dirname(os.path.realpath(__file__)) + '/scripts/update.sh'])
    do_go_back_if_ineractive()
