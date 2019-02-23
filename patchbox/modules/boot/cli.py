import subprocess
import click
import os
from os.path import isfile, expanduser
from patchbox.utils import do_group_menu, do_ensure_param, do_go_back_if_ineractive


def get_cards():
    cards = []
    with open('/proc/asound/cards', 'r') as f:
        for line in f:
            if ']:' in line:
                card_id = line.split('[')[0].strip()
                card_name = line.split(':')[1].split('-')[0].strip()
                cards.append({'key': card_id, 'value': card_name})
    return cards

def get_cards_names():
    return [card.get('value') for card in get_cards()]


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
        click.echo('Done! {} set as active system Soundcard.'.format(card.get('value')), err=True)


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
    """Manage Boot options"""
    do_group_menu(ctx)


@cli.command()
@click.argument('option', type=click.Choice(['desktop', 'console']))
@click.pass_context
def environment(ctx, option):
    """Choose Boot environment (Desktop or Console)"""
    option = do_ensure_param(ctx, 'option')
    if option == 'desktop':
        subprocess.call(['sudo', 'sh', '-c', os.path.dirname(os.path.realpath(__file__)) + '/scripts/set_boot_to_desktop.sh'])
    if option == 'console':
        subprocess.call(['sudo', 'sh', '-c', os.path.dirname(os.path.realpath(__file__)) + '/scripts/set_boot_to_console.sh'])
    do_go_back_if_ineractive()
