class PatchboxEnvironment(object):

    @staticmethod
    def get(param, debug=True):
        param = str(param)

        with open('/etc/environment', 'r') as f:
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

    @staticmethod
    def set(param, value, debug=True):
        if value and debug:
            print('Environment: set {}={}'.format(param, value))
        elif debug:
            print('Environment: {} unset'.format(param))
        with open('/etc/environment', 'r') as f:
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

        with open('/etc/environment', 'w') as f:
            f.writelines(data)
