# Contributing to Nagios-Plugins

Thank you for your interest in contributing to Nagios-Plugins.

Contributions are welcome, including bug fixes, new monitoring plugins,
documentation improvements, and tests.

## Reporting Issues

Before opening a new issue:

- Check whether the issue has already been reported.
- Use the latest version of the plugin when possible.
- Include the plugin name and version.
- Include your operating system and version.
- Include the command used to run the plugin.
- Include the complete plugin output and exit code.
- Remove passwords, API credentials, tokens, and other sensitive information.

For plugin failures, verbose or debug output can be especially useful when
available.

## Contributing Code

1. Fork the repository.
2. Create a new branch for your change.
3. Make your changes.
4. Add or update tests when applicable.
5. Run the relevant tests locally.
6. Commit your changes with a clear commit message.
7. Push the branch to your fork.
8. Open a pull request against the `main` branch.

Please keep pull requests focused on a single change whenever possible.

## Plugin Guidelines

New or modified monitoring plugins should:

- Follow the Nagios/Icinga plugin exit code conventions:
  - `0` - OK
  - `1` - WARNING
  - `2` - CRITICAL
  - `3` - UNKNOWN
- Produce a clear, single-line status message suitable for Nagios/Icinga.
- Include performance data where appropriate.
- Provide `--help` or `-h` output.
- Provide a version option where appropriate.
- Avoid embedding credentials or environment-specific configuration.
- Handle errors and timeouts gracefully.
- Remain suitable for non-interactive execution by monitoring systems such
  as Nagios, Icinga, or NRPE.

## Testing

Run the relevant tests before submitting a pull request.

For Python tests, for example:

```bash
python3 -m unittest discover -s tests -v
