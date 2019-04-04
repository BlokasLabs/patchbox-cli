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
   def __init__(self, module_name, *args):
        self.message = '{}.module is not installed yet. install it first'.format(module_name)    
        super(ModuleNotFound, self).__init__(self.message, *args) 


class ModuleNotFound(Exception):
   def __init__(self, module_name, *args):
        self.message = 'module not found. is {}.module installed?'.format(module_name)    
        super(ModuleNotFound, self).__init__(self.message, *args) 


class ModuleArgumentError(Exception):
    pass


class ModuleError(Exception):
    pass


class ModuleManagerError(Exception):
    pass


class PatchboxModule(object):

    DEFAULT_MODULE_FILE = 'patchbox-module.json'
    REQUIRED_MODULE_FILES = ['install.sh', 'patchbox-module.json']
    SYSTEM_SERVICES_KEY = 'depends_on'
    MODULE_SERVICES_KEY = 'services'

    def __init__(self, path, filename=None):
        self.path = path if path.endswith('/') else path + '/'
        self.name = path.split('/')[-1]
        self._module = self.get_module(filename)
        self.description = self._module.get('description', 'module has no description')
        self.autolaunch = self.get_autolaunch_mode()
        self.scripts = self._module.get('scripts', dict())
        self.errors = []

    def get_module(self, filename):
        filename = filename or self.__class__.DEFAULT_MODULE_FILE
        path = self.path + filename
        try:
            with open(path) as f:
                return json.load(f)
        except ValueError:
            raise ModuleError('{}.module file ({}) is not valid'.format(self.name, path))

    @property
    def has_install(self):
        return self._module.get('scripts', dict()).get('install')

    @property
    def has_list(self):
        return self._module.get('scripts', dict()).get('list')

    @property
    def has_launch(self):
        return self._module.get('scripts', dict()).get('launch')

    @property
    def has_stop(self):
        return self._module.get('scripts', dict()).get('stop')

    def get_autolaunch_mode(self):
        autolaunch = self._module.get('launch_mode')
        if not autolaunch:
            return False
        if str(autolaunch) == 'list':
            return 'list'
        if str(autolaunch) == 'argument':
            return 'argument'
        if str(autolaunch) == 'path':
            return 'path'
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
        return status


class PatchboxModuleManager(object):

    DEFAULT_MODULES_FOLDER = '/usr/local/patchbox-modules'
    DEFAULT_SERVICE_MANAGER = PatchboxServiceManager

    def __init__(self, path=None, service_manager=None):
        self.path = self._verify_path(path)
        self.state = PatchboxModuleStateManager()
        self._service_manager = service_manager or self.__class__.DEFAULT_SERVICE_MANAGER()
        self.modules = self.parse_modules()

    def _verify_path(self, path):
        path = path or self.__class__.DEFAULT_MODULES_FOLDER
        path = path if path.endswith('/') else path + '/'
        if not os.path.isdir(path):
            raise ModuleManagerError(
                '"patchbox-modules" folder not found in "{}"'.format(self.path))
        return path

    def parse_modules(self):
        modules = []
        for module_path in glob.glob(self.path + '*'):
            try:
                module = PatchboxModule(module_path)
                modules.append(module)
            except ModuleError as err:
                pass          
        return modules
    
    def get_valid_modules(self):
        return [{'value': module.name, 'description': module.description} for module in self.modules]
    
    def get_module(self, module_name):
        """
        checks if module already loaded
        loads it if not
        returns
        """
        for module in self.modules:
            if module.name == module_name:
                return module

        path = self.path + str(module_name)
        if not os.path.isdir(path):
            raise ModuleNotFound(module_name)

        module = PatchboxModule(path)
        if not module.is_valid():
            raise ModuleError(' '.join(module.errors))

        self.modules.append(module)
        return module

    def get_active_module(self):
        module_name = self.state.get('active_module')
        if module_name:
            return self.get_module(module_name)
        return None

    def init(self):
        module = self.get_active_module()
        if module:
            self.activate(module)
            if module.autolaunch:
                try:
                    self._launch_module(module)
                except (ServiceError, ModuleError, ModuleArgumentError) as error:
                    print('Manager: ERROR: {}'.format(error))
                    self._stop_module(module)

    def launch(self, module, arg=None):
        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(str(module)))

        if not self.state.get('installed', module.name):
            raise ModuleNotInstalled(module.name)
        
        if not module.has_launch:
            raise ModuleManagerError(
            '{}.module does not support launch command'.format(module.name))
        
        current = self.get_active_module()
        if not current or current.name != module.name:
            if current:
                self._stop_module(current)
                self._deactivate_module(current)
            try:
                self._activate_module(module)
            except (ServiceError, ModuleError, ModuleManagerError) as error:
                print('Manager: ERROR: {}'.format(error))
                self._deactivate_module(module)
                return
        
        try:
            self._launch_module(module, arg=arg)
        except (ServiceError, ModuleError, ModuleArgumentError) as error:
            print('Manager: ERROR: {}'.format(error))
            self._stop_module(module)

    def _launch_module(self, module, arg=None):
        if not module.has_launch:
            return

        print('Manager: {}.module launch mode is {}'.format(module.name, module.autolaunch))
        arg = arg or self.state.get('autolaunch', module.name)

        if arg:
            print('Manager: {}.module launch argument is {}'.format(module.name, arg))

        if module.autolaunch in ['list', 'argument', 'path'] and not arg:
            raise ModuleArgumentError(
                '{}.module launch argument is missing'.format(module.name))

        if module.autolaunch == 'list':
            options = self.list(module)
            if arg not in options:
                raise ModuleArgumentError(
                    '{}.module launch argument "{}" is not valid'.format(module.name, arg))
        
        if module.autolaunch == 'path':
            if not os.path.isfile(arg):
                raise ModuleArgumentError(
                    '{}.module launch argument "{}" is not valid'.format(module.name, arg))                

        if module.autolaunch == 'auto':
            arg = None

        try:
            if arg:
                subprocess.Popen(['sh', module.path + module.has_launch, arg],
                                 stdout=DEVNULL, stderr=DEVNULL)
            else:
                subprocess.Popen(['sh', module.path + module.has_launch],
                                 stdout=DEVNULL, stderr=DEVNULL)
        except Exception as err:
            raise ModuleError(
                'failed to launch {}.module {}'.format(module.name, err))
        print('Manager: {}.module launched'.format(module.name))
    
    def stop(self, module):
        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(str(module)))
        
        active = self.get_active_module()
        if not active or active.name != module.name:
            raise ModuleManagerError(
            '{}.module is not active'.format(module.name)) 

        self._stop_module(module)

    def _stop_module(self, module):
        if module.has_stop:
            try:
                subprocess.Popen(['sh', module.path + module.has_stop],
                                 stdout=DEVNULL, stderr=DEVNULL)
            except:
                raise ModuleManagerError(
                    'failed to stop {}.module'.format(module.name))
            print('Manager: {}.module stopped'.format(module.name))
            return
        raise ModuleManagerError(
            '{}.module does not support stop command'.format(module.name))

    def list(self, module):
        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(str(module)))

        if module.has_list:
            try:
                output = subprocess.check_output(
                    ['sh', module.path + module.has_list])
                return [item for item in output.rstrip().split('\n') if item]
            except:
                raise ModuleError(
                    '{}.module listing error'.format(module.name))
        raise ModuleManagerError(
            '{}.module does not support list command'.format(module.name))

    def install(self, module):
        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(str(module)))

        if not module.is_valid():
            raise ModuleError(
                "{}.module is not valid: {}".format(module.name, module.errors))

        self._install_module(module)

    def _install_module(self, module):
        if module.has_install:
            print('Manager: {}.module install launched'.format(module.name))
            try:
                subprocess.call(
                    ['sudo', 'chmod', '+x', module.path + str(module.has_install)])
                subprocess.call(['sudo', 'sh', module.path + str(module.has_install)])
            except:
                raise ModuleManagerError(
                    'Failed to install {}.module via {} script'.format(self.name, module.path + str(module.has_install)))
        else:
            print('Manager: no install script declared for {}.module'.format(module.name))
        self.state.set('installed', True, module.name)

    def activate(self, module, autolaunch=True, autoinstall=False):
        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(str(module)))

        if not self.state.get('installed', module.name):
            if not autoinstall:
                raise ModuleNotInstalled(module.name)
            self._install_module(module)

        current = self.get_active_module()
        if current and current.name != module.name:
            self._deactivate_module(current)
        try:
            self._activate_module(module)
        except (ServiceError, ModuleError) as error:
            print('Manager: ERROR: {}'.format(error))
            self._deactivate_module(module)
            return
        if module.autolaunch and autolaunch:
            try:
                self._launch_module(module)
            except (ServiceError, ModuleError, ModuleArgumentError) as error:
                print('Manager: ERROR: {}'.format(error))
                self._stop_module(module)

    def _activate_module(self, module):
        if module.system_services():
            for service in module.system_services():
                self._service_manager.enable_start_unit(service)

        if module.module_services():
            for service in module.module_services():
                self._service_manager.enable_start_unit(service)

        self.state.set_active_module(module.name)

    def deactivate(self):
        current = self.get_active_module()
        if current:
            self._stop_module(current)
            self._deactivate_module(current)

    def _deactivate_module(self, module):
        if module.module_services():
            for service in module.module_services():
                self._service_manager.stop_disable_unit(service)
        self.state.set_active_module(None)
    
    def _set_autolaunch_argument(self, module, arg):
        self.state.set('autolaunch', arg, module.name)

    def status(self):
        return self._state
