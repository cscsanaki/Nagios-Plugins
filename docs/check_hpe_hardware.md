# check_hpe_hardware.py

`check_hpe_hardware.py` is a Nagios/Icinga plugin for monitoring HPE server
hardware through the local HPE iLOrest CLI.

Current version: **1.0.6**

## Tested environments

The plugin has been tested on real HPE hardware with:

| Server | OS | iLO | iLOrest |
|---|---|---|---|
| HPE ProLiant DL380 Gen10 | Rocky Linux 9 | iLO 5 | 7.3.0.0 |
| HPE ProLiant DL380 Gen11 | Debian 12 (Bookworm) | iLO 6 | 7.3.0.0 |

The Debian 12 / DL380 Gen11 configuration has been validated on two separate
servers, including local CHIF access, NRPE execution, and end-to-end Nagios
monitoring.

Example healthy Gen10 result:

```text
HPE OK: hardware is healthy (Model: HPE ProLiant DL380 Gen10, S/N: CZ282701B5, ROM: U30 v3.70 (08/19/2026), iLO: iLO 5: 3.21 Jul 30 2026)
```

Example healthy Gen11 result:

```text
HPE OK: hardware is healthy (Model: HPE ProLiant DL380 Gen11, S/N: CZ2D2M083G, ROM: U54 v3.00 (08/20/2026), iLO: iLO 6: 1.78 Jul 29 2026)
```

## Requirements

- Python 3
- HPE iLOrest
- Local access to the HPE iLO Channel Interface (CHIF)
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

Tested HPE iLOrest version:

```text
7.3.0.0
```

On the tested Rocky Linux system, iLOrest is installed at:

```text
/usr/sbin/ilorest
```

On the tested Debian 12 systems, iLOrest is installed in a Python virtual
environment at:

```text
/opt/ilorest/bin/ilorest
```

## iLOrest executable discovery

Version 1.0.4 automatically searches for iLOrest in the following order:

```text
/opt/ilorest/bin/ilorest
/usr/sbin/ilorest
/usr/bin/ilorest
/usr/local/bin/ilorest
PATH
```

A custom executable can still be specified explicitly:

```bash
check_hpe_hardware.py --ilorest /custom/path/ilorest
```

## Debian 12 iLOrest installation

The Debian 12 repository version of iLOrest was not suitable for local CHIF
access in the tested environment because the required CHIF userspace library
was not available to the tool.

The working configuration uses iLOrest 7.3.0.0 in a dedicated Python virtual
environment.

Install the Python virtual environment support:

```bash
sudo apt update
sudo apt install python3-venv
```

Create the environment:

```bash
sudo python3 -m venv /opt/ilorest
```

Upgrade pip inside the environment:

```bash
sudo /opt/ilorest/bin/pip install --upgrade pip
```

Install iLOrest:

```bash
sudo /opt/ilorest/bin/pip install ilorest
```

Verify the installation:

```bash
/opt/ilorest/bin/ilorest --version
```

Expected version:

```text
RESTful Interface Tool 7.3.0.0
```

The installation should contain the Linux CHIF userspace library, for example:

```text
/opt/ilorest/lib/python3.11/site-packages/ilorest/chiflibrary/ilorest_chif.so
```

Verify local CHIF access:

```bash
sudo /opt/ilorest/bin/ilorest login
sudo /opt/ilorest/bin/ilorest systeminfo
sudo /opt/ilorest/bin/ilorest logout
```

On the tested DL380 Gen11 systems, `systeminfo` successfully returned the
server model, serial number, active ROM version, iLO 6 version, processor,
memory, power supply, fan, and thermal health information.

## Status mapping

| Condition | Nagios state | Exit code |
|---|---|---:|
| Hardware healthy | OK | 0 |
| Degraded / warning health state | WARNING | 1 |
| Critical / failed health state | CRITICAL | 2 |
| iLOrest, CHIF, timeout, login, or execution failure | UNKNOWN | 3 |

The plugin preserves the worst hardware state found. A later WARNING cannot
downgrade an earlier CRITICAL state.

## Gen10 and Gen11 parsing

HPE iLOrest `systeminfo` output can contain multiple `Model:` fields.

For example, on Gen11 the server model is reported as:

```text
Model: HPE ProLiant DL380 Gen11
```

while the processor section can later contain:

```text
Model: INTEL(R) XEON(R) SILVER 4510
```

The plugin preserves the server model and does not allow component model fields
to overwrite it.

Gen11 systems can also report both the active and redundant ROM:

```text
Bios Version: U54 v3.00 (08/20/2026)
System ROM : U54 v3.00 (08/20/2026)
Redundant System ROM : U54 v2.94 (06/25/2026)
```

The plugin reports the active BIOS/System ROM and does not allow the redundant
ROM to overwrite it.

Both iLO 5 and iLO 6 firmware lines are supported.

## Usage

```text
check_hpe_hardware.py [OPTIONS]

-t, --timeout SECONDS   iLOrest command timeout (default: 60)
--ilorest PATH          Path to the iLOrest executable (default: auto-detect)
-v, --verbose           Increase diagnostic output
-V, --version           Show plugin version
-h, --help              Show help
```

Verbose diagnostics can be increased with `-v`, `-vv`, or `-vvv`.

The default iLOrest command timeout was increased to 60 seconds because local
CHIF operations on the tested Gen11/iLO 6 systems can take longer than
15 seconds.

The timeout is a maximum per iLOrest command; it does not force every command
to run for 60 seconds.

## Installation

### RHEL / Rocky Linux

The standard Nagios plugin directory is commonly:

```text
/usr/lib64/nagios/plugins
```

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_hardware.py \
  /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Test:

```bash
sudo /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

### Debian

The standard Nagios plugin directory is commonly:

```text
/usr/lib/nagios/plugins
```

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_hardware.py \
  /usr/lib/nagios/plugins/check_hpe_hardware.py
```

Test:

```bash
sudo /usr/lib/nagios/plugins/check_hpe_hardware.py
```

## Local execution and CHIF permissions

On the tested HPE systems, iLOrest requires elevated privileges to access the
local CHIF interface.

Running the plugin without the required privileges can result in an iLOrest or
CHIF access error.

This is reported as UNKNOWN rather than CRITICAL because the monitoring check
could not reliably determine the hardware state.

Do not grant unrestricted sudo access to the NRPE account.

## NRPE integration

The complete plugin runs with elevated privileges so iLOrest can access the
local CHIF interface.

Use a narrowly scoped sudoers rule that permits only the plugin itself.

Security: The sudoers rule must restrict the plugin to execution without command-line arguments. The trailing "" prevents the NRPE account from passing arbitrary options, including --ilorest, which could otherwise select an unintended executable running with root privileges.

The plugin and its parent directories must be owned by trusted administrators and must not be writable by the NRPE account. Verify that no other sudoers rule grants broader access. Custom executable paths should only be configured through administrator-controlled, reviewed configurations.

These examples must also be applied to the actual monitored servers; updating this documentation does not change existing sudoers permissions.

### RHEL / Rocky Linux

Example sudoers rule when NRPE runs as `nrpe`:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_hpe_hardware.py ""
```

Example NRPE command:

```text
command[check_hpe_hardware]=sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

Test locally:

```bash
sudo -u nrpe sudo -n /usr/lib64/nagios/plugins/check_hpe_hardware.py
```

### Debian

On the tested Debian 12 systems, NRPE runs as the `nagios` user.

Example sudoers rule:

```text
nagios ALL=(root) NOPASSWD: /usr/lib/nagios/plugins/check_hpe_hardware.py ""
```

Example NRPE command:

```text
command[check_hpe_hardware]=sudo -n /usr/lib/nagios/plugins/check_hpe_hardware.py
```

Test locally:

```bash
sudo -u nagios sudo -n /usr/lib/nagios/plugins/check_hpe_hardware.py
```

Validate sudoers after editing:

```bash
sudo visudo -c
```

Test from the Nagios server:

```bash
check_nrpe -H <hpe-server> -c check_hpe_hardware
```

The exact `check_nrpe` path depends on the Nagios installation.

## BIOS fallback

The plugin normally obtains the ROM/BIOS version from iLOrest.

If unavailable, it first attempts to read:

```text
/sys/class/dmi/id/bios_version
```

and only then falls back to `dmidecode`.

## IML details

When a WARNING or CRITICAL hardware state is detected, the plugin requests the
iLO Integrated Management Log (IML) and appends the last three relevant
entries to the monitoring output.


### IML output formatting (v1.0.5)

Version 1.0.5 improves the formatting of Integrated Management Log (IML) information in Nagios/Icinga output.

IML details are appended to the human-readable plugin status text using `; IML Logs:` instead of the Nagios performance data separator (`|`).

Example:

```text
HPE CRITICAL: hardware health degraded; IML Logs: Memory failure detected
```

If IML retrieval fails, the diagnostic message also remains part of the status text:

```text
HPE CRITICAL: hardware health degraded; IML Logs: unable to retrieve detailed IML logs (CHIF unavailable)
```

This prevents IML messages from being interpreted as Nagios performance data.

The change does not modify hardware health detection, severity mapping, or Nagios exit codes.

Two regression tests verify the formatting of successful and failed IML retrieval.


ANSI terminal colour sequences are removed from IML text.

## Nagios UNKNOWN exit code handling (v1.0.6)

Version 1.0.6 improves error handling for invalid command-line arguments and unexpected runtime exceptions.

Invalid command-line arguments now return Nagios UNKNOWN (exit code 3) instead of the default argparse exit code 2, which Nagios would interpret as CRITICAL.

Examples:

```bash
./check_hpe_hardware.py --invalid-option
./check_hpe_hardware.py --timeout abc
./check_hpe_hardware.py --timeout 0
```

All three commands return UNKNOWN (3).

Unexpected runtime exceptions are handled by the protected `run_main()` entry point and reported as UNKNOWN (3) instead of terminating with an unhandled traceback.

Example diagnostic output:

```text
HPE UNKNOWN: unexpected error: OSError: simulated filesystem error
```

The `--help` and `--version` options continue to exit with code 0.

Existing hardware health detection, IML reporting, severity mapping, and normal Nagios exit codes remain unchanged.

## Automated tests

The unit tests mock iLOrest and do not require HPE hardware:

```bash
python -m unittest tests/test_check_hpe_hardware.py -v
```

The test suite covers:

- HPE ProLiant DL380 Gen10 system information parsing
- HPE ProLiant DL380 Gen11 system information parsing
- iLO 5 parsing
- iLO 6 parsing
- server model preservation when component `Model:` fields are present
- active ROM preservation when a redundant ROM is present
- System ROM fallback when `Bios Version` is unavailable
- OK, WARNING, CRITICAL, and UNKNOWN states
- severity priority
- login failure
- systeminfo failure
- empty output
- command timeout
- non-zero iLOrest exit code
- IML parsing
- ANSI removal
- explicit iLOrest executable selection
- `/opt/ilorest/bin/ilorest` auto-discovery
- `/usr/sbin/ilorest` auto-discovery
- PATH fallback
- missing iLOrest handling
- 60-second default timeout validation
- Invalid command-line arguments returning Nagios UNKNOWN
- Invalid timeout values returning Nagios UNKNOWN
- Unexpected runtime exceptions returning Nagios UNKNOWN

GitHub Actions runs the tests with Python 3.9, 3.11, and 3.13.
