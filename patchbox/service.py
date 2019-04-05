import dbus

class ServiceError(Exception):
    pass

class ServiceManagerError(Exception):
    pass


class PatchboxService(object):

    def __init__(self, service_obj):
        self.name = None
        self.config_file = None
        self.environ_variable = None

        if isinstance(service_obj, unicode):
            self.name = str(service_obj)
        elif isinstance(service_obj, str):
            self.name = service_obj
        elif isinstance(service_obj, dict):
            if not service_obj.get('service'):
                raise ServiceError('service declaration ({}) is not valid'.format(service_obj))
            self.name = service_obj.get('service')
            if service_obj.get('config'):
                self.config_file = service_obj.get('config')
                self.environ_variable = self.get_config_type(self.name)
        else:
            raise ServiceError('service declaration ({}) is not valid'.format(service_obj))
    
    @staticmethod
    def get_config_type(service_name):
        service_name = service_name.split('/')[-1].rstrip('.service') if service_name.endswith('.service') else service_name.split('/')[-1]
        info = {
            'amidiauto': 'AMIDIAUTO_CFG',
            'pisound-btn': 'PISOUND_BTN_CFG'
        }
        return info.get(service_name)



class PatchboxServiceManager(object):

    UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"
    SERVICE_UNIT_INTERFACE = "org.freedesktop.systemd1.Service"

    def __init__(self):
        self.__bus = dbus.SystemBus()

    def start_unit(self, pservice, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            if pservice.environ_variable:
                print('Service: {} environment variable found'.format(pservice.name, pservice.environ_variable))
            interface.StartUnit(pservice.name, mode)
            print('Service: {} started'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def enable_start_unit(self, pservice, mode="replace"):
        if pservice.environ_variable:
            print('Service: {} environment variable found: {}'.format(pservice.name, pservice.environ_variable))
        if not self.is_active(pservice):
            if not self.enable_unit(pservice):
                return False
            if not self.start_unit(pservice, mode=mode):
                return False
            return True
        print('Service: {} already active'.format(pservice.name))
        return True

    def stop_disable_unit(self, pservice):
        if not self.stop_unit(pservice):
            pass
        if not self.disable_unit(pservice):
            pass

    def stop_unit(self, pservice, mode="replace"):
        interface = self._get_interface()

        if interface is None:
            return False
        try:
            interface.StopUnit(pservice.name, mode)
            if pservice.environ_variable:
                print('Service: {} environment variable found'.format(pservice.name, pservice.environ_variable))
                pass
            print('Service: {} stopped'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def restart_unit(self, pservice, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.RestartUnit(pservice, mode)
            print('Service: {} restarted'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def enable_unit(self, pservice):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.EnableUnitFiles([pservice.name],
                                      dbus.Boolean(False),
                                      dbus.Boolean(True))
            print('Service: {} enabled'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def disable_unit(self, pservice):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.DisableUnitFiles([pservice.name], dbus.Boolean(False))
            print('Service: {} disabled'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def _get_unit_file_state(self, pservice):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            state = interface.GetUnitFileState(pservice.name)
            return state
        except dbus.exceptions.DBusException as error:
            print(error)
            return False

    def _get_interface(self):
        try:
            obj = self.__bus.get_object("org.freedesktop.systemd1",
                                        "/org/freedesktop/systemd1")
            return dbus.Interface(obj, "org.freedesktop.systemd1.Manager")
        except dbus.exceptions.DBusException as error:
            print(error)
            return None

    def get_active_state(self, pservice):
        properties = self._get_unit_properties(pservice, self.UNIT_INTERFACE)
        if properties is None:
            return False
        try:
            state = properties["ActiveState"].encode("utf-8")
            return state
        except KeyError:
            return False

    def is_active(self, pservice):
        unit_state = self.get_active_state(pservice)
        return unit_state == b"active"

    def is_failed(self, pservice):
        unit_state = self.get_active_state(pservice)
        return unit_state == b"failed"

    def get_error_code(self, pservice):
        service_properties = self._get_unit_properties(
            pservice, self.SERVICE_UNIT_INTERFACE)
        if service_properties is None:
            return None
        return self._get_exec_status(service_properties)

    def _get_exec_status(self, properties):
        try:
            exec_status = int(properties["ExecMainStatus"])
            return exec_status
        except KeyError:
            return None

    def _get_result(self, properties):
        try:
            result = properties["Result"].encode("utf-8")
            return result
        except KeyError:
            return False

    def _get_unit_properties(self, pservice, unit_interface):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            unit_path = interface.LoadUnit(pservice.name)
            obj = self.__bus.get_object(
                "org.freedesktop.systemd1", unit_path)
            properties_interface = dbus.Interface(
                obj, "org.freedesktop.DBus.Properties")
            return properties_interface.GetAll(unit_interface)
        except dbus.exceptions.DBusException as error:
            print(error)
            return None