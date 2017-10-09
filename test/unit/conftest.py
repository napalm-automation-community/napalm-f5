"""Test fixtures."""

import ast
import pytest
import re

from mock import Mock
from napalm_base.test import conftest as parent_conftest
from napalm_base.test.double import BaseTestDouble

from napalm_f5 import f5


@pytest.fixture(scope='class')
def set_device_parameters(request):
    """Set up the class."""

    def fin():
        pass

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

    def __init__(self, hostname, username, password, timeout=60,
                 optional_args=None):
        """Patched F5 Driver constructor."""
        super(PatchedF5Driver, self).__init__(hostname, username, password,
                                              timeout, optional_args)
        self.patched_attrs = ['device']
        self.device = FakeF5Device()
        self.devices = None

    def open(self):
        pass


class FakeF5Device(BaseTestDouble):
    """F5 device test double."""

    def __init__(self):
        self.icr = FakeIControl(self)
        self.Management = Mock()
        self.Networking = Mock()
        self.System = Mock()
        self.Management.Device.get_hostname = self.icr.get_hostname
        self.Management.SNMPConfiguration.get_readonly_community = self.icr.get_readonly_community
        self.Management.SNMPConfiguration.get_readwrite_community = self.icr.get_readwrite_community
        self.Management.SNMPConfiguration.get_system_information = self.icr.get_snmp_system_information
        self.Management.UserManagement.get_list = self.icr.get_user_list
        self.Management.UserManagement.get_encrypted_password = self.icr.get_encrypted_password
        self.Networking.Interfaces.get_active_media = self.icr.get_active_media
        self.Networking.Interfaces.get_description = self.icr.get_description
        self.Networking.Interfaces.get_enabled_state = self.icr.get_enabled_state
        self.Networking.Interfaces.get_list = self.icr.get_list
        self.Networking.Interfaces.get_mac_address = self.icr.get_mac_address
        self.Networking.Interfaces.get_media_status = self.icr.get_media_status
        self.Networking.Interfaces.get_all_statistics = self.icr.get_all_statistics
        self.Networking.RouteDomainV2.get_list = self.icr.rd_get_list
        self.Networking.RouteDomainV2.get_description = self.icr.rd_get_description
        self.Networking.RouteDomainV2.get_identifier = self.icr.rd_get_identifier
        self.Networking.RouteDomainV2.get_vlan = self.icr.rd_get_vlan
        self.Networking.SelfIPV2.get_address = self.icr.get_self_address
        self.Networking.SelfIPV2.get_list = self.icr.get_self_list
        self.Networking.SelfIPV2.get_netmask = self.icr.get_self_netmask
        self.Networking.VLAN.get_list = self.icr.get_vlan_list
        self.Networking.VLAN.get_vlan_id = self.icr.get_vlan_id
        self.Networking.VLAN.get_dynamic_forwarding = self.icr.get_dynamic_forwarding
        self.Networking.VLAN.get_static_forwarding = self.icr.get_static_forwarding
        self.System.Inet.get_ntp_server_address = self.icr.get_ntp_servers
        self.System.SystemInfo.get_marketing_name = self.icr.get_marketing_name
        self.System.SystemInfo.get_system_information = self.icr.get_system_information
        self.System.SystemInfo.get_uptime = self.icr.get_uptime
        self.System.SystemInfo.get_version = self.icr.get_version


class FakeIControl:
    """ Patched iControl handler (F5's API) """

    def __init__(self, device):
        self._device = device

    def get_from_file(self, api_call):
        api_call_mod = api_call.replace('.', '_')
        filename = "_get_device_{}.txt".format(api_call_mod)
        filepath = self._device.find_file(filename)
        return self._device.read_txt_file(filepath)

    @staticmethod
    def _str(content):
        new_content = re.sub("^'", "", content)
        new_content = re.sub("'$", "", new_content)
        return new_content

    def get_list(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_list")
        )

    def get_hostname(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Management.Device.get_hostname")
        )

    def get_uptime(self, *args, **kwargs):
        return int(self.get_from_file("System.SystemInfo.get_uptime")
                   )

    def get_marketing_name(self, *args, **kwargs):
        return self._str(
            self.get_from_file("System.SystemInfo.get_marketing_name")
        )

    def get_version(self, *args, **kwargs):
        return self._str(self.get_from_file("System.SystemInfo.get_version")
                         )

    def get_system_information(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("System.SystemInfo.get_system_information")
        )

    def get_enabled_state(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_enabled_state")
        )

    def get_mac_address(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_mac_address")
        )

    def get_active_media(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_active_media")
        )

    def get_media_status(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_media_status")
        )

    def get_description(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_description")
        )

    def get_all_statistics(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.Interfaces.get_all_statistics")
        )

    def get_snmp_system_information(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Management.SNMPConfiguration.get_system_information")
        )

    def get_readonly_community(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Management.SNMPConfiguration.get_readonly_community")
        )

    def get_readwrite_community(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Management.SNMPConfiguration.get_readwrite_community")
        )

    def get_user_list(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Management.UserManagement.get_list")
        )

    def get_encrypted_password(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Management.UserManagement.get_encrypted_password")
        )

    def get_ntp_servers(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("System.Inet.get_ntp_server_address")
        )

    def get_self_address(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.SelfIPV2.get_address")
        )

    def get_self_list(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.SelfIPV2.get_list")
        )

    def get_self_netmask(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.SelfIPV2.get_netmask")
        )

    def get_vlan_list(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.VLAN.get_list")
        )
    def get_vlan_id(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.VLAN.get_vlan_id")
        )
    def get_dynamic_forwarding(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.VLAN.get_dynamic_forwarding")
        )
    def get_static_forwarding(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.VLAN.get_static_forwarding")
        )

    def rd_get_list(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.RouteDomainV2.get_list")
        )

    def rd_get_description(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.RouteDomainV2.get_description")
        )

    def rd_get_identifier(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.RouteDomainV2.get_identifier")
        )

    def rd_get_vlan(self, *args, **kwargs):
        return ast.literal_eval(
            self.get_from_file("Networking.RouteDomainV2.get_vlan")
        )

