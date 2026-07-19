# s8ga-spack-packages

Custom [Spack](https://spack.io) package repositories for:

1. **ABACUS** (Atomic-orbital Based Ab-initio Computation at UStc) and related
   header/libs packages
2. **`force_avx512` math-library overrides** for HPC mixed-ISA cluster deployment

Repos use the spack **v2.5** layout (`spack_repo/<namespace>/`).

## Repository Structure

```
spack_repo/
  abacus/                  # namespace: abacus (api: v2.5)
    packages/
      abacus/              # Main package: 9 versions, CUDA, multi-variant
      libri/               # Header-only
      libcomm/             # Header-only
      libnpy/              # Header-only
      nep_cpu/             # NEP v1.4 (dir=underscore → package name nep-cpu)
  s8_overrides/            # namespace: s8_overrides (api: v2.5)
    packages/
      openblas/            # +force_avx512
      elpa/                # +force_all_x86_kernel + version-gated patches
      fftw/                # +force_avx512
  s8_custom_repo/          # Legacy empty placeholder (no packages)
scripts/
  verify_overrides.sh              # Upstream source/patch compatibility checks
  abacus_run_module_tests.sh       # Container helper: module unit tests (MODULE_* / LTS)
  abacus_run_integration_tests.sh  # Container helper: Autotest.sh groups
```

Current `s8_overrides` recipes are rebased on
[spack/spack-packages](https://github.com/spack/spack-packages)
**`develop@18aeef72`** (builtin api v2.2).

## Quick Start

### Register in a Spack environment

Use **env-scoped** repos (never global `spack repo add`):

```bash
git clone https://github.com/s8ga/s8ga-spack-packages.git

# Priority: first added = highest
spack -e <env> repo add /path/to/s8ga-spack-packages/spack_repo/s8_overrides
spack -e <env> repo add /path/to/s8ga-spack-packages/spack_repo/abacus

spack -e <env> repo list
# Expected: abacus > s8_overrides > builtin
```

Do **not** register the empty `s8_custom_repo` unless you intentionally add
packages there again.

### Install ABACUS

```bash
# LTS + force_avx512 math libs
spack install abacus@3.10.1-lts +deepks+pexsi+lcao+elpa+libri+libxc \
  ^openblas+force_avx512 ^elpa+force_all_x86_kernel ^fftw+force_avx512

# Develop (beta) + force_avx512 math libs
spack install abacus@3.11.0-beta.6 +mlalgo+nep+deepmd+pexsi+lcao+elpa+libri+libxc \
  ^openblas+force_avx512 ^elpa+force_all_x86_kernel ^fftw+force_avx512

# CUDA example (set a real SM arch for your GPUs)
spack install abacus@3.11.0-beta.6 +cuda+lcao+elpa cuda_arch=80 \
  ^openblas+force_avx512 ^elpa+force_all_x86_kernel+cuda ^fftw+force_avx512
```

`+deepks` (LTS / `ENABLE_DEEPKS`) and `+mlalgo` (develop / `ENABLE_MLALGO`) are
version-disjoint — never enable both.

## force_avx512: What and Why

In HPC mixed-ISA clusters (some nodes AVX2, some AVX512), you need:

- Binaries built on AVX2 hosts that **still contain** AVX512 kernels
- Runtime CPUID dispatch to pick the right kernel per node

Spack `target=x86_64_v4` hardcodes AVX512 (SIGILL on non-AVX512 nodes).
`+force_avx512` / `+force_all_x86_kernel` compile the AVX512 kernels **and** keep
runtime dispatch, so the same binary runs on any x86_64 node.

### Supported overrides

| Package  | Variant                 | Mechanism |
|----------|-------------------------|-----------|
| OpenBLAS | `+force_avx512`         | Suppress `NO_AVX512=1`; build all kernels with dynamic dispatch |
| FFTW     | `+force_avx512`         | Force `--enable-avx512` regardless of target |
| ELPA     | `+force_all_x86_kernel` | Version-gated patches: relax configure AVX512 probes + per-object CFLAGS |

Supported / verified force windows (see `scripts/verify_overrides.sh`):

| Package  | Supported | Verified versions |
|----------|-----------|-------------------|
| OpenBLAS | `@0.3.30:` (`@:0.3.29` conflicts) | `0.3.30`, `0.3.32`, `0.3.33` |
| ELPA     | `@2025:` (`@:2024.05.001` conflicts) | `2025.01.001/002`, `2025.06.001`, `2026.02.001/002` |
| FFTW     | `@3.3.10:` (`@:3.3.9` conflicts) | `3.3.10`, `3.3.11` |

### Check AVX512 kernels are present

```bash
objdump -d "$(spack location -i openblas)/lib/libopenblas.so" | grep -c zmm
# non-zero → AVX512 kernels are in the binary
```

### Rebase / compatibility check

```bash
./scripts/verify_overrides.sh
# Downloads ~11MB of upstream tarballs via `spack stage` (not git clones)
# Checks OpenBLAS NO_AVX512, FFTW avx512 configure, ELPA patch --dry-run
```

## ABACUS Versions

| Version          | Line    | Key ML variant |
|------------------|---------|----------------|
| `3.10.0-lts`     | LTS     | `+deepks` |
| `3.10.1-lts`     | LTS     | `+deepks` |
| `3.9.0.10`–`3.9.0.27` | Develop | `+mlalgo` |
| `3.11.0-beta.4`  | Develop | `+mlalgo` |
| `3.11.0-beta.6`  | Develop | `+mlalgo` |

GPU: `CudaPackage` mixin (`+cuda`, `cuda_arch=...`), plus optional
`+cuda-mpi` / `+nccl` / `+cusolvermp` / `+cublasmp`. LTS CUDA 13 needs
`lts-cuda13-fix.patch` (applied automatically for `@3.10 +cuda`).

Related packages in the same `abacus` namespace: `libri`, `libcomm`, `libnpy`,
`nep-cpu`.

## Container / local test helpers

Scripts resolve the tests tree via `$ABACUS_TESTS`, `$ABACUS_PREFIX`, PATH
`abacus`, or the legacy `/opt/spack/linux-x86_64_v3/…` layout. Needs
`abacus+tests` (one shared `PP_ORB/` + per-module symlinks).

```bash
# Module GoogleTest binaries (MODULE_* on develop; ELF under module_*/test* on LTS)
ABACUS_PREFIX=$(spack -e <env> location -i abacus) \
  bash scripts/abacus_run_module_tests.sh

# Integration Autotest.sh groups 01–10 (passes -a <abacus>)
ABACUS_PREFIX=$(spack -e <env> location -i abacus) \
  bash scripts/abacus_run_integration_tests.sh
```

## Documentation

See [AGENTS.md](AGENTS.md) for agent/maintainer details:

- Rebase workflow when `spack-packages` advances
- Exact `force_avx512` deltas to re-apply after copying builtin recipes
- ABACUS dependency quirks, patches, and 4-layer test stack
- HPC Container Factory integration notes

## License

MIT. See [LICENSE](LICENSE).

The `s8_overrides` packages are derived from
[spack-packages](https://github.com/spack/spack-packages) (MIT OR Apache-2.0).
Builtin copyright headers are preserved in those files.
