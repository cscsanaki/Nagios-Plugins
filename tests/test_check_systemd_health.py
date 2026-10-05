#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# Unit tests for check_systemd_health.py

import argparse
import unittest
from unittest.mock import patch

import check_systemd_health as plugin


class TestParseSince(unittest.TestCase):

    def test_seconds(self):
        self.assertEqual(plugin.parse_since("30s"), 30)

    def test_minutes(self):
        self.assertEqual(plugin.parse_since("15m"), 900)

    def test_hours(self):
        self.assertEqual(plugin.parse_since("2h"), 7200)

    def test_days(self):
        self.assertEqual(plugin.parse_since("1d"), 86400)

    def test_uppercase_suffix(self):
        self.assertEqual(plugin.parse_since("2H"), 7200)

    def test_invalid_long_format(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            plugin.parse_since("30minutes")

    def test_invalid_zero(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            plugin.parse_since("0m")

    def test_invalid_missing_suffix(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            plugin.parse_since("30")


class TestFiltering(unittest.TestCase):

    def setUp(self):
        self.units = [
            "sshd.service",
            "nginx.service",
            "backup.service",
            "dnf-makecache.service",
        ]

    def test_no_filters(self):
        included, excluded = plugin.filter_units(
            self.units,
            [],
            [],
        )

        self.assertEqual(included, self.units)
        self.assertEqual(excluded, [])

    def test_include_exact(self):
        included, excluded = plugin.filter_units(
            self.units,
            ["sshd.service"],
            [],
        )

        self.assertEqual(
            included,
            ["sshd.service"],
        )
        self.assertEqual(excluded, [])

    def test_include_wildcard(self):
        included, excluded = plugin.filter_units(
            self.units,
            ["*.service"],
            [],
        )

        self.assertEqual(included, self.units)
        self.assertEqual(excluded, [])

    def test_exclude_exact(self):
        included, excluded = plugin.filter_units(
            self.units,
            [],
            ["backup.service"],
        )

        self.assertNotIn(
            "backup.service",
            included,
        )

        self.assertEqual(
            excluded,
            ["backup.service"],
        )

    def test_exclude_wildcard(self):
        included, excluded = plugin.filter_units(
            self.units,
            [],
            ["dnf-*"],
        )

        self.assertNotIn(
            "dnf-makecache.service",
            included,
        )

        self.assertEqual(
            excluded,
            ["dnf-makecache.service"],
        )

    def test_exclude_wins_over_include(self):
        included, excluded = plugin.filter_units(
            self.units,
            ["*.service"],
            ["backup.service"],
        )

        self.assertNotIn(
            "backup.service",
            included,
        )

        self.assertEqual(
            excluded,
            ["backup.service"],
        )


class TestProblemThresholds(unittest.TestCase):

    def test_zero_is_ok(self):
        status = plugin.determine_problem_status(
            0,
            None,
            None,
        )

        self.assertEqual(
            status,
            plugin.OK,
        )

    def test_default_problem_is_critical(self):
        status = plugin.determine_problem_status(
            1,
            None,
            None,
        )

        self.assertEqual(
            status,
            plugin.CRITICAL,
        )

    def test_warning_threshold(self):
        status = plugin.determine_problem_status(
            1,
            1,
            3,
        )

        self.assertEqual(
            status,
            plugin.WARNING,
        )

    def test_below_warning_is_ok(self):
        status = plugin.determine_problem_status(
            1,
            2,
            3,
        )

        self.assertEqual(
            status,
            plugin.OK,
        )

    def test_critical_threshold(self):
        status = plugin.determine_problem_status(
            3,
            1,
            3,
        )

        self.assertEqual(
            status,
            plugin.CRITICAL,
        )


class TestRestartUnitExtraction(unittest.TestCase):

    def test_extract_restart_unit(self):
        message = (
            "nginx.service: Scheduled restart job, "
            "restart counter is at 3."
        )

        self.assertEqual(
            plugin.extract_restart_unit(message),
            "nginx.service",
        )

    def test_template_service(self):
        message = (
            "worker@42.service: Scheduled restart job, "
            "restart counter is at 2."
        )

        self.assertEqual(
            plugin.extract_restart_unit(message),
            "worker@42.service",
        )

    def test_non_restart_message(self):
        message = (
            "nginx.service: Failed with result "
            "'exit-code'."
        )

        self.assertIsNone(
            plugin.extract_restart_unit(message)
        )


class TestRestartParsing(unittest.TestCase):

    JOURNAL = """
nginx.service: Scheduled restart job, restart counter is at 1.
nginx.service: Scheduled restart job, restart counter is at 2.
nginx.service: Scheduled restart job, restart counter is at 3.
backup.service: Scheduled restart job, restart counter is at 1.
backup.service: Failed with result 'exit-code'.
sshd.service: Started OpenSSH server daemon.
"""

    @patch(
        "check_systemd_health.run_command"
    )
    def test_restart_counts(self, mock_run):
        mock_run.return_value = self.JOURNAL

        counts = plugin.get_restart_counts(
            1800,
            30,
        )

        self.assertEqual(
            counts["nginx.service"],
            3,
        )

        self.assertEqual(
            counts["backup.service"],
            1,
        )

        self.assertNotIn(
            "sshd.service",
            counts,
        )

    @patch(
        "check_systemd_health.run_command"
    )
    def test_restart_include(self, mock_run):
        mock_run.return_value = self.JOURNAL

        counts = plugin.get_restart_counts(
            1800,
            30,
            includes=["nginx*"],
        )

        self.assertEqual(
            counts,
            {
                "nginx.service": 3,
            },
        )

    @patch(
        "check_systemd_health.run_command"
    )
    def test_restart_exclude(self, mock_run):
        mock_run.return_value = self.JOURNAL

        counts = plugin.get_restart_counts(
            1800,
            30,
            excludes=["nginx*"],
        )

        self.assertNotIn(
            "nginx.service",
            counts,
        )

        self.assertEqual(
            counts["backup.service"],
            1,
        )


class TestRestartThresholds(unittest.TestCase):

    def test_restart_ok(self):
        counts = {
            "nginx.service": 2,
        }

        status = plugin.determine_restart_status(
            counts,
            3,
            5,
        )

        self.assertEqual(
            status,
            plugin.OK,
        )

    def test_restart_warning(self):
        counts = {
            "nginx.service": 3,
        }

        status = plugin.determine_restart_status(
            counts,
            3,
            5,
        )

        self.assertEqual(
            status,
            plugin.WARNING,
        )

    def test_restart_critical(self):
        counts = {
            "nginx.service": 5,
        }

        status = plugin.determine_restart_status(
            counts,
            3,
            5,
        )

        self.assertEqual(
            status,
            plugin.CRITICAL,
        )

    def test_highest_service_wins(self):
        counts = {
            "nginx.service": 3,
            "backup.service": 7,
        }

        status = plugin.determine_restart_status(
            counts,
            3,
            5,
        )

        self.assertEqual(
            status,
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

    def test_warning_wins_over_ok(self):
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


class TestArgumentValidation(unittest.TestCase):

    def make_args(self):
        return argparse.Namespace(
            timeout=30,
            warning=None,
            critical=None,
            check_restarts=False,
            restart_warning=None,
            restart_critical=None,
            since=None,
        )

    def test_valid_defaults(self):
        args = self.make_args()

        plugin.validate_arguments(args)

    def test_invalid_timeout(self):
        args = self.make_args()
        args.timeout = 0

        with self.assertRaises(
            plugin.PluginError
        ):
            plugin.validate_arguments(args)

    def test_invalid_warning_critical(self):
        args = self.make_args()
        args.warning = 5
        args.critical = 3

        with self.assertRaises(
            plugin.PluginError
        ):
            plugin.validate_arguments(args)

    def test_restart_option_requires_check_restarts(self):
        args = self.make_args()
        args.since = 1800

        with self.assertRaises(
            plugin.PluginError
        ):
            plugin.validate_arguments(args)

    def test_restart_defaults(self):
        args = self.make_args()
        args.check_restarts = True

        plugin.validate_arguments(args)

        self.assertEqual(
            args.restart_warning,
            plugin.DEFAULT_RESTART_WARNING,
        )

        self.assertEqual(
            args.restart_critical,
            plugin.DEFAULT_RESTART_CRITICAL,
        )

        self.assertEqual(
            args.since,
            1800,
        )

    def test_invalid_restart_thresholds(self):
        args = self.make_args()

        args.check_restarts = True
        args.restart_warning = 5
        args.restart_critical = 3

        with self.assertRaises(
            plugin.PluginError
        ):
            plugin.validate_arguments(args)


class TestRestartSummary(unittest.TestCase):

    def test_only_threshold_violations_are_reported(self):
        counts = {
            "normal.service": 1,
            "warning.service": 3,
            "critical.service": 8,
        }

        summary = plugin.build_restart_summary(
            counts,
            3,
        )

        self.assertNotIn(
            "normal.service restarted 1 times",
            summary,
        )

        self.assertIn(
            "warning.service restarted 3 times",
            summary,
        )

        self.assertIn(
            "critical.service restarted 8 times",
            summary,
        )


class TestMain(unittest.TestCase):

    def make_args(
        self,
        *,
        warning=None,
        critical=None,
        check_restarts=False,
        restart_warning=None,
        restart_critical=None,
        since=None,
        includes=None,
        excludes=None,
        unit_type=None,
        states=None,
        verbose=0,
    ):
        return argparse.Namespace(
            exclude=excludes or [],
            include=includes or [],
            unit_type=unit_type,
            states=states,
            warning=warning,
            critical=critical,
            check_restarts=check_restarts,
            restart_warning=restart_warning,
            restart_critical=restart_critical,
            since=since,
            timeout=30,
            verbose=verbose,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    @patch(
        "check_systemd_health.get_units"
    )
    def test_main_ok(
        self,
        mock_get_units,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args()

        mock_get_state.return_value = "running"
        mock_get_units.return_value = []

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.OK,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "SYSTEMD OK",
            output,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    @patch(
        "check_systemd_health.get_units"
    )
    def test_main_failed_unit_is_critical(
        self,
        mock_get_units,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args()

        mock_get_state.return_value = "degraded"

        mock_get_units.return_value = [
            "backup.service",
        ]

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.CRITICAL,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "backup.service",
            output,
        )

        self.assertIn(
            "SYSTEMD CRITICAL",
            output,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    @patch(
        "check_systemd_health.get_units"
    )
    def test_main_threshold_warning(
        self,
        mock_get_units,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args(
            warning=1,
            critical=3,
        )

        mock_get_state.return_value = "degraded"

        mock_get_units.return_value = [
            "backup.service",
        ]

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.WARNING,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "SYSTEMD WARNING",
            output,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    @patch(
        "check_systemd_health.get_units"
    )
    def test_main_excluded_failure_is_ok(
        self,
        mock_get_units,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args(
            excludes=[
                "backup.service",
            ],
        )

        mock_get_state.return_value = "degraded"

        mock_get_units.return_value = [
            "backup.service",
        ]

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.OK,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "all matching problem units are excluded",
            output,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    @patch(
        "check_systemd_health.get_units"
    )
    @patch(
        "check_systemd_health.get_restart_counts"
    )
    def test_main_restart_warning(
        self,
        mock_restarts,
        mock_get_units,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args(
            check_restarts=True,
            restart_warning=3,
            restart_critical=5,
            since=1800,
        )

        mock_get_state.return_value = "running"
        mock_get_units.return_value = []

        mock_restarts.return_value = {
            "nginx.service": 3,
        }

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.WARNING,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "nginx.service restarted 3 times",
            output,
        )

        self.assertIn(
            "SYSTEMD WARNING",
            output,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    @patch(
        "check_systemd_health.get_units"
    )
    @patch(
        "check_systemd_health.get_restart_counts"
    )
    def test_main_restart_critical(
        self,
        mock_restarts,
        mock_get_units,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args(
            check_restarts=True,
            restart_warning=3,
            restart_critical=5,
            since=1800,
        )

        mock_get_state.return_value = "running"
        mock_get_units.return_value = []

        mock_restarts.return_value = {
            "nginx.service": 7,
        }

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.CRITICAL,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "nginx.service restarted 7 times",
            output,
        )

        self.assertIn(
            "SYSTEMD CRITICAL",
            output,
        )

    @patch(
        "check_systemd_health.parse_arguments"
    )
    @patch(
        "check_systemd_health.get_system_state"
    )
    def test_main_command_error_is_unknown(
        self,
        mock_get_state,
        mock_parse,
    ):
        mock_parse.return_value = self.make_args()

        mock_get_state.side_effect = (
            plugin.PluginError(
                "systemctl failed"
            )
        )

        with patch(
            "builtins.print"
        ) as mock_print:
            status = plugin.main()

        self.assertEqual(
            status,
            plugin.UNKNOWN,
        )

        output = " ".join(
            str(call)
            for call in mock_print.call_args_list
        )

        self.assertIn(
            "SYSTEMD UNKNOWN",
            output,
        )

        self.assertIn(
            "systemctl failed",
            output,
        )


if __name__ == "__main__":
    unittest.main()
