import subprocess
import click
import os
from os.path import isfile, join, expanduser
from patchbox import settings

INTERACTIONS = ['CLICK_1', 'CLICK_2', 'CLICK_3', 
        'CLICK_OTHER', 'HOLD_1S', 'HOLD_3S', 'HOLD_5S', 'HOLD_OTHER', 'CLICK_COUNT_LIMIT']

def prepare_btn_config():
    keys = INTERACTIONS
    
    if not isfile(settings.BTN_CFG):
            with open(settings.BTN_CFG, 'w') as f:
                for key in keys:
                    f.writelines(key + '\t' + settings.BTN_SCRIPTS_DIR + '/do_nothing.sh' '\n')
    
    with open(settings.BTN_CFG, 'r') as f:
        missing_keys = []
        data = f.read()
        for key in keys:
                if str(key) not in data:
                    missing_keys.append(key)

    with open(settings.BTN_CFG, 'r') as f:
        lines = f.readlines()
    
    if len(missing_keys) > 0:
        for key in missing_keys:
            if key == 'CLICK_COUNT_LIMIT':
                lines.append(str(key + '\t' + '8' '\n'))
                continue
            lines.append(str(key + '\t' + settings.BTN_SCRIPTS_DIR + '/do_nothing.sh' '\n'))

        with open(settings.BTN_CFG, 'w') as f:
            f.writelines(sorted(lines))

def get_btn_config():
    prepare_btn_config()
    items = []
    with open(settings.BTN_CFG, 'r') as f:
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

def get_btn_scripts():
    path = settings.BTN_SCRIPTS_DIR
    return [{'title': f.split('.')[0].replace('_', ' ').title(), 'value': join(path, f)} for f in os.listdir(path) if isfile(join(path, f)) and f.endswith(".sh")]


def update_btn_config(param, value):
    with open(settings.BTN_CFG, 'r') as f:
        data = f.readlines()
        for i, line in enumerate(data):
            if line.startswith(param):
                data[i] = param + '\t' + value + '\n'
                break
    with open(settings.BTN_CFG, 'w') as f:
        f.writelines(data)


def get_btn_version():
    try:
        check = subprocess.check_output(['which', 'pisound-btn'])
        out = subprocess.check_output(['pisound-btn', '--version'])
        return str(out.decode("utf-8")).split(' ')[1].strip(',')
    except:
        return None


def is_supported():
    try:
        subprocess.check_output(['which', 'pisound-btn'])
        return True
    except:
        return False


def get_status():
    status = 'installed={}'.format(int(is_supported()))
    version = get_btn_version()
    if version:
        status += '\nversion={}'.format(version)
    return status


@click.group(invoke_without_command=False)
@click.pass_context
def cli(ctx):
    """Manage Pisound Button."""


@cli.command()
def interactions():
    """List all supported Button interactions"""
    if not is_supported():
        raise click.ClickException('Button software not found!')
    for interaction in INTERACTIONS:
        click.echo(interaction)


@cli.command()
def status():
    """Button status"""
    click.echo(get_status())


@cli.command()
def actions():
    """List all supported Button actions"""
    if not is_supported():
        raise click.ClickException('Button software not found!')
    for action in get_btn_scripts():
        path = action.get('value')
        if path:
            click.echo(path)


@cli.command()
def config():
    """Display Button config"""
    if not is_supported():
        raise click.ClickException('Button software not found!')
    for option in get_btn_config():
        line = option.get('key', 'UNKNOWN') + ': ' + option.get('path', 'unknown')
        click.echo(line)


@cli.command()
@click.option('--interaction', help='Button interaction.')
@click.option('--actions', help='Button action.')
@click.pass_context
def assign(ctx, interaction, actions):
    """Assign different Button interaction to different actions. Yes, it does sound funny."""
    if not is_supported():
        raise click.ClickException('Button software not found!')
    prepare_btn_config()
    if not interaction:
        raise click.ClickException(
            'Button interaction not provided! Use --interaction INTERACTION option.')
    if not actions:
        raise click.ClickException(
            'Button action not provided! Use --action ACTION option.')
    if interaction != 'CLICK_COUNT_LIMIT' and not isfile(action):
        raise click.ClickException('Button action script not found!')
    update_btn_config(interaction, action)
    