import subprocess
import shlex
import click
import os
import time
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive, get_system_service_property


def get_cards():
    cards = []
    with open('/proc/asound/cards', 'r') as f:
        for line in f:
            if ']:' in line:
                card_id = line.split('[')[0].strip()
                card_name = line.split('[')[1].split(']')[0].strip()
                card_title = line.split(':')[1].split('-')[0].strip()
                cards.append({'key': card_id, 'value': card_name, 'description': card_title})
    return cards


def jack_installed():
    try:
        subprocess.check_output(['which', 'jackd'])
        return True
    except:
        return False


def jack_start():
    try:
        subprocess.call(['sudo', 'systemctl', 'start', 'jack'])
        click.echo('Jack service started!')
    except:
        raise
        raise click.ClickException('Failed to start Jack service!')


def jack_verify():
    try:
        click.echo('Waiting for Jack to boot...', err=True)
        ec = subprocess.call(['jack_wait','-w','-t','5'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ec == 0:
            state = get_system_service_property('jack', 'SubState')
            if state == 'running':
                click.echo('Jack is running!', err=True)
        else:
            raise click.ClickException('Failed to start Jack service! Please check Jack configuration.')
    except:
        raise click.ClickException('Failed to start Jack service! Try different settings!')



def jack_restart():
    try:
        subprocess.call(['sudo', 'systemctl', 'restart', 'jack'])
        click.echo('Jack service restarted!')
    except:
        raise click.ClickException('Failed to restart Jack service!')


def jack_stop():
    try:
        subprocess.call(['sudo', 'systemctl', 'stop', 'jack'])
        click.echo('Jack service stopped!')
    except:
        raise click.ClickException('Failed to stop Jack service!')


def get_jack_config():
    cfg = []

    with open('/etc/jackdrc', 'r') as f:
        args = None
        for line in f:
            if not line.startswith('exec'):
                continue
            args = shlex.split(line)
            break
        i = 0
        while i < len(args)-1:
            if args[i].startswith('-'):
                if not args[i+1].startswith('-'):
                    cfg.append([args[i], args[i+1]])
                    i += 1
                else:
                    cfg.append(args[i])
                    if len(args) - i == 2:
                        cfg.append(args[i+1])
            else:
                cfg.append(args[i])
            i += 1
    return cfg


def update_jack_config(param, value):
    with open('/etc/jackdrc', 'rt') as f:
        data = f.readlines()
        for i, line in enumerate(data):
            if line.startswith('exec'):
                line = ''
                for p in get_jack_config():
                    if isinstance(p, list):
                        if p[0] == param:
                            if p[1] != 'alsa':
                                line += '{} {} '.format(param, value)
                                continue
                        line += '{} {} '.format(p[0], p[1])
                        continue
                    line += p + ' '
                data[i] = line + '\n'
                break
    with open('/etc/jackdrc', 'w') as f:
        f.writelines(data)


def get_status():
    properties = {'active_state': 'ActiveState', 'sub_state': 'SubState'}
    results = 'jack_installed={}\n'.format(int(jack_installed()))
    for prop in properties:
        value = get_system_service_property('jack', properties.get(prop)) or 'unknown'
        results += '{}_service_{}={}\n'.format('jack', prop, value)
    return results.rstrip()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage Jack settings"""
    do_group_menu(ctx)


@cli.command()
def start():
    """Start Jack service"""
    jack_start()
    do_go_back_if_ineractive()


@cli.command()
def stop():
    """Stop Jack service"""
    jack_stop()
    do_go_back_if_ineractive()


@cli.command()
def restart():
    """Restart Jack service"""
    jack_restart()
    do_go_back_if_ineractive()


@cli.command()
def status():
    """Display Jack service status"""
    click.echo(get_status())
    do_go_back_if_ineractive()


@cli.command()
@click.option('--card', help='Set default soundcard (-d)', type=click.Choice(get_cards))
@click.option('--rate', help='Set sample rate compatible with your Soundcard (-r), use 48000, 96000 or 192000 with Pisound', type=click.Choice(['44100', '48000', '96000', '192000']))
@click.option('--buffer', help='Set buffer size (-p), recommended value: 128', type=click.Choice(['64', '128', '256', '512', '1024']))
@click.option('--period', help='Set period (-n), recommended value: 2', type=click.Choice(['2', '3', '4', '5', '6', '7', '8', '9']))
@click.pass_context
def config(ctx, card, rate, buffer, period):
    """Update Jack service settings"""

    if card is None and rate is None and buffer is None and period is None:
        ctx.meta['interactive'] = True

    if not jack_installed():
        raise click.ClickException('Jack software not found!')
    card = do_ensure_param(ctx, 'card')
    if card:
        update_jack_config('-d', 'hw:{}'.format(card.get('value')))
    rate = do_ensure_param(ctx, 'rate')
    if rate:
        update_jack_config('-r', rate)
    buffer = do_ensure_param(ctx, 'buffer')
    if buffer:
        update_jack_config('-p', buffer)
    period = do_ensure_param(ctx, 'period')
    if period:
        update_jack_config('-n', period)
    if card or rate or buffer or period:
        jack_restart()
        jack_verify()
    do_go_back_if_ineractive(ctx)
