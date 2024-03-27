import os
import glob
import subprocess
import re
import click
import time
import struct
import json
from patchbox import settings
from patchbox.utils import run_cmd, do_group_menu, do_ensure_param, do_go_back_if_ineractive, run_interactive_cmd, go_home_or_exit, do_pause_if_interactive
from patchbox.views import do_yesno

def get_kernel_name():
	return subprocess.check_output(['uname', '-a']).decode('utf-8')

def is_realtime():
	return subprocess.call(['sh', '-c', 'uname -a | grep -q PREEMPT_RT']) == 0

# https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes
def code_to_mem_size_str(code):
	return {
		0: '256MB',
		1: '512MB',
		2: '1GB',
		3: '2GB',
		4: '4GB',
		5: '8GB',
	}.get(code, 'unknown')

def code_to_model_str(code):
	return {
		0x00: 'A',
		0x01: 'B',
		0x02: 'A+',
		0x03: 'B+',
		0x04: '2B',
		0x05: 'Alpha (early prototype)',
		0x06: 'CM1',
		0x08: '3B',
		0x09: 'Zero',
		0x0a: 'CM3',
		0x0c: 'Zero W',
		0x0d: '3B+',
		0x0e: '3A+',
		0x0f: 'Internal use only',
		0x10: 'CM3+',
		0x11: '4B',
		0x12: 'Zero 2 W',
		0x13: '400',
		0x14: 'CM4',
		0x15: 'CM4S',
		0x16: 'Internal use only',
		0x17: '5',
	}.get(code, 'unknown')

def get_hardware_info():
	rev = 0
	try:
		with open("/sys/firmware/devicetree/base/system/linux,revision", "rb") as f:
			rev = struct.unpack('!i', f.read(4))[0]
	except:
		return None

	model_id = (rev >> 4) & 0xff
	mem_size = (rev >> 20) & 0x07

	return {
		'rev_raw': rev,
		'model_id': model_id,
		'model_str': code_to_model_str(model_id),
		'mem_size': mem_size,
		'mem_str': code_to_mem_size_str(mem_size)
	}

@click.command(help='Install realtime kernel.')
@click.option('--yes', is_flag=True, help='Confirm action.')
@click.pass_context
def install_rt(ctx, yes):
	"""Switch the current kernel to realtime one."""
	if is_realtime():
		print("The kernel is already a realtime one.")
		do_go_back_if_ineractive()
		return

	is_interactive = ctx.meta.get('interactive', False)

	confirmed = yes
	if not confirmed and is_interactive:
		info = get_hardware_info()

		compatible = True

		if info['model_str'] in [ 'Zero', 'Zero W', 'A', 'B', 'A+', 'B+', '2B', '3B', '3B+' ]:
			compatible = False

		current_system_str = 'Raspberry Pi ' + info['model_str'] + ' ' + info['mem_str']

		message = "Please keep in mind that realtime kernel could be less stable and is not compatible with Pi Zero, Pi 2B or Pi 3B(+) versions.\n\n" + \
			"Your current system is " + current_system_str + "\n\n" + \
			("It is known to be compatible with your system." if compatible else "It is NOT COMPATIBLE and your system may fail to boot or work properly.") + "\n\n" + \
			"Continue?"

		no, output = do_yesno(message)
		confirmed = not no

	if confirmed:
		subprocess.call([os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/install_kernel_rt.sh')])
		do_pause_if_interactive(ctx)
	elif not is_interactive:
		print("This action may make your system unstable or not able to boot and must be confirmed by providing --yes option. Run it through `patchbox` menu for more information.")

	if is_interactive:
		go_home_or_exit(ctx)

@click.command(help='Install regular kernel.')
@click.pass_context
def install_reg(ctx):
	"""Switch the current kernel to regular one."""
	if not is_realtime():
		print("The kernel is already a regular one.")
		do_go_back_if_ineractive()
		return
	subprocess.call([os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts/install_kernel_reg.sh')])
	do_pause_if_interactive(ctx)
	if ctx.meta.get('interactive', False):
		go_home_or_exit(ctx)

class SwitchKernelCommand(click.MultiCommand):
	def __init__(self, *args, **kwargs):
		super(SwitchKernelCommand, self).__init__(*args, **kwargs)

	def list_commands(self, ctx):
		if ctx.meta.get('interactive'):
			cmds = [ 'install_rt' if not is_realtime() else 'install_reg' ]
		else:
			cmds = [ 'install_rt', 'install_reg' ]

		rv = []
		for cmd in cmds:
			rv.append(self.get_command(ctx, cmd).name)

		return rv

	def get_command(self, ctx, name):
		return { 'install_rt': install_rt, 'install_reg': install_reg, 'install-rt': install_rt, 'install-reg': install_reg }.get(name, None)

@click.command(cls=SwitchKernelCommand)
@click.pass_context
def cli(ctx):
	"""Kernel configuration"""

	desc = "\n\nThe current kernel is:\n\n%s" % get_kernel_name()
	desc += "\nIt's a %s kernel." % ('realtime' if is_realtime() else 'regular')

	ctx.meta['additional_description'] = desc;
	do_group_menu(ctx)
