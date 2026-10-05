# check_systemd_health.py

Nagios/Icinga plugin for monitoring systemd unit health and excessive service
restarts.

Current version: **1.0.2**

## Overview

`check_systemd_health.py` monitors the health of systemd-based Linux systems.

The plugin can:

- Detect failed systemd units
- Monitor arbitrary systemd unit states
- Filter by unit type
- Include or exclude individual units or wildcard patterns
- Apply configurable WARNING and CRITICAL thresholds
- Detect excessive automatic service restarts
- Count restart events within a configurable time window
- Detect restart events even when the affected service is no longer loaded
- Provide Nagios-compatible performance data
- Return standard Nagios exit codes
- Provide verbose and debug output

The plugin has been tested on Rocky Linux 9 with systemd.

Automated tests are run under:

- Python 3.9
- Python 3.11
- Python 3.13

## Requirements

- Python 3
- systemd
- `systemctl`
- `journalctl` when restart monitoring is enabled
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system

Restart monitoring requires sufficient access to the systemd journal for the
account executing the plugin.

No third-party Python modules are required.

## Installation

### RHEL / Rocky Linux

The standard Nagios plugin directory is commonly:

```text
/usr/lib64/nagios/plugins
```

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_systemd_health.py \
  /usr/lib64/nagios/plugins/check_systemd_health.py
```

Verify the installed version:

```bash
/usr/lib64/nagios/plugins/check_systemd_health.py --version
```

Expected output:

```text
check_systemd_health.py 1.0.2
```

Display help:

```bash
/usr/lib64/nagios/plugins/check_systemd_health.py --help
```

## Basic usage

Run:

```bash
/usr/lib64/nagios/plugins/check_systemd_health.py
```

On a healthy system:

```text
SYSTEMD OK: system running; 0 matching problem units | problems=0 excluded=0
```

Exit code:

```text
0
```

By default, the plugin checks systemd units in the `failed` state.

If one or more matching failed units are found, the default result is
CRITICAL.

Example:

```text
SYSTEMD CRITICAL: system state degraded; 1 matching unit - backup.service | problems=1 excluded=0
```

## Command-line options

```text
--exclude PATTERN
--include PATTERN
--type TYPE
--state STATE
--warning N
--critical N
--check-restarts
--restart-warning N
--restart-critical N
--since TIME
-t SECONDS
--timeout SECONDS
-v
-vv
-V
--version
-h
--help
```

## Unit filtering

### --include

Only units matching the supplied pattern are considered.

Example:

```bash
check_systemd_health.py \
  --include 'nginx.service'
```

Shell-style wildcards are supported:

```bash
check_systemd_health.py \
  --include 'nginx-*'
```

`--include` may be specified multiple times.

Example:

```bash
check_systemd_health.py \
  --include 'nginx*' \
  --include 'httpd*'
```

### --exclude

Units matching the supplied pattern are excluded.

Example:

```bash
check_systemd_health.py \
  --exclude 'backup.service'
```

Wildcards are supported:

```bash
check_systemd_health.py \
  --exclude 'dnf-*'
```

Multiple exclusions can be supplied:

```bash
check_systemd_health.py \
  --exclude 'dnf-*' \
  --exclude 'test-*'
```

Exclusion takes precedence over inclusion.

For example:

```bash
check_systemd_health.py \
  --include '*.service' \
  --exclude 'backup.service'
```

will check matching services except `backup.service`.

If the system is degraded only because of explicitly excluded failed units,
the plugin can return OK.

Example:

```text
SYSTEMD OK: system degraded; all matching problem units are excluded | problems=0 excluded=1
```

## Unit type filtering

Use `--type` to restrict the check to a specific systemd unit type.

Example:

```bash
check_systemd_health.py \
  --type service
```

Other examples:

```bash
check_systemd_health.py --type timer
check_systemd_health.py --type mount
check_systemd_health.py --type socket
```

A failed service does not make a check restricted to timers CRITICAL.

For example:

```bash
check_systemd_health.py \
  --type timer
```

can return:

```text
SYSTEMD OK: 0 matching timer problem units | problems=0 excluded=0
```

even when an unrelated service is failed.

## Unit state filtering

The default checked state is:

```text
failed
```

Specify another state with:

```bash
check_systemd_health.py \
  --state inactive
```

`--state` may be specified multiple times.

Example:

```bash
check_systemd_health.py \
  --state failed \
  --state activating
```

A type and state can be combined:

```bash
check_systemd_health.py \
  --type service \
  --state failed
```

## Problem thresholds

Without explicit thresholds:

```text
0 matching problem units -> OK
1 or more matching problem units -> CRITICAL
```

Thresholds can be configured with:

```text
--warning N
--critical N
```

Example:

```bash
check_systemd_health.py \
  --warning 1 \
  --critical 3
```

This means:

```text
0 problems     -> OK
1-2 problems   -> WARNING
3+ problems    -> CRITICAL
```

Example WARNING:

```text
SYSTEMD WARNING: system state degraded; 1 matching unit - backup.service | problems=1 excluded=0
```

The WARNING threshold must be lower than the CRITICAL threshold.

Invalid configuration:

```bash
check_systemd_health.py \
  --warning 5 \
  --critical 3
```

Result:

```text
SYSTEMD UNKNOWN: --warning must be lower than --critical
```

Exit code:

```text
3
```

## Restart monitoring

Restart monitoring is enabled with:

```text
--check-restarts
```

Example:

```bash
check_systemd_health.py \
  --check-restarts
```

The plugin reads automatic service restart events from the systemd journal.

A restart is counted from systemd journal messages containing:

```text
Scheduled restart job
```

The plugin intentionally does not rely on the lifetime `NRestarts` counter.
Only restart events inside the requested time window are counted.

Restart monitoring uses a single journal query for the requested time window.
This keeps the check efficient even on systems with many services.

It can also detect restart events for services that are no longer loaded when
the check runs, as long as the relevant event is still available in the
journal.

## Restart monitoring window

Use `--since` to define the restart monitoring window.

Supported suffixes:

| Suffix | Meaning |
| --- | --- |
| `s` | seconds |
| `m` | minutes |
| `h` | hours |
| `d` | days |

Examples:

```text
30s
15m
2h
1d
```

Example:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m
```

The default restart monitoring window is:

```text
30m
```

Invalid example:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30minutes
```

Result:

```text
SYSTEMD UNKNOWN: argument --since: must use the format Ns, Nm, Nh or Nd (examples: 30m, 2h, 1d)
```

Exit code:

```text
3
```

## Restart thresholds

Default restart thresholds are:

```text
WARNING  = 3
CRITICAL = 5
```

They can be changed using:

```text
--restart-warning N
--restart-critical N
```

Example:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --restart-warning 3 \
  --restart-critical 5
```

Restart thresholds are evaluated **per service**, not against the combined
number of restarts across all services.

Example WARNING:

```text
SYSTEMD WARNING: system state degraded; 0 matching problem units; nginx.service restarted 3 times | problems=0 excluded=0 restarts=3
```

Example CRITICAL:

```text
SYSTEMD CRITICAL: system state degraded; 0 matching problem units; nginx.service restarted 7 times | problems=0 excluded=0 restarts=7
```

The restart WARNING threshold must be lower than the restart CRITICAL
threshold.

## Restart filtering

The same `--include` and `--exclude` patterns also apply to restart
monitoring.

Example:

```bash
check_systemd_health.py \
  --check-restarts \
  --include 'nginx*' \
  --since 30m
```

Only matching services are considered.

Example exclusion:

```bash
check_systemd_health.py \
  --check-restarts \
  --exclude 'test-*' \
  --since 30m
```

## Combined health and restart monitoring

Failed-unit monitoring and restart monitoring can be used together.

Example:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --warning 1 \
  --critical 3 \
  --restart-warning 3 \
  --restart-critical 5
```

The plugin preserves the most severe Nagios state.

For example:

```text
failed unit status = WARNING
restart status     = CRITICAL
final status       = CRITICAL
```

## Performance data

The plugin provides Nagios-compatible performance data.

Basic example:

```text
problems=0 excluded=0
```

With restart monitoring:

```text
problems=0 excluded=0 restarts=7
```

Fields:

| Metric | Meaning |
| --- | --- |
| `problems` | Number of matching problematic systemd units |
| `excluded` | Number of matching problematic units excluded by filters |
| `restarts` | Total restart events found after restart filtering |

Restart WARNING and CRITICAL thresholds are evaluated per service even though
the `restarts` performance metric reports the total number of matched restart
events.

## Verbose output

Use:

```text
-v
```

Example:

```bash
check_systemd_health.py -v
```

Example output:

```text
System state: running
Checked states: failed
Matching units before filtering: 0
Matching units after filtering: 0
Excluded units: 0
SYSTEMD OK: system running; 0 matching problem units | problems=0 excluded=0
```

With restart monitoring:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m \
  -v
```

Verbose output includes restart counts for discovered services.

## Debug output

Use:

```text
-vv
```

Example:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --restart-warning 3 \
  --restart-critical 5 \
  -vv
```

Debug output additionally displays:

- include patterns
- exclude patterns
- unit thresholds
- command timeout
- restart thresholds

## Timeout

The default command timeout is:

```text
30 seconds
```

Change it with:

```bash
check_systemd_health.py \
  --timeout 60
```

or:

```bash
check_systemd_health.py \
  -t 60
```

The timeout must be greater than zero.

Command timeouts are reported as UNKNOWN.

## Invalid arguments

Invalid command-line arguments are reported using the Nagios UNKNOWN exit
code rather than the default argparse exit code.

Example:

```bash
check_systemd_health.py --foobar
```

Result:

```text
SYSTEMD UNKNOWN: unrecognized arguments: --foobar
```

Exit code:

```text
3
```

Restart-specific options require `--check-restarts`.

For example:

```bash
check_systemd_health.py \
  --since 30m
```

returns:

```text
SYSTEMD UNKNOWN: --restart-warning, --restart-critical and --since require --check-restarts
```

## Nagios exit codes

| Code | State | Meaning |
| ---: | --- | --- |
| 0 | OK | No configured problem condition detected |
| 1 | WARNING | Configured warning condition detected |
| 2 | CRITICAL | Configured critical condition detected |
| 3 | UNKNOWN | Check could not reliably determine system state |

## NRPE integration

### Basic check

Example NRPE configuration:

```text
command[check_systemd_health]=/usr/lib64/nagios/plugins/check_systemd_health.py
```

Remote test:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <server> \
  -c check_systemd_health
```

### Restart monitoring

Example:

```text
command[check_systemd_health]=/usr/lib64/nagios/plugins/check_systemd_health.py --check-restarts --since 30m --restart-warning 3 --restart-critical 5
```

The NRPE account must have sufficient permission to read the relevant systemd
journal entries.

Test journal access using the same account that runs the plugin.

For example, on a system using the `nrpe` account:

```bash
sudo -u nrpe journalctl \
  --since "30 minutes ago" \
  --no-pager \
  -o cat \
  _PID=1
```

If the required journal entries are not visible, configure journal access
according to the security policy of the monitored system.

Do not grant unrestricted sudo access solely to enable journal monitoring.

## Examples

### Check all failed units

```bash
check_systemd_health.py
```

### Check only failed services

```bash
check_systemd_health.py \
  --type service
```

### Check failed timers

```bash
check_systemd_health.py \
  --type timer
```

### Ignore a known failed service

```bash
check_systemd_health.py \
  --exclude 'known-broken.service'
```

### Ignore a group of units

```bash
check_systemd_health.py \
  --exclude 'test-*'
```

### Check selected services

```bash
check_systemd_health.py \
  --include 'nginx*' \
  --include 'httpd*'
```

### Configure problem thresholds

```bash
check_systemd_health.py \
  --warning 1 \
  --critical 3
```

### Monitor restart loops

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --restart-warning 3 \
  --restart-critical 5
```

### Monitor restarts for selected services

```bash
check_systemd_health.py \
  --check-restarts \
  --include 'nginx*' \
  --since 1h \
  --restart-warning 3 \
  --restart-critical 5
```

### Full debug output

```bash
check_systemd_health.py \
  --check-restarts \
  --since 30m \
  --restart-warning 3 \
  --restart-critical 5 \
  -vv
```

## Troubleshooting

### Plugin reports UNKNOWN for journal access

Run the journal query using the same account that executes the plugin.

Example:

```bash
sudo -u nrpe journalctl \
  --since "30 minutes ago" \
  --no-pager \
  -o cat \
  _PID=1
```

Verify that systemd service restart events are visible.

### Restart count is zero

Verify that automatic restart events exist:

```bash
journalctl \
  --since "30 minutes ago" \
  --no-pager \
  -o cat \
  _PID=1 |
grep 'Scheduled restart job'
```

Increase the time window if necessary:

```bash
check_systemd_health.py \
  --check-restarts \
  --since 2h
```

### System is degraded but plugin returns OK

This can be expected when:

- the failed unit is excluded with `--exclude`
- the failed unit does not match `--include`
- `--type` restricts the check to another unit type
- `--state` restricts the check to another state

The plugin evaluates the configured monitoring scope rather than blindly
mapping every `systemctl is-system-running` degraded state to CRITICAL.

### Check systemd directly

Overall state:

```bash
systemctl is-system-running
```

Failed units:

```bash
systemctl \
  --failed \
  --no-legend \
  --no-pager \
  --plain
```

## Automated tests

The repository contains:

```text
tests/test_check_systemd_health.py
```

Run the test suite from the repository root:

```bash
PYTHONPATH=plugins \
  python3 -m unittest tests/test_check_systemd_health.py -v
```

The current suite contains **46 tests**.

The tests cover:

- duration parsing
- exact include filtering
- wildcard include filtering
- exact exclude filtering
- wildcard exclude filtering
- exclude precedence
- problem thresholds
- restart journal parsing
- restart service extraction
- restart include/exclude filtering
- restart thresholds
- worst-state selection
- argument validation
- restart defaults
- restart summary generation
- main OK state
- main WARNING state
- main CRITICAL state
- excluded failed units
- restart WARNING state
- restart CRITICAL state
- command failure UNKNOWN state

A successful run ends with:

```text
Ran 46 tests in ...

OK
```

## Continuous integration

GitHub Actions validates the plugin under:

```text
Python 3.9
Python 3.11
Python 3.13
```

The workflow performs:

- Python syntax validation
- CLI version check
- CLI help check
- all 46 automated tests
- committed Python bytecode detection
- repository legacy-reference checks

Workflow:

```text
.github/workflows/plugin-tests.yml
```

## License

MIT. See the repository [LICENSE](../LICENSE) file.
