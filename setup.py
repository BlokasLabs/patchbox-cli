#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
	name='patchbox-cli',
	version='1.4.0',
	packages=find_packages(),
	include_package_data=True,
	install_requires=[
		'click', 'urwid', 'dbus-python', 'python-dotenv'
	],
	package_data={
			'patchbox.modules': [
				'scripts/import_raspi_config.sh'
			],
			'patchbox.modules.boot': [
				'scripts/set_boot_to_console.sh',
				'scripts/set_boot_to_desktop.sh'
			],
			'patchbox.modules.module': [
				'scripts/patchbox_init_as_user.sh',
				'scripts/patchbox_stop_as_user.sh'
			],
			'patchbox.modules.update': [
				'scripts/update.sh'
			],
			'patchbox.modules.kernel': [
				'scripts/backup_kernel.sh',
				'scripts/install_kernel_reg.sh',
				'scripts/install_kernel_rt.sh',
				'scripts/restore_backedup_modules.sh'
			],
			'patchbox.modules.wifi': [
				'scripts/connect_wifi.sh',
				'scripts/get_wifi_country.sh',
				'scripts/set_wifi_country.sh',
				'scripts/set_hs_password.sh',
				'scripts/set_hs_ssid.sh',
			]
		},
	data_files=[
		('share/applications', ['patchbox-init.desktop', 'patchbox-stop.desktop']),
		('/etc/xdg/autostart', ['patchbox-init.desktop']),
		('share/patchbox-cli', ['version'])
	],
	entry_points='''
		[console_scripts]
		patchbox-config=patchbox.cli:cli
		patchbox=patchbox.cli:cli
	''',
)
