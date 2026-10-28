"""Tests for driver behaviour not covered by the getter fixtures."""

import inspect

import pytest
from napalm.base.base import NetworkDriver
from napalm.base.exceptions import MergeConfigException, ReplaceConfigException

from napalm_f5 import f5
from napalm_f5.exceptions import ReadOnlyModeException
from napalm_f5.f5 import BASE_GET_CONFIG_TAKES_FORMAT, F5Driver, _safe_filename


class RecordingDevice:
    """Stand-in for bigrest's BIGIP that records the calls made against it."""

    def __init__(self):
        """Start with an empty call log."""
        self.commands = []
        self.uploads = []

    def upload(self, path, filename):
        """Record an upload."""
        self.uploads.append((path, filename))

    def command(self, path, data=None):
        """Record a command and return empty output."""
        self.commands.append((path, data))
        return ""


def build_driver(optional_args=None):
    """Return a driver wired to a recording device instead of a real BIG-IP."""
    driver = F5Driver("device.example.net", "admin", "admin", optional_args=optional_args)
    driver.device = RecordingDevice()
    return driver


@pytest.mark.parametrize("optional_args", [None, {}, {"port": 443}, {"read_only": False}])
def test_config_methods_allowed_when_read_only_is_unset(optional_args):
    """read_only is optional, so omitting it must leave the device writable."""
    driver = build_driver(optional_args)

    driver.cli(["show sys version"])
    driver.commit_config()
    driver.filename = "candidate.scf"
    driver.discard_config()

    assert len(driver.device.commands) == 3


def test_cli_keys_results_by_command():
    """cli() returns each command's output keyed by the command itself."""
    driver = build_driver()

    assert driver.cli(["show sys version"]) == {"show sys version": ""}


def test_get_config_signature_matches_installed_napalm():
    """The override must match whichever base class NAPALM 4.x or 5.x installed."""
    assert inspect.getfullargspec(F5Driver.get_config)[:4] == inspect.getfullargspec(NetworkDriver.get_config)[:4]


def test_get_config_returns_running_config():
    """get_config() works on both supported NAPALM versions."""
    driver = build_driver()

    assert driver.get_config() == {"running": "", "candidate": "", "startup": ""}


@pytest.mark.parametrize("retrieve", ["startup", "candidate"])
def test_get_config_rejects_unsupported_retrieve(retrieve):
    """Only running-config can be read off a BIG-IP."""
    driver = build_driver()

    with pytest.raises(NotImplementedError):
        driver.get_config(retrieve=retrieve)


@pytest.mark.skipif(
    not BASE_GET_CONFIG_TAKES_FORMAT,
    reason="NAPALM 4.x get_config takes no format argument",
)
def test_get_config_rejects_non_text_format():
    """F5 only returns text configuration, so other formats are refused."""
    driver = build_driver()

    with pytest.raises(NotImplementedError):
        driver.get_config(format="json")


def test_interfaces_counters_convert_bits_to_octets():
    """Octet counters are derived from the device's bit counters."""
    driver = build_driver()
    driver._get_interfaces_all_statistics = lambda: {  # pylint: disable=protected-access
        "entries": {
            "https://localhost/mgmt/tm/net/interface/1.1/stats": {
                "nestedStats": {
                    "entries": {
                        "tmName": {"description": "1.1"},
                        "counters.bitsIn": {"value": 800},
                        "counters.bitsOut": {"value": 80},
                        "counters.pktsIn": {"value": 7},
                        "counters.pktsOut": {"value": 3},
                        "counters.dropsAll": {"value": 5},
                        "counters.errorsAll": {"value": 9},
                    }
                }
            }
        }
    }

    counters = driver.get_interfaces_counters()["1.1"]

    assert counters["rx_octets"] == 100
    assert counters["tx_octets"] == 10
    assert counters["rx_unicast_packets"] == 7
    assert counters["tx_unicast_packets"] == 3
    # dropsAll and errorsAll are totals the device cannot split by direction.
    for unavailable in ("rx_errors", "tx_errors", "rx_discards", "tx_discards"):
        assert counters[unavailable] == -1


@pytest.mark.parametrize(
    "method, args",
    [
        ("cli", (["show sys version"],)),
        ("commit_config", ()),
        ("discard_config", ()),
        ("load_replace_candidate", ()),
        ("load_merge_candidate", ()),
    ],
)
def test_read_only_mode_blocks_changes(method, args):
    """Every config-changing entry point refuses to run in read-only mode."""
    driver = build_driver({"read_only": True})

    with pytest.raises(ReadOnlyModeException):
        getattr(driver, method)(*args)

    assert driver.device.commands == []


@pytest.mark.parametrize(
    "path, expected",
    [("candidate.scf", "candidate.scf"), ("/home/user/configs/candidate-2024_01.scf", "candidate-2024_01.scf")],
)
def test_safe_filename_returns_basename(path, expected):
    """Only the final path component is used on the device."""
    assert _safe_filename(path) == expected


@pytest.mark.parametrize(
    "path",
    ["a;reboot.scf", "$(reboot).scf", "`reboot`.scf", 'a"b.scf', "has space.scf", ".hidden", "-rf", "", "café.scf"],
)
def test_safe_filename_rejects_shell_characters(path):
    """Anything that could be interpreted by the device shell is refused."""
    with pytest.raises(ValueError):
        _safe_filename(path)


@pytest.mark.parametrize("method, merge", [("load_replace_candidate", False), ("load_merge_candidate", True)])
def test_load_candidate_uploads_full_path_and_moves_basename(tmp_path, method, merge):
    """The local path is uploaded, then the bare filename is moved without a shell."""
    candidate = tmp_path / "candidate.scf"
    driver = build_driver()

    getattr(driver, method)(filename=str(candidate))

    assert driver.device.uploads == [("/mgmt/shared/file-transfer/uploads", str(candidate))]
    assert driver.device.commands == [
        (
            "/mgmt/tm/util/unix-mv",
            {"command": "run", "utilCmdArgs": "/var/config/rest/downloads/candidate.scf /tmp/candidate.scf"},
        ),
        ("/mgmt/tm/sys/config", {"command": "load", "options": [{"file": "/tmp/candidate.scf", "merge": merge}]}),
    ]
    assert driver.filename == "candidate.scf"


@pytest.mark.parametrize(
    "method, exception",
    [("load_replace_candidate", ReplaceConfigException), ("load_merge_candidate", MergeConfigException)],
)
def test_load_candidate_rejects_unsafe_filename(method, exception):
    """An unsafe filename never reaches the device."""
    driver = build_driver()

    with pytest.raises(exception):
        getattr(driver, method)(filename="/configs/x;reboot.scf")

    assert driver.device.uploads == []
    assert driver.device.commands == []


def test_discard_config_without_candidate_does_nothing():
    """With nothing loaded there is no file to remove."""
    driver = build_driver()

    driver.discard_config()

    assert driver.device.commands == []


def test_discard_config_removes_candidate_without_shell():
    """The loaded candidate is removed through unix-rm and forgotten."""
    driver = build_driver()
    driver.filename = "candidate.scf"

    driver.discard_config()

    assert driver.device.commands == [
        ("/mgmt/tm/util/unix-rm", {"command": "run", "utilCmdArgs": "/tmp/candidate.scf"})
    ]
    assert driver.filename is None


def test_commit_config_forgets_candidate():
    """After a commit, a later discard has nothing to remove."""
    driver = build_driver()
    driver.filename = "candidate.scf"

    driver.commit_config()
    driver.discard_config()

    assert driver.device.commands == [("/mgmt/tm/sys/config", {"command": "save"})]


def test_cli_quotes_command_for_bash():
    """Double quotes in a command no longer break out of the bash -c argument."""
    driver = build_driver()

    driver.cli(['tmsh list ltm pool "my pool"'])

    assert driver.device.commands == [
        ("/mgmt/tm/util/bash", {"command": "run", "utilCmdArgs": "-c 'tmsh list ltm pool \"my pool\"'"})
    ]


@pytest.mark.parametrize(
    "optional_args, expected",
    [(None, True), ({"ssl_verify": False}, False), ({"ssl_verify": "/etc/ssl/ca.pem"}, "/etc/ssl/ca.pem")],
)
def test_open_passes_ssl_verify(monkeypatch, optional_args, expected):
    """TLS verification is on unless explicitly disabled or pointed at a CA bundle."""
    calls = []
    monkeypatch.setattr(f5, "BIGIP", lambda **kwargs: calls.append(kwargs))
    driver = F5Driver("device.example.net", "admin", "admin", optional_args=optional_args)

    driver.open()

    assert calls[0]["session_verify"] == expected
