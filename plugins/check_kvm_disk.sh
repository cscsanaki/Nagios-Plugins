#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# check_kvm_disk.sh - Nagios/Icinga KVM guest filesystem monitoring
# Copyright (c) 2026 Csaba Csanaki
# Licensed under the MIT License.
# Version: 1.0.1
# Repository: https://github.com/cscsanaki/Nagios-Plugins
#
# Requirements: bash, virsh/libvirt, QEMU Guest Agent, jq, base64, timeout
# The guest agent executes /bin/df -P -k inside the selected VM.

VERSION="1.0.1"
OK=0; WARNING_STATE=1; CRITICAL_STATE=2; UNKNOWN=3
VM_NAME=""; PARTITION=""; WARNING=""; CRITICAL=""; TIMEOUT=30; VERBOSE=0

unknown() { printf 'DISK UNKNOWN: %s\n' "$1"; exit "$UNKNOWN"; }
usage() {
  cat <<'HELP'
Usage: check_kvm_disk.sh -d VM -p MOUNT -w FREE_WARN -c FREE_CRIT [options]
  -d, --domain NAME       libvirt virtual machine name
  -p, --partition MOUNT   exact guest mount point (e.g. / or /boot)
  -w, --warning PERCENT   WARNING when free space <= PERCENT
  -c, --critical PERCENT  CRITICAL when free space <= PERCENT
  -t, --timeout SECONDS   total execution deadline (default: 30)
  -v, --verbose           diagnostic output (stderr)
  -h, --help              show this help
  -V, --version           show version
Example: check_kvm_disk.sh -d example-vm -p / -w 20 -c 10
HELP
}

while (($#)); do
  case "$1" in
    -d|--domain) (($# >= 2)) || unknown "missing value for $1"; VM_NAME=$2; shift 2 ;;
    -p|--partition) (($# >= 2)) || unknown "missing value for $1"; PARTITION=$2; shift 2 ;;
    -w|--warning) (($# >= 2)) || unknown "missing value for $1"; WARNING=$2; shift 2 ;;
    -c|--critical) (($# >= 2)) || unknown "missing value for $1"; CRITICAL=$2; shift 2 ;;
    -t|--timeout) (($# >= 2)) || unknown "missing value for $1"; TIMEOUT=$2; shift 2 ;;
    -v|--verbose) VERBOSE=$((VERBOSE + 1)); shift ;;
    -V|--version) printf 'check_kvm_disk.sh %s\n' "$VERSION"; exit "$OK" ;;
    -h|--help) usage; exit "$OK" ;;
    *) unknown "unrecognized argument: $1" ;;
  esac
done

[[ -n $VM_NAME && -n $PARTITION && -n $WARNING && -n $CRITICAL ]] || unknown "-d, -p, -w and -c are required (see --help)"
WARNING=${WARNING%%%}; CRITICAL=${CRITICAL%%%}
[[ $WARNING =~ ^[0-9]+$ && $CRITICAL =~ ^[0-9]+$ ]] || unknown "thresholds must be whole percentages"
((10#$WARNING <= 100 && 10#$CRITICAL <= 100)) || unknown "thresholds must be between 0 and 100"
WARNING=$((10#$WARNING)); CRITICAL=$((10#$CRITICAL))
((WARNING > CRITICAL)) || unknown "--warning must be greater than --critical for free-space thresholds"
[[ $TIMEOUT =~ ^[1-9][0-9]*$ ]] || unknown "--timeout must be a positive integer"
for dependency in virsh jq base64 timeout date sleep; do
  command -v "$dependency" >/dev/null 2>&1 || unknown "missing required command: $dependency"
done

# One shared deadline for all virsh calls and polling, not a timeout per call.
DEADLINE=$(( $(date +%s) + TIMEOUT ))
run_virsh() {
  local remaining result rc
  remaining=$(( DEADLINE - $(date +%s) ))
  ((remaining > 0)) || unknown "operation timed out after ${TIMEOUT}s"
  result=$(timeout --signal=TERM --kill-after=1s "${remaining}s" virsh "$@" 2>&1)
  rc=$?
  ((rc == 0)) || unknown "virsh command failed (exit ${rc}): ${result:0:240}"
  printf '%s' "$result"
}

VM_STATE=$(run_virsh domstate "$VM_NAME")
[[ $VM_STATE == running ]] || unknown "VM '$VM_NAME' is not running (state: $VM_STATE)"

# JSON is passed as one argument; never interpolate the VM or mount into JSON.
REQUEST='{"execute":"guest-exec","arguments":{"path":"/bin/df","arg":["-P","-k"],"capture-output":true}}'
EXEC_RESULT=$(run_virsh qemu-agent-command "$VM_NAME" "$REQUEST")
PID=$(jq -er '.return.pid | select(type == "number" and . >= 0)' <<< "$EXEC_RESULT" 2>/dev/null) || unknown "guest-exec did not return a valid PID"
[[ $PID =~ ^[0-9]+$ ]] || unknown "invalid guest execution PID"
((VERBOSE)) && printf 'VM=%s mount=%s guest PID=%s\n' "$VM_NAME" "$PARTITION" "$PID" >&2

STATUS_REQUEST=$(jq -cn --argjson pid "$PID" '{execute:"guest-exec-status",arguments:{pid:$pid}}') || unknown "unable to build status request"
while :; do
  STATUS_RESULT=$(run_virsh qemu-agent-command "$VM_NAME" "$STATUS_REQUEST")
  EXITED=$(jq -r '.return.exited | select(type == "boolean")' <<< "$STATUS_RESULT" 2>/dev/null) || unknown "invalid guest-exec-status response"
  [[ $EXITED == true ]] && break
  (( $(date +%s) < DEADLINE )) || unknown "guest df timed out after ${TIMEOUT}s"
  sleep 0.2
done

EXIT_CODE=$(jq -er '.return.exitcode | select(type == "number")' <<< "$STATUS_RESULT" 2>/dev/null) || unknown "guest df exit code unavailable"
((EXIT_CODE == 0)) || unknown "guest df failed (exit ${EXIT_CODE})"
BASE64_DATA=$(jq -er '.return["out-data"] | select(type == "string")' <<< "$STATUS_RESULT" 2>/dev/null) || unknown "guest df output unavailable"
DF_OUTPUT=$(printf '%s' "$BASE64_DATA" | base64 --decode 2>/dev/null) || unknown "invalid base64 output from guest df"

# POSIX df -P -k has predictable columns; exact mount match prevents prefix collisions.
PART_LINE=$(printf '%s\n' "$DF_OUTPUT" | awk -v mount="$PARTITION" 'NR>1 && NF>=6 && $NF==mount {print; exit}')
[[ -n $PART_LINE ]] || unknown "mount '$PARTITION' not found in VM '$VM_NAME'"
read -r FILESYSTEM TOTAL_KB USED_KB FREE_KB USE_PCT MOUNT <<< "$PART_LINE"
[[ $TOTAL_KB =~ ^[0-9]+$ && $USED_KB =~ ^[0-9]+$ && $FREE_KB =~ ^[0-9]+$ ]] || unknown "invalid numeric values returned by guest df"
((TOTAL_KB > 0)) || unknown "guest filesystem size is zero"

# Compare integer quantities without rounding away boundary conditions.
FREE_PCT=$((100 * FREE_KB / TOTAL_KB))
USED_PCT=$((100 * USED_KB / TOTAL_KB))
TOTAL_GIB=$(awk -v n="$TOTAL_KB" 'BEGIN {printf "%.2f", n/1048576}')
FREE_GIB=$(awk -v n="$FREE_KB" 'BEGIN {printf "%.2f", n/1048576}')
USED_GIB=$(awk -v n="$USED_KB" 'BEGIN {printf "%.2f", n/1048576}')

# Nagios perfdata: report free/used percentages separately from KiB values.
# Free-space thresholds use Nagios inside-range alert syntax (@0:N).
LABEL=${PARTITION//\'/\'\'}
PERF="'${LABEL}_free_pct'=${FREE_PCT}%;@0:${WARNING};@0:${CRITICAL};0;100 '${LABEL}_used_pct'=${USED_PCT}% '${LABEL}_used_kib'=${USED_KB}KB '${LABEL}_free_kib'=${FREE_KB}KB '${LABEL}_total_kib'=${TOTAL_KB}KB"
if ((100 * FREE_KB <= CRITICAL * TOTAL_KB)); then
  CODE=$CRITICAL_STATE; STATE=CRITICAL
elif ((100 * FREE_KB <= WARNING * TOTAL_KB)); then
  CODE=$WARNING_STATE; STATE=WARNING
else
  CODE=$OK; STATE=OK
fi
printf 'DISK %s: VM=%s mount=%s, %s%% used, %s%% free (%s GiB free / %s GiB total, %s GiB used) | %s\n' \
  "$STATE" "$VM_NAME" "$PARTITION" "$USED_PCT" "$FREE_PCT" "$FREE_GIB" "$TOTAL_GIB" "$USED_GIB" "$PERF"
exit "$CODE"
