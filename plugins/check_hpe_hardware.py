#!/usr/bin/env python3
#
# check_hpe_hardware.py - Nagios/Icinga plugin for monitoring HPE server hardware via iLOrest.
#
# Copyright (c) 2026 Csanaki Csaba <cscsanaki@gmail.com>
# SPDX-License-Identifier: MIT
#
# Requires HPE iLOrest (tested with ilorest 7.3.0.0-7).
#
# Nagios exit codes:
#   0 OK
#   1 WARNING
#   2 CRITICAL
#   3 UNKNOWN
#

import argparse
import os
import re
import shutil
import subprocess
import sys

VERSION = "1.0.0"
DEFAULT_ILOREST = "/usr/sbin/ilorest"
DEFAULT_TIMEOUT = 15
DEFAULT_DMI_TIMEOUT = 5

OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3
SEVERITY_OK, SEVERITY_WARNING, SEVERITY_CRITICAL = 0, 1, 2


class CommandError(Exception):
    """Raised when an external command cannot be executed successfully."""


def normalize(value):
    return " ".join(value.split())


def run_command(cmd, timeout):
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise CommandError(f"command not found: {cmd[0]}") from exc
    except PermissionError as exc:
        raise CommandError(f"permission denied: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandError(
            f"command exceeded timeout ({timeout}s): {' '.join(cmd)}"
        ) from exc
    except OSError as exc:
        raise CommandError(f"unable to execute {' '.join(cmd)}: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        message = f"command exited with code {result.returncode}: {' '.join(cmd)}"
        if detail:
            message += f": {normalize(detail)}"
        raise CommandError(message)

    return result.stdout


class IloRestSession:
    def __init__(self, executable, timeout, verbose=0):
        self.executable = executable
        self.timeout = timeout
        self.verbose = verbose
        self.logged_in = False

    def debug(self, level, message):
        if self.verbose >= level:
            print(f"DEBUG{level}: {message}", file=sys.stderr)

    def run(self, args):
        cmd = [self.executable] + args
        self.debug(2, f"running command: {' '.join(cmd)}")
        output = run_command(cmd, self.timeout)
        if self.verbose >= 3 and output:
            print(output.rstrip(), file=sys.stderr)
        return output

    def login(self):
        output = self.run(["login"])
        self.logged_in = True
        return output

    def logout(self):
        if not self.logged_in:
            return
        try:
            self.run(["logout"])
        except CommandError as exc:
            self.debug(1, f"logout failed: {exc}")
        finally:
            self.logged_in = False


def get_local_bios_fallback(timeout, verbose=0):
    """Return the local BIOS version when iLO does not provide it."""
    try:
        with open("/sys/class/dmi/id/bios_version", "r", encoding="utf-8") as handle:
            value = handle.read().strip()
        if value:
            return normalize(value)
    except (OSError, UnicodeError):
        pass

    dmidecode = shutil.which("dmidecode")
    if not dmidecode:
        return "Unknown BIOS"

    commands = [[dmidecode, "-s", "bios-version"]]
    if os.geteuid() != 0 and shutil.which("sudo"):
        commands.append(["sudo", "-n", dmidecode, "-s", "bios-version"])

    for cmd in commands:
        try:
            if verbose >= 2:
                print(f"DEBUG2: running BIOS fallback: {' '.join(cmd)}", file=sys.stderr)
            output = run_command(cmd, timeout)
            if output.strip():
                return normalize(output)
        except CommandError:
            continue

    return "Unknown BIOS"


def parse_system_info(output):
    """Parse system identity, firmware versions, and the worst health state."""
    data = {
        "model": "HPE Server",
        "serial": "Unknown S/N",
        "bios": "",
        "ilo": "Unknown iLO",
        "severity": SEVERITY_OK,
    }

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if "Model:" in line and "Processor" not in line:
            candidate = line.split(":", 1)[1].strip()
            if candidate and "Intel" not in candidate and "Xeon" not in candidate:
                data["model"] = candidate
        elif "Serial Number:" in line:
            data["serial"] = line.split(":", 1)[1].strip() or data["serial"]
        elif "Bios Version:" in line or "System ROM :" in line:
            data["bios"] = line.split(":", 1)[1].strip()
        elif "iLO " in line and ":" in line:
            left, right = line.split(":", 1)
            data["ilo"] = f"{left.strip()}: {right.strip()}"
        elif "Health:" in line or "Status:" in line:
            value = line.split(":", 1)[1].strip().upper()
            if any(x in value for x in ("CRITICAL", "FAILED", "FAIL")):
                data["severity"] = max(data["severity"], SEVERITY_CRITICAL)
            elif any(x in value for x in ("DEGRADED", "WARNING", "WARN")):
                data["severity"] = max(data["severity"], SEVERITY_WARNING)

    for key in ("model", "serial", "bios", "ilo"):
        data[key] = normalize(data[key])
    return data


def get_latest_iml_logs(session, count=3):
    """Return the last relevant IML entries when a hardware issue is detected."""
    try:
        logs = session.run(["iml"])
    except CommandError as exc:
        return f" | IML Logs: unable to retrieve detailed IML logs ({exc})"

    ansi = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
    lines = []
    for line in logs.splitlines():
        clean = ansi.sub("", line).strip()
        if clean and not any(x in clean for x in ("IML", "Severity", "===", "Logged")):
            lines.append(clean)
    return " | IML Logs: " + " -> ".join(lines[-count:]) if lines else ""


def resolve_ilorest(path):
    candidate = path if os.path.isabs(path) else shutil.which(path)
    if not candidate or not os.path.isfile(candidate):
        raise CommandError(f"iLOrest executable not found: {path}")
    if not os.access(candidate, os.X_OK):
        raise CommandError(f"iLOrest executable is not executable: {candidate}")
    return candidate


def build_parser():
    parser = argparse.ArgumentParser(
        description="Nagios/Icinga plugin for monitoring HPE hardware through HPE iLOrest."
    )
    parser.add_argument(
        "-t", "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"iLOrest command timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--ilorest", default=DEFAULT_ILOREST,
        help=f"path to iLOrest (default: {DEFAULT_ILOREST})"
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="increase diagnostic output; may be specified multiple times"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    return parser


def main():
    args = build_parser().parse_args()
    if not 1 <= args.timeout <= 3600:
        print("HPE UNKNOWN: timeout must be between 1 and 3600 seconds")
        return UNKNOWN

    try:
        executable = resolve_ilorest(args.ilorest)
    except CommandError as exc:
        print(f"HPE UNKNOWN: {exc}")
        return UNKNOWN

    session = IloRestSession(executable, args.timeout, args.verbose)

    try:
        try:
            session.login()
        except CommandError as exc:
            print(f"HPE UNKNOWN: iLOrest login failed: {exc}")
            return UNKNOWN

        try:
            system_info = session.run(["systeminfo"])
        except CommandError as exc:
            print(f"HPE UNKNOWN: unable to retrieve system information: {exc}")
            return UNKNOWN

        if not system_info.strip():
            print("HPE UNKNOWN: iLOrest systeminfo returned no data")
            return UNKNOWN

        data = parse_system_info(system_info)
        bios = data["bios"]
        if not bios or "unknown" in bios.lower():
            bios = get_local_bios_fallback(DEFAULT_DMI_TIMEOUT, args.verbose)

        info = (
            f"Model: {data['model']}, S/N: {data['serial']}, "
            f"ROM: {bios}, iLO: {data['ilo']}"
        )

        if data["severity"] == SEVERITY_CRITICAL:
            print(f"HPE CRITICAL: hardware status is FAILED ({info})"
                  f"{get_latest_iml_logs(session)}")
            return CRITICAL
        if data["severity"] == SEVERITY_WARNING:
            print(f"HPE WARNING: hardware status is DEGRADED ({info})"
                  f"{get_latest_iml_logs(session)}")
            return WARNING

        print(f"HPE OK: hardware is healthy ({info})")
        return OK
    finally:
        session.logout()


if __name__ == "__main__":
    sys.exit(main())
