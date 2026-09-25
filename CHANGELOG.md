# Changelog

All notable changes to this repository will be documented here.

## 1.2.0 - 2026-09-24

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

## 1.1.1 - 2026-09-24

- Improved kernel version display by omitting architecture suffixes.

## 1.1.0 - 2026-09-24

- Added reboot-required detection and kernel status reporting.
- Increased default timeout to 120 seconds.

## 1.0.0 - 2026-09-24

- Initial DNF-focused implementation.
