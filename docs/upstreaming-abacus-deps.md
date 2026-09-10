# Upstreaming the four ABACUS dependency packages

Date: 2026-09-09 · Status: **3 PRs OPEN (user-authorized this once), libri
held back** — #6404 libnpy, #6405 libcomm, #6406 nep-cpu. libri (branch
`add-libri`, stacks on libcomm) is submitted after libcomm merges: rebase
`--onto develop`, re-sign, push, open. Default rule stands: agents never
open PRs without explicit per-instance authorization.

## What and why

A complete ABACUS build (`+libri`, `+deepks`/`+mlalgo`, `+nep`) needs four
packages that builtin spack-packages does not carry. They were prepared and
validated for upstreaming, modeled on recently merged tiny/header-only
precedents (rapidxml #5597, tdls #6254, copacabana #6347 — all merged
2026-07/09; upstream abacus already depends on header-only `cereal`).

## Artifacts

| Piece | Location |
|---|---|
| spack-packages clone (builtin repointed here) | `~/spack-packages` (develop @ `e9b2c22d`) |
| Worktrees (one per package) | `~/spack-worktrees/add-{libnpy,libcomm,nep-cpu,libri}` |
| Branches (pushed to fork `s8ga/spack-packages`) | `add-libnpy` `add-libcomm` `add-nep-cpu` `add-libri` |
| PR bodies (real-upstream style: 3–4 sentences, no checklist) | `~/spack-worktrees/pr-bodies/*.md` |

Branch stack: `add-libri` sits on top of `add-libcomm` (LibRI headers
`#include <Comm/...>`, so `libri` depends on `libcomm`).

## Opening the PRs (manual, by s8ga)

1. Anytime, in any order: `add-libnpy`, `add-libcomm`, `add-nep-cpu`
   (titles: `<pkg>: new package`; bodies in pr-bodies/).
2. `add-libri` last — its PR body states it stacks on the libcomm PR;
   merge libcomm first.
3. After merge: `spack repo set --destination ~/.spack/package_repos/fncqgg4 builtin`
   (or keep the clone and `git pull`) and re-run the checklist below.

## Validation performed (2026-09-09, spack 1.2.0, gcc 14.2.0, linux-debian13)

- `spack spec` + real `spack install` of EVERY packaged version: libnpy
  1.0.1+1.0, libcomm 0.1.1+0.1.0, libri 0.2.1.1+0.2.1.0+0.2.0.0 (concretizes
  `^libcomm@0.1.1`), nep-cpu 1.4 (compiles 3 TUs → `lib/libnep.a`, 570
  symbols, `NEP` class present).
- libri versions 0.1.0/0.1.1/0.2.0 were tried and FAIL (no
  `include/RI/version.h` before 0.2.0.0) → trimmed to the three working
  versions. Our local namespace copies of libri still carry the broken old
  versions — same failure applies there if anyone requests them.
- License verified against the actual LICENSE files at the packaged tags
  (via git clones in /tmp): libnpy = MIT; libri/libcomm = **GPL-3.0-only**
  — upstream relicensed GPLv3 → LGPLv3 on master on 2026-03-28 (commits
  LibRI `1f4200c`, LibComm `965bf90`), but NO tag contains the change, so
  every released tarball ships the plain GPL-3.0 LICENSE with no or-later
  grant. GitHub's repo page shows LGPL-3.0 because it reads master — expect
  reviewer questions; when a post-relicensing release is tagged, bump the
  license() accordingly. nep-cpu = GPL-3.0-or-later, granted explicitly in
  source headers. NOTE: our local s8 recipes say `LGPL-3.0-or-later` for
  libri/libcomm — wrong for the tagged releases; fixed in the upstream
  versions, local copies will be deleted on migration anyway.
- All `sanity_check_is_file` targets verified on disk (`npy.hpp`,
  `Comm/Comm_Tools.h`, `RI/version.h`, `libnep.a` + `nep.h`).
- `spack style`: PROVEN clean — spack 1.2.0's style.py hardcodes
  `--config <spack prefix>/pyproject.toml`, whose per-file-ignores only cover
  the legacy `var/spack/*/package.py` layout, so F403/F405 fire on package
  files in an external package repo (rapidxml/libsvm fail identically).
  Re-running the same bootstrapped ruff (0.15.0) with the spack-packages
  repo's own pyproject.toml (which ignores F403 and declares the package-API
  builtins) reports "All checks passed!" for all four recipes.
- Note: used namespace-qualified specs (`builtin.libnpy` etc.) because a
  transient libnpy boilerplate in globally-registered `s8_custom_repo`
  shadowed builtin by name — an accidental artifact of the failed early
  `spack create` attempts (no `-r` flag → writes to the highest-priority
  repo). Artifact deleted afterwards; see side effects below.

## After upstream merge — migration in THIS repo

1. Delete `spack_repo/abacus/packages/{libri,libcomm,libnpy,nep_cpu}`;
   `depends_on("libri")` etc. in the abacus recipe then resolve to builtin.
2. Re-concretize envs (`concretize -f`; hashes change — expected rebuild).
3. Known local divergence to drop then: our libri recipe lacks
   `depends_on("libcomm")` (upstream version has it).

## Environment side effects / cleanups noticed (2026-09-09)

- `s8_custom_repo` is **not the "empty placeholder"** AGENTS.md describes:
  it contains `libmbd` and `vasp` (committed; vasp is active work), and it
  is registered **globally**, contrary to the "never global repo add" rule.
  During this session the failed early `spack create` calls (no `-r`) also
  dropped an accidental libnpy boilerplate there, which shadowed builtin
  until deleted. Recommend either `spack repo remove s8_custom_repo`
  (global) or always passing `-r`/namespace to `spack create`.
- Two failed-install records left in the store (`/4ak3zod`, `/yi3sqyp`,
  from the shadowed libnpy attempts). `spack uninstall --force` is blocked
  by a namespace quirk: the abacus-lts env references the env-scoped
  `abacus` repo, which global commands cannot resolve. Cosmetic only.
- builtin repo destination now points at `~/spack-packages` (develop tip);
  other envs re-concretizing will pick up today's develop. Rollback:
  `spack repo set --destination ~/.spack/package_repos/fncqgg4 builtin`.

## Container build validation (2026-09-10, abacus big-PR prep)

Environment: podman container `abacus-build`
(`nvcr.io/nvidia/nvhpc:26.5-devel-cuda_multi-ubuntu24.04`, `--network=host`,
proxy `100.77.110.122:40022`, USTC apt mirror). gcc 13.3 host compiler;
CUDA **12.9** and **13.2** toolkits under
`/opt/nvidia/hpc_sdk/Linux_x86_64/2026/cuda/{12.9,13.2}`; nvhpc 26.5
math_libs shared, with per-version subdirs
`26.5/math_libs/{12.9,13.2}/{include,lib64}`.

### Raw cmake matrix (round 3, `/work/build3-*`, `BUILD3-RESULTS.txt`)

All rows: `-DUSE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=80 -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DENABLE_LCAO=OFF`, make -j18.

| Row | Source | CUDA | Result |
|-----|--------|------|--------|
| A | 3.10.1 + s8 patches | 13.2 | **OK** (`abacus_pw`, links cublas/cufft/cudart 13) |
| B | 3.10.1 vanilla | 13.2 | **FAIL 6s**: `#error Thrust requires at least C++17` (CCCL 3 rejects the LTS default C++14) |
| C | 3.10.1 + s8 patches | 12.9 | **OK** (`abacus_pw`) |
| D | 3.9.0.27 | 13.2 | **OK** (`abacus_1g`) |
| E | 3.9.0.27 | 12.9 | **OK** (`abacus_1g`) |

Row B is the negative control proving `lts-cuda13-fix.patch` necessity: the
patch's `set_if_higher(CMAKE_CXX_STANDARD 17)` for `CUDAToolkit >= 13` (plus
arch≥75 list and CUDA-13-removed `cudaDeviceProp` fields / CUFFT enum guards)
is exactly what vanilla LTS lacks. 3.9.0.27 needs no patch on either toolkit.

### nvhpc 26.5 container landmines (for future reruns)

1. The 13.2 toolkit ships CCCL **only** under `include/cccl/` (no top-level
   `thrust/`, `cub/`); 12.9 still has top-level dirs. Host-side
   `#include <thrust/...>` under 13.2 needs `-I<cuda>/include/cccl`.
   Open question for the big PR: whether NVIDIA *runfile* CUDA 13 toolkits
   share this layout (nvhpc's usually mirror upstream) — if yes, upstream
   abacus@3.10+cuda+CUDA13 needs the include path added by the build system.
2. The image's `CPATH` contains the **unversioned** `26.5/math_libs/include`
   (= CUDA 13 headers); compiling against CUDA 12.9 then fails on
   `cudaEmulation*` APIs missing from the 12.9 runtime headers. Use the
   versioned `26.5/math_libs/<ver>/include` instead. Same for `lib64` —
   image `LIBRARY_PATH` only has gdrcopy, so `-lcublas/-lcufft` resolution
   needs `26.5/math_libs/<ver>/lib64` on `LIBRARY_PATH`.
3. `VAR=... cmake <configure>` does not propagate to `cmake --build` children
   — `export` the env fixes, or the build phase silently reverts to the
   image defaults (this cost one full round to diagnose).
4. spack `env.unset("CPATH")` in clean build contexts means spack builds are
   immune to landmine 2, but also can't be fixed via CPATH for landmine 1.
5. nvhpc splits math libs out of the per-version CUDA toolkits, so the
   toolkit prefix has no cublas/cufft. spack externals consuming cublas
   (elpa+cuda configure: "Could not link cublas") need a **merged prefix**:
   `/opt/cuda-ext/12.9` with `cp -rs` symlink trees of
   `2026/cuda/12.9/{bin,include,lib64}` + `26.5/math_libs/12.9/{include,lib64}`
   + symlinks for every other top-level toolkit dir (nvvm, compat, extras…).
   The extra dirs matter because **nvcc resolves its components relative to
   argv[0]**, not /proc/self/exe — a bin/nvcc symlink alone dies with
   `bin/../nvvm/bin/cicc: not found` (exit 127).

### spack pipeline (env `/work/env-abacus`) — SUCCESS 2026-09-10

`spack.yaml`: spec `abacus@3.10.1 +cuda cuda_arch=80 ^cuda@12.9`,
`unify: false` (loose, per s8ga decision: let spack resolve/build all deps),
externals only `{gcc@13.3, nvhpc@26.5, cuda@12.9, cuda@13.2}`. Full stack
built from source by spack (openmpi 5.0.10, openblas 0.3.34,
elpa 2026.02.002 +cuda, fftw 3.3.11, libxc 7.1.2, netlib-scalapack,
cereal…; 48-package DAG). Result: `spack install` rc=0, installed
`abacus@3.10.1+cuda cuda_arch=80`; `bin/abacus --version` →
`ABACUS version v3.10.1`; ldd resolves libcudart/libcublas/libcufft .so.12
from the merged external prefix; `cuobjdump --list-elf` shows **40× sm_80
fatbins, no other arch** (cuda_arch propagation through the recipe is exact).
elpa keeps its own default arch (sm_60) — the recipe deliberately leaves
`elpa cuda_arch=none`; production envs pin it explicitly.

Two container-only fixes were needed (both environmental, not recipe):
(a) the merged CUDA external prefix (landmine 5) — including a
**targets/x86_64-linux overlay**: CMake FindCUDAToolkit prefers
`targets/.../include`, which in a plain merge still lacks cublas headers, so
`cp -rs` the math_libs headers+libs into `$MP/targets/x86_64-linux/{include,lib}`
too; (b) first-run checksum failures (libxml2/perl/util-linux-uuid) through
the proxy were **transient** — loose-mode retry rebuilt them from source
fine. (Hand-added `/usr` externals for libxml2/perl were tried first and
**reverted**: the `/usr/include/libxml2` subdir layout is invisible to spack
consumers and broke hwloc/gettext configure.)



- **abacus "full recipe" PR — IN PREPARATION (2026-09-10)**, decisions
  locked with s8ga: add ALL supported formal versions (3.9.0.10–.27,
  3.10.0; no betas) + all feature variants (mpi, float-fftw, pexsi,
  libri→libnpy/libcomm, rapidjson, deepmd, deepks@3.10/mlalgo, nep, cuda
  stack incl. nccl/cusolvermp/cublasmp/cuda-mpi) + 3 patches
  (lts-pexsi-compile @3.10+pexsi, lts-cuda13-fix @3.10+cuda — kept gated
  per user decision, v3.9.0.10-cstdint). EXCLUDED: +tests (user), kml/dftd4
  (beta-gated), beta versions. Local s8 abacus repo stays FOREVER (beta.6
  in production). Open when the four dep PRs (#6404/#6405/#6406 + libri)
  are merged; then a clean branch = develop + abacus files only.
- Status: integration branch `tmp-integration` (develop + 4 dep packages +
  enriched abacus recipe) validated 2026-09-10: ruff clean, concretize
  matrix 14/14 green. TWO LATENT BUGS found & fixed in the CUDA wiring —
  **both exist verbatim in our local s8 abacus recipe too** (masked in
  production because envs are CPU-only + unify + pinned preferences):
  1. `depends_on("mpi+cuda", when="+cuda-mpi")` is unsatisfiable by
     construction — the virtual would require EVERY MPI provider to have a
     +cuda variant (mpich/mvapich2 don't). Fixed with abinit's
     `requires("^openmpi+cuda", "^mpich+cuda", policy="one_of")` pattern.
     Only package in all of builtin that ever wrote `mpi+cuda` was ours.
  2. cuda_arch does NOT propagate across dependency edges (sticky variant;
     "propagates via unify" was a wrong assumption). `+nccl` with root
     cuda_arch left nccl at cuda_arch=none → its own conflicts fired.
     Fixed with enumerated per-arch edges (the cusolvermp/cublasmp
     internal pattern): for arch in CudaPackage.cuda_arch_values:
     depends_on(f"nccl cuda_arch={arch}", when="+nccl cuda_arch={arch}") etc.
  RECOMMENDED LOCAL BACKPORT: DONE 2026-09-10 — both fixes applied to
  spack_repo/abacus/packages/abacus/package.py and verified in a throwaway
  env (nccl/cusolvermp/cublasmp rows + cuda-mpi^openmpi+cuda all green).
- cuda_arch=80 (A100) support audit (2026-09-10, /tmp/fork-audit): 80 is in
  CudaPackage.cuda_arch_values; CUDA 11–13 all cover sm_80 (13 dropped only
  <sm_75). elpa builds with --with-nvidia-compute-capability=sm_80. nccl
  needs explicit cuda_arch (conflicts on none) — now propagated; nccl
  version↔cuda matrix: 2.27+→cuda@12:13, 2.22–2.26→cuda@12, 2.16–2.21→
  cuda@11:12. cusolvermp: cuda@12:, nccl@2.18.5:. cublasmp: cuda@12:,
  nvshmem@3.1: (cuda@11: for 3.2.5+) — both propagate arch internally. gcc14
  host requires cuda@12.6+ (nvcc 12.4 caps at gcc 13) — unrelated to us.
  py-torch guard: web-verified (Gemini/Google, pytorch.org release notes) —
  official CUDA 13 support starts at torch 2.9; torch 2.4 tops out at CUDA
  12.4 and cannot build vs CUDA 13, even though spack's py_torch ladder
  (cuda@11: for @2.4:) permits it on paper → added
  conflicts("^cuda@13:", when="+deepks/+mlalgo +cuda") to BOTH the
  integration recipe and the local s8 recipe; verified firing (^cuda@13.0
  rejected, ^cuda@12.8 accepted with gcc 14).
- Patch dry-runs vs real staged tarballs (2026-09-10): lts-pexsi-compile
  (2 files) + lts-cuda13-fix (4 files) apply clean on BOTH v3.10.1 and
  LTSv3.10.0; v3.9.0.10-cstdint (1 file) clean on v3.9.0.10. 5/5 exit=0.
- Repo-name discovery (2026-09-10): `abacusmodeling/abacus-develop` is a
  STALE MIRROR (tags stop at v3.9.0.19/v3.10.1); `deepmodeling/
  abacus-develop` is canonical (has v3.9.0.20–.27, all v3.11.0-beta*).
  The enriched recipe therefore pins version-level url= overrides to
  deepmodeling tarballs for the new versions; existing upstream versions
  (3.10.1, 3.9.0.19) left on abacusmodeling — ask bitllion which org is
  canonical in the PR.
- Optional: upstream a CMakeLists to brucefan1983/NEP_CPU to replace the
  manual compile+archive in nep-cpu.
