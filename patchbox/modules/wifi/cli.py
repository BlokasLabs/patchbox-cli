import os
import glob
import subprocess
import re
import click
import time
from patchbox import settings
from patchbox.utils import run_cmd, do_group_menu, do_ensure_param, do_go_back_if_ineractive


def get_ifaces():
    return [p.split('/')[-2] for p in glob.glob('/sys/class/net/*/wireless')]


def get_default_iface():
    ifaces = get_ifaces()
    if len(ifaces) >= 1:
        return ifaces[0]
    return None

def local_script_path(script):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts', script)

def get_wifi_country():
    try:
        country=subprocess.check_output([local_script_path('get_wifi_country.sh')]).decode('utf-8')
        return country or 'unset'
    except:
        return 'unset'


def get_wifi_countries():
    try:
        countries = []
        with open('/usr/share/zoneinfo/iso3166.tab', 'rt') as f:
            for line in f.readlines():
                if line.startswith('#'):
                    continue
                countries.append({'value': line[:2], 'description': line[3:].strip()})
        return countries
    except:
        raise click.ClickException('WiFi countries file is missing!')


def do_save_config():
    try:
        cmd = subprocess.Popen(
            ['wpa_cli', '-i', get_default_iface(), 'save_config'], stdout=subprocess.PIPE)
    except:
        raise click.ClickException('Saving WiFi configuration failed!')


def set_wifi_country(country):
    if isinstance(country, dict):
        country = country.get('value')
    if not country or country.upper() not in [c.get('value') for c in get_wifi_countries()]:
        raise click.ClickException('Country code is not valid!')
    try:
        cmd = subprocess.Popen([local_script_path('get_wifi_country.sh'), country], stdout=subprocess.PIPE)
        click.echo('Country code set.', err=True)
    except:
        raise click.ClickException('Setting country code failed!')


def get_networks():
    ids = []
    try:
        cmd = subprocess.Popen(['wpa_cli', '-i', get_default_iface(),
                                'list_networks'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in cmd.stdout.readlines():
            line = line.decode('utf-8')
            if line.startswith('network'):
                continue
            try:
                network_id = line.split('\t')[0]
                if network_id.isdigit():
                    ids.append(network_id)
            except:
                continue
        return ids
    except:
        raise click.ClickException('Listing WiFi networks failed!')


def do_forget(network_id):
    try:
        cmd = subprocess.check_output(
            ['wpa_cli', '-i', get_default_iface(), 'remove_network', network_id])
        do_save_config()
    except:
        raise click.ClickException('Forget network failed!')


def do_forget_all():
    ids = get_networks()
    for id in ids:
        do_forget(id)

def do_connect(ssid, password):
    if not ssid:
        raise click.ClickException('Network name is invalid!')
    click.echo('Connecting to {}...'.format(ssid))
    return subprocess.call([local_script_path('connect_wifi.sh'), ssid, password])

def is_wifi_supported():
    return get_default_iface() is not None


def is_connected():
    try:
        return subprocess.check_output(['cat', '/sys/class/net/{}/operstate'.format(get_default_iface())]).strip().decode('utf-8') == 'up'
    except:
        return False


def do_disconnect():
    try:
        click.echo(subprocess.check_output(['nmcli', 'device', 'down', get_default_iface()]), err=True)
        click.echo('Disconnected.', err=True)
    except:
        raise click.ClickException('Operation failed!')


def do_verify_connection(hotspot_fallback=True):
    MAX_RETRIES = 10
    retries = 0
    while retries < MAX_RETRIES:
        if is_connected():
            click.echo('Connected.', err=True)
            return
        retries += 1
        time.sleep(2)
        click.echo(
            'Trying to connect to WiFi network ({}/{}).'.format(retries, MAX_RETRIES), err=True)
    click.echo('Connection failed.', err=True)
    if hotspot_fallback:
        click.echo('Activating hotspot.', err=True)
        do_hotspot_enable()


def do_reconnect(hotspot_fallback=True):
    if is_hotspot_active():
        click.echo('Disabling WiFi hotspot.', err=True)
        do_hotspot_disable()
    do_verify_connection(hotspot_fallback=hotspot_fallback)


def is_disabled():
    return 'wpa_state=INTERFACE_DISABLED' in get_wpa_status()


def do_enable():
    try:
        subprocess.call(
            ['sudo', 'ifconfig', get_default_iface(), 'up'])
        click.echo('WiFi enabled.', err=True)
    except:
        raise click.ClickException('Operation failed!')


def do_disable():
    try:
        subprocess.call(
            ['sudo', 'ifconfig', get_default_iface(), 'down'])
        click.echo('WiFi disabled.', err=True)
    except:
        raise click.ClickException('Operation failed!')


def get_wpa_status():
    try:
        return subprocess.check_output(['wpa_cli', '-i', get_default_iface(), 'status']).strip().decode('utf-8')
    except:
        return None


def get_status():
    return 'wifi_supported={}\ndefault_iface={}\nwifi_disabled={}\nwifi_connected={}\nhotspot_active={}\nwifi_country={}\n{}'.format(
        int(is_wifi_supported()),
        get_default_iface(),
        int(is_disabled()),
        int(is_connected()),
        int(is_hotspot_active()),
        get_wifi_country(),
        get_wpa_status()
    )


def get_ssids():
    click.echo('Network scan started.', err=True)
    try:
        scan = subprocess.check_output(
            ['sudo', 'iwlist', get_default_iface(), 'scan']).decode('utf-8')
        return re.findall('ESSID:"([^"]*)"', scan)
    except:
        raise click.ClickException('Scan failed!')


def get_hs_config():
    items = []
    lines = subprocess.check_output(
        ['sudo', 'nmcli', '-s', 'c', 'show', 'pb-hotspot']).decode('utf-8')
    for line in lines.splitlines():
        for p in ['802-11-wireless.ssid:', '802-11-wireless-security.psk:']:
            if line.startswith(p):
                param = line.strip().split(':')
                items.append(
                    {'title': p + ': ' + param[1].strip(), 'key': param[0], 'value': param[1].strip()})
    return items


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage WiFi"""
    do_group_menu(ctx)


# @cli.command()
def enable():
    """Enable WiFi interface"""
    if not is_wifi_supported():
        raise click.ClickException('WiFi interface not found!')
    do_enable()
    do_go_back_if_ineractive()


# @cli.command()
def disable():
    """Disable WiFi interface"""
    do_disable()
    do_go_back_if_ineractive()


@cli.command()
def disconnect():
    """Disconnect from default network"""
    do_disconnect()
    do_go_back_if_ineractive()


@cli.command()
def status():
    """Display WiFi status"""
    if not is_wifi_supported():
        raise click.ClickException('WiFi interface not found!')
    click.echo(get_status())
    do_go_back_if_ineractive()


@cli.command()
def scan():
    """List available WiFi networks"""
    if not is_wifi_supported():
        raise click.ClickException('WiFi interface not found!')
    if is_disabled():
        do_enable()
    ssids = get_ssids()
    for ssid in ssids:
        click.echo(ssid)
    do_go_back_if_ineractive()


@cli.command()
def reconnect():
    """Reconnect to default WiFi network"""
    try:
        subprocess.check_output(['nmcli', 'connection', 'up', 'ifname', get_default_iface()])
    except:
        pass
    do_reconnect()
    do_go_back_if_ineractive()


@cli.command()
@click.pass_context
@click.option('--name', help='WiFi network name (SSID)', required=True, type=click.Choice(get_ssids))
@click.option('--country', help='WiFi network country code (e.g. US, DE, LT)', type=click.Choice(get_wifi_countries()))
@click.option('--password', help='WiFi network password (Leave empty for unsecure networks)')
def connect(ctx, name, country, password):
    """Connect to WiFi network"""
    if not is_wifi_supported():
        raise click.ClickException('WiFi interface not found!')
    if is_disabled():
        do_enable()
    name = do_ensure_param(ctx, 'name')
    password = do_ensure_param(ctx, 'password')
    if country:
        set_wifi_country(country)
    elif get_wifi_country() == 'unset':
        country = do_ensure_param(ctx, 'country')
        if not country:
            raise click.ClickException(
                'WiFi country not set! Use --country COUNTRY_CODE option.')
    if not name:
        raise click.ClickException(
            'WiFi name (SSID) not set! Use --name NETWORK_NAME option.')
    do_forget_all()
    do_connect(name, password)
    do_reconnect()
    do_go_back_if_ineractive(ctx)


@cli.group(invoke_without_command=True)
@click.pass_context
def hotspot(ctx):
    """Manage WiFi hotspot"""
    do_group_menu(ctx)


def is_hotspot_active():
    error, output = run_cmd(['systemctl', 'is-active', 'wifi-hotspot', '--quiet'])
    if error:
        return False
    return True


@hotspot.command('up')
def hotspot_enable():
    """Enable WiFi hotspot"""
    do_hotspot_enable()
    do_go_back_if_ineractive()


def do_hotspot_enable():
    click.echo('Hotspot enable started.', err=True)
    error, output = run_cmd(['sudo', 'systemctl', 'enable', '--now', 'wifi-hotspot'])
    if not error:
        click.echo('Hotspot enabled.', err=True)


def do_hotspot_disable():
    click.echo('Hotspot disable started.', err=True)
    error, output = run_cmd(['sudo', 'systemctl', 'disable', '--now', 'wifi-hotspot'])
    if not error:
        click.echo('Hotspot disabled.', err=True)


@hotspot.command('down')
def hotspot_disable():
    """Disable WiFi hotspot"""
    if not is_wifi_supported():
        raise click.ClickException('WiFi interface not found!')
    do_hotspot_disable()
    do_go_back_if_ineractive()


@hotspot.command('status')
def hotspot_status():
    """Display WiFi hotspot status"""
    active = is_hotspot_active()
    click.echo('hotspot_active={}'.format(int(active)))
    for item in get_hs_config():
        line = '{}={}'.format(item.get('key'), item.get('value'))
        click.echo(line)
    do_go_back_if_ineractive()

def set_hs_ssid(ssid):
    subprocess.call([local_script_path('set_hs_ssid.sh'), ssid])

def set_hs_password(password):
    subprocess.call([local_script_path('set_hs_password.sh'), password])

@hotspot.command('setup')
@click.option('--name', help='Hotspot name (SSID)')
@click.option('--password', help='Hotspot WiFi network password')
@click.pass_context
def hotspot_config(ctx, name, password):
    """Change WiFi hotspot settings"""

    if name is None and password is None:
        ctx.meta['interactive'] = True

    if not is_wifi_supported():
        raise click.ClickException('WiFi interface not found!')
    name = do_ensure_param(ctx, 'name')
    password = do_ensure_param(ctx, 'password')
    if name:
        set_hs_ssid(name)
    if password:
        set_hs_password(password)
    if is_hotspot_active():
        do_hotspot_disable()
        do_hotspot_enable()
    do_go_back_if_ineractive(ctx, silent=True)
