import json
import os
import dbus
from patchbox.environment import PatchboxEnvironment as penviron


class PatchboxModuleStateManager(object):

    DEFAULT_STATE_DIR = '/root/.patchbox/'
    DEFAULT_STATE_FILE = 'state.json'

    @staticmethod
    def init_state_file(path):
        with open(path, 'wt') as f:
            json.dump(
                {'type': 'PatchboxModuleManagerStateFile', 'modules': {}}, f)

    def __init__(self, path=None):
        self.path = path or self.__class__.DEFAULT_STATE_DIR + \
            self.__class__.DEFAULT_STATE_FILE
        if not os.path.isfile(self.path):
            if not os.path.exists(self.__class__.DEFAULT_STATE_DIR):
                os.makedirs(self.__class__.DEFAULT_STATE_DIR)
            self.init_state_file(self.path)
            with open(self.path, 'w') as f:
                json.dump(
                    {'type': 'PatchboxModuleManagerStateFile', 'modules': {}}, f)
        with open(self.path, 'rt') as f:
            try:
                self.data = json.load(f)
            except:
                self.init_state_file(self.path)
                self.data = json.load(f)

    def set(self, param, value, module_name=None):
        if module_name:
            try:
                current_value = self.data.get('modules').get(module_name, dict()).get(param)
                if current_value == value:
                    print('State: {} module {} {} -> {} (skip)'.format(module_name, param, current_value, value))
                    return
                self.data.get('modules')[module_name][param] = value
                print('State: {} module {} {} -> {}'.format(module_name, param, current_value, value))
            except KeyError:
                self.data.get('modules')[module_name] = {}
                self.data.get('modules')[module_name][param] = value
                print('State: {} module {} None -> {}'.format(module_name, param, value))
        else:
            current_value = self.data.get(param)
            if current_value == value:
                print('State: {} {} -> {} (skip)'.format(param, current_value, value))
                return
            self.data[param] = value
            print('State: {} {} -> {}'.format(param, current_value, value))

        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def get(self, param, module_name=None):
        if module_name:
            return self.data.get('modules').get(module_name, dict()).get(param)
        return self.data.get(param)

    def set_active_module(self, module_name):
        if module_name == None:
            active_name = self.get('active_module')
            self.set('active_module', None)
            penviron.set('PATCHBOX_MODULE_ACTIVE', None)
            return
        self.set('active_module', module_name)
        penviron.set('PATCHBOX_MODULE_ACTIVE', module_name)
