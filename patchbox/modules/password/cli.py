import click
import subprocess
import os
from patchbox.utils import do_go_back_if_ineractive


@click.command()
def cli():
    """Change Password"""
    subprocess.call(['passwd', os.environ['SUDO_USER']])
    do_go_back_if_ineractive()
