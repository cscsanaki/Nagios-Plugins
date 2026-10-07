# Nagios Plugins

[![Plugin tests](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/plugin-tests.yml/badge.svg)](https://github.com/cscsanaki/Nagios-Plugins/actions/workflows/plugin-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.11%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-Shell%20Scripts-green.svg)](https://www.gnu.org/software/bash/)

A collection of Python and Bash Nagios/Icinga monitoring plugins for Linux systems.

## Current versions

| Plugin | Version | Release |
| --- | ---: | --- |
| `check_dnf.py` | 1.2.1 | [check_dnf.py v1.2.1](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-dnf-v1.2.1) |
| `check_librenms_validate` | 1.0.3 | [check_librenms_validate v1.0.3](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-librenms-validate-v1.0.3) |
| `check_hpe_hardware.py` | 1.0.4 | [check_hpe_hardware.py v1.0.4](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-hpe-hardware-v1.0.4) |
| `check_ssacli_disks.sh` | 1.0.0 | [check_ssacli_disks.sh v1.0.0](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-ssacli-disks-v1.0.0) |
| `check_hpe_raid.py` | 1.0.0 | [check_hpe_raid.py v1.0.0](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-hpe-raid-v1.0.0) |
| `check_systemd_health.py` | 1.0.2 | [check_systemd_health.py v1.0.2](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-systemd-health-v1.0.2) |
| `check_container_health.py` | 1.0.1 | [check_container_health.py v1.0.1](https://github.com/cscsanaki/Nagios-Plugins/releases/tag/check-container-health-v1.0.1) |

Each plugin is versioned independently. See the [Releases](https://github.com/cscsanaki/Nagios-Plugins/releases) page for plugin-specific release notes and source archives.

## Plugins

### check_dnf.py

Python 3 plugin for monitoring package updates on DNF-based RHEL-compatible Linux distributions.

Currently tested on Rocky Linux 9.8.

Features:

- Counts available security and non-security package updates
- CRITICAL by default when one or more security updates are available
- Detects whether a reboot is required
- CRITICAL by default when a reboot is required
- Reports the reason for a required reboot when provided by `dnf needs-restarting -r`
- Reports updated components such as `linux-firmware` directly in Nagios output
- Supports multiple reboot reasons
- Reports the installed security kernel and currently running kernel
- Preserves kernel-specific reboot information with priority over generic reboot reasons
- Provides Nagios-compatible performance data
- Configurable command timeout
- Nagios-compatible OK, WARNING, CRITICAL, and UNKNOWN exit codes
- No third-party Python modules required

Example:

```bash
./check_dnf.py
```

Example output:

```text
DNF OK: 0 security updates, 0 non-security updates, 0 total | security_updates=0 non_security_updates=0 total_updates=0
```

Example with updates and reboot required:

```text
DNF CRITICAL: 0 security updates, 13 non-security updates, 13 total, reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8) | security_updates=0 non_security_updates=13 total_updates=13 reboot_required=1
```

Example with a non-kernel reboot reason:

```text
DNF CRITICAL: 0 security updates, 0 non-security updates, 0 total, reboot required (linux-firmware updated since boot) | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

Version 1.2.1 extracts reboot reasons from `dnf needs-restarting -r`. If a
security-kernel mismatch is also available, the kernel-specific reboot
information takes priority.
```

See [docs/check_dnf.md](docs/check_dnf.md) for detailed documentation.

---

### check_librenms_validate

Bash Nagios/Icinga plugin for monitoring the output of LibreNMS `validate.php`.

Features:

- Executes LibreNMS validation non-interactively
- Runs `validate.php` as the `librenms` account
- Maps LibreNMS `WARN` results to Nagios WARNING
- Maps LibreNMS `FAIL` results to Nagios CRITICAL
- Handles ANSI colour escape sequences
- Configurable validation timeout
- Reports failures and warnings as performance data
- Designed for NRPE operation using a narrowly scoped sudoers rule

Example:

```bash
./check_librenms_validate
```

Example output:

```text
LIBRENMS WARNING: 1 warning - Your install is over 24 hours out of date | failures=0 warnings=1
```

See [docs/check_librenms_validate.md](docs/check_librenms_validate.md) for detailed documentation.

---

### check_hpe_hardware.py

Python 3 Nagios/Icinga plugin for monitoring HPE ProLiant server hardware through HPE iLOrest.

Tested with:

- HPE ProLiant DL380 Gen10
- HPE ProLiant DL380 Gen11
- iLO 5
- iLO 6
- HPE iLOrest
- Rocky Linux
- Debian 12

Features:

- HPE server model reporting
- Serial number reporting
- Active System ROM/BIOS reporting
- iLO firmware reporting
- Hardware health monitoring
- Integrated Management Log information for hardware problems
- Automatic iLOrest executable discovery
- Support for common iLOrest installation paths
- Explicit custom iLOrest executable path
- Local CHIF access
- Configurable command timeout
- Nagios-compatible exit codes
- NRPE support

Example:

```bash
./check_hpe_hardware.py
```

See [docs/check_hpe_hardware.md](docs/check_hpe_hardware.md) for detailed documentation.

---

### check_ssacli_disks.sh

Bash Nagios/Icinga plugin for monitoring HPE Smart Array physical drives through HPE Smart Storage Administrator CLI (`ssacli`).

Features:

- Automatic Smart Array controller discovery
- Multiple controller support
- Monitoring of all discovered physical drives
- CRITICAL for non-OK physical drive states
- Detection of missing physical-drive status
- Controller slot and physical-drive identifiers in problem output
- Nagios-compatible performance data
- Configurable `ssacli` executable through `SSACLI_BIN`
- NRPE support with a narrowly scoped sudoers rule
- Hardware-independent mock-based automated tests

Example:

```bash
./check_ssacli_disks.sh
```

See [docs/check_ssacli_disks.md](docs/check_ssacli_disks.md) for detailed documentation.

---

### check_hpe_raid.py

Python 3 Nagios/Icinga plugin for monitoring HPE Smart Array RAID configuration and health through HPE Smart Storage Administrator CLI (`ssacli`).

Features:

- Automatic Smart Array controller discovery
- Multiple controller support
- Controller health monitoring
- Array discovery and health monitoring
- Logical drive discovery and health monitoring
- OK handling for healthy logical drives
- Support for `Disabled` logical drive state as OK
- WARNING for rebuild/recovery states
- CRITICAL for unhealthy controllers, arrays, and logical drives
- UNKNOWN handling when status information is unavailable
- Automatic `ssacli` executable discovery
- Explicit `--ssacli` executable path
- Configurable command timeout
- Nagios-compatible performance data
- NRPE support
- Hardware-independent automated tests

Example:

```bash
./check_hpe_raid.py
```

See [docs/check_hpe_raid.md](docs/check_hpe_raid.md) for detailed documentation.

---

### check_systemd_health.py

Python 3 Nagios/Icinga plugin for monitoring systemd system and unit health.

Features:

- Checks the overall systemd system state
- Detects failed systemd units
- Supports configurable unit states
- Supports configurable unit types
- Exact and shell-style wildcard include filtering
- Exact and shell-style wildcard exclude filtering
- Exclude patterns take precedence over include patterns
- Configurable WARNING and CRITICAL thresholds
- Optional service restart monitoring through the systemd journal
- Configurable restart WARNING and CRITICAL thresholds
- Configurable restart monitoring window
- Restart detection can identify services that are no longer loaded
- Uses a single journal query for restart-event collection
- Nagios-compatible performance data
- Configurable command timeout
- Verbose and debug output
- Nagios-compatible OK, WARNING, CRITICAL, and UNKNOWN exit codes
- No third-party Python modules required
- Hardware-independent automated tests

Example:

```bash
./check_systemd_health.py
```

Example output:

```text
SYSTEMD OK: system running; 0 matching problem units | problems=0 excluded=0
```

Restart monitoring:

```bash
./check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --restart-warning 3 \
  --restart-critical 5
```

Example problem:

```text
SYSTEMD CRITICAL: system state degraded; 0 matching problem units; application.service restarted 7 times | problems=0 excluded=0 restarts=7
```

See [docs/check_systemd_health.md](docs/check_systemd_health.md) for detailed documentation.

---

### check_container_health.py

Python 3 Nagios/Icinga plugin for monitoring Docker container state, health, restart counts, and resource usage.

Current version: **1.0.1**

Version 1.0.1 supports Docker. Podman support is not yet available.

Features:

- Automatic Docker runtime detection
- Monitoring of all Docker containers on a host
- Monitoring of one specific container by exact name, full ID, or unique ID prefix
- Shell-style `--include` and `--exclude` filtering
- Expected-container monitoring with `--expect`
- Container state monitoring
- Docker HEALTHCHECK monitoring
- Detection of OOM-killed containers
- Optional Docker lifetime restart-count monitoring
- CPU usage monitoring
- Memory usage monitoring
- PID count collection
- CPU and memory WARNING/CRITICAL thresholds
- CPU percentages above 100% supported
- Detection of containers without an explicit Docker memory limit
- Nagios-compatible performance data
- Configurable problem-count thresholds
- Configurable command timeout
- Configurable maximum problem details
- Verbose and debug output
- Nagios-compatible OK, WARNING, CRITICAL, and UNKNOWN exit codes
- No third-party Python modules required
- Read-only Docker monitoring
- 109 hardware-independent automated tests

Basic check:

```bash
./check_container_health.py
```

Example:

```text
CONTAINERS OK: 5 containers, 5 running, no problems | containers=5 running=5 stopped=0 paused=0 restarting=0 unhealthy=0 oom_killed=0 missing=0 restarts=0
```

Monitor one container:

```bash
./check_container_health.py \
  --container kof-grafana
```

Example:

```text
CONTAINERS OK: kof-grafana running, health=none, restarts=0 | containers=1 running=1 stopped=0 paused=0 restarting=0 unhealthy=0 oom_killed=0 missing=0 restarts=0
```

Monitor one container including CPU, memory, and PID statistics:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-resources
```

Example:

```text
CONTAINERS OK: kof-grafana running, health=none, restarts=0, CPU 0.05%, memory 2.22% | containers=1 running=1 stopped=0 paused=0 restarting=0 unhealthy=0 oom_killed=0 missing=0 restarts=0 'kof-grafana_cpu'=0.05% 'kof-grafana_memory'=2.22% 'kof-grafana_memory_bytes'=178887065B 'kof-grafana_pids'=16
```

Configure CPU and memory thresholds:

```bash
./check_container_health.py \
  --container kof-grafana \
  --check-resources \
  --cpu-warning 80 \
  --cpu-critical 95 \
  --memory-warning 80 \
  --memory-critical 90
```

Monitor restart counts:

```bash
./check_container_health.py \
  --check-restarts \
  --restart-warning 3 \
  --restart-critical 5
```

Restart monitoring uses Docker's lifetime `RestartCount`. Version 1.0.1 does not currently provide a time-window-based restart counter.

Require specific containers:

```bash
./check_container_health.py \
  --expect kof-grafana \
  --expect kof-nginx_be
```

Monitor only selected container groups:

```bash
./check_container_health.py \
  --include 'kof-*'
```

Exclude selected containers:

```bash
./check_container_health.py \
  --exclude 'test-*'
```

Combine include and exclude filters:

```bash
./check_container_health.py \
  --include 'atom-*' \
  --exclude '*fluent-bit'
```

Resource and restart monitoring can be combined:

```bash
./check_container_health.py \
  --check-restarts \
  --check-resources
```

The plugin performs read-only Docker queries and does not intentionally create, start, stop, restart, pause, unpause, or remove containers.

See [docs/check_container_health.md](docs/check_container_health.md) for detailed documentation.

## Download

### Download check_dnf.py

Latest released version:

```bash
curl -L -o check_dnf.py \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-dnf-v1.2.1/plugins/check_dnf.py

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

### Download check_container_health.py

Latest released version:

```bash
curl -L -o check_container_health.py \
  https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/check-container-health-v1.0.1/plugins/check_container_health.py

chmod +x check_container_health.py
```

See the [Releases](https://github.com/cscsanaki/Nagios-Plugins/releases) page for plugin-specific release notes and source archives.

## Installation

### RHEL / Rocky Linux

The standard Nagios plugin directory is commonly:

```text
/usr/lib64/nagios/plugins
```

### check_dnf.py

```bash
sudo cp check_dnf.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_dnf.py
```

### check_librenms_validate

```bash
sudo cp check_librenms_validate /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_librenms_validate
```

### check_hpe_hardware.py

```bash
sudo cp check_hpe_hardware.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

### check_ssacli_disks.sh

```bash
sudo cp check_ssacli_disks.sh /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

### check_hpe_raid.py

```bash
sudo cp check_hpe_raid.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_hpe_raid.py
```

### check_systemd_health.py

```bash
sudo cp check_systemd_health.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_systemd_health.py
```

### check_container_health.py

```bash
sudo cp check_container_health.py /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_container_health.py
```

The account running the container plugin must be able to communicate with the Docker daemon.

Test access with:

```bash
docker info
docker ps
```

For NRPE:

```bash
sudo -u nrpe docker info
sudo -u nrpe docker ps
```

Docker socket access is security-sensitive and should be granted carefully.

## NRPE examples

### DNF

```text
command[check_dnf]=/usr/lib64/nagios/plugins/check_dnf.py
```

### LibreNMS

```text
command[check_librenms_validate]=/usr/lib64/nagios/plugins/check_librenms_validate
```

### HPE hardware

```text
command[check_hpe_hardware]=/usr/lib64/nagios/plugins/check_hpe_hardware.py
```

### HPE physical disks

```text
command[check_ssacli_disks]=/usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

### HPE RAID

```text
command[check_hpe_raid]=/usr/lib64/nagios/plugins/check_hpe_raid.py
```

### systemd health

```text
command[check_systemd_health]=/usr/lib64/nagios/plugins/check_systemd_health.py
```

Restart monitoring example:

```text
command[check_systemd_health_restarts]=/usr/lib64/nagios/plugins/check_systemd_health.py --check-restarts --since 30m --restart-warning 3 --restart-critical 5
```

### Docker container health

Basic host-level monitoring:

```text
command[check_container_health]=/usr/lib64/nagios/plugins/check_container_health.py
```

Health plus restart monitoring:

```text
command[check_container_health_restarts]=/usr/lib64/nagios/plugins/check_container_health.py --check-restarts
```

Resource monitoring:

```text
command[check_container_resources]=/usr/lib64/nagios/plugins/check_container_health.py --check-resources
```

Specific container monitoring:

```text
command[check_container_grafana]=/usr/lib64/nagios/plugins/check_container_health.py --container kof-grafana --check-restarts --check-resources --cpu-warning 80 --cpu-critical 95 --memory-warning 80 --memory-critical 90
```

## Nagios exit codes

All plugins follow the standard Nagios exit-code convention:

| Exit code | State |
| ---: | --- |
| 0 | OK |
| 1 | WARNING |
| 2 | CRITICAL |
| 3 | UNKNOWN |

## Testing

The repository contains automated tests for the plugins.

### check_dnf.py

```bash
python3 -m unittest tests/test_check_dnf.py -v
```

### check_librenms_validate

```bash
bash tests/test_check_librenms_validate.sh
```

### check_hpe_hardware.py

```bash
python3 -m unittest tests/test_check_hpe_hardware.py -v
```

### check_ssacli_disks.sh

```bash
bash tests/test_check_ssacli_disks.sh
```

### check_hpe_raid.py

```bash
python3 -m unittest tests/test_check_hpe_raid.py -v
```

### check_systemd_health.py

```bash
PYTHONPATH=plugins \
python3 -m unittest tests/test_check_systemd_health.py -v
```

The systemd health plugin currently has 46 automated tests.

### check_container_health.py

```bash
PYTHONPATH=plugins \
python3 -m unittest tests/test_check_container_health.py -v
```

The container health plugin currently has **109 automated tests**.

The tests cover, among other things:

- Docker inspect parsing
- Docker statistics parsing
- Containers with and without HEALTHCHECK
- Running containers
- Created containers
- Paused containers
- Restarting containers
- Exited containers
- Dead containers
- OOM-killed containers
- Restart thresholds
- CPU thresholds
- CPU values above 100%
- Memory thresholds
- Container-name and ID selection
- Include/exclude filtering
- Expected containers
- Performance data
- Docker command failures
- Docker command timeouts
- Complete OK/WARNING/CRITICAL/UNKNOWN execution paths

## Continuous integration

GitHub Actions validates the repository with:

- Python 3.9
- Python 3.11
- Python 3.13

The CI workflow performs:

- Python syntax checks
- Plugin CLI checks
- Python unit tests
- Bash syntax checks
- Bash plugin tests
- Detection of committed Python bytecode
- Detection of legacy package-manager references

For `check_container_health.py`, CI performs:

```text
Check container health plugin syntax
Check container health plugin CLI
Run container health plugin tests
```

The container test suite contains 109 tests and does not require access to a live Docker daemon.

## Repository layout

```text
Nagios-Plugins/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/
│   │   └── plugin-tests.yml
│   └── pull_request_template.md
├── docs/
│   ├── check_container_health.md
│   ├── check_dnf.md
│   ├── check_hpe_hardware.md
│   ├── check_hpe_raid.md
│   ├── check_librenms_validate.md
│   ├── check_ssacli_disks.md
│   └── check_systemd_health.md
├── plugins/
│   ├── check_container_health.py
│   ├── check_dnf.py
│   ├── check_hpe_hardware.py
│   ├── check_hpe_raid.py
│   ├── check_librenms_validate
│   ├── check_ssacli_disks.sh
│   └── check_systemd_health.py
├── tests/
│   ├── test_check_container_health.py
│   ├── test_check_dnf.py
│   ├── test_check_hpe_hardware.py
│   ├── test_check_hpe_raid.py
│   ├── test_check_librenms_validate.sh
│   ├── test_check_ssacli_disks.sh
│   └── test_check_systemd_health.py
├── .gitignore
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── SECURITY.md
```

## Requirements summary

### check_dnf.py

- Python 3
- DNF
- RHEL-compatible Linux distribution
- DNF `needs-restarting` support when reboot detection is enabled

Reboot detection uses:

```text
dnf -q needs-restarting -r

### check_librenms_validate

- Bash
- LibreNMS
- `validate.php`
- Permission to execute validation as the `librenms` user

### check_hpe_hardware.py

- Python 3
- HPE ProLiant server
- HPE iLOrest
- Local iLO CHIF access or supported iLOrest configuration

### check_ssacli_disks.sh

- Bash
- HPE Smart Array controller
- HPE Smart Storage Administrator CLI (`ssacli`)

### check_hpe_raid.py

- Python 3
- HPE Smart Array controller
- HPE Smart Storage Administrator CLI (`ssacli`)

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

### check_systemd_health.py

- Python 3
- systemd
- `systemctl`
- `journalctl` when restart monitoring is enabled
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- Sufficient journal access for the account running the plugin

### check_container_health.py

- Python 3
- Docker CLI
- Docker Engine
- Permission to communicate with the Docker daemon
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

No third-party Python modules are required.

Podman is not supported by `check_container_health.py` version 1.0.1.

## Documentation

- [check_container_health.py documentation](docs/check_container_health.md)
- [check_dnf.py documentation](docs/check_dnf.md)
- [check_librenms_validate documentation](docs/check_librenms_validate.md)
- [check_hpe_hardware.py documentation](docs/check_hpe_hardware.md)
- [check_ssacli_disks.sh documentation](docs/check_ssacli_disks.md)
- [check_hpe_raid.py documentation](docs/check_hpe_raid.md)
- [check_systemd_health.py documentation](docs/check_systemd_health.md)
- [Changelog](CHANGELOG.md)

## Contributing

Contributions are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

Please follow the repository's [Code of Conduct](CODE_OF_CONDUCT.md).

Security issues should be reported according to [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for details.
