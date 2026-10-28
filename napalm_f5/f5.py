"""Napalm driver for F5.

Read https://napalm.readthedocs.io for more information.
"""

import inspect
import re
import shlex
from pathlib import PurePath
from typing import Dict, List, Optional

from bigrest.bigip import BIGIP, RESTAPIError
from napalm.base.base import NetworkDriver
from napalm.base.exceptions import ConnectionException, MergeConfigException, ReplaceConfigException
from napalm.base.models import ConfigDict, InterfaceCounterDict

from napalm_f5.exceptions import CommitConfigException, DiscardConfigException, ReadOnlyModeException

# NAPALM 5 added a `format` argument to get_config; NAPALM 4 did not. NAPALM's own
# signature test requires an override to match the installed base class exactly, so
# the public signature is chosen from whichever version is installed.
BASE_GET_CONFIG_TAKES_FORMAT = "format" in inspect.signature(NetworkDriver.get_config).parameters

_SAFE_FILENAME = re.compile(r"[\w.-]+", re.ASCII)

# Directory iControl REST writes uploaded files to on the BIG-IP.
REST_DOWNLOADS_DIR = "/var/config/rest/downloads"


def _safe_filename(path: str) -> str:
    """Return the final component of path, rejecting anything unsafe for the device shell."""
    name = PurePath(path).name
    if name.startswith((".", "-")) or not _SAFE_FILENAME.fullmatch(name):
        raise ValueError(f"Unsafe config filename: {name!r}")
    return name


class F5Driver(NetworkDriver):  # pylint: disable=abstract-method, too-many-instance-attributes, too-many-public-methods
    """F5 REST API based NAPALM driver."""

    def __init__(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self, hostname: str, username: str, password: str, timeout: int = 60, optional_args: Optional[dict] = None
    ):
        """Initialize shared variables for driver.

        Args:
            hostname (str): Hostname for device to connect to.
            username (str): Username to authenticate with against device.
            password (str): Password to authenticate with against device.
            timeout (int, optional): Timeout for requests.. Defaults to 60.
            optional_args (Optional[dict], optional): Optional arguments to use with driver. Defaults to None.

        If optional_args contains a value called 'read_only' set to True, the interactions with the device will be set to read-only disabling any changes.
        'ssl_verify' controls TLS certificate verification: True (default), False, or a path to a CA bundle.
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        self.config_replace = False
        self.filename = None
        self.device = None

        if optional_args is None:
            self.optional_args = {}
        else:
            self.optional_args = optional_args

    def open(self):
        """F5 version of `open` method, see NAPALM for documentation."""
        try:
            self.device = BIGIP(
                device=self.hostname,
                username=self.username,
                password=self.password,
                session_verify=self.optional_args.get("ssl_verify", True),
                timeout=self.timeout,
            )
        except RESTAPIError as err:
            raise ConnectionException(f"F5 API Error ({err})") from err

    def close(self):
        """F5 version of `close` method, see NAPALM for documentation."""
        self.device = None

    def cli(self, commands: List[str], encoding: str = "text") -> Dict[str, str]:
        """F5 version of 'cli' method, see NAPALM for documentation.

        Each command is run with bash on the BIG-IP using the connecting user's privileges,
        so it must never be given untrusted input.

        Args:
            commands (List[str]): List of commands to be sent as strings.
            encoding (str, optional): Encoding of results. Defaults to "text".

        Returns:
            Dict[str, str]: Dictionary of commands sent and their associated response.
        """
        results = {}
        if self.optional_args.get("read_only"):
            raise ReadOnlyModeException

        for command in commands:
            results[command] = self.device.command(
                "/mgmt/tm/util/bash", {"command": "run", "utilCmdArgs": f"-c {shlex.quote(command)}"}
            )
        return results

    def load_replace_candidate(self, filename=None, config=None):
        """F5 version of 'load_replace_candidate' method, see NAPALM for documentation."""
        self.config_replace = True

        if config:
            raise NotImplementedError

        if self.optional_args.get("read_only"):
            raise ReadOnlyModeException

        if filename:
            try:
                self.filename = _safe_filename(filename)
                self._upload_scf(filename, self.filename)
                # /tmp here is a path on the BIG-IP, not a local temp directory.
                data = {
                    "command": "load",
                    "options": [{"file": f"/tmp/{self.filename}", "merge": False}],  # noqa: S108
                }
                self.device.command("/mgmt/tm/sys/config", data)
            except Exception as err:
                raise ReplaceConfigException(err) from err

    def _get_config(  # pylint: disable=redefined-builtin
        self,
        retrieve: str,
        full: bool,
        sanitized: bool,
        format: str,
    ) -> ConfigDict:
        """Shared implementation behind the version-specific get_config signatures.

        Args:
            retrieve (string): Which configuration type you want to populate, default is full running-config. The rest will be set to "".
            full (bool): Retrieve all the configuration. For instance, on ios, "sh run all".
            sanitized (bool): Remove secret data. Default: False.
            format (string): Configuration format to retrieve. Only "text" is supported on F5.

        Returns:
            running(string): Representation of the native running configuration
            candidate(string): Representation of the native candidate configuration. If the device doesnt differentiate between running and startup configuration this will an empty string
            startup(string): Representation of the native startup configuration. If the device doesnt differentiate between running and startup configuration this will an empty string
        """
        if sanitized or full:
            raise NotImplementedError("Specified feature for get_config() is not implemented.")

        if format != "text":
            raise NotImplementedError(f"Configuration format {format} is not supported, only 'text' is available.")

        if retrieve not in ["all", "recursive", "running"]:
            raise NotImplementedError(f"Retrieve type of {retrieve} is not valid. Only running-config can be provided.")

        if retrieve == "recursive":
            config = self.device.command(
                "/mgmt/tm/util/bash", {"command": "run", "utilCmdArgs": '-c "tmsh show running-config recursive"'}
            )
        else:
            config = self.device.command(
                "/mgmt/tm/util/bash", {"command": "run", "utilCmdArgs": '-c "tmsh show running-config"'}
            )
        return {"running": config, "candidate": "", "startup": ""}

    if BASE_GET_CONFIG_TAKES_FORMAT:

        def get_config(  # pylint: disable=redefined-builtin, arguments-differ
            self,
            retrieve: str = "all",
            full: bool = False,
            sanitized: bool = False,
            format: str = "text",
        ) -> ConfigDict:
            """F5 version of 'get_config' method, see NAPALM for documentation."""
            return self._get_config(retrieve, full, sanitized, format)

    else:

        def get_config(  # pylint: disable=arguments-differ
            self,
            retrieve: str = "all",
            full: bool = False,
            sanitized: bool = False,
        ) -> ConfigDict:
            """F5 version of 'get_config' method, see NAPALM for documentation."""
            return self._get_config(retrieve, full, sanitized, "text")

    def load_merge_candidate(self, filename=None, config=None):
        """F5 version of 'load_merge_candidate' method, see NAPALM for documentation."""
        self.config_replace = False

        if config:
            raise NotImplementedError

        if self.optional_args.get("read_only"):
            raise ReadOnlyModeException

        if filename:
            try:
                self.filename = _safe_filename(filename)
                self._upload_scf(filename, self.filename)
                # /tmp here is a path on the BIG-IP, not a local temp directory.
                data = {
                    "command": "load",
                    "options": [{"file": f"/tmp/{self.filename}", "merge": True}],  # noqa: S108
                }
                self.device.command("/mgmt/tm/sys/config", data)
            except Exception as err:
                raise MergeConfigException(err) from err

    def commit_config(self, message: str = "", revert_in: Optional[int] = None) -> None:
        """F5 version of 'commit_config' method, see NAPALM for documentation.

        Args:
            message (str): Optional - configuration session commit message
            revert_in (Optional[int]): Not supported on F5. Raises NotImplementedError if set.
        """
        if revert_in is not None:
            raise NotImplementedError("revert_in is not supported on F5 devices.")
        if self.optional_args.get("read_only"):
            raise ReadOnlyModeException

        try:
            self.device.command("/mgmt/tm/sys/config", {"command": "save"})
        except RESTAPIError as err:
            raise CommitConfigException(err) from err
        self.filename = None

    def discard_config(self):
        """F5 version of 'discard_config' method, see NAPALM for documentation."""
        if self.optional_args.get("read_only"):
            raise ReadOnlyModeException

        if self.filename is None:
            return

        try:
            # /tmp here is a path on the BIG-IP, not a local temp directory.
            self.device.command(
                "/mgmt/tm/util/unix-rm",
                {"command": "run", "utilCmdArgs": f"/tmp/{self.filename}"},  # noqa: S108
            )
        except RESTAPIError as err:
            raise DiscardConfigException(err) from err
        self.filename = None

    def is_alive(self):
        """F5 version of `is_alive` method, see NAPALM for documentation."""
        if self.device:
            return {"is_alive": True}
        return {"is_alive": False}

    def _get_uptime(self) -> float:
        result = self.device.command("/mgmt/tm/util/bash", {"command": "run", "utilCmdArgs": "-c 'cat /proc/uptime'"})
        return float(result.split()[0])

    def _get_device_info(self):
        return self.device.load("/mgmt/tm/cm/device/")[0].properties

    def get_facts(self):
        """F5 version of `get_facts` method, see NAPALM for documentation."""
        device_info = self._get_device_info()
        facts = {
            "uptime": self._get_uptime(),
            "vendor": "F5 Networks",
            "model": device_info["marketingName"],
            "hostname": device_info["hostname"],
            "fqdn": device_info["hostname"],
            "os_version": device_info["version"],
            "serial_number": device_info["chassisId"],
            "interface_list": self._get_interfaces_list(query=self.device.load("/mgmt/tm/net/interface/")),
        }
        return facts

    def _get_interfaces_list(self, query) -> List[str]:
        interfaces = [intf.properties["name"] for intf in query]
        return interfaces

    def _get_interfaces_enabled_state(self, query) -> List[bool]:
        enabled_state = [intf.properties["enabled"] for intf in query]
        return enabled_state

    def _get_interfaces_mac_address(self, query) -> List[str]:
        mac_addresses = [intf.properties["macAddress"] for intf in query]
        return mac_addresses

    def _get_interfaces_active_media(self, query) -> List[bool]:
        active_media = [intf.properties["mediaActive"] for intf in query]
        return active_media

    def _get_interfaces_media_status(self, query) -> List[bool]:
        media_status = [not (intf.properties["mediaActive"] == "none") for intf in query]
        return media_status

    def _get_interfaces_description(self, query) -> List[str]:
        description = [intf.properties["description"] if intf.properties.get("description") else "" for intf in query]
        return description

    def _get_interfaces_mtu(self, query) -> List[int]:
        mtu = [intf.properties.get("mtu", 0) for intf in query]
        return mtu

    def _get_interfaces_all_statistics(self) -> dict:
        return self.device.load("/mgmt/tm/net/interface/stats/").properties

    def _get_system_information(self) -> dict:
        system_information = self.device.load("/mgmt/tm/sys/snmp/").properties
        return system_information

    def get_snmp_information(self):
        """F5 version of 'get_snmp_information' method, see NAPALM for documentation."""
        sys_info = self._get_system_information()
        device_info = self._get_device_info()
        snmp_info = {
            "contact": sys_info["sysContact"] or "",
            "location": sys_info["sysLocation"] or "",
            "chassis_id": device_info["chassisId"],
            "community": {},
        }
        communities = self.device.load("/mgmt/tm/sys/snmp/communities/")

        for comm in communities:
            snmp_info["community"][comm.properties["communityName"]] = {
                "acl": comm.properties["source"] or "N/A",
                "mode": comm.properties["access"],
            }

        return snmp_info

    def get_lldp_neighbors(self):
        """F5 version of 'get_lldp_neigbors' method, see NAPALM for documentation."""
        lldp_info = {}
        lldp_neighbors = self.device.load("/mgmt/tm/net/lldp-neighbors?options=all-properties")
        for neighbor in lldp_neighbors:
            lldp_info[neighbor.properties["localInterface"]["description"]] = [
                {
                    "hostname": neighbor.properties["chassisId"]["description"],
                    "port": neighbor.properties["portId"]["description"],
                }
            ]
        return lldp_info

    def get_lldp_neighbors_detail(self, interface: str = ""):
        """F5 version of 'get_lldp_neigbors_detail' method, see NAPALM for documentation."""
        raise NotImplementedError

    def get_mac_address_table(self):
        """F5 version of 'get_mac_address_table' method, see NAPALM for documentation."""
        raise NotImplementedError

    def get_users(self):
        """F5 version of `get_users` method, see NAPALM for documentation."""
        users_dict = {}
        api_users = self.device.load("/mgmt/tm/auth/user/")
        for user in api_users:
            users_dict[user.properties["name"]] = {
                "level": 15 if user.properties["partitionAccess"][0]["role"] == "admin" else 0,
                "password": user.properties["encryptedPassword"],
                "sshkeys": [],
            }
        return users_dict

    def get_ntp_servers(self) -> dict:
        """F5 version of `get_ntp_servers` method, see NAPALM for documentation.

        Returns:
            dict: Dictionary of NTP server hosts as key with empty value.
        """
        result = self.device.load("/mgmt/tm/sys/ntp/").properties
        ntp_servers = result.get("servers")
        return {server: {} for server in ntp_servers}

    def get_interfaces_ip(self):
        """F5 version of 'get_interfaces_ip' method, see NAPALM for documentation."""
        result = self.device.load("/mgmt/tm/net/self/")
        interfaces_ip = {}
        for ip in result:
            host, prefix = tuple(ip.properties["address"].split("/"))
            if ":" in ip.properties["address"]:
                interfaces_ip[ip.properties["fullPath"]] = {"ipv6": {host: {"prefix_length": int(prefix)}}}
            else:
                interfaces_ip[ip.properties["fullPath"]] = {"ipv4": {host: {"prefix_length": int(prefix)}}}
        return interfaces_ip

    def get_environment(self):
        """F5 version of 'get_environment' method, see NAPALM for documentation."""
        raise NotImplementedError

    def get_network_instances(self, name=""):
        """F5 version of 'get_network_instances' method, see NAPALM for documentation."""
        raise NotImplementedError

    def get_interfaces_counters(self) -> Dict[str, InterfaceCounterDict]:
        """F5 version of 'get_interfaces_counters' method, see NAPALM for documentation.

        The REST API reports octets as bit counts, and reports errors and discards only as
        totals that cannot be split by direction. Counters the device does not break out are
        returned as -1, per the NAPALM convention for unsupported counters.
        """
        try:
            statistics = self._get_interfaces_all_statistics()
        except RESTAPIError as err:
            raise ConnectionError(f"get_interfaces_counters: {err}") from err

        counters = {}
        for entry in statistics["entries"].values():
            stats = entry["nestedStats"]["entries"]
            counters[stats["tmName"]["description"]] = {
                "rx_octets": stats["counters.bitsIn"]["value"] // 8,
                "tx_octets": stats["counters.bitsOut"]["value"] // 8,
                "rx_unicast_packets": stats["counters.pktsIn"]["value"],
                "tx_unicast_packets": stats["counters.pktsOut"]["value"],
                "rx_errors": -1,
                "tx_errors": -1,
                "rx_discards": -1,
                "tx_discards": -1,
                "rx_multicast_packets": -1,
                "tx_multicast_packets": -1,
                "rx_broadcast_packets": -1,
                "tx_broadcast_packets": -1,
            }
        return counters

    def get_interfaces(self):
        """F5 version of 'get_interfaces' method, see NAPALM for documentation."""

        def if_speed(active_media) -> float:
            if "100000" in active_media:
                return 100000.0
            if "40000" in active_media:
                return 40000.0
            if "10000" in active_media:
                return 10000.0
            if "1000" in active_media:
                return 1000.0
            if "100" in active_media:
                return 100.0
            return -1.0

        try:
            intf_query = self.device.load("/mgmt/tm/net/interface/")
            interfaces = self._get_interfaces_list(intf_query)
            active_media = self._get_interfaces_active_media(intf_query)
            description = self._get_interfaces_description(intf_query)
            enabled_state = self._get_interfaces_enabled_state(intf_query)
            mac_address = self._get_interfaces_mac_address(intf_query)
            media_status = self._get_interfaces_media_status(intf_query)
            mtu = self._get_interfaces_mtu(intf_query)
        except RESTAPIError as err:
            raise ConnectionError(f"get_interfaces: {err}") from err

        interfaces_dict = {
            interface_name: {
                "is_up": media_status,
                "is_enabled": enabled_state,
                "description": description,
                "last_flapped": -1.0,
                "speed": if_speed(active_media),
                "mac_address": mac_address,
                "mtu": mtu_val,
            }
            for (interface_name, media_status, enabled_state, description, mac_address, active_media, mtu_val) in zip(
                interfaces, media_status, enabled_state, description, mac_address, active_media, mtu
            )
        }

        return interfaces_dict

    def get_vlans(self):
        """F5 version of 'get_vlans' method, see NAPALM for documentation."""
        vlans = self.device.load("/mgmt/tm/net/vlan/")
        vlan_info = {}
        for vlan in vlans:
            intfs = self.device.load(f"/mgmt/tm/net/vlan/{vlan.properties['name']}/interfaces")
            vlan_info[vlan.properties["tag"]] = {
                "name": vlan.properties["name"],
                "interfaces": [intf.properties["name"] for intf in intfs],
            }
        return vlan_info

    def _upload_scf(self, local_path: str, filename: str):
        """Upload local_path and move it to /tmp/<filename> on the BIG-IP.

        filename must already have passed _safe_filename(); bigrest stores the upload under that basename.
        """
        if self.optional_args.get("read_only"):
            raise ReadOnlyModeException

        try:
            self.device.upload("/mgmt/shared/file-transfer/uploads", local_path)
            # we need to move the file to a whitelisted directory and /tmp is the easiest as it's cleared upon reboot
            self.device.command(
                "/mgmt/tm/util/unix-mv",
                {"command": "run", "utilCmdArgs": f"{REST_DOWNLOADS_DIR}/{filename} /tmp/{filename}"},  # noqa: S108
            )
        except RESTAPIError as err:
            raise ConnectionError(f"F5 API Error: {err}") from err
        except EnvironmentError as err:
            raise EnvironmentError(f"Error ({err.errno}): {err.strerror}") from err
