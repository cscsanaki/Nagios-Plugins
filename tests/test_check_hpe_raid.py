#!/usr/bin/env python3

import importlib.util
import io
import pathlib
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

PLUGIN = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "check_hpe_raid.py"

spec = importlib.util.spec_from_file_location("check_hpe_raid", PLUGIN)
hpe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hpe)


CONTROLLER_OK = """
HPE Smart Array P408i-a SR Gen10 in Slot 0 (Embedded)

   Controller Status: OK
"""

ARRAYS_OK = """
array A (OK)

   logicaldrive 1 (447.1 GB, RAID 1, OK)

array B (OK)

   logicaldrive 2 (1.8 TB, RAID 1, OK)
"""


class TestControllerParsing(unittest.TestCase):

    def test_controller_identity(self):
        result = hpe.controllers(CONTROLLER_OK)

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["model"],
            "HPE Smart Array P408i-a SR Gen10",
        )
        self.assertEqual(result[0]["slot"], "0")
        self.assertEqual(result[0]["status"], "OK")

    def test_multiple_controllers(self):
        output = """
HPE Smart Array P408i-a SR Gen10 in Slot 0 (Embedded)
   Controller Status: OK

HPE Smart Array P816i-a SR Gen10 in Slot 1
   Controller Status: OK
"""
        result = hpe.controllers(output)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["slot"], "0")
        self.assertEqual(result[1]["slot"], "1")

    def test_missing_controller_status(self):
        output = """
HPE Smart Array P408i-a SR Gen10 in Slot 0 (Embedded)
"""
        result = hpe.controllers(output)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["status"])


class TestArrayParsing(unittest.TestCase):

    def test_two_arrays_are_found(self):
        result = hpe.arrays(ARRAYS_OK)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "A")
        self.assertEqual(result[1]["name"], "B")

    def test_array_status(self):
        result = hpe.arrays(ARRAYS_OK)

        self.assertEqual(result[0]["status"], "OK")
        self.assertEqual(result[1]["status"], "OK")

    def test_logical_drives_are_found(self):
        result = hpe.arrays(ARRAYS_OK)

        self.assertEqual(result[0]["lds"][0]["id"], "1")
        self.assertEqual(result[0]["lds"][0]["status"], "OK")

        self.assertEqual(result[1]["lds"][0]["id"], "2")
        self.assertEqual(result[1]["lds"][0]["status"], "OK")

    def test_failed_array_status(self):
        output = ARRAYS_OK.replace(
            "array A (OK)",
            "array A (Failed)",
        )

        result = hpe.arrays(output)

        self.assertEqual(result[0]["status"], "Failed")

    def test_array_without_explicit_status_defaults_to_ok(self):
        output = """
array A

   logicaldrive 1 (447.1 GB, RAID 1, OK)
"""
        result = hpe.arrays(output)

        self.assertEqual(result[0]["status"], "OK")


class TestLogicalDriveSeverity(unittest.TestCase):

    def test_ok(self):
        self.assertEqual(hpe.ldsev("OK"), hpe.OK)

    def test_disabled_is_ok(self):
        self.assertEqual(hpe.ldsev("Disabled"), hpe.OK)

    def test_rebuild_is_warning(self):
        self.assertEqual(hpe.ldsev("Rebuild"), hpe.WARNING)

    def test_rebuilding_is_warning(self):
        self.assertEqual(hpe.ldsev("Rebuilding"), hpe.WARNING)

    def test_recover_is_warning(self):
        self.assertEqual(hpe.ldsev("Recover"), hpe.WARNING)

    def test_recovering_is_warning(self):
        self.assertEqual(hpe.ldsev("Recovering"), hpe.WARNING)

    def test_failed_is_critical(self):
        self.assertEqual(hpe.ldsev("Failed"), hpe.CRITICAL)

    def test_interim_recovery_mode_is_critical(self):
        self.assertEqual(
            hpe.ldsev("Interim Recovery Mode"),
            hpe.CRITICAL,
        )

    def test_unknown_status_is_critical(self):
        self.assertEqual(
            hpe.ldsev("Something Unexpected"),
            hpe.CRITICAL,
        )


class TestCommandHandling(unittest.TestCase):

    @patch.object(hpe.subprocess, "run")
    def test_successful_command(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["ssacli"],
            0,
            stdout="hello\n",
            stderr="",
        )

        result = hpe.run(["ssacli"], 30)

        self.assertEqual(result, "hello\n")

    @patch.object(hpe.subprocess, "run")
    def test_timeout_raises_check_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            ["ssacli"],
            30,
        )

        with self.assertRaises(hpe.CheckError):
            hpe.run(["ssacli"], 30)

    @patch.object(hpe.subprocess, "run")
    def test_nonzero_exit_raises_check_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["ssacli"],
            1,
            stdout="",
            stderr="Controller error",
        )

        with self.assertRaises(hpe.CheckError):
            hpe.run(["ssacli"], 30)


class TestSsacliDiscovery(unittest.TestCase):

    def test_explicit_missing_ssacli(self):
        with self.assertRaises(hpe.CheckError):
            hpe.resolve("/definitely/not/here/ssacli")

    @patch.object(hpe.shutil, "which", return_value="/usr/sbin/ssacli")
    def test_path_discovery(self, mock_which):
        self.assertEqual(
            hpe.resolve(None),
            "/usr/sbin/ssacli",
        )


class TestMainStatusLogic(unittest.TestCase):

    def run_main(self, controller_output, logical_outputs):
        def fake_run(command, timeout):
            if command[1:] == [
                "controller",
                "all",
                "show",
                "status",
            ]:
                return controller_output

            if (
                len(command) >= 6
                and command[1] == "controller"
                and command[3:] == [
                    "logicaldrive",
                    "all",
                    "show",
                ]
            ):
                slot = command[2].split("=", 1)[1]
                return logical_outputs[slot]

            raise AssertionError(
                f"Unexpected command: {command}"
            )

        stdout = io.StringIO()

        with patch.object(
            hpe,
            "resolve",
            return_value="/usr/sbin/ssacli",
        ), patch.object(
            hpe,
            "run",
            side_effect=fake_run,
        ), patch.object(
            sys,
            "argv",
            ["check_hpe_raid.py"],
        ), redirect_stdout(stdout):

            rc = hpe.main()

        return rc, stdout.getvalue().strip()

    def test_healthy_system_returns_ok(self):
        rc, output = self.run_main(
            CONTROLLER_OK,
            {"0": ARRAYS_OK},
        )

        self.assertEqual(rc, hpe.OK)
        self.assertIn("HPE RAID OK:", output)
        self.assertIn(
            "HPE Smart Array P408i-a SR Gen10[OK]",
            output,
        )
        self.assertIn(
            "Array A(OK)[LUN1:OK]",
            output,
        )
        self.assertIn(
            "Array B(OK)[LUN2:OK]",
            output,
        )
        self.assertIn("controllers=1", output)
        self.assertIn("arrays=2", output)
        self.assertIn("logical_drives=2", output)
        self.assertIn("problems=0", output)

    def test_rebuild_returns_warning(self):
        logical = ARRAYS_OK.replace(
            "RAID 1, OK",
            "RAID 1, Rebuild",
            1,
        )

        rc, output = self.run_main(
            CONTROLLER_OK,
            {"0": logical},
        )

        self.assertEqual(rc, hpe.WARNING)
        self.assertIn("HPE RAID WARNING:", output)
        self.assertIn("LUN1:Rebuild", output)
        self.assertIn("problems=1", output)

    def test_failed_logical_drive_returns_critical(self):
        logical = ARRAYS_OK.replace(
            "RAID 1, OK",
            "RAID 1, Failed",
            1,
        )

        rc, output = self.run_main(
            CONTROLLER_OK,
            {"0": logical},
        )

        self.assertEqual(rc, hpe.CRITICAL)
        self.assertIn("HPE RAID CRITICAL:", output)
        self.assertIn("LUN1:Failed", output)
        self.assertIn("problems=1", output)

    def test_failed_array_returns_critical(self):
        logical = ARRAYS_OK.replace(
            "array A (OK)",
            "array A (Failed)",
        )

        rc, output = self.run_main(
            CONTROLLER_OK,
            {"0": logical},
        )

        self.assertEqual(rc, hpe.CRITICAL)
        self.assertIn("Array A(Failed)", output)
        self.assertIn("problems=1", output)

    def test_failed_controller_returns_critical(self):
        controller = CONTROLLER_OK.replace(
            "Controller Status: OK",
            "Controller Status: Failed",
        )

        rc, output = self.run_main(
            controller,
            {"0": ARRAYS_OK},
        )

        self.assertEqual(rc, hpe.CRITICAL)
        self.assertIn(
            "HPE Smart Array P408i-a SR Gen10[Failed]",
            output,
        )
        self.assertIn("problems=1", output)

    def test_missing_controller_status_returns_unknown(self):
        controller = """
HPE Smart Array P408i-a SR Gen10 in Slot 0 (Embedded)
"""

        rc, output = self.run_main(
            controller,
            {"0": ARRAYS_OK},
        )

        self.assertEqual(rc, hpe.UNKNOWN)
        self.assertIn("HPE RAID UNKNOWN:", output)
        self.assertIn("[UNKNOWN]", output)

    def test_no_controller_returns_unknown(self):
        rc, output = self.run_main(
            "",
            {},
        )

        self.assertEqual(rc, hpe.UNKNOWN)
        self.assertIn(
            "no HPE Smart Array controllers found",
            output,
        )

    def test_no_arrays_returns_unknown(self):
        rc, output = self.run_main(
            CONTROLLER_OK,
            {"0": ""},
        )

        self.assertEqual(rc, hpe.UNKNOWN)
        self.assertIn("HPE RAID UNKNOWN:", output)
        self.assertIn("arrays=0", output)
        self.assertIn("logical_drives=0", output)
        self.assertIn("problems=1", output)

    def test_critical_is_not_downgraded_by_warning(self):
        logical = """
array A (OK)

   logicaldrive 1 (447.1 GB, RAID 1, Failed)

array B (OK)

   logicaldrive 2 (1.8 TB, RAID 1, Rebuild)
"""

        rc, output = self.run_main(
            CONTROLLER_OK,
            {"0": logical},
        )

        self.assertEqual(rc, hpe.CRITICAL)
        self.assertIn("HPE RAID CRITICAL:", output)
        self.assertIn("problems=2", output)

    def test_multiple_controllers(self):
        controllers = """
HPE Smart Array P408i-a SR Gen10 in Slot 0 (Embedded)
   Controller Status: OK

HPE Smart Array P816i-a SR Gen10 in Slot 1
   Controller Status: OK
"""

        second = """
array C (OK)

   logicaldrive 3 (2.0 TB, RAID 5, OK)
"""

        rc, output = self.run_main(
            controllers,
            {
                "0": ARRAYS_OK,
                "1": second,
            },
        )

        self.assertEqual(rc, hpe.OK)
        self.assertIn("controllers=2", output)
        self.assertIn("arrays=3", output)
        self.assertIn("logical_drives=3", output)
        self.assertIn("problems=0", output)


class TestMainErrors(unittest.TestCase):

    def run_error_main(self, error):
        stdout = io.StringIO()

        with patch.object(
            hpe,
            "resolve",
            side_effect=error,
        ), patch.object(
            sys,
            "argv",
            ["check_hpe_raid.py"],
        ), redirect_stdout(stdout):

            rc = hpe.main()

        return rc, stdout.getvalue().strip()

    def test_missing_ssacli_returns_unknown(self):
        rc, output = self.run_error_main(
            hpe.CheckError("ssacli executable not found")
        )

        self.assertEqual(rc, hpe.UNKNOWN)
        self.assertEqual(
            output,
            "HPE RAID UNKNOWN: ssacli executable not found",
        )


if __name__ == "__main__":
    unittest.main()
