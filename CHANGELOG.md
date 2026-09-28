# Changelog

All notable changes to this repository will be documented here.

## check_hpe_hardware.py 1.0.0 - 2026-09-28

- Added HPE server hardware monitoring through HPE iLOrest.
- Tested with HPE ProLiant DL380 Gen10, iLO 5, and iLOrest 7.3.0.0-7.
- Added model, serial number, ROM/BIOS, and iLO firmware reporting.
- Added OK, WARNING, CRITICAL, and UNKNOWN Nagios states.
- Added worst-severity preservation across multiple health and status values.
- Added iLOrest login, timeout, return-code, and CHIF error handling.
- Added IML details for WARNING and CRITICAL hardware states.
- Added ANSI escape sequence handling for IML output.
- Added local BIOS fallback through sysfs and `dmidecode`.
- Added configurable iLOrest command timeout and executable path.
- Added `--version`, `--help`, and verbose diagnostic options.
- Added tested NRPE integration with a narrowly scoped sudoers rule.
- Added 15 hardware-independent automated unit tests.

## check_librenms_validate 1.0.3 - 2026-09-25

- Added `check_librenms_validate` for monitoring LibreNMS `validate.php`.
- Maps LibreNMS `WARN` results to Nagios WARNING.
- Maps LibreNMS `FAIL` results to Nagios CRITICAL.
- Added ANSI colour escape sequence handling.
- Added OK, WARNING, CRITICAL, and UNKNOWN Nagios states.
- Added configurable 120-second validation timeout.
- Added non-interactive execution of `validate.php` as the `librenms` user.
- Added `failures` and `warnings` performance data.
- Added tested NRPE integration with a narrowly scoped sudoers rule.
- Added automated mock-based tests.

## check_dnf.py 1.2.0 - 2026-09-24

- Prepared `check_dnf.py` for standalone publication.
- Added MIT licensing metadata.
- Removed legacy package-manager references.
- Retained native DNF package and security-update checks.
- Reboot-required detection is enabled by default.
- Reboot-required state is CRITICAL by default.
- Added security-kernel versus running-kernel reporting.
- Default command timeout is 120 seconds.
- Timeout failures return UNKNOWN.
- Added Nagios-compatible performance data.

## check_dnf.py 1.1.1 - 2026-09-24

- Improved kernel version display by omitting architecture suffixes.

## check_dnf.py 1.1.0 - 2026-09-24

- Added reboot-required detection and kernel status reporting.
- Increased default timeout to 120 seconds.

## check_dnf.py 1.0.0 - 2026-09-24

- Initial DNF-focused implementation.
