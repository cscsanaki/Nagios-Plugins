# Nagios Plugins

[![Plugin tests](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/plugin-tests.yml/badge.svg)](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/plugin-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.11%20%7C%203.13-blue.svg)](https://www.python.org/)

A collection of Nagios/Icinga monitoring plugins for Linux systems.

## Current versions

| Plugin | Version | Release |
| --- | ---: | --- |
| `check_dnf.py` | 1.2.0 | [check_dnf.py v1.2.0](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/v1.2.0) |
| `check_librenms_validate` | 1.0.3 | [check_librenms_validate v1.0.3](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-librenms-validate-v1.0.3) |
| `check_hpe_hardware.py` | 1.0.4 | [check_hpe_hardware.py v1.0.4](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-hpe-hardware-v1.0.4) |
| `check_ssacli_disks.sh` | 1.0.0 | Release pending |

Each plugin is versioned independently. See the
[Releases](https://github.com/cscsanaki/Nagios-Plugins/releases) page for
plugin-specific release notes and source archives.

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

### check_hpe_hardware.py

Nagios/Icinga plugin for monitoring HPE server hardware through the local
HPE iLOrest CLI.

Current version: **1.0.4**

Tested on real hardware with:

- HPE ProLiant DL380 Gen10 / iLO 5 / Rocky Linux 9
- HPE ProLiant DL380 Gen11 / iLO 6 / Debian 12
- HPE iLOrest 7.3.0.0

The Debian 12 / DL380 Gen11 configuration has been validated on two separate
servers with local CHIF access, NRPE, and end-to-end Nagios monitoring.

Features:

- Monitors HPE hardware health through the local iLOrest CLI
- Reports OK, WARNING, CRITICAL, and UNKNOWN Nagios states
- Preserves the worst hardware health state found
- Reports server model and serial number
- Reports active ROM/BIOS version
- Reports iLO 5 and iLO 6 firmware versions
- Prevents component `Model:` fields from overwriting the server model
- Prevents redundant ROM information from overwriting the active ROM
- Adds recent IML entries to WARNING and CRITICAL output
- Handles iLOrest, CHIF, login, execution, and timeout failures as UNKNOWN
- Automatically discovers common iLOrest installation locations
- Supports an explicit custom iLOrest executable path
- Uses a 60-second default iLOrest command timeout
- Uses sysfs and `dmidecode` as local BIOS fallbacks
- Supports NRPE with narrowly scoped sudoers rules
- Includes hardware-independent automated regression tests

Example Gen10 result:

```text
HPE OK: hardware is healthy (Model: HPE ProLiant DL380 Gen10, S/N: CZ282701B5, ROM: U30 v3.70 (08/19/2026), iLO: iLO 5: 3.21 Jul 30 2026)
```

Example Gen11 result:

```text
HPE OK: hardware is healthy (Model: HPE ProLiant DL380 Gen11, S/N: CZ2D2M083G, ROM: U54 v3.00 (08/20/2026), iLO: iLO 6: 1.78 Jul 29 2026)
```

Full documentation:

[docs/check_hpe_hardware.md](docs/check_hpe_hardware.md)

### check_ssacli_disks.sh

Bash Nagios/Icinga plugin for monitoring HPE Smart Array physical drive health
through HPE Smart Storage Administrator CLI (`ssacli`).

Current version: **1.0.0**

**The HPE `ssacli` package is required on the monitored server.**

The plugin has been validated on real HPE Smart Array hardware with eight
physical drives and through an end-to-end NRPE/Nagios monitoring path.

Features:

- Discovers HPE Smart Array controllers automatically
- Supports multiple Smart Array controllers
- Queries all physical drives through `ssacli`
- Reports OK when all discovered physical drives are healthy
- Reports CRITICAL when one or more physical drives are not `Status: OK`
- Reports UNKNOWN when `ssacli` is missing or cannot be executed
- Reports UNKNOWN when controller discovery fails
- Reports UNKNOWN when no Smart Array controller is found
- Reports UNKNOWN when a controller cannot be queried
- Reports UNKNOWN when no physical drives are found
- Treats a physical drive with no reported status as problematic
- Reports controller slot and physical drive identifier for failed drives
- Provides Nagios-compatible performance data
- Supports a custom `ssacli` executable through `SSACLI_BIN`
- Includes hardware-independent mock-based tests

Example healthy result:

```text
SSACLI OK: all 8 physical drive(s) are healthy | drives=8 problems=0
```

Example problem result:

```text
SSACLI CRITICAL: 1 problematic drive(s) found: Slot 0, Drive 1I:1:2 (Failed) | drives=8 problems=1
```

The default `ssacli` executable is:

```text
/usr/sbin/ssacli
```

A different executable can be specified with:

```bash
SSACLI_BIN=/custom/path/ssacli check_ssacli_disks.sh
```

Full documentation will be available at:

```text
docs/check_ssacli_disks.md
```

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

Latest released version:

```bash
curl -L -o check_librenms_validate \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-librenms-validate-v1.0.3/plugins/check_librenms_validate

chmod +x check_librenms_validate
```

### Download check_hpe_hardware.py

Latest released version:

```bash
curl -L -o check_hpe_hardware.py \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-hpe-hardware-v1.0.4/plugins/check_hpe_hardware.py

chmod +x check_hpe_hardware.py
```

### Download check_ssacli_disks.sh

Current 1.0.0 version from the `main` branch:

```bash
curl -L -o check_ssacli_disks.sh \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/main/plugins/check_ssacli_disks.sh

chmod +x check_ssacli_disks.sh
```

After the 1.0.0 release is published, the versioned release URL will be:

```text
https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-ssacli-disks-v1.0.0/plugins/check_ssacli_disks.sh
```

See the [Releases](https://github.com/cscsanaki/Nagios-Plugins/releases)
page for plugin-specific release notes and source archives.

## Installation

### RHEL / Rocky Linux

The standard Nagios plugin directory is commonly:

```text
/usr/lib64/nagios/plugins
```

#### check_dnf.py

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_dnf.py \
  /usr/lib64/nagios/plugins/check_dnf.py
```

#### check_librenms_validate

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_librenms_validate \
  /usr/lib64/nagios/plugins/check_librenms_validate
```

#### check_hpe_hardware.py

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_hardware.py \
  /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

#### check_ssacli_disks.sh

The HPE `ssacli` package must be installed before using this plugin.

Verify that the executable is available:

```bash
/usr/sbin/ssacli version
```

Install the plugin:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_ssacli_disks.sh \
  /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Test:

```bash
sudo /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

### Debian

The standard Nagios plugin directory is commonly:

```text
/usr/lib/nagios/plugins
```

Install the HPE hardware plugin:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_hardware.py \
  /usr/lib/nagios/plugins/check_hpe_hardware.py
```

Test:

```bash
sudo /usr/lib/nagios/plugins/check_hpe_hardware.py
```

For the tested Debian 12 iLOrest installation procedure, see
[docs/check_hpe_hardware.md](docs/check_hpe_hardware.md#debian-12-ilorest-installation).

## HPE iLOrest discovery

`check_hpe_hardware.py` 1.0.4 automatically searches for iLOrest in this order:

```text
/opt/ilorest/bin/ilorest
/usr/sbin/ilorest
/usr/bin/ilorest
/usr/local/bin/ilorest
PATH
```

A custom path can be supplied explicitly:

```bash
check_hpe_hardware.py --ilorest /custom/path/ilorest
```

On the tested Debian 12 systems, iLOrest 7.3.0.0 is installed at:

```text
/opt/ilorest/bin/ilorest
```

On the tested Rocky Linux system, iLOrest is available at:

```text
/usr/sbin/ilorest
```

## NRPE integration

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

### check_hpe_hardware.py — RHEL / Rocky Linux

On the tested RHEL-compatible system, NRPE runs as `nrpe`.

sudoers:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

NRPE command:

```text
command[check_hpe_hardware]=sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Local test:

```bash
sudo -u nrpe sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

### check_hpe_hardware.py — Debian

On the tested Debian 12 systems, NRPE runs as `nagios`.

sudoers:

```text
nagios ALL=(root) NOPASSWD: /usr/lib/nagios/plugins/check_hpe_hardware.py
```

NRPE command:

```text
command[check_hpe_hardware]=sudo -n /usr/lib/nagios/plugins/check_hpe_hardware.py
```

Local test:

```bash
sudo -u nagios sudo -n /usr/lib/nagios/plugins/check_hpe_hardware.py
```

See [docs/check_hpe_hardware.md](docs/check_hpe_hardware.md#nrpe-integration)
for the complete HPE iLOrest, CHIF, sudoers, and NRPE configuration.

### check_ssacli_disks.sh

The plugin requires elevated privileges for local `ssacli` access on the tested
system.

Use a narrowly scoped sudoers rule:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Example NRPE command:

```text
command[check_ssacli_disks]=sudo -n /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Local NRPE-account test:

```bash
sudo -u nrpe sudo -n /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Remote test from the Nagios server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <hpe-server> \
  -c check_ssacli_disks
```

Do not grant unrestricted sudo access to the NRPE account.

## Nagios exit codes

All plugins use the standard Nagios plugin exit codes:

| Code | State | Meaning |
| ---: | --- | --- |
| 0 | OK | Check completed successfully |
| 1 | WARNING | Warning condition detected |
| 2 | CRITICAL | Critical condition detected |
| 3 | UNKNOWN | Check could not reliably determine the state |

## Automated testing

GitHub Actions automatically validates the repository on pushes and pull
requests.

The workflow is:

```text
.github/workflows/plugin-tests.yml
```

Current CI checks include:

- Python syntax validation
- Python 3.9, 3.11, and 3.13 compatibility
- `check_dnf.py` unit tests
- Nagios status logic tests
- `check_librenms_validate` shell syntax and CLI checks
- `check_librenms_validate` mock-based tests
- `check_hpe_hardware.py` syntax and CLI checks
- `check_hpe_hardware.py` hardware-independent regression tests
- `check_ssacli_disks.sh` shell syntax and CLI checks
- `check_ssacli_disks.sh` hardware-independent mock-based tests
- Detection of committed Python bytecode
- Legacy reference checks

The LibreNMS plugin tests do not require a LibreNMS installation:

```bash
bash tests/test_check_librenms_validate.sh
```

The HPE hardware plugin tests do not require HPE hardware:

```bash
python -m unittest tests/test_check_hpe_hardware.py -v
```

The HPE Smart Array disk tests do not require HPE hardware or an installed
`ssacli` package:

```bash
bash tests/test_check_ssacli_disks.sh
```

The `check_ssacli_disks.sh` test suite covers:

- `--version`
- `--help`
- unknown CLI options
- missing `ssacli`
- controller query failures
- no Smart Array controller found
- physical drive query failures
- no physical drives found
- healthy physical drives
- failed physical drives
- multiple failed physical drives
- missing physical drive status
- multiple Smart Array controllers
- Nagios exit states
- performance data

The real plugin itself still requires the HPE `ssacli` package on the monitored
server.

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

### check_hpe_hardware.py

- Python 3
- HPE iLOrest
- Local access to the HPE iLO Channel Interface (CHIF)
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

Tested iLOrest version:

```text
7.3.0.0
```

See [docs/check_hpe_hardware.md](docs/check_hpe_hardware.md) for platform-specific
iLOrest installation and NRPE configuration.

### check_ssacli_disks.sh

- Bash
- HPE Smart Array controller
- **HPE Smart Storage Administrator CLI (`ssacli`)**
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- `sudo` when elevated privileges are required for local `ssacli` access

The `ssacli` package must be installed on the monitored server.

The default executable path is:

```text
/usr/sbin/ssacli
```

Verify the installation with:

```bash
/usr/sbin/ssacli version
```

A custom executable can be selected through the `SSACLI_BIN` environment
variable.

## Documentation

- [check_dnf.py documentation](docs/check_dnf.md)
- [check_librenms_validate documentation](docs/check_librenms_validate.md)
- [check_hpe_hardware.py documentation](docs/check_hpe_hardware.md)
- `check_ssacli_disks.sh` documentation — pending
- [Changelog](CHANGELOG.md)
- [Releases](https://github.com/cscsanaki/Nagios-Plugins/releases)

## License

MIT. See [LICENSE](LICENSE).
