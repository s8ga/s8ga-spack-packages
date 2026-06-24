#!/bin/bash
#
# abacus_run_module_tests.sh — Batch run ABACUS MODULE_* unit tests
#
# Auto-discovers the ABACUS install under /opt/spack/linux-x86_64_v3/
# and runs all MODULE_* unit-test executables sequentially.
#
# Usage (inside container):
#   podman run --rm --network=host \
#     -v $PWD/scripts/abacus_run_module_tests.sh:/tmp/run_tests.sh:ro \
#     abacus_opensource:3.9.0.27-force-avx512 bash /tmp/run_tests.sh

set -eu

TESTS="$(ls -d /opt/spack/linux-x86_64_v3/abacus-*/share/abacus/tests 2>/dev/null | head -1)"
if [[ -z "$TESTS" ]]; then
    echo "ERROR: Cannot find test dir under /opt/spack/linux-x86_64_v3/" >&2
    exit 1
fi

echo "================================================================"
echo "  ABACUS Module Unit Tests"
echo "  $TESTS"
echo "================================================================"
echo ""

PASS=0
FAIL=0
SKIP=0
FAILED_TESTS=""
START=$(date +%s)

for test_bin in "$TESTS"/MODULE_*; do
    [[ -x "$test_bin" ]] || continue
    name=$(basename "$test_bin")

    # Skip test-specific data dirs that match MODULE_* pattern
    [[ -d "$test_bin" ]] && continue

    echo "--- $name ---"
    t0=$(date +%s)

    rc=0
    (cd "$TESTS" && ./"$name" 2>&1) || rc=$?

    t1=$(date +%s)
    if [[ $rc -eq 0 ]]; then
        echo "[PASS] $name — $((t1 - t0))s"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $name — $((t1 - t0))s (rc=$rc)"
        FAIL=$((FAIL + 1))
        FAILED_TESTS="${FAILED_TESTS}\n  $name"
    fi
    echo ""
done

END=$(date +%s)
ELAPSED=$((END - START))
TOTAL=$((PASS + FAIL + SKIP))

echo "================================================================"
echo "  Summary"
echo "================================================================"
printf "  %-10s %d\n" "Total:"   "$TOTAL"
printf "  %-10s %d\n" "Passed:"  "$PASS"
printf "  %-10s %d\n" "Failed:"  "$FAIL"
printf "  %-10s %ds\n" "Time:"   "$ELAPSED"
if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "  Failed tests:"
    echo -e "$FAILED_TESTS"
fi
echo "================================================================"

[[ $FAIL -gt 0 ]] && exit 1
exit 0
