import sys
import subprocess
import os
from os.path import isfile
from inspect import isfunction
import click
from patchbox import views
from click.termui import prompt, confirm
from patchbox.views import do_msgbox, do_yesno

class PatchboxChoice(click.ParamType):
	"""Dictionary support for click.Choice"""

	name = 'choice'

	def __init__(self, choices, case_sensitive=True):
		self.type = 'list'
		self.choices = choices
		self.case_sensitive = case_sensitive
		if self.choices:
			if isfunction(self.choices):
				self.type = 'callback'
			elif isinstance(self.choices[0], dict):
				self.type = 'dict'

	def get_metavar(self, param):
		if self.type == 'dict':
			return '[%s]' % '|'.join([c.get('value') for c in self.choices])
		if self.type == 'callback':
			return '{}'.format(self.choices.__name__)
		return '[%s]' % '|'.join(self.choices)

	def get_missing_message(self, param):
		if isfunction(self.choices):
			return ''
		if self.choices:
			message = 'Choose from:\n\t'
			for choice in self.choices:
				if isinstance(choice, str):
					message += '{}\n\t'.format(choice)
				if isinstance(choice, dict):
					value = choice.get('value')
					if value:
						message += '{}\n\t'.format(value)
			return message.rstrip()
		return 'No choices found.'

	def get_choices(self):
		if self.type == 'callback':
			return self.choices()
		return self.choices

	def convert(self, value, param, ctx):
		# Exact match
		if self.type == 'callback':
			choices = self.choices()
		else:
			choices = self.choices

		if self.type == 'dict':
			for c in choices:
				if c.get('value') == value:
					return c

		if self.type == 'list':
			if value in choices:
				return value

		# Match through normalization and case sensitivity
		# first do token_normalize_func, then lowercase
		# preserve original `value` to produce an accurate message in
		# `self.fail`
		normed_value = value
		normed_choices = choices

		if ctx is not None and \
		   ctx.token_normalize_func is not None:
			normed_value = ctx.token_normalize_func(value)
			normed_choices = [ctx.token_normalize_func(choice) for choice in
							  choices]

		if not self.case_sensitive:
			normed_value = normed_value.lower()
			normed_choices = [choice.lower() for choice in normed_choices]

		if normed_value in normed_choices:
			return normed_value

		if self.type == 'list':
			self.fail('invalid choice: %s. (choose from %s)' %
					  (value, ', '.join(choices)), param, ctx)

		if self.type == 'dict':
			self.fail('invalid choice: %s. (choose from %s)' % (
				value, ', '.join(c.get('value') for c in choices)), param, ctx)

	def __repr__(self):
		if self.type == 'callback':
			return 'PatchboxChoice(%r)' % self.choices
		return 'PatchboxChoice(%r)' % list(self.choices or [c.get('value') for c in self.choices])


modules_folder = os.path.abspath(
	os.path.join(os.path.dirname(__file__), 'modules'))


class PatchboxHomeGroup(click.MultiCommand):

	def __init__(self, *args, **kwargs):
		self.is_home = True
		super(PatchboxHomeGroup, self).__init__(
			invoke_without_command=True, *args, **kwargs)

	def list_commands(self, ctx):
		rv = []
		for module in next(os.walk(modules_folder))[1]:
			if os.path.isfile(os.path.join(modules_folder, module, 'cli.py')):
				rv.append(module)
		rv.sort()
		return rv

	def get_command(self, ctx, name):
		if sys.version_info[0] == 2:
			name = name.encode('ascii', 'replace')
		mod = __import__('patchbox.modules.{}.cli'.format(name),
							None, None, ['cli'])

		return mod.cli


def run_cmd(list, silent=True):
	""" Runs bash command, returns is_error, output"""
	try:
		output = subprocess.check_output(list).decode('utf-8')
		return False, output
	except:
		if not silent:
			raise click.ClickException(
				'Operation failed: {}'.format(' '.join([i for i in list])))
		return True, None


def run_cmd_bg(list, silent=True):
	""" Runs bash command, returns is_error, output"""
	try:
		output = subprocess.Popen(list, preexec_fn=os.setpgrp)
	except:
		if not silent:
			raise click.ClickException(
				'Operation failed: {}'.format(' '.join([i for i in list])))


def write_file(path, content, silent=True):
	if not isfile(path) and not silent:
		raise click.ClickException('File not found!')
	try:
		with open(path, 'w') as f:
			f.write(content)
		return False
	except Exception as e:
		click.echo(e, err=True)
		return True


def go_home_or_exit(ctx):
	if ctx.meta.get('wizard'):
		return
	context = ctx
	while context.parent is not None:
		if isinstance(context.parent.command, PatchboxHomeGroup):
			if ctx.command != context.parent.command:
				ctx.invoke(context.parent.command)
		context = context.parent
	ctx.exit()


def do_group_menu(ctx, cancel=None, ok=None):
	if ctx.invoked_subcommand is None:
		if ctx.meta.get('interactive', False):
			# click.clear()
			options = []
			commands = ctx.command.list_commands(ctx)
			for command in commands:
				options.append({'key': command, 'value': command,
								'description': ctx.command.get_command(ctx, command).__doc__})
			if not cancel and ctx.parent:
				cancel = 'Back'
			description = ctx.command.help + ctx.meta.get('additional_description', '')
			try:
				del ctx.meta['additional_description']
			except KeyError:
				pass
			close, output = views.do_menu(
				description, options, ok=ok, cancel=cancel)
			if close:
				go_home_or_exit(ctx)
			if output:
				cmd = None
				if isinstance(output, dict):
					cmd = output.get('value')
				if isinstance(output, str):
					cmd = output
				ctx.invoke(ctx.command.get_command(ctx, cmd))
		else:
			click.echo(ctx.command.get_help(ctx))


def do_ensure_param(ctx, name):
	param = None
	close = None
	value = ctx.params.get(name)

	if value:
		return value

	for p in ctx.command.params:
		if p.name == name:
			param = p
			break

	if not param:
		raise click.ClickException(
			'"{}" parameter is not registered via decorator.'.format(name))

	message = '{}'.format(ctx.command.help)
	if hasattr(param, 'help'):
		message += '\n{}'.format(param.help)

	if not ctx.meta.get('interactive', False):
		value = param.get_default(ctx)
		return value

	if isinstance(param.type, click.Choice):
		close, value = views.do_menu(
			message, param.type.get_choices(), cancel='Cancel')
		if param.type == dict:
			for option in param.choices:
				if option.get('value') == value:
					value = option

	if isinstance(param.type, click.types.StringParamType):
		close, value = views.do_inputbox(message)

	if isinstance(param.type, click.types.IntParamType):
		close, value = views.do_inputbox(message)

	if close:
		go_home_or_exit(ctx)

	return value

def do_pause_if_interactive(ctx = None):
	if not ctx:
		ctx = click.get_current_context()
	if ctx.meta.get('interactive'):
		click.echo("\nPress any key to continue...", err=True)
		click.getchar()
		click.echo()

def do_go_back_if_ineractive(ctx=None, silent=False, steps=1):
	if not ctx:
		ctx = click.get_current_context()
		
	if ctx.meta.get('interactive'):
		if not silent:
			click.echo("\nPress any key to continue...", err=True)
			click.getchar()
			click.echo()
		if ctx.meta.get('wizard'):
			return

		context = ctx
		for step in range(steps):
			if context.parent and context.parent.command:
				context = context.parent
			else:
				context.invoke(context.parent)
				return
	
		ctx.invoke(context.command)


def get_system_service_property(name, prop):
	return subprocess.check_output(['systemctl', 'show', '-p', prop, '--value', name]).strip().decode('utf-8')


def run_interactive_cmd(ctx, command=None, args=None, message="Let's begin!", error="Oops! Something ain't right. Let's try again.", required=False):
	if required:
		do_msgbox(message)
	while command:
		if not required:
			no, output = do_yesno(message)
			if no:
				break
		try:
			if args and isinstance(args, dict):
				ctx.invoke(command, **args)
			else:
				ctx.invoke(command)
			break
		except Exception as err:
			print(str(err))
			do_msgbox(error)
