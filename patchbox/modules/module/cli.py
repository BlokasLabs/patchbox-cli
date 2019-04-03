import click
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive, get_system_service_property
from patchbox.manager import PatchboxModuleManager, PatchboxModuleNotFound


def get_module(ctx, name, silent=False):
    try:
        return ctx.obj.get_module(name)
    except PatchboxModuleNotFound:
        if silent:
            return None
        raise click.ClickException(
            'Module "{name}" not found! Place module files inside "{dir}{name}/" directory.'.format(name=name, dir=ctx.obj.path))


@click.group(invoke_without_command=False)
@click.pass_context
def cli(ctx):
    """Manage Patchbox modules"""
    ctx.obj = PatchboxModuleManager()
    do_group_menu(ctx)


@cli.command() 
@click.pass_context
def init(ctx):
    """Activate Patchbox Module Manager"""
    manager = ctx.obj
    manager.init()


@cli.command()
@click.argument('name', default='')
@click.pass_context
def list(ctx, name):
    """List available modules"""
    manager = ctx.obj
    if name:
        module = get_module(ctx, name)
        lst = manager.list(module)
        for l in lst:
            click.echo(l)
    else:    
        active_name = ctx.obj.state.get('active')
        for module in manager.modules:
            active = 'inactive'
            installed = 'not_installed'
            if module.name == active_name:
                active = 'active'
            if module.installed:
                installed = 'installed'
            if not module.valid:
                continue
            click.echo('{} {}|{}'.format(module.name, active, installed))


@cli.command()
@click.pass_context
def current(ctx):
    """Display actived module"""
    active_name = ctx.obj.state.get('active')
    if active_name:
        click.echo(active_name)


@cli.command()
@click.pass_context
@click.argument('name')
def install(ctx, name):
    """Install module"""
    module = get_module(ctx, name)
    ctx.obj.install(module)


@cli.command()
@click.argument('name', default='')
@click.pass_context
def status(ctx, name):
    """Module manager status"""
    status = ''
    module = get_module(ctx, name, silent=True)
    if module:
        for key, value in module.status().items():
            status += '{}={}\n'.format(key, value)
    else:
        active = ctx.obj.state.get('active')
        status = 'active_module={}\n'.format(active)
    click.echo(status.rstrip('\n'))


@cli.command()
@click.pass_context
@click.argument('name')
def activate(ctx, name):
    """Activate module"""
    module = get_module(ctx, name)
    ctx.obj.activate(module)


@cli.command()
@click.pass_context
def deactivate(ctx):
    """Deactivate active module"""
    ctx.obj.deactivate()


@cli.command()
@click.pass_context
@click.argument('name')
@click.argument('arg', default=False)
def start(ctx, name, arg):
    """Start module"""
    module = get_module(ctx, name)
    ctx.obj.start(module, arg)