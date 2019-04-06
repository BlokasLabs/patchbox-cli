import subprocess
import click
import os
from os.path import isfile, join, expanduser
from patchbox import settings
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive
from patchbox.environment import PatchboxEnvironment as penviron

class PisoundButton(object):

    INTERACTIONS = ['CLICK_1', 'CLICK_2', 'CLICK_3', 
        'CLICK_OTHER', 'HOLD_1S', 'HOLD_3S', 'HOLD_5S', 'HOLD_OTHER', 'CLICK_COUNT_LIMIT']

    def __init__(self, path=None):
        self.path = path or penviron.get('PISOUND_BTN_CFG', debug=False) or settings.BTN_CFG
        self.system_dir = settings.BTN_SCRIPTS_DIR
        self.module_dir = None
        
        active_module = penviron.get('PATCHBOX_MODULE_ACTIVE', debug=False)
        if active_module:
            self.module_dir = '/usr/local/patchbox-modules/{}/pisound-btn/'.format(active_module)


    def _get_system_actions(self):
        if self.system_dir == None:
            return []
        if not os.path.isdir(self.system_dir):
            return []
        return [join(self.system_dir, f) for f in os.listdir(self.system_dir) if isfile(join(self.system_dir, f)) and f.endswith(".sh")]

    
    def _get_module_actions(self):
        if self.module_dir == None:
            return []
        if not os.path.isdir(self.module_dir):
            return []
        return [join(self.module_dir, f) for f in os.listdir(self.module_dir) if isfile(join(self.module_dir, f)) and f.endswith(".sh")]

    
    def get_actions(self):
        all_scripts = self._get_module_actions() + self._get_system_actions()
        actions = [{'title': f.split('.')[0].replace('_', ' ').title(), 'value': f} for f in all_scripts]
        return actions

    def ensure_config(self, interactions=INTERACTIONS):
        keys = self.__class__.INTERACTIONS
        
        if not isfile(self.path):
                with open(self.path, 'w') as f:
                    for key in keys:
                        f.writelines(key + '\t' + self.system_dir + '/do_nothing.sh' '\n')
        
        with open(self.path, 'r') as f:
            missing_keys = []
            data = f.read()
            for key in keys:
                    if str(key) not in data:
                        missing_keys.append(key)

        with open(self.path, 'r') as f:
            lines = f.readlines()
        
        if len(missing_keys) > 0:
            for key in missing_keys:
                if key == 'CLICK_COUNT_LIMIT':
                    lines.append(str(key + '\t' + '8' '\n'))
                    continue
                lines.append(str(key + '\t' + self.system_dir + '/do_nothing.sh' '\n'))

            with open(self.path, 'w') as f:
                f.writelines(sorted(lines))

    def get_config(self):
        self.ensure_config()
        items = []
        with open(self.path, 'r') as f:
            for line in f:
                if len(line.strip()) != 0:
                    if 'UP' in line or 'DOWN' in line: 
                        continue
                    try:
                        interaction = line.split()[0]
                        script_path = line.split()[1]
                        script_name = script_path.split('/')[-1]
                        name = script_name.split('.')[0].replace('_', ' ').title()
                    except:
                        interaction = line.strip()
                        name = 'Not Set'
                    items.append({
                        'title': interaction + ': ' + name,
                        'key': interaction,
                        'value': name,
                        'path': script_path
                        })
        return items


    def update_config(self, param, value):
        with open(self.path, 'r') as f:
            data = f.readlines()
            for i, line in enumerate(data):
                if line.startswith(param):
                    data[i] = param + '\t' + value + '\n'
                    break
        with open(self.path, 'w') as f:
            f.writelines(data)


    def get_version(self):
        try:
            check = subprocess.check_output(['which', 'pisound-btn'])
            out = subprocess.check_output(['pisound-btn', '--version'])
            return str(out.decode("utf-8")).split(' ')[1].strip(',')
        except:
            return None


    def is_supported(self):
        try:
            subprocess.check_output(['which', 'pisound-btn'])
            return True
        except:
            return False


    def get_status(self):
        status = 'pisound_btn_installed={}'.format(int(self.is_supported()))
        version = self.get_version()
        if version:
            status += '\npisound_btn_version={}'.format(version)
            for option in self.get_config():
                status += '\n' + option.get('key', 'UNKNOWN') + '=' + option.get('path', 'unknown')
        return status


def INTERACTION():
    return PisoundButton.INTERACTIONS[:-1]

def ACTION():
    return PisoundButton().get_actions()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage Pisound Button"""
    ctx.obj = PisoundButton()
    do_group_menu(ctx)


@cli.command()
@click.pass_context
def interactions(ctx):
    """List all supported Button interactions"""
    if not ctx.obj.is_supported():
        raise click.ClickException('Button software not found!')
    for interaction in ctx.obj.INTERACTIONS:
        click.echo(interaction)
    do_go_back_if_ineractive()


@cli.command()
@click.pass_context
def status(ctx):
    """Display Button status"""
    if not ctx.obj.is_supported():
        raise click.ClickException('Button software not found!')
    click.echo(ctx.obj.get_status())
    do_go_back_if_ineractive()


@cli.command()
@click.pass_context
def actions(ctx):
    """List all supported Button actions"""
    if not ctx.obj.is_supported():
        raise click.ClickException('Button software not found!')
    for action in ctx.obj.get_actions():
        path = action.get('value')
        if path:
            click.echo(path)
    do_go_back_if_ineractive()


@cli.command()
@click.option('--interaction', help='Button interaction', type=click.Choice(INTERACTION))
@click.option('--action', help='Button action', type=click.Choice(ACTION))
@click.pass_context
def assign(ctx, interaction, action):
    """Assign different Button interaction to different actions"""
    if not ctx.obj.is_supported():
        raise click.ClickException('Button software not found!')

    interaction = do_ensure_param(ctx, 'interaction')
    action = do_ensure_param(ctx, 'action')
    
    if not interaction:
        raise click.ClickException(
            'Button interaction not provided! Use --interaction INTERACTION option.')
    
    if not action:
        raise click.ClickException(
            'Button action not provided! Use --action ACTION option.')
    
    ctx.obj.update_config(interaction, action.get('value'))
    do_go_back_if_ineractive(ctx, silent=True)
    