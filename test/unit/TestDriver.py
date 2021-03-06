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

"""Tests."""

import unittest

from napalm_f5 import f5
from napalm_base.test.base import TestConfigNetworkDriver, TestGettersNetworkDriver
import json


class TestConfigDriver(unittest.TestCase, TestConfigNetworkDriver):
    """Group of tests that test Configuration related methods."""

    @classmethod
    def setUpClass(cls):
        """Run before starting the tests."""
        hostname = '10.144.129.58'
        username = 'admin'
        password = 'admin'
        cls.vendor = 'f5'

        optional_args = {'port': None, }
        cls.device = f5.F5Driver(hostname, username, password, timeout=60,
                                             optional_args=optional_args)
        cls.device.open()

        cls.device.load_replace_candidate(filename='%s/initial.conf' % cls.vendor)
        cls.device.commit_config()


class TestGetterDriver(unittest.TestCase, TestGettersNetworkDriver):
    """Group of tests that test getters."""

    @classmethod
    def setUpClass(cls):
        """Run before starting the tests."""
        cls.mock = True

        hostname = '10.144.129.58'
        username = 'admin'
        password = 'admin'
        cls.vendor = 'f5'

        optional_args = {'port': None, }
        cls.device = f5.F5Driver(hostname, username, password, timeout=60,
                                             optional_args=optional_args)

        if cls.mock:
            cls.device.device = FakeDevice()
        else:
            cls.device.open()


class FakeDevice:
    """Test double."""

    @staticmethod
    def read_json_file(filename):
        """Return the content of a file with content formatted as json."""
        with open(filename) as data_file:
            return json.load(data_file)

    @staticmethod
    def read_txt_file(filename):
        """Return the content of a file."""
        with open(filename) as data_file:
            return data_file.read()
