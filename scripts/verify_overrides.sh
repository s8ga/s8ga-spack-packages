#!/bin/bash
#
# verify_overrides.sh — Verify force_avx512 compatibility with upstream sources
#
# Uses `spack stage` (downloads source tarballs, NOT git clones) to verify that
# our force_avx512 / force_all_x86_kernel modifications are compatible with the
# actual upstream build files (Makefile, configure, configure.ac, Makefile.am).
#
# Usage:
#   ./scripts/verify_overrides.sh                              # default versions
#   ./scripts/verify_overrides.sh --openblas 0.3.33            # specific version
#   ./scripts/verify_overrides.sh --elpa 2026.02.002           # specific version
#   ./scripts/verify_overrides.sh --fftw 3.3.11                # specific version
#   ./scripts/verify_overrides.sh --openblas 0.3.33 --fftw 3.3.11  # multiple
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed (force_avx512 may be broken)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OVERRIDE_DIR="$REPO_ROOT/spack_repo/s8_overrides/packages"

# Default versions (matching current ABACUS env pins + latest builtin)
OPENBLAS_VERSIONS=("0.3.30" "0.3.33")
ELPA_VERSIONS=("2025.01.001" "2026.02.001" "2026.02.002")
FFTW_VERSIONS=("3.3.10" "3.3.11")

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --openblas) OPENBLAS_VERSIONS=("$2"); shift 2 ;;
        --elpa)     ELPA_VERSIONS=("$2");     shift 2 ;;
        --fftw)     FFTW_VERSIONS=("$2");     shift 2 ;;
        --help|-h)
            head -20 "$0" | tail -18
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

PASS=0
FAIL=0

ok()   { echo "  [PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

echo ""
echo "================================================================"
echo "  force_avx512 upstream build file compatibility verification"
echo "  (spack stage — source tarballs, NOT git clones)"
echo "================================================================"
echo ""

# Helper: find the actual source directory inside a spack stage
# spack extracts source into $stage/spack-src/ (or similar)
stage_src_dir() {
    local stage="$1"
    # Try spack-src first (most common), then fall back to any single subdir
    if [[ -d "$stage/spack-src" ]]; then
        echo "$stage/spack-src"
    else
        # Find the first directory containing the file we need
        find "$stage" -maxdepth 2 -type d | tail -1
    fi
}

# --- OpenBLAS ---
# Verification: NO_AVX512 make variable still exists in Makefile.system
# Our package.py adds +force_avx512 to suppress NO_AVX512=1 conditionally.
# If upstream removes NO_AVX512, our override breaks silently.
verify_openblas() {
    local version="$1"
    echo "-- OpenBLAS@$version --"
    local stage
    stage="$(spack location -s "openblas@$version" 2>/dev/null || true)"
    if [[ -z "$stage" || ! -d "$stage" ]]; then
        echo "  Staging openblas@$version ..."
        spack stage "openblas@$version" >/dev/null 2>&1 || true
        stage="$(spack location -s "openblas@$version" 2>/dev/null || true)"
    fi
    if [[ -z "$stage" || ! -d "$stage" ]]; then
        fail "Cannot stage openblas@$version"
        return
    fi
    local src
    src="$(stage_src_dir "$stage")"
    if grep -q 'NO_AVX512' "$src/Makefile.system" 2>/dev/null; then
        ok "NO_AVX512 found in Makefile.system ($(grep -c 'NO_AVX512' "$src/Makefile.system") matches)"
    else
        fail "NO_AVX512 NOT found in Makefile.system — force_avx512 will be broken!"
    fi
    echo ""
}

# --- FFTW ---
# Verification: --enable-avx512 configure flag still supported
# Our package.py forces --enable-avx512 when +force_avx512.
# If upstream removes avx512 from configure, our override breaks.
verify_fftw() {
    local version="$1"
    echo "-- FFTW@$version --"
    local stage
    stage="$(spack location -s "fftw@$version" 2>/dev/null || true)"
    if [[ -z "$stage" || ! -d "$stage" ]]; then
        echo "  Staging fftw@$version ..."
        spack stage "fftw@$version" >/dev/null 2>&1 || true
        stage="$(spack location -s "fftw@$version" 2>/dev/null || true)"
    fi
    if [[ -z "$stage" || ! -d "$stage" ]]; then
        fail "Cannot stage fftw@$version"
        return
    fi
    local src
    src="$(stage_src_dir "$stage")"
    if grep -q 'avx512' "$src/configure" 2>/dev/null; then
        ok "avx512 SIMD option found in configure ($(grep -c 'avx512' "$src/configure") matches)"
    else
        fail "avx512 NOT found in configure — force_avx512 will be broken!"
    fi
    echo ""
}

# --- ELPA ---
# Verification: 3 patches apply cleanly via --dry-run
# ELPA is the most fragile: configure and Makefile.in patches use exact
# line numbers. Must verify per-version.
verify_elpa() {
    local version="$1"
    echo "-- ELPA@$version --"
    local stage
    stage="$(spack location -s "elpa@$version" 2>/dev/null || true)"
    if [[ -z "$stage" || ! -d "$stage" ]]; then
        echo "  Staging elpa@$version ..."
        spack stage "elpa@$version" >/dev/null 2>&1 || true
        stage="$(spack location -s "elpa@$version" 2>/dev/null || true)"
    fi
    if [[ -z "$stage" || ! -d "$stage" ]]; then
        fail "Cannot stage elpa@$version"
        return
    fi
    local src
    src="$(stage_src_dir "$stage")"

    # Select version-gated patches matching package.py when= conditions.
    # sort -V: true when first arg <= second (input already sorted ascending).
    version_ge() { printf '%s\n%s\n' "$1" "$2" | sort -C -V; }

    local patches=("force_all_x86_kernel.patch")
    if version_ge "2026.02.002" "$version"; then
        patches+=("force_avx512_configure-2026.02.002.patch")
    else
        patches+=("force_avx512_configure.patch")
    fi
    if version_ge "2026.02.001" "$version"; then
        patches+=("force_avx512_makefile_in-2026.patch")
    else
        patches+=("force_avx512_makefile_in.patch")
    fi

    # Check each selected patch with --dry-run
    for patch_name in "${patches[@]}"; do
        local patch_file="$OVERRIDE_DIR/elpa/${patch_name}"
        if [[ ! -f "$patch_file" ]]; then
            fail "$patch_name file not found"
            continue
        fi
        if (cd "$src" && patch --dry-run -p1 < "$patch_file" >/dev/null 2>&1); then
            ok "$patch_name applies cleanly"
        else
            fail "$patch_name FAILED — needs regeneration for this version!"
        fi
    done
    echo ""
}

# --- Run all verifications ---
for v in "${OPENBLAS_VERSIONS[@]}"; do verify_openblas "$v"; done
for v in "${ELPA_VERSIONS[@]}";     do verify_elpa "$v"; done
for v in "${FFTW_VERSIONS[@]}";     do verify_fftw "$v"; done

# --- Summary ---
echo "================================================================"
if [[ $FAIL -eq 0 ]]; then
    echo "[PASS] All $PASS checks passed — force_avx512 is compatible!"
    exit 0
else
    echo "[FAIL] $FAIL failed, $PASS passed — check details above"
    exit 1
fi
