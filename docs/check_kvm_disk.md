# check_kvm_disk.sh

Nagios/Icinga plugin for monitoring filesystem disk usage inside KVM virtual machines through libvirt and QEMU Guest Agent.

**Current version:** 1.0.1

## Features

- Monitors filesystem disk usage inside running KVM virtual machines.
- Uses libvirt and QEMU Guest Agent without requiring SSH access to the guest.
- Supports monitoring individual filesystem mount points.
- Configurable WARNING and CRITICAL thresholds based on free disk space.
- Accepts thresholds with or without the `%` suffix.
- Reports used, available, and total filesystem capacity.
- Provides Nagios-compatible performance data with threshold ranges.
- Supports asynchronous QEMU Guest Agent command execution and polling.
- Configurable command timeout.
- Handles invalid arguments, guest-agent failures, command errors, and timeouts.
- Verbose diagnostic output.
- Standard Nagios OK, WARNING, CRITICAL, and UNKNOWN exit codes.
- Supports Nagios, Icinga, Centreon, and NRPE integration.
- Includes 20 automated mock-based regression tests.
- No Python modules required.

## Requirements

The KVM host requires:

- Bash
- KVM/QEMU and libvirt
- `virsh`
- `jq`
- `base64`
- Permission to communicate with libvirt and QEMU Guest Agent

The guest virtual machine requires:

- A running QEMU Guest Agent
- Support for `guest-exec` and `guest-exec-status`
- `/bin/df` executable

The plugin must run on the KVM host or another system with suitable libvirt access.

## Installation

Copy the plugin to the Nagios plugin directory.

On RHEL-compatible systems:

```bash
sudo cp check_kvm_disk.sh /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_kvm_disk.sh
```

Verify the installed version:

```bash
/usr/lib64/nagios/plugins/check_kvm_disk.sh --version
```

Expected output:

```text
check_kvm_disk.sh 1.0.1
```

Check Bash syntax:

```bash
bash -n /usr/lib64/nagios/plugins/check_kvm_disk.sh
```

## QEMU Guest Agent verification

Check that the virtual machine is running:

```bash
virsh domstate example-vm
```

Expected output:

```text
running
```

Verify communication with QEMU Guest Agent:

```bash
virsh qemu-agent-command example-vm '{"execute":"guest-ping"}'
```

Expected response:

```json
{"return":{}}
```

If the guest agent is unavailable, verify that the guest-agent service is running inside the virtual machine and that the VM has a configured guest-agent communication channel.

## Usage

Basic syntax:

```bash
./check_kvm_disk.sh -d <vm_name> -p <mount_point> -w <warning_percent> -c <critical_percent>
```

Example:

```bash
./check_kvm_disk.sh -d example-vm -p / -w 20 -c 10
```

Threshold values can also include `%`:

```bash
./check_kvm_disk.sh -d example-vm -p / -w 20% -c 10%
```

Both commands behave identically.

## Command-line options

| Option | Description |
|---|---|
| `-d NAME` | KVM virtual machine name |
| `-p PATH` | Filesystem mount point inside the guest |
| `-w PERCENT` | WARNING threshold for free disk space |
| `-c PERCENT` | CRITICAL threshold for free disk space |
| `-t SECONDS`, `--timeout SECONDS` | Command timeout |
| `-v`, `--verbose` | Enable verbose diagnostics |
| `-h`, `--help` | Display help |
| `-V`, `--version` | Display version |

Default timeout: **30 seconds**.

## Free-space thresholds

The plugin evaluates the percentage of available filesystem space.

Example:

```bash
./check_kvm_disk.sh -d example-vm -p / -w 20 -c 10
```

| Available space | Nagios state |
|---|---|
| More than 20% | OK |
| More than 10%, up to 20% | WARNING |
| 10% or less | CRITICAL |

The WARNING threshold must be greater than the CRITICAL threshold.

Invalid threshold values return UNKNOWN.

## Example output

The following values are illustrative and do not represent a specific production environment.

### OK

```text
DISK OK: VM=example-vm mount=/, 40% used, 60% free (60.00 GiB free / 100.00 GiB total, 40.00 GiB used)
```

### WARNING

```text
DISK WARNING: VM=example-vm mount=/, 82% used, 18% free (18.00 GiB free / 100.00 GiB total, 82.00 GiB used)
```

### CRITICAL

```text
DISK CRITICAL: VM=example-vm mount=/, 95% used, 5% free (5.00 GiB free / 100.00 GiB total, 95.00 GiB used)
```

## Filesystem usage calculation

The plugin executes:

```bash
df -P -k
```

inside the guest through QEMU Guest Agent.

The output contains filesystem capacity, used space, available space, and mount point information.

The plugin converts KiB values into GiB for human-readable output.

On filesystems with reserved blocks, used and available percentages may not total exactly 100%.

This is expected filesystem behavior.

## Performance data

The plugin returns Nagios-compatible performance data.

Illustrative example:

```text
'/_free_pct'=60%;@0:20;@0:10;0;100 '/_used_pct'=40% '/_used_kib'=41943040KB '/_free_kib'=62914560KB '/_total_kib'=104857600KB
```

| Metric | Description |
|---|---|
| `<mount>_free_pct` | Available disk space percentage |
| `<mount>_used_pct` | Used disk space percentage |
| `<mount>_used_kib` | Used space in KiB |
| `<mount>_free_kib` | Available space in KiB |
| `<mount>_total_kib` | Total filesystem size in KiB |

### Threshold range syntax

The free-space performance metric includes WARNING and CRITICAL thresholds.

Example:

```text
'/_free_pct'=60%;@0:20;@0:10;0;100
```

This expresses:

- WARNING when available space is between 0% and 20%, inclusive.
- CRITICAL when available space is between 0% and 10%, inclusive.

The plugin itself evaluates the configured thresholds and returns the appropriate Nagios exit code.

Graphing systems may differ in how they display Nagios range thresholds.

## QEMU Guest Agent execution

The plugin uses the following process:

1. Check whether the selected VM exists and is running.
2. Execute `df -P -k` inside the guest using `guest-exec`.
3. Retrieve the guest execution PID.
4. Poll `guest-exec-status` until the command finishes.
5. Verify the guest command exit code.
6. Decode the Base64-encoded command output.
7. Locate the requested filesystem mount point.
8. Calculate used and available space.
9. Evaluate WARNING and CRITICAL thresholds.
10. Return the Nagios status and performance data.

The plugin does not require SSH access to the virtual machine.

## Timeout handling

The default timeout is 30 seconds.

To increase it:

```bash
./check_kvm_disk.sh -d example-vm -p / -w 20 -c 10 --timeout 60
```

If the guest command does not finish within the timeout, the plugin returns UNKNOWN.

## Verbose output

Enable diagnostic output:

```bash
./check_kvm_disk.sh -d example-vm -p / -w 20 -c 10 -v
```

Verbose mode is intended for troubleshooting.

Normal Nagios/NRPE checks should generally run without verbose output.

## NRPE integration

The plugin runs on the KVM host and can be invoked remotely through NRPE.

Monitoring path:

```text
Nagios / Icinga / Centreon
          |
          | NRPE
          v
       KVM host
          |
          | libvirt / virsh
          v
    QEMU Guest Agent
          |
          | df -P -k
          v
    Guest filesystem
```

### NRPE command configuration

Example NRPE command definition:

```text
command[check_kvm_disk_root]=/usr/lib64/nagios/plugins/check_kvm_disk.sh -d example-vm -p / -w 20% -c 10%
```

The NRPE account must have permission to communicate with libvirt and QEMU Guest Agent.

Use narrowly scoped permissions where possible.

### Remote Nagios check

From the Nagios monitoring server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H kvm-host.example.com \
  -c check_kvm_disk_root
```

Illustrative output:

```text
DISK OK: VM=example-vm mount=/, 40% used, 60% free (60.00 GiB free / 100.00 GiB total, 40.00 GiB used) | '/_free_pct'=60%;@0:20;@0:10;0;100 '/_used_pct'=40% '/_used_kib'=41943040KB '/_free_kib'=62914560KB '/_total_kib'=104857600KB
```

Exit code:

```text
0
```

## Nagios exit codes

| Exit code | State | Meaning |
|---|---|---|
| 0 | OK | Available disk space is above WARNING threshold |
| 1 | WARNING | Available disk space is at or below WARNING threshold |
| 2 | CRITICAL | Available disk space is at or below CRITICAL threshold |
| 3 | UNKNOWN | Invalid arguments, VM unavailable, guest-agent error, parsing failure, or timeout |

## Troubleshooting

### Virtual machine not found

List available domains:

```bash
virsh list --all
```

Ensure the name supplied with `-d` matches the libvirt domain name.

### Virtual machine is not running

Check:

```bash
virsh domstate example-vm
```

### QEMU Guest Agent unavailable

Check:

```bash
virsh qemu-agent-command example-vm '{"execute":"guest-ping"}'
```

Verify the guest-agent service and communication channel.

### Guest command failure

Ensure `/bin/df` exists in the guest and that the guest agent supports command execution.

### Mount point not found

Verify the filesystem mount point inside the guest.

Examples:

```text
/
/boot
/var
/data
```

### NRPE returns UNKNOWN

Check:

- VM name and state
- Guest-agent connectivity
- NRPE user permissions
- `virsh` and `jq` availability
- Timeout settings
- NRPE command configuration

## Automated testing

The repository includes:

```text
tests/test_check_kvm_disk.sh
```

The test suite contains **20 mock-based automated tests** covering:

- Version and help output
- Missing and invalid arguments
- Invalid threshold ordering
- Invalid timeout
- OK, WARNING, and CRITICAL states
- Threshold boundaries
- Performance-data formatting
- Zero available space
- Missing or stopped virtual machine
- QEMU Guest Agent failure
- Guest command failure
- Invalid Base64 data
- Missing filesystem mount point
- Timeout handling

Run from the repository root:

```bash
bash tests/test_check_kvm_disk.sh
```

Expected result:

```text
Tests: 20 passed, 0 failed
```

The tests use mocked `virsh` responses and do not require a running virtual machine.

They do not create, stop, or modify real virtual machines.

## Continuous integration

GitHub Actions validates:

- Plugin Bash syntax
- Test script Bash syntax
- CLI version and help output
- All 20 automated tests

The tests run within the repository's existing Python 3.9, 3.11, and 3.13 CI matrix jobs.

## Validation

Version 1.0.1 has been validated through:

- Local execution on a KVM host
- QEMU Guest Agent filesystem queries
- Nagios-to-NRPE remote execution
- Successful Nagios OK status and exit code 0
- Nagios performance-data threshold formatting
- 20 successful mock-based regression tests

The validation did not require modifying the monitored virtual machine.

## Security

The plugin uses QEMU Guest Agent `guest-exec` to run a filesystem query inside the guest.

Although the plugin is designed for read-only monitoring, guest command execution is a security-sensitive capability.

Restrict libvirt and QEMU Guest Agent access to trusted monitoring accounts.

Avoid exposing unrestricted guest command execution to untrusted users.

## Known limitations

- Requires a running KVM virtual machine.
- Requires a functional QEMU Guest Agent.
- Requires support for `guest-exec` and `guest-exec-status`.
- Requires `/bin/df` inside the guest.
- Checks one filesystem mount point per invocation.
- Does not currently monitor inode usage.
- Does not measure filesystem I/O latency or throughput.
- Monitors guest filesystem space, not host-side virtual disk image allocation.

## License

MIT
