# Nagios Plugins

[![Plugin tests](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/python-tests.yml/badge.svg)](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/python-tests.yml)
[![Latest Release](https://img.shields.io/github/v/release/cscsanaki/Nagios-Plugins)](https://github.com/cscsanaki/Nagios-Plugins/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.11%20%7C%203.13-blue.svg)](https://www.python.org/)

A collection of Nagios/Icinga monitoring plugins for Linux systems.

## Plugins

### check_dnf.py

Python 3 plugin for monitoring package updates on modern DNF-based
RHEL-compatible Linux distributions.

Currently tested on Rocky Linux 9.8.

Features:

- Counts available security and non-security package updates
- CRITICAL by default when one or more security updates are available
- Detects whether a reboot is required
- CRITICAL by default when a reboot is required
- Reports the installed security kernel and currently running kernel
- Provides Nagios-compatible performance data
- Supports repository enable/disable options
- Supports optional cache-only operation
- Supports configurable timeout and security thresholds
- Provides verbose diagnostic output
- Uses standard Nagios exit codes
- Includes automated unit tests

Example:

```text
DNF CRITICAL: 0 security updates, 13 non-security updates, 13 total, reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8) | security_updates=0 non_security_updates=13 total_updates=13 reboot_required=1
```

Full documentation:

[docs/check_dnf.md](docs/check_dnf.md)

### check_librenms_validate

Nagios/Icinga plugin for monitoring the result of LibreNMS `validate.php`.

Currently tested with LibreNMS 26.9.1.

Features:

- Maps LibreNMS `WARN` results to Nagios WARNING
- Maps LibreNMS `FAIL` results to Nagios CRITICAL
- FAIL takes priority over WARN
- Handles ANSI-coloured LibreNMS output
- Detects execution failures and timeouts as UNKNOWN
- Supports a configurable validation timeout
- Provides `failures` and `warnings` performance data
- Supports NRPE with a narrowly scoped sudoers rule
- Includes automated mock-based tests

Example:

```text
LIBRENMS WARNING: 1 warning - Your install is over 24 hours out of date, last update: Thu, 24 Sep 2026 12:37:05 +0000 | failures=0 warnings=1
```

Full documentation:

[docs/check_librenms_validate.md](docs/check_librenms_validate.md)

## Download

### Clone the repository

```bash
git clone https://github.com/cscsanaki/Nagios-Plugins.git
cd Nagios-Plugins
```

### Download check_dnf.py

Latest released version:

```bash
curl -L -o check_dnf.py \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/v1.2.0/plugins/check_dnf.py

chmod +x check_dnf.py
```

### Download check_librenms_validate

Current version from the `main` branch:

```bash
curl -L -o check_librenms_validate \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/main/plugins/check_librenms_validate

chmod +x check_librenms_validate
```

See the [latest release](https://github.com/cscsanaki/Nagios-Plugins/releases/latest)
for release notes and source archives.

## Installation

The standard Nagios plugin directory on RHEL-compatible systems is commonly:

```text
/usr/lib64/nagios/plugins
```

### check_dnf.py

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_dnf.py \
  /usr/lib64/nagios/plugins/check_dnf.py
```

Test:

```bash
/usr/lib64/nagios/plugins/check_dnf.py
echo $?
```

### check_librenms_validate

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_librenms_validate \
  /usr/lib64/nagios/plugins/check_librenms_validate
```

Test:

```bash
/usr/lib64/nagios/plugins/check_librenms_validate
echo $?
```

## NRPE integration

Both plugins can be executed remotely through NRPE.

### check_dnf.py

Example NRPE command:

```text
command[check_dnf]=/usr/lib64/nagios/plugins/check_dnf.py
```

Remote test:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <host> \
  -c check_dnf
```

See [docs/check_dnf.md](docs/check_dnf.md#nrpe-integration) for the complete
NRPE configuration.

### check_librenms_validate

The recommended configuration keeps the plugin running as the unprivileged
`nrpe` account and permits only LibreNMS `validate.php` to run as the
`librenms` user.

sudoers:

```text
nrpe ALL=(librenms) NOPASSWD: /opt/librenms/validate.php
```

NRPE command:

```text
command[check_librenms_validate]=/usr/lib64/nagios/plugins/check_librenms_validate
```

Remote test:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <host> \
  -c check_librenms_validate
```

See [docs/check_librenms_validate.md](docs/check_librenms_validate.md#nrpe-integration)
for the complete sudoers and NRPE configuration.

## Nagios exit codes

Both plugins use the standard Nagios plugin exit codes:

| Code | State | Meaning |
| ---: | --- | --- |
| 0 | OK | Check completed successfully |
| 1 | WARNING | Warning condition detected |
| 2 | CRITICAL | Critical condition detected |
| 3 | UNKNOWN | Check could not reliably determine the state |

## Automated testing

GitHub Actions automatically validates the repository on pushes and pull
requests.

Current CI checks include:

- Python syntax validation
- Python 3.9, 3.11, and 3.13 compatibility
- `check_dnf.py` unit tests
- Nagios status logic tests
- `check_librenms_validate` shell syntax and CLI checks
- `check_librenms_validate` mock-based tests
- Detection of committed Python bytecode
- Legacy reference checks

The LibreNMS plugin tests do not require a LibreNMS installation:

```bash
bash tests/test_check_librenms_validate.sh
```

## Requirements

### check_dnf.py

- Python 3
- DNF
- `needs-restarting` for reboot detection
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

### check_librenms_validate

- Bash
- LibreNMS
- `sudo`
- GNU `timeout`
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

## Documentation

- [check_dnf.py documentation](docs/check_dnf.md)
- [check_librenms_validate documentation](docs/check_librenms_validate.md)
- [Changelog](CHANGELOG.md)

## License

MIT. See [LICENSE](LICENSE).
