import dbus


class ServiceError(Exception):
    pass


class PatchboxServiceManager(object):

    UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"
    SERVICE_UNIT_INTERFACE = "org.freedesktop.systemd1.Service"

    def __init__(self):
        self.__bus = dbus.SystemBus()

    def start_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.StartUnit(unit_name, mode)
            print('Service: {} started'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def enable_start_unit(self, unit_name, mode="replace"):
        if not self.is_active(unit_name):
            if not self.enable_unit(unit_name):
                return False
            if not self.start_unit(unit_name, mode=mode):
                return False
            return True
        print('Service: {} active'.format(unit_name))
        return True

    def stop_disable_unit(self, unit_name):
        if not self.stop_unit(unit_name):
            pass
        if not self.disable_unit(unit_name):
            pass

    def stop_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()

        if interface is None:
            return False
        try:
            interface.StopUnit(unit_name, mode)
            print('Service: {} stopped'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def restart_unit(self, unit_name, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.RestartUnit(unit_name, mode)
            print('Service: {} restarted'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def enable_unit(self, unit_name):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.EnableUnitFiles([unit_name],
                                      dbus.Boolean(False),
                                      dbus.Boolean(True))
            print('Service: {} enabled'.format(unit_name))
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def disable_unit(self, unit_name):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.DisableUnitFiles([unit_name], dbus.Boolean(False))
            print('Service: {} disabled'.format(unit_name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def _get_unit_file_state(self, unit_name):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            state = interface.GetUnitFileState(unit_name)
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

    def get_active_state(self, unit_name):
        properties = self._get_unit_properties(unit_name, self.UNIT_INTERFACE)
        if properties is None:
            return False
        try:
            state = properties["ActiveState"].encode("utf-8")
            return state
        except KeyError:
            return False

    def is_active(self, unit_name):
        unit_state = self.get_active_state(unit_name)
        return unit_state == b"active"

    def is_failed(self, unit_name):
        unit_state = self.get_active_state(unit_name)
        return unit_state == b"failed"

    def get_error_code(self, unit_name):
        service_properties = self._get_unit_properties(
            unit_name, self.SERVICE_UNIT_INTERFACE)
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

    def _get_unit_properties(self, unit_name, unit_interface):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            unit_path = interface.LoadUnit(unit_name)
            obj = self.__bus.get_object(
                "org.freedesktop.systemd1", unit_path)
            properties_interface = dbus.Interface(
                obj, "org.freedesktop.DBus.Properties")
            return properties_interface.GetAll(unit_interface)
        except dbus.exceptions.DBusException as error:
            print(error)
            return None