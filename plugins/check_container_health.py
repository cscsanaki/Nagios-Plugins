#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# check_container_health.py
#
# Nagios/Icinga plugin for monitoring Docker container health,
# restart counts, CPU usage, and memory usage.
#
# Copyright (c) 2026 Csaba Csanaki
#
# Licensed under the MIT License.
#
# Version: 1.0.1

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys


VERSION = "1.0.1"

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
DEFAULT_MAX_DETAILS = 5


class PluginError(Exception):
    """Errors that should result in Nagios UNKNOWN."""


class NagiosArgumentParser(argparse.ArgumentParser):
    """Argument parser that returns Nagios UNKNOWN for invalid arguments."""

    def error(self, message):
        print(f"CONTAINERS UNKNOWN: {message}")
        raise SystemExit(UNKNOWN)


def run_command(command, timeout, acceptable_returncodes=(0,)):
    """Execute a command and return stdout."""
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


def find_docker():
    """Return Docker executable path."""
    return shutil.which("docker")


def detect_runtime(requested):
    """Detect and validate the requested container runtime."""
    if requested == "podman":
        raise PluginError(
            "Podman support is not available in version 1.0.1"
        )

    docker = find_docker()

    if requested == "docker":
        if not docker:
            raise PluginError(
                "Docker executable not found"
            )

        return "docker", docker

    if docker:
        return "docker", docker

    raise PluginError(
        "no supported container runtime found; "
        "Docker is required by version 1.0.1"
    )


def validate_runtime(runtime_bin, timeout):
    """Verify that the Docker daemon is reachable."""
    run_command(
        [
            runtime_bin,
            "info",
            "--format",
            "{{.ServerVersion}}",
        ],
        timeout,
    )


def get_container_ids(runtime_bin, timeout):
    """Return IDs for all Docker containers."""
    output = run_command(
        [
            runtime_bin,
            "ps",
            "-aq",
            "--no-trunc",
        ],
        timeout,
    )

    return [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]


def safe_int(value, default=0):
    """Convert a value to int safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_inspect_json(output):
    """Parse docker inspect JSON into normalized container dictionaries."""
    try:
        raw = json.loads(output)
    except json.JSONDecodeError as exc:
        raise PluginError(
            f"unable to parse Docker inspect JSON: {exc}"
        )

    if not isinstance(raw, list):
        raise PluginError(
            "unexpected Docker inspect response"
        )

    containers = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        state = item.get("State") or {}
        host = item.get("HostConfig") or {}
        config = item.get("Config") or {}

        health_data = state.get("Health")

        if isinstance(health_data, dict):
            health = health_data.get(
                "Status",
                "unknown",
            )
        else:
            health = "none"

        restart_policy_data = (
            host.get("RestartPolicy") or {}
        )

        container_id = str(
            item.get("Id") or ""
        )

        name = str(
            item.get("Name") or ""
        ).lstrip("/")

        containers.append(
            {
                "id": container_id,
                "short_id": container_id[:12],
                "name": name,
                "image": str(
                    config.get("Image") or ""
                ),
                "state": str(
                    state.get("Status") or "unknown"
                ).lower(),
                "running": bool(
                    state.get("Running", False)
                ),
                "paused": bool(
                    state.get("Paused", False)
                ),
                "restarting": bool(
                    state.get("Restarting", False)
                ),
                "oom_killed": bool(
                    state.get("OOMKilled", False)
                ),
                "dead": bool(
                    state.get("Dead", False)
                ),
                "exit_code": safe_int(
                    state.get("ExitCode"),
                    0,
                ),
                "health": str(
                    health
                ).lower(),
                "restart_count": safe_int(
                    item.get("RestartCount"),
                    0,
                ),
                "restart_policy": str(
                    restart_policy_data.get(
                        "Name"
                    ) or "no"
                ),
                "memory_limit_bytes": safe_int(
                    host.get("Memory"),
                    0,
                ),
                "cpu_percent": None,
                "memory_percent": None,
                "memory_used_bytes": None,
                "memory_stats_limit_bytes": None,
                "memory_usage_text": None,
                "pids": None,
            }
        )

    return containers


def get_containers(runtime_bin, timeout):
    """Retrieve all Docker containers using one inspect call."""
    ids = get_container_ids(
        runtime_bin,
        timeout,
    )

    if not ids:
        return []

    output = run_command(
        [
            runtime_bin,
            "inspect",
            *ids,
        ],
        timeout,
    )

    return parse_inspect_json(output)


def parse_percent(value):
    """Parse Docker percentage strings such as 12.34%."""
    if value is None:
        return None

    text = str(value).strip()

    if text.endswith("%"):
        text = text[:-1]

    try:
        return float(text)
    except ValueError:
        return None


SIZE_UNITS = {
    "b": 1,
    "kb": 1000,
    "kib": 1024,
    "mb": 1000 ** 2,
    "mib": 1024 ** 2,
    "gb": 1000 ** 3,
    "gib": 1024 ** 3,
    "tb": 1000 ** 4,
    "tib": 1024 ** 4,
}


def parse_size(value):
    """Convert Docker human-readable byte values to bytes."""
    if value is None:
        return None

    text = str(value).strip()

    match = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)",
        text,
    )

    if not match:
        return None

    number = float(
        match.group(1)
    )

    unit = match.group(2).lower()

    multiplier = SIZE_UNITS.get(unit)

    if multiplier is None:
        return None

    return int(
        number * multiplier
    )


def parse_memory_usage(value):
    """Parse values such as '170.4MiB / 7.5GiB'."""
    if not value:
        return None, None

    parts = value.split("/", 1)

    if len(parts) != 2:
        return None, None

    used = parse_size(
        parts[0].strip()
    )

    limit = parse_size(
        parts[1].strip()
    )

    return used, limit


def parse_stats_output(output):
    """Parse machine-oriented docker stats output."""
    stats = {}

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        fields = line.split("|")

        if len(fields) != 6:
            continue

        (
            container_id,
            name,
            cpu_text,
            memory_text,
            memory_percent_text,
            pids_text,
        ) = fields

        used, limit = parse_memory_usage(
            memory_text
        )

        stats[name] = {
            "id": container_id,
            "cpu_percent": parse_percent(
                cpu_text
            ),
            "memory_percent": parse_percent(
                memory_percent_text
            ),
            "memory_used_bytes": used,
            "memory_limit_bytes": limit,
            "memory_usage_text": (
                memory_text.strip()
            ),
            "pids": safe_int(
                pids_text,
                0,
            ),
        }

    return stats


def get_resource_stats(runtime_bin, timeout):
    """Retrieve Docker resource usage with one stats call."""
    output = run_command(
        [
            runtime_bin,
            "stats",
            "--no-stream",
            "--format",
            (
                "{{.ID}}|{{.Name}}|{{.CPUPerc}}|"
                "{{.MemUsage}}|{{.MemPerc}}|{{.PIDs}}"
            ),
        ],
        timeout,
    )

    return parse_stats_output(
        output
    )


def merge_stats(containers, stats):
    """Merge resource stats into container dictionaries."""
    for container in containers:
        item = stats.get(
            container["name"]
        )

        if not item:
            continue

        container["cpu_percent"] = (
            item["cpu_percent"]
        )

        container["memory_percent"] = (
            item["memory_percent"]
        )

        container["memory_used_bytes"] = (
            item["memory_used_bytes"]
        )

        container["memory_stats_limit_bytes"] = (
            item["memory_limit_bytes"]
        )

        container["memory_usage_text"] = (
            item["memory_usage_text"]
        )

        container["pids"] = (
            item["pids"]
        )


def matches_any(value, patterns):
    """Return True if value matches any shell-style pattern."""
    return any(
        fnmatch.fnmatch(
            value,
            pattern,
        )
        for pattern in patterns
    )


def find_single_container(containers, selector):
    """
    Find exactly one container by exact name, full ID,
    or unique ID prefix.
    """
    exact_name = [
        item
        for item in containers
        if item["name"] == selector
    ]

    if len(exact_name) == 1:
        return exact_name[0]

    exact_id = [
        item
        for item in containers
        if item["id"] == selector
    ]

    if len(exact_id) == 1:
        return exact_id[0]

    prefix_matches = [
        item
        for item in containers
        if item["id"].startswith(
            selector
        )
    ]

    if len(prefix_matches) == 1:
        return prefix_matches[0]

    if len(prefix_matches) > 1:
        raise PluginError(
            f"container selector '{selector}' "
            "matches multiple container IDs"
        )

    return None


def select_containers(
    containers,
    selector=None,
    includes=None,
    excludes=None,
):
    """Select containers according to CLI filtering rules."""
    includes = includes or []
    excludes = excludes or []

    if selector:
        item = find_single_container(
            containers,
            selector,
        )

        if item is None:
            return [], [], True

        return [item], [], False

    selected = []
    excluded = []

    for item in containers:
        name = item["name"]

        if (
            includes
            and not matches_any(
                name,
                includes,
            )
        ):
            continue

        if (
            excludes
            and matches_any(
                name,
                excludes,
            )
        ):
            excluded.append(
                item
            )
            continue

        selected.append(
            item
        )

    return selected, excluded, False


def get_missing_expected(containers, expected):
    """Return expected container names that do not exist."""
    names = {
        item["name"]
        for item in containers
    }

    return [
        name
        for name in expected
        if name not in names
    ]


def state_status(container, check_health=True):
    """Return status and state problem descriptions for one container."""
    problems = []

    state = container["state"]

    if container["oom_killed"]:
        problems.append(
            (
                CRITICAL,
                f"{container['name']}: OOM-killed",
            )
        )

    if container["dead"] or state == "dead":
        problems.append(
            (
                CRITICAL,
                f"{container['name']}: dead",
            )
        )

    elif state == "exited":
        problems.append(
            (
                CRITICAL,
                (
                    f"{container['name']}: exited "
                    f"({container['exit_code']})"
                ),
            )
        )

    elif (
        container["restarting"]
        or state == "restarting"
    ):
        problems.append(
            (
                WARNING,
                f"{container['name']}: restarting",
            )
        )

    elif (
        container["paused"]
        or state == "paused"
    ):
        problems.append(
            (
                WARNING,
                f"{container['name']}: paused",
            )
        )

    elif state == "created":
        problems.append(
            (
                WARNING,
                f"{container['name']}: created but not running",
            )
        )

    elif state != "running":
        problems.append(
            (
                CRITICAL,
                (
                    f"{container['name']}: "
                    f"unexpected state {state}"
                ),
            )
        )

    if check_health:
        health = container["health"]

        if health == "unhealthy":
            problems.append(
                (
                    CRITICAL,
                    f"{container['name']}: unhealthy",
                )
            )

        elif health == "starting":
            problems.append(
                (
                    WARNING,
                    (
                        f"{container['name']}: "
                        "healthcheck starting"
                    ),
                )
            )

        elif health not in (
            "none",
            "healthy",
        ):
            problems.append(
                (
                    WARNING,
                    (
                        f"{container['name']}: "
                        f"health={health}"
                    ),
                )
            )

    if not problems:
        return OK, []

    status = max(
        item[0]
        for item in problems
    )

    return status, problems


def resource_status(
    container,
    cpu_warning,
    cpu_critical,
    memory_warning,
    memory_critical,
):
    """Evaluate resource thresholds for one container."""
    problems = []
    status = OK

    cpu = container["cpu_percent"]

    if cpu is not None:
        if (
            cpu_critical is not None
            and cpu >= cpu_critical
        ):
            problems.append(
                (
                    CRITICAL,
                    (
                        f"{container['name']}: CPU "
                        f"{cpu:.2f}% >= "
                        f"{cpu_critical:g}%"
                    ),
                )
            )

        elif (
            cpu_warning is not None
            and cpu >= cpu_warning
        ):
            problems.append(
                (
                    WARNING,
                    (
                        f"{container['name']}: CPU "
                        f"{cpu:.2f}% >= "
                        f"{cpu_warning:g}%"
                    ),
                )
            )

    memory = container[
        "memory_percent"
    ]

    if memory is not None:
        memory_text = format_memory_detail(
            container
        )

        if (
            memory_critical is not None
            and memory >= memory_critical
        ):
            problems.append(
                (
                    CRITICAL,
                    (
                        f"{container['name']}: memory "
                        f"{memory:.2f}% >= "
                        f"{memory_critical:g}%"
                        f" ({memory_text})"
                    ),
                )
            )

        elif (
            memory_warning is not None
            and memory >= memory_warning
        ):
            problems.append(
                (
                    WARNING,
                    (
                        f"{container['name']}: memory "
                        f"{memory:.2f}% >= "
                        f"{memory_warning:g}%"
                        f" ({memory_text})"
                    ),
                )
            )

    if problems:
        status = max(
            item[0]
            for item in problems
        )

    return status, problems


def restart_status(
    container,
    warning,
    critical,
):
    """Evaluate lifetime Docker restart count."""
    count = container[
        "restart_count"
    ]

    if count >= critical:
        return (
            CRITICAL,
            [
                (
                    CRITICAL,
                    (
                        f"{container['name']}: "
                        f"restarted {count} times"
                    ),
                )
            ],
        )

    if count >= warning:
        return (
            WARNING,
            [
                (
                    WARNING,
                    (
                        f"{container['name']}: "
                        f"restarted {count} times"
                    ),
                )
            ],
        )

    return OK, []


def highest_status(*statuses):
    """Return highest Nagios severity."""
    if CRITICAL in statuses:
        return CRITICAL

    if WARNING in statuses:
        return WARNING

    if UNKNOWN in statuses:
        return UNKNOWN

    return OK


def problem_count_status(
    count,
    warning,
    critical,
):
    """Apply aggregate problem-count thresholds."""
    if count == 0:
        return OK

    if (
        warning is None
        and critical is None
    ):
        return CRITICAL

    if (
        critical is not None
        and count >= critical
    ):
        return CRITICAL

    if (
        warning is not None
        and count >= warning
    ):
        return WARNING

    return OK


def format_bytes(value):
    """Format byte values for human-readable output."""
    if value is None:
        return "unknown"

    units = [
        ("TiB", 1024 ** 4),
        ("GiB", 1024 ** 3),
        ("MiB", 1024 ** 2),
        ("KiB", 1024),
    ]

    for label, divisor in units:
        if value >= divisor:
            number = value / divisor

            if number >= 10:
                return (
                    f"{number:.1f} {label}"
                )

            return (
                f"{number:.2f} {label}"
            )

    return f"{value} B"


def format_memory_detail(container):
    """Return human-readable memory information."""
    used = container[
        "memory_used_bytes"
    ]

    limit = container[
        "memory_stats_limit_bytes"
    ]

    percent = container[
        "memory_percent"
    ]

    if used is None:
        return "memory data unavailable"

    if limit is None:
        return format_bytes(
            used
        )

    detail = (
        f"{format_bytes(used)} / "
        f"{format_bytes(limit)}"
    )

    if percent is not None:
        detail += (
            f", {percent:.2f}%"
        )

    if (
        container[
            "memory_limit_bytes"
        ] == 0
    ):
        detail += (
            ", no explicit container limit"
        )

    return detail


def perf_label(value):
    """Escape a Nagios performance-data label."""
    return value.replace(
        "'",
        "''",
    )


def build_perfdata(
    selected,
    all_containers,
    missing_count,
    check_resources,
    cpu_warning,
    cpu_critical,
    memory_warning,
    memory_critical,
):
    """Build Nagios performance data."""
    running = sum(
        1
        for item in selected
        if item["state"] == "running"
        and not item["paused"]
        and not item["restarting"]
    )

    stopped = sum(
        1
        for item in selected
        if item["state"] in (
            "exited",
            "dead",
        )
    )

    paused = sum(
        1
        for item in selected
        if item["paused"]
        or item["state"] == "paused"
    )

    restarting = sum(
        1
        for item in selected
        if item["restarting"]
        or item["state"] == "restarting"
    )

    unhealthy = sum(
        1
        for item in selected
        if item["health"] == "unhealthy"
    )

    oom_count = sum(
        1
        for item in selected
        if item["oom_killed"]
    )

    restarts = sum(
        item["restart_count"]
        for item in selected
    )

    perf = [
        f"containers={len(selected)}",
        f"running={running}",
        f"stopped={stopped}",
        f"paused={paused}",
        f"restarting={restarting}",
        f"unhealthy={unhealthy}",
        f"oom_killed={oom_count}",
        f"missing={missing_count}",
        f"restarts={restarts}",
    ]

    if check_resources:
        for item in selected:
            name = perf_label(
                item["name"]
            )

            cpu = item[
                "cpu_percent"
            ]

            memory = item[
                "memory_percent"
            ]

            memory_bytes = item[
                "memory_used_bytes"
            ]

            pids = item[
                "pids"
            ]

            if cpu is not None:
                cpu_perf = (
                    f"'{name}_cpu'="
                    f"{cpu:.2f}%"
                )

                if (
                    cpu_warning is not None
                    or cpu_critical is not None
                ):
                    warn = (
                        ""
                        if cpu_warning is None
                        else f"{cpu_warning:g}"
                    )

                    crit = (
                        ""
                        if cpu_critical is None
                        else f"{cpu_critical:g}"
                    )

                    cpu_perf += (
                        f";{warn};{crit}"
                    )

                perf.append(
                    cpu_perf
                )

            if memory is not None:
                memory_perf = (
                    f"'{name}_memory'="
                    f"{memory:.2f}%"
                )

                if (
                    memory_warning is not None
                    or memory_critical is not None
                ):
                    warn = (
                        ""
                        if memory_warning is None
                        else f"{memory_warning:g}"
                    )

                    crit = (
                        ""
                        if memory_critical is None
                        else f"{memory_critical:g}"
                    )

                    memory_perf += (
                        f";{warn};{crit};0;100"
                    )

                perf.append(
                    memory_perf
                )

            if memory_bytes is not None:
                perf.append(
                    (
                        f"'{name}_memory_bytes'="
                        f"{memory_bytes}B"
                    )
                )

            if pids is not None:
                perf.append(
                    f"'{name}_pids'={pids}"
                )

    return perf


def print_verbose(
    args,
    runtime,
    all_containers,
    selected,
    excluded,
    missing_expected,
):
    """Print verbose/debug information."""
    if args.verbose < 1:
        return

    print(
        f"Runtime: {runtime}"
    )

    print(
        "Containers discovered: "
        f"{len(all_containers)}"
    )

    print(
        "Containers after filtering: "
        f"{len(selected)}"
    )

    print(
        "Excluded containers: "
        f"{len(excluded)}"
    )

    if missing_expected:
        print(
            "Missing expected containers: "
            + ", ".join(
                missing_expected
            )
        )

    for item in selected:
        print(
            f"{item['name']}:"
        )

        print(
            f"  id: {item['short_id']}"
        )

        print(
            f"  image: {item['image']}"
        )

        print(
            f"  state: {item['state']}"
        )

        print(
            f"  health: {item['health']}"
        )

        print(
            f"  restarts: "
            f"{item['restart_count']}"
        )

        print(
            "  restart policy: "
            f"{item['restart_policy']}"
        )

        print(
            f"  oom killed: "
            f"{item['oom_killed']}"
        )

        if args.check_resources:
            cpu = item[
                "cpu_percent"
            ]

            if cpu is None:
                print(
                    "  cpu: unavailable"
                )
            else:
                print(
                    f"  cpu: {cpu:.2f}%"
                )

            print(
                "  memory: "
                + format_memory_detail(
                    item
                )
            )

            if item["pids"] is None:
                print(
                    "  pids: unavailable"
                )
            else:
                print(
                    f"  pids: "
                    f"{item['pids']}"
                )

    if args.verbose >= 2:
        print("Debug:")

        print(
            f"  container selector: "
            f"{args.container or 'none'}"
        )

        print(
            f"  include patterns: "
            f"{args.include or 'none'}"
        )

        print(
            f"  exclude patterns: "
            f"{args.exclude or 'none'}"
        )

        print(
            f"  expected containers: "
            f"{args.expect or 'none'}"
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
            f"  restart monitoring: "
            f"{args.check_restarts}"
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

        print(
            f"  resource monitoring: "
            f"{args.check_resources}"
        )

        if args.check_resources:
            print(
                f"  cpu warning: "
                f"{args.cpu_warning}"
            )

            print(
                f"  cpu critical: "
                f"{args.cpu_critical}"
            )

            print(
                f"  memory warning: "
                f"{args.memory_warning}"
            )

            print(
                f"  memory critical: "
                f"{args.memory_critical}"
            )

        print(
            f"  timeout: "
            f"{args.timeout}s"
        )

        print(
            f"  max details: "
            f"{args.max_details}"
        )


def parse_arguments():
    parser = NagiosArgumentParser(
        description=(
            "Nagios/Icinga plugin for monitoring "
            "container health and resource usage."
        )
    )

    runtime_group = parser.add_argument_group(
        "container runtime"
    )

    runtime_group.add_argument(
        "--runtime",
        choices=(
            "auto",
            "docker",
            "podman",
        ),
        default="auto",
        help=(
            "Container runtime. "
            "Version 1.0.1 supports Docker; "
            "default: auto."
        ),
    )

    selection = parser.add_argument_group(
        "container selection"
    )

    selection.add_argument(
        "--container",
        metavar="NAME_OR_ID",
        help=(
            "Check exactly one container by exact "
            "name, full ID, or unique ID prefix."
        ),
    )

    selection.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Only include container names matching "
            "PATTERN. May be specified multiple times."
        ),
    )

    selection.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help=(
            "Exclude container names matching PATTERN. "
            "May be specified multiple times."
        ),
    )

    selection.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "Require a container with exact NAME to "
            "exist. May be specified multiple times."
        ),
    )

    health = parser.add_argument_group(
        "container health"
    )

    health.add_argument(
        "--check-health",
        dest="check_health",
        action="store_true",
        default=True,
        help=(
            "Check Docker HEALTHCHECK state "
            "(default)."
        ),
    )

    health.add_argument(
        "--no-health",
        dest="check_health",
        action="store_false",
        help=(
            "Do not evaluate Docker HEALTHCHECK state."
        ),
    )

    health.add_argument(
        "--warning",
        type=int,
        metavar="N",
        help=(
            "WARNING when N or more selected containers "
            "have state/health problems."
        ),
    )

    health.add_argument(
        "--critical",
        type=int,
        metavar="N",
        help=(
            "CRITICAL when N or more selected containers "
            "have state/health problems."
        ),
    )

    restarts = parser.add_argument_group(
        "restart monitoring"
    )

    restarts.add_argument(
        "--check-restarts",
        action="store_true",
        help=(
            "Check Docker lifetime RestartCount."
        ),
    )

    restarts.add_argument(
        "--restart-warning",
        type=int,
        metavar="N",
        help=(
            "WARNING when a container RestartCount "
            "is N or higher. Default: 3."
        ),
    )

    restarts.add_argument(
        "--restart-critical",
        type=int,
        metavar="N",
        help=(
            "CRITICAL when a container RestartCount "
            "is N or higher. Default: 5."
        ),
    )

    resources = parser.add_argument_group(
        "resource monitoring"
    )

    resources.add_argument(
        "--check-resources",
        action="store_true",
        help=(
            "Collect CPU, memory, and PID statistics."
        ),
    )

    resources.add_argument(
        "--cpu-warning",
        type=float,
        metavar="PERCENT",
        help=(
            "WARNING when a container CPU percentage "
            "is at or above PERCENT."
        ),
    )

    resources.add_argument(
        "--cpu-critical",
        type=float,
        metavar="PERCENT",
        help=(
            "CRITICAL when a container CPU percentage "
            "is at or above PERCENT."
        ),
    )

    resources.add_argument(
        "--memory-warning",
        type=float,
        metavar="PERCENT",
        help=(
            "WARNING when a container memory percentage "
            "is at or above PERCENT."
        ),
    )

    resources.add_argument(
        "--memory-critical",
        type=float,
        metavar="PERCENT",
        help=(
            "CRITICAL when a container memory percentage "
            "is at or above PERCENT."
        ),
    )

    output = parser.add_argument_group(
        "output and execution"
    )

    output.add_argument(
        "--max-details",
        type=int,
        default=DEFAULT_MAX_DETAILS,
        metavar="N",
        help=(
            "Maximum number of problem details in "
            f"plugin output (default: {DEFAULT_MAX_DETAILS})."
        ),
    )

    output.add_argument(
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

    output.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=(
            "Increase verbosity. Use -vv for debug output."
        ),
    )

    output.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )

    return parser.parse_args()


def validate_arguments(args):
    """Validate CLI options."""
    if args.timeout <= 0:
        raise PluginError(
            "--timeout must be greater than zero"
        )

    if args.max_details < 1:
        raise PluginError(
            "--max-details must be greater than zero"
        )

    if args.container and (
        args.include
        or args.exclude
        or args.expect
    ):
        raise PluginError(
            "--container cannot be combined with "
            "--include, --exclude or --expect"
        )

    if (
        args.warning is not None
        and args.warning < 1
    ):
        raise PluginError(
            "--warning must be greater than zero"
        )

    if (
        args.critical is not None
        and args.critical < 1
    ):
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

    restart_options = (
        args.restart_warning is not None
        or args.restart_critical is not None
    )

    if (
        restart_options
        and not args.check_restarts
    ):
        raise PluginError(
            "--restart-warning and --restart-critical "
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

    resource_options = (
        args.cpu_warning is not None
        or args.cpu_critical is not None
        or args.memory_warning is not None
        or args.memory_critical is not None
    )

    if (
        resource_options
        and not args.check_resources
    ):
        raise PluginError(
            "CPU and memory thresholds require "
            "--check-resources"
        )

    for name, value in (
        ("--cpu-warning", args.cpu_warning),
        ("--cpu-critical", args.cpu_critical),
    ):
        if (
            value is not None
            and value <= 0
        ):
            raise PluginError(
                f"{name} must be greater than zero"
            )

    if (
        args.cpu_warning is not None
        and args.cpu_critical is not None
        and args.cpu_warning
        >= args.cpu_critical
    ):
        raise PluginError(
            "--cpu-warning must be lower than "
            "--cpu-critical"
        )

    for name, value in (
        (
            "--memory-warning",
            args.memory_warning,
        ),
        (
            "--memory-critical",
            args.memory_critical,
        ),
    ):
        if (
            value is not None
            and (
                value <= 0
                or value > 100
            )
        ):
            raise PluginError(
                f"{name} must be greater than zero "
                "and at most 100"
            )

    if (
        args.memory_warning is not None
        and args.memory_critical is not None
        and args.memory_warning
        >= args.memory_critical
    ):
        raise PluginError(
            "--memory-warning must be lower than "
            "--memory-critical"
        )


def main():
    args = parse_arguments()

    try:
        validate_arguments(
            args
        )

        runtime, runtime_bin = (
            detect_runtime(
                args.runtime
            )
        )

        validate_runtime(
            runtime_bin,
            args.timeout,
        )

        all_containers = get_containers(
            runtime_bin,
            args.timeout,
        )

        missing_expected = (
            get_missing_expected(
                all_containers,
                args.expect,
            )
        )

        (
            selected,
            excluded,
            selector_missing,
        ) = select_containers(
            all_containers,
            selector=args.container,
            includes=args.include,
            excludes=args.exclude,
        )

        if args.check_resources:
            stats = get_resource_stats(
                runtime_bin,
                args.timeout,
            )

            merge_stats(
                selected,
                stats,
            )

        print_verbose(
            args,
            runtime,
            all_containers,
            selected,
            excluded,
            missing_expected,
        )

        if selector_missing:
            print(
                "CONTAINERS CRITICAL: "
                f"container '{args.container}' not found"
                " | containers=0 running=0 stopped=0 "
                "unhealthy=0 missing=1 restarts=0"
            )

            return CRITICAL

        problems = []

        state_problem_containers = 0
        state_worst = OK

        for container in selected:
            status, details = state_status(
                container,
                args.check_health,
            )

            if status != OK:
                state_problem_containers += 1

            state_worst = highest_status(
                state_worst,
                status,
            )

            problems.extend(
                details
            )

        aggregate_state = (
            problem_count_status(
                state_problem_containers,
                args.warning,
                args.critical,
            )
        )

        if (
            args.warning is None
            and args.critical is None
        ):
            aggregate_state = (
                state_worst
            )

        final_status = (
            aggregate_state
        )

        for name in missing_expected:
            problems.append(
                (
                    CRITICAL,
                    (
                        f"expected container "
                        f"'{name}' is missing"
                    ),
                )
            )

            final_status = (
                CRITICAL
            )

        if args.check_restarts:
            for container in selected:
                (
                    status,
                    details,
                ) = restart_status(
                    container,
                    args.restart_warning,
                    args.restart_critical,
                )

                final_status = (
                    highest_status(
                        final_status,
                        status,
                    )
                )

                problems.extend(
                    details
                )

        if args.check_resources:
            for container in selected:
                (
                    status,
                    details,
                ) = resource_status(
                    container,
                    args.cpu_warning,
                    args.cpu_critical,
                    args.memory_warning,
                    args.memory_critical,
                )

                final_status = (
                    highest_status(
                        final_status,
                        status,
                    )
                )

                problems.extend(
                    details
                )

        perfdata = build_perfdata(
            selected,
            all_containers,
            len(missing_expected),
            args.check_resources,
            args.cpu_warning,
            args.cpu_critical,
            args.memory_warning,
            args.memory_critical,
        )

        if not all_containers:
            if args.expect:
                final_status = (
                    CRITICAL
                )

            elif not args.container:
                final_status = OK

        if final_status == OK:
            running = sum(
                1
                for item in selected
                if item["state"] == "running"
                and not item["paused"]
                and not item["restarting"]
            )

            if not all_containers:
                summary = (
                    "no containers found"
                )

            elif args.container and selected:
                item = selected[0]

                summary = (
                    f"{item['name']} "
                    f"{item['state']}"
                )

                if args.check_health:
                    summary += (
                        f", health={item['health']}"
                    )

                summary += (
                    f", restarts="
                    f"{item['restart_count']}"
                )

                if args.check_resources:
                    if (
                        item["cpu_percent"]
                        is not None
                    ):
                        summary += (
                            f", CPU "
                            f"{item['cpu_percent']:.2f}%"
                        )

                    if (
                        item["memory_percent"]
                        is not None
                    ):
                        summary += (
                            f", memory "
                            f"{item['memory_percent']:.2f}%"
                        )

            else:
                container_word = (
                    "container"
                    if len(selected) == 1
                    else "containers"
                )

                summary = (
                    f"{len(selected)} {container_word}, "
                    f"{running} running, "
                    "no problems"
                )

                if args.check_restarts:
                    summary += (
                        ", no excessive restarts"
                    )

        else:
            ordered = sorted(
                problems,
                key=lambda item: item[0],
                reverse=True,
            )

            detail_text = [
                item[1]
                for item in ordered[
                    :args.max_details
                ]
            ]

            hidden = (
                len(ordered)
                - len(detail_text)
            )

            summary = "; ".join(
                detail_text
            )

            if hidden > 0:
                summary += (
                    f"; +{hidden} more"
                )

            if not summary:
                summary = (
                    "container problem detected"
                )

        print(
            f"CONTAINERS "
            f"{STATUS_TEXT[final_status]}: "
            f"{summary} | "
            + " ".join(
                perfdata
            )
        )

        return final_status

    except PluginError as exc:
        print(
            f"CONTAINERS UNKNOWN: {exc}"
        )

        return UNKNOWN

    except KeyboardInterrupt:
        print(
            "CONTAINERS UNKNOWN: interrupted"
        )

        return UNKNOWN


if __name__ == "__main__":
    sys.exit(
        main()
    )
