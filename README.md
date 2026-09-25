# Nagios Plugins

A collection of Nagios/Icinga monitoring plugins.

## Download

Latest release: **v1.2.0**

Download `check_dnf.py` directly:

```bash
curl -L -o check_dnf.py https://raw.githubusercontent.com/cscsanaki/Nagios-Plugins/v1.2.0/plugins/check_dnf.py
chmod +x check_dnf.py
```

Or clone the complete repository:

```bash
git clone https://github.com/cscsanaki/Nagios-Plugins.git
cd Nagios-Plugins
```

See the [latest release](https://github.com/cscsanaki/Nagios-Plugins/releases/latest) for release notes and source archives.

## Quick installation

Install `check_dnf.py` into the standard Nagios plugin directory:

```bash
sudo install -o root -g root -m 0755 plugins/check_dnf.py /usr/lib64/nagios/plugins/check_dnf
```

Test it locally:

```bash
/usr/lib64/nagios/plugins/check_dnf
echo $?
```

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
- Reports installed security kernel and currently running kernel when DNF
  provides that information
- Nagios-compatible performance data
- Repository enable/disable options
- Optional cache-only operation
- Configurable timeout and security thresholds
- Verbose diagnostic output
- Uses Nagios standard exit codes

### Example

```console
$ ./plugins/check_dnf.py
DNF CRITICAL: 0 security updates, 13 non-security updates, 13 total, reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8) | security_updates=0 non_security_updates=13 total_updates=13 reboot_required=1
```

## Installation

```bash
sudo install -o root -g root -m 0755 plugins/check_dnf.py /usr/lib64/nagios/plugins/check_dnf
```

Test it directly before configuring NRPE:

```bash
/usr/lib64/nagios/plugins/check_dnf
echo $?
```

See [docs/check_dnf.md](docs/check_dnf.md) for full usage information.

## Nagios exit codes

| Code | State | Meaning |
|---:|---|---|
| 0 | OK | Check completed and no configured warning/critical condition exists |
| 1 | WARNING | A configured warning condition exists |
| 2 | CRITICAL | Security updates, required reboot, or another configured critical condition exists |
| 3 | UNKNOWN | The check could not reliably determine package status |

## Requirements

- Python 3
- DNF
- Nagios, Icinga, NRPE, or another monitoring system supporting Nagios plugin semantics

The reboot check uses `dnf needs-restarting -r` when available.

## License

MIT. See [LICENSE](LICENSE).
