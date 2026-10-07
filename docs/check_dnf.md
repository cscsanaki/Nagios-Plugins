# check_dnf.py

`check_dnf.py` is a Nagios/Icinga plugin for monitoring package updates on
modern DNF-based RHEL-compatible Linux distributions.

Current version: **1.2.1**

## Features

- Detects available package updates through DNF
- Separates security and non-security updates
- Reports security updates as CRITICAL by default
- Supports configurable security WARNING and CRITICAL thresholds
- Supports optional WARNING for non-security updates
- Supports CRITICAL status for any available update
- Detects whether a reboot is required
- Reports reboot-required status as CRITICAL by default
- Reports the reason for a required reboot when provided by
  `dnf needs-restarting -r`
- Reports updated components such as `linux-firmware` directly in Nagios output
- Supports multiple reboot reasons
- Preserves security-kernel versus running-kernel information when a kernel
  reboot is required
- Gives kernel-specific reboot information priority over generic reboot reasons
- Falls back to a generic `reboot required` message when no specific reason
  can be extracted
- Supports disabling reboot detection
- Supports reporting a reboot requirement without changing the Nagios state to
  CRITICAL
- Provides Nagios-compatible performance data
- Supports repository enable/disable options
- Supports an alternative DNF configuration file
- Supports cache-only operation
- Detects DNF command failures and timeouts
- Handles package-manager lock conditions
- Provides verbose diagnostic output
- Includes automated regression tests

## Requirements

- Python 3
- DNF
- DNF `needs-restarting` support for reboot detection
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

The reboot check uses:

```text
dnf -q needs-restarting -r
```

When available, the plugin can also fall back to:

```text
/usr/bin/needs-restarting -r
```

The DNF `needs-restarting` functionality must therefore be available if reboot
detection is enabled.

If reboot detection is not required, it can be disabled with:

```text
--no-reboot-check
```

## Tested environment

The plugin has been validated on Rocky Linux 9.

Version 1.2.1 has also been validated against a real reboot-required condition
reported by DNF:

```text
Core libraries or services have been updated since boot-up:
  * linux-firmware

Reboot is required to fully utilize these updates.
```

The resulting Nagios output is:

```text
DNF CRITICAL: 0 security updates, 0 non-security updates, 0 total, reboot required (linux-firmware updated since boot) | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

Automated tests are run with:

```text
Python 3.9
Python 3.11
Python 3.13
```

## Status mapping

The default status mapping is:

| Condition | Nagios state | Exit code |
|---|---|---:|
| No security updates and no reboot required | OK | 0 |
| Non-security updates only | OK | 0 |
| Security updates available | CRITICAL | 2 |
| Reboot required | CRITICAL | 2 |
| DNF execution failure | UNKNOWN | 3 |
| DNF command timeout | UNKNOWN | 3 |

Additional command-line options can change some of these defaults.

For example:

- `--warn-on-any-update` makes non-security updates WARNING
- `--all-updates` makes any available package update CRITICAL
- `--no-reboot-critical` reports a reboot requirement without making the check
  CRITICAL
- `--no-reboot-check` disables reboot detection

## Usage

```text
check_dnf.py [OPTIONS]
```

Show all options:

```bash
./check_dnf.py --help
```

Show the version:

```bash
./check_dnf.py --version
```

Expected output:

```text
check_dnf.py 1.2.1
```

## Command-line options

### All updates

```text
-A, --all-updates
```

Return CRITICAL if any package update is available.

Example:

```bash
./check_dnf.py --all-updates
```

### Warn on any update

```text
-W, --warn-on-any-update
```

Return WARNING when non-security updates are available and no higher-priority
condition exists.

Example:

```bash
./check_dnf.py --warn-on-any-update
```

### Cache-only mode

```text
-C, --cache-only
```

Use cached repository metadata only.

Example:

```bash
./check_dnf.py --cache-only
```

### Enable repositories

```text
-e REPO, --enablerepo REPO
```

May be specified multiple times.

Example:

```bash
./check_dnf.py \
  --enablerepo=baseos \
  --enablerepo=appstream
```

### Disable repositories

```text
-d REPO, --disablerepo REPO
```

May be specified multiple times.

Example:

```bash
./check_dnf.py --disablerepo=epel
```

### Alternative DNF configuration

```text
-c FILE, --config FILE
```

Use an alternative DNF configuration file.

Example:

```bash
./check_dnf.py --config /etc/dnf/dnf.conf
```

### DNF lock handling

```text
-N, --no-warn-on-lock
```

Return OK instead of WARNING if the package manager is locked by another
process.

### Timeout

```text
-t SECONDS, --timeout SECONDS
```

Set the DNF command timeout.

Default:

```text
120 seconds
```

Allowed range:

```text
1 - 3600 seconds
```

Example:

```bash
./check_dnf.py --timeout 180
```

### Security WARNING threshold

```text
--warning-security N
```

Return WARNING when at least `N` security updates are available.

The default value is:

```text
0
```

which disables the WARNING threshold.

### Security CRITICAL threshold

```text
--critical-security N
```

Return CRITICAL when at least `N` security updates are available.

Default:

```text
1
```

The WARNING threshold, when enabled, must be lower than the CRITICAL
threshold.

### Disable reboot detection

```text
--no-reboot-check
```

Disable the reboot-required check entirely.

When this option is used, `reboot_required` is omitted from the performance
data.

### Do not make reboot CRITICAL

```text
--no-reboot-critical
```

Continue reporting that a reboot is required, but do not change the Nagios
state to CRITICAL solely because of the reboot requirement.

For example, with no updates and `linux-firmware` requiring a reboot:

```text
DNF OK: 0 security updates, 0 non-security updates, 0 total, reboot required (linux-firmware updated since boot) | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

### Verbose diagnostics

```text
-v, --verbose
```

The option can be specified multiple times:

```bash
./check_dnf.py -v
./check_dnf.py -vv
./check_dnf.py -vvv
```

For example, `-vv` shows the commands being executed:

```text
DEBUG2: running command: /usr/bin/dnf -q check-update
DEBUG2: running command: /usr/bin/dnf -q --security check-update
DEBUG2: running reboot check: /usr/bin/dnf -q needs-restarting -r
```

Higher verbosity also includes command return codes and command output.

## Package update detection

The plugin performs two DNF queries.

All updates:

```text
dnf -q check-update
```

Security updates:

```text
dnf -q --security check-update
```

DNF `check-update` uses these relevant return codes:

```text
0    no updates
100  updates available
```

Both are valid results for the plugin.

Other DNF failures are handled separately.

The plugin extracts package names from DNF output and calculates:

```text
security updates
non-security updates
total updates
```

Duplicate package entries are counted only once.

## Reboot detection

Unless disabled with:

```text
--no-reboot-check
```

the plugin first attempts:

```text
dnf -q needs-restarting -r
```

The expected return-code convention is:

```text
0 = reboot not required
1 = reboot required
```

If the DNF reboot check cannot be used, the plugin can also attempt:

```text
/usr/bin/needs-restarting -r
```

When the reboot check cannot determine the status, the monitoring output
contains:

```text
reboot status unavailable
```

## Reboot reason reporting

Version **1.2.1** adds extraction of reboot reasons from
`dnf needs-restarting -r`.

For example, DNF may return:

```text
Core libraries or services have been updated since boot-up:
  * linux-firmware

Reboot is required to fully utilize these updates.
More information: https://access.redhat.com/solutions/27943
```

The plugin extracts:

```text
linux-firmware
```

and reports:

```text
reboot required (linux-firmware updated since boot)
```

This makes it possible to see directly from Nagios why a reboot is required.

### Single reboot reason

Input:

```text
Core libraries or services have been updated since boot-up:
  * linux-firmware
```

Nagios output includes:

```text
reboot required (linux-firmware updated since boot)
```

### Multiple reboot reasons

If multiple components are reported:

```text
Core libraries or services have been updated since boot-up:
  * linux-firmware
  * systemd
```

the plugin reports:

```text
reboot required (linux-firmware, systemd updated since boot)
```

### No extractable reason

If DNF reports that a reboot is required but no individual component can be
extracted, the plugin falls back to:

```text
reboot required
```

This preserves compatibility with reboot-check output formats that do not
provide a component list.

## Kernel reboot reporting

The plugin retains its existing security-kernel detection.

When DNF reports both an installed security kernel and the currently running
kernel, the plugin extracts information such as:

```text
Security: kernel-core-5.14.0-687.49.1.el9_8.x86_64 is an installed security update
Security: kernel-core-5.14.0-687.46.1.el9_8.x86_64 is the currently running version
```

and reports:

```text
reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8)
```

Architecture suffixes such as:

```text
.x86_64
```

are removed from the displayed kernel versions.

### Kernel information has priority

If both a kernel mismatch and another reboot reason such as
`linux-firmware` are present, the kernel-specific message takes priority.

For example:

```text
reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8)
```

is shown instead of:

```text
reboot required (linux-firmware updated since boot)
```

This preserves the more specific kernel information from earlier plugin
versions.

## Example outputs

### No updates and no reboot required

```text
DNF OK: 0 security updates, 0 non-security updates, 0 total, reboot not required | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=0
```

### Non-security updates only

```text
DNF OK: 0 security updates, 13 non-security updates, 13 total, reboot not required | security_updates=0 non_security_updates=13 total_updates=13 reboot_required=0
```

### Security updates available

Example:

```text
DNF CRITICAL: 2 security updates, 5 non-security updates, 7 total, reboot not required | security_updates=2 non_security_updates=5 total_updates=7 reboot_required=0
```

### Reboot required because of linux-firmware

```text
DNF CRITICAL: 0 security updates, 0 non-security updates, 0 total, reboot required (linux-firmware updated since boot) | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

### Reboot required because of a security kernel

```text
DNF CRITICAL: 0 security updates, 13 non-security updates, 13 total, reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8) | security_updates=0 non_security_updates=13 total_updates=13 reboot_required=1
```

### Reboot reason unavailable

If a reboot is required but no reason can be extracted:

```text
DNF CRITICAL: 0 security updates, 0 non-security updates, 0 total, reboot required | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

### Reboot status unavailable

If reboot detection cannot determine a result:

```text
DNF OK: 0 security updates, 0 non-security updates, 0 total, reboot status unavailable | security_updates=0 non_security_updates=0 total_updates=0
```

## Performance data

The plugin provides Nagios-compatible performance data:

```text
security_updates=<number>
non_security_updates=<number>
total_updates=<number>
reboot_required=<0|1>
```

Normal example:

```text
security_updates=0 non_security_updates=13 total_updates=13 reboot_required=0
```

Reboot-required example:

```text
security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

When reboot detection is disabled or unavailable, `reboot_required` may be
omitted.

## DNF lock handling

If DNF reports that another process is holding the package-manager lock, the
plugin normally returns WARNING.

With:

```text
--no-warn-on-lock
```

the same condition returns OK.

## Error handling

### DNF command failure

Unexpected DNF failures return UNKNOWN.

Example:

```text
DNF UNKNOWN: dnf failed with exit code 1: Failed to download metadata
```

### Command timeout

A command exceeding the configured timeout returns UNKNOWN.

Example:

```text
DNF UNKNOWN: command exceeded timeout (120s): /usr/bin/dnf -q check-update
```

### DNF executable missing

If neither DNF nor DNF5 can be found:

```text
DNF UNKNOWN: dnf executable not found
```

## Installation

The standard Nagios plugin directory on RHEL-compatible systems is commonly:

```text
/usr/lib64/nagios/plugins
```

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_dnf.py \
  /usr/lib64/nagios/plugins/check_dnf.py
```

Verify:

```bash
/usr/lib64/nagios/plugins/check_dnf.py --version
```

Expected result:

```text
check_dnf.py 1.2.1
```

Run a local check:

```bash
/usr/lib64/nagios/plugins/check_dnf.py
```

For additional diagnostics:

```bash
/usr/lib64/nagios/plugins/check_dnf.py -vv
```

## NRPE integration

Example NRPE command:

```text
command[check_dnf]=/usr/lib64/nagios/plugins/check_dnf.py
```

Test locally using the NRPE account where appropriate.

Remote test from the Nagios server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <host> \
  -c check_dnf
```

The exact path to `check_nrpe` depends on the Nagios installation.

## Automated tests

The plugin includes hardware-independent regression tests:

```bash
python3 -m unittest tests/test_check_dnf.py -v
```

Version 1.2.1 currently has **40 automated tests**.

The test suite covers:

- empty update lists
- non-security updates
- security updates
- duplicate package entries
- multiple architectures
- DNF return code `0`
- DNF return code `100`
- DNF command failures
- command timeouts
- security-kernel parsing
- missing kernel status
- reboot not required
- reboot required
- single reboot reason
- multiple reboot reasons
- missing reboot reason
- unrelated bullet-list output
- empty reboot-check output
- `linux-firmware` reboot reason
- multiple component reboot reasons
- generic reboot-required fallback
- kernel reboot message priority
- reboot-required CRITICAL state
- `--no-reboot-check`
- `--no-reboot-critical`
- reboot status unavailable
- reboot performance data
- security WARNING thresholds
- security CRITICAL thresholds
- warning on non-security updates
- CRITICAL on all updates
- worst applicable Nagios state
- final Nagios output formatting

A successful run ends with:

```text
Ran 40 tests in ...

OK
```

## Continuous integration

GitHub Actions validates the plugin on:

```text
Python 3.9
Python 3.11
Python 3.13
```

The CI workflow performs:

- Python syntax validation
- `--version` validation
- `--help` validation
- all 40 `check_dnf.py` regression tests

The repository workflow is:

```text
.github/workflows/plugin-tests.yml
```

Version 1.2.1 has been successfully validated by the complete CI matrix on all
three supported Python versions.

## Changes in 1.2.1

Version 1.2.1 improves reboot-required reporting.

Previously, a non-kernel reboot requirement was reported as:

```text
reboot required
```

Version 1.2.1 can now report the component responsible:

```text
reboot required (linux-firmware updated since boot)
```

The release also adds:

- parsing of component names from `dnf needs-restarting -r`
- support for multiple reboot reasons
- generic fallback when no reason can be extracted
- preservation of kernel-specific reboot reporting
- kernel-message priority over generic reboot reasons
- improved reboot-check executable handling
- expanded automated regression coverage from the previous test suite to
  40 tests
- CI validation on Python 3.9, 3.11, and 3.13

## Nagios exit codes

- `0` — OK
- `1` — WARNING
- `2` — CRITICAL
- `3` — UNKNOWN

## License

MIT
