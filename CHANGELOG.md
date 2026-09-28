# Changelog

All notable changes to this repository will be documented here.

## check_hpe_raid.py 1.0.0 - 2026-09-28

Initial public release of `check_hpe_raid.py`.

- Added HPE Smart Array RAID health monitoring through HPE Smart Storage Administrator CLI (`ssacli`).
- Added automatic HPE Smart Array controller discovery.
- Added support for multiple Smart Array controllers.
- Added controller health monitoring.
- Added array discovery and health monitoring.
- Added logical drive discovery and health monitoring.
- Added OK state for healthy logical drives.
- Added support for `Disabled` logical drive state as OK.
- Added WARNING state for `Rebuild`, `Rebuilding`, `Recover`, and `Recovering` logical drive states.
- Added CRITICAL state for failed or otherwise unhealthy logical drives.
- Added CRITICAL state for non-OK Smart Array controllers.
- Added CRITICAL state for non-OK arrays.
- Added UNKNOWN state when controller status is unavailable.
- Added UNKNOWN state when no HPE Smart Array controller is found.
- Added UNKNOWN state when no arrays are found for a discovered controller.
- Added UNKNOWN handling for missing or non-executable `ssacli`.
- Added UNKNOWN handling for `ssacli` command failures and timeouts.
- Added worst-severity preservation across controllers, arrays, and logical drives.
- Added automatic `ssacli` executable discovery through PATH and common installation locations.
- Added explicit custom `ssacli` executable support through `--ssacli`.
- Added configurable `ssacli` command timeout with a 30-second default.
- Added `--version` and `--help` command-line options.
- Added Nagios-compatible `controllers`, `arrays`, `logical_drives`, and `problems` performance data.
- Added NRPE support with a narrowly scoped sudoers rule.
- Added 33 hardware-independent automated unit tests.
- Added controller, array, logical drive, command failure, timeout, multiple-controller, and worst-severity regression tests.
- Added Python syntax, CLI, and unit-test validation to GitHub Actions.
- Added CI validation with Python 3.9, 3.11, and 3.13.
- Added dedicated `check_hpe_raid.py` documentation.
- Documented HPE Smart Storage Administrator CLI (`ssacli`) as a mandatory runtime dependency.
- Validated on real HPE Smart Array P408i-a SR Gen10 hardware.
- Validated a configuration containing two arrays and two logical drives.
- Validated through the NRPE, sudo, plugin, and `ssacli` execution path.
- Validated through end-to-end Nagios monitoring.

## check_ssacli_disks.sh 1.0.0 - 2026-09-28

Initial public release of `check_ssacli_disks.sh`.

- Added HPE Smart Array physical drive monitoring through HPE Smart Storage Administrator CLI (`ssacli`).
- Added automatic discovery of HPE Smart Array controllers.
- Added support for multiple Smart Array controllers.
- Added monitoring of all discovered physical drives.
- Added CRITICAL state when one or more physical drives do not report `Status: OK`.
- Added UNKNOWN state when `ssacli` is missing or not executable.
- Added UNKNOWN state for controller discovery failures.
- Added UNKNOWN state when no Smart Array controller is found.
- Added UNKNOWN state for physical drive query failures.
- Added UNKNOWN state when no physical drives are found.
- Added detection of physical drives with missing status information.
- Added controller slot and physical drive identifiers to problem output.
- Added Nagios-compatible `drives` and `problems` performance data.
- Added configurable `ssacli` executable path through the `SSACLI_BIN` environment variable.
- Added `--version` and `--help` command-line options.
- Added NRPE support with a narrowly scoped sudoers rule.
- Added 13 hardware-independent mock-based tests.
- Added shell syntax and CLI validation to GitHub Actions.
- Validated on real HPE Smart Array hardware with eight physical drives.
- Validated through NRPE and end-to-end Nagios monitoring.

## check_hpe_hardware.py 1.0.4 - 2026-09-28

- Added support for HPE ProLiant DL380 Gen11 and iLO 6.
- Added tested support for Debian 12 (Bookworm).
- Added automatic iLOrest executable discovery.
- Added support for `/opt/ilorest/bin/ilorest` installations.
- Retained support for `/usr/sbin/ilorest`, `/usr/bin/ilorest`, `/usr/local/bin/ilorest`, and PATH-based discovery.
- Added explicit custom iLOrest path support through `--ilorest`.
- Fixed server model parsing so processor `Model:` fields cannot overwrite the HPE server model.
- Fixed ROM parsing so `Redundant System ROM` cannot overwrite the active BIOS/System ROM.
- Added iLO 6 firmware parsing while retaining iLO 5 support.
- Increased the default iLOrest command timeout from 15 to 60 seconds for slower local CHIF operations.
- Added Gen10 and Gen11 parser regression tests.
- Added iLO 5 and iLO 6 parsing tests.
- Added active and redundant ROM regression tests.
- Added iLOrest executable auto-discovery tests.
- Added validation of the 60-second default timeout.
- Validated the plugin on HPE ProLiant DL380 Gen10 with iLO 5.
- Validated the plugin on two HPE ProLiant DL380 Gen11 servers with iLO 6.
- Validated Debian 12 local CHIF access with iLOrest 7.3.0.0.
- Validated Debian 12 NRPE and end-to-end Nagios monitoring.

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
