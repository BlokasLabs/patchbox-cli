class PatchboxEnvironment(object):

    def __init__(self):
        self.path = '/etc/environment'


    def get(self, param):
        param = str(param)

        with open(self.path, 'r') as f:
            for line in f:
                if len(line.strip()) != 0:
                    if line.startswith(param):
                        value = line.split('=')[-1].strip()
                        print('Environment: get {}={}'.format(param, value))
                        return value
        print('Environment: get {}={}'.format(param, None))
        return None


    def set(self, param, value):
        param = str(param)
        value = str(value)
        print('Environment: set {}={}'.format(param, value))
        with open(self.path, 'r') as f:
            data = f.readlines()
            changed = None
            for i, line in enumerate(data):
                if line.startswith(param):
                    data[i] = '{}={}\n'.format(param, value)
                    changed = True
                    break
            if not changed:
                data.append('{}={}\n'.format(param, value))

        with open(self.path, 'w') as f:
            f.writelines(data)