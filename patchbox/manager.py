import subprocess
import json
import os
import glob
import dbus
from marshmallow import Schema, fields


class PatchboxModuleError(Exception):
    pass


class PatchboxServiceError(Exception):
    pass


class PatchboxModuleNotFound(Exception):
    pass


class PatchboxModulesDirNotFound(Exception):
    pass


class PatchboxModuleManagerState(object):

    DEFAULT_STATE_PATH = '/usr/local/patchbox-modules/system/state.json'

    def __init__(self, path=None):
        self.path = path or self.__class__.DEFAULT_STATE_PATH
        if not os.path.isfile(self.path):
            with open(self.path, 'w') as f:
                json.dump({'type': 'PatchboxModuleManagerState'}, f)
        with open(self.path) as f:
            self.data = json.load(f)

    def set(self, param, value, module=None):
        if module:
            try:
                self.data[module][param] = value
            except KeyError:
                self.data[module] = {}
                self.data[module][param] = value
        else:
            self.data[param] = value
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def get(self, param, module=None):
        if module:
            return self.data.get(module, dict()).get(param)
        return self.data.get(param)


class PatchboxServiceManager(object):

    UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"
    SERVICE_UNIT_INTERFACE = "org.freedesktop.systemd1.Service"

    def __init__(self):
        self.__bus = dbus.SystemBus()

    def start_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.StartUnit(unit_name, mode)
            print('PatchboxServiceManager: {} started.'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def enable_and_start_unit_if_inactive(self, unit_name, mode="replace"):
        if not self.is_active(unit_name):
            if not self.enable_unit(unit_name):
                return False
            if not self.start_unit(unit_name, mode=mode):
                return False
            return True
        print('PatchboxServiceManager: {} already active.'.format(unit_name))
        return True

    def stop_disable_unit(self, unit_name):
        if not self.stop_unit(unit_name):
            pass
        if not self.disable_unit(unit_name):
            pass

    def stop_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()

        if interface is None:
            return False
        try:
            interface.StopUnit(unit_name, mode)
            print('PatchboxServiceManager: {} stopped.'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def restart_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.RestartUnit(unit_name, mode)
            print('PatchboxServiceManager: {} restarted.'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def enable_unit(self, unit_name):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.EnableUnitFiles([unit_name],
                                      dbus.Boolean(False),
                                      dbus.Boolean(True))
            print('PatchboxServiceManager: {} enabled.'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def disable_unit(self, unit_name):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.DisableUnitFiles([unit_name], dbus.Boolean(False))
            print('PatchboxServiceManager: {} disabled.'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def _get_unit_file_state(self, unit_name):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            state = interface.GetUnitFileState(unit_name)
            return state
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def _get_interface(self):
        try:
            obj = self.__bus.get_object("org.freedesktop.systemd1",
                                        "/org/freedesktop/systemd1")
            return dbus.Interface(obj, "org.freedesktop.systemd1.Manager")
        except dbus.exceptions.DBusException as error:
            print(error)
            return None

    def get_active_state(self, unit_name):
        properties = self._get_unit_properties(unit_name, self.UNIT_INTERFACE)
        if properties is None:
            return False
        try:
            state = properties["ActiveState"].encode("utf-8")
            return state
        except KeyError:
            return False

    def is_active(self, unit_name):
        unit_state = self.get_active_state(unit_name)
        return unit_state == b"active"

    def is_failed(self, unit_name):
        unit_state = self.get_active_state(unit_name)
        return unit_state == b"failed"

    def get_error_code(self, unit_name):
        service_properties = self._get_unit_properties(
            unit_name, self.SERVICE_UNIT_INTERFACE)
        if service_properties is None:
            return None
        return self._get_exec_status(service_properties)

    def _get_exec_status(self, properties):
        try:
            exec_status = int(properties["ExecMainStatus"])
            return exec_status
        except KeyError:
            return None

    def _get_result(self, properties):
        try:
            result = properties["Result"].encode("utf-8")
            return result
        except KeyError:
            return False

    def _get_unit_properties(self, unit_name, unit_interface):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            unit_path = interface.LoadUnit(unit_name)
            obj = self.__bus.get_object(
                "org.freedesktop.systemd1", unit_path)
            properties_interface = dbus.Interface(
                obj, "org.freedesktop.DBus.Properties")
            return properties_interface.GetAll(unit_interface)
        except dbus.exceptions.DBusException as error:
            print(error)
            return None


class PatchboxModule(object):

    REQUIRED_MODULE_FILES = ['install.sh', 'patchbox-module.json']
    SYSTEM_SERVICES_KEY = 'depends_on'
    MODULE_SERVICES_KEY = 'services'

    def __init__(self, path, service_manager=None):
        self.path = path if path.endswith('/') else path + '/'
        self._service_manager = service_manager or PatchboxServiceManager()

        self.name = path.split('/')[-1]
        self.autostart = self._module.get('autostart', False)

        self.scripts = self._module.get('scripts', dict())

        self.valid = False

    @property
    def _module(self):
        with open(self.path + 'patchbox-module.json') as f:
            return json.load(f)

    def is_valid(self):
        required_files = self.__class__.REQUIRED_MODULE_FILES
        found_files = [f.split('/')[-1] for f in glob.glob(self.path + '*')]
        for f in required_files:
            if f not in found_files:
                return False
        return True

    def system_services(self):
        ss = self._module.get(self.__class__.SYSTEM_SERVICES_KEY)
        if ss:
            return list(ss.keys())
        return []

    def module_services(self):
        ss = self._module.get(self.__class__.MODULE_SERVICES_KEY)
        if ss:
            return list(ss.keys())
        return []

    def status(self):
        services = self._module.get(self.__class__.SYSTEM_SERVICES_KEY, dict()).keys(
        ) + self._module.get(self.__class__.MODULE_SERVICES_KEY, dict()).keys()
        status = {'module_valid': self.valid,
                  'module_installed': self.installed}
        for s in services:
            status[s] = self._service_manager.get_active_state(s)
        return status


class PatchboxModuleManager(object):

    DEFAULT_MODULES_FOLDER = '/usr/local/patchbox-modules'
    DEFAULT_SERVICE_MANAGER = PatchboxServiceManager

    def __init__(self, path=None, service_manager=None):
        path = path or self.__class__.DEFAULT_MODULES_FOLDER
        self.path = path if path.endswith('/') else path + '/'
        if not os.path.isdir(self.path):
            raise Exception(
                '"patchbox-modules" folder not found. "{}"'.format(self.path))
        self.state = PatchboxModuleManagerState()
        self.modules = self.parse_modules()
        self._service_manager = service_manager or self.__class__.DEFAULT_SERVICE_MANAGER()

    def init(self):
        active = self.get_active_module()
        if active:
            self.activate(active)
            if active.autostart:
                self._start_module(active)

    def parse_modules(self):
        modules = []
        paths = glob.glob(self.path + '*')
        candidates = [PatchboxModule(p)
                      for p in paths if not p.endswith('system')]
        for m in candidates:
            if m.is_valid():
                m.valid = True
                if self.state.get('installed', m.name):
                    m.installed = True
            modules.append(m)
        return modules

    def start(self, module, arg=False):
        print(os.environ.get('JACK_PROMISCUOUS_SERVER'))
        self._start_module(module, arg=arg)

    def _start_module(self, module, arg=False):
        print('PatchboxModuleManager: {}.module started (NOT).'.format(module.name))
        start_script = module.scripts.get('start')
        arg_required = module._module.get('arg_required')
        if start_script:
            if not arg and arg_required:
                raise PatchboxModuleError(
                    'argument is required for {}.module to start.'.format(module.name))
        try:
            output = subprocess.Popen(['sh', module.path + start_script, arg], preexec_fn=os.setpgrp)
            # subprocess.call()
        except:
            raise PatchboxModuleManagerError(
                'Failed to start {}.module!'.format(self.name))

    def list(self, module):
        has_list = module._module.get('scripts', dict()).get('list')
        if has_list:
            subprocess.call(['sh', module.path + has_list])
            return
        raise PatchboxModuleError(
            '{}.module does not support listing.'.format(module.name))

    def get_module_names(self):
        return [module.name for module in self.modules]

    def get_module(self, name):
        for m in self.modules:
            if m.name == name:
                return m
        raise PatchboxModuleNotFound(name)

    def get_active_module(self):
        name = self.state.get('active')
        if name:
            return self.get_module(name)
        return None

    def _install_module(self, module):
        try:
            subprocess.call(
                ['sudo', 'chmod', '+x', module.path + 'install.sh'])
            subprocess.call(['sudo', 'sh', module.path + 'install.sh'])
            self.state.set('installed', True, module=module.name)
        except:
            raise PatchboxModuleManagerError(
                'Failed to install {}.module!'.format(self.name))

    def install(self, module):
        if not module.is_valid():
            raise PatchboxModuleError(
                "{}.module is not valid.".format(module.name))
        self._install_module(module)

    def activate(self, module):
        current = self.get_active_module()
        if current and current != module:
            self._deactivate_module(current)
        try:
            self._activate_module(module)
        except (PatchboxServiceError, PatchboxModuleError) as error:
            print('PatchboxModuleManager:FatalError {}'.format(error))
            self._deactivate_module(module)
        if module.autostart:
            print('PatchboxModuleManager: {}.module has autostart enabled.'.format(
                module.name))
            self._start_module(module)

    def deactivate(self):
        current = self.get_active_module()
        if current:
            self._deactivate_module(current)

    def _activate_module(self, module):
        print('PatchboxModuleManager: {}.module activatation started.'.format(module.name))
        if not self.state.get('installed', module=module.name):
            raise PatchboxModuleManagerError(
                '{}.module not installed.'.format(module.name))
        if module.system_services():
            for service in module.system_services():
                success = self._service_manager.enable_and_start_unit_if_inactive(
                    service)
                if not success:
                    raise PatchboxServiceError(service)
        if module.module_services():
            for service in module.module_services():
                success = self._service_manager.enable_and_start_unit_if_inactive(
                    service)
                if not success:
                    raise PatchboxServiceError(service)
        self.state.set('active', module.name)

    def _deactivate_module(self, module):
        print('PatchboxModuleManager: {}.module deactivatation started.'.format(
            module.name))
        if module.module_services():
            for service in module.module_services():
                self._service_manager.stop_disable_unit(service)
        self.state.set('active', None)
