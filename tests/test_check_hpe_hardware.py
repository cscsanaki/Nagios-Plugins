import importlib.util
import os
import pathlib
import subprocess
import unittest
from unittest.mock import patch

PLUGIN = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "check_hpe_hardware.py"
spec = importlib.util.spec_from_file_location("check_hpe_hardware", PLUGIN)
hpe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hpe)


class TestSystemInfoParsing(unittest.TestCase):

    def test_ok_gen10_system_info(self):
        output = """
Model: HPE ProLiant DL380 Gen10
Serial Number: CZ282701B5
Bios Version: U30 v3.70 (08/19/2026)
iLO 5 : 3.21 Jul 30 2026
Health: OK
"""
        data = hpe.parse_system_info(output)

        self.assertEqual(data["model"], "HPE ProLiant DL380 Gen10")
        self.assertEqual(data["serial"], "CZ282701B5")
        self.assertEqual(data["bios"], "U30 v3.70 (08/19/2026)")
        self.assertEqual(data["ilo"], "iLO 5: 3.21 Jul 30 2026")
        self.assertEqual(data["severity"], hpe.SEVERITY_OK)

    def test_ok_gen11_system_info(self):
        output = """
System:
Model: HPE ProLiant DL380 Gen11
Bios Version: U54 v3.00 (08/20/2026)
Serial Number: CZ2D2M083G

Firmware:
iLO 6 : 1.78 Jul 29 2026
System ROM : U54 v3.00 (08/20/2026)
Redundant System ROM : U54 v2.94 (06/25/2026)

Processor:
Processor 1:
        Model: INTEL(R) XEON(R) SILVER 4510
        Health: OK
        State: Enabled
"""
        data = hpe.parse_system_info(output)

        self.assertEqual(data["model"], "HPE ProLiant DL380 Gen11")
        self.assertEqual(data["serial"], "CZ2D2M083G")
        self.assertEqual(data["bios"], "U54 v3.00 (08/20/2026)")
        self.assertEqual(data["ilo"], "iLO 6: 1.78 Jul 29 2026")
        self.assertEqual(data["severity"], hpe.SEVERITY_OK)

    def test_processor_model_does_not_replace_server_model(self):
        output = """
Model: HPE ProLiant DL380 Gen11
Processor 1:
        Model: INTEL(R) XEON(R) SILVER 4510
"""
        data = hpe.parse_system_info(output)

        self.assertEqual(data["model"], "HPE ProLiant DL380 Gen11")

    def test_redundant_rom_does_not_replace_active_bios(self):
        output = """
Bios Version: U54 v3.00 (08/20/2026)
System ROM : U54 v3.00 (08/20/2026)
Redundant System ROM : U54 v2.94 (06/25/2026)
"""
        data = hpe.parse_system_info(output)

        self.assertEqual(data["bios"], "U54 v3.00 (08/20/2026)")

    def test_system_rom_is_used_when_bios_version_is_missing(self):
        output = """
System ROM : U30 v3.70 (08/19/2026)
Redundant System ROM : U30 v3.68 (07/23/2026)
"""
        data = hpe.parse_system_info(output)

        self.assertEqual(data["bios"], "U30 v3.70 (08/19/2026)")

    def test_ilo5_parsing(self):
        data = hpe.parse_system_info("iLO 5 : 3.21 Jul 30 2026")
        self.assertEqual(data["ilo"], "iLO 5: 3.21 Jul 30 2026")

    def test_ilo6_parsing(self):
        data = hpe.parse_system_info("iLO 6 : 1.78 Jul 29 2026")
        self.assertEqual(data["ilo"], "iLO 6: 1.78 Jul 29 2026")

    def test_warning_state(self):
        data = hpe.parse_system_info("Health: Degraded")
        self.assertEqual(data["severity"], hpe.SEVERITY_WARNING)

    def test_critical_state(self):
        data = hpe.parse_system_info("Health: Critical")
        self.assertEqual(data["severity"], hpe.SEVERITY_CRITICAL)

    def test_critical_is_not_downgraded_by_later_warning(self):
        output = """
Health: Critical
Status: Warning
"""
        data = hpe.parse_system_info(output)
        self.assertEqual(data["severity"], hpe.SEVERITY_CRITICAL)


class TestIloRestDiscovery(unittest.TestCase):

    def test_explicit_ilorest_path_is_used(self):
        with patch.object(hpe.os.path, "isfile", return_value=True), \
             patch.object(hpe.os, "access", return_value=True):
            result = hpe.resolve_ilorest("/custom/bin/ilorest")

        self.assertEqual(result, "/custom/bin/ilorest")

    def test_opt_ilorest_is_auto_detected(self):
        def fake_isfile(path):
            return path == "/opt/ilorest/bin/ilorest"

        with patch.object(hpe.os.path, "isfile", side_effect=fake_isfile), \
             patch.object(hpe.os, "access", return_value=True):
            result = hpe.resolve_ilorest()

        self.assertEqual(result, "/opt/ilorest/bin/ilorest")

    def test_usr_sbin_ilorest_is_auto_detected(self):
        def fake_isfile(path):
            return path == "/usr/sbin/ilorest"

        with patch.object(hpe.os.path, "isfile", side_effect=fake_isfile), \
             patch.object(hpe.os, "access", return_value=True):
            result = hpe.resolve_ilorest()

        self.assertEqual(result, "/usr/sbin/ilorest")

    def test_path_fallback_is_used(self):
        with patch.object(hpe.os.path, "isfile") as mock_isfile, \
             patch.object(hpe.os, "access", return_value=True), \
             patch.object(hpe.shutil, "which", return_value="/custom/path/ilorest"):

            mock_isfile.side_effect = (
                lambda path: path == "/custom/path/ilorest"
            )

            result = hpe.resolve_ilorest()

        self.assertEqual(result, "/custom/path/ilorest")

    def test_missing_ilorest_raises_command_error(self):
        with patch.object(hpe.os.path, "isfile", return_value=False), \
             patch.object(hpe.shutil, "which", return_value=None):

            with self.assertRaises(hpe.CommandError):
                hpe.resolve_ilorest()


class TestDefaults(unittest.TestCase):

    def test_default_timeout_is_60_seconds(self):
        self.assertEqual(hpe.DEFAULT_TIMEOUT, 60)

    def test_expected_ilorest_candidates(self):
        self.assertIn(
            "/opt/ilorest/bin/ilorest",
            hpe.DEFAULT_ILOREST_CANDIDATES,
        )
        self.assertIn(
            "/usr/sbin/ilorest",
            hpe.DEFAULT_ILOREST_CANDIDATES,
        )
        self.assertIn(
            "/usr/bin/ilorest",
            hpe.DEFAULT_ILOREST_CANDIDATES,
        )
        self.assertIn(
            "/usr/local/bin/ilorest",
            hpe.DEFAULT_ILOREST_CANDIDATES,
        )


class FakeSession:
    def __init__(
        self,
        systeminfo="",
        iml="",
        login_error=None,
        system_error=None,
    ):
        self.systeminfo = systeminfo
        self.iml = iml
        self.login_error = login_error
        self.system_error = system_error
        self.logged_in = False

    def login(self):
        if self.login_error:
            raise hpe.CommandError(self.login_error)
        self.logged_in = True

    def run(self, args):
        if args == ["systeminfo"]:
            if self.system_error:
                raise hpe.CommandError(self.system_error)
            return self.systeminfo

        if args == ["iml"]:
            return self.iml

        if args == ["logout"]:
            self.logged_in = False
            return ""

        return ""

    def logout(self):
        self.logged_in = False


class TestMainStatusLogic(unittest.TestCase):

    def args(self):
        return type(
            "Args",
            (),
            {
                "timeout": 60,
                "ilorest": None,
                "verbose": 0,
            },
        )()

    def run_main(self, session):
        with patch.object(hpe, "build_parser") as parser, \
             patch.object(
                 hpe,
                 "resolve_ilorest",
                 return_value="/opt/ilorest/bin/ilorest",
             ), \
             patch.object(
                 hpe,
                 "IloRestSession",
                 return_value=session,
             ), \
             patch.object(
                 hpe,
                 "get_local_bios_fallback",
                 return_value="Fallback BIOS",
             ):

            parser.return_value.parse_args.return_value = self.args()
            return hpe.main()

    def test_ok_returns_zero(self):
        session = FakeSession(
            systeminfo="""
Model: HPE ProLiant DL380 Gen11
Serial Number: TEST123
Bios Version: U54 v3.00
iLO 6 : 1.78
Health: OK
"""
        )

        self.assertEqual(self.run_main(session), hpe.OK)

    def test_warning_returns_one(self):
        session = FakeSession(
            systeminfo="Health: Degraded",
            iml="Power warning",
        )

        self.assertEqual(self.run_main(session), hpe.WARNING)

    def test_critical_returns_two(self):
        session = FakeSession(
            systeminfo="Health: Critical",
            iml="Memory failure",
        )

        self.assertEqual(self.run_main(session), hpe.CRITICAL)

    def test_login_failure_returns_unknown(self):
        session = FakeSession(login_error="CHIF unavailable")
        self.assertEqual(self.run_main(session), hpe.UNKNOWN)

    def test_systeminfo_failure_returns_unknown(self):
        session = FakeSession(system_error="systeminfo failed")
        self.assertEqual(self.run_main(session), hpe.UNKNOWN)

    def test_empty_systeminfo_returns_unknown(self):
        session = FakeSession(systeminfo="")
        self.assertEqual(self.run_main(session), hpe.UNKNOWN)


class TestCommandHandling(unittest.TestCase):

    @patch.object(hpe.subprocess, "run")
    def test_timeout_raises_command_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            ["ilorest"],
            60,
        )

        with self.assertRaises(hpe.CommandError):
            hpe.run_command(["ilorest", "login"], 60)

    @patch.object(hpe.subprocess, "run")
    def test_nonzero_exit_raises_command_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["ilorest"],
            34,
            stdout="",
            stderr="Chif driver not found",
        )

        with self.assertRaises(hpe.CommandError):
            hpe.run_command(["ilorest", "login"], 60)


class TestImlParsing(unittest.TestCase):

    def test_last_three_iml_entries(self):
        session = FakeSession(
            iml="""
IML
Severity
Event one
Event two
Event three
Event four
"""
        )

        result = hpe.get_latest_iml_logs(session)

        self.assertIn(
            "Event two -> Event three -> Event four",
            result,
        )

    def test_ansi_is_removed_from_iml(self):
        session = FakeSession(
            iml="\x1b[1;31mMemory failure\x1b[0m"
        )

        result = hpe.get_latest_iml_logs(session)

        self.assertIn("Memory failure", result)
        self.assertNotIn("\x1b", result)


if __name__ == "__main__":
    unittest.main()
