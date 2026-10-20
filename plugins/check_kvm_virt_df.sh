#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# check_kvm_virt_df.sh - Nagios/Icinga host-side KVM image filesystem check
# Copyright (c) 2026 Csaba Csanaki
# Licensed under the MIT License.
# Version: 1.0.3
# Repository: https://github.com/cscsanaki/Nagios-Plugins
#
# Requirements: Bash, libguestfs-tools-c (virt-df), GNU timeout, Python 3,
#               libvirt virsh (for active-guest safety verification).
# Install on RHEL/Rocky Linux: sudo dnf install libguestfs-tools-c
#
# Domain mode (-d) supports active or inactive libvirt guests via virt-df.
# Image mode (-i) accepts offline images and consistent snapshots only.
# Live guest results may be inconsistent; never bypass QEMU image locks.
# Nagios exit codes: OK=0 WARNING=1 CRITICAL=2 UNKNOWN=3

set -u
OK=0; WARNING=1; CRITICAL=2; UNKNOWN=3
VERSION=1.0.3
IMAGE_PATH=''; DOMAIN='' ; PARTITION=''; WARN_PCT=80; CRIT_PCT=90; TIMEOUT=60; VERBOSE=0

usage() {
  cat <<'HELP'
Usage: check_kvm_virt_df.sh (-d DOMAIN | -i IMAGE) [-p FILESYSTEM] [-w WARNING] [-c CRITICAL] [-t SECONDS] [-v]
  -d, --domain NAME      Libvirt guest name (running or stopped)
  -i, --image PATH       Offline disk image or consistent snapshot
  -p, --partition FS     Exact virt-df filesystem name (default: all)
  -w, --warning PCT      Used-space WARNING percentage (default: 80)
  -c, --critical PCT     Used-space CRITICAL percentage (default: 90)
  -t, --timeout SECONDS  virt-df timeout (default: 60)
  -v, --verbose          Diagnostic output on stderr
  -h, --help             Display this help
  -V, --version          Display version
Example: check_kvm_virt_df.sh -d example-vm -p /dev/sda1 -w 80 -c 90
Example: check_kvm_virt_df.sh -i /path/to/offline.qcow2 -p /dev/sda1 -w 80 -c 90
Filesystem names come from the Filesystem column of virt-df --csv.
IMPORTANT: Running guest results may be inconsistent; -i refuses directly attached live images.
HELP
}
unknown() { printf 'VIRT_DF UNKNOWN: %s\n' "$1"; exit "$UNKNOWN"; }
debug() { if (( VERBOSE )); then printf 'DEBUG: %s\n' "$*" >&2; fi; }

while (($#)); do
  case "$1" in
    -d|--domain|-i|--image|-p|--partition|-w|--warning|-c|--critical|-t|--timeout)
      (($# >= 2)) || unknown "missing value for $1"
      case "$1" in
        -d|--domain) DOMAIN=$2 ;;
        -i|--image) IMAGE_PATH=$2 ;;
        -p|--partition) [[ -n "$2" ]] || unknown "partition selector must not be empty"; PARTITION=$2 ;;
        -w|--warning) WARN_PCT=$2 ;;
        -c|--critical) CRIT_PCT=$2 ;;
        -t|--timeout) TIMEOUT=$2 ;;
      esac
      shift 2 ;;
    -v|--verbose) VERBOSE=1; shift ;;
    -h|--help) usage; exit "$OK" ;;
    -V|--version) printf 'check_kvm_virt_df.sh %s\n' "$VERSION"; exit "$OK" ;;
    *) unknown "unknown argument: $1" ;;
  esac
done

if [[ -n $IMAGE_PATH && -n $DOMAIN ]] || [[ -z $IMAGE_PATH && -z $DOMAIN ]]; then
  unknown 'specify exactly one of -d DOMAIN or -i IMAGE'
fi
for value in "$WARN_PCT" "$CRIT_PCT"; do
  [[ $value =~ ^(0|[1-9][0-9]*)$ ]] || unknown 'thresholds must be whole percentages from 0 to 100'
done
(( WARN_PCT >= 0 && WARN_PCT < CRIT_PCT && CRIT_PCT <= 100 )) || unknown 'require 0 <= warning < critical <= 100'
[[ $TIMEOUT =~ ^[1-9][0-9]*$ ]] || unknown 'timeout must be a positive integer'
for tool in virt-df timeout python3; do
  command -v "$tool" >/dev/null 2>&1 || unknown "required command not found: $tool"
done

# Direct image access is restricted to offline images/snapshots.
# Domain mode delegates discovery and read-only inspection to virt-df/libvirt.
if [[ -n $IMAGE_PATH ]]; then
  [[ -f "$IMAGE_PATH" && -r "$IMAGE_PATH" ]] || unknown "image missing or unreadable: $IMAGE_PATH"
  command -v virsh >/dev/null 2>&1 || unknown 'required command not found: virsh'
  IMAGE_PATH=$(realpath -e -- "$IMAGE_PATH" 2>/dev/null) || unknown 'cannot resolve image path'
  domains=$(virsh list --name --state-running 2>/dev/null) || unknown 'cannot query running libvirt domains; refusing potentially live image'
  while IFS= read -r domain; do
    [[ -n "$domain" ]] || continue
    disks=$(virsh domblklist --details "$domain" 2>/dev/null) || unknown "cannot inspect disks of running VM: $domain"
    while IFS= read -r source; do
      [[ -n "$source" && "$source" == /* ]] || continue
      resolved=$(realpath -e -- "$source" 2>/dev/null) || unknown "cannot resolve running VM disk source: $source"
      [[ "$resolved" != "$IMAGE_PATH" ]] || unknown "image is attached to running VM '$domain'; use -d $domain instead"
    done < <(printf '%s\n' "$disks" | awk 'NR>2 && $1=="file" && $2=="disk" {print $4}')
  done <<< "$domains"
fi

# Allow libguestfs defaults; do not force a distribution-specific QEMU binary.
export LIBGUESTFS_BACKEND="${LIBGUESTFS_BACKEND:-direct}"
TMPDIR_CHECK=$(mktemp -d) || unknown 'cannot create temporary directory'
trap 'rm -rf -- "$TMPDIR_CHECK"' EXIT
RAW="$TMPDIR_CHECK/virt-df.csv"; ERR="$TMPDIR_CHECK/virt-df.err"
debug "partition=${PARTITION:-all}"
debug "domain=${DOMAIN:-none} image=${IMAGE_PATH:-none} timeout=${TIMEOUT}s warning=$WARN_PCT critical=$CRIT_PCT"
# --format=auto works for supported libguestfs formats; --csv is parsed using Python csv.
virt_df_args=(--csv)
if [[ -n $DOMAIN ]]; then
  virt_df_args+=(-d "$DOMAIN")
else
  virt_df_args+=(-a "$IMAGE_PATH")
fi
if ! timeout --signal=TERM --kill-after=5 "${TIMEOUT}s" virt-df "${virt_df_args[@]}" >"$RAW" 2>"$ERR"; then
  debug "virt-df stderr: $(head -c 1000 "$ERR")"
  unknown "virt-df failed or timed out after ${TIMEOUT}s (check domain/image, permissions and libguestfs)"
fi

# Python's csv module handles quoted commas, and also validates numeric fields.
# Output is sanitized to one Nagios line, with Nagios perfdata escaping.
python3 - "$RAW" "$WARN_PCT" "$CRIT_PCT" "$PARTITION" <<'PY'
import csv
import sys

path, warning, critical, selected = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rows = []
try:
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            fields = [cell.strip() for cell in row]
            # virt-df --csv outputs six columns:
            # VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%
            # Also accept the legacy five-column layout without VM name.
            if fields[0].lower() == 'virtualmachine' and len(fields) >= 6:
                continue
            if fields[0].lower() == 'filesystem' and len(fields) >= 5:
                continue
            if len(fields) == 6:
                vm, fs, total, used, available, percent = fields
                name = f'{vm}:{fs}' if vm else fs
            elif len(fields) == 5:
                fs, total, used, available, percent = fields
                name = fs
            else:
                raise ValueError('malformed CSV record (expected 5 or 6 columns)')
            if selected and fs != selected:
                continue
            if 'swap' in fs.lower():
                continue
            total, used, available = (int(v) for v in (total, used, available))
            percent = float(percent.rstrip('%'))
            if total <= 0 or min(used, available) < 0 or not 0 <= percent <= 100:
                raise ValueError('invalid filesystem values')
            rows.append((name, fs, total, used, available, percent))
except (OSError, UnicodeError, csv.Error, ValueError) as exc:
    print(f'VIRT_DF UNKNOWN: invalid virt-df CSV output: {exc}')
    sys.exit(3)

if not rows:
    if selected:
        print(f'VIRT_DF UNKNOWN: filesystem {selected!r} not found in virt-df output')
    else:
        print('VIRT_DF UNKNOWN: no usable filesystem records returned')
    sys.exit(3)

status = 0
parts = []
perf = []
for name, fs, total, used, available, percent in rows:
    level = 2 if percent >= critical else 1 if percent >= warning else 0
    status = max(status, level)
    label = name.replace('\n', '_').replace('\r', '_').replace('|', '_').replace("'", "''")
    short = fs.replace('\n', '_').replace('\r', '_').replace('|', '_')
    warn_kib = total * warning // 100
    crit_kib = total * critical // 100
    pct_text = f'{percent:g}'
    parts.append(f'{short}: {pct_text}% used ({used / 1048576:.2f}/{total / 1048576:.2f} GiB) {("OK", "WARNING", "CRITICAL")[level]}')
    perf.append(f"'{label}_used_kib'={used}KB;{warn_kib};{crit_kib};0;{total}")
    perf.append(f"'{label}_used_pct'={pct_text}%;{warning};{critical};0;100")

print(f"VIRT_DF {('OK', 'WARNING', 'CRITICAL')[status]}: " + '; '.join(parts) + ' | ' + ' '.join(perf))
sys.exit(status)
PY

