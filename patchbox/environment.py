class PatchboxEnvironment(object):

    @staticmethod
    def get(param, debug=True):
        param = str(param)

        with open('/etc/environment', 'rt') as f:
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
        with open('/etc/environment', 'rt') as f:
            data = f.readlines()
            changed = None
            for i, line in enumerate(data):
                if line.startswith(param):
                    current_value = line.split('=')[-1].strip()
                    if current_value == value:
                        if debug:
                            print('Environment: {} {} -> {} (skip)'.format(param, current_value, value))
                        return
                    if value:
                        if debug:
                            print('Environment: {} {} -> {}'.format(param, current_value, value))
                        data[i] = '{}={}\n'.format(param, value)
                    else:
                        if debug:
                            print('Environment: {} {} -> unset'.format(param, current_value))
                        del data[i]
                    changed = True
                    break
            if not changed and value:
                if debug:
                    print('Environment: {} unset -> {}'.format(param, value))
                data.append('{}={}\n'.format(param, value))

        with open('/etc/environment', 'w') as f:
            f.writelines(data)
