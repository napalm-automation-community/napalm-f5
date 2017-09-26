"""Test fixtures."""
from builtins import super
from mock import Mock


import pytest
from napalm_base.test import conftest as parent_conftest

from napalm_base.test.double import BaseTestDouble

from napalm_f5 import f5


@pytest.fixture(scope='class')
def set_device_parameters(request):
    """Set up the class."""
    def fin():
        pass
        #request.cls.device.close()
    request.addfinalizer(fin)

    request.cls.driver = f5.F5Driver
    request.cls.patched_driver = PatchedF5Driver
    request.cls.vendor = 'f5'
    parent_conftest.set_device_parameters(request)


def pytest_generate_tests(metafunc):
    """Generate test cases dynamically."""
    parent_conftest.pytest_generate_tests(metafunc, __file__)


class PatchedF5Driver(f5.F5Driver):
    """Patched F5 Driver."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Patched F5 Driver constructor."""
        super().__init__(hostname, username, password, timeout, optional_args)

        self.patched_attrs = ['device']
        self.device = FakeF5Device()
        self.devices = None

    def open(self):
        pass


class FakeF5Device():
    """F5 device test double."""

    def __init__(self):
        #self.Management = self.Management()
        #self.Networking = self.Networking()
        self.System = self.System()

        #self.System.SystemInfo.get_hostname = iControlMock.get_hostname
        #self.System.SystemInfo.get_marketing_name = iControlMock.get_marketing_name
        #self.System.SystemInfo.get_uptime = iControlMock.get_uptime
        #self.System.SystemInfo.get_version = iControlMock.get_version
        #self.System.SystemInfo.get_system_information = iControlMock.get_system_information

    class System()
        def __init__(self):
            self.SystemInfo = SystemInfo()

    class SystemInfo()
        def __init__(self):
            pass
        def get_hostname(self):
            return u'BIG-IP_v13.0.0'
        def get_marketing_name(self):
            return u'BIG-IP Virtual Edition'
        def get_uptime(self):
            return 2
        def get_version(self):
            return '13'
        def get_system_information(self):
            return {   'annunciator_board_part_revision': None,
    'annunciator_board_serial': None,
    'chassis_serial': '4225052f-6da8-a9c6-ae4b3609da29',
    'host_board_part_revision': None,
    'host_board_serial': None,
    'host_name': 'localhost.localdomain',
    'os_machine': 'x86_64',
    'os_release': '3.10.0-327.36.3.el7.ve.x86_64',
    'os_version': '#1 SMP Tue Jan 31 16:09:28 PST 2017',
    'platform': 'Z100',
    'product_category': 'Virtual Edition',
    'switch_board_part_revision': None,
    'switch_board_serial': None,
    'system_name': 'Linux'}

    def open(self):
        pass

    #@staticmethod
    #def get_content(**kwargs):
    #    return 10

    #@staticmethod
    #def name(orig_name):
    #    name = orig_name.replace('.', '_').lower()


class iControlMock():
    @staticmethod
    def get_uptime():
        return 2

    @staticmethod
    def get_marketing_name():
        return u'BIG-IP Virtual Edition'

    @staticmethod
    def get_version():
        return u'BIG-IP_v13.0.0'

    @staticmethod
    def get_hostname():
        return u'BIG-IP_v13.0.0'

    @staticmethod
    def get_system_information():
        return {   'annunciator_board_part_revision': None,
    'annunciator_board_serial': None,
    'chassis_serial': '4225052f-6da8-a9c6-ae4b3609da29',
    'host_board_part_revision': None,
    'host_board_serial': None,
    'host_name': 'localhost.localdomain',
    'os_machine': 'x86_64',
    'os_release': '3.10.0-327.36.3.el7.ve.x86_64',
    'os_version': '#1 SMP Tue Jan 31 16:09:28 PST 2017',
    'platform': 'Z100',
    'product_category': 'Virtual Edition',
    'switch_board_part_revision': None,
    'switch_board_serial': None,
    'system_name': 'Linux'}

