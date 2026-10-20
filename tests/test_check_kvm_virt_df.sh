#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Mock-based regression tests for check_kvm_virt_df.sh 1.0.3.
set -u
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -n ${PLUGIN:-} ]]; then
  :
elif [[ -f "$SCRIPT_DIR/../plugins/check_kvm_virt_df.sh" ]]; then
  PLUGIN="$SCRIPT_DIR/../plugins/check_kvm_virt_df.sh"
else
  PLUGIN="$SCRIPT_DIR/check_kvm_virt_df.sh"
fi
[[ -f "$PLUGIN" ]] || { printf 'ERROR: plugin not found: %s\n' "$PLUGIN" >&2; exit 1; }
PLUGIN=$(cd -- "$(dirname -- "$PLUGIN")" && pwd)/$(basename -- "$PLUGIN")
TMP=$(mktemp -d) || exit 1
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/bin"
: > "$TMP/offline.qcow2"
: > "$TMP/live.qcow2"
cat > "$TMP/bin/virt-df" <<'MOCK'
#!/usr/bin/env bash
case "${MOCK_SCENARIO:-normal}" in
  command_failure) echo 'virt-df error' >&2; exit 1 ;;
  timeout) sleep 4; exit 0 ;;
  empty) exit 0 ;;
  header_only) printf 'VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%%\n'; exit 0 ;;
  malformed) printf 'VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%%\nexample-vm,/dev/sda1,invalid,5,95,5.0\n'; exit 0 ;;
  malformed_csv) printf 'VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%%\nexample-vm,/dev/sda1,100,20\n'; exit 0 ;;
  negative) printf 'VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%%\nexample-vm,/dev/sda1,100,-1,101,1.0\n'; exit 0 ;;
  swap_only) printf 'VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%%\nexample-vm,/dev/swap,100,20,80,20.0\n'; exit 0 ;;
  legacy) printf 'Filesystem,1K-blocks,Used,Available,Use%%\n/dev/sda1,1000,100,900,10.0\n'; exit 0 ;;
esac
printf 'VirtualMachine,Filesystem,1K-blocks,Used,Available,Use%%\n'
printf 'example-vm,/dev/sda1,1000,115,885,11.5\n'
printf 'example-vm,/dev/mapper/vg-root,1000,766,234,76.6\n'
printf 'example-vm,/dev/swap,1000,1000,0,100.0\n'
MOCK
cat > "$TMP/bin/virsh" <<'MOCK'
#!/usr/bin/env bash
case "${1:-}" in
  list)
    [[ ${MOCK_SCENARIO:-} == virsh_failure ]] && exit 1
    printf 'running-vm\n' ;;
  domblklist)
    [[ ${MOCK_SCENARIO:-} == disks_failure ]] && exit 1
    printf 'Type Device Target Source\n---- ------ ------ ------\nfile disk vda %s\n' "${MOCK_LIVE_IMAGE:-/nonexistent}" ;;
  *) exit 1 ;;
esac
MOCK
chmod +x "$TMP/bin/virt-df" "$TMP/bin/virsh"
export PATH="$TMP/bin:$PATH" MOCK_LIVE_IMAGE="$TMP/live.qcow2"
export MOCK_SCENARIO=normal
passed=0 failed=0
check() {
  local name=$1 expected=$2 pattern=$3
  shift 3
  local output rc
  output=$(bash "$PLUGIN" "$@" 2>&1); rc=$?
  if [[ $rc -eq $expected && $output == *"$pattern"* ]]; then
    printf 'PASS %s\n' "$name"; ((passed+=1))
  else
    printf 'FAIL %s: exit=%s expected=%s output=%s\n' "$name" "$rc" "$expected" "$output"; ((failed+=1))
  fi
}
base=(-d example-vm -p /dev/mapper/vg-root)
check version 0 '1.0.3' --version
check help 0 'Usage:' --help
check missing_selector 3 'exactly one' -w 80 -c 90
check conflicting_selectors 3 'exactly one' -d example-vm -i "$TMP/offline.qcow2"
check unknown_argument 3 'unknown argument' -d example-vm --wrong
check missing_value 3 'missing value' -d
check invalid_warning 3 'whole percentages' -d example-vm -w abc
check reversed_thresholds 3 'require 0 <= warning' -d example-vm -w 90 -c 80
check invalid_timeout 3 'positive integer' -d example-vm -t 0
check domain_ok 0 'VIRT_DF OK:' "${base[@]}" -w 80 -c 90
check decimal_percent 0 '76.6% used' "${base[@]}"
check partition_only 0 "'example-vm:/dev/mapper/vg-root_used_pct'=76.6%" "${base[@]}"
check perfdata 0 ';80;90;0;100' "${base[@]}" -w 80 -c 90
check warning 1 'VIRT_DF WARNING:' "${base[@]}" -w 70 -c 90
check critical 2 'VIRT_DF CRITICAL:' "${base[@]}" -w 60 -c 75
check all_filesystems 2 '/dev/sda1:' -d example-vm -w 10 -c 75
check missing_partition 3 'not found' -d example-vm -p /dev/notfound
check offline_image 0 'VIRT_DF OK:' -i "$TMP/offline.qcow2" -p /dev/sda1
check live_image_rejected 3 'attached to running VM' -i "$TMP/live.qcow2"
check missing_image 3 'missing or unreadable' -i "$TMP/missing.qcow2"
export MOCK_SCENARIO=command_failure
check virt_df_failure 3 'virt-df failed or timed out' -d example-vm
export MOCK_SCENARIO=empty
check empty_output 3 'no usable filesystem' -d example-vm
export MOCK_SCENARIO=header_only
check header_only 3 'no usable filesystem' -d example-vm
export MOCK_SCENARIO=malformed
check invalid_number 3 'invalid virt-df CSV' -d example-vm
export MOCK_SCENARIO=malformed_csv
check malformed_csv 3 'invalid virt-df CSV' -d example-vm
export MOCK_SCENARIO=negative
check negative_usage 3 'invalid virt-df CSV' -d example-vm
export MOCK_SCENARIO=swap_only
check swap_excluded 3 'no usable filesystem' -d example-vm
export MOCK_SCENARIO=legacy
check legacy_csv 0 'VIRT_DF OK:' -d example-vm -p /dev/sda1
export MOCK_SCENARIO=virsh_failure
check virsh_failure 3 'cannot query running libvirt domains' -i "$TMP/offline.qcow2"
export MOCK_SCENARIO=disks_failure
check disk_discovery_failure 3 'cannot inspect disks' -i "$TMP/offline.qcow2"
export MOCK_SCENARIO=timeout
check timeout 3 'virt-df failed or timed out' -d example-vm -t 1
printf '\nTests: %d passed, %d failed\n' "$passed" "$failed"
((failed == 0))

