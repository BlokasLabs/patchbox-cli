import click
import subprocess

def get_serial():
    try:
        with open('/sys/kernel/pisound/serial', 'r') as f:
            data=f.read().replace('\n', '')
        return data
    except:
        return 'Pisound Not Found'

def get_version():
    try:
        with open('/sys/kernel/pisound/version', 'r') as f:
            data=f.read().replace('\n', '')
        return data
    except:
        return 'Pisound Not Found'

def get_btn_version():
    try:
        check = subprocess.check_output(['which', 'pisound-btn'])
    except:
        return 'Not Installed'
    out = subprocess.check_output(['pisound-btn', '--version'])
    return str(out.decode("utf-8")).split(' ')[1].strip(',')

def get_ctl_version():
    try:
        check = subprocess.check_output(['which', 'pisound-ctl'])
    except:
        return 'Not Installed'
    out = subprocess.check_output(['pisound-ctl', '--version'])
    return str(out.decode("utf-8")).split(' ')[4].strip(',')

def get_ip():
    out = subprocess.check_output(['hostname', '-I'])
    return str(out.decode("utf-8")).strip()

def get_hostname():
    out = subprocess.check_output(['hostname'])
    return str(out.decode("utf-8")).strip()

@click.command()
def cli():
    """Display system info."""
    message = 'Button Version: {}'\
        '\nServer Version: {}\nFirmware Version: {}'\
        '\nSerial Number: {}\nIP Address: {}'\
        '\nHostname: {}'.format(get_btn_version(), get_ctl_version(), get_version(), get_serial(), get_ip(), get_hostname())
    click.echo(message)
