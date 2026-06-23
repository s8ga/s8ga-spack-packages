# AGENTS.md — abacus_spack repo guide for AI agents

## Repository Structure

```
spack_repo/
  s8_custom_repo/          # ABACUS original packages (not in spack builtin)
    repo.yaml              # namespace: s8_custom_repo, api: v2.5
    packages/
      abacus/              # Main package: 9 versions, 36 variants
      libri/               # Header-only
      libcomm/             # Header-only
      libnpy/              # Header-only
      nep_cpu/             # NEP v1.4 (dir=underscore, name=hyphen)
  s8_overrides/            # Builtin package overrides (+force_avx512)
    repo.yaml              # namespace: s8_overrides, api: v2.5
    packages/
      openblas/            # +force_avx512 variant
      elpa/                # +force_all_x86_kernel variant + 3 patches
      fftw/                # +force_avx512 variant
scripts/
  verify_overrides.sh      # Verify upstream build file compatibility
```

## Repo Registration

Use **env-scoped** repos, not global:

```bash
# Register in a spack env (priority: first added = highest)
spack -e <env> repo add /path/to/spack_repo/s8_overrides
spack -e <env> repo add /path/to/spack_repo/s8_custom_repo

# Verify
spack -e <env> repo list
# Should show: s8_custom_repo > s8_overrides > builtin
```

**Never use global `spack repo add`** — it affects all envs and causes
namespace conflicts when multiple envs need different package versions.

## s8_overrides: force_avx512

### What it does

Allows building AVX512 kernels on non-AVX512 hosts (target=x86_64_v3),
with runtime CPUID dispatch for portability. Used in HPC mixed-ISA clusters.

### Per-package changes vs builtin

| Package | Changes | Upstream patches |
|---------|---------|-----------------|
| openblas | 1 variant + 1 condition (`NO_AVX512`) | None |
| fftw | 1 variant + 1 SIMD loop condition | None |
| elpa | 1 variant + 3 `patch()` + simd_features restructure | 3 custom patches |

### Future Rebase Workflow

When spack-packages updates (new tag), rebase s8_overrides:

```bash
# 1. Run verification script to check compatibility
./scripts/verify_overrides.sh
# Or for specific new versions:
./scripts/verify_overrides.sh --openblas 0.3.34 --elpa 2026.05.001 --fftw 3.3.12

# 2. If ALL pass (exit 0):
#    a. Copy new builtin package.py + data files
BUILTIN=$(spack location -p openblas)
cp $BUILTIN/package.py spack_repo/s8_overrides/packages/openblas/
cp $BUILTIN/*.patch spack_repo/s8_overrides/packages/openblas/  # data files

#    b. Re-apply force_avx512 delta (2-3 edits per package, see below)
#    c. Run verification again to confirm

# 3. If ELPA patches FAIL:
#    a. spack stage elpa@<new_version>
#    b. cd $(spack location -s elpa@<new_version>)/spack-src
#    c. Regenerate patches from source (context-based, fuzz=2)
#    d. Update sha256 in package.py
#    e. Re-run verify_overrides.sh
```

### force_avx512 delta (exact changes to re-apply after rebase)

**openblas** (2 edits):
1. Add `variant("force_avx512", default=False, ...)` after other variants
2. In `_make_defs`: change `if not target=x86_64_v4:` to also check `and not +force_avx512`

**fftw** (2 edits):
1. Add `variant("force_avx512", default=False, ...)` after other variants
2. In SIMD loop: add `if feature == "avx512" and +force_avx512: msg = "--enable-{0}"`

**elpa** (3 edits):
1. Add `variant("force_all_x86_kernel", default=False, ...)`
2. Add 3 `patch()` declarations with sha256
3. In `setup_execution_flags`: split `avx512` from simd_features into `x86_force_features`, add if/else

### Verification script

`scripts/verify_overrides.sh` uses `spack stage` (downloads source tarballs,
NOT git clones). Total download ~11MB. Checks:
- OpenBLAS: `NO_AVX512` variable in `Makefile.system`
- FFTW: `avx512` in `configure` script
- ELPA: `patch --dry-run` for all 3 custom patches

## ABACUS package patches

### Patch files in s8_custom_repo/packages/abacus/

| Patch | When | Purpose |
|-------|------|---------|
| `lts-pexsi-compile.patch` | `@3.10 +pexsi` | LTS PEXSI compile fix (missing include + Gint signature) |
| `v3.9.0.10-cstdint.patch` | `@3.9.0.10` | uint64_t without `#include <cstdint>` |
| `pexsi-tests-copyable-3.9.patch` | `@3.9.0.10:3.9.0.27 +pexsi +tests` | Group A: copy ctor + scalapack_connector.h include |
| `pexsi-tests-copyable-3.9.patch` | `@3.11.0-beta.4 +pexsi +tests` | Group A (same patch, different version) |
| `pexsi-tests-copyable-3.10.patch` | `@3.10 +pexsi +tests` | Group B: copy ctor only |

### PEXSI copy ctor bug

`Parallel_2D` declares move ops → implicitly deletes copy ctor →
`PexsiPrepare` non-copyable → GoogleTest `TestWithParam<T>` fails.
Fix: explicit copy ctor copying all members except `po` (Parallel_Orbitals).

## ABACUS Key Design Decisions

### Version-variant mapping

| Variant | Versions | CMake option |
|---------|----------|-------------|
| `+deepks` | `@3.10` (LTS) | `ENABLE_DEEPKS` |
| `+mlalgo` | `@3.9.0.10:` (develop) | `ENABLE_MLALGO` |

These are version-disjoint (upstream renamed the CMake option). Never enable both.

### Dependency quirks

- **py-torch**: constrained to `@2.1:2.4` (`torch::linalg` removed in 2.5). Needs `--deprecated` flag for `@2.4.1`.
- **nep-cpu**: uses `src/` not `libs/` (NEP3 renamed to NEP in v1.4). Manual `ar libnep.a`.
- **dftd4**: `build_system=cmake` required (meson default produces no cmake config; PR #7380).
- **elpa**: variant gated on `when="+lcao+mpi"` (stronger than explicit `conflicts()`).
- **GoogleTest**: via `resource()` not `depends_on()` (self-contained, offline, nnpack precedent).
- **test path rewriting**: `filter_file` in `def patch()` (not `@run_before`) (spack convention).
- **KML**: upstream stub (`FindKML.cmake` is TODO), variant exists but no `depends_on`.

### Supported versions

`3.10.0-lts`, `3.10.1-lts`, `3.9.0.10`, `3.9.0.15`, `3.9.0.20`, `3.9.0.25`, `3.9.0.27`, `3.11.0-beta.4`

## Testing Infrastructure (4 layers)

| Layer | What | Always runs? |
|-------|------|:---:|
| L1 | `sanity_check_is_file = [join_path("bin", "abacus")]` | Yes |
| L2 | `test_version()` + `test_info()` smoke tests | Yes |
| L3 | `+tests` variant: GoogleTest unit tests (resource gtest v1.14.0) | No (needs `+tests`) |
| L4 | Autotest.sh integration tests (MPI, CASES_CPU.txt) | Manual |

Test results: 3.9.0.27 = 235/235 pass, beta.4 = 238/239+1 skip (100%).

## HPC Container Factory Integration

This repo is consumed by HPC-Container-Factory envs:

```
HPC-Container-Factory/spack-envs/
  abacus_opensource-3.10.1-force-avx512/   # LTS + force_avx512
  abacus_opensource-3.9.0.27-force-avx512/ # develop + force_avx512
```

Each env's `env.yaml` registers repos via `custom_repos` with `path: repos`.
Container envs use a combined `repos/` dir (single namespace `abacus-env`);
our repo splits into `s8_custom_repo` + `s8_overrides` for cleaner maintenance.

## Conventions

- spack v2.5 repo format: `api: v2.5` in repo.yaml
- Package dirs use underscores (`nep_cpu`), spack auto-translates to hyphens (`nep-cpu`)
- All LSP errors (spack imports) are expected — resolved at spack runtime
- `--deprecated` flag needed for `py-torch@2.4.1`
- `reuse: true` in env can cause stale builds — use `concretize -f` after package.py changes
- Verify AVX512 kernels: `objdump -d libfoo.so | grep -c zmm`
