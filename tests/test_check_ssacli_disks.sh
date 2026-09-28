#!/usr/bin/env bash

set -u

PLUGIN="${PLUGIN:-plugins/check_ssacli_disks.sh}"

PASS=0
FAIL=0

pass() {
    printf 'PASS: %s\n' "$1"
    PASS=$((PASS + 1))
}

fail() {
    printf 'FAIL: %s\n' "$1"
    printf '      %s\n' "$2"
    FAIL=$((FAIL + 1))
}

assert_check() {
    name="$1"
    expected_rc="$2"
    expected_text="$3"
    mock_mode="$4"

    output="$(
        SSACLI_BIN="$MOCK_SSACLI" \
        MOCK_MODE="$mock_mode" \
        "$PLUGIN" 2>&1
    )"
    rc=$?

    if [[ "$rc" -ne "$expected_rc" ]]; then
        fail "$name" "expected exit $expected_rc, got $rc: $output"
        return
    fi

    if [[ "$output" != *"$expected_text"* ]]; then
        fail "$name" "expected '$expected_text', got: $output"
        return
    fi

    pass "$name"
}

TEST_TMP="$(mktemp -d)"
trap 'rm -rf "$TEST_TMP"' EXIT

MOCK_SSACLI="$TEST_TMP/ssacli"

cat > "$MOCK_SSACLI" <<'EOF'
#!/usr/bin/env bash

mode="${MOCK_MODE:-healthy}"

if [[ "$1" == "ctrl" && "$2" == "all" && "$3" == "show" ]]; then
    case "$mode" in
        controller_error)
            echo "Error: controller query failed" >&2
            exit 1
            ;;
        no_controller)
            echo "No controllers detected"
            exit 0
            ;;
        multi_controller)
            cat <<OUT
Smart Array P408i-a SR Gen10 in Slot 0
Smart Array P816i-a SR Gen10 in Slot 1
OUT
            exit 0
            ;;
        *)
            echo "Smart Array P408i-a SR Gen10 in Slot 0"
            exit 0
            ;;
    esac
fi

if [[ "$1" == "ctrl" && "$2" == slot=* &&
      "$3" == "pd" && "$4" == "all" &&
      "$5" == "show" && "$6" == "detail" ]]; then

    slot="${2#slot=}"

    case "$mode" in
        drive_query_error)
            echo "Error: physical drive query failed" >&2
            exit 2
            ;;

        no_drives)
            echo "No physical drives present"
            exit 0
            ;;

        failed_drive)
            cat <<OUT
physicaldrive 1I:1:1
   Status: OK

physicaldrive 1I:1:2
   Status: Failed
OUT
            exit 0
            ;;

        multiple_failed_drives)
            cat <<OUT
physicaldrive 1I:1:1
   Status: Failed

physicaldrive 1I:1:2
   Status: Predictive Failure

physicaldrive 1I:1:3
   Status: OK
OUT
            exit 0
            ;;

        missing_status)
            cat <<OUT
physicaldrive 1I:1:1
   Status: OK

physicaldrive 1I:1:2
OUT
            exit 0
            ;;

        multi_controller)
            if [[ "$slot" == "0" ]]; then
                cat <<OUT
physicaldrive 1I:1:1
   Status: OK

physicaldrive 1I:1:2
   Status: OK
OUT
            else
                cat <<OUT
physicaldrive 2I:1:1
   Status: OK

physicaldrive 2I:1:2
   Status: OK
OUT
            fi
            exit 0
            ;;

        *)
            cat <<OUT
physicaldrive 1I:1:1
   Status: OK

physicaldrive 1I:1:2
   Status: OK

physicaldrive 1I:1:3
   Status: OK

physicaldrive 1I:1:4
   Status: OK

physicaldrive 2I:1:5
   Status: OK

physicaldrive 2I:1:6
   Status: OK

physicaldrive 2I:1:7
   Status: OK

physicaldrive 2I:1:8
   Status: OK
OUT
            exit 0
            ;;
    esac
fi

echo "Unexpected ssacli arguments: $*" >&2
exit 99
EOF

chmod 755 "$MOCK_SSACLI"

echo "Running check_ssacli_disks.sh tests..."
echo

# CLI tests

output="$("$PLUGIN" --version 2>&1)"
rc=$?

if [[ "$rc" -eq 0 && "$output" == *"1.0.0"* ]]; then
    pass "--version"
else
    fail "--version" "exit=$rc output=$output"
fi

output="$("$PLUGIN" --help 2>&1)"
rc=$?

if [[ "$rc" -eq 0 && "$output" == *"Usage:"* ]]; then
    pass "--help"
else
    fail "--help" "exit=$rc output=$output"
fi

output="$("$PLUGIN" --definitely-invalid-option 2>&1)"
rc=$?

if [[ "$rc" -eq 3 && "$output" == *"unknown option"* ]]; then
    pass "unknown option returns UNKNOWN"
else
    fail "unknown option returns UNKNOWN" "exit=$rc output=$output"
fi

# Missing ssacli

output="$(
    SSACLI_BIN="$TEST_TMP/does-not-exist" \
    "$PLUGIN" 2>&1
)"
rc=$?

if [[ "$rc" -eq 3 &&
      "$output" == *"ssacli executable not found"* ]]; then
    pass "missing ssacli returns UNKNOWN"
else
    fail "missing ssacli returns UNKNOWN" "exit=$rc output=$output"
fi

# Controller / drive tests

assert_check \
    "controller query failure returns UNKNOWN" \
    3 \
    "failed to query controllers" \
    controller_error

assert_check \
    "no controller returns UNKNOWN" \
    3 \
    "no Smart Array controllers found" \
    no_controller

assert_check \
    "drive query failure returns UNKNOWN" \
    3 \
    "failed to query controller in slot 0" \
    drive_query_error

assert_check \
    "no physical drives returns UNKNOWN" \
    3 \
    "no physical drives found" \
    no_drives

assert_check \
    "healthy drives return OK" \
    0 \
    "SSACLI OK: all 8 physical drive(s) are healthy | drives=8 problems=0" \
    healthy

assert_check \
    "failed drive returns CRITICAL" \
    2 \
    "Drive 1I:1:2 (Failed)" \
    failed_drive

assert_check \
    "multiple failed drives return CRITICAL" \
    2 \
    "2 problematic drive(s) found" \
    multiple_failed_drives

assert_check \
    "missing drive status returns CRITICAL" \
    2 \
    "Drive 1I:1:2 (status unknown)" \
    missing_status

assert_check \
    "multiple controllers are counted" \
    0 \
    "all 4 physical drive(s) are healthy | drives=4 problems=0" \
    multi_controller

echo
echo "Results: $PASS passed, $FAIL failed"

if (( FAIL > 0 )); then
    exit 1
fi

exit 0
