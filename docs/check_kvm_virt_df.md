# check_kvm_virt_df.sh

Nagios/Icinga plugin for monitoring filesystem disk usage inside KVM virtual machines using libguestfs `virt-df`.

**Current version:** 1.0.3

## Overview

`check_kvm_virt_df.sh` monitors filesystem usage inside KVM virtual machines from the hypervisor host.

The plugin uses `virt-df` to inspect guest filesystems without requiring QEMU Guest Agent, SSH access, or an additional monitoring agent inside the virtual machine.

It supports running and stopped libvirt guests through domain-based monitoring, as well as offline disk images.

Individual filesystems can be monitored with independent WARNING and CRITICAL thresholds.

## Features

- KVM guest filesystem monitoring through libguestfs `virt-df`.
- Monitoring of running and stopped libvirt virtual machines.
- No QEMU Guest Agent required.
- No SSH access to the guest required.
- Domain-based monitoring with `-d`.
- Offline disk image monitoring with `-i`.
- Individual filesystem selection with `-p`.
- Monitoring of all discovered filesystems when `-p` is omitted.
- Configurable used-space WARNING and CRITICAL thresholds.
- Support for decimal filesystem usage percentages.
- Multiple filesystem monitoring with highest-severity evaluation.
- Nagios-compatible performance data.
- Filesystem capacity reporting in GiB.
- CSV parsing using Python 3.
- Configurable command timeout.
- Verbose diagnostic output.
- Validation of command-line arguments.
- Handling of malformed or empty CSV output.
- Detection of missing filesystems.
- Protection against directly inspecting disk images attached to running libvirt guests in image mode.
- Standard Nagios exit codes.
- NRPE integration.
- 31 automated mock-based Bash regression tests.

## Requirements

The KVM host requires:

- Linux
- Bash
- KVM/QEMU and libvirt
- `virt-df` from the libguestfs toolset
- Python 3
- GNU `timeout` (coreutils)
- `virsh` for direct disk image safety checks
- Appropriate permissions to query libvirt and inspect guest filesystems

The plugin does not require QEMU Guest Agent inside the virtual machine.

### Installing libguestfs

On RHEL-compatible distributions such as Rocky Linux, install the required package:

```bash
sudo dnf install libguestfs-tools-c
```

Verify the installation:

```bash
virt-df --version
```

Check libvirt access:

```bash
virsh list --all
```

The monitoring account must have the necessary permissions to access libvirt and use libguestfs.

## Installation

Copy the plugin to the Nagios plugin directory.

On RHEL-compatible systems:

```bash
sudo cp check_kvm_virt_df.sh /usr/lib64/nagios/plugins/
sudo chmod 755 /usr/lib64/nagios/plugins/check_kvm_virt_df.sh
```

Verify the installed version:

```bash
/usr/lib64/nagios/plugins/check_kvm_virt_df.sh --version
```

Expected output:

```text
check_kvm_virt_df.sh 1.0.3
```

Check Bash syntax:

```bash
bash -n /usr/lib64/nagios/plugins/check_kvm_virt_df.sh
```

## Discovering guest filesystems

Before configuring monitoring, use `virt-df` to identify the filesystems available inside the virtual machine.

### List guest filesystems

```bash
virt-df -d example-vm --csv
```

Example output:

```csv
VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%
example-vm,/dev/sda1,10166108,2387304,7238184,23.5
example-vm,/dev/sda2,88574536,31959456,52089820,36.1
```

The `Filesystem` column identifies the filesystem to monitor using the plugin's `-p` option.

For example:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 80 \
  -c 90
```

To monitor another filesystem with different thresholds:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda2 \
  -w 85 \
  -c 95
```

Each filesystem can be configured as a separate Nagios, Icinga, or Centreon service.

**Important:** The filesystem identifiers reported by `virt-df` do not necessarily correspond directly to mount points such as `/`, `/boot`, or `/var`.

For example, `/dev/sda1` may represent a boot filesystem, but this must be verified against the guest's actual partition and mount configuration.

### Human-readable output

For manual inspection:

```bash
virt-df -d example-vm -h
```

For monitoring and automated processing, use CSV output:

```bash
virt-df -d example-vm --csv
```

## Usage

Basic syntax:

```bash
check_kvm_virt_df.sh \
  (-d DOMAIN | -i IMAGE) \
  [-p FILESYSTEM] \
  [-w WARNING] \
  [-c CRITICAL] \
  [-t SECONDS] \
  [-v]
```

### Command-line options

| Option | Description |
|---|---|
| `-d`, `--domain NAME` | Select a libvirt virtual machine |
| `-i`, `--image PATH` | Select an offline disk image or consistent snapshot |
| `-p`, `--partition FS` | Select an exact filesystem identifier |
| `-w`, `--warning PCT` | Used-space WARNING threshold |
| `-c`, `--critical PCT` | Used-space CRITICAL threshold |
| `-t`, `--timeout SECONDS` | Command timeout |
| `-v`, `--verbose` | Enable diagnostic output |
| `-h`, `--help` | Display help |
| `-V`, `--version` | Display plugin version |

Default values:

| Setting | Default |
|---|---|
| WARNING | 80% |
| CRITICAL | 90% |
| Timeout | 60 seconds |
| Filesystem selection | All discovered filesystems |

Exactly one of `-d` or `-i` must be specified.

The WARNING threshold must be lower than the CRITICAL threshold.

Thresholds must be whole percentages between 0 and 100.

## Domain-based monitoring

Domain-based monitoring is the recommended mode for libvirt-managed virtual machines.

The plugin uses `virt-df -d` to inspect guest filesystems.

This mode supports running and stopped virtual machines.

Example:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 80 \
  -c 90
```

The plugin does not require a QEMU Guest Agent inside the guest.

### Monitoring individual filesystems

The `-p` option allows independent filesystem monitoring.

Example boot filesystem:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 70 \
  -c 85
```

Example root filesystem:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/cl_example/root \
  -w 85 \
  -c 95
```

The filesystem identifiers must match the `Filesystem` column returned by `virt-df --csv`.

### Monitoring all filesystems

Omit `-p` to monitor every discovered filesystem:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -w 80 \
  -c 90
```

The plugin evaluates every usable filesystem record and returns the highest Nagios severity.

**Note:** Monitoring all filesystems may include special or unexpected devices. Use `virt-df --csv` to inspect the discovered filesystems before configuring production monitoring.

For independent thresholds, configure separate checks with `-p`.

## Disk image monitoring

The plugin also supports offline disk images:

```bash
check_kvm_virt_df.sh \
  -i /var/lib/libvirt/images/offline-example.qcow2 \
  -p /dev/sda1 \
  -w 80 \
  -c 90
```

Image mode is intended for offline disk images or consistent snapshots.

The plugin checks whether the specified image is directly attached to a running libvirt guest.

If a direct attachment is detected, the plugin returns UNKNOWN.

Example:

```text
VIRT_DF UNKNOWN: image is attached to running VM 'example-vm'; use -d example-vm instead
```

Use domain mode to monitor running libvirt guests.

The direct-image safety check does not provide a complete guarantee that an image is unused. Backing chains, external QEMU processes, and other storage access must also be considered.

## Threshold evaluation

Thresholds are based on the percentage of **used filesystem space**.

For example:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 80 \
  -c 90
```

| Used disk space | Nagios state |
|---|---|
| Below 80% | OK |
| 80% to below 90% | WARNING |
| 90% or above | CRITICAL |

The threshold boundary is inclusive.

A filesystem at exactly 80% returns WARNING.

A filesystem at exactly 90% returns CRITICAL.

This differs from `check_kvm_disk.sh`, which evaluates free-space thresholds through QEMU Guest Agent.

## Example output

The following examples use illustrative filesystem values.

### OK

```text
VIRT_DF OK: /dev/sda1: 35% used (3.50/10.00 GiB) OK
```

### WARNING

```text
VIRT_DF WARNING: /dev/sda1: 85% used (8.50/10.00 GiB) WARNING
```

### CRITICAL

```text
VIRT_DF CRITICAL: /dev/sda1: 95% used (9.50/10.00 GiB) CRITICAL
```

Actual plugin output also includes Nagios performance data.

## Performance data

The plugin returns two metrics for each monitored filesystem:

- Used capacity in KiB.
- Used capacity as a percentage.

Illustrative example:

```text
'example-vm:/dev/sda1_used_kib'=3670016KB;8388608;9437184;0;10485760 'example-vm:/dev/sda1_used_pct'=35%;80;90;0;100
```

| Metric | Description |
|---|---|
| `<vm>:<filesystem>_used_kib` | Used filesystem capacity in KiB |
| `<vm>:<filesystem>_used_pct` | Used filesystem percentage |

The performance data includes WARNING and CRITICAL thresholds.

For percentage metrics:

```text
;80;90;0;100
```

For KiB metrics, the plugin converts percentage thresholds to KiB using the filesystem's total capacity.

Monitoring systems can use these metrics for graphs and threshold visualization.

## CSV processing

The plugin uses Python 3's CSV module to parse `virt-df --csv` output.

The standard six-column format is:

```csv
VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%
```

The plugin also supports the legacy five-column format without a virtual machine name.

Supported processing includes:

- CSV header detection.
- Quoted CSV fields.
- Decimal usage percentages.
- Numeric field validation.
- Empty output detection.
- Malformed CSV handling.
- Filesystem selection.
- Swap record exclusion.

Invalid or unusable output results in UNKNOWN.

## Timeout handling

The default timeout is 60 seconds.

Example:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 80 \
  -c 90 \
  --timeout 120
```

The plugin uses GNU `timeout` to limit the `virt-df` command execution.

If `virt-df` fails or times out, the plugin returns UNKNOWN.

The timeout applies to the `virt-df` invocation; it is not a strict deadline for every operation performed by the complete plugin.

## Verbose mode

Enable diagnostic output:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 80 \
  -c 90 \
  --verbose
```

Verbose information is written to standard error.

Normal Nagios checks should generally run without verbose mode.

## NRPE integration

The plugin can run on the KVM hypervisor and be queried remotely through NRPE.

Monitoring architecture:

```text
Nagios / Icinga / Centreon
           |
           | NRPE
           v
       KVM host
           |
           | virt-df / libguestfs
           v
    Guest filesystem
```

### NRPE command configuration

Example root filesystem:

```text
command[check_kvm_root]=/usr/lib64/nagios/plugins/check_kvm_virt_df.sh -d example-vm -p /dev/sda2 -w 85 -c 95
```

Example boot filesystem:

```text
command[check_kvm_boot]=/usr/lib64/nagios/plugins/check_kvm_virt_df.sh -d example-vm -p /dev/sda1 -w 70 -c 85
```

The filesystem-to-mount-point mapping must be verified for the actual guest.

### Remote Nagios check

From the monitoring server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H kvm-host.example.com \
  -c check_kvm_root
```

The NRPE account must have permission to use libvirt and libguestfs.

Use narrowly scoped permissions where possible.

## Nagios exit codes

| Exit code | State | Meaning |
|---|---|---|
| 0 | OK | Used filesystem space is below WARNING |
| 1 | WARNING | Used space reaches WARNING |
| 2 | CRITICAL | Used space reaches CRITICAL |
| 3 | UNKNOWN | Invalid arguments, missing filesystem, command failure, invalid output, or timeout |

## Troubleshooting

### virt-df command not found

Install the required package:

```bash
sudo dnf install libguestfs-tools-c
```

Verify:

```bash
virt-df --version
```

### Virtual machine not found

List libvirt domains:

```bash
virsh list --all
```

Verify the name supplied with `-d`.

### Filesystem not found

Run:

```bash
virt-df -d example-vm --csv
```

Use the exact value from the `Filesystem` column with `-p`.

### Image attached to running VM

Use domain mode:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  -w 80 \
  -c 90
```

Do not bypass QEMU image locks to force direct inspection of an active disk image.

### virt-df timeout

Increase the timeout if the guest contains large or complex filesystems:

```bash
check_kvm_virt_df.sh \
  -d example-vm \
  -p /dev/sda1 \
  --timeout 120
```

Also check libguestfs permissions and system resources.

### NRPE returns UNKNOWN

Check:

- Libvirt access permissions.
- `virt-df` installation.
- Python 3 availability.
- Filesystem identifier.
- Domain name.
- Command timeout.
- NRPE execution account permissions.

## Automated testing

The repository includes:

```text
tests/test_check_kvm_virt_df.sh
```

The test suite contains **31 automated mock-based regression tests**.

Coverage includes:

- Version and help output.
- Missing and conflicting selectors.
- Unknown arguments and missing values.
- Invalid thresholds and timeout.
- Domain-based monitoring.
- Decimal usage percentages.
- Filesystem selection.
- Nagios performance data.
- OK, WARNING, and CRITICAL states.
- Multiple filesystem handling.
- Missing filesystem detection.
- Offline image monitoring.
- Active image rejection.
- Missing image handling.
- `virt-df` command failures.
- Empty or header-only CSV output.
- Invalid numeric data.
- Malformed CSV.
- Negative filesystem usage.
- Swap exclusion.
- Legacy CSV support.
- Libvirt failures.
- Disk discovery failures.
- Timeout handling.

Run from the repository root:

```bash
bash tests/test_check_kvm_virt_df.sh
```

Expected result:

```text
Tests: 31 passed, 0 failed
```

The tests use mocked commands and do not require a running virtual machine.

They do not modify guest disk images.

## Continuous integration

The GitHub Actions `Plugin tests` workflow validates:

- Bash syntax of the plugin.
- Bash syntax of the test script.
- Plugin version output.
- Plugin help output.
- All 31 automated regression tests.

The Bash tests run in the repository's existing Python 3.9, 3.11, and 3.13 CI matrix jobs.

## Validation

Version 1.0.3 has been validated through:

- Live domain-based filesystem queries.
- Filesystem selection using `-p`.
- OK, WARNING, and CRITICAL threshold evaluation.
- Correct Nagios exit codes.
- Nagios performance-data generation.
- Offline disk image inspection.
- Running guest direct-image rejection.
- Bash syntax validation.
- 31 successful automated regression tests.

The plugin does not require QEMU Guest Agent.

## Security and consistency

Domain-based monitoring uses libguestfs `virt-df` to inspect guest filesystem metadata.

The plugin does not intentionally modify guest filesystems.

However, filesystem information obtained from running guests may not be fully consistent because the guest operating system can modify its disks during inspection.

The plugin should not be treated as a substitute for application-consistent snapshots, backups, or guest-side filesystem monitoring.

Avoid bypassing QEMU disk image locks.

Restrict libvirt and libguestfs access to trusted monitoring accounts.

## Known limitations

- Requires libguestfs and a supported guest filesystem.
- Domain-based monitoring requires access to libvirt.
- Running guest filesystem data may be inconsistent.
- Exact filesystem names must be discovered using `virt-df --csv`.
- Filesystem identifiers do not necessarily correspond to mount points.
- Direct image mode is intended for offline images or consistent snapshots.
- The active-image check does not detect every possible external disk user or backing-chain dependency.
- Does not monitor filesystem I/O latency or throughput.
- Does not monitor inode usage.
- Does not report host-side QCOW2 allocation as guest filesystem usage.
- The timeout does not cover every stage of plugin execution.

## License

MIT

See [LICENSE](../LICENSE) for details.
