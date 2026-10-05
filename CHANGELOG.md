# Changelog

All notable changes to this repository will be documented here.

## check_systemd_health.py 1.0.2 - 2026-10-05

Initial public release of `check_systemd_health.py`.

- Added systemd unit health monitoring for Nagios and Icinga.
- Added failed systemd unit detection with CRITICAL status by default.
- Added support for monitoring arbitrary systemd unit states through `--state`.
- Added support for filtering by systemd unit type through `--type`.
- Added `--include` filtering for individual units and shell-style wildcard patterns.
- Added `--exclude` filtering for individual units and shell-style wildcard patterns.
- Added exclude-over-include precedence.
- Added support for explicitly excluding known failed units from the monitoring result.
- Added configurable unit WARNING and CRITICAL thresholds through `--warning` and `--critical`.
- Added validation requiring the WARNING threshold to be lower than the CRITICAL threshold.
- Added automatic service restart monitoring through `--check-restarts`.
- Added systemd journal-based restart detection using `Scheduled restart job` events.
- Added restart detection for services that are no longer loaded when the check runs.
- Added configurable restart monitoring windows through `--since`.
- Added support for second, minute, hour, and day duration suffixes.
- Added a 30-minute default restart monitoring window.
- Added configurable per-service restart WARNING and CRITICAL thresholds.
- Added default restart thresholds of 3 for WARNING and 5 for CRITICAL.
- Added validation requiring the restart WARNING threshold to be lower than the restart CRITICAL threshold.
- Added include and exclude filtering to restart monitoring.
- Added worst-severity preservation between unit health and restart monitoring results.
- Optimized restart monitoring to use a single systemd journal query instead of one query per service.
- Added restart event detection independent of the currently loaded systemd service list.
- Added Nagios-compatible `problems`, `excluded`, and `restarts` performance data.
- Added standard Nagios OK, WARNING, CRITICAL, and UNKNOWN exit states.
- Added Nagios UNKNOWN handling for invalid command-line arguments.
- Added Nagios UNKNOWN handling for invalid option combinations.
- Added Nagios UNKNOWN handling for command execution failures and timeouts.
- Added configurable command timeout with a 30-second default.
- Added `-v` verbose output.
- Added `-vv` debug output.
- Added `--version` and `--help` command-line options.
- Added NRPE integration documentation.
- Documented systemd journal access requirements for restart monitoring.
- Added 46 automated unit and integration tests.
- Added duration parsing tests.
- Added exact and wildcard include/exclude filtering tests.
- Added include/exclude precedence tests.
- Added unit problem threshold tests.
- Added restart journal parsing and service extraction tests.
- Added restart include/exclude filtering tests.
- Added restart WARNING and CRITICAL threshold tests.
- Added argument validation and default-value tests.
- Added complete OK, WARNING, CRITICAL, excluded-failure, restart, and UNKNOWN main-path tests.
- Added Python syntax and CLI validation to GitHub Actions.
- Added automated test execution to the repository `Plugin tests` workflow.
- Added CI validation with Python 3.9, 3.11, and 3.13.
- Added dedicated `check_systemd_health.py` documentation.
- Added installation, NRPE, restart monitoring, troubleshooting, and testing documentation.
- Validated on Rocky Linux 9 with systemd.
- Validated failed-service detection against a real intentionally failed systemd service.
- Validated exact and wildcard include/exclude filtering against real systemd state.
- Validated WARNING and CRITICAL unit thresholds against real systemd state.
- Validated restart-loop detection against a real automatically restarting systemd service.
- Validated restart detection for a service that was no longer loaded.
- Validated journal restart counts against direct `journalctl` results.
- Reduced the measured restart-check runtime from approximately 1.8 seconds to approximately 0.06 seconds by replacing per-service journal queries with a single journal query.

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
