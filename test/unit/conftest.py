"""Test fixtures."""
from builtins import super

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

    def open(self):
        pass


class FakeF5Device():
    """F5 device test double."""

    def __init__(self):
        self.Management = Mock()
        self.Networking = Mock()
        self.System = Mock()

        self.System.SystemInfo.get_marketing_name = get_content(name(System.SystemInfo.get_marketing_name))
        self.System.SystemInfo.get_uptime = get_content(name(System.SystemInfo.get_uptime))
        self.System.SystemInfo.get_version = get_content(name(System.SystemInfo.get_version))
        self.System.SystemInfo.get_system_information = get_content(name(System.SystemInfo.get_system_information))


    @staticmethod
    def get_content(filename):
        return 10

    @staticmethod
    def name(orig_name):
        name = orig_name.replace('.', '_').lower()
