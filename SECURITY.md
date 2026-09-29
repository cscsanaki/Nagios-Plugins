# Security Policy

## Supported Versions

Nagios-Plugins contains independently versioned monitoring plugins.

Security fixes are generally applied to the latest version of each plugin.
Older plugin versions may not receive security updates.

Users are encouraged to use the latest release available for the plugin they
are using.

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues,
pull requests, or discussions.

If you discover a potential security vulnerability, please report it privately
using GitHub's private vulnerability reporting feature for this repository,
if available.

When reporting a vulnerability, please include:

- The affected plugin and version
- A description of the vulnerability
- Steps to reproduce the issue
- The potential security impact
- Any suggested mitigation or fix, if known

Please do not include passwords, API keys, authentication tokens, SNMP
community strings, or other sensitive credentials in reports.

## Response

Security reports will be reviewed as soon as reasonably possible.

If the issue is confirmed, a fix will be prepared and released as appropriate.
Details of confirmed vulnerabilities may be published after a fix is available
so that users have an opportunity to update.

## Scope

Security issues may include, but are not limited to:

- Command injection
- Unsafe handling of external command output
- Credential or sensitive information exposure
- Insecure temporary file handling
- Privilege escalation
- Unsafe input handling
- Vulnerabilities introduced by plugin dependencies

General bugs, feature requests, and compatibility issues should be reported
through the normal GitHub issue tracker.
