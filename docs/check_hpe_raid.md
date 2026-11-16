# check_hpe_raid.py

`check_hpe_raid.py` is a Nagios/Icinga plugin for monitoring HPE Smart Array
RAID health through HPE Smart Storage Administrator CLI (`ssacli`).

Current version: **1.0.3**

## Requirements

- Python 3
- HPE Smart Array controller
- **HPE Smart Storage Administrator CLI (`ssacli`)**
- Nagios, Icinga, NRPE, or another Nagios-compatible monitoring system
- `sudo` when elevated privileges are required for local `ssacli` access

**The HPE `ssacli` package must be installed on the monitored server.**

The plugin automatically searches for `ssacli` in:

```text
PATH
/usr/sbin/ssacli
/usr/bin/ssacli
/usr/local/bin/ssacli
```

A custom executable can also be specified with:

```bash
check_hpe_raid.py --ssacli /custom/path/ssacli
```

Verify that `ssacli` is installed and working:

```bash
/usr/sbin/ssacli version
```

## Tested environment

The plugin has been validated on real HPE Smart Array hardware.

Tested controller:

```text
HPE Smart Array P408i-a SR Gen10
```

The tested configuration contains:

```text
Controller
├── Array A
│   └── LUN1
└── Array B
    └── LUN2
```

A healthy result from the tested system:

```text
HPE RAID OK: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:OK], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=0
```

The complete monitoring path has also been validated through:

```text
HPE Smart Array
      |
    ssacli
      |
check_hpe_raid.py
      |
     sudo
      |
     NRPE
      |
 Nagios server
```

## What the plugin monitors

The plugin monitors three levels of the HPE Smart Array RAID configuration:

- Smart Array controllers
- Arrays
- Logical drives

Controller information is obtained with:

```text
ssacli controller all show status
```

Logical drive information is obtained for every discovered controller with:

```text
ssacli controller slot=<slot> logicaldrive all show
```

All discovered controllers are checked.

## Controller health

A controller reporting:

```text
Controller Status: OK
```

is considered healthy.

A non-OK controller status is CRITICAL.

If a controller is discovered but no controller status is available, the
result is UNKNOWN.

## Array health

Arrays are discovered from the logical drive output.

Example:

```text
array A (OK)
```

An array reporting `OK` is considered healthy.

A non-OK array status is CRITICAL.

## Logical drive health

Logical drive status is evaluated independently for every discovered logical
drive.

The following statuses are considered OK:

```text
OK
Disabled
```

The following statuses generate WARNING:

```text
Rebuild
Rebuilding
Recover
Recovering
```

Other logical drive states, including `Failed` and
`Interim Recovery Mode`, generate CRITICAL.

## Status mapping

| Condition | Nagios state | Exit code |
|---|---|---:|
| All controllers, arrays and logical drives healthy | OK | 0 |
| Logical drive rebuilding or recovering | WARNING | 1 |
| Controller not OK | CRITICAL | 2 |
| Array not OK | CRITICAL | 2 |
| Logical drive failed or otherwise unhealthy | CRITICAL | 2 |
| `ssacli` missing or not executable | UNKNOWN | 3 |
| `ssacli` execution failure | UNKNOWN | 3 |
| `ssacli` command timeout | UNKNOWN | 3 |
| No Smart Array controller found | UNKNOWN | 3 |
| Controller status unavailable | UNKNOWN | 3 |
| No arrays found for a controller | UNKNOWN | 3 |

The plugin preserves the worst state found during the complete check.

For example, a CRITICAL logical drive followed by another logical drive in
WARNING state still produces a final CRITICAL result.

## Usage

```text
check_hpe_raid.py [-h] [-t TIMEOUT] [--ssacli SSACLI] [-V]
```

Options:

```text
-h, --help
    Show help and exit.

-t TIMEOUT, --timeout TIMEOUT
    ssacli command timeout in seconds.
    Default: 30 seconds.

--ssacli SSACLI
    Explicit path to the ssacli executable.

-V, --version
    Show plugin version and exit.
```

Show the version:

```bash
./check_hpe_raid.py --version
```

Expected output:

```text
check_hpe_raid.py 1.0.0
```

Show help:

```bash
./check_hpe_raid.py --help
```

## Performance data

The plugin provides Nagios-compatible performance data:

```text
controllers=<number> arrays=<number> logical_drives=<number> problems=<number>
```

Example:

```text
controllers=1 arrays=2 logical_drives=2 problems=0
```

The values represent:

- `controllers` — number of discovered Smart Array controllers
- `arrays` — number of discovered arrays
- `logical_drives` — number of discovered logical drives
- `problems` — number of detected non-OK conditions

## Example outputs

### Healthy RAID

```text
HPE RAID OK: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:OK], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=0
```

### Logical drive rebuilding

Example:

```text
HPE RAID WARNING: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:Rebuild], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=1
```

### Failed logical drive

Example:

```text
HPE RAID CRITICAL: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:Failed], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=1
```

## Installation

The standard Nagios plugin directory on RHEL-compatible systems is commonly:

```text
/usr/lib64/nagios/plugins
```

Install the plugin:

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_hpe_raid.py \
  /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Verify:

```bash
/usr/lib64/nagios/plugins/check_hpe_raid.py --version
```

Expected output:

```text
check_hpe_raid.py 1.0.0
```

## Local test

Run the plugin with the privileges required for `ssacli`:

```bash
sudo /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Check the Nagios exit code:

```bash
echo $?
```

A healthy system returns:

```text
0
```

## NRPE integration

On the tested system, `ssacli` requires elevated privileges.

Use a narrowly scoped sudoers rule rather than unrestricted sudo access.

Example:

```text
nrpe ALL=(root) NOPASSWD: /usr/lib64/nagios/plugins/check_hpe_raid.py ""
```

Validate the sudoers configuration:

```bash
sudo visudo -c
```
Security: The trailing "" in the sudoers rule restricts the plugin to execution without command-line arguments. This prevents the NRPE account from using --ssacli to select an arbitrary executable with root privileges.

The plugin executable and all parent directories must be owned by trusted administrators and must not be writable by the NRPE account. Verify that no other sudoers rule grants broader access.

If custom command-line arguments are required, use a separately reviewed and tightly restricted sudoers configuration rather than removing the argument restriction.

Updating this documentation does not change the permissions on already deployed monitoring servers.

Example NRPE command:

```text
command[check_hpe_raid]=sudo -n /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Test using the NRPE account:

```bash
sudo -u nrpe sudo -n \
  /usr/lib64/nagios/plugins/check_hpe_raid.py
```

Expected healthy result:

```text
HPE RAID OK: HPE Smart Array P408i-a SR Gen10[OK]: Array A(OK)[LUN1:OK], Array B(OK)[LUN2:OK] | controllers=1 arrays=2 logical_drives=2 problems=0
```

Remote test from the Nagios server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <hpe-server> \
  -c check_hpe_raid
```

Do not grant unrestricted sudo access to the NRPE account.

## ssacli dependency

The plugin does not communicate directly with the Smart Array controller.

It uses HPE Smart Storage Administrator CLI (`ssacli`) to obtain controller,
array, and logical drive information.

Therefore:

**The HPE `ssacli` package is a mandatory runtime dependency.**

Check that it is available:

```bash
command -v ssacli
```

or:

```bash
/usr/sbin/ssacli version
```

If `ssacli` is installed at a non-standard location:

```bash
check_hpe_raid.py \
  --ssacli /custom/path/ssacli
```

## Error handling

### ssacli missing

If `ssacli` cannot be found:

```text
HPE RAID UNKNOWN: ssacli executable not found
```

### Invalid explicit ssacli path

Example:

```text
HPE RAID UNKNOWN: ssacli executable not found or not executable: /custom/path/ssacli
```

### Command timeout

A timed-out `ssacli` command returns UNKNOWN.

Example:

```text
HPE RAID UNKNOWN: command exceeded timeout (30s): ...
```

### ssacli command failure

A non-zero `ssacli` exit status returns UNKNOWN and includes the command error
when available.

### No controller

If no HPE Smart Array controller is discovered:

```text
HPE RAID UNKNOWN: no HPE Smart Array controllers found
```

## Nagios UNKNOWN exit code handling (v1.0.1)

Version 1.0.1 improves error handling for invalid command-line arguments and unexpected runtime exceptions.

Invalid command-line arguments now return Nagios UNKNOWN (exit code 3) instead of the default argparse exit code 2, which Nagios would interpret as CRITICAL.

Examples:

```bash
./check_hpe_raid.py --invalid-option
./check_hpe_raid.py --timeout abc
```

Both commands return UNKNOWN (3).

Unexpected runtime exceptions are also handled and reported as UNKNOWN (3) instead of terminating with an unhandled traceback.

Example diagnostic output:

```text
HPE RAID UNKNOWN: unexpected error: OSError: simulated filesystem error
```

The `--help` and `--version` options continue to exit with code 0.

Existing RAID controller, array, and logical drive health monitoring remains unchanged.

## Release correction (v1.0.3)

Version 1.0.3 is a corrective release following an incorrectly
targeted v1.0.2 GitHub release tag.

The v1.0.2 tag referenced an older commit containing the v1.0.1
plugin implementation.

Version 1.0.3 is intended to publish the complete, previously
developed HPE RAID monitoring improvements, including:

- Controller cache health monitoring.
- Battery/capacitor health monitoring.
- WARNING and CRITICAL severity evaluation for controller components.
- Logical drive recovery and rebuild progress parsing.
- Detailed controller component diagnostics in Nagios output.
- Updated problem counters.

No additional monitoring functionality is introduced compared with
the corrected v1.0.2 source code already merged into main.

The release retains the 45 automated regression tests validated
with Python 3.9, 3.11, and 3.13.

## Controller health and recovery parsing (v1.0.2)

Version 1.0.2 extends HPE Smart Array monitoring to include controller cache and battery/capacitor health.

### Controller component monitoring

The plugin now parses the following `ssacli` fields when available:

- `Controller Status`
- `Cache Status`
- `Battery/Capacitor Status`
- `Battery Status`
- `Capacitor Status`

Cache and battery/capacitor health states are evaluated independently of the overall controller status.

| Component status | Nagios state |
|---|---|
| OK, Not Applicable, N/A | OK (0) |
| Degraded, Recharging, Charging, Recovering | WARNING (1) |
| Failed or other unrecognized states | CRITICAL (2) |

Missing component fields are ignored because not all HPE Smart Array controllers expose the same hardware information.

Affected components are included in the human-readable Nagios output.

Example:

```text
HPE RAID CRITICAL: HPE Smart Array P408i-a SR Gen10[OK][Cache:Failed, Capacitor:Recharging]: Array A(OK)[LUN1:OK] | controllers=1 arrays=1 logical_drives=1 problems=2
```

### Logical drive recovery progress

The logical drive parser now recognizes recovery and rebuild progress information without treating the progress percentage as a separate drive status.

Examples:

```text
logicaldrive 1 (447.1 GB, RAID 1, Recovering, 45% complete)
logicaldrive 2 (1.8 TB, RAID 5, Rebuilding, 80% complete)
```

Both logical drives are reported as WARNING (1), rather than incorrectly being classified as CRITICAL.

### Monitoring behavior

- Existing controller, array, and logical drive monitoring is preserved.
- Cache and battery/capacitor failures contribute to the `problems` performance counter.
- Degraded and recharging components produce WARNING.
- CRITICAL takes precedence over WARNING when multiple component problems are detected.
- Existing Nagios exit codes and command-line options remain unchanged.

## Automated tests

The plugin includes hardware-independent unit tests:

```bash
python3 -m unittest tests/test_check_hpe_raid.py -v
```

The current test suite contains **45 tests**.

The tests cover:

- controller discovery and parsing
- controller model, slot and status
- multiple controllers
- missing controller status
- array discovery and parsing
- multiple arrays
- array status
- logical drive discovery
- logical drive status parsing
- OK logical drive state
- Disabled logical drive state
- Rebuild / Rebuilding WARNING states
- Recover / Recovering WARNING states
- Failed logical drive state
- Interim Recovery Mode
- unexpected logical drive states
- successful `ssacli` command execution
- command timeout
- non-zero command exit status
- explicit missing `ssacli`
- PATH-based `ssacli` discovery
- complete healthy RAID state
- controller CRITICAL state
- array CRITICAL state
- logical drive CRITICAL state
- WARNING state
- UNKNOWN state
- no controller
- no arrays
- multiple controllers
- worst-severity preservation
- Nagios performance data
- Invalid command-line arguments returning Nagios UNKNOWN
- Invalid timeout values returning Nagios UNKNOWN
- Unexpected runtime exceptions returning Nagios UNKNOWN
- Controller cache status parsing and severity evaluation
- Battery/capacitor status parsing and severity evaluation
- Logical drive recovery and rebuild progress parsing
- WARNING and CRITICAL precedence for multiple component problems
- Nagios diagnostic output and problem counter validation

The tests do not require HPE hardware or an installed `ssacli` package.

A successful run ends with:

```text
Ran 33 tests in ...

OK
```

## Continuous integration

GitHub Actions validates the plugin with:

- Python syntax checks
- CLI `--version` and `--help` checks
- all 33 hardware-independent unit tests

The tests run on:

```text
Python 3.9
Python 3.11
Python 3.13
```

The repository workflow is:

```text
.github/workflows/plugin-tests.yml
```

## Comparison with check_ssacli_disks.sh

The repository contains two complementary Smart Array plugins.

`check_hpe_raid.py` monitors:

```text
Smart Array controller
        ↓
      Array
        ↓
   Logical drive
```

`check_ssacli_disks.sh` monitors:

```text
Physical drives
```

Using both provides monitoring of the logical RAID configuration and the
underlying physical disks.

## Nagios exit codes

- `0` — OK
- `1` — WARNING
- `2` — CRITICAL
- `3` — UNKNOWN

## License

MIT
