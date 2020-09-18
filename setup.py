#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
	name='patchbox-cli',
	version='1.0',
	packages=find_packages(),
	include_package_data=True,
	install_requires=[
		'click', 'urwid', 'dbus-python', 'python-dotenv'
	],
	package_data={
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
		},
	entry_points='''
		[console_scripts]
		patchbox-config=patchbox.cli:cli
		patchbox=patchbox.cli:cli
	''',
)
