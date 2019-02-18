import subprocess
import click

def run_cmd(list, silent=True):
    """ Runs bash command, returns is_error, output"""
    try:
        output = subprocess.check_output(list)
        return False, output
    except:
        if not silent:
            raise click.ClickException('Operation failed!')
        return True, None