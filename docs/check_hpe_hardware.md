# check_hpe_hardware.py

`check_hpe_hardware.py` is a Nagios/Icinga plugin for monitoring HPE server
hardware through the local HPE iLOrest CLI.

Current version: **1.0.0**

## Tested environment

The plugin has been tested with:

- HPE ProLiant DL380 Gen10
- HPE iLO 5
- iLOrest 7.3.0.0-7
- Python 3
- NRPE

A tested healthy result:

```text
HPE OK: hardware is healthy (Model: HPE ProLiant DL380 Gen10, S/N: CZ282701B5, ROM: U30 v3.68 (07/23/2026), iLO: iLO 5: 3.21 Jul 30 2026)
```

## Requirements

- Python 3
- HPE iLOrest
- Local access to the HPE iLO Channel Interface (CHIF)
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

Tested RPM:

```text
ilorest-7.3.0.0-7.x86_64
```

The default iLOrest executable is:

```text
/usr/sbin/ilorest
```

## Status mapping

| Condition | Nagios state | Exit code |
|---|---|---:|
| Hardware healthy | OK | 0 |
| Degraded / warning health state | WARNING | 1 |
| Critical / failed health state | CRITICAL | 2 |
| iLOrest, CHIF, timeout, login, or execution failure | UNKNOWN | 3 |

The plugin preserves the worst hardware state found. A later WARNING cannot
downgrade an earlier CRITICAL state.

## Usage

```text
check_hpe_hardware.py [OPTIONS]

-t, --timeout SECONDS   iLOrest command timeout (default: 15)
--ilorest PATH          Path to the iLOrest executable
-v, --verbose           Increase diagnostic output
-V, --version           Show plugin version
-h, --help              Show help
```

Verbose diagnostics can be increased with `-v`, `-vv`, or `-vvv`.

## Installation

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_hardware.py \
  /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

## Local execution and CHIF permissions

On the tested HPE system, iLOrest requires elevated privileges to access CHIF.

Running the plugin as an unprivileged user produced:

```text
HPE UNKNOWN: iLOrest login failed: command exited with code 34: /usr/sbin/ilorest login: ... Chif driver not found ...
```

Running the same plugin with the required privileges returned the correct
hardware state.

This is treated as UNKNOWN rather than CRITICAL because the monitoring check
could not determine the hardware state.

## NRPE integration

On the tested system the complete plugin must run as root so iLOrest can access
the local CHIF interface.

Use a narrowly scoped sudoers rule:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Validate sudoers after editing:

```bash
sudo visudo -c
```

Example NRPE command:

```text
command[check_hpe_hardware]=sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Test locally as the NRPE account:

```bash
sudo -u nrpe sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Test from the Nagios server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <hpe-server> \
  -c check_hpe_hardware
```

Do not grant unrestricted sudo access to the NRPE account.

## BIOS fallback

The plugin normally obtains the ROM/BIOS version from iLOrest. If unavailable,
it first attempts to read:

```text
/sys/class/dmi/id/bios_version
```

and only then falls back to `dmidecode`.

## IML details

When a WARNING or CRITICAL hardware state is detected, the plugin requests the
iLO Integrated Management Log (IML) and appends the last three relevant
entries to the monitoring output.

ANSI terminal colour sequences are removed from IML text.

## Automated tests

The unit tests mock iLOrest and do not require HPE hardware:

```bash
python -m unittest tests/test_check_hpe_hardware.py -v
```

They cover:

- system identity parsing
- OK, WARNING, CRITICAL, and UNKNOWN states
- severity priority
- login failure
- systeminfo failure
- empty output
- command timeout
- non-zero iLOrest exit code
- IML parsing
- ANSI removal
