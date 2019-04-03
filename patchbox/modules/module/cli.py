import click
import json
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive, get_system_service_property
from patchbox.module import PatchboxModuleManager, ModuleNotFound, ModuleNotInstalled, ModuleError, ModuleManagerError


def get_module(ctx, name, silent=False):
    try:
        return ctx.obj.get_module(name)
    except ModuleNotFound:
        if silent:
            return None
        raise click.ClickException(
            '{name}.module not found! Place module files inside "{dir}{name}/" directory.'.format(name=name, dir=ctx.obj.path))

def get_module_names():
    return [module.name for module in PatchboxModuleManager().modules] 


@click.group(invoke_without_command=False)
@click.pass_context
def cli(ctx):
    """Manage Patchbox modules"""
    ctx.obj = PatchboxModuleManager()
    if ctx.invoked_subcommand is None:
        if ctx.meta.get('interactive'):
            ctx.invoke(ctx.command.get_command(ctx, 'setup'))


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
        try:
            lst = manager.list(module)
            for l in lst:
                click.echo(l)
        except ModuleError as err:
            raise click.ClickException(str(err))
    else:    
        for module in manager.modules:
            active = 'inactive'
            installed = 'not_installed'
            if manager.state.get('active', module.name):
                active = 'active'
            if manager.state.get('installed', module.name):
                installed = 'installed'
            click.echo('{} {}|{}'.format(module.name, active, installed))


@cli.command()
@click.pass_context
def active(ctx):
    """Display active module"""
    active_name = ctx.obj.state.get('active_module')
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
        click.echo(status.rstrip('\n'))
    else:
        status = ctx.obj.state.data
        click.echo(json.dumps(status, indent=4, sort_keys=True))


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
    try:
        ctx.obj.start(module, arg)
    except (ModuleNotInstalled, ModuleManagerError) as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
@click.argument('name')
def stop(ctx, name):
    """Stop module"""
    module = get_module(ctx, name)
    ctx.obj.stop(module)


@cli.command()
@click.pass_context
@click.argument('name')
@click.argument('arg', default=False)
@click.option('--autostart/--no-autostart', default=True)
def activate(ctx, name, arg, autostart):
    """Activate module"""
    module = get_module(ctx, name)
    try:
        ctx.obj.activate(module, autostart=autostart)
    except (ModuleNotInstalled, ModuleManagerError) as err:
        raise click.ClickException(str(err))


@cli.command()
@click.option('--module', help='Module', type=click.Choice(get_module_names))
#@click.option('--action', help='Button action', type=click.Choice(get_btn_scripts))
@click.pass_context
def setup(ctx, module):
    """Module configuration wizard (Interactive)"""
    module = do_ensure_param(ctx, 'module')
    # action = do_ensure_param(ctx, 'action')
    # if not interaction:
    #     raise click.ClickException(
    #         'Button interaction not provided! Use --interaction INTERACTION option.')
    # if not actions:
    #     raise click.ClickException(
    #         'Button action not provided! Use --action ACTION option.')
    # update_btn_config(interaction, action.get('value'))
    # print(dir(ctx.parent.parent))
    do_go_back_if_ineractive(ctx, silent=True, steps=2)