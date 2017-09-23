# Copyright 2016 Dravetech AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Napalm driver for F5.
Read https://napalm.readthedocs.io for more information.
"""

import base64
import os

import bigsuds

from napalm_base.base import NetworkDriver
from napalm_base.exceptions import ConnectionException,\
    MergeConfigException, ReplaceConfigException

from napalm_f5.exceptions import CommitConfigException, DiscardConfigException


class F5Driver(NetworkDriver):
    def __init__(self, hostname, username, password, timeout=60,
                 optional_args=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        self.config_replace = False
        self.filename = None

        if optional_args is None:
            optional_args = {}

    def open(self):
        try:
            self.device = bigsuds.BIGIP(hostname=self.hostname,
                                        username=self.username,
                                        password=self.password
                                        )
            self.devices = self.device.Management.Device.get_list()
        except bigsuds.OperationFailed as err:
            raise ConnectionException('ConfigSync API Error ({})'.format(err))

    def load_replace_candidate(self, filename=None, config=None):
        self.config_replace = True

        if config:
            raise NotImplementedError

        if filename:
            self.filename = os.path.basename(filename)
            try:
                self._upload_scf(filename)
            except Exception as err:
                raise ReplaceConfigException('{}'.format(err))

    def load_merge_candidate(self, filename=None, config=None):
        self.config_replace = False

        if config:
            raise NotImplementedError

        if filename:
            self.filename = os.path.basename(filename)
            try:
                self._upload_scf(filename)
            except Exception as err:
                raise MergeConfigException('{}'.format(err))

    def commit_config(self):
        try:
            self.device.System.ConfigSync.install_single_configuration_file(
                filename=self.filename,
                load_flag='LOAD_HIGH_LEVEL_CONFIG',
                passphrase='',
                tarfile='',
                merge=not self.config_replace
            )
        except bigsuds.OperationFailed as err:
            raise CommitConfigException('{}'.format(err))

    def discard_config(self):
        try:
            self.device.System.ConfigSync.delete_single_configuration_file(
                filename=self.filename
            )
        except bigsuds.OperationFailed as err:
            raise DiscardConfigException('{}'.format(err))

    def _get_uptime(self):
        return self.device.System.SystemInfo.get_uptime()

    def _get_version(self):
        return self.device.System.SystemInfo.get_version()

    def _get_serial_number(self):
        system_information = self.device.System.SystemInfo.get_system_information()
        chassis_serial = system_information['chassis_serial']
        return chassis_serial

    def _get_model(self):
        return self.device.System.SystemInfo.get_marketing_name()

    def _get_hostname(self):
        return self.device.Management.Device.get_hostname(self.devices)

    def get_facts(self):
        facts = {
            'uptime': self._get_uptime(),
            'vendor': 'F5 Networks',
            'model': self._get_model(),
            'hostname': self._get_hostname(),
            'fqdn': self._get_hostname(),
            'os_version': self._get_version(),
            'serial_number': self._get_serial_number(),
            'interface_list': self._get_interfaces_list()
        }
        return facts

    def _get_interfaces_list(self):
        interfaces = self.device.Networking.Interfaces.get_list()
        return interfaces

    def _get_interfaces_enabled_state(self, interfaces):
        enabled_state = self.device.Networking.Interfaces.get_enabled_state(
            interfaces)
        return enabled_state

    def _get_interfaces_mac_address(self, interfaces):
        mac_address = self.device.Networking.Interfaces.get_mac_address(
            interfaces)
        return mac_address

    def _get_interfaces_active_media(self, interfaces):
        active_media = self.device.Networking.Interfaces.get_active_media(
            interfaces)
        return active_media

    def _get_interfaces_media_status(self, interfaces):
        media_status = self.device.Networking.Interfaces.get_media_status(
            interfaces)
        return media_status

    def _get_interfaces_description(self, interfaces):
        description = self.device.Networking.Interfaces.get_description(
            interfaces)
        return description

    def get_interfaces(self):
        try:
            interfaces = self._get_interfaces_list()
            active_media = self._get_interfaces_active_media(interfaces)
            description = self._get_interfaces_description(interfaces)
            enabled_state = self._get_interfaces_enabled_state(interfaces)
            mac_address = self._get_interfaces_mac_address(interfaces)
            media_status = self._get_interfaces_media_status(interfaces)
        except bigsuds.OperationFailed as err:
            raise Exception('get_interfaces: {}'.format(err))

        interfaces_dict = {
            interface_name: {
                'is_up': True if media_status == 'MEDIA_STATUS_UP' else False,
                'is_enabled': True if enabled_state == 'STATE_ENABLED' else False,
                'description': description,
                'last_flapped': None,
                'speed': active_media,
                'mac_address': mac_address,
            } for (
                interface_name,
                media_status,
                enabled_state,
                description,
                mac_address,
                active_media
            ) in zip(
                interfaces,
                media_status,
                enabled_state,
                description,
                mac_address,
                active_media
            )
        }

        return interfaces_dict

    def _upload_scf(self, fp):
        try:
            chunk_size = 512 * 1024
            filename = os.path.basename(fp)
            size = os.path.getsize(fp)
            start = 0
            with open(fp, 'rb') as fileobj:
                while True:
                    payload = base64.b64encode(fileobj.read(chunk_size))
                    if not payload:
                        break
                    end = fileobj.tell()

                    if start == 0 and end == size:
                        chain_type = 'FILE_FIRST_AND_LAST'
                    elif start == 0 and end < size:
                        chain_type = 'FILE_FIRST'
                    elif start > 0 and end < size:
                        chain_type = 'FILE_MIDDLE'
                    elif start > 0 and end == size:
                        chain_type = 'FILE_LAST'

                    self.device.System.ConfigSync.upload_file(
                        file_name='/var/local/scf/' + filename,
                        file_context=dict(
                            file_data=payload,
                            chain_type=chain_type
                        )
                    )

                    start += len(payload)

        except bigsuds.OperationFailed as e:
            raise Exception('ConfigSync API Error: {}'.format(e.message))
        except EnvironmentError as e:
            raise Exception('Error ({}): {}'.format(e.errno, e.strerror))

