#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# Unit tests for check_container_health.py
#
# Copyright (c) 2026 Csaba Csanaki
#
# Licensed under the MIT License.

import argparse
import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import check_container_health as plugin


def make_container(
    name="test-container",
    container_id="a" * 64,
    state="running",
    running=True,
    paused=False,
    restarting=False,
    oom_killed=False,
    dead=False,
    exit_code=0,
    health="none",
    restart_count=0,
    restart_policy="always",
    memory_limit_bytes=0,
    cpu_percent=None,
    memory_percent=None,
    memory_used_bytes=None,
    memory_stats_limit_bytes=None,
    pids=None,
):
    """Create a normalized container dictionary for tests."""
    return {
        "id": container_id,
        "short_id": container_id[:12],
        "name": name,
        "image": "example/test:1.0",
        "state": state,
        "running": running,
        "paused": paused,
        "restarting": restarting,
        "oom_killed": oom_killed,
        "dead": dead,
        "exit_code": exit_code,
        "health": health,
        "restart_count": restart_count,
        "restart_policy": restart_policy,
        "memory_limit_bytes": memory_limit_bytes,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "memory_used_bytes": memory_used_bytes,
        "memory_stats_limit_bytes": memory_stats_limit_bytes,
        "memory_usage_text": None,
        "pids": pids,
    }


def make_args(**overrides):
    """Create an argparse.Namespace matching plugin defaults."""
    values = {
        "runtime": "auto",
        "container": None,
        "include": [],
        "exclude": [],
        "expect": [],
        "check_health": True,
        "warning": None,
        "critical": None,
        "check_restarts": False,
        "restart_warning": None,
        "restart_critical": None,
        "check_resources": False,
        "cpu_warning": None,
        "cpu_critical": None,
        "memory_warning": None,
        "memory_critical": None,
        "max_details": plugin.DEFAULT_MAX_DETAILS,
        "timeout": plugin.DEFAULT_TIMEOUT,
        "verbose": 0,
    }

    values.update(overrides)
    return argparse.Namespace(**values)


class TestSafeInt(unittest.TestCase):

    def test_integer(self):
        self.assertEqual(plugin.safe_int(42), 42)

    def test_string_integer(self):
        self.assertEqual(plugin.safe_int("42"), 42)

    def test_invalid(self):
        self.assertEqual(plugin.safe_int("invalid", 7), 7)

    def test_none(self):
        self.assertEqual(plugin.safe_int(None, 3), 3)


class TestPercentParsing(unittest.TestCase):

    def test_percent(self):
        self.assertEqual(plugin.parse_percent("12.34%"), 12.34)

    def test_percent_without_suffix(self):
        self.assertEqual(plugin.parse_percent("7.5"), 7.5)

    def test_over_100_percent(self):
        self.assertEqual(plugin.parse_percent("237.4%"), 237.4)

    def test_invalid_percent(self):
        self.assertIsNone(plugin.parse_percent("invalid"))

    def test_none_percent(self):
        self.assertIsNone(plugin.parse_percent(None))


class TestSizeParsing(unittest.TestCase):

    def test_bytes(self):
        self.assertEqual(plugin.parse_size("10B"), 10)

    def test_kib(self):
        self.assertEqual(plugin.parse_size("1KiB"), 1024)

    def test_mib(self):
        self.assertEqual(
            plugin.parse_size("170.4MiB"),
            int(170.4 * 1024 ** 2),
        )

    def test_gib(self):
        self.assertEqual(
            plugin.parse_size("7.5GiB"),
            int(7.5 * 1024 ** 3),
        )

    def test_decimal_mb(self):
        self.assertEqual(
            plugin.parse_size("2MB"),
            2 * 1000 ** 2,
        )

    def test_invalid_size(self):
        self.assertIsNone(plugin.parse_size("unknown"))

    def test_memory_usage(self):
        used, limit = plugin.parse_memory_usage(
            "170.4MiB / 7.5GiB"
        )

        self.assertEqual(
            used,
            int(170.4 * 1024 ** 2),
        )
        self.assertEqual(
            limit,
            int(7.5 * 1024 ** 3),
        )

    def test_invalid_memory_usage(self):
        used, limit = plugin.parse_memory_usage("invalid")
        self.assertIsNone(used)
        self.assertIsNone(limit)


class TestInspectParsing(unittest.TestCase):

    def test_running_without_healthcheck(self):
        raw = [
            {
                "Id": "a" * 64,
                "Name": "/grafana",
                "State": {
                    "Status": "running",
                    "Running": True,
                    "Paused": False,
                    "Restarting": False,
                    "OOMKilled": False,
                    "Dead": False,
                    "ExitCode": 0,
                },
                "RestartCount": 0,
                "HostConfig": {
                    "RestartPolicy": {
                        "Name": "always"
                    },
                    "Memory": 0,
                },
                "Config": {
                    "Image": "grafana:test"
                },
            }
        ]

        containers = plugin.parse_inspect_json(
            json.dumps(raw)
        )

        self.assertEqual(len(containers), 1)

        item = containers[0]

        self.assertEqual(item["name"], "grafana")
        self.assertEqual(item["state"], "running")
        self.assertEqual(item["health"], "none")
        self.assertEqual(item["restart_count"], 0)
        self.assertEqual(item["restart_policy"], "always")
        self.assertEqual(item["memory_limit_bytes"], 0)

    def test_healthcheck_healthy(self):
        raw = [
            {
                "Id": "b" * 64,
                "Name": "/web",
                "State": {
                    "Status": "running",
                    "Running": True,
                    "Health": {
                        "Status": "healthy"
                    },
                },
                "HostConfig": {},
                "Config": {},
            }
        ]

        item = plugin.parse_inspect_json(
            json.dumps(raw)
        )[0]

        self.assertEqual(item["health"], "healthy")

    def test_healthcheck_unhealthy(self):
        raw = [
            {
                "Id": "b" * 64,
                "Name": "/web",
                "State": {
                    "Status": "running",
                    "Running": True,
                    "Health": {
                        "Status": "unhealthy"
                    },
                },
                "HostConfig": {},
                "Config": {},
            }
        ]

        item = plugin.parse_inspect_json(
            json.dumps(raw)
        )[0]

        self.assertEqual(item["health"], "unhealthy")

    def test_oom_and_restart_count(self):
        raw = [
            {
                "Id": "c" * 64,
                "Name": "/worker",
                "State": {
                    "Status": "running",
                    "Running": True,
                    "OOMKilled": True,
                },
                "RestartCount": 8,
                "HostConfig": {},
                "Config": {},
            }
        ]

        item = plugin.parse_inspect_json(
            json.dumps(raw)
        )[0]

        self.assertTrue(item["oom_killed"])
        self.assertEqual(item["restart_count"], 8)

    def test_invalid_json(self):
        with self.assertRaises(plugin.PluginError):
            plugin.parse_inspect_json("{invalid")

    def test_non_list_json(self):
        with self.assertRaises(plugin.PluginError):
            plugin.parse_inspect_json("{}")


class TestStatsParsing(unittest.TestCase):

    def test_stats_line(self):
        output = (
            "07e4f91ddf6b|kof-grafana|0.10%|"
            "170.4MiB / 7.5GiB|2.22%|16"
        )

        stats = plugin.parse_stats_output(output)

        self.assertIn("kof-grafana", stats)

        item = stats["kof-grafana"]

        self.assertEqual(item["cpu_percent"], 0.10)
        self.assertEqual(item["memory_percent"], 2.22)
        self.assertEqual(item["pids"], 16)

    def test_multiple_stats_lines(self):
        output = "\n".join(
            [
                "a|one|1.00%|10MiB / 1GiB|0.98%|2",
                "b|two|2.00%|20MiB / 1GiB|1.95%|3",
            ]
        )

        stats = plugin.parse_stats_output(output)

        self.assertEqual(len(stats), 2)
        self.assertEqual(stats["one"]["cpu_percent"], 1.0)
        self.assertEqual(stats["two"]["pids"], 3)

    def test_malformed_stats_line_is_ignored(self):
        stats = plugin.parse_stats_output(
            "this-is-not-valid"
        )

        self.assertEqual(stats, {})


class TestMergeStats(unittest.TestCase):

    def test_merge_stats(self):
        containers = [
            make_container(name="grafana")
        ]

        stats = {
            "grafana": {
                "id": "abc",
                "cpu_percent": 3.5,
                "memory_percent": 25.0,
                "memory_used_bytes": 256 * 1024 ** 2,
                "memory_limit_bytes": 1024 ** 3,
                "memory_usage_text": "256MiB / 1GiB",
                "pids": 12,
            }
        }

        plugin.merge_stats(containers, stats)

        item = containers[0]

        self.assertEqual(item["cpu_percent"], 3.5)
        self.assertEqual(item["memory_percent"], 25.0)
        self.assertEqual(item["pids"], 12)

    def test_missing_stats_are_allowed(self):
        containers = [
            make_container(name="stopped")
        ]

        plugin.merge_stats(containers, {})

        self.assertIsNone(
            containers[0]["cpu_percent"]
        )


class TestFiltering(unittest.TestCase):

    def setUp(self):
        self.containers = [
            make_container(
                name="kof-grafana",
                container_id="a" * 64,
            ),
            make_container(
                name="kof-nginx",
                container_id="b" * 64,
            ),
            make_container(
                name="atom-fluentd",
                container_id="c" * 64,
            ),
        ]

    def test_no_filters(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers
            )
        )

        self.assertEqual(len(selected), 3)
        self.assertEqual(excluded, [])
        self.assertFalse(missing)

    def test_include_wildcard(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                includes=["kof-*"],
            )
        )

        self.assertEqual(
            [x["name"] for x in selected],
            ["kof-grafana", "kof-nginx"],
        )
        self.assertFalse(missing)

    def test_exclude_wildcard(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                excludes=["kof-*"],
            )
        )

        self.assertEqual(
            [x["name"] for x in selected],
            ["atom-fluentd"],
        )
        self.assertEqual(len(excluded), 2)
        self.assertFalse(missing)

    def test_exclude_wins_over_include(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                includes=["kof-*"],
                excludes=["*nginx"],
            )
        )

        self.assertEqual(
            [x["name"] for x in selected],
            ["kof-grafana"],
        )
        self.assertEqual(
            [x["name"] for x in excluded],
            ["kof-nginx"],
        )
        self.assertFalse(missing)

    def test_container_exact_name(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                selector="kof-grafana",
            )
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["name"],
            "kof-grafana",
        )
        self.assertFalse(missing)

    def test_container_full_id(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                selector="b" * 64,
            )
        )

        self.assertEqual(
            selected[0]["name"],
            "kof-nginx",
        )
        self.assertFalse(missing)

    def test_container_unique_id_prefix(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                selector="cccccccccccc",
            )
        )

        self.assertEqual(
            selected[0]["name"],
            "atom-fluentd",
        )
        self.assertFalse(missing)

    def test_container_missing(self):
        selected, excluded, missing = (
            plugin.select_containers(
                self.containers,
                selector="missing",
            )
        )

        self.assertEqual(selected, [])
        self.assertTrue(missing)

    def test_ambiguous_id_prefix(self):
        containers = [
            make_container(
                name="one",
                container_id="abc111" + "0" * 58,
            ),
            make_container(
                name="two",
                container_id="abc222" + "0" * 58,
            ),
        ]

        with self.assertRaises(plugin.PluginError):
            plugin.find_single_container(
                containers,
                "abc",
            )


class TestExpectedContainers(unittest.TestCase):

    def test_all_expected_exist(self):
        containers = [
            make_container(name="grafana"),
            make_container(name="mysql"),
        ]

        missing = plugin.get_missing_expected(
            containers,
            ["grafana", "mysql"],
        )

        self.assertEqual(missing, [])

    def test_expected_missing(self):
        containers = [
            make_container(name="grafana")
        ]

        missing = plugin.get_missing_expected(
            containers,
            ["grafana", "mysql"],
        )

        self.assertEqual(missing, ["mysql"])


class TestStateStatus(unittest.TestCase):

    def test_running_no_healthcheck_is_ok(self):
        status, details = plugin.state_status(
            make_container()
        )

        self.assertEqual(status, plugin.OK)
        self.assertEqual(details, [])

    def test_healthy_is_ok(self):
        status, details = plugin.state_status(
            make_container(health="healthy")
        )

        self.assertEqual(status, plugin.OK)
        self.assertEqual(details, [])

    def test_unhealthy_is_critical(self):
        status, details = plugin.state_status(
            make_container(health="unhealthy")
        )

        self.assertEqual(status, plugin.CRITICAL)
        self.assertTrue(details)

    def test_unhealthy_ignored_with_no_health(self):
        status, details = plugin.state_status(
            make_container(health="unhealthy"),
            check_health=False,
        )

        self.assertEqual(status, plugin.OK)
        self.assertEqual(details, [])

    def test_health_starting_is_warning(self):
        status, details = plugin.state_status(
            make_container(health="starting")
        )

        self.assertEqual(status, plugin.WARNING)

    def test_paused_is_warning(self):
        status, details = plugin.state_status(
            make_container(
                state="paused",
                running=False,
                paused=True,
            )
        )

        self.assertEqual(status, plugin.WARNING)

    def test_restarting_is_warning(self):
        status, details = plugin.state_status(
            make_container(
                state="restarting",
                running=False,
                restarting=True,
            )
        )

        self.assertEqual(status, plugin.WARNING)

    def test_created_is_warning(self):
        status, details = plugin.state_status(
            make_container(
                state="created",
                running=False,
            )
        )

        self.assertEqual(status, plugin.WARNING)

    def test_exited_is_critical(self):
        status, details = plugin.state_status(
            make_container(
                state="exited",
                running=False,
                exit_code=1,
            )
        )

        self.assertEqual(status, plugin.CRITICAL)
        self.assertIn(
            "exited (1)",
            details[0][1],
        )

    def test_dead_is_critical(self):
        status, details = plugin.state_status(
            make_container(
                state="dead",
                running=False,
                dead=True,
            )
        )

        self.assertEqual(status, plugin.CRITICAL)

    def test_oom_killed_is_critical(self):
        status, details = plugin.state_status(
            make_container(
                oom_killed=True
            )
        )

        self.assertEqual(status, plugin.CRITICAL)
        self.assertTrue(
            any(
                "OOM-killed" in detail
                for _, detail in details
            )
        )

    def test_unknown_state_is_critical(self):
        status, details = plugin.state_status(
            make_container(
                state="mystery",
                running=False,
            )
        )

        self.assertEqual(status, plugin.CRITICAL)


class TestRestartStatus(unittest.TestCase):

    def test_restart_ok(self):
        status, details = plugin.restart_status(
            make_container(restart_count=2),
            3,
            5,
        )

        self.assertEqual(status, plugin.OK)
        self.assertEqual(details, [])

    def test_restart_warning(self):
        status, details = plugin.restart_status(
            make_container(restart_count=3),
            3,
            5,
        )

        self.assertEqual(status, plugin.WARNING)

    def test_restart_critical(self):
        status, details = plugin.restart_status(
            make_container(restart_count=5),
            3,
            5,
        )

        self.assertEqual(status, plugin.CRITICAL)

    def test_high_restart_count(self):
        status, details = plugin.restart_status(
            make_container(restart_count=20),
            3,
            5,
        )

        self.assertEqual(status, plugin.CRITICAL)


class TestResourceStatus(unittest.TestCase):

    def test_resources_ok(self):
        container = make_container(
            cpu_percent=10.0,
            memory_percent=20.0,
            memory_used_bytes=200 * 1024 ** 2,
            memory_stats_limit_bytes=1024 ** 3,
        )

        status, details = plugin.resource_status(
            container,
            80,
            95,
            80,
            90,
        )

        self.assertEqual(status, plugin.OK)
        self.assertEqual(details, [])

    def test_cpu_warning(self):
        container = make_container(
            cpu_percent=80.0
        )

        status, details = plugin.resource_status(
            container,
            80,
            95,
            None,
            None,
        )

        self.assertEqual(status, plugin.WARNING)

    def test_cpu_critical(self):
        container = make_container(
            cpu_percent=100.0
        )

        status, details = plugin.resource_status(
            container,
            80,
            95,
            None,
            None,
        )

        self.assertEqual(status, plugin.CRITICAL)

    def test_cpu_over_100_supported(self):
        container = make_container(
            cpu_percent=250.0
        )

        status, details = plugin.resource_status(
            container,
            200,
            300,
            None,
            None,
        )

        self.assertEqual(status, plugin.WARNING)

    def test_memory_warning(self):
        container = make_container(
            memory_percent=85.0,
            memory_used_bytes=850 * 1024 ** 2,
            memory_stats_limit_bytes=1024 ** 3,
        )

        status, details = plugin.resource_status(
            container,
            None,
            None,
            80,
            90,
        )

        self.assertEqual(status, plugin.WARNING)

    def test_memory_critical(self):
        container = make_container(
            memory_percent=95.0,
            memory_used_bytes=950 * 1024 ** 2,
            memory_stats_limit_bytes=1024 ** 3,
        )

        status, details = plugin.resource_status(
            container,
            None,
            None,
            80,
            90,
        )

        self.assertEqual(status, plugin.CRITICAL)


class TestProblemThresholds(unittest.TestCase):

    def test_zero_is_ok(self):
        self.assertEqual(
            plugin.problem_count_status(
                0,
                None,
                None,
            ),
            plugin.OK,
        )

    def test_default_problem_is_critical(self):
        self.assertEqual(
            plugin.problem_count_status(
                1,
                None,
                None,
            ),
            plugin.CRITICAL,
        )

    def test_warning_threshold(self):
        self.assertEqual(
            plugin.problem_count_status(
                1,
                1,
                3,
            ),
            plugin.WARNING,
        )

    def test_critical_threshold(self):
        self.assertEqual(
            plugin.problem_count_status(
                3,
                1,
                3,
            ),
            plugin.CRITICAL,
        )


class TestHighestStatus(unittest.TestCase):

    def test_all_ok(self):
        self.assertEqual(
            plugin.highest_status(
                plugin.OK,
                plugin.OK,
            ),
            plugin.OK,
        )

    def test_warning_wins(self):
        self.assertEqual(
            plugin.highest_status(
                plugin.OK,
                plugin.WARNING,
            ),
            plugin.WARNING,
        )

    def test_critical_wins(self):
        self.assertEqual(
            plugin.highest_status(
                plugin.WARNING,
                plugin.CRITICAL,
            ),
            plugin.CRITICAL,
        )


class TestPerfdata(unittest.TestCase):

    def test_perfdata_without_resource_thresholds_is_clean(self):
        container = make_container(
            name="grafana",
            cpu_percent=0.10,
            memory_percent=2.22,
            memory_used_bytes=170 * 1024 ** 2,
            memory_stats_limit_bytes=int(
                7.5 * 1024 ** 3
            ),
            pids=16,
        )

        perf = plugin.build_perfdata(
            [container],
            [container],
            0,
            True,
            None,
            None,
            None,
            None,
        )

        self.assertIn(
            "'grafana_cpu'=0.10%",
            perf,
        )
        self.assertIn(
            "'grafana_memory'=2.22%",
            perf,
        )

        joined = " ".join(perf)

        self.assertNotIn(
            "'grafana_cpu'=0.10%;;",
            joined,
        )
        self.assertNotIn(
            "'grafana_memory'=2.22%;;;",
            joined,
        )

    def test_perfdata_with_thresholds(self):
        container = make_container(
            name="grafana",
            cpu_percent=10.0,
            memory_percent=50.0,
            memory_used_bytes=512 * 1024 ** 2,
            memory_stats_limit_bytes=1024 ** 3,
            pids=10,
        )

        perf = plugin.build_perfdata(
            [container],
            [container],
            0,
            True,
            80,
            95,
            70,
            90,
        )

        self.assertIn(
            "'grafana_cpu'=10.00%;80;95",
            perf,
        )

        self.assertIn(
            "'grafana_memory'=50.00%;70;90;0;100",
            perf,
        )

    def test_perf_label_escaping(self):
        self.assertEqual(
            plugin.perf_label("it's-running"),
            "it''s-running",
        )


class TestArgumentValidation(unittest.TestCase):

    def test_valid_defaults(self):
        args = make_args()

        plugin.validate_arguments(args)

    def test_invalid_timeout(self):
        args = make_args(timeout=0)

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_invalid_max_details(self):
        args = make_args(max_details=0)

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_container_conflicts_with_include(self):
        args = make_args(
            container="grafana",
            include=["grafana*"],
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_container_conflicts_with_exclude(self):
        args = make_args(
            container="grafana",
            exclude=["test*"],
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_container_conflicts_with_expect(self):
        args = make_args(
            container="grafana",
            expect=["grafana"],
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_invalid_problem_thresholds(self):
        args = make_args(
            warning=5,
            critical=3,
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_restart_threshold_requires_restart_check(self):
        args = make_args(
            restart_warning=3
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_restart_defaults(self):
        args = make_args(
            check_restarts=True
        )

        plugin.validate_arguments(args)

        self.assertEqual(
            args.restart_warning,
            3,
        )
        self.assertEqual(
            args.restart_critical,
            5,
        )

    def test_invalid_restart_thresholds(self):
        args = make_args(
            check_restarts=True,
            restart_warning=5,
            restart_critical=3,
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_resource_threshold_requires_resource_check(self):
        args = make_args(
            cpu_warning=80
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_invalid_cpu_thresholds(self):
        args = make_args(
            check_resources=True,
            cpu_warning=95,
            cpu_critical=80,
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_cpu_can_exceed_100(self):
        args = make_args(
            check_resources=True,
            cpu_warning=200,
            cpu_critical=300,
        )

        plugin.validate_arguments(args)

    def test_invalid_memory_threshold_over_100(self):
        args = make_args(
            check_resources=True,
            memory_warning=80,
            memory_critical=101,
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)

    def test_invalid_memory_threshold_order(self):
        args = make_args(
            check_resources=True,
            memory_warning=90,
            memory_critical=80,
        )

        with self.assertRaises(plugin.PluginError):
            plugin.validate_arguments(args)


class TestRuntimeDetection(unittest.TestCase):

    @patch.object(plugin, "find_docker")
    def test_auto_detects_docker(self, mock_find):
        mock_find.return_value = "/usr/bin/docker"

        runtime, binary = plugin.detect_runtime(
            "auto"
        )

        self.assertEqual(runtime, "docker")
        self.assertEqual(binary, "/usr/bin/docker")

    @patch.object(plugin, "find_docker")
    def test_explicit_docker(self, mock_find):
        mock_find.return_value = "/usr/bin/docker"

        runtime, binary = plugin.detect_runtime(
            "docker"
        )

        self.assertEqual(runtime, "docker")

    @patch.object(plugin, "find_docker")
    def test_missing_docker(self, mock_find):
        mock_find.return_value = None

        with self.assertRaises(plugin.PluginError):
            plugin.detect_runtime("auto")

    def test_podman_not_supported(self):
        with self.assertRaises(plugin.PluginError):
            plugin.detect_runtime("podman")


class TestRunCommand(unittest.TestCase):

    @patch("check_container_health.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="hello\n",
            stderr="",
        )

        output = plugin.run_command(
            ["docker", "info"],
            30,
        )

        self.assertEqual(output, "hello")

    @patch("check_container_health.subprocess.run")
    def test_command_failure(self, mock_run):
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="daemon unavailable",
        )

        with self.assertRaises(plugin.PluginError):
            plugin.run_command(
                ["docker", "info"],
                30,
            )

    @patch("check_container_health.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = (
            subprocess.TimeoutExpired(
                cmd=["docker", "info"],
                timeout=30,
            )
        )

        with self.assertRaises(plugin.PluginError):
            plugin.run_command(
                ["docker", "info"],
                30,
            )


class TestMain(unittest.TestCase):

    def run_main(
        self,
        argv,
        containers,
        stats=None,
        runtime_error=None,
    ):
        """
        Run main() with Docker-facing functions mocked.
        Returns (exit_code, stdout).
        """
        if stats is None:
            stats = {}

        with patch.object(
            sys,
            "argv",
            ["check_container_health.py"] + argv,
        ), patch.object(
            plugin,
            "detect_runtime",
            return_value=(
                "docker",
                "/usr/bin/docker",
            ),
        ), patch.object(
            plugin,
            "validate_runtime",
        ) as mock_validate, patch.object(
            plugin,
            "get_containers",
            return_value=containers,
        ), patch.object(
            plugin,
            "get_resource_stats",
            return_value=stats,
        ):

            if runtime_error is not None:
                mock_validate.side_effect = (
                    runtime_error
                )

            output = io.StringIO()

            with redirect_stdout(output):
                rc = plugin.main()

        return rc, output.getvalue()

    def test_main_ok(self):
        rc, output = self.run_main(
            [],
            [
                make_container(
                    name="grafana"
                )
            ],
        )

        self.assertEqual(rc, plugin.OK)
        self.assertIn(
            "CONTAINERS OK:",
            output,
        )
        self.assertIn(
            "1 container, 1 running",
            output,
        )

    def test_main_exited_is_critical(self):
        rc, output = self.run_main(
            [],
            [
                make_container(
                    name="failed",
                    state="exited",
                    running=False,
                    exit_code=1,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )
        self.assertIn(
            "exited (1)",
            output,
        )

    def test_main_paused_is_warning(self):
        rc, output = self.run_main(
            [],
            [
                make_container(
                    name="paused",
                    state="paused",
                    running=False,
                    paused=True,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.WARNING,
        )

    def test_main_restarting_is_warning(self):
        rc, output = self.run_main(
            [],
            [
                make_container(
                    name="restart",
                    state="restarting",
                    running=False,
                    restarting=True,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.WARNING,
        )

    def test_main_unhealthy_is_critical(self):
        rc, output = self.run_main(
            [],
            [
                make_container(
                    name="web",
                    health="unhealthy",
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )
        self.assertIn(
            "unhealthy",
            output,
        )

    def test_main_no_health_ignores_unhealthy(self):
        rc, output = self.run_main(
            ["--no-health"],
            [
                make_container(
                    name="web",
                    health="unhealthy",
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.OK,
        )

    def test_main_oom_is_critical(self):
        rc, output = self.run_main(
            [],
            [
                make_container(
                    name="worker",
                    oom_killed=True,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )
        self.assertIn(
            "OOM-killed",
            output,
        )

    def test_main_missing_container_is_critical(self):
        rc, output = self.run_main(
            [
                "--container",
                "missing",
            ],
            [
                make_container(
                    name="grafana"
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )
        self.assertIn(
            "not found",
            output,
        )

    def test_main_missing_expected_is_critical(self):
        rc, output = self.run_main(
            [
                "--expect",
                "mysql",
            ],
            [
                make_container(
                    name="grafana"
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )
        self.assertIn(
            "expected container 'mysql' is missing",
            output,
        )

    def test_main_restart_warning(self):
        rc, output = self.run_main(
            [
                "--check-restarts",
            ],
            [
                make_container(
                    name="web",
                    restart_count=3,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.WARNING,
        )
        self.assertIn(
            "restarted 3 times",
            output,
        )

    def test_main_restart_critical(self):
        rc, output = self.run_main(
            [
                "--check-restarts",
            ],
            [
                make_container(
                    name="web",
                    restart_count=5,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )

    def test_main_resource_warning(self):
        container = make_container(
            name="grafana"
        )

        stats = {
            "grafana": {
                "id": "abc",
                "cpu_percent": 10.0,
                "memory_percent": 85.0,
                "memory_used_bytes": (
                    850 * 1024 ** 2
                ),
                "memory_limit_bytes": (
                    1024 ** 3
                ),
                "memory_usage_text": (
                    "850MiB / 1GiB"
                ),
                "pids": 10,
            }
        }

        rc, output = self.run_main(
            [
                "--check-resources",
                "--memory-warning",
                "80",
                "--memory-critical",
                "90",
            ],
            [container],
            stats=stats,
        )

        self.assertEqual(
            rc,
            plugin.WARNING,
        )
        self.assertIn(
            "memory 85.00%",
            output,
        )

    def test_main_resource_critical(self):
        container = make_container(
            name="grafana"
        )

        stats = {
            "grafana": {
                "id": "abc",
                "cpu_percent": 100.0,
                "memory_percent": 20.0,
                "memory_used_bytes": (
                    200 * 1024 ** 2
                ),
                "memory_limit_bytes": (
                    1024 ** 3
                ),
                "memory_usage_text": (
                    "200MiB / 1GiB"
                ),
                "pids": 10,
            }
        }

        rc, output = self.run_main(
            [
                "--check-resources",
                "--cpu-warning",
                "80",
                "--cpu-critical",
                "95",
            ],
            [container],
            stats=stats,
        )

        self.assertEqual(
            rc,
            plugin.CRITICAL,
        )
        self.assertIn(
            "CPU 100.00%",
            output,
        )

    def test_main_problem_threshold_warning(self):
        rc, output = self.run_main(
            [
                "--warning",
                "1",
                "--critical",
                "3",
            ],
            [
                make_container(
                    name="failed",
                    state="exited",
                    running=False,
                    exit_code=1,
                )
            ],
        )

        self.assertEqual(
            rc,
            plugin.WARNING,
        )

    def test_main_runtime_failure_is_unknown(self):
        rc, output = self.run_main(
            [],
            [],
            runtime_error=plugin.PluginError(
                "Docker daemon unavailable"
            ),
        )

        self.assertEqual(
            rc,
            plugin.UNKNOWN,
        )
        self.assertIn(
            "CONTAINERS UNKNOWN:",
            output,
        )

    def test_main_no_containers_is_ok(self):
        rc, output = self.run_main(
            [],
            [],
        )

        self.assertEqual(
            rc,
            plugin.OK,
        )
        self.assertIn(
            "no containers found",
            output,
        )


if __name__ == "__main__":
    unittest.main()
