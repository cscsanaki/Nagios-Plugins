# check_ssacli_disks.sh

`check_ssacli_disks.sh` is a Nagios/Icinga plugin for monitoring HPE Smart
Array physical drive health through HPE Smart Storage Administrator CLI
(`ssacli`).

Current version: **1.0.0**

## Requirements

- Bash
- HPE Smart Array controller
- HPE Smart Storage Administrator CLI (`ssacli`)
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- `sudo` when elevated privileges are required for local `ssacli` access

**The HPE `ssacli` package must be installed on the monitored server.**

The plugin uses the following executable by default:

```text
/usr/sbin/ssacli
```

Verify that `ssacli` is installed and working:

```bash
/usr/sbin/ssacli version
```

A custom executable can be selected with the `SSACLI_BIN` environment
variable:

```bash
SSACLI_BIN=/custom/path/ssacli ./check_ssacli_disks.sh
```

## Tested environment

The plugin has been validated on real HPE Smart Array hardware with eight
physical drives.

The complete monitoring path has also been tested through:

```text
HPE Smart Array
      |
    ssacli
      |
check_ssacli_disks.sh
      |
     sudo
      |
     NRPE
      |
 Nagios server
```

Example healthy result:

```text
SSACLI OK: all 8 physical drive(s) are healthy | drives=8 problems=0
```

## What the plugin monitors

The plugin discovers all HPE Smart Array controllers reported by `ssacli`.

For every discovered controller it executes:

```text
ssacli ctrl slot=<slot> pd all show detail
```

and evaluates every physical drive.

A physical drive is considered healthy only when its reported status is:

```text
Status: OK
```

Any other status, including a missing status, is treated as a drive problem.

## Status mapping

| Condition | Nagios state | Exit code |
|---|---|---:|
| All physical drives healthy | OK | 0 |
| One or more physical drives not OK | CRITICAL | 2 |
| `ssacli` missing or not executable | UNKNOWN | 3 |
| Controller query failure | UNKNOWN | 3 |
| No Smart Array controller found | UNKNOWN | 3 |
| Physical drive query failure | UNKNOWN | 3 |
| No physical drives found | UNKNOWN | 3 |

The plugin currently does not generate a WARNING state.

## Output

Healthy example:

```text
SSACLI OK: all 8 physical drive(s) are healthy | drives=8 problems=0
```

Failed drive example:

```text
SSACLI CRITICAL: 1 problematic drive(s) found: Slot 0, Drive 1I:1:2 (Failed) | drives=8 problems=1
```

Multiple problematic drives are separated by semicolons.

Example:

```text
SSACLI CRITICAL: 2 problematic drive(s) found: Slot 0, Drive 1I:1:1 (Failed); Slot 0, Drive 1I:1:2 (Predictive Failure) | drives=3 problems=2
```

## Performance data

The plugin provides Nagios-compatible performance data:

```text
drives=<number> problems=<number>
```

Example:

```text
drives=8 problems=0
```

The `drives` value is the number of discovered physical drives.

The `problems` value is the number of physical drives whose status is not
`OK`.

## Usage

```text
check_ssacli_disks.sh [OPTIONS]

Options:
  -V, --version   Show plugin version and exit
  -h, --help      Show help and exit

Environment:
  SSACLI_BIN      Path to ssacli (default: /usr/sbin/ssacli)
```

Version:

```bash
./check_ssacli_disks.sh --version
```

Help:

```bash
./check_ssacli_disks.sh --help
```

## Installation

The standard Nagios plugin directory on RHEL-compatible systems is commonly:

```text
/usr/lib64/nagios/plugins
```

Install:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_ssacli_disks.sh \
  /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Verify:

```bash
/usr/lib64/nagios/plugins/check_ssacli_disks.sh --version
```

Expected result:

```text
check_ssacli_disks.sh 1.0.0
```

## Local test

Run the plugin with the privileges required for `ssacli`:

```bash
sudo /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

A healthy system should return exit code `0`:

```bash
echo $?
```

Example:

```text
SSACLI OK: all 8 physical drive(s) are healthy | drives=8 problems=0
```

## NRPE integration

On the tested system, `ssacli` requires elevated privileges.

The complete plugin is therefore executed through a narrowly scoped sudoers
rule.

Example:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Do not grant unrestricted sudo access to the NRPE account.

Example NRPE command:

```text
command[check_ssacli_disks]=sudo -n /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Test using the NRPE account:

```bash
sudo -u nrpe sudo -n \
  /usr/lib64/nagios/plugins/check_ssacli_disks.sh
```

Expected healthy result:

```text
SSACLI OK: all 8 physical drive(s) are healthy | drives=8 problems=0
```

Remote test from the Nagios server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <hpe-server> \
  -c check_ssacli_disks
```

The exact path to `check_nrpe` depends on the Nagios installation.

## Multiple controllers

The plugin automatically discovers all controller slot numbers reported by:

```bash
ssacli ctrl all show
```

Every discovered controller is checked.

Physical drive counts and problem counts are combined into a single Nagios
result.

## Error handling

### ssacli missing

If the configured executable does not exist or is not executable:

```text
SSACLI UNKNOWN: ssacli executable not found or not executable: /usr/sbin/ssacli
```

### Controller discovery failure

If `ssacli ctrl all show` fails:

```text
SSACLI UNKNOWN: failed to query controllers ...
```

### No controller

If no Smart Array controller can be discovered:

```text
SSACLI UNKNOWN: no Smart Array controllers found
```

### Drive query failure

If a controller cannot return physical drive information:

```text
SSACLI UNKNOWN: failed to query controller in slot <slot> ...
```

### No physical drives

If no physical drives are discovered:

```text
SSACLI UNKNOWN: no physical drives found
```

### Missing drive status

A discovered physical drive without a `Status:` value is treated as a
problematic drive and reported as:

```text
(status unknown)
```

## Automated tests

The test suite uses a mock `ssacli` executable and therefore does not require
HPE hardware or an installed `ssacli` package.

Run:

```bash
bash tests/test_check_ssacli_disks.sh
```

The test suite covers:

- `--version`
- `--help`
- unknown CLI options
- missing `ssacli`
- controller query failure
- no Smart Array controller
- physical drive query failure
- no physical drives
- healthy physical drives
- failed physical drive
- multiple failed physical drives
- missing physical drive status
- multiple Smart Array controllers
- Nagios exit codes
- performance data

The current suite contains 13 mock-based checks.

A successful test run ends with:

```text
Results: 13 passed, 0 failed
```

## Continuous integration

GitHub Actions runs:

- shell syntax validation for the plugin
- shell syntax validation for the test suite
- `--version` and `--help` CLI checks
- all mock-based tests

The repository workflow is:

```text
.github/workflows/plugin-tests.yml
```

The shell-based tests run as part of the existing Python 3.9, 3.11, and 3.13
CI matrix.

## Nagios exit codes

- `0` — OK
- `1` — WARNING (reserved; currently not generated)
- `2` — CRITICAL
- `3` — UNKNOWN

## License

MIT
