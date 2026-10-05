# Nagios Plugins

[![Plugin tests](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/plugin-tests.yml/badge.svg)](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/plugin-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.11%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-Shell_Scripts-4EAA25?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

A collection of Python and Bash Nagios/Icinga monitoring plugins for Linux systems.

## Current versions

| Plugin | Version | Release |
| --- | ---: | --- |
| `check_dnf.py` | 1.2.0 | [check_dnf.py v1.2.0](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/v1.2.0) |
| `check_librenms_validate` | 1.0.3 | [check_librenms_validate v1.0.3](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-librenms-validate-v1.0.3) |
| `check_hpe_hardware.py` | 1.0.4 | [check_hpe_hardware.py v1.0.4](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-hpe-hardware-v1.0.4) |
| `check_ssacli_disks.sh` | 1.0.0 | [check_ssacli_disks.sh v1.0.0](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-ssacli-disks-v1.0.0) |
| `check_hpe_raid.py` | 1.0.0 | [check_hpe_raid.py v1.0.0](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-hpe-raid-v1.0.0) |
| `check_systemd_health.py` | 1.0.2 | [check_systemd_health.py v1.0.2](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-systemd-health-v1.0.2) |

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

Full documentation:

[docs/check_ssacli_disks.md](docs/check_ssacli_disks.md)

### check_hpe_raid.py

Python 3 Nagios/Icinga plugin for monitoring HPE Smart Array RAID health
through HPE Smart Storage Administrator CLI (`ssacli`).

Current version: **1.0.0**

**The HPE `ssacli` package is required on the monitored server.**

The plugin monitors the logical RAID hierarchy:

```text
Smart Array controller
        |
      Array
        |
   Logical drive
```

It complements `check_ssacli_disks.sh`, which monitors the underlying physical
drives.

The plugin has been validated on real HPE hardware with:

```text
HPE Smart Array P408i-a SR Gen10
```

Tested configuration:

```text
Controller
├── Array A
│   └── LUN1
└── Array B
    └── LUN2
```

Features:

- Discovers HPE Smart Array controllers automatically
- Supports multiple Smart Array controllers
- Monitors controller health
- Discovers and monitors arrays
- Discovers and monitors logical drives
- Reports rebuilding/recovering logical drives as WARNING
- Reports failed controllers as CRITICAL
- Reports failed arrays as CRITICAL
- Reports failed or otherwise unhealthy logical drives as CRITICAL
- Reports missing controller status as UNKNOWN
- Reports missing controllers or arrays as UNKNOWN
- Handles `ssacli` command failures and timeouts as UNKNOWN
- Preserves the worst Nagios state found
- Automatically searches common `ssacli` locations
- Supports an explicit `--ssacli` executable path
- Supports a configurable command timeout
- Provides Nagios-compatible performance data
- Includes 33 hardware-independent unit tests
- Tested under Python 3.9, 3.11, and 3.13 in CI
- Validated through NRPE and end-to-end Nagios monitoring

Healthy example:

```text
HPE RAID OK: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:OK], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=0
```

Example WARNING:

```text
HPE RAID WARNING: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:Rebuild], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=1
```

Example CRITICAL:

```text
HPE RAID CRITICAL: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:Failed], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=1
```

Full documentation:

[docs/check_hpe_raid.md](docs/check_hpe_raid.md)

### check_systemd_health.py

Python 3 Nagios/Icinga plugin for monitoring systemd unit health and excessive
service restarts.

Current version: **1.0.2**

Tested on Rocky Linux 9 with systemd.

Features:

- Monitors failed systemd units
- Supports arbitrary unit states with `--state`
- Supports unit type filtering with `--type`
- Supports `--include` and `--exclude` filters
- Supports shell-style wildcard patterns
- Supports configurable WARNING and CRITICAL problem thresholds
- Monitors automatic service restart events through the systemd journal
- Detects restart events even when the affected service is no longer loaded
- Uses a single journal query for efficient restart monitoring
- Supports configurable restart WARNING and CRITICAL thresholds
- Supports configurable restart monitoring windows with `--since`
- Reports command failures and timeouts as UNKNOWN
- Reports invalid command-line arguments as UNKNOWN
- Provides Nagios-compatible performance data
- Supports verbose (`-v`) and debug (`-vv`) output
- Includes 46 automated tests
- Tested under Python 3.9, 3.11, and 3.13 in CI

Healthy example:

```text
SYSTEMD OK: system running; 0 matching problem units | problems=0 excluded=0
```

Failed unit example:

```text
SYSTEMD CRITICAL: system state degraded; 1 matching unit - backup.service | problems=1 excluded=0
```

Restart example:

```text
SYSTEMD CRITICAL: system state degraded; 0 matching problem units; nginx.service restarted 7 times | problems=0 excluded=0 restarts=7
```

Full documentation:

[docs/check_systemd_health.md](docs/check_systemd_health.md)

## HPE Smart Array monitoring

The repository contains two complementary HPE Smart Array plugins.

### Logical RAID health

`check_hpe_raid.py` monitors:

```text
Smart Array controller
        ↓
      Array
        ↓
   Logical drive
```

### Physical disk health

`check_ssacli_disks.sh` monitors:

```text
Physical drives
```

For complete Smart Array monitoring, both plugins can be used together.

Both require the HPE Smart Storage Administrator CLI (`ssacli`) package on the
monitored server.

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

Latest released version:

```bash
curl -L -o check_ssacli_disks.sh \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-ssacli-disks-v1.0.0/plugins/check_ssacli_disks.sh

chmod +x check_ssacli_disks.sh
```

### Download check_hpe_raid.py

Latest released version:

```bash
curl -L -o check_hpe_raid.py \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-hpe-raid-v1.0.0/plugins/check_hpe_raid.py

chmod +x check_hpe_raid.py
```

### Download check_systemd_health.py

Latest released version:

```bash
curl -L -o check_systemd_health.py \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-systemd-health-v1.0.2/plugins/check_systemd_health.py

chmod +x check_systemd_health.py
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

**The HPE `ssacli` package must be installed before using this plugin.**

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_ssacli_disks.sh \
  /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Test:

```bash
sudo /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

#### check_hpe_raid.py

**The HPE `ssacli` package must be installed before using this plugin.**

Verify `ssacli`:

```bash
/usr/sbin/ssacli version
```

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_raid.py \
  /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Verify the plugin:

```bash
/usr/lib64/nagios/plugins/check_hpe_raid.py --version
```

Test against the Smart Array:

```bash
sudo /usr/lib64/nagios/plugins/check_hpe_raid.py
```

#### check_systemd_health.py

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_systemd_health.py \
  /usr/lib64/nagios/plugins/check_systemd_health.py
```

Verify:

```bash
/usr/lib64/nagios/plugins/check_systemd_health.py --version
```

Basic test:

```bash
/usr/lib64/nagios/plugins/check_systemd_health.py
```

Restart monitoring example:

```bash
/usr/lib64/nagios/plugins/check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --restart-warning 3 \
  --restart-critical 5
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

## HPE ssacli dependency

Both Smart Array plugins require HPE Smart Storage Administrator CLI
(`ssacli`):

```text
check_hpe_raid.py
check_ssacli_disks.sh
```

**The HPE `ssacli` package must be installed on the monitored server.**

The default executable is commonly:

```text
/usr/sbin/ssacli
```

Verify it with:

```bash
/usr/sbin/ssacli version
```

`check_hpe_raid.py` can use an explicit custom path:

```bash
check_hpe_raid.py --ssacli /custom/path/ssacli
```

`check_ssacli_disks.sh` supports a custom executable through:

```bash
SSACLI_BIN=/custom/path/ssacli check_ssacli_disks.sh
```

## NRPE integration

### check_dnf.py

Example:

```text
command[check_dnf]=/usr/lib64/nagios/plugins/check_dnf.py
```

### check_librenms_validate

Example sudoers rule:

```text
nrpe ALL=(librenms) NOPASSWD: /opt/librenms/validate.php
```

NRPE:

```text
command[check_librenms_validate]=/usr/lib64/nagios/plugins/check_librenms_validate
```

### check_hpe_hardware.py — RHEL / Rocky Linux

sudoers:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

NRPE:

```text
command[check_hpe_hardware]=sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Local test:

```bash
sudo -u nrpe sudo -n \
  /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

### check_hpe_hardware.py — Debian

sudoers:

```text
nagios ALL=(root) NOPASSWD: /usr/lib/nagios/plugins/check_hpe_hardware.py
```

NRPE:

```text
command[check_hpe_hardware]=sudo -n /usr/lib/nagios/plugins/check_hpe_hardware.py
```

### check_ssacli_disks.sh

sudoers:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

NRPE:

```text
command[check_ssacli_disks]=sudo -n /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Local test:

```bash
sudo -u nrpe sudo -n \
  /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

### check_hpe_raid.py

On the tested system, `ssacli` requires elevated privileges.

Use a narrowly scoped sudoers rule:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_hpe_raid.py
```

NRPE command:

```text
command[check_hpe_raid]=sudo -n /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Validate sudoers:

```bash
sudo visudo -c
```

Test as the NRPE account:

```bash
sudo -u nrpe sudo -n \
  /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Remote test:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <hpe-server> \
  -c check_hpe_raid
```

Do not grant unrestricted sudo access to the NRPE account.

### check_systemd_health.py

Basic NRPE command:

```text
command[check_systemd_health]=/usr/lib64/nagios/plugins/check_systemd_health.py
```

Example with restart monitoring:

```text
command[check_systemd_health]=/usr/lib64/nagios/plugins/check_systemd_health.py --check-restarts --since 30m --restart-warning 3 --restart-critical 5
```

Restart monitoring requires the NRPE account to have sufficient access to the
systemd journal.

Verify journal access using the same account that runs the plugin. For example:

```bash
sudo -u nrpe journalctl \
  --since "30 minutes ago" \
  --no-pager \
  -o cat \
  _PID=1
```

Do not grant unrestricted sudo access solely to enable journal monitoring.

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

Workflow:

```text
.github/workflows/plugin-tests.yml
```

The Python matrix currently covers:

```text
Python 3.9
Python 3.11
Python 3.13
```

Current CI checks include:

- Python syntax validation
- Python 3.9, 3.11, and 3.13 compatibility
- `check_dnf.py` unit tests
- `check_librenms_validate` shell syntax and CLI checks
- `check_librenms_validate` mock-based tests
- `check_hpe_hardware.py` syntax and CLI checks
- `check_hpe_hardware.py` hardware-independent regression tests
- `check_hpe_raid.py` syntax and CLI checks
- `check_hpe_raid.py` 33 hardware-independent unit tests
- `check_ssacli_disks.sh` shell syntax and CLI checks
- `check_ssacli_disks.sh` hardware-independent mock-based tests
- `check_systemd_health.py` syntax and CLI checks
- `check_systemd_health.py` 46 automated unit and integration tests
- Detection of committed Python bytecode
- Legacy reference checks

### check_systemd_health.py tests

Run:

```bash
PYTHONPATH=plugins \
  python3 -m unittest tests/test_check_systemd_health.py -v
```

The current suite contains **46 tests**.

It covers:

- duration parsing
- exact and wildcard include/exclude filtering
- include/exclude precedence
- unit problem thresholds
- restart journal parsing
- restart unit extraction
- restart include/exclude filtering
- restart WARNING and CRITICAL thresholds
- worst-severity preservation
- argument validation
- restart defaults
- restart summary generation
- complete OK state
- failed-unit CRITICAL state
- threshold WARNING state
- excluded failure handling
- restart WARNING and CRITICAL states
- command failure UNKNOWN state

The tests do not require failed systemd units or restart loops on the test host.

The CI suite runs under Python 3.9, 3.11, and 3.13.

A successful run ends with:

```text
Ran 46 tests in ...

OK
```

### check_hpe_raid.py tests

Run:

```bash
python3 -m unittest tests/test_check_hpe_raid.py -v
```

The current suite contains **33 tests**.

It covers:

- controller parsing
- multiple controllers
- missing controller status
- array parsing
- multiple arrays
- logical drive parsing
- OK / Disabled logical drive states
- Rebuild / Rebuilding WARNING states
- Recover / Recovering WARNING states
- Failed logical drive state
- Interim Recovery Mode
- unexpected logical drive states
- `ssacli` discovery
- command execution
- command timeout
- command failure
- complete OK state
- WARNING state
- CRITICAL controller state
- CRITICAL array state
- CRITICAL logical drive state
- UNKNOWN states
- worst-severity preservation
- performance data

The tests do not require HPE hardware or an installed `ssacli` package.

A successful run ends with:

```text
Ran 33 tests in ...

OK
```

### check_ssacli_disks.sh tests

Run:

```bash
bash tests/test_check_ssacli_disks.sh
```

The tests use a mock `ssacli` and do not require HPE hardware.

### check_hpe_hardware.py tests

Run:

```bash
python -m unittest tests/test_check_hpe_hardware.py -v
```

The tests do not require HPE hardware.

### check_librenms_validate tests

Run:

```bash
bash tests/test_check_librenms_validate.sh
```

The tests do not require a LibreNMS installation.

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

### check_ssacli_disks.sh

- Bash
- HPE Smart Array controller
- **HPE Smart Storage Administrator CLI (`ssacli`)**
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- `sudo` when elevated privileges are required for local `ssacli` access

**The `ssacli` package must be installed on the monitored server.**

### check_hpe_raid.py

- Python 3
- HPE Smart Array controller
- **HPE Smart Storage Administrator CLI (`ssacli`)**
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- `sudo` when elevated privileges are required for local `ssacli` access

**The `ssacli` package must be installed on the monitored server.**

The plugin searches:

```text
PATH
/usr/sbin/ssacli
/usr/bin/ssacli
/usr/local/bin/ssacli
```

An explicit path can be supplied with:

```bash
check_hpe_raid.py --ssacli /custom/path/ssacli
```

See [docs/check_hpe_raid.md](docs/check_hpe_raid.md) for complete installation
and configuration information.

### check_systemd_health.py

- Python 3
- systemd
- `systemctl`
- `journalctl` when restart monitoring is enabled
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- Sufficient journal access for the account running restart monitoring

See [docs/check_systemd_health.md](docs/check_systemd_health.md) for complete
installation, configuration, restart monitoring, NRPE, and troubleshooting
information.

## Documentation

- [check_dnf.py documentation](docs/check_dnf.md)
- [check_librenms_validate documentation](docs/check_librenms_validate.md)
- [check_hpe_hardware.py documentation](docs/check_hpe_hardware.md)
- [check_ssacli_disks.sh documentation](docs/check_ssacli_disks.md)
- [check_hpe_raid.py documentation](docs/check_hpe_raid.md)
- [check_systemd_health.py documentation](docs/check_systemd_health.md)
- [Changelog](CHANGELOG.md)
- [Releases](https://github.com/cscsanaki/Nagios-Plugins/releases)

## License

MIT. See [LICENSE](LICENSE).

<!-- Branch protection workflow verified. -->
