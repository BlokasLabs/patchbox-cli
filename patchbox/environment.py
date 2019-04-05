class PatchboxEnvironment(object):

    def __init__(self):
        self.path = '/etc/environment'


    def get(self, param):
        param = str(param)

        with open(self.path, 'r') as f:
            for line in f:
                if len(line.strip()) != 0:
                    if line.startswith(param):
                        return line.split('=')[-1]
        return None


    def set(self, param, value):
        param = str(param)
        value = str(value)
        with open(self.path, 'r') as f:
            data = f.readlines()
            changed = None
            for i, line in enumerate(data):
                if line.startswith(param):
                    data[i] = '{}={}'.format(param, value)
                    changed = True
                    break
            if not changed:
                data.append('{}={}'.format(param, value))

        with open(self.path, 'w') as f:
            f.writelines(data)
