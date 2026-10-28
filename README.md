# NAPALM F5

[![PyPI](https://img.shields.io/pypi/v/napalm-f5.svg)](https://pypi.python.org/pypi/napalm-f5)
[![PyPI](https://img.shields.io/pypi/dm/napalm-f5.svg)](https://pypi.python.org/pypi/napalm-f5)
[![Build Status](https://travis-ci.org/napalm-automation/napalm-f5.svg?branch=master)](https://travis-ci.org/napalm-automation/napalm-f5)
[![Coverage Status](https://coveralls.io/repos/github/napalm-automation/napalm-napalm-f5/badge.svg?branch=master)](https://coveralls.io/github/napalm-automation/napalm-napalm-f5)

This is a community version of [NAPALM](https://napalm.readthedocs.io/) for the F5 BIG-IP operating system. It is intended for use with the REST API starting in version 11.5. For standard tutorials and an overview of NAPALM, please review their documentation.

## Configuration Support

This table identifies the currently available configuration methods supported:

| Feature                   | Supported |
| ------------------------- | --------- |
| Config Replace            | ✅        |
| Commit Confirm            | ❌        |
| Config Merge              | ❌        |
| Compare Config            | ✅        |
| Atomic Changes            | ❌        |
| Rollback                  | ❌        |

> Commit Confirm is not supported by the vendor at the time of this writing.

```python
from napalm import get_network_driver

f5_device = "nyc-f5"
f5_user = "admin"
f5_password = "pass123"
driver = get_network_driver("f5")
optional_args = {}

with driver(f5_device, f5_user, f5_password, optional_args=optional_args) as device:
    device.load_replace_candidate(filename="2024-01-01-intended-config.scf")
    device.commit_config()

```

As shown in the example above, the use of NAPALM's context manager is supported and is recommended for use.

## Optional Arguments

| Argument     | Default | Description |
| ------------ | ------- | ----------- |
| `read_only`  | `False` | Refuse any driver method that can change the device. See [Required Privileges](#required-privileges). |
| `ssl_verify` | `True`  | TLS certificate verification for the iControl REST connection: `True`, `False`, or a path to a CA bundle. |

> TLS certificates are verified by default. To connect to a device with a self-signed certificate, either set `optional_args = {"ssl_verify": "/path/to/ca-bundle.pem"}` or, if you accept the risk, `optional_args = {"ssl_verify": False}`.

## Required Privileges

Some methods run commands through the `/mgmt/tm/util/bash` endpoint. On a BIG-IP this generally requires an account with the Administrator role and advanced shell (bash) access, even when you only read from the device:

| Method                                         | Uses bash |
| ---------------------------------------------- | --------- |
| `get_config`                                   | ✅        |
| `get_facts` (uptime)                           | ✅        |
| `cli`                                          | ✅        |
| `load_replace_candidate`, `load_merge_candidate` | ❌ (file upload, `unix-mv`, `tmsh load`) |
| `discard_config`                               | ❌ (`unix-rm`) |

`read_only` is only a guard inside the driver: it blocks the methods that change the device, but it does not reduce the privileges of the account you connect with.

`cli()` runs each command with bash on the BIG-IP using the connecting account's privileges. Never pass it untrusted input.

Candidate config filenames may contain only letters, digits, `_`, `.` and `-`, and must not start with `.` or `-`. Only the final path component is used on the device.

## Supported Getters

This table identifies the currently available getters and the support for each:

| Getter                    | Supported |
| ------------------------- | --------- |
| get_arp_table             | ❌        |
| get_bgp_config            | ❌        |
| get_bgp_neighbors         | ❌        |
| get_bgp_neighbors_detail  | ❌        |
| get_config                | ✅        |
| get_environment           | ❌        |
| get_facts                 | ✅        |
| get_firewall_policies     | ❌        |
| get_interfaces            | ✅        |
| get_interfaces_counters   | ❌        |
| get_interfaces_ip         | ✅        |
| get_ipv6_neighbors_table  | ❌        |
| get_lldp_neighbors        | ✅        |
| get_lldp_neighbors_detail | ❌        |
| get_mac_address_table     | ❌        |
| get_network_instances     | ❌        |
| get_ntp_peers             | ❌        |
| get_ntp_servers           | ✅        |
| get_ntp_stats             | ❌        |
| get_optics                | ❌        |
| get_probes_config         | ❌        |
| get_probes_results        | ❌        |
| get_route_to              | ❌        |
| get_snmp_information      | ✅        |
| get_users                 | ✅        |
| get_vlans                 | ✅        |
| is_alive                  | ✅        |
| ping                      | ❌        |
| traceroute                | ❌        |

> NOTE: This driver has a `read-only mode` feature that will disable any driver functions that can make changes on the connected Device. To enable this feature you simply need to pass `"read_only": True` in optional_args. It does not reduce the privileges needed on the device; see [Required Privileges](#required-privileges).
