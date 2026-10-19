#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Mock-based regression tests for check_kvm_disk.sh 1.0.1.
set -u
PLUGIN="${PLUGIN:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/plugins/check_kvm_disk.sh}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
cat > "$TMP/bin/virsh" <<'MOCK'
#!/usr/bin/env bash
case "${1:-}" in
  domstate)
    if [[ ${MOCK_SCENARIO:-} == vm_missing ]]; then exit 1; fi
    if [[ ${MOCK_SCENARIO:-} == vm_off ]]; then echo 'shut off'; else echo running; fi ;;
  qemu-agent-command)
    case "$3" in
      *'"guest-exec"'*)
        [[ ${MOCK_SCENARIO:-} == agent_failure ]] && exit 1
        echo '{"return":{"pid":123}}' ;;
      *'"guest-exec-status"'*)
        case "${MOCK_SCENARIO:-}" in
          timeout)
            echo '{"return":{"exited":false}}' ;;
          guest_failure)
            echo '{"return":{"exited":true,"exitcode":1}}' ;;
          invalid_base64)
            echo '{"return":{"exited":true,"exitcode":0,"out-data":"%%%"}}' ;;
          *)
            df="Filesystem 1024-blocks Used Available Capacity Mounted on
/dev/vda1 100 $((100 - MOCK_FREE)) ${MOCK_FREE} 50% /"
            if [[ ${MOCK_SCENARIO:-} == missing_mount ]]; then
              df="Filesystem 1024-blocks Used Available Capacity Mounted on
/dev/vda1 1000 500 500 50% /other"
            fi
            data=$(printf '%s\n' "$df" | base64 -w0)
            printf '{"return":{"exited":true,"exitcode":0,"out-data":"%s"}}\n' "$data" ;;
        esac ;;
      *) exit 1 ;;
    esac ;;
  *) exit 1 ;;
esac
MOCK
chmod +x "$TMP/bin/virsh"
export PATH="$TMP/bin:$PATH"
export MOCK_FREE=50 MOCK_SCENARIO=''
passed=0; failed=0
check() {
  local title=$1 expected=$2 pattern=$3; shift 3
  local output rc
  output=$(bash "$PLUGIN" "$@" 2>&1); rc=$?
  if [[ $rc -eq $expected && $output == *"$pattern"* ]]; then
    printf 'PASS %s\n' "$title"; ((passed+=1))
  else
    printf 'FAIL %s: exit=%s expected=%s output=%s\n' "$title" "$rc" "$expected" "$output"; ((failed+=1))
  fi
}
base=(-d example-vm -p / -w 20% -c 10%)
check version 0 '1.0.1' --version
check help 0 'Usage:' --help
check missing_arguments 3 'required' -d example-vm
check invalid_threshold 3 'whole percentages' -d example-vm -p / -w abc -c 10
check reversed_threshold 3 'greater than' -d example-vm -p / -w 10 -c 20
check invalid_timeout 3 'positive integer' "${base[@]}" -t 0
check ok 0 'DISK OK:' "${base[@]}"
check perfdata 0 "'/_free_pct'=50%;@0:20;@0:10;0;100" "${base[@]}"
export MOCK_FREE=20; check warning_boundary 1 'DISK WARNING:' "${base[@]}"
export MOCK_FREE=21; check warning_above 0 'DISK OK:' "${base[@]}"
export MOCK_FREE=10; check critical_boundary 2 'DISK CRITICAL:' "${base[@]}"
export MOCK_FREE=11; check critical_above 1 'DISK WARNING:' "${base[@]}"
export MOCK_FREE=0; check zero_free 2 'DISK CRITICAL:' "${base[@]}"
export MOCK_FREE=50
export MOCK_SCENARIO=vm_missing; check vm_missing 3 'virsh command failed' "${base[@]}"
export MOCK_SCENARIO=vm_off; check vm_off 3 'not running' "${base[@]}"
export MOCK_SCENARIO=agent_failure; check agent_failure 3 'guest-exec did not return a valid PID' "${base[@]}"
export MOCK_SCENARIO=guest_failure; check guest_failure 3 'guest df failed' "${base[@]}"
export MOCK_SCENARIO=invalid_base64; check invalid_base64 3 'invalid base64' "${base[@]}"
export MOCK_SCENARIO=missing_mount; check missing_mount 3 'not found' "${base[@]}"
export MOCK_SCENARIO=timeout; check timeout 3 'UNKNOWN:' "${base[@]}" -t 1
printf '\nTests: %d passed, %d failed\n' "$passed" "$failed"
((failed == 0))
