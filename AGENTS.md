# AGENTS.md — s8ga-spack-packages guide for AI agents

## Repository Structure

```
spack_repo/
  abacus/                  # namespace: abacus, api: v2.5
    packages/
      abacus/              # Main package: 9 versions, CUDA via CudaPackage
      libri/               # Header-only
      libcomm/             # Header-only
      libnpy/              # Header-only
      nep_cpu/             # NEP v1.4 (dir=underscore, name=hyphen)
  s8_overrides/            # namespace: s8_overrides, api: v2.5
    packages/
      openblas/            # +force_avx512 variant
      elpa/                # +force_all_x86_kernel + version-gated patches
      fftw/                # +force_avx512 variant
  s8_custom_repo/          # Legacy empty placeholder (repo.yaml only)
scripts/
  verify_overrides.sh              # Verify upstream build file compatibility
  abacus_run_module_tests.sh       # Container: MODULE_* unit tests
  abacus_run_integration_tests.sh  # Container: Autotest.sh integration tests
```

`s8_overrides` last rebased against
[spack/spack-packages](https://github.com/spack/spack-packages)
**`develop@18aeef72`** (local builtin path under `~/.spack/package_repos/`,
api v2.2).

## Repo Registration

Use **env-scoped** repos, not global:

```bash
# Register in a spack env (priority: first added = highest)
spack -e <env> repo add /path/to/spack_repo/s8_overrides
spack -e <env> repo add /path/to/spack_repo/abacus

# Verify
spack -e <env> repo list
# Should show: abacus > s8_overrides > builtin
```

**Never use global `spack repo add`** — it affects all envs and causes
namespace conflicts when multiple envs need different package versions.

Do **not** register empty `s8_custom_repo` unless packages are added back.

## s8_overrides: force_avx512

### What it does

Allows building AVX512 kernels on non-AVX512 hosts (target=x86_64_v3),
with runtime CPUID dispatch for portability. Used in HPC mixed-ISA clusters.

### Per-package changes vs builtin

| Package | Changes | Upstream / custom patches | Supported window |
|---------|---------|---------------------------|------------------|
| openblas | 1 variant + 1 condition (`NO_AVX512`) | None | `@0.3.30:` (`conflicts` `@:0.3.29`) |
| fftw | 1 variant + 1 SIMD loop condition | None (also carries builtin `%gcc@14:` warning fix) | `@3.3.10:` (`conflicts` `@:3.3.9`) |
| elpa | 1 variant + version-gated `patch()` + simd_features restructure | Custom force_* patches + builtin wantDebug | `@2025:` (`conflicts` `@:2024.05.001`) |

### ELPA force patches (version-gated, `@2025:` only)

`conflicts("+force_all_x86_kernel", when="@:2024.05.001")` — older releases are unsupported.

| Patch | `when=` |
|-------|---------|
| `force_all_x86_kernel.patch` | `+force_all_x86_kernel @2025:` |
| `force_avx512_configure.patch` | `+force_all_x86_kernel @2025:2026.02.001` |
| `force_avx512_configure-2026.02.002.patch` | `+force_all_x86_kernel @2026.02.002:` |
| `force_avx512_makefile_in.patch` | `+force_all_x86_kernel @2025.01.001:2025.01.002` |
| `force_avx512_makefile_in-2026.patch` | `+force_all_x86_kernel @2025.06.001:` |

Verified dry-run matrix: `2025.01.001`, `2025.01.002`, `2025.06.001`, `2026.02.001`, `2026.02.002`.
Also synced from builtin: `elpa-2026.02.001-wantDebug.patch` (`@2026.02.001:`).

### Future Rebase Workflow

When spack-packages updates (new develop tip / new library versions):

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
#    d. Record the new spack-packages commit in README.md / this file

# 3. If ELPA patches FAIL:
#    a. spack stage elpa@<new_version>
#    b. cd $(spack location -s elpa@<new_version>)/spack-src
#    c. Regenerate patches from source (context-based, fuzz=2)
#    d. Prefer version-gated patch() entries over one mega-patch
#    e. Update sha256 in package.py + verify_overrides.sh selectors
#    f. Re-run verify_overrides.sh
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
2. Add version-gated `patch()` declarations with sha256 (see table above)
3. In `setup_execution_flags`: split `avx512` from simd_features into `x86_force_features`, add if/else

### Verification script

`scripts/verify_overrides.sh` uses `spack stage` (downloads **official upstream
tarballs** via recipe URL+sha256, NOT git clones, NOT handmade fixtures).

Checks:
- OpenBLAS: `NO_AVX512` variable still exists in `Makefile.system`
- FFTW: `avx512` / `--enable-avx512` still in `configure`
- ELPA: `patch --dry-run` for version-selected force patches

This is a **compatibility / applyability** gate, not a full build or SIMD
content proof. After install, still use `objdump … | grep -c zmm`.

Default versions: OpenBLAS `0.3.30`/`0.3.32`/`0.3.33`, ELPA
`2025.01.001`/`2025.01.002`/`2025.06.001`/`2026.02.001`/`2026.02.002`,
FFTW `3.3.10`/`3.3.11`.

## ABACUS package patches

### Patch files in `spack_repo/abacus/packages/abacus/`

| Patch | When | Purpose |
|-------|------|---------|
| `lts-pexsi-compile.patch` | `@3.10 +pexsi` | LTS PEXSI compile fix (missing include + Gint signature) |
| `lts-cuda13-fix.patch` | `@3.10 +cuda` | LTS CUDA 13 / CCCL compatibility (PR #6772+#6813) |
| `v3.9.0.10-cstdint.patch` | `@3.9.0.10` | `uint64_t` without `#include <cstdint>` |
| `pexsi-tests-copyable-3.9.patch` | `@3.9.0.10:3.9.0.27 +pexsi +tests` | Group A: copy ctor + scalapack_connector.h |
| `pexsi-tests-copyable-3.9.patch` | `@3.11.0-beta.4 +pexsi +tests` | Group A (same patch) |
| `pexsi-tests-copyable-3.11.patch` | `@3.11.0-beta.6: +pexsi +tests` | Group A beta6+: copy ctor only |
| `pexsi-tests-copyable-3.10.patch` | `@3.10 +pexsi +tests` | Group B: copy ctor only |
| `esolver_dp_test-guard-3.9.patch` | `@3.9.0.10:3.9.0.27 +tests` and `@3.11.0-beta.4:3.11.0-beta.5 +tests` | Skip DeePMD unit test when not linked |
| `esolver_dp_test-guard-3.10.patch` | `@3.10 +tests` | Same for LTS layout |

### PEXSI copy ctor bug

`Parallel_2D` declares move ops → implicitly deletes copy ctor →
`PexsiPrepare` non-copyable → GoogleTest `TestWithParam<T>` fails.
Fix: explicit copy ctor copying all members except `po` (Parallel_Orbitals).

## ABACUS Key Design Decisions

### Version-variant mapping

| Variant | Versions | CMake option |
|---------|----------|-------------|
| `+deepks` | `@3.10` (LTS) | `ENABLE_DEEPKS` |
| `+mlalgo` | `@3.9.0.10:` develop (not LTS) | `ENABLE_MLALGO` |

These are version-disjoint (upstream renamed the CMake option). Never enable both.

### CUDA

- `class Abacus(CMakePackage, CudaPackage)` — inherits `+cuda` / `cuda_arch`
- Extra variants when `+cuda +mpi`: `cuda-mpi`, `nccl`, `cusolvermp`, `cublasmp`
- Bidirectional ELPA CUDA constraint (`elpa~cuda` / `elpa+cuda`) so `cuda_arch` unifies
- LTS needs `lts-cuda13-fix.patch` for CUDA 13 toolkits

### Dependency quirks

- **py-torch**: constrained to `@2.1:2.4` (`torch::linalg` removed in 2.5). Needs `--deprecated` flag for `@2.4.1`.
- **nep-cpu**: uses `src/` not `libs/` (NEP3 renamed to NEP in v1.4). Manual `ar libnep.a`.
- **dftd4**: `build_system=cmake` required (meson default produces no cmake config; PR #7380).
- **pexsi** (beta6+): also needs `build_system=cmake` for `PEXSIConfig.cmake`.
- **elpa**: variant gated on `when="+lcao+mpi"` (stronger than explicit `conflicts()`).
- **GoogleTest**: via `resource()` not `depends_on()` (self-contained, offline, nnpack precedent).
- **test path rewriting**: `filter_file` in `def patch()` (not `@run_before`) (spack convention).
- **KML**: upstream stub (`FindKML.cmake` is TODO), variant exists but no `depends_on`.

### Supported versions

`3.10.0-lts`, `3.10.1-lts`, `3.9.0.10`, `3.9.0.15`, `3.9.0.20`, `3.9.0.25`,
`3.9.0.27`, `3.11.0-beta.4`, `3.11.0-beta.6`

## Testing Infrastructure (4 layers)

| Layer | What | Always runs? |
|-------|------|:---:|
| L1 | `sanity_check_is_file = [join_path("bin", "abacus")]` | Yes |
| L2 | `test_version()` + `test_info()` smoke tests | Yes |
| L3 | `+tests` variant: GoogleTest unit tests (resource gtest v1.14.0) | No (needs `+tests`) |
| L4 | Autotest.sh integration tests (MPI, CASES_CPU.txt) | Manual |

Container helpers for L3/L4: `scripts/abacus_run_module_tests.sh`,
`scripts/abacus_run_integration_tests.sh` (expect install under
`/opt/spack/linux-x86_64_v3/`).

## HPC Container Factory Integration

This repo is consumed by HPC-Container-Factory envs:

```
HPC-Container-Factory/spack-envs/
  abacus_opensource-3.10.1-force-avx512/   # LTS + force_avx512
  abacus_opensource-3.9.0.27-force-avx512/ # develop + force_avx512
```

Each env's `env.yaml` registers repos via `custom_repos`. Prefer pointing at
`spack_repo/abacus` + `spack_repo/s8_overrides` (not the empty `s8_custom_repo`).

## Conventions

- spack v2.5 repo format: `api: v2.5` in repo.yaml
- Package dirs use underscores (`nep_cpu`), spack auto-translates to hyphens (`nep-cpu`)
- All LSP errors (spack imports) are expected — resolved at spack runtime
- `--deprecated` flag needed for `py-torch@2.4.1`
- `reuse: true` in env can cause stale builds — use `concretize -f` after package.py changes
- Verify AVX512 kernels: `objdump -d libfoo.so | grep -c zmm`
- After rebasing overrides, record the `spack-packages` commit SHA in README / this file
