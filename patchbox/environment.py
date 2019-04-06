class PatchboxEnvironment(object):

    def __init__(self):
        self.path = '/etc/environment'


    def get(self, param, debug=True):
        param = str(param)

        with open(self.path, 'r') as f:
            for line in f:
                if len(line.strip()) != 0:
                    if line.startswith(param):
                        value = line.split('=')[-1].strip()
                        if debug:
                            print('Environment: get {}={}'.format(param, value))
                        return value
        if debug:
            print('Environment: get {}={}'.format(param, None))
        return None


    def set(self, param, value, debug=True):
        if value and debug:
            print('Environment: set {}={}'.format(param, value))
        elif debug:
            print('Environment: {} unset'.format(param))
        with open(self.path, 'r') as f:
            data = f.readlines()
            changed = None
            for i, line in enumerate(data):
                if line.startswith(param):
                    if value:
                        data[i] = '{}={}\n'.format(param, value)
                    else:
                        del data[i]
                    changed = True
                    break
            if not changed and value:
                data.append('{}={}\n'.format(param, value))

        with open(self.path, 'w') as f:
            f.writelines(data)
