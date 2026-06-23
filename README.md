# s8ga-spack-packages

Custom [Spack](https://spack.io) package repository for **ABACUS** (Atomic-orbital Based Ab-initio Computation at UStc) and **force_avx512** math library overrides for HPC mixed-ISA cluster deployment.

## Repository Structure

```
spack_repo/
  s8_custom_repo/          # Original packages (not in spack builtin)
    packages/
      abacus/              # 9 versions, 36 variants, 4-layer test infrastructure
      libri/               # Header-only
      libcomm/             # Header-only
      libnpy/              # Header-only
      nep_cpu/             # NEP v1.4
  s8_overrides/            # Builtin package overrides (+force_avx512)
    packages/
      openblas/            # +force_avx512 variant
      elpa/                # +force_all_x86_kernel variant + 3 patches
      fftw/                # +force_avx512 variant
scripts/
  verify_overrides.sh      # Verify upstream build file compatibility
```

## Quick Start

### Register in a Spack environment

```bash
# Clone this repo
git clone https://github.com/s8ga/s8ga-spack-packages.git

# Register repos in your spack env (order matters: first = highest priority)
spack -e <env> repo add /path/to/s8ga-spack-packages/spack_repo/s8_overrides
spack -e <env> repo add /path/to/s8ga-spack-packages/spack_repo/s8_custom_repo

# Verify
spack -e <env> repo list
# Should show: s8_custom_repo > s8_overrides > builtin
```

### Install ABACUS

```bash
# LTS with force_avx512
spack install abacus@3.10.1-lts +deepks+pexsi+lcao+elpa+libri+libxc \
  +force_avx512 ^openblas+force_avx512 ^elpa+force_all_x86_kernel ^fftw+force_avx512

# Develop with force_avx512
spack install abacus@3.9.0.27 +mlalgo+nep+deepmd+pexsi+lcao+elpa+libri+libxc \
  +force_avx512 ^openblas+force_avx512 ^elpa+force_all_x86_kernel ^fftw+force_avx512
```

## force_avx512: What and Why

In HPC mixed-ISA clusters (some nodes AVX2, some AVX512), you need:
- Binaries compiled on AVX2 build nodes that **contain** AVX512 kernels
- Runtime CPUID dispatch to select the optimal kernel per node

Spack's `target=x86_64_v4` hardcodes AVX512 instructions (SIGILL on non-AVX512 nodes).
The `+force_avx512` variant compiles all SIMD kernels **including** AVX512, with
runtime CPUID dispatch for portability — the binary runs on any x86_64 node.

### Supported packages

| Package | Variant | How it works |
|---------|---------|-------------|
| OpenBLAS | `+force_avx512` | Suppresses `NO_AVX512=1`, builds all kernels via dynamic dispatch |
| FFTW | `+force_avx512` | Forces `--enable-avx512` configure flag regardless of target |
| ELPA | `+force_all_x86_kernel` | 3 source patches: relax configure AVX512 test + per-object CFLAGS |

### Verify AVX512 kernels are present

```bash
# Should show non-zero zmm (AVX512) instruction count
objdump -d $(spack location -i openblas)/lib/libopenblas.so | grep -c zmm
```

### Verify upstream compatibility before rebase

```bash
./scripts/verify_overrides.sh
# Uses spack stage (downloads ~11MB of source tarballs, NOT git clones)
# Checks: OpenBLAS NO_AVX512 variable, FFTW avx512 configure, ELPA patch --dry-run
```

## ABACUS Versions

| Version | Branch | Key variant |
|---------|--------|------------|
| `3.10.0-lts` | LTS | `+deepks` (ENABLE_DEEPKS) |
| `3.10.1-lts` | LTS | `+deepks` |
| `3.9.0.10` – `3.9.0.27` | Develop | `+mlalgo` (ENABLE_MLALGO) |
| `3.11.0-beta.4` | Develop | `+mlalgo` |

`+deepks` and `+mlalgo` are version-disjoint (upstream renamed the CMake option).

## Documentation

See [AGENTS.md](AGENTS.md) for:
- Detailed rebase workflow (when spack-packages updates)
- force_avx512 delta (exact code changes to re-apply)
- ABACUS dependency quirks and design decisions
- Testing infrastructure (4 layers)
- HPC Container Factory integration

## License

MIT. See [LICENSE](LICENSE).

The `s8_overrides` packages are derived from [spack-packages](https://github.com/spack/spack-packages)
(MIT OR Apache-2.0). Builtin copyright headers are preserved in those files.
