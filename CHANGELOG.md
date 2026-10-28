# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Unreleased

This release rewrites the driver on top of iControl REST and is not backwards compatible with 0.x.

### Changed

- The driver now talks to the BIG-IP over iControl REST using [bigrest](https://pypi.org/project/bigrest/) instead of iControl SOAP (`bigsuds`).
- Requires Python 3.10 or later and NAPALM 4.x or 5.x; `napalm_base` and `six` are no longer dependencies.
- TLS certificates are verified by default. Set the new `ssl_verify` optional arg to `False`, or to the path of a CA bundle, to connect to devices with self-signed certificates.
- Candidate config files are moved and removed on the device with the `unix-mv` and `unix-rm` endpoints instead of bash.

### Added

- `ssl_verify` optional arg for TLS certificate verification (`True`, `False`, or a CA bundle path).
- `read_only` optional arg that refuses any driver method that can change the device.
- `get_interfaces_counters`, `get_lldp_neighbors` and `get_vlans` getters.
- README sections on optional args and the device privileges each method needs.

### Fixed

- Loading a candidate config from a path that includes directories.
- `discard_config` no longer tries to remove `/tmp/None` when no candidate has been loaded.

### Security

- Candidate config filenames are validated before they reach the device, preventing shell injection on the BIG-IP.
- `cli()` quotes each command before passing it to bash.
