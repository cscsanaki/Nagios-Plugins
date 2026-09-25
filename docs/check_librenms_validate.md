# check_librenms_validate

`check_librenms_validate` is a Nagios/Icinga plugin that runs LibreNMS
`validate.php` as the `librenms` user and converts validation findings into
standard monitoring states.

Current version: **1.0.3**

## Tested environment

The plugin has been tested with:

- LibreNMS 26.9.1
- PHP 8.4.26
- Python 3.9.25
- MariaDB 10.11.18
- RRDTool 1.7.2
- SNMP 5.9.1
- NRPE 4.x

## Status mapping

| LibreNMS result | Nagios state | Exit code |
|---|---|---:|
| No WARN or FAIL | OK | 0 |
| One or more WARN, no FAIL | WARNING | 1 |
| One or more FAIL | CRITICAL | 2 |
| Execution, timeout, or unrecognized failure | UNKNOWN | 3 |

`FAIL` takes priority over `WARN`.

## Installation

```bash
sudo install -o root -g root -m 0755 \
  plugins/check_librenms_validate \
  /usr/lib64/nagios/plugins/check_librenms_validate
```

The default validator is:

```text
/opt/librenms/validate.php
```

The plugin executes it non-interactively as the `librenms` user:

```bash
sudo -n -u librenms /opt/librenms/validate.php
```

## Usage

```text
check_librenms_validate [OPTIONS]

-t, --timeout SECONDS   Timeout for validate.php (default: 120)
-V, --version           Show plugin version
-h, --help              Show help
```

## Local test

```bash
/usr/lib64/nagios/plugins/check_librenms_validate
echo $?
```

Example from a tested LibreNMS system:

```text
LIBRENMS WARNING: 1 warning - Your install is over 24 hours out of date, last update: Thu, 24 Sep 2026 12:37:05 +0000 | failures=0 warnings=1
```

The corresponding exit code is `1`.

## Performance data

The plugin returns Nagios-compatible performance data:

```text
failures=N warnings=N
```

## ANSI colour handling

LibreNMS can include ANSI colour escape sequences around status labels when
`validate.php` output is captured by a monitoring process. For example, a
visually displayed `[WARN]` may contain colour-control bytes around `WARN`.

The plugin strips ANSI escape sequences before parsing `[WARN]` and `[FAIL]`.

## NRPE integration

The recommended configuration keeps the plugin running as the unprivileged
`nrpe` account. Only the LibreNMS validator itself is permitted through sudo
as the `librenms` user.

### sudoers

Create a narrowly scoped sudoers rule:

```text
nrpe ALL=(librenms) NOPASSWD: /opt/librenms/validate.php
```

For example:

```bash
sudo visudo -f /etc/sudoers.d/check_librenms_validate
```

Then validate the sudoers file:

```bash
sudo visudo -cf /etc/sudoers.d/check_librenms_validate
```

Do not grant unrestricted sudo access to the NRPE account.

### NRPE command

Add the command to the appropriate NRPE configuration file:

```text
command[check_librenms_validate]=/usr/lib64/nagios/plugins/check_librenms_validate
```

The plugin itself does not need to run through `sudo`.

Restart or reload NRPE as appropriate for the installation.

### End-to-end test

From the Nagios server:

```bash
/usr/lib64/nagios/plugins/check_nrpe \
  -H <librenms-host> \
  -c check_librenms_validate
```

A tested remote result:

```text
LIBRENMS WARNING: 1 warning - Your install is over 24 hours out of date, last update: Thu, 24 Sep 2026 12:37:05 +0000 | failures=0 warnings=1
```

This confirms the full path:

```text
Nagios server
    -> check_nrpe
    -> NRPE (nrpe user)
    -> check_librenms_validate
    -> sudo -n -u librenms
    -> /opt/librenms/validate.php
```

## Automated tests

The test suite uses mocked validator output and does not require LibreNMS:

```bash
bash tests/test_check_librenms_validate.sh
```

It covers:

- OK
- WARNING
- CRITICAL
- WARN + FAIL priority
- ANSI-coloured WARN
- ANSI-coloured FAIL
- multiple warnings
- execution failure

## Security

The recommended sudoers rule permits the `nrpe` account to execute only
`/opt/librenms/validate.php` as `librenms`. It does not grant root access to
the plugin or unrestricted sudo access.
