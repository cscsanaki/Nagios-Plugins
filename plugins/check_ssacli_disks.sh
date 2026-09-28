#!/usr/bin/env bash
#
# check_ssacli_disks.sh - Nagios/Icinga plugin for monitoring HPE Smart Array physical drive health via ssacli.
#
# Copyright (c) 2026 Csanaki Csaba <cscsanaki@gmail.com>
# SPDX-License-Identifier: MIT
#
# Requires HPE Smart Storage Administrator CLI (ssacli).
#
# Nagios exit codes:
#   0 OK
#   1 WARNING
#   2 CRITICAL
#   3 UNKNOWN
#

set -u

VERSION="1.0.0"
SSACLI_BIN="${SSACLI_BIN:-/usr/sbin/ssacli}"

OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3

usage() {
  cat <<EOF_USAGE
Usage: $(basename "$0") [OPTIONS]

Nagios/Icinga plugin for monitoring HPE Smart Array physical drive health.

Options:
  -V, --version   Show plugin version and exit
  -h, --help      Show this help and exit

Environment:
  SSACLI_BIN      Path to ssacli (default: /usr/sbin/ssacli)

Nagios exit codes:
  0 OK
  1 WARNING
  2 CRITICAL
  3 UNKNOWN
EOF_USAGE
}

case "${1:-}" in
  -V|--version)
    echo "$(basename "$0") $VERSION"
    exit "$OK"
    ;;
  -h|--help)
    usage
    exit "$OK"
    ;;
  "")
    ;;
  *)
    echo "SSACLI UNKNOWN: unknown option: $1"
    exit "$UNKNOWN"
    ;;
esac

if [[ ! -x "$SSACLI_BIN" ]]; then
  echo "SSACLI UNKNOWN: ssacli executable not found or not executable: $SSACLI_BIN"
  exit "$UNKNOWN"
fi

controller_output="$($SSACLI_BIN ctrl all show 2>&1)"
controller_rc=$?
if [[ $controller_rc -ne 0 ]]; then
  controller_output="$(printf '%s' "$controller_output" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//')"
  echo "SSACLI UNKNOWN: failed to query controllers (exit $controller_rc): $controller_output"
  exit "$UNKNOWN"
fi

controllers="$(printf '%s\n' "$controller_output" | sed -n 's/.*[Ss]lot[[:space:]]\+\([0-9][0-9]*\).*/\1/p' | sort -nu)"
if [[ -z "$controllers" ]]; then
  echo "SSACLI UNKNOWN: no Smart Array controllers found"
  exit "$UNKNOWN"
fi

problem_drives=()
total_drives=0

while IFS= read -r slot; do
  [[ -n "$slot" ]] || continue

  drives="$($SSACLI_BIN ctrl slot="$slot" pd all show detail 2>&1)"
  rc=$?
  if [[ $rc -ne 0 ]]; then
    detail="$(printf '%s' "$drives" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//')"
    echo "SSACLI UNKNOWN: failed to query controller in slot $slot (exit $rc): $detail"
    exit "$UNKNOWN"
  fi

  current_drive=""
  current_status=""

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[[:space:]]*physicaldrive[[:space:]]+([^[:space:]]+) ]]; then
      if [[ -n "$current_drive" ]]; then
        ((total_drives+=1))
        if [[ "$current_status" != "OK" ]]; then
          problem_drives+=("Slot $slot, Drive $current_drive (${current_status:-status unknown})")
        fi
      fi
      current_drive="${BASH_REMATCH[1]}"
      current_status=""
      continue
    fi

    if [[ -n "$current_drive" && "$line" =~ ^[[:space:]]*Status:[[:space:]]*(.*)$ ]]; then
      current_status="${BASH_REMATCH[1]}"
    fi
  done <<< "$drives"

  if [[ -n "$current_drive" ]]; then
    ((total_drives+=1))
    if [[ "$current_status" != "OK" ]]; then
      problem_drives+=("Slot $slot, Drive $current_drive (${current_status:-status unknown})")
    fi
  fi
done <<< "$controllers"

if (( total_drives == 0 )); then
  echo "SSACLI UNKNOWN: no physical drives found"
  exit "$UNKNOWN"
fi

if (( ${#problem_drives[@]} > 0 )); then
  printf 'SSACLI CRITICAL: %d problematic drive(s) found: ' "${#problem_drives[@]}"
  printf '%s' "${problem_drives[0]}"
  for ((i=1; i<${#problem_drives[@]}; i++)); do
    printf '; %s' "${problem_drives[$i]}"
  done
  printf ' | drives=%d problems=%d\n' "$total_drives" "${#problem_drives[@]}"
  exit "$CRITICAL"
fi

echo "SSACLI OK: all $total_drives physical drive(s) are healthy | drives=$total_drives problems=0"
exit "$OK"
