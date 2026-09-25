#!/bin/bash
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PLUGIN="$ROOT/plugins/check_librenms_validate"
PASS=0
FAIL=0

run_case() {
    name="$1"
    expected_rc="$2"
    expected_text="$3"
    validate_rc="$4"
    validate_output="$5"

    tmp=$(mktemp -d)
    mkdir -p "$tmp/bin" "$tmp/opt/librenms"

    cat > "$tmp/bin/id" <<'EOF'
#!/bin/sh
exit 0
EOF

    cat > "$tmp/bin/sudo" <<EOF
#!/bin/sh
cat <<'OUTPUT'
$validate_output
OUTPUT
exit $validate_rc
EOF

    cat > "$tmp/bin/timeout" <<'EOF'
#!/bin/sh
while [ "$#" -gt 0 ]; do
    case "$1" in
        --signal=*|--kill-after=*) shift ;;
        *s) shift; break ;;
        *) shift ;;
    esac
done
exec "$@"
EOF

    chmod +x "$tmp/bin/id" "$tmp/bin/sudo" "$tmp/bin/timeout"

    sed "s#VALIDATE=\"/opt/librenms/validate.php\"#VALIDATE=\"$tmp/opt/librenms/validate.php\"#" \
        "$PLUGIN" > "$tmp/check"
    chmod +x "$tmp/check"
    : > "$tmp/opt/librenms/validate.php"
    chmod 644 "$tmp/opt/librenms/validate.php"

    set +e
    output=$(PATH="$tmp/bin:/usr/bin:/bin" "$tmp/check" 2>&1)
    rc=$?
    set -e

    if [ "$rc" -eq "$expected_rc" ] && printf '%s\n' "$output" | grep -Fq "$expected_text"; then
        printf 'PASS: %s\n' "$name"
        PASS=$((PASS + 1))
    else
        printf 'FAIL: %s\n' "$name"
        printf '  expected rc: %s, actual rc: %s\n' "$expected_rc" "$rc"
        printf '  expected text: %s\n' "$expected_text"
        printf '  output: %s\n' "$output"
        FAIL=$((FAIL + 1))
    fi

    rm -rf "$tmp"
}

set -e

run_case "OK result" 0 \
    "LIBRENMS OK: validation successful - 0 failures, 0 warnings | failures=0 warnings=0" \
    0 "[OK]    Database Connected"

run_case "WARNING result" 1 \
    "LIBRENMS WARNING: 1 warning - Test warning | failures=0 warnings=1" \
    0 "[WARN]  Test warning"

run_case "CRITICAL result" 2 \
    "LIBRENMS CRITICAL: 1 failure - Test failure | failures=1 warnings=0" \
    0 "[FAIL]  Test failure"

run_case "FAIL takes priority over WARN" 2 \
    "LIBRENMS CRITICAL: 1 failure, 1 warning - Test failure; warnings: Test warning | failures=1 warnings=1" \
    0 "[WARN]  Test warning
[FAIL]  Test failure"

run_case "ANSI WARNING" 1 \
    "LIBRENMS WARNING: 1 warning - ANSI warning | failures=0 warnings=1" \
    0 "$(printf '[\033[1;33mWARN\033[0m]  ANSI warning')"

run_case "ANSI CRITICAL" 2 \
    "LIBRENMS CRITICAL: 1 failure - ANSI failure | failures=1 warnings=0" \
    0 "$(printf '[\033[1;31mFAIL\033[0m]  ANSI failure')"

run_case "Multiple warnings" 1 \
    "LIBRENMS WARNING: 2 warnings - Warning one; Warning two | failures=0 warnings=2" \
    0 "[WARN]  Warning one
[WARN]  Warning two"

run_case "Execution failure" 3 \
    "LIBRENMS UNKNOWN: validate.php exited with code 5:" \
    5 "PHP Fatal error: test failure"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
