import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import patch

PLUGIN = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "check_hpe_hardware.py"
spec = importlib.util.spec_from_file_location("check_hpe_hardware", PLUGIN)
hpe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hpe)


class TestSystemInfoParsing(unittest.TestCase):

    def test_ok_system_info(self):
        output = """
Model: HPE ProLiant DL380 Gen10
Serial Number: CZ282701B5
Bios Version: U30 v3.68 (07/23/2026)
iLO 5 : 3.21 Jul 30 2026
Health: OK
"""
        data = hpe.parse_system_info(output)
        self.assertEqual(data["model"], "HPE ProLiant DL380 Gen10")
        self.assertEqual(data["serial"], "CZ282701B5")
        self.assertEqual(data["bios"], "U30 v3.68 (07/23/2026)")
        self.assertEqual(data["ilo"], "iLO 5: 3.21 Jul 30 2026")
        self.assertEqual(data["severity"], hpe.SEVERITY_OK)

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

    def test_processor_model_does_not_replace_server_model(self):
        output = """
Model: HPE ProLiant DL380 Gen10
Processor Model: Intel(R) Xeon(R) Gold
"""
        data = hpe.parse_system_info(output)
        self.assertEqual(data["model"], "HPE ProLiant DL380 Gen10")


class FakeSession:
    def __init__(self, systeminfo="", iml="", login_error=None, system_error=None):
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
        return type("Args", (), {
            "timeout": 15,
            "ilorest": "/usr/sbin/ilorest",
            "verbose": 0,
        })()

    def run_main(self, session):
        with patch.object(hpe, "build_parser") as parser, \
             patch.object(hpe, "resolve_ilorest", return_value="/usr/sbin/ilorest"), \
             patch.object(hpe, "IloRestSession", return_value=session), \
             patch.object(hpe, "get_local_bios_fallback", return_value="Fallback BIOS"):
            parser.return_value.parse_args.return_value = self.args()
            return hpe.main()

    def test_ok_returns_zero(self):
        session = FakeSession(systeminfo="""
Model: HPE ProLiant DL380 Gen10
Serial Number: TEST123
Bios Version: U30 v3.68
iLO 5 : 3.21
Health: OK
""")
        self.assertEqual(self.run_main(session), hpe.OK)

    def test_warning_returns_one(self):
        session = FakeSession(systeminfo="Health: Degraded", iml="Power warning")
        self.assertEqual(self.run_main(session), hpe.WARNING)

    def test_critical_returns_two(self):
        session = FakeSession(systeminfo="Health: Critical", iml="Memory failure")
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
        mock_run.side_effect = subprocess.TimeoutExpired(["ilorest"], 15)
        with self.assertRaises(hpe.CommandError):
            hpe.run_command(["ilorest", "login"], 15)

    @patch.object(hpe.subprocess, "run")
    def test_nonzero_exit_raises_command_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            ["ilorest"], 34, stdout="", stderr="Chif driver not found"
        )
        with self.assertRaises(hpe.CommandError):
            hpe.run_command(["ilorest", "login"], 15)


class TestImlParsing(unittest.TestCase):

    def test_last_three_iml_entries(self):
        session = FakeSession(iml="""
IML
Severity
Event one
Event two
Event three
Event four
""")
        result = hpe.get_latest_iml_logs(session)
        self.assertIn("Event two -> Event three -> Event four", result)

    def test_ansi_is_removed_from_iml(self):
        session = FakeSession(iml="\x1b[1;31mMemory failure\x1b[0m")
        result = hpe.get_latest_iml_logs(session)
        self.assertIn("Memory failure", result)
        self.assertNotIn("\x1b", result)


if __name__ == "__main__":
    unittest.main()
