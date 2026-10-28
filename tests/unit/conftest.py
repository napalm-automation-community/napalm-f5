"""Test fixtures."""

import json
import re

import pytest
from bigrest.common.restobject import RESTObject
from napalm.base.test import conftest as parent_conftest
from napalm.base.test.double import BaseTestDouble

from napalm_f5 import f5


@pytest.fixture(scope="class")
def set_device_parameters(request):
    """Set up the class."""

    def fin():
        pass

    request.addfinalizer(fin)

    request.cls.driver = f5.F5Driver
    request.cls.patched_driver = PatchedF5Driver
    request.cls.vendor = "f5"
    parent_conftest.set_device_parameters(request)


def pytest_generate_tests(metafunc):
    """Generate test cases dynamically."""
    parent_conftest.pytest_generate_tests(metafunc, __file__)


class PatchedF5Driver(f5.F5Driver):  # pylint: disable=abstract-method
    """Patched F5 Driver."""

    platform = "f5"

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Patched F5 Driver constructor."""
        super(PatchedF5Driver, self).__init__(hostname, username, password, timeout, optional_args)
        self.patched_attrs = ["device"]
        self.device = FakeF5Device()

    def open(self):
        """Skip connecting; the test double is already attached."""


class FakeF5Device(BaseTestDouble):
    """F5 REST API device test double.

    Simulates bigrest's BIGIP object by dispatching load() and command() calls
    to JSON/text fixture files on disk, keyed by the iControl REST URL path.

    URL-to-filename mapping:
      /mgmt/tm/net/interface/   -> mgmt.tm.net.interface.json  (list -> [RESTObject])
      /mgmt/tm/sys/ntp/         -> mgmt.tm.sys.ntp.json        (dict -> RESTObject)
      /mgmt/tm/util/bash        -> mgmt.tm.util.bash.txt       (text -> str)

    Fixture files are resolved via BaseTestDouble.find_file():
      tests/unit/mocked_data/{current_test}/{current_test_case}/{filename}
    """

    _QUERY_RE = re.compile(r"\?.*$")

    def _url_to_filename(self, path: str, ext: str) -> str:
        """Convert a REST URL path to a fixture filename."""
        clean = self._QUERY_RE.sub("", path).strip("/")
        return clean.replace("/", ".") + "." + ext

    def load(self, path: str):
        """Return fixture data for a GET against the given REST path.

        Yields a list of RESTObject if the fixture is a JSON array,
        or a single RESTObject if it is a JSON object.
        """
        filename = self._url_to_filename(path, "json")
        filepath = self.find_file(filename)
        data = json.loads(self.read_txt_file(filepath))
        if isinstance(data, list):
            return [RESTObject(item) for item in data]
        return RESTObject(data)

    def command(self, path: str, data: dict = None) -> str:
        """Return raw text fixture content for a POST against the given REST path."""
        filename = self._url_to_filename(path, "txt")
        filepath = self.find_file(filename)
        return self.read_txt_file(filepath)
