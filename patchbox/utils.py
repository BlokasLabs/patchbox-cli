import subprocess
import click
import os
from os.path import isfile

def run_cmd(list, silent=True):
    """ Runs bash command, returns is_error, output"""
    try:
        output = subprocess.check_output(list)
        return False, output
    except:
        if not silent:
            raise click.ClickException('Operation failed: {}'.format(' '.join([i for i in list])))
        return True, None

def run_cmd_bg(list, silent=True):
    """ Runs bash command, returns is_error, output"""
    try:
        output = subprocess.Popen(list, preexec_fn=os.setpgrp)
    except:
        if not silent:
            raise click.ClickException('Operation failed: {}'.format(' '.join([i for i in list])))

def write_file(path, content, silent=True):
    if not isfile(path) and not silent:
        raise click.ClickException('File not found!')
    try:
        with open(path, 'w') as f:
            f.write(content)
        return False
    except Exception as e:
        click.echo(e, err=True)
        return True