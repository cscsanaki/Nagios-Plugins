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

## NRPE integration

The plugin can be executed through NRPE like any other Nagios plugin.

The following configuration has been tested with:

- Rocky Linux 9.8
- NRPE 4.1.2
- Nagios Plugins 2.5
- Python 3
- DNF
- Plugin directory: `/usr/lib64/nagios/plugins`
- NRPE configuration: `/etc/nagios/nrpe.cfg`
- Additional NRPE configuration directory: `/etc/nrpe.d`

### Install the plugin

Install the plugin as root:

```bash
sudo install -o root -g root -m 0755 \
  check_dnf.py \
  /usr/lib64/nagios/plugins/check_dnf.py
```

Verify the installed version:

```bash
/usr/lib64/nagios/plugins/check_dnf.py --version
```

### Test locally

Always test the plugin locally before adding it to NRPE:

```bash
/usr/lib64/nagios/plugins/check_dnf.py
echo $?
```

Example output:

```text
DNF CRITICAL: 0 security updates, 0 non-security updates, 0 total, reboot required (security kernel 5.14.0-687.49.1.el9_8 installed, running 5.14.0-687.46.1.el9_8) | security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

In this example there are no pending package updates, but a newer security
kernel is already installed and the system is still running an older kernel.
The reboot check therefore returns CRITICAL.

### Test as the NRPE user

Determine which account NRPE is running under:

```bash
ps -ef | grep '[n]rpe'
```

For an NRPE service running as user `nrpe`, test the plugin with the same
account:

```bash
sudo -u nrpe /usr/lib64/nagios/plugins/check_dnf.py
echo $?
```

This test is important because DNF repository access, cache access and
`needs-restarting` may behave differently under the NRPE service account.

### Configure NRPE

Create a dedicated NRPE configuration file:

```bash
sudo vi /etc/nrpe.d/check_dnf.cfg
```

Add:

```text
command[check_dnf]=/usr/lib64/nagios/plugins/check_dnf.py
```

Using a separate configuration file is recommended instead of modifying the
main `/etc/nagios/nrpe.cfg` when the installation includes `/etc/nrpe.d`.

### NRPE timeout

The default timeout of `check_dnf.py` is 120 seconds.

Make sure the NRPE command timeout is longer than the plugin timeout. Check the
current NRPE configuration with:

```bash
grep -E '^[[:space:]]*(command_timeout|connection_timeout)=' /etc/nagios/nrpe.cfg
```

If the NRPE command timeout is shorter than the plugin timeout, adjust it
according to your monitoring environment.

DNF may occasionally need more time when repository metadata must be refreshed.

### Restart NRPE

After adding the command definition:

```bash
sudo systemctl restart nrpe
sudo systemctl status nrpe --no-pager
```

### Test through NRPE locally

If `check_nrpe` is installed, test the complete NRPE path:

```bash
/usr/lib64/nagios/plugins/check_nrpe -H 127.0.0.1 -c check_dnf
```

The returned status and output should match a direct execution of
`check_dnf.py`.

### Nagios server configuration

On the Nagios server, define or use an existing `check_nrpe` command.

Example service definition:

```text
define service {
    use                     generic-service
    host_name               my-linux-server
    service_description     DNF Updates
    check_command           check_nrpe!check_dnf
}
```

The exact host and service configuration depends on the local Nagios
configuration.

### Performance data

The plugin returns Nagios-compatible performance data:

```text
security_updates=0 non_security_updates=0 total_updates=0 reboot_required=1
```

The values can be collected by a compatible performance-data backend.

### Security considerations

The plugin only performs read-only package and reboot-status checks. It does
not install, remove or update packages.

Do not configure unrestricted NRPE command arguments unless they are required
by your monitoring environment.

## Exit codes

| Code | State |
|---:|---|
| 0 | OK |
| 1 | WARNING |
| 2 | CRITICAL |
| 3 | UNKNOWN |
