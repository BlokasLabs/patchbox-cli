import subprocess
import click
import os
from os.path import isfile
from patchbox import views


def run_cmd(list, silent=True):
    """ Runs bash command, returns is_error, output"""
    try:
        output = subprocess.check_output(list)
        return False, output
    except:
        if not silent:
            raise click.ClickException(
                'Operation failed: {}'.format(' '.join([i for i in list])))
        return True, None


def run_cmd_bg(list, silent=True):
    """ Runs bash command, returns is_error, output"""
    try:
        output = subprocess.Popen(list, preexec_fn=os.setpgrp)
    except:
        if not silent:
            raise click.ClickException(
                'Operation failed: {}'.format(' '.join([i for i in list])))


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


def ensure_param(ctx, value, required=False, required_message='', options=[]):
    if not ctx.meta.get('show_ui', False):
        if value is None:
            raise click.ClickException()
        return value
    close, output = views.do_menu(ctx.command.short_help, options)
    if close:
        ctx.exit()
    return output
    


def do_group_root(ctx):
    if ctx.invoked_subcommand is None:
        if ctx.meta.get('show_ui', False):
            options = []
            commands = ctx.command.list_commands(ctx)
            for command in commands:
                options.append({'key': command, 'value': command, 'description': ctx.command.get_command(ctx, command).__doc__})
            close, output = views.do_menu(ctx.command.short_help, options)
            if close:
                ctx.exit()
            if output:
                # ctx.command.get_command(ctx, output)() for direct exec (main context gets lost) todo: how to merge context meta?
                ctx.invoke(ctx.command.get_command(ctx, output))
        else:
            click.echo(ctx.command.get_help(ctx))
