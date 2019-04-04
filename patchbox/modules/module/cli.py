import os
import click
import json
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive, get_system_service_property
from patchbox.module import PatchboxModuleManager, ModuleNotFound, ModuleNotInstalled, ModuleError, ModuleManagerError
from patchbox.views import do_msgbox, do_yesno, do_menu, do_inputbox
from patchbox.utils import do_go_back_if_ineractive, run_interactive_cmd


def get_module(ctx, name, silent=False):
    try:
        return ctx.obj.get_module(name)
    except (ModuleNotFound, ModuleError) as err:
        if silent:
            return None
        raise click.ClickException(str(err))


@click.group(invoke_without_command=False)
@click.pass_context
def cli(ctx):
    """Manage Patchbox modules"""
    ctx.obj = PatchboxModuleManager()
    if ctx.invoked_subcommand is None:
        if ctx.meta.get('interactive'):
            ctx.invoke(ctx.command.get_command(ctx, 'config'))


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
        except ModuleManagerError as err:
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
def launch(ctx, name, arg):
    """Launch module"""
    module = get_module(ctx, name)
    try:
        ctx.obj.launch(module, arg)
    except ModuleManagerError as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
@click.argument('name')
def stop(ctx, name):
    """Stop module"""
    module = get_module(ctx, name)
    try:
        ctx.obj.stop(module)
    except ModuleManagerError as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
@click.argument('name')
@click.argument('arg', default=False)
@click.option('--autolaunch/--no-autolaunch', default=True)
@click.option('--autoinstall/--no-autoinstall', default=False)
def activate(ctx, name, arg, autolaunch, autoinstall):
    """Activate module"""
    name = do_ensure_param(ctx, 'name')
    module = get_module(ctx, name)
    try:
        ctx.obj.activate(module, autolaunch=autolaunch, autoinstall=autoinstall)
    except ModuleManagerError as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
def config(ctx):
    """Module configuration wizard (Interactive)"""
    manager = ctx.obj
    if not isinstance(manager, PatchboxModuleManager):
        manager = PatchboxModuleManager()
    close, value = do_menu('Choose a module:', manager.get_valid_modules(), cancel='Cancel')
    if close:
        return
    module = manager.get_module(value.get('value'))
    manager.activate(module, autolaunch=False)
    if module.autolaunch:
        arg = None
        if module.autolaunch == 'list':
            options = manager.list(module)
            close, arg = do_menu('Choose an option for autolaunch on boot', options, cancel='Cancel')
            if close:
                return
        if module.autolaunch == 'argument':
            close, arg = do_inputbox('Enter an argument for autolaunch on boot')
            if close:
                manager._set_autolaunch_argument(module, None)
                return
        if module.autolaunch == 'path':
            while True:
                close, arg = do_inputbox('Enter a path for autolaunch on boot')
                if close:
                    manager._set_autolaunch_argument(module, None)
                    return
                if os.path.isfile(arg) or os.path.isdir(arg):
                    break
                do_msgbox('Argument must be a valid file path')
        if arg:
            manager._set_autolaunch_argument(module, arg)
            
        
        close, value = do_yesno('Do you want to launch now?')
        if close == 0:
            manager.launch(module, arg=arg)

    do_go_back_if_ineractive(ctx, silent=True, steps=2)
