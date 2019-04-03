import subprocess
import json
import os
import glob
from patchbox.state import PatchboxModuleStateManager
from patchbox.service import PatchboxServiceManager, ServiceError

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')


class ModuleNotInstalled(Exception):
    pass


class ModuleNotFound(Exception):
    pass


class ModuleArgumentError(Exception):
    pass


class ModuleError(Exception):
    pass


class ModuleManagerError(Exception):
    pass


class PatchboxModule(object):

    REQUIRED_MODULE_FILES = ['install.sh', 'patchbox-module.json']
    SYSTEM_SERVICES_KEY = 'depends_on'
    MODULE_SERVICES_KEY = 'services'

    def __init__(self, path, service_manager=None):
        self.path = path if path.endswith('/') else path + '/'
        self._service_manager = service_manager or PatchboxServiceManager()

        self.name = path.split('/')[-1]
        self.autostart = self.get_autostart_mode()

        self.scripts = self._module.get('scripts', dict())

        self.valid = False

    @property
    def _module(self):
        with open(self.path + 'patchbox-module.json') as f:
            return json.load(f)
    
    def get_autostart_mode(self):
        autostart = self._module.get('autostart')
        if not autostart:
            return False
        if str(autostart) == 'list':
            return 'list' 
        if str(autostart) == 'argument': 
            return 'argument'
        return 'auto'

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
            raise ModuleManagerError(
                '"patchbox-modules" folder not found. "{}"'.format(self.path))
        self.state = PatchboxModuleStateManager()
        self.modules = self.parse_modules()
        self._service_manager = service_manager or self.__class__.DEFAULT_SERVICE_MANAGER()

    def init(self):
        active = self.get_active_module()
        if active:
            self.activate(active)
            if active.autostart:
                try:
                    self._start_module(module)
                except (ServiceError, ModuleError, ModuleArgumentError) as error:
                    print('pbmm: ERROR! {}'.format(error))
                    self._stop_module(module)

    def parse_modules(self):
        modules = []
        paths = glob.glob(self.path + '*')
        candidates = [PatchboxModule(p)
                      for p in paths]
        for m in candidates:
            if m.is_valid():
                m.valid = True
                if self.state.get('installed', m.name):
                    m.installed = True
            modules.append(m)
        return modules

    def get_module_names(self):
        return [module.name for module in self.modules]

    def get_module(self, name):
        for m in self.modules:
            if m.name == name:
                return m
        raise ModuleNotFound(name)

    def get_active_module(self):
        name = self.state.get('active_module')
        if name:
            return self.get_module(name)
        return None

    def _validate_start_argument(self, arg):
        pass

    def _start_module(self, module, arg=None):
        mode = module.autostart
        script = module.scripts.get('start')
        if not script:
            return True

        print('pbmm: {}.module start mode is {}'.format(module.name, mode))
        arg = arg or self.state.get('autostart', module.name)
        
        if arg:
            print('pbmm: {}.module start argument is {}'.format(module.name, arg))
        

        if str(mode) in ['list', 'argument'] and not arg:
                raise ModuleArgumentError(
                '{}.module start argument is missing'.format(module.name))            

        if str(mode) == 'list':
            options = self.list(module)
            if arg not in options:
                raise ModuleArgumentError(
                '{}.module start argument "{}" is not valid'.format(module.name, arg))
        
        if str(mode) == 'auto':
            arg = None

        try:
            if arg:
                subprocess.Popen(['sh', module.path + script, arg], stdout=DEVNULL, stderr=DEVNULL)
            else:
                subprocess.Popen(['sh', module.path + script], stdout=DEVNULL, stderr=DEVNULL)                
        except:
            raise ModuleManagerError(
                'failed to start {}.module'.format(module.name))
    
    def stop(self, module):
        self._stop_module(module)        

    def start(self, module, arg=None):
        if not self.state.get('installed', module.name):
            raise ModuleNotInstalled(
                '{}.module not installed'.format(module.name))
        current = self.get_active_module()
        if current != module:
            if current:
                self._stop_module(current)
                self._deactivate_module(current)
            try:
                self._activate_module(module)
            except (ServiceError, ModuleError, ModuleManagerError) as error:
                print('pbmm: ERROR {}'.format(error))
                self._deactivate_module(module)
                return
        try:
            self._start_module(module, arg=arg)
        except (ServiceError, ModuleError, ModuleArgumentError) as error:
            print('pbmm: ERROR {}'.format(error))
            self._stop_module(module)

    def _stop_module(self, module):
        script = module.scripts.get('stop')
        if script:
            try:
                subprocess.Popen(['sh', module.path + script], stdout=DEVNULL, stderr=DEVNULL)
            except:
                raise ModuleManagerError(
                    'failed to stop {}.module'.format(module.name))
        print('pbmm: {}.module stopped'.format(module.name))

    def list(self, module):
        has_list = module._module.get('scripts', dict()).get('list')
        if has_list:
            try:
                output = subprocess.check_output(['sh', module.path + has_list])
                return [item for item in output.rstrip().split('\n') if item]
            except:
                raise ModuleError('{}.module listing error'.format(module.name))
        raise ModuleError(
            '{}.module does not support listing'.format(module.name))

    def _install_module(self, module):
        try:
            subprocess.call(
                ['sudo', 'chmod', '+x', module.path + 'install.sh'])
            subprocess.call(['sudo', 'sh', module.path + 'install.sh'])
        except:
            raise ModuleManagerError(
                'Failed to install {}.module!'.format(self.name))

    def install(self, module):
        if not module.is_valid():
            raise ModuleError(
                "{}.module is not valid.".format(module.name))
        self._install_module(module)
        self.state.set('installed', True, module.name)

    def activate(self, module, autostart=True):
        if not self.state.get('installed', module.name):
            raise ModuleNotInstalled(
                '{}.module not installed'.format(module.name))
        current = self.get_active_module()
        if current and current != module:
            self._deactivate_module(current)
        try:
            self._activate_module(module)
        except (ServiceError, ModuleError, ModuleManagerError) as error:
            print('pbmm: ERROR! {}'.format(error))
            self._deactivate_module(module)
            return
        if module.autostart and autostart:
            try:
                self._start_module(module)
            except (ServiceError, ModuleError, ModuleArgumentError) as error:
                print('pbmm: ERROR! {}'.format(error))
                self._stop_module(module)


    def deactivate(self):
        current = self.get_active_module()
        if current:
            self._stop_module(current)
            self._deactivate_module(current)

    def _activate_module(self, module):
        if module.system_services():
            for service in module.system_services():
                success = self._service_manager.enable_and_start_unit_if_inactive(
                    service)
                if not success:
                    raise ServiceError(service)
        if module.module_services():
            for service in module.module_services():
                success = self._service_manager.enable_and_start_unit_if_inactive(
                    service)
                if not success:
                    raise ServiceError(service)
        self.state.set_active_module(module.name)
        print('pbmm: {}.module activated'.format(module.name))

    def _deactivate_module(self, module):
        if module.module_services():
            for service in module.module_services():
                self._service_manager.stop_disable_unit(service)
        self.state.set_active_module(None)
        print('pbmm: {}.module deactivated'.format(module.name))

    def status(self):
        return self.state
