from os import environ, path, symlink, remove, readlink
import dbus
from patchbox.environment import PatchboxEnvironment as penviron

class ServiceError(Exception):
    pass

class ServiceManagerError(Exception):
    pass

class PatchboxDefaultServiceHandler:
    def handle_activate(self, service):
        if service.environ_param:
            if penviron.get(service.environ_param, debug=False) != service.environ_value:
                penviron.set(service.environ_param, service.environ_value)
                return True
        return False

    def handle_deactivate(self, service):
        if service.environ_param:
            penviron.set(service.environ_param, None)
            return True
        return False

class PatchboxSymbolicLinkConfHandler(PatchboxDefaultServiceHandler):
    def __init__(self, conf_file, default_conf_file):
        super().__init__()
        self.conf_file = conf_file
        self.default_conf_file = default_conf_file

    @staticmethod
    def update_symlink(src, dst):
        print('{} -> {}'.format(dst, src))
        dst_exists = path.exists(dst)
        if not dst_exists or (not path.islink(dst) or readlink(dst) != src):
            if dst_exists:
                remove(dst)
            symlink(src, dst)
            return True
        return False

    def handle_activate(self, service):
        return PatchboxSymbolicLinkConfHandler.update_symlink(service.environ_value or self.default_conf_file, self.conf_file)

    def handle_deactivate(self, service):
        return PatchboxSymbolicLinkConfHandler.update_symlink(self.default_conf_file, self.conf_file)

def get_handler_for_service(service):
    if service.name == 'pisound-btn.service':
        return PatchboxSymbolicLinkConfHandler('/etc/pisound.conf', '/usr/local/etc/pisound.conf')
    elif service.name == 'amidiminder.service':
        return PatchboxSymbolicLinkConfHandler('/etc/amidiminder.rules', '/etc/default/amidiminder.rules')
    return PatchboxDefaultServiceHandler()

class PatchboxService(object):

    def __init__(self, service_obj, path=None):
        self.name = None
        self.environ_value = None
        self.environ_param = None
        self.auto_start = True

        if isinstance(service_obj, str):
            self.name = service_obj
        elif isinstance(service_obj, dict):
            if not service_obj.get('service'):
                raise ServiceError('service declaration ({}) is not valid'.format(service_obj))
            self.name = str(service_obj.get('service'))

            if service_obj.get('config'):
                self.environ_value = service_obj.get('config')
                self.environ_param = self.get_env_param(self.name)
            
            if service_obj.get('auto_start', True) == False:
                self.auto_start = service_obj.get('auto_start')
        else:
            raise ServiceError('service declaration ({}) is not valid'.format(service_obj))
    
    def __repr__(self):
        return '<PatchboxService: {}, {}, {}, {}>'.format(self.name, self.auto_start, self.environ_value, self.environ_param)
    
    @staticmethod
    def get_env_param(service_name):
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
            interface.StartUnit(pservice.name, mode)
            print('Service: {} started'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))

    def enable_start_unit(self, pservice, mode="replace"):
        get_enabled = self.get_enabled(pservice)
        if get_enabled == 'masked':
            print('Skipping enabling {}, because it is masked. Unmask it by running `sudo systemctl unmask {}`'.format(pservice.name, pservice.name))
            return True
        is_active = self.is_active(pservice)
        if not is_active:
            self.enable_unit(pservice)
            get_handler_for_service(pservice).handle_activate(pservice)
            self.start_unit(pservice, mode=mode)
            return True
        else:
            if get_handler_for_service(pservice).handle_activate(pservice):
                self.restart_unit(pservice, mode=mode)
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
            get_handler_for_service(pservice).handle_activate(pservice)
            print('Service: {} stopped'.format(pservice.name))
            return True
        except dbus.exceptions.DBusException as err:
            raise ServiceError(str(err))
    
    def reset_unit_environment(self, pservice):
        if get_handler_for_service(pservice).handle_deactivate(pservice):
            self.restart_unit(pservice)

    def restart_unit(self, pservice, mode="replace"):
        interface = self._get_interface()
        if interface is None:
            return False
        try:
            interface.RestartUnit(pservice.name, mode)
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

    def get_unit_start_timestamp(self, pservice):
        properties = self._get_unit_properties(pservice, self.UNIT_INTERFACE)
        if properties is None:
            return False
        try:
            state = properties["ActiveEnterTimestampMonotonic"]
            return state
        except KeyError:
            return 0

    def get_enabled(self, pservice):
        return self._get_unit_file_state(pservice)

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

    def _get_unit_state(self, pservice):
        interface = self._get_interface()
        if interface is None:
            return None
        try:
            return interface.GetUnitFileState(pservice.name)
        except dbus.exceptions.DBusException as error:
            print(error)
            return None

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
