#!/bin/bash
#
# abacus_run_integration_tests.sh — Batch run ABACUS integration tests (01–10)
#
# Resolves the tests tree and abacus binary, then runs Autotest.sh groups
# sequentially with ``-a <abacus>``.
#
# Resolution order for tests root:
#   1. $ABACUS_TESTS
#   2. $ABACUS_PREFIX/share/abacus/tests
#   3. $(dirname $(dirname $(command -v abacus)))/share/abacus/tests
#   4. legacy /opt/spack/linux-x86_64_v3/abacus-*/share/abacus/tests
#
# Usage (local / container):
#   ABACUS_PREFIX=$(spack -e abacus-lts location -i abacus) \
#     bash scripts/abacus_run_integration_tests.sh

set -eu

resolve_tests_root() {
    if [[ -n "${ABACUS_TESTS:-}" ]]; then
        printf '%s\n' "$ABACUS_TESTS"
        return 0
    fi
    if [[ -n "${ABACUS_PREFIX:-}" ]]; then
        printf '%s\n' "$ABACUS_PREFIX/share/abacus/tests"
        return 0
    fi
    if command -v abacus >/dev/null 2>&1; then
        local prefix
        prefix="$(dirname "$(dirname "$(command -v abacus)")")"
        if [[ -d "$prefix/share/abacus/tests" ]]; then
            printf '%s\n' "$prefix/share/abacus/tests"
            return 0
        fi
    fi
    # Legacy container layout
    ls -d /opt/spack/linux-x86_64_v3/abacus-*/share/abacus/tests 2>/dev/null | head -1
}

resolve_abacus_bin() {
    if [[ -n "${ABACUS_PREFIX:-}" && -x "${ABACUS_PREFIX}/bin/abacus" ]]; then
        printf '%s\n' "$ABACUS_PREFIX/bin/abacus"
        return 0
    fi
    if command -v abacus >/dev/null 2>&1; then
        command -v abacus
        return 0
    fi
    return 1
}

TESTS="$(resolve_tests_root || true)"
if [[ -z "$TESTS" || ! -d "$TESTS" ]]; then
    echo "ERROR: Cannot find ABACUS tests dir." >&2
    echo "  Set ABACUS_TESTS, ABACUS_PREFIX, or put abacus on PATH." >&2
    exit 1
fi

AUTOTEST="$TESTS/integrate/Autotest.sh"
if [[ ! -f "$AUTOTEST" ]]; then
    echo "ERROR: Autotest.sh not found at $AUTOTEST" >&2
    exit 1
fi

ABACUS_BIN="$(resolve_abacus_bin || true)"
if [[ -z "$ABACUS_BIN" ]]; then
    echo "ERROR: Cannot find abacus binary (set ABACUS_PREFIX or PATH)." >&2
    exit 1
fi

DIRS="01_PW 02_NAO_Gamma 03_NAO_multik 04_FF 05_rtTDDFT 06_SDFT 07_OFDFT 08_EXX 09_DeePKS 10_others"

echo "================================================================"
echo "  ABACUS Integration Tests"
echo "  $TESTS"
echo "  abacus: $ABACUS_BIN"
echo "================================================================"
echo ""

PASS=0
FAIL=0
SKIP=0
START=$(date +%s)

for dir in $DIRS; do
    if [[ ! -d "$TESTS/$dir" ]]; then
        echo "[SKIP] $dir not found"
        SKIP=$((SKIP + 1))
        continue
    fi

    cases="$TESTS/$dir/CASES_CPU.txt"
    if [[ ! -f "$cases" ]]; then
        echo "[SKIP] $dir: no CASES_CPU.txt"
        SKIP=$((SKIP + 1))
        continue
    fi

    n=$(grep -cE '^[^#].*_.*$' "$cases" 2>/dev/null || echo "?")

    echo "--- $dir ($n cases) ---"
    t0=$(date +%s)

    rc=0
    (cd "$TESTS/$dir" && bash "$AUTOTEST" -a "$ABACUS_BIN") || rc=$?

    t1=$(date +%s)
    if [[ $rc -eq 0 ]]; then
        echo "[PASS] $dir — $((t1 - t0))s"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $dir — $((t1 - t0))s (rc=$rc)"
        FAIL=$((FAIL + 1))
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
printf "  %-10s %d\n" "Skipped:" "$SKIP"
printf "  %-10s %ds\n" "Time:"   "$ELAPSED"
echo "================================================================"

[[ $FAIL -gt 0 ]] && exit 1
exit 0
