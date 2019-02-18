import subprocess
import click
import os
from os.path import isfile, expanduser


def get_cards():
    cards = []
    with open('/proc/asound/cards', 'r') as f:
        for line in f:
            if ']:' in line:
                card_id = line.split('[')[0].strip()
                card_name = line.split(':')[1].split('-')[0].strip()
                cards.append({'key': card_id, 'title': card_name})
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
            active_card['title'] = card['title']
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
        click.echo('Active soundcard set.', err=True)


def is_supported():
    if len(get_cards()) > 0:
        return True
    return False


def get_status():
    active_card = get_active_card()
    if active_card.get('title'):
        return 'active_soundcard={}'.format(active_card.get('title'))
    return 'active_soundcard=none'


@click.group(invoke_without_command=False)
@click.pass_context
def cli(ctx):
    """Manage Soundcards."""


@cli.command()
def list():
    """List available system soundcards"""
    if not is_supported():
        raise click.ClickException('No supported soundcard found!')
    for card in get_cards():
        click.echo(card.get('title'))


@cli.command()
def status():
    """Show active soundcard"""
    click.echo(get_status())

@cli.command()
def config():
    """Show '.asoundrc' config"""
    with open(expanduser('~' + os.environ['SUDO_USER']) + '/.asoundrc', 'r') as f:
        data = f.readlines()
        for line in data:
            click.echo(line.rstrip())    


@cli.command()
@click.option('--name', help='Soundcard name.')
@click.pass_context
def set(ctx, name):
    """Set active soundcard"""
    if not is_supported():
        raise click.ClickException('No supported soundcard found!')
    if not name:
        raise click.ClickException(
            'Soundcard name not provided! Use --name SOUNDCARD_NAME option.')
    cards = get_cards()
    selected_card = None
    for card in cards:
        if card.get('title') == name:
            selected_card = card
    if not selected_card:
        raise click.ClickException('Soundcard not found!')
    active_card = get_active_card()
    if active_card:
        selected_card['current'] = active_card['key']
    set_active_card(selected_card)
