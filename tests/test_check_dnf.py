import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import patch


PLUGIN = pathlib.Path(__file__).resolve().parents[1] / "plugins" / "check_dnf.py"

spec = importlib.util.spec_from_file_location("check_dnf", PLUGIN)
check_dnf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_dnf)


class TestPackageParsing(unittest.TestCase):

    def test_no_updates(self):
        self.assertEqual(check_dnf.DnfCheck.package_names(""), set())

    def test_non_security_updates(self):
        output = """
containernetworking-plugins.x86_64        1:1.9.0-4.el9_8        appstream
podman.x86_64                             6:5.8.2-7.el9_8        appstream
rsyslog.x86_64                            8.2510.0-2.el9_8.2     appstream
"""
        self.assertEqual(
            check_dnf.DnfCheck.package_names(output),
            {
                "containernetworking-plugins.x86_64",
                "podman.x86_64",
                "rsyslog.x86_64",
            },
        )

    def test_multiple_architectures(self):
        output = """
package1.x86_64    1.0-1.el9    baseos
package2.noarch    2.0-1.el9    appstream
package3.aarch64   3.0-1.el9    baseos
package4.ppc64le   4.0-1.el9    baseos
package5.s390x     5.0-1.el9    baseos
package6.i686      6.0-1.el9    appstream
"""
        packages = check_dnf.DnfCheck.package_names(output)

        self.assertEqual(len(packages), 6)
        self.assertIn("package1.x86_64", packages)
        self.assertIn("package2.noarch", packages)
        self.assertIn("package3.aarch64", packages)
        self.assertIn("package4.ppc64le", packages)
        self.assertIn("package5.s390x", packages)
        self.assertIn("package6.i686", packages)

    def test_security_status_lines_are_not_packages(self):
        output = """
Security: kernel-core-5.14.0-687.49.1.el9_8.x86_64 is an installed security update
Security: kernel-core-5.14.0-687.46.1.el9_8.x86_64 is the currently running version
"""
        self.assertEqual(check_dnf.DnfCheck.package_names(output), set())

    def test_duplicate_packages_count_once(self):
        output = """
podman.x86_64    6:5.8.2-7.el9_8    appstream
podman.x86_64    6:5.8.2-7.el9_8    appstream
"""
        self.assertEqual(
            check_dnf.DnfCheck.package_names(output),
            {"podman.x86_64"},
        )


class TestKernelSecurityStatus(unittest.TestCase):

    def test_kernel_security_status(self):
        output = """
Security: kernel-core-5.14.0-687.49.1.el9_8.x86_64 is an installed security update
Security: kernel-core-5.14.0-687.46.1.el9_8.x86_64 is the currently running version
"""
        result = check_dnf.DnfCheck.kernel_security_status(output)

        self.assertEqual(
            result,
            (
                "5.14.0-687.49.1.el9_8.x86_64",
                "5.14.0-687.46.1.el9_8.x86_64",
            ),
        )

    def test_kernel_security_status_missing(self):
        self.assertIsNone(
            check_dnf.DnfCheck.kernel_security_status(
                "Last metadata expiration check: 0:10:00 ago"
            )
        )


class TestCommandExecution(unittest.TestCase):

    def make_checker(self):
        args = type(
            "Args",
            (),
            {
                "cache_only": False,
                "enablerepo": [],
                "disablerepo": [],
                "config": None,
                "timeout": 120,
                "verbose": 0,
                "no_warn_on_lock": False,
            },
        )()

        with patch.object(check_dnf, "find_dnf", return_value="/usr/bin/dnf"):
            return check_dnf.DnfCheck(args)

    @patch.object(check_dnf.subprocess, "run")
    def test_dnf_return_code_zero(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["dnf"],
            returncode=0,
            stdout="",
        )

        checker = self.make_checker()
        rc, output = checker.run(
            ["/usr/bin/dnf", "-q", "check-update"],
            valid_codes=(0, 100),
        )

        self.assertEqual(rc, 0)
        self.assertEqual(output, "")

    @patch.object(check_dnf.subprocess, "run")
    def test_dnf_return_code_100(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["dnf"],
            returncode=100,
            stdout="podman.x86_64 6:5.8.2-7.el9_8 appstream\n",
        )

        checker = self.make_checker()
        rc, _ = checker.run(
            ["/usr/bin/dnf", "-q", "check-update"],
            valid_codes=(0, 100),
        )

        self.assertEqual(rc, 100)

    @patch.object(check_dnf.subprocess, "run")
    def test_dnf_failure_returns_unknown(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["dnf"],
            returncode=1,
            stdout="Failed to download metadata",
        )

        checker = self.make_checker()

        with self.assertRaises(SystemExit) as ctx:
            checker.run(
                ["/usr/bin/dnf", "-q", "check-update"],
                valid_codes=(0, 100),
            )

        self.assertEqual(ctx.exception.code, check_dnf.UNKNOWN)

    @patch.object(check_dnf.subprocess, "run")
    def test_timeout_returns_unknown(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["/usr/bin/dnf"],
            timeout=120,
        )

        checker = self.make_checker()

        with self.assertRaises(SystemExit) as ctx:
            checker.run(
                ["/usr/bin/dnf", "-q", "check-update"],
                valid_codes=(0, 100),
            )

        self.assertEqual(ctx.exception.code, check_dnf.UNKNOWN)

class TestNagiosStatusLogic(unittest.TestCase):

    def make_args(self, **overrides):
        defaults = {
            "all_updates": False,
            "warn_on_any_update": False,
            "cache_only": False,
            "enablerepo": [],
            "disablerepo": [],
            "config": None,
            "no_warn_on_lock": False,
            "timeout": 120,
            "warning_security": 0,
            "critical_security": 1,
            "no_reboot_check": False,
            "no_reboot_critical": False,
            "verbose": 0,
        }
        defaults.update(overrides)
        return type("Args", (), defaults)()

    def make_checker(self, **overrides):
        args = self.make_args(**overrides)

        with patch.object(
            check_dnf,
            "find_dnf",
            return_value="/usr/bin/dnf",
        ):
            return check_dnf.DnfCheck(args)

    def run_execute(
        self,
        all_packages=None,
        security_packages=None,
        reboot=False,
        **args,
    ):
        checker = self.make_checker(**args)

        all_packages = set(all_packages or [])
        security_packages = set(security_packages or [])

        all_output = ""
        security_output = ""

        with patch.object(
            checker,
            "check_update",
            side_effect=[
                (all_packages, all_output),
                (security_packages, security_output),
            ],
        ), patch.object(
            checker,
            "reboot_required",
            return_value=reboot,
        ), self.assertRaises(SystemExit) as ctx:
            checker.execute()

        return ctx.exception.code

    def test_no_updates_no_reboot_is_ok(self):
        status = self.run_execute()

        self.assertEqual(status, check_dnf.OK)

    def test_non_security_updates_are_ok_by_default(self):
        status = self.run_execute(
            all_packages={
                "podman.x86_64",
                "rsyslog.x86_64",
                "rsyslog-gnutls.x86_64",
            }
        )

        self.assertEqual(status, check_dnf.OK)

    def test_non_security_updates_can_warn(self):
        status = self.run_execute(
            all_packages={
                "podman.x86_64",
                "rsyslog.x86_64",
            },
            warn_on_any_update=True,
        )

        self.assertEqual(status, check_dnf.WARNING)

    def test_security_update_is_critical(self):
        status = self.run_execute(
            all_packages={"podman.x86_64"},
            security_packages={"podman.x86_64"},
        )

        self.assertEqual(status, check_dnf.CRITICAL)

    def test_security_and_non_security_updates_are_critical(self):
        status = self.run_execute(
            all_packages={
                "podman.x86_64",
                "rsyslog.x86_64",
            },
            security_packages={"podman.x86_64"},
        )

        self.assertEqual(status, check_dnf.CRITICAL)

    def test_reboot_required_is_critical(self):
        status = self.run_execute(reboot=True)

        self.assertEqual(status, check_dnf.CRITICAL)

    def test_reboot_can_be_non_critical(self):
        status = self.run_execute(
            reboot=True,
            no_reboot_critical=True,
        )

        self.assertEqual(status, check_dnf.OK)

    def test_all_updates_makes_normal_update_critical(self):
        status = self.run_execute(
            all_packages={"rsyslog.x86_64"},
            all_updates=True,
        )

        self.assertEqual(status, check_dnf.CRITICAL)

    def test_security_critical_takes_priority_over_warning(self):
        status = self.run_execute(
            all_packages={
                "podman.x86_64",
                "rsyslog.x86_64",
            },
            security_packages={"podman.x86_64"},
            warn_on_any_update=True,
        )

        self.assertEqual(status, check_dnf.CRITICAL)

    def test_custom_security_warning_threshold(self):
        status = self.run_execute(
            all_packages={"pkg1.x86_64"},
            security_packages={"pkg1.x86_64"},
            warning_security=1,
            critical_security=2,
        )

        self.assertEqual(status, check_dnf.WARNING)

    def test_custom_security_critical_threshold(self):
        status = self.run_execute(
            all_packages={
                "pkg1.x86_64",
                "pkg2.x86_64",
            },
            security_packages={
                "pkg1.x86_64",
                "pkg2.x86_64",
            },
            warning_security=1,
            critical_security=2,
        )

        self.assertEqual(status, check_dnf.CRITICAL)

if __name__ == "__main__":
    unittest.main()
