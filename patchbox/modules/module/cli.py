import os
import click
import json
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive, get_system_service_property
from patchbox.module import PatchboxModuleManager, ModuleNotFound, ModuleNotInstalled, ModuleError, ModuleManagerError
from patchbox.views import do_msgbox, do_yesno, do_menu, do_inputbox
from patchbox.utils import do_go_back_if_ineractive, run_interactive_cmd


def get_module_by_name(ctx, name, silent=False):
    try:
        return ctx.obj.get_module_by_name(name)
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
    """Initiate manager (System)"""
    manager = ctx.obj or PatchboxModuleManager()
    try:
        manager.init()
    except (ModuleManagerError, ModuleError) as err:
        raise click.ClickException(str(err))


@cli.command()
@click.argument('name', default='')
@click.pass_context
def list(ctx, name):
    """List available modules"""
    manager = ctx.obj
    if name:
        module = get_module_by_name(ctx, name)
        try:
            lst = manager.list(module)
            for l in lst:
                click.echo(l)
        except ModuleManagerError as err:
            raise click.ClickException(str(err))
    else:
        for module in manager.get_all_modules():
            click.echo('{}'.format(module.path))


@cli.command()
@click.pass_context
def active(ctx):
    """Display active module"""
    active_name = ctx.obj.state.get('active_module')
    if active_name:
        click.echo(active_name)


@cli.command()
@click.pass_context
@click.argument('path', type=click.Path(exists=True))
def install(ctx, path):
    """Install module from file"""
    try:
        ctx.obj.install(path)
    except ModuleManagerError as err:
        raise click.ClickException(str(err))

@cli.command()
@click.pass_context
def status(ctx):
    """Module manager status"""
    click.echo(ctx.obj.status())


@cli.command()
@click.pass_context
def deactivate(ctx):
    """Deactivate active module"""
    try:
        ctx.obj.deactivate()
    except ModuleManagerError as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
@click.argument('name')
@click.argument('arg', default=False)
def launch(ctx, name, arg):
    """Launch module"""
    module = get_module_by_name(ctx, name)
    try:
        ctx.obj.launch(module, arg)
    except ModuleManagerError as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop active module"""
    try:
        ctx.obj.stop()
    except ModuleManagerError as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
@click.argument('name')
@click.argument('arg', default=False)
@click.option('--autolaunch/--no-autolaunch', default=True, is_flag=True)
@click.option('--autoinstall/--no-autoinstall', default=True, is_flag=True)
def activate(ctx, name, arg, autolaunch, autoinstall):
    """Activate module by name"""
    name = do_ensure_param(ctx, 'name')
    module = get_module_by_name(ctx, name)
    try:
        ctx.obj.activate(module, autolaunch=autolaunch, autoinstall=autoinstall)
    except (ModuleManagerError, ModuleNotInstalled) as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
def restart(ctx):
    """Restart active module"""
    active_path = ctx.obj.state.get('active_module')
    if not active_path:
        return
    module = ctx.obj.get_active_module()
    try:
        ctx.obj.deactivate()
        ctx.obj.activate(module)
    except (ModuleManagerError, ModuleNotInstalled) as err:
        raise click.ClickException(str(err))


@cli.command()
@click.pass_context
def config(ctx):
    """Configuration wizard (Interactive)"""
    manager = ctx.obj
    if not isinstance(manager, PatchboxModuleManager):
        manager = PatchboxModuleManager()
    
    options = [{'value': module.path, 'title': '{}: {} v{}'.format(module.name, module.description, module.version)} for module in manager.get_all_modules()]
    options = sorted(options, key=lambda k: k.get('title')) 
    options.append({'value': 'none', 'title': 'none: Default Patchbox OS environment'})
    
    close, value = do_menu('Choose a module:', options, cancel='Cancel')
    
    if close:
        do_go_back_if_ineractive(ctx, steps=2, silent=True)
        return
    
    if value.get('value') == 'none':
        manager.deactivate()
        do_go_back_if_ineractive(ctx, steps=2)
        return

    module = manager.get_module_by_path(value.get('value'))
    manager.activate(module, autolaunch=False, autoinstall=True)

    for ser in [s for s in module.get_module_services() if s.auto_start == False]:
        
        close, value = do_yesno('Do you want to start {} now?'.format(ser.name))
        if close == 0:
            manager._service_manager.enable_start_unit(ser)
        else:
            manager._service_manager.stop_disable_unit(ser)

    if module.autolaunch:
        arg = None
        
        if module.autolaunch == 'auto':
            pass

        if module.autolaunch == 'list':
            options = manager.list(module)
            close, arg = do_menu('Choose an option for autolaunch on boot', options, cancel='Cancel')
            if close:
                manager._set_autolaunch_argument(module, None)
                do_go_back_if_ineractive(ctx, steps=2)
                return
        
        if module.autolaunch == 'argument':
            close, arg = do_inputbox('Enter an argument for autolaunch on boot')
            if close:
                manager._set_autolaunch_argument(module, None)
                do_go_back_if_ineractive(ctx, steps=2)
                return
        
        if module.autolaunch == 'path':
            while True:
                close, arg = do_inputbox('Enter a path for autolaunch on boot')
                if close:
                    manager._set_autolaunch_argument(module, None)
                    do_go_back_if_ineractive(ctx, steps=2)
                    return
                
                if os.path.isfile(arg) or os.path.isdir(arg):
                    break
                do_msgbox('Argument must be a valid file path')
        
        if arg:
            manager._set_autolaunch_argument(module, arg)            
        
        close, value = do_yesno('Do you want to launch now?')
        if close == 0:
            manager.launch(module, arg=arg)

    do_go_back_if_ineractive(ctx, steps=2)
