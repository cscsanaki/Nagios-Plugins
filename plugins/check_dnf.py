#!/usr/bin/env python3
"""
check_dnf.py - Nagios/Icinga plugin for monitoring DNF package updates.

Copyright (c) 2026 Csanaki Csaba <cscsanaki@gmail.com>
SPDX-License-Identifier: MIT

Designed for modern DNF-based RHEL-compatible distributions, including
Rocky Linux, AlmaLinux and Red Hat Enterprise Linux.

Nagios exit codes:
    0 OK
    1 WARNING
    2 CRITICAL
    3 UNKNOWN
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from typing import List, Optional, Sequence, Tuple

__version__ = "1.2.0"

OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
DEFAULT_TIMEOUT = 120


def finish(status: int, message: str) -> None:
    labels = {
        OK: "OK",
        WARNING: "WARNING",
        CRITICAL: "CRITICAL",
        UNKNOWN: "UNKNOWN",
    }
    label = labels.get(status, "UNKNOWN")
    print(f"DNF {label}: {message}")
    raise SystemExit(status if status in labels else UNKNOWN)


def find_dnf() -> str:
    """Return the DNF executable path or exit UNKNOWN."""
    for candidate in ("/usr/bin/dnf", "/usr/bin/dnf5"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    candidate = shutil.which("dnf") or shutil.which("dnf5")
    if candidate:
        return candidate

    finish(UNKNOWN, "dnf executable not found")
    raise AssertionError("unreachable")


def clean_message(text: str, max_len: int = 600) -> str:
    """Turn multiline command output into a compact Nagios-friendly message."""
    text = " ".join(line.strip() for line in text.splitlines() if line.strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


class DnfCheck:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.dnf = find_dnf()

    def debug(self, level: int, message: str) -> None:
        if self.args.verbose >= level:
            print(f"DEBUG{level}: {message}")

    def common_args(self) -> List[str]:
        args: List[str] = []

        if self.args.cache_only:
            args.append("-C")

        for repo in self.args.enablerepo:
            args.append(f"--enablerepo={repo}")

        for repo in self.args.disablerepo:
            args.append(f"--disablerepo={repo}")

        if self.args.config:
            args.append(f"--config={self.args.config}")

        return args

    def run(self, command: Sequence[str], valid_codes: Sequence[int] = (0,)) -> Tuple[int, str]:
        env = os.environ.copy()
        env["LANG"] = "C"
        env["LC_ALL"] = "C"

        cmd = list(command)
        self.debug(2, "running command: " + " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=self.args.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            finish(
                UNKNOWN,
                f"command exceeded timeout ({self.args.timeout}s): {' '.join(cmd)}",
            )
        except OSError as exc:
            finish(UNKNOWN, f"failed to execute {cmd[0]}: {exc}")

        output = result.stdout or ""
        self.debug(3, f"return code: {result.returncode}\n{output.rstrip()}")

        if result.returncode not in valid_codes:
            low = output.lower()

            if "another app is currently holding the dnf lock" in low or \
               "another copy is running" in low or \
               ("lock" in low and "dnf" in low):
                if self.args.no_warn_on_lock:
                    finish(OK, "package manager is locked by another process")
                finish(WARNING, "package manager is locked by another process")

            finish(
                UNKNOWN,
                f"dnf failed with exit code {result.returncode}: "
                f"{clean_message(output) or 'no output'}",
            )

        return result.returncode, output

    @staticmethod
    def package_names(output: str) -> set:
        """
        Extract package NEVRA/name.arch entries from `dnf check-update` output.

        DNF check-update package rows normally contain:
            package.arch    version-release    repository

        Informational/status lines are ignored.
        """
        packages = set()

        ignored_prefixes = (
            "last metadata expiration check:",
            "metadata cache created",
            "obsoleting packages",
            "security:",
        )

        pkg_re = re.compile(
            r"^\s*(?P<pkg>[A-Za-z0-9_+.-]+\."
            r"(?:x86_64|noarch|aarch64|ppc64le|s390x|i[3-6]86))"
            r"\s+\S+\s+\S+"
        )

        for raw_line in output.splitlines():
            line = raw_line.strip()

            if not line:
                continue
            if line.lower().startswith(ignored_prefixes):
                continue

            match = pkg_re.match(raw_line)
            if match:
                packages.add(match.group("pkg"))

        return packages

    def check_update(self, security_only: bool = False) -> set:
        cmd = [self.dnf, "-q"]
        cmd.extend(self.common_args())

        if security_only:
            cmd.append("--security")

        cmd.append("check-update")

        _, output = self.run(cmd, valid_codes=(0, 100))
        return self.package_names(output), output

    @staticmethod
    def kernel_security_status(output: str) -> Optional[Tuple[str, str]]:
        """Return (installed_security_kernel, running_kernel) when DNF reports both."""
        installed = None
        running = None
        installed_re = re.compile(
            r"^Security:\s+kernel-core-(.+)\s+is an installed security update$"
        )
        running_re = re.compile(
            r"^Security:\s+kernel-core-(.+)\s+is the currently running version$"
        )
        for raw_line in output.splitlines():
            line = raw_line.strip()
            match = installed_re.match(line)
            if match:
                installed = match.group(1)
                continue
            match = running_re.match(line)
            if match:
                running = match.group(1)
        if installed and running:
            return installed, running
        return None

    def reboot_required(self) -> Optional[bool]:
        """
        Check whether a reboot is required.

        Returns:
            True  - reboot required
            False - reboot not required
            None  - check unavailable/unsupported
        """
        if self.args.no_reboot_check:
            return None

        candidates = [
            [self.dnf, "-q", "needs-restarting", "-r"],
            ["/usr/bin/needs-restarting", "-r"],
        ]

        for cmd in candidates:
            if cmd[0].startswith("/") and not os.path.exists(cmd[0]):
                continue

            env = os.environ.copy()
            env["LANG"] = "C"
            env["LC_ALL"] = "C"

            self.debug(2, "running reboot check: " + " ".join(cmd))

            try:
                result = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    timeout=self.args.timeout,
                    check=False,
                )
            except (subprocess.TimeoutExpired, OSError) as exc:
                self.debug(1, f"reboot check failed: {exc}")
                continue

            self.debug(
                3,
                f"reboot check return code: {result.returncode}\n"
                f"{(result.stdout or '').rstrip()}",
            )

            # needs-restarting -r convention:
            # 0 = reboot not required, 1 = reboot required.
            if result.returncode == 0:
                return False
            if result.returncode == 1:
                return True

            self.debug(
                1,
                "reboot check unavailable: "
                + clean_message(result.stdout or f"exit code {result.returncode}"),
            )

        return None

    def execute(self) -> None:
        all_packages, all_output = self.check_update(security_only=False)
        security_packages, security_output = self.check_update(security_only=True)
        kernel_status = self.kernel_security_status(
            security_output if security_output.strip() else all_output
        )

        # Defensive intersection: a package reported by --security should also
        # be present in the full update set. Keep it security even if DNF output
        # differs unexpectedly, while preventing a negative non-security count.
        total = len(all_packages)
        security = len(security_packages)

        if security > total:
            self.debug(
                1,
                "security package count is greater than total package count; "
                "using union for total",
            )
            total = len(all_packages | security_packages)

        non_security = max(total - security, 0)

        reboot = self.reboot_required()

        if self.args.all_updates:
            status = CRITICAL if total > 0 else OK
        elif security >= self.args.critical_security:
            status = CRITICAL
        elif self.args.warning_security > 0 and security >= self.args.warning_security:
            status = WARNING
        elif self.args.warn_on_any_update and non_security > 0:
            status = WARNING
        else:
            status = OK

        if reboot is True and not self.args.no_reboot_critical:
            status = CRITICAL

        parts = [
            f"{security} security update{'s' if security != 1 else ''}",
            f"{non_security} non-security update{'s' if non_security != 1 else ''}",
            f"{total} total",
        ]

        if reboot is True:
            if kernel_status:
                installed_kernel, running_kernel = kernel_status
                kernel_arch_re = re.compile(
                    r"\.(?:x86_64|aarch64|ppc64le|s390x|i[3-6]86)$"
                )
                installed_kernel_display = kernel_arch_re.sub("", installed_kernel)
                running_kernel_display = kernel_arch_re.sub("", running_kernel)
                parts.append(
                    f"reboot required (security kernel {installed_kernel_display} installed, "
                    f"running {running_kernel_display})"
                )
            else:
                parts.append("reboot required")
        elif reboot is False:
            parts.append("reboot not required")
        elif not self.args.no_reboot_check:
            parts.append("reboot status unavailable")

        perfdata = (
            f"security_updates={security} "
            f"non_security_updates={non_security} "
            f"total_updates={total}"
        )

        if reboot is not None:
            perfdata += f" reboot_required={1 if reboot else 0}"

        finish(status, ", ".join(parts) + " | " + perfdata)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nagios/Icinga plugin for checking DNF package updates"
    )

    parser.add_argument(
        "-A",
        "--all-updates",
        action="store_true",
        help="return CRITICAL if any package update is available",
    )
    parser.add_argument(
        "-W",
        "--warn-on-any-update",
        action="store_true",
        help="return WARNING for non-security updates if no security CRITICAL exists",
    )
    parser.add_argument(
        "-C",
        "--cache-only",
        action="store_true",
        help="use cached repository metadata only",
    )
    parser.add_argument(
        "-e",
        "--enablerepo",
        action="append",
        default=[],
        metavar="REPO",
        help="enable repository; may be specified multiple times",
    )
    parser.add_argument(
        "-d",
        "--disablerepo",
        action="append",
        default=[],
        metavar="REPO",
        help="disable repository; may be specified multiple times",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="FILE",
        help="use an alternative DNF configuration file",
    )
    parser.add_argument(
        "-N",
        "--no-warn-on-lock",
        action="store_true",
        help="return OK instead of WARNING if DNF is locked",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"command timeout, default: {DEFAULT_TIMEOUT}",
    )
    parser.add_argument(
        "--warning-security",
        type=int,
        default=0,
        metavar="N",
        help="WARNING at N security updates; 0 disables WARNING threshold",
    )
    parser.add_argument(
        "--critical-security",
        type=int,
        default=1,
        metavar="N",
        help="CRITICAL at N security updates; default: 1",
    )
    parser.add_argument(
        "--no-reboot-check",
        action="store_true",
        help="disable the reboot-required check",
    )
    parser.add_argument(
        "--no-reboot-critical",
        action="store_true",
        help="report reboot requirement without changing status to CRITICAL",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase debug output; may be specified multiple times",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    if not 1 <= args.timeout <= 3600:
        parser.error("--timeout must be between 1 and 3600 seconds")

    if args.warning_security < 0:
        parser.error("--warning-security cannot be negative")

    if args.critical_security < 1:
        parser.error("--critical-security must be at least 1")

    if (
        args.warning_security > 0
        and args.warning_security >= args.critical_security
    ):
        parser.error(
            "--warning-security must be lower than --critical-security"
        )

    return args


def main() -> None:
    args = parse_args()
    DnfCheck(args).execute()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        finish(UNKNOWN, "interrupted")
