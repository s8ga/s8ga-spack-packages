#!/bin/bash
#
# abacus_run_module_tests.sh — Batch run ABACUS module unit tests
#
# Resolves the tests tree (see resolve order below) and runs unit-test
# executables. Develop/3.9/beta use MODULE_* names under source_*/test*;
# LTS 3.10 uses module_*/test* with names like dm_mixing_test / base_matrix3.
# Strategy: prefer MODULE_* when present; otherwise run ELF executables under
# source_*/test* or module_*/test*. Each test runs from its own directory so
# ./support/ and ./PP_ORB/ resolve correctly.
#
# Resolution order for tests root:
#   1. $ABACUS_TESTS
#   2. $ABACUS_PREFIX/share/abacus/tests
#   3. $(dirname $(dirname $(command -v abacus)))/share/abacus/tests
#   4. legacy /opt/spack/linux-x86_64_v3/abacus-*/share/abacus/tests
#
# Usage (local / container):
#   ABACUS_PREFIX=$(spack -e abacus-lts location -i abacus) \
#     bash scripts/abacus_run_module_tests.sh
#
#   # or after: eval "$(spack -e abacus-lts load --sh abacus)"
#   bash scripts/abacus_run_module_tests.sh

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

# Shared find exclusions: integration trees, support/data, non-binaries.
_find_excludes=(
    -not -path "*/support/*" -not -path "*/data/*"
    -not -path "*/CMakeFiles/*" -not -path "*/.spack/*"
    -not -path "*/PP_ORB/*"
    -not -path "*/01_PW/*" -not -path "*/02_NAO*" -not -path "*/03_NAO*"
    -not -path "*/04_FF/*" -not -path "*/05_rt*" -not -path "*/06_SDFT/*"
    -not -path "*/07_OFDFT/*" -not -path "*/08_EXX/*" -not -path "*/09_DeePKS/*"
    -not -path "*/10_others/*" -not -path "*/integrate/*"
    -not -path "*/libxc/*" -not -path "*/deepks/*" -not -path "*/performance/*"
)

is_elf() {
    local magic
    magic=$(head -c 4 "$1" 2>/dev/null || true)
    [[ "$magic" == $'\x7fELF' ]]
}

# Discover unit-test binaries under source_*/test* or module_*/test*.
# Prefer MODULE_* (develop); else ELF executables (LTS naming).
discover_unit_tests() {
    local tests_root="$1"
    local -a module_bins=()
    local -a elf_bins=()
    local f

    while IFS= read -r f; do
        [[ -x "$f" ]] || continue
        module_bins+=("$f")
    done < <(find "$tests_root" -type f -executable -name 'MODULE_*' \
        "${_find_excludes[@]}" 2>/dev/null | sort)

    if [[ ${#module_bins[@]} -gt 0 ]]; then
        printf '%s\n' "${module_bins[@]}"
        return 0
    fi

    while IFS= read -r f; do
        [[ -x "$f" ]] || continue
        case "$f" in
            *.sh|*.py|*.txt|*.md|*.dat|*.csv|*.json|*.yml|*.yaml|*.orb|*.UPF|*.upf)
                continue ;;
        esac
        is_elf "$f" || continue
        elf_bins+=("$f")
    done < <(find "$tests_root" -type f -executable \
        \( -path '*/source_*/test*' -o -path '*/module_*/test*' \) \
        "${_find_excludes[@]}" 2>/dev/null | sort)

    if [[ ${#elf_bins[@]} -gt 0 ]]; then
        printf '%s\n' "${elf_bins[@]}"
    fi
}

TESTS="$(resolve_tests_root || true)"
if [[ -z "$TESTS" || ! -d "$TESTS" ]]; then
    echo "ERROR: Cannot find ABACUS tests dir." >&2
    echo "  Set ABACUS_TESTS, ABACUS_PREFIX, or put abacus on PATH." >&2
    exit 1
fi

echo "================================================================"
echo "  ABACUS Module Unit Tests"
echo "  $TESTS"
echo "================================================================"
echo ""

PASS=0
FAIL=0
FAILED_TESTS=""
START=$(date +%s)

mapfile -t TEST_BINS < <(discover_unit_tests "$TESTS")
if [[ ${#TEST_BINS[@]} -eq 0 ]]; then
    echo "ERROR: No unit-test binaries found under $TESTS" >&2
    echo "  Expected MODULE_* (develop) or ELF executables under" >&2
    echo "  source_*/test* / module_*/test* (LTS)." >&2
    exit 1
fi

for test_bin in "${TEST_BINS[@]}"; do
    [[ -x "$test_bin" ]] || continue
    name=$(basename "$test_bin")
    dir=$(dirname "$test_bin")

    echo "--- $name ---"
    t0=$(date +%s)

    rc=0
    (cd "$dir" && timeout 30 ./"$name" 2>&1) || rc=$?

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
TOTAL=$((PASS + FAIL))

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
