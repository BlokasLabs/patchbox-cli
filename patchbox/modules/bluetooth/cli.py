import os
import glob
import subprocess
import re
import click
from patchbox.utils import do_group_menu, do_go_back_if_ineractive


def get_system_service_property(name, prop):
    return subprocess.check_output(['systemctl', 'show', '-p', prop, '--value', name]).strip()


def get_devices():
    try:
        devices = []
        cmd = subprocess.Popen(['rfkill', 'list', 'bluetooth'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in cmd.stdout.readlines():
            if 'Bluetooth' in line:
                devices.append(line.split(':')[1].strip())
        return devices 
    except:
        click.echo("'rfkill' utility unresponsive.", err=True)
        return []

def is_supported():
    return len(get_devices()) > 0


def get_rfkill_bluetooth_status():
    result = ''
    try:
        cmd = subprocess.Popen(['rfkill', 'list', 'bluetooth'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in cmd.stdout.readlines():
            if not 'Bluetooth' in line:
                result += 'bluetooth_' + line.lower().strip().replace(': ', '=').replace(' ', '_') + '\n'
        return result  
    except:
        click.echo("'rfkill' utility unresponsive.", err=True)
        return result


def get_status():
    services = ['bluetooth', 'bluealsa', 'hciuart']
    properties = {'active_state': 'ActiveState', 'sub_state': 'SubState'}
    results = 'bluetooth_supported={}\n'.format(int(is_supported()))
    for service in services:
        for prop in properties:
            value = get_system_service_property(service, properties.get(prop)) or 'unknown'
            results += '{}_service_{}={}\n'.format(service, prop, value)
    results += get_rfkill_bluetooth_status()
    return results


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage Bluetooth"""
    do_group_menu(ctx)


@cli.command()
def status():
    """Display Bluetooth status"""
    click.echo(get_status().strip())
    do_go_back_if_ineractive()


@cli.command()
def start():
    """Start Bluetooth device pairing"""
    if not is_supported():
        raise click.ClickException('Bluetooth is not supported!')
    subprocess.call(['/usr/local/pisound/scripts/pisound-btn/system/set_bt_discoverable.sh', 'true'])
    do_go_back_if_ineractive(silent=True)


@cli.command()
def stop():
    """Stop Bluetooth device pairing"""
    if not is_supported():
        raise click.ClickException('Bluetooth is not supported!')
    subprocess.call(['/usr/local/pisound/scripts/pisound-btn/system/set_bt_discoverable.sh', 'false'])
    do_go_back_if_ineractive(silent=True)
