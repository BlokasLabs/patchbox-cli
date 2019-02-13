import click
from patchbox.cli import pass_store


@click.command('status', short_help='Display System Status.')
@pass_store
def cli(ctx):
    """Shows file changes in the current working directory."""
    click.echo('All important system info:\n')
    ctx.vlog('bla bla bla, debug info')
