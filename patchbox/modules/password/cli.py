import click
import subprocess
from patchbox.utils import do_go_back_if_ineractive


@click.command()
def cli():
    """Change Password"""
    subprocess.call('passwd')
    do_go_back_if_ineractive()
