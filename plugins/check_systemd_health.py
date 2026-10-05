#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# check_systemd_health.py - Nagios/Icinga plugin for monitoring systemd health
#
# Copyright (c) 2026 Csaba Csanaki
#
# Licensed under the MIT License.
#
# Version: 1.0.2

import argparse
import fnmatch
import re
import subprocess
import sys


VERSION = "1.0.2"

OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

STATUS_TEXT = {
    OK: "OK",
    WARNING: "WARNING",
    CRITICAL: "CRITICAL",
    UNKNOWN: "UNKNOWN",
}

DEFAULT_TIMEOUT = 30
DEFAULT_RESTART_WARNING = 3
DEFAULT_RESTART_CRITICAL = 5
DEFAULT_SINCE = "30m"


class NagiosArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that reports command-line errors as Nagios UNKNOWN."""

    def error(self, message):
        print(f"SYSTEMD UNKNOWN: {message}")
        raise SystemExit(UNKNOWN)


class PluginError(Exception):
    """Exception for errors that should result in UNKNOWN."""


def run_command(command, timeout, acceptable_returncodes=(0,)):
    """Run a command and return stdout."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise PluginError(
            f"command timed out after {timeout}s: {' '.join(command)}"
        )
    except OSError as exc:
        raise PluginError(
            f"unable to execute {command[0]}: {exc}"
        )

    if result.returncode not in acceptable_returncodes:
        error = result.stderr.strip() or result.stdout.strip()

        if not error:
            error = f"command exited with status {result.returncode}"

        raise PluginError(
            f"{command[0]} failed: {error}"
        )

    return result.stdout.strip()


def get_system_state(timeout):
    """Return the overall systemd system state."""
    try:
        result = subprocess.run(
            ["systemctl", "is-system-running"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise PluginError(
            f"systemctl is-system-running timed out after {timeout}s"
        )
    except OSError as exc:
        raise PluginError(
            f"unable to execute systemctl: {exc}"
        )

    state = result.stdout.strip()

    if not state:
        error = result.stderr.strip()

        if error:
            raise PluginError(
                f"unable to determine system state: {error}"
            )

        raise PluginError(
            "unable to determine system state"
        )

    return state


def get_units(timeout, states, unit_type=None):
    """Return systemd units matching requested states and optional type."""
    command = [
        "systemctl",
        "list-units",
        "--all",
        "--no-legend",
        "--no-pager",
        "--plain",
    ]

    if states:
        command.append(
            f"--state={','.join(states)}"
        )

    if unit_type:
        command.append(
            f"--type={unit_type}"
        )

    output = run_command(
        command,
        timeout,
        acceptable_returncodes=(0,),
    )

    units = []

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        fields = line.split()

        if fields:
            units.append(fields[0])

    return units


def matches_any(unit, patterns):
    """Return True if unit matches any shell-style pattern."""
    return any(
        fnmatch.fnmatch(unit, pattern)
        for pattern in patterns
    )


def filter_units(units, includes, excludes):
    """Apply include and exclude filters."""
    included = []
    excluded = []

    for unit in units:
        if includes and not matches_any(unit, includes):
            continue

        if excludes and matches_any(unit, excludes):
            excluded.append(unit)
            continue

        included.append(unit)

    return included, excluded


def parse_since(value):
    """Convert 30m, 2h, 1d etc. to seconds."""
    match = re.fullmatch(
        r"([1-9][0-9]*)([smhd])",
        value.lower(),
    )

    if not match:
        raise argparse.ArgumentTypeError(
            "must use the format Ns, Nm, Nh or Nd "
            "(examples: 30m, 2h, 1d)"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    return amount * multipliers[unit]


def format_since(seconds):
    """Convert seconds to a journalctl --since expression."""
    return f"{seconds} seconds ago"


def extract_restart_unit(message):
    """Extract service name from a systemd restart journal message."""
    match = re.search(
        r"(?P<unit>[A-Za-z0-9_.@:\\x2d-]+\.service): "
        r"Scheduled restart job(?:,|\.|$)",
        message,
    )

    if not match:
        return None

    return match.group("unit")


def get_restart_counts(
    since_seconds,
    timeout,
    includes=None,
    excludes=None,
):
    """Return automatic restart counts from the system journal."""
    includes = includes or []
    excludes = excludes or []

    command = [
        "journalctl",
        "--no-pager",
        "--quiet",
        "--since",
        format_since(since_seconds),
        "-o",
        "cat",
        "_PID=1",
    ]

    output = run_command(
        command,
        timeout,
        acceptable_returncodes=(0,),
    )

    restart_counts = {}

    for line in output.splitlines():
        if "Scheduled restart job" not in line:
            continue

        unit = extract_restart_unit(line)

        if not unit:
            continue

        if includes and not matches_any(
            unit,
            includes,
        ):
            continue

        if excludes and matches_any(
            unit,
            excludes,
        ):
            continue

        restart_counts[unit] = (
            restart_counts.get(unit, 0) + 1
        )

    return restart_counts


def determine_problem_status(count, warning, critical):
    """Determine Nagios status from a problem count."""
    if count == 0:
        return OK

    if warning is None and critical is None:
        return CRITICAL

    if critical is not None and count >= critical:
        return CRITICAL

    if warning is not None and count >= warning:
        return WARNING

    return OK


def determine_restart_status(
    restart_counts,
    warning,
    critical,
):
    """Determine highest Nagios status produced by restart counts."""
    status = OK

    for count in restart_counts.values():
        if count >= critical:
            return CRITICAL

        if count >= warning:
            status = WARNING

    return status


def highest_status(*statuses):
    """Return the most severe Nagios status."""
    if CRITICAL in statuses:
        return CRITICAL

    if WARNING in statuses:
        return WARNING

    if UNKNOWN in statuses:
        return UNKNOWN

    return OK


def build_restart_summary(
    restart_counts,
    warning,
):
    """Build human-readable restart problem information."""
    problems = []

    for unit, count in sorted(
        restart_counts.items()
    ):
        if count >= warning:
            problems.append(
                f"{unit} restarted {count} times"
            )

    return problems


def parse_arguments():
    parser = NagiosArgumentParser(
        description=(
            "Nagios/Icinga plugin for monitoring systemd health."
        )
    )

    filtering = parser.add_argument_group(
        "unit filtering"
    )

    filtering.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Exclude units matching PATTERN. "
            "Shell-style wildcards are supported. "
            "May be specified multiple times."
        ),
    )

    filtering.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Only include units matching PATTERN. "
            "Shell-style wildcards are supported. "
            "May be specified multiple times."
        ),
    )

    filtering.add_argument(
        "--type",
        dest="unit_type",
        metavar="TYPE",
        help=(
            "Only check a specific unit type "
            "(e.g. service, timer, mount, socket)."
        ),
    )

    filtering.add_argument(
        "--state",
        action="append",
        dest="states",
        metavar="STATE",
        help=(
            "Systemd unit state to check. "
            "May be specified multiple times. "
            "Default: failed."
        ),
    )

    thresholds = parser.add_argument_group(
        "unit thresholds"
    )

    thresholds.add_argument(
        "--warning",
        type=int,
        metavar="N",
        help=(
            "WARNING when N or more matching units are found."
        ),
    )

    thresholds.add_argument(
        "--critical",
        type=int,
        metavar="N",
        help=(
            "CRITICAL when N or more matching units are found."
        ),
    )

    restarts = parser.add_argument_group(
        "restart monitoring"
    )

    restarts.add_argument(
        "--check-restarts",
        action="store_true",
        help=(
            "Check automatic service restart events using "
            "the systemd journal."
        ),
    )

    restarts.add_argument(
        "--restart-warning",
        type=int,
        metavar="N",
        help=(
            "WARNING when an individual service has restarted "
            "N or more times. "
            f"Default with --check-restarts: "
            f"{DEFAULT_RESTART_WARNING}."
        ),
    )

    restarts.add_argument(
        "--restart-critical",
        type=int,
        metavar="N",
        help=(
            "CRITICAL when an individual service has restarted "
            "N or more times. "
            f"Default with --check-restarts: "
            f"{DEFAULT_RESTART_CRITICAL}."
        ),
    )

    restarts.add_argument(
        "--since",
        type=parse_since,
        metavar="TIME",
        help=(
            "Restart monitoring window. "
            "Supported suffixes: s, m, h, d. "
            "Examples: 30s, 15m, 2h, 1d. "
            f"Default: {DEFAULT_SINCE}."
        ),
    )

    general = parser.add_argument_group(
        "general options"
    )

    general.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=(
            f"Command timeout in seconds "
            f"(default: {DEFAULT_TIMEOUT})."
        ),
    )

    general.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=(
            "Increase verbosity. "
            "Use -vv for debug output."
        ),
    )

    general.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )

    return parser.parse_args()


def validate_arguments(args):
    """Validate command-line arguments and combinations."""
    if args.timeout <= 0:
        raise PluginError(
            "timeout must be greater than zero"
        )

    if args.warning is not None and args.warning < 1:
        raise PluginError(
            "--warning must be greater than zero"
        )

    if args.critical is not None and args.critical < 1:
        raise PluginError(
            "--critical must be greater than zero"
        )

    if (
        args.warning is not None
        and args.critical is not None
        and args.warning >= args.critical
    ):
        raise PluginError(
            "--warning must be lower than --critical"
        )

    restart_options_used = (
        args.restart_warning is not None
        or args.restart_critical is not None
        or args.since is not None
    )

    if (
        restart_options_used
        and not args.check_restarts
    ):
        raise PluginError(
            "--restart-warning, --restart-critical and --since "
            "require --check-restarts"
        )

    if args.check_restarts:
        if args.restart_warning is None:
            args.restart_warning = (
                DEFAULT_RESTART_WARNING
            )

        if args.restart_critical is None:
            args.restart_critical = (
                DEFAULT_RESTART_CRITICAL
            )

        if args.since is None:
            args.since = parse_since(
                DEFAULT_SINCE
            )

        if args.restart_warning < 1:
            raise PluginError(
                "--restart-warning must be greater than zero"
            )

        if args.restart_critical < 1:
            raise PluginError(
                "--restart-critical must be greater than zero"
            )

        if (
            args.restart_warning
            >= args.restart_critical
        ):
            raise PluginError(
                "--restart-warning must be lower than "
                "--restart-critical"
            )


def print_verbose(
    args,
    system_state,
    all_units,
    filtered_units,
    excluded_units,
    restart_counts,
):
    """Print verbose and debug information."""
    if args.verbose < 1:
        return

    print(f"System state: {system_state}")
    print(
        "Checked states: "
        + ", ".join(args.states)
    )

    if args.unit_type:
        print(f"Unit type: {args.unit_type}")

    print(
        "Matching units before filtering: "
        f"{len(all_units)}"
    )

    print(
        "Matching units after filtering: "
        f"{len(filtered_units)}"
    )

    print(
        f"Excluded units: {len(excluded_units)}"
    )

    for unit in filtered_units:
        print(f"  problem: {unit}")

    for unit in excluded_units:
        print(f"  excluded: {unit}")

    if args.check_restarts:
        print(
            f"Restart window: {args.since} seconds"
        )

        if restart_counts:
            for unit, count in sorted(
                restart_counts.items()
            ):
                print(
                    f"  restarts: {unit} = {count}"
                )
        else:
            print("  restarts: none")

    if args.verbose >= 2:
        print("Debug:")

        print(
            f"  include patterns: "
            f"{args.include or 'none'}"
        )

        print(
            f"  exclude patterns: "
            f"{args.exclude or 'none'}"
        )

        print(
            f"  warning threshold: "
            f"{args.warning}"
        )

        print(
            f"  critical threshold: "
            f"{args.critical}"
        )

        print(
            f"  timeout: "
            f"{args.timeout}s"
        )

        if args.check_restarts:
            print(
                "  restart warning threshold: "
                f"{args.restart_warning}"
            )

            print(
                "  restart critical threshold: "
                f"{args.restart_critical}"
            )


def main():
    args = parse_arguments()

    try:
        validate_arguments(args)

        if not args.states:
            args.states = ["failed"]

        system_state = get_system_state(
            args.timeout
        )

        all_units = get_units(
            args.timeout,
            args.states,
            args.unit_type,
        )

        filtered_units, excluded_units = (
            filter_units(
                all_units,
                args.include,
                args.exclude,
            )
        )

        problem_count = len(
            filtered_units
        )

        unit_status = determine_problem_status(
            problem_count,
            args.warning,
            args.critical,
        )

        restart_counts = {}
        restart_status = OK

        if args.check_restarts:
            restart_counts = get_restart_counts(
                args.since,
                args.timeout,
                args.include,
                args.exclude,
            )

            restart_status = (
                determine_restart_status(
                    restart_counts,
                    args.restart_warning,
                    args.restart_critical,
                )
            )

        final_status = highest_status(
            unit_status,
            restart_status,
        )

        print_verbose(
            args,
            system_state,
            all_units,
            filtered_units,
            excluded_units,
            restart_counts,
        )

        messages = []

        if problem_count:
            word = (
                "unit"
                if problem_count == 1
                else "units"
            )

            messages.append(
                f"{problem_count} matching {word} - "
                + ", ".join(filtered_units)
            )

        elif excluded_units:
            messages.append(
                "all matching problem units are excluded"
            )

        else:
            if args.unit_type:
                messages.append(
                    f"0 matching {args.unit_type} "
                    "problem units"
                )
            else:
                messages.append(
                    "0 matching problem units"
                )

        if args.check_restarts:
            restart_problems = (
                build_restart_summary(
                    restart_counts,
                    args.restart_warning,
                )
            )

            if restart_problems:
                messages.extend(
                    restart_problems
                )
            else:
                messages.append(
                    "no excessive restarts"
                )

        if (
            final_status == OK
            and system_state == "degraded"
            and excluded_units
        ):
            messages.insert(
                0,
                "system degraded",
            )

        elif (
            final_status == OK
            and system_state == "running"
        ):
            messages.insert(
                0,
                "system running",
            )

        elif (
            final_status == OK
            and system_state
            not in ("running", "degraded")
        ):
            final_status = WARNING

            messages.insert(
                0,
                f"system state {system_state}",
            )

        elif final_status != OK:
            messages.insert(
                0,
                f"system state {system_state}",
            )

        perfdata = [
            f"problems={problem_count}",
            f"excluded={len(excluded_units)}",
        ]

        if args.check_restarts:
            total_restarts = sum(
                restart_counts.values()
            )

            perfdata.append(
                f"restarts={total_restarts}"
            )

        print(
            f"SYSTEMD "
            f"{STATUS_TEXT[final_status]}: "
            + "; ".join(messages)
            + " | "
            + " ".join(perfdata)
        )

        return final_status

    except PluginError as exc:
        print(
            f"SYSTEMD UNKNOWN: {exc}"
        )
        return UNKNOWN

    except KeyboardInterrupt:
        print(
            "SYSTEMD UNKNOWN: interrupted"
        )
        return UNKNOWN


if __name__ == "__main__":
    sys.exit(main())
