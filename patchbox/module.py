import subprocess
import json
import os
from shutil import rmtree, copytree, Error as shutil_error
import glob
import zipfile
import tarfile
from patchbox.state import PatchboxModuleStateManager
from patchbox.service import PatchboxServiceManager, PatchboxService, ServiceError

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')


class ModuleNotInstalled(Exception):
   def __init__(self, module_name, *args):
        self.message = '{}.module is not installed yet. install it first'.format(module_name)    
        super(ModuleNotInstalled, self).__init__(self.message, *args)


class ModuleNotFound(Exception):
   def __init__(self, module_name, *args):
        self.message = 'module not found. is {}.module installed?'.format(module_name)    
        super(ModuleNotFound, self).__init__(self.message, *args) 


class ModuleArgumentError(Exception):
    pass


class ModuleError(Exception):
    pass


class ModuleManagerError(Exception):
    def __init__(self, message, remove_dir=None, *args):
        self.message = message
        if remove_dir:
            self._clean_tmp_dir(remove_dir)
        super(ModuleManagerError, self).__init__(self.message, *args)

    
    def _clean_tmp_dir(self, remove_dir):
        rmtree(dir)
        print('Manager: {} directory deleted'.format(remove_dir)) 


class PatchboxModule(object):

    DEFAULT_MODULE_FILE = 'patchbox-module.json'
    REQUIRED_MODULE_FILES = ['install.sh', 'patchbox-module.json']
    REQUIRED_MODULE_KEYS = ['name', 'description', 'version', 'author']
    SYSTEM_SERVICES_KEY = 'depends_on'
    MODULE_SERVICES_KEY = 'services'

    def __init__(self, path):
        self.path = path if path.endswith('/') else path + '/'
        self.name = path.split('/')[-1]
        self._module = self.parse_module_file()
        self.description = self._module.get('description')
        self.autolaunch = self.get_autolaunch_mode()
        self.scripts = self._module.get('scripts', dict())
        self.errors = []

    def parse_module_file(self):
        path = self.path + self.__class__.DEFAULT_MODULE_FILE
        try:
            with open(path) as f:
                data = json.load(f)
                module_keys = [k for k in data]
                for k in self.__class__.REQUIRED_MODULE_KEYS:
                    if k not in module_keys:
                        raise ModuleError('{}.module is not valid: "{}" key not defined in {}'.format(self.name, k, path))
                for service_type in [self.__class__.SYSTEM_SERVICES_KEY, self.__class__.MODULE_SERVICES_KEY]:
                    if not isinstance(data.get(service_type, []), list):
                        raise ModuleError('{}.module is not valid: "{}" key must be a list'.format(self.name, service_type))
                    for i, service in enumerate(data.get(service_type, [])):
                        if isinstance(service, dict) and service.get('config'):
                            if not os.path.isfile(self.path + service.get('config').rstrip('/')):
                                raise ModuleError('{}.module file {} not found'.format(self.name, service.get('config')))
                            else:
                                data[service_type][i]['config'] = self.path + service.get('config').rstrip('/')
                for key in data.get('scripts', dict()):
                    if data.get('scripts', dict()).get(key) and not os.path.isfile(self.path + data.get('scripts', dict()).get(key).rstrip('/')):
                        raise ModuleError('{}.module file {} not found'.format(self.name, data.get('scripts', dict()).get(key)))
                return data
        except ValueError:
            raise ModuleError('{}.module file ({}) formatting is not valid'.format(self.name, path))

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
            return [PatchboxService(service) for service in ss]
        return []

    def module_services(self):
        ss = self._module.get(self.__class__.MODULE_SERVICES_KEY)
        if ss:
            return [PatchboxService(service) for service in ss]
        return []

    def status(self):
        services = self._module.get(self.__class__.SYSTEM_SERVICES_KEY, dict()).keys(
        ) + self._module.get(self.__class__.MODULE_SERVICES_KEY, dict()).keys()
        status = {'module_valid': self.valid,
                  'module_installed': self.installed}
        return status
    
    def pre_install_validate(self, service_manager=PatchboxServiceManager()):
        for system_service in self.system_services:
            break
        pass



class PatchboxModuleManager(object):

    DEFAULT_MODULES_FOLDER = '/usr/local/patchbox-modules'
    DEFAULT_SERVICE_MANAGER = PatchboxServiceManager
    IGNORED_MODULES = ['system', 'tmp']

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
            if not os.path.isdir(module_path):
                continue
            if module_path.split('/')[-1] in self.__class__.IGNORED_MODULES:
                continue
            try:
                module = PatchboxModule(module_path)
                modules.append(module)
            except ModuleError as err:
                pass          
        return modules
    
    def get_valid_modules(self):
        return [{'value': module.name, 'description': module.description} for module in self.modules]
    
    def get_module(self, module_name, custom_path=None):
        """
        checks if module already loaded
        loads it if not
        returns
        """
        if not custom_path:
            for module in self.modules:
                if module.name == module_name:
                    return module

        path = self.path + str(module_name) if not custom_path else custom_path + str(module_name)
        if not os.path.isdir(path):
            raise ModuleNotFound(module_name)

        module = PatchboxModule(path)
        if not module.is_valid():
            raise ModuleError(' '.join(module.errors))
    
        if not custom_path:
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
    
    def stop(self):        
        active = self.get_active_module()
        if not active:
            raise ModuleManagerError(
                'no active module found')            

        if module.has_stop:
            self._stop_module(module)
        else:
            raise ModuleManagerError(
                '{}.module does not support stop command'.format(module.name))

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

    def install(self, path):
        tmp_dir = self.path + 'tmp/'
        tar_file_path = None
        zip_file_path = None
        module_name = None

        if os.path.isdir(path):
            raise ModuleManagerError('module file can\'t be a directory: {}'.format(path))

        if tarfile.is_tarfile(path):
            tar_file_path = path
        
        if zipfile.is_zipfile(path):
            zip_file_path = path
        
        if not tar_file_path and not zip_file_path:
            raise ModuleManagerError('{} is not a valid file type: *.tar and *.zip files are supported'.format(path))
        
        print('Manager: extracting {} to {}'.format(path, tmp_dir))
        try:
            if tar_file_path:
                tar_file = tarfile.open(tar_file_path)
                tar_file.extractall(path=tmp_dir)
                tar_file.close()

            if zip_file_path:
                zip_file = zipfile.ZipFile(zip_file_path, 'r')
                zip_file.extractall(tmp_dir)
                zip_file.close()

            files = glob.glob(tmp_dir + '*')
            if len(files) > 1 or not os.path.isdir(files[0]):
                raise Exception

            module_name = files[0].split('/')[-1]
            print('Manager: {}.module found'.format(module_name))
        except:
            raise ModuleManagerError('{} module extraction failed'.format(path), remove_dir=tmp_dir)

        module = self.get_module(module_name, custom_path=tmp_dir)

        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(str(module)), remove_dir=tmp_dir)

        if not module.is_valid():
            raise ModuleManagerError(
                "{}.module is not valid: {}".format(module.name, module.errors), remove_dir=tmp_dir)
        print('Manager: {}.module is valid'.format(module.name)) 

        if os.path.isdir(self.path + module_name):
            print('Manager: old {}.module deleted'.format(module.name))
            rmtree(self.path + module_name)
        
        try:
            copytree(tmp_dir + module_name, self.path + module_name)
        except (shutil_error, OSError) as e:
            raise ModuleManagerError(
                "{}.module copy failed".format(module.name), remove_dir=tmp_dir)
        print('Manager: {}.module prepared for installation'.format(module.name))        
        
        try:
            self._install_module(module)
        except ModuleError as err:
            raise ModuleManagerError(
                "{}.module installation failed".format(module.name), remove_dir=self.path + module_name)
        
        rmtree(tmp_dir)

    def _install_module(self, module):
        if module.has_install:
            print('Manager: {}.module install script found'.format(module.name))
            try:
                subprocess.call(
                    ['sudo', 'chmod', '+x', module.path + str(module.has_install)])
                subprocess.call(['sudo', 'sh', module.path + str(module.has_install)])
            except:
                raise ModuleError(
                    'Failed to install {}.module via {} script'.format(self.name, module.path + str(module.has_install)))
        else:
            print('Manager: no install script declared for {}.module'.format(module.name))
        self.state.set('installed', True, module.name)

    def activate(self, module, autolaunch=True, autoinstall=False):
        # if not isinstance(module, PatchboxModule):
        #     raise ModuleManagerError('{} is not a valid module'.format(str(module)))

        if not self.state.get('installed', module.name):
            if not autoinstall:
                raise ModuleNotInstalled(module.name)
            self._install_module(module)

        current = self.get_active_module()
        if current and current.name != module.name:
            self._stop_module(current)
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
        if module.system_services():
            for service in module.system_services():
                self._service_manager.reset_unit_environment(service)            
        self.state.set_active_module(None)
    
    def _set_autolaunch_argument(self, module, arg):
        self.state.set('autolaunch', arg, module.name)

    def status(self):
        return self._state
