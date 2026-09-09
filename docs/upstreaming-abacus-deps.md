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

## Future work (deliberately out of scope now)

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
