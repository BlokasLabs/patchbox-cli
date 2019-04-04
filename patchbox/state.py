import subprocess
import json
import os
import glob
import dbus

class PatchboxModuleStateManager(object):

    DEFAULT_STATE_DIR = '/usr/local/patchbox-modules/system/'
    DEFAULT_STATE_FILE = 'state.json'

    def __init__(self, path=None):
        self.path = path or self.__class__.DEFAULT_STATE_DIR + self.__class__.DEFAULT_STATE_FILE
        if not os.path.isfile(self.path):
            if not os.path.exists(self.__class__.DEFAULT_STATE_DIR):
                os.makedirs(self.__class__.DEFAULT_STATE_DIR)
            with open(self.path, 'w') as f:
                json.dump({'type': 'PatchboxModuleManagerStateFile', 'modules': {}}, f)
        with open(self.path) as f:
            self.data = json.load(f)

    def set(self, param, value, module_name=None):
        if module_name:
            try:
                self.data.get('modules')[module_name][param] = value
                print('State: {}.module {} {}'.format(module_name, param, value))
            except KeyError:
                self.data.get('modules')[module_name] = {}
                self.data.get('modules')[module_name][param] = value
                print('State: {}.module {} {}'.format(module_name, param, value))
        else:
            self.data[param] = value
        with open(self.path, 'w') as f:
            json.dump(self.data, f)

    def get(self, param, module_name=None):
        if module_name:
            return self.data.get('modules').get(module_name, dict()).get(param)
        return self.data.get(param)
    
    def set_active_module(self, module_name):
        if module_name == None:
            active_name = self.get('active_module')
            if not active_name:
                for name, state in self.data.get('modules').items():
                    if state.get('active'):
                        self.set('active', False, name)
                return
            self.set('active', False, module_name=active_name)
            self.set('active_module', None)
            return
        self.set('active', True, module_name=module_name)
        self.set('active_module', module_name)