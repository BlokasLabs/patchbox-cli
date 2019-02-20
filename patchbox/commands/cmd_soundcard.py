import subprocess
import click
import os
from os.path import isfile, expanduser
from patchbox.utils import do_group_root, ensure_param


def get_cards():
    cards = []
    with open('/proc/asound/cards', 'r') as f:
        for line in f:
            if ']:' in line:
                card_id = line.split('[')[0].strip()
                card_name = line.split(':')[1].split('-')[0].strip()
                cards.append({'key': card_id, 'value': card_name})
    return cards


def get_active_card():
    if not isfile(expanduser('~' + os.environ['SUDO_USER']) + '/.asoundrc'):
        with open(expanduser('~' + os.environ['SUDO_USER']) + '/.asoundrc', 'w') as f:
            f.write(
                'pcm.!default {\n\ttype hw\n\tcard 0\n}\n\nctl.!default {\n\ttype hw\n\tcard 0\n}\n')

    active_card = {}
    with open(expanduser('~' + os.environ['SUDO_USER']) + '/.asoundrc', 'r') as f:
        for line in f:
            if 'card' in line:
                active_card['key'] = line.split(' ')[1].strip()
                break

    for card in get_cards():
        if card['key'] == active_card['key']:
            active_card['value'] = card['value']
            break

    return(active_card)


def set_active_card(card):
    with open(expanduser('~' + os.environ['SUDO_USER']) + '/.asoundrc', 'r') as f:
        data = f.readlines()
        for i, line in enumerate(data):
            if str(card['current']) in line:
                data[i] = data[i].replace(
                    str(card['current']), str(card['key']))
    with open(expanduser('~' + os.environ['SUDO_USER']) + '/.asoundrc', 'w') as f:
        f.writelines(data)
        click.echo('Active Soundcard set.', err=True)


def is_supported():
    if len(get_cards()) > 0:
        return True
    return False


def get_status():
    active_card = get_active_card()
    if active_card.get('value'):
        return 'active_system_soundcard={}'.format(active_card.get('value'))
    return 'active_system_soundcard=none'


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Manage Soundcards"""
    do_group_root(ctx)
    

@cli.command()
def list():
    """List available system Soundcards"""
    if not is_supported():
        raise click.ClickException('No supported Soundcard found!')
    for card in get_cards():
        click.echo(card.get('value'))


@cli.command()
def status():
    """Show active system Soundcard"""
    click.echo(get_status())


@cli.command()
@click.option('--name', help='Soundcard name.')
@click.pass_context
def set(ctx, name):
    """Set active system Soundcard"""
    if not is_supported():
        raise click.ClickException('No supported Soundcard found!')
    cards = get_cards()
    options = [card.get('value') for card in cards]
    name = ensure_param(ctx, name, required=True, options=cards, required_message='Soundcard name not provided! Use --name SOUNDCARD_NAME option.')
    if not name:
        raise click.ClickException('Soundcard not found!')
    active_card = get_active_card()
    if active_card:
        selected_card['current'] = active_card['key']
    set_active_card(selected_card)
