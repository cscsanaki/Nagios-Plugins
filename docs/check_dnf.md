# check_dnf.py

`check_dnf.py` checks available DNF package updates and returns a standard
Nagios/Icinga plugin status.

Current version: **1.2.0**

## Default policy

By default:

- no security updates and no required reboot: `OK`
- one or more security updates: `CRITICAL`
- reboot required: `CRITICAL`
- ordinary non-security updates alone: `OK`
- DNF execution failure or timeout: `UNKNOWN`

Default command timeout is 120 seconds.

## Usage

```bash
check_dnf.py [options]
```

Show all options:

```bash
check_dnf.py --help
```

Show version:

```bash
check_dnf.py --version
```

Verbose diagnostics:

```bash
check_dnf.py -vvv
```

## Useful options

`-A, --all-updates`
: Return CRITICAL if any package update is available.

`-W, --warn-on-any-update`
: Return WARNING when non-security updates are available and no higher-priority
  condition exists.

`-C, --cache-only`
: Use cached repository metadata only. Cached results can differ from current
  repository state if metadata is stale.

`-e REPO, --enablerepo REPO`
: Enable a repository. May be specified multiple times.

`-d REPO, --disablerepo REPO`
: Disable a repository. May be specified multiple times.

`-c FILE, --config FILE`
: Use an alternative DNF configuration file.

`-t SECONDS, --timeout SECONDS`
: Set command timeout. Default: 120 seconds.

`--warning-security N`
: Return WARNING at N security updates. Zero disables this warning threshold.

`--critical-security N`
: Return CRITICAL at N security updates. Default: 1.

`--no-reboot-check`
: Disable reboot-required detection.

`--no-reboot-critical`
: Report reboot requirement without changing the plugin state to CRITICAL.

## Performance data

Example:

```text
security_updates=0 non_security_updates=13 total_updates=13 reboot_required=1
```

This can be consumed by monitoring/performance-data systems.

## Reboot detection

Unless disabled, the plugin executes:

```bash
dnf -q needs-restarting -r
```

A reboot-required result is CRITICAL by default.

When DNF reports both an installed security kernel and the currently running
kernel, the human-readable plugin output includes both versions.

## Cache-only warning

`--cache-only` prevents repository metadata refresh. It is useful when metadata
is refreshed separately, but the result can be stale. For monitoring current
repository state, do not use `--cache-only` unless a separate process keeps the
DNF cache current.

## NRPE

A typical command definition is:

```text
command[check_dnf]=/usr/lib64/nagios/plugins/check_dnf
```

Before enabling it, run the plugin as the account used by NRPE and verify that
DNF and reboot detection work with that account's permissions.

The NRPE timeout should be longer than the plugin timeout.

## Exit codes

| Code | State |
|---:|---|
| 0 | OK |
| 1 | WARNING |
| 2 | CRITICAL |
| 3 | UNKNOWN |
