import subprocess
import json
import os
import requests
from shutil import rmtree, copytree, Error as shutil_error
from collections import defaultdict
import glob
import zipfile
import tarfile
import urllib
from urllib.parse import urlparse
from pathlib import Path
import tempfile
from enum import Enum
from patchbox.state import PatchboxModuleStateManager
from patchbox.service import PatchboxServiceManager, PatchboxService, ServiceError
from patchbox import settings

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')


class ModuleNotInstalled(Exception):
    def __init__(self, module_name, *args):
        self.message = '{}.module is not installed: activate it first'.format(
            module_name)
        super(ModuleNotInstalled, self).__init__(self.message, *args)


class ModuleNotFound(Exception):
    def __init__(self, module_name, *args):
        self.message = 'module not found. is {}.module installed?'.format(
            module_name)
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
        rmtree(remove_dir)
        print('Manager: {} directory deleted'.format(remove_dir))


class PatchboxModule(object):

    PATCHBOX_MODULE_FILE = settings.PATCHBOX_MODULE_FILE
    PATCHBOX_MODULE_REQUIRED_KEYS = settings.PATCHBOX_MODULE_REQUIRED_KEYS

    def __init__(self, path):
        self.path = path if path.endswith('/') else path + '/'
        self.name = self.path.split('/')[-2]

        self.data = self.parse_module_file()

        self.description = self.data.get('description')
        self.version = self.data.get('version')
        self.autolaunch = self.get_autolaunch_mode()

        self._system_services_validated = False
        self._module_services_validated = False
        self._scripts_validated = False

        self._module_services = []
        self._system_services = []
        self._scripts = {}

        self.errors = []

    def parse_module_file(self):
        path = os.path.join(self.path, self.__class__.PATCHBOX_MODULE_FILE)
        try:
            with open(path) as f:
                data = json.load(f)
                module_keys = [k for k in data]
                for k in self.__class__.PATCHBOX_MODULE_REQUIRED_KEYS:
                    if k not in module_keys:
                        raise ModuleError(
                            '{}.module is not valid: "{}" key not defined in {}'.format(self.name, k, path))
                return data
        except (ValueError, IOError):
            raise ModuleError(
                '{}.module file ({}) is not valid or missing'.format(self.name, path))

    def is_valid(self):
        self.get_scripts()
        self.get_system_services()
        self.get_module_services()
        return True

    def _parse_scripts(self, scripts_obj):
        scripts = {}
        if not isinstance(scripts_obj, dict):
            raise ModuleError(
                '{}.module is not valid: scripts must be declared as a dict'.format(self.name))
        for key in scripts_obj:
            if scripts_obj.get(key) and not os.path.isfile(os.path.join(self.path, scripts_obj.get(key))):
                raise ModuleError('{}.module file {} not found'.format(
                    self.name, scripts_obj.get(key)))
            scripts[key] = scripts_obj.get(key)
        return scripts

    def get_scripts(self):
        if not self._scripts_validated:
            self._scripts = self._parse_scripts(self.data.get('scripts', {}))
            self._scripts_validated = True
        return self._scripts

    def _parse_services(self, services_obj, fail_silent=False):
        services = []
        if not isinstance(services_obj, list):
            raise ModuleError(
                '{}.module is not valid: services must be declared as a list'.format(self.name))
        for i, service in enumerate(services_obj):
            if isinstance(service, dict) and service.get('config'):
                if not os.path.isfile(os.path.join(self.path, service.get('config'))):
                    message = '{}.module {} file {} not found'.format(
                        self.name, str(service.get('service', 'service')), os.path.join(self.path, service.get('config')))
                    self.errors.append(message)
                    if not fail_silent:
                        raise ModuleError(message)
                else:
                    service['config'] = os.path.join(
                        self.path, service.get('config'))
            services.append(PatchboxService(service))
        return services

    def get_system_services(self, fail_silent=False):
        if not self._system_services_validated:
            self._system_services = self._parse_services(
                self.data.get('depends_on', []), fail_silent=fail_silent)
            self._system_services_validated = True
        return self._system_services

    def get_module_services(self, fail_silent=False):
        if not self._module_services_validated:
            self._module_services = self._parse_services(
                self.data.get('services', []), fail_silent=fail_silent)
            self._module_services_validated = True
        return self._module_services

    @property
    def has_install(self):
        return self.get_scripts().get('install')

    @property
    def has_list(self):
        return self.get_scripts().get('list')

    @property
    def has_launch(self):
        return self.get_scripts().get('launch')

    @property
    def has_stop(self):
        return self.get_scripts().get('stop')

    @property
    def has_button_scripts(self):
        return os.path.isdir(os.path.join(self.path, 'pisound-btn/'))

    def get_autolaunch_mode(self):
        autolaunch = self.data.get('launch_mode')
        if not autolaunch:
            return False
        if str(autolaunch) == 'list':
            return 'list'
        if str(autolaunch) == 'argument':
            return 'argument'
        if str(autolaunch) == 'path':
            return 'path'
        if str(autolaunch) == 'auto':
            return 'auto'
        raise ModuleError(
            '{}.module unsupported auto_launch mode: {}'.format(self.name, autolaunch))

    def pre_install_validate(self, service_manager=PatchboxServiceManager()):
        #todo: validation
        pass

# Workaround to extract zips, keeping the permissions (especially +x).


class ZipFileWithPermissions(zipfile.ZipFile):
    def extract(self, member, path=None, pwd=None):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        ret_val = self._extract_member(member, path, pwd)
        attr = member.external_attr >> 16
        if attr:
            os.chmod(ret_val, attr)
        return ret_val


class PatchboxModuleManager(object):

    PATCHBOX_MODULE_FOLDER = settings.PATCHBOX_MODULE_FOLDER
    PATCHBOX_MODULE_TMP_FOLDER = settings.PATCHBOX_MODULE_TMP_FOLDER
    PATCHBOX_MODULE_IGNORED = settings.PATCHBOX_MODULE_IGNORED
    PATCHBOX_MODULE_FILE = settings.PATCHBOX_MODULE_FILE
    DEFAULT_SERVICE_MANAGER = PatchboxServiceManager

    def __init__(self, path=None, service_manager=None):
        self.path = self._verify_path(path)
        self.imp_path = os.path.join(self.path, 'imported/')
        self.tmp_path = self.__class__.PATCHBOX_MODULE_TMP_FOLDER
        if not os.path.isdir(self.tmp_path):
            os.makedirs(self.tmp_path)
        self.state = PatchboxModuleStateManager()
        self._service_manager = service_manager or self.__class__.DEFAULT_SERVICE_MANAGER()
        self._module_paths = None

    def _verify_path(self, path):
        modules_path = path or self.__class__.PATCHBOX_MODULE_FOLDER

        if not os.path.isdir(modules_path):
            if not path:
                os.mkdir(modules_path)
            else:
                raise ModuleManagerError(
                    '"patchbox-modules" folder not found in "{}"'.format(path))

        if not os.path.isdir(os.path.join(modules_path, 'imported/')):
            os.mkdir(os.path.join(modules_path, 'imported/'))

        return modules_path
    
    def _get_module_paths(self):
        if self._module_paths:
            return self._module_paths

        default = [(path.split('/')[-1], path) for path in glob.glob(self.path + '*') if os.path.isdir(
            path)]

        imported = [(path.split('/')[-1], path) for path in glob.glob(self.imp_path + '*') if os.path.isdir(
            path)]
        
        paths = default + imported

        modules = defaultdict(list)

        for k, v in paths:
            if k not in self.__class__.PATCHBOX_MODULE_IGNORED:
                modules[k].append(v)
        
        self._module_paths = modules
        
        return modules

    def _pick_module_path_from_paths(self, module_name, paths, silent=False):
        path = None
           
        if len(paths) == 1:
            path = paths[0]
        elif len(paths) > 1:
            if not silent:
                print('Manager: multiple paths for {}.module found: {}'.format(module_name, paths))
            path = None
            version = None
            for can in paths:
                try:
                    tmp_module = PatchboxModule(can)
                    if tmp_module.version >= version:
                        version = tmp_module.version
                        path = tmp_module.path
                except Exception as err:
                    print('Manager: ERROR: {}'.format(err))
                    continue
            if not silent:
                print('Manager: {}.module ({}, {}) choosen'.format(module_name, path, version))
        
        if not path and not silent:
            raise ModuleNotFound(module_name)
        
        return path

    def get_all_modules(self):
        modules = []

        module_paths = self._get_module_paths()

        for name, paths in module_paths.items():
            path = self._pick_module_path_from_paths(name, paths, silent=True)
            try:
                module = PatchboxModule(path)
                modules.append(module)
            except ModuleError as err:
                pass

        return modules

    def get_module_by_name(self, module_name):
        paths = self._get_module_paths().get(module_name)
        if not paths:
            raise ModuleNotFound(module_name)
        
        path = self._pick_module_path_from_paths(module_name, paths)

        return self.get_module_by_path(path)
    
    def get_module_by_path(self, path):
        module = PatchboxModule(path)
        installed_version = self.state.get('version', module.path)
        if installed_version and installed_version != module.version:
            print('Manager: {}.module version mismatch {} vs {}'.format(module.name, installed_version, module.version))
            self.state.set('installed', False, module.path)
        return module

    def get_active_module(self):
        module_path = self.get_active_module_path()
        if module_path:
            return self.get_module_by_path(module_path)
        return None

    def get_active_module_path(self):
        path = self.state.get('active_module')
        if path and not os.path.exists(path):
            return None
        return path

    def init(self):
        module = self.get_active_module()
        if module:
            self.activate(module, autolaunch=True, autoinstall=False)

    def launch(self, module, arg=None):
        if not self.state.get('installed', module.path):
            self._install_module(module)

        if not module.has_launch:
            raise ModuleManagerError(
                '{}.module does not support launch command'.format(module.name))

        active_path = self.get_active_module_path()
        if not active_path or active_path != module.path:

            if active_path:
                active = self.get_module_by_path(active_path)
                self._stop_module(active)
                self._deactivate_module(active)

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

        print('Manager: {}.module launch mode is {}'.format(
            module.name, module.autolaunch))
        arg = arg or self.state.get('auto_launch', module.path)

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
            if not os.path.isfile(arg) or not os.path.isdir(arg):
                raise ModuleArgumentError(
                    '{}.module launch argument "{}" is not valid'.format(module.name, arg))

        if module.autolaunch == 'auto':
            arg = None

        try:
            if arg:
                subprocess.Popen(['sh', os.path.join(module.path, module.has_launch), arg])
            else:
                subprocess.Popen(['sh', os.path.join(module.path, module.has_launch)])
        except Exception as err:
            raise ModuleError(
                'failed to launch {}.module {}'.format(module.name, err))
        print('Manager: {}.module launched'.format(module.name))

    def stop(self):
        active_path = self.get_active_module_path()
        if not active_path:
            return

        active = self.get_module_by_path(active_path)

        if active.has_stop:
            self._stop_module(active)
        else:
            raise ModuleManagerError(
                '{}.module does not support stop command'.format(active.name))

    def _stop_module(self, module):
        if module.has_stop:
            try:
                subprocess.Popen(['sh', module.path + module.has_stop])
            except:
                raise ModuleManagerError(
                    'failed to stop {}.module'.format(module.name))
            print('Manager: {}.module stopped'.format(module.name))
        return

    def list(self, module):
        if module.has_list:
            try:
                output = subprocess.check_output(
                    ['sh', module.path + module.has_list]).decode('utf-8')
                return [item for item in output.rstrip().split('\n') if item]
            except:
                raise ModuleError(
                    '{}.module listing error'.format(module.name))
        raise ModuleManagerError(
            '{}.module does not support list command'.format(module.name))

    @staticmethod
    def url_is_git(url):
        try:
            proc = subprocess.Popen(['git', 'ls-remote', url], stdout=DEVNULL, stderr=DEVNULL, env={"GIT_ASKPASS": "true"})
            return proc.wait() == 0
        except:
            return False

    @staticmethod
    def url_git_get_name(url):
        result = urllib.parse.urlparse(url)
        name = Path(result.path).name
        if name.endswith('.git'):
            return name[:-4]
        return name

    @staticmethod
    def url_is_url(url):
        try:
            result = urllib.parse.urlparse(url)
            return result.scheme in ['http', 'https']
        except:
            raise
            return False

    class PathType(Enum):
        GIT  = 1
        URL  = 2
        FILE = 3

    @staticmethod
    def path_get_type(path):
        if PatchboxModuleManager.url_is_git(path):
            return PatchboxModuleManager.PathType.GIT
        if PatchboxModuleManager.url_is_url(path):
            return PatchboxModuleManager.PathType.URL
        return PatchboxModuleManager.PathType.FILE

    def install(self, path):
        pathType = PatchboxModuleManager.path_get_type(path)

        tmp_dir = self.tmp_path
        module_name = None

        if pathType == PatchboxModuleManager.PathType.GIT:
            module_name = PatchboxModuleManager.url_git_get_name(path)
            subprocess.call(['git', 'clone', path, module_name], cwd=self.tmp_path)
        elif pathType in [PatchboxModuleManager.PathType.URL, PatchboxModuleManager.PathType.FILE]:
            file = None
            if pathType == PatchboxModuleManager.PathType.URL:
                r = requests.get(path)
                if r.status_code == 200:
                    file = tempfile.NamedTemporaryFile()
                    file.write(r.content)
                    file.flush()
                    path = file.name
                else:
                    raise ModuleManagerError('{} returned status code {}'.format(path, r.status_code))
            else:
                if not os.path.exists(path):
                    raise ModuleManagerError('{} does not exist'.format(path))

            tar_file_path = None
            zip_file_path = None

            if os.path.isdir(path):
                raise ModuleManagerError(
                    'module file can\'t be a directory: {}'.format(path))

            if tarfile.is_tarfile(path):
                tar_file_path = path

            if zipfile.is_zipfile(path):
                zip_file_path = path

            if not tar_file_path and not zip_file_path:
                raise ModuleManagerError(
                    '{} is not a valid file type: *.tar and *.zip files are supported'.format(path))

            print('Manager: extracting {} to {}'.format(path, tmp_dir))
            try:
                if tar_file_path:
                    tar_file = tarfile.open(tar_file_path)
                    tar_file.extractall(path=tmp_dir)
                    tar_file.close()

                if zip_file_path:
                    zip_file = ZipFileWithPermissions(zip_file_path, 'r')
                    zip_file.extractall(tmp_dir)
                    zip_file.close()

                files = glob.glob(tmp_dir + '*')
            
                if len(files) > 1 or not os.path.isdir(files[0]):
                    raise Exception

                module_name = files[0].split('/')[-1]
                print('Manager: {}.module found'.format(module_name))
            except:
                raise ModuleManagerError(
                    '{} module extraction failed'.format(path), remove_dir=tmp_dir)

        module = self.get_module_by_path(os.path.join(tmp_dir, module_name))

        if not isinstance(module, PatchboxModule):
            raise ModuleManagerError('{} is not a valid module'.format(
                str(module)), remove_dir=tmp_dir)

        if not module.is_valid():
            raise ModuleManagerError(
                "{}.module is not valid: {}".format(module.name, module.errors), remove_dir=tmp_dir)
        print('Manager: {}.module is valid'.format(module.name))

        if os.path.isdir(os.path.join(self.imp_path, module_name)):
            rmtree(os.path.join(self.imp_path, module_name))
            print('Manager: old {}.module deleted'.format(module.name))

        try:
            copytree(os.path.join(tmp_dir, module_name),
                     os.path.join(self.imp_path, module_name))
        except (shutil_error, OSError) as e:
            raise ModuleManagerError(
                "{}.module copy failed".format(module.name), remove_dir=tmp_dir)
        print('Manager: {}.module prepared for installation'.format(module.name))
        
        new_path = os.path.join(self.imp_path, module_name)
        new_path = new_path if new_path.endswith('/') else new_path + '/'
        module.path = new_path

        try:
            self._install_module(module)
        except ModuleError as err:
            raise ModuleManagerError(
                "{}.module installation failed".format(module.name), remove_dir=os.path.join(self.imp_path, module_name))

        self._deactivate_module(module, fake=True)

        rmtree(tmp_dir)

    def _install_module(self, module):
        if module.has_install:
            print('Manager: {}.module install script found: {}'.format(module.name, os.path.join(module.path, module.has_install)))
            try:
                subprocess.call(
                    ['chmod', '+x', os.path.join(module.path, module.has_install)])
                error = subprocess.call(
                    ['sh', '-e', os.path.join(module.path, module.has_install)])
                if error != 0:
                    raise ModuleError(
                        'Failed to install {}.module via {} script'.format(module.name, os.path.join(module.path, module.has_install)))
            except:
                raise ModuleError(
                    'Failed to install {}.module via {} script'.format(module.name, os.path.join(module.path, module.has_install)))
        else:
            print('Manager: no install script declared for {}.module'.format(module.name))
        self.state.set('installed', True, module.path)
        self.state.set('version', module.version, module.path)
        print('Module name: {}'.format(module.name))

    def activate(self, module, autolaunch=True, autoinstall=False):
        if not self.state.get('installed', module.path):
            if not autoinstall:
                raise ModuleNotInstalled(module.name)
            self._install_module(module)

        active_path = self.get_active_module_path()

        if active_path and active_path != module.path:
            active = self.get_module_by_path(active_path)
            self._stop_module(active)
            self._deactivate_module(active)

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
        if module.get_system_services():
            for service in module.get_system_services():
                self._service_manager.enable_start_unit(service)

        if module.get_module_services():
            for service in module.get_module_services():
                if service.auto_start:
                    self._service_manager.enable_start_unit(service)
                else:
                    print('Manager: {} auto_start {}'.format(
                        service.name, service.auto_start))

        self.state.set_active_module(module.path)
        print('Manager: {}.module activated'.format(module.name))

    def deactivate(self):
        active_path = self.get_active_module_path()
        if active_path:
            active = self.get_module_by_path(active_path)
            self._stop_module(active)
            self._deactivate_module(active)

    def _deactivate_module(self, module, fake=False):
        if module.get_module_services(fail_silent=True):
            for service in module.get_module_services():
                self._service_manager.stop_disable_unit(service)
        if not fake:
            if module.get_system_services(fail_silent=True):
                for service in module.get_system_services():
                    self._service_manager.reset_unit_environment(service)
            self.state.set_active_module(None)
            print('Manager: {}.module deactivated'.format(module.name))

    def _set_autolaunch_argument(self, module, arg):
        self.state.set('auto_launch', arg, module.path)

    def status(self):
        status = ''
        status += 'module_active={}\n'.format(self.state.get('active_module'))
        module = self.get_active_module()
        if module:
            status += 'module_version={}\n'.format(module.version)
            status += 'module_auto_launch_mode={}\n'.format(module.autolaunch)
            status += 'module_auto_launch_argument={}\n'.format(self.state.get('auto_launch', module.path))
            for service in module.get_system_services():
                status += 'module_system_service_{}={}\n'.format(service.name.split('.')[0], self._service_manager.get_active_state(service))
            for service in module.get_module_services():
                status += 'module_service_{}={}\n'.format(service.name.split('.')[0], self._service_manager.get_active_state(service))
        return status.rstrip()
