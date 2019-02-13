import click
from patchbox.cli import pass_store


@click.command('init', short_help='Configure Pisound Button.')
@click.argument('path', required=False, type=click.Path(resolve_path=True))
@pass_store
def cli(ctx, path):
    """Configure Pisound Button."""
    ctx.log('Initialized the repository in %s',
            click.format_filename(path))
