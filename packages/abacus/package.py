# Copyright Spack Project Developers. See COPYRIGHT file for details.
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import glob

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack.package import *


class Abacus(CMakePackage):
    """ABACUS (Atomic-orbital Based Ab-initial Computation at UStc) is an
    open-source package for first-principles electronic structure calculations.

    This package supports two parallel release lines, verified via git branch
    topology (fork point c53f4456, 2025-01-02):

      * LTS line (origin/LTS): 3.10.x -- old build system
        (ENABLE_DEEPKS, module_* sources, Intel MKL only, no BuildInfo)
      * develop   (origin/develop): 3.9.0.x + 3.11.x -- new build system
        (ENABLE_MLALGO, source_* sources, GNU+MKL supported, BuildInfo)

    LTS 3.10.x is captured by ``@3.10``; develop by ``@3.9.0.10:`` (cutoff at
    v3.9.0.10 -- earlier 3.9.0.8/.9 are transitional and unsupported).
    """

    homepage = "https://abacus.deepmodeling.com/"
    url = (
        "https://github.com/deepmodeling/abacus-develop/"
        "archive/refs/tags/v3.10.1.tar.gz"
    )
    git = "https://github.com/deepmodeling/abacus-develop.git"
    list_url = "https://github.com/deepmodeling/abacus-develop/releases"

    license("LGPL-3.0-or-later")

    # ------------------------------------------------------------------ #
    #  Versions                                                          #
    # ------------------------------------------------------------------ #
    # newest first. git tag + full commit SHA gives trusted provenance
    # (Spack strongly recommends pairing tags with commits) and keeps .git
    # in the stage so COMMIT_INFO=ON can `git describe` for `abacus --version`,
    # which matters for bug tracking. LTS tags carry a "-lts" suffix to
    # distinguish them from any future regular 3.10.x on the develop line.
    # develop line (new build system), newest first
    version("3.11.0-beta.4", tag="v3.11.0-beta4",
            commit="7cb8da759b96b6508515515cffd7dcfea9596fb6")
    version("3.9.0.27", tag="v3.9.0.27",
            commit="3a996b6eb50af8c2c07bc3ff39c67e6164d56faf")
    version("3.9.0.25", tag="v3.9.0.25",
            commit="2087308d9d09d57d0c6a9fe7c6dbbeb075a5dc40")
    version("3.9.0.20", tag="v3.9.0.20",
            commit="f1c5f1b47bb0209182a0da65ca6101a017844880")
    version("3.9.0.15", tag="v3.9.0.15",
            commit="b062b0758d3636799dc83fe6ddf480c412542c63")
    version("3.9.0.10", tag="v3.9.0.10",
            commit="a94c62d265d825f39a8d6b3b52c35e8ec68d887d")
    # LTS line (old build system)
    version("3.10.1-lts", tag="v3.10.1",
            commit="f71921fe848659deac8db319cd4311b55b5ad480")
    version("3.10.0-lts", tag="LTSv3.10.0",
            commit="1be7425f0e73dacbe9c9e7be3fbfc9df30d100fa")

    # ------------------------------------------------------------------ #
    #  Variants                                                          #
    # ------------------------------------------------------------------ #

    # Core build options (all versions)
    variant("mpi", default=True, description="Enable MPI parallelization")
    variant("openmp", default=True, description="Enable OpenMP support")
    variant(
        "lcao",
        default=True,
        description="Enable LCAO (linear combination of atomic orbitals) basis",
    )
    variant(
        "float-fftw",
        default=False,
        description="Enable single-precision FFTW backend",
    )
    variant(
        "native-optimization",
        default=False,
        description="Enable host-native CPU optimizations (-march=native)",
    )
    variant(
        "debug",
        default=False,
        description="Enable developer debug messages (DEBUG_INFO)",
    )
    variant(
        "mathlib",
        default=False,
        description="Build ABACUS libmath from source (USE_ABACUS_LIBM, "
        "only useful for old compilers lacking optimized libm)",
    )

    # Variants gated on LCAO and/or MPI (forced OFF by CMake otherwise)
    variant(
        "elpa",
        default=True,
        when="+lcao+mpi",
        description="Use ELPA for eigenvalue problems (requires LCAO+MPI)",
    )
    variant(
        "pexsi",
        default=False,
        when="+lcao+mpi",
        description="Enable PEXSI for large-scale electronic structure "
        "(requires LCAO+MPI)",
    )

    # Optional scientific libraries (all versions)
    variant("libri", default=False, description="Enable EXX with LibRI")
    variant("libxc", default=False, description="Enable LibXC functionality")
    variant("rapidjson", default=False, description="Enable RapidJSON usage")
    variant("deepmd", default=False, description="Enable DeePMD-kit (Deep Potential MD)")

    # ML: follow upstream option names exactly.
    #   LTS (3.10.x) + <=3.9.0.7 use ENABLE_DEEPKS
    #   develop @3.9.0.8: uses ENABLE_MLALGO (unified DeePKS + ML-KEDF)
    # Two variants with disjoint version ranges (the OR of two `when` clauses
    # on `mlalgo` covers develop 3.9.0.x + 3.11.x while excluding LTS 3.10.x,
    # which sits in between on the version axis). Requesting the absent
    # variant on a given version auto-errors (spack: "variant not found").
    variant(
        "deepks",
        default=False,
        when="@3.10",
        description="DeePKS (maps to ENABLE_DEEPKS, LTS line)",
    )
    variant(
        "mlalgo",
        default=False,
        when="@3.9.0.10:3.9.0.27",
        description="ML algorithms: DeePKS + ML-KEDF (maps to ENABLE_MLALGO, develop)",
    )
    variant(
        "mlalgo",
        default=False,
        when="@3.11.0-beta.1:",
        description="ML algorithms: DeePKS + ML-KEDF (maps to ENABLE_MLALGO, develop)",
    )

    # New features on the develop line (version-gated to their introduction)
    variant(
        "nep",
        default=False,
        when="@3.9.0.27:",
        description="Enable NEP neuroevolution potential (FindNEP.cmake)",
    )
    variant(
        "kml",
        default=False,
        when="@3.11.0-beta.3:",
        description="Enable Kunpeng Math Library (upstream stub, no backend lib)",
    )
    variant(
        "dftd4",
        default=False,
        when="@3.11.0-beta.4:",
        description="Enable DFT-D4 dispersion correction",
    )

    # ------------------------------------------------------------------ #
    #  Dependencies                                                      #
    # ------------------------------------------------------------------ #

    # Language and build tools. ABACUS declares `project(... LANGUAGES CXX)`
    # only; the source tree has one .c file (mcd.c), so keep `c` for safety.
    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("cmake@3.16:", type="build")

    # MPI
    depends_on("mpi", when="+mpi")

    # Core math libraries (virtual providers, solver picks one)
    depends_on("fftw-api@3")
    depends_on("blas")
    depends_on("lapack")
    depends_on("scalapack", when="+lcao+mpi")

    # LCAO dependencies
    depends_on("cereal", when="+lcao")
    depends_on("elpa", when="+lcao+elpa")

    # Optional libraries
    depends_on("libxc", when="+libxc")
    depends_on("libri", when="+libri")
    depends_on("libcomm", when="+libri")
    depends_on("pexsi", when="+pexsi")
    depends_on("rapidjson", when="+rapidjson")
    depends_on("deepmdkit", when="+deepmd")

    # ML: libtorch via py-torch + libnpy header (libnpy_INCLUDE_DIR avoids
    # ABACUS FetchContent download at build time).
    #
    # Upper bound 2.4: ABACUS uses the torch::linalg C++ namespace, which was
    # removed in pytorch 2.5 (2024-10; functions moved to torch::linalg_*
    # prefix). develop HEAD is mid-migration but still uses the old namespace,
    # so every ABACUS version (LTS + develop) requires py-torch <= 2.4.
    depends_on("py-torch@2.1:2.4 ~cuda", when="+deepks")
    depends_on("py-torch@2.1:2.4 ~cuda", when="+mlalgo")
    depends_on("libnpy", when="+deepks")
    depends_on("libnpy", when="+mlalgo")

    # NEP (self-built nep-cpu package; FindNEP expects <prefix>/{include,lib})
    depends_on("nep-cpu", when="+nep")

    # DFT-D4. ABACUS is CXX-only but ENABLE_DFTD4=ON calls
    # enable_language(Fortran) in CMakeLists.txt (beta.4+), so we
    # need the Fortran compiler even though we only link dftd4.
    # Force build_system=cmake: dftd4's meson build does not produce
    # dftd4Config.cmake, which ABACUS's find_package(dftd4) requires
    # (see PR #7380).
    depends_on("fortran", type="build", when="+dftd4")
    depends_on("dftd4@4.2.0: build_system=cmake", when="+dftd4")

    # OpenMP forward propagation: pick threaded BLAS/FFTW/MKL providers
    with when("+openmp"):
        depends_on("fftw+openmp", when="^[virtuals=fftw-api] fftw")
        depends_on(
            "openblas threads=openmp", when="^[virtuals=blas,lapack] openblas"
        )
        depends_on(
            "intel-oneapi-mkl threads=openmp",
            when="^[virtuals=blas,lapack,scalapack,fftw-api] intel-oneapi-mkl",
        )

    # Single-precision FFTW: ENABLE_FLOAT_FFTW links FFTW3::FFTW3_FLOAT.
    depends_on("fftw precision=float", when="+float-fftw ^[virtuals=fftw-api] fftw")

    # OpenMP reverse propagation: ensure elpa is built ~openmp when ABACUS is
    with when("~openmp"):
        depends_on("elpa~openmp", when="+elpa")

    # GNU+MKL: develop @3.9.0.25: supports the gf interface (cp2k pattern).
    # Force +gfortran so MKL ships mkl_gf_lp64 / mkl_gnu_thread for %gcc.
    depends_on(
        "intel-oneapi-mkl+gfortran threads=openmp",
        when="@3.9.0.25: +openmp ^[virtuals=blas] intel-oneapi-mkl %gcc",
    )

    # ------------------------------------------------------------------ #
    #  Conflicts                                                         #
    # ------------------------------------------------------------------ #

    # GNU+MKL is unsupported on LTS and on develop <3.9.0.25: FindMKL only
    # locates Intel Fortran interfaces there, so %gcc linking fails.
    conflicts(
        "%gcc ^intel-oneapi-mkl",
        when="@3.10",
        msg="LTS MKL only provides Intel Fortran interfaces. "
        "Use %intel-oneapi-compilers with intel-oneapi-mkl, or pick a "
        "non-MKL BLAS/FFTW provider (e.g. openblas + fftw).",
    )
    conflicts(
        "%gcc ^intel-oneapi-mkl",
        when="@:3.9.0.24",
        msg="develop <3.9.0.25: GNU+MKL not supported (same as LTS).",
    )

    # LTS PEXSI compile fix: upstream bug (missing #include + Gint_inout
    # signature mismatch) fixed in PR #6689 on develop, but not cherry-picked
    # to the LTS branch. See issue #6684.
    patch("lts-pexsi-compile.patch", when="@3.10 +pexsi")

    # v3.9.0.10 compile fix: uint64_t used without #include <cstdint>
    # (fixed in later develop versions)
    patch("v3.9.0.10-cstdint.patch", when="@3.9.0.10")

    # ------------------------------------------------------------------ #
    #  CMake arguments                                                   #
    # ------------------------------------------------------------------ #

    def cmake_args(self):
        spec = self.spec
        args = [
            # --- shared variant -> option mapping (all versions) ---
            self.define_from_variant("ENABLE_MPI", "mpi"),
            self.define_from_variant("USE_OPENMP", "openmp"),
            self.define_from_variant("ENABLE_LCAO", "lcao"),
            self.define_from_variant("USE_ELPA", "elpa"),
            self.define_from_variant("ENABLE_LIBRI", "libri"),
            self.define_from_variant("ENABLE_LIBXC", "libxc"),
            self.define_from_variant("ENABLE_PEXSI", "pexsi"),
            self.define_from_variant("ENABLE_RAPIDJSON", "rapidjson"),
            self.define_from_variant("ENABLE_FLOAT_FFTW", "float-fftw"),
            self.define_from_variant(
                "ENABLE_NATIVE_OPTIMIZATION", "native-optimization"
            ),
            self.define_from_variant("DEBUG_INFO", "debug"),
            self.define_from_variant("USE_ABACUS_LIBM", "mathlib"),
            # --- shared force-disabled (CPU-only x86_64) ---
            self.define("USE_CUDA", False),
            self.define("USE_ROCM", False),
            self.define("USE_DSP", False),
            self.define("USE_CUDA_ON_DCU", False),
            self.define("ENABLE_CUSOLVERMP", False),
            self.define("GIT_SUBMODULE", False),
            # COMMIT_INFO=ON: git versions keep .git in the stage, so
            # `git describe` works and `abacus --version` shows the commit.
            self.define("COMMIT_INFO", True),
        ]

        # FFT backend: MKL (MKLROOT) vs FFTW3 (FFTW3_DIR).
        # FindMKL reads the *CMake variable* ${MKLROOT} (not the env var), so
        # it must be passed explicitly. intel-oneapi-mkl ships MKL under
        # <prefix>/mkl/<version>/{include,lib}; `latest` symlinks the active
        # version and is stable across MKL releases.
        if "^intel-oneapi-mkl" in spec:
            mkl = spec["intel-oneapi-mkl"]
            args.append(
                self.define("MKLROOT", join_path(mkl.prefix, "mkl", "latest"))
            )
        else:
            args.append(self.define("FFTW3_DIR", spec["fftw-api"].prefix))

        # Cereal: FindCereal expects CEREAL_INCLUDE_DIR = the include dir
        # itself (it searches for cereal/cereal.hpp under it).
        if "+lcao" in spec:
            args.append(
                self.define("CEREAL_INCLUDE_DIR", spec["cereal"].prefix.include)
            )

        # ELPA: FindELPA uses ELPA_DIR (prefix); it has a built-in #3589
        # guard that rejects /usr/include/elpa system hits when ELPA_DIR is set.
        if "+lcao+elpa" in spec:
            args.append(self.define("ELPA_DIR", spec["elpa"].prefix))

        # LibRI / LibComm: ENABLE_LIBRI auto-enables ENABLE_LIBCOMM in CMake,
        # but we pass it explicitly and both _DIR prefixes for clarity.
        if "+libri" in spec:
            args.append(self.define("ENABLE_LIBCOMM", True))
            args.append(self.define("LIBRI_DIR", spec["libri"].prefix))
            args.append(self.define("LIBCOMM_DIR", spec["libcomm"].prefix))

        # LibXC: FindLibxc uses Libxc_DIR (prefix) or pkg-config.
        if "+libxc" in spec:
            args.append(self.define("Libxc_DIR", spec["libxc"].prefix))

        # PEXSI: FindPEXSI requires PEXSI_DIR + ParMETIS_DIR + SuperLU_DIST_DIR
        # (ParMETIS and SuperLU_DIST libraries are REQUIRED). spack's pexsi
        # package already depends on parmetis + superlu-dist.
        if "+pexsi" in spec:
            args.append(self.define("PEXSI_DIR", spec["pexsi"].prefix))
            args.append(self.define("ParMETIS_DIR", spec["parmetis"].prefix))
            args.append(
                self.define("SuperLU_DIST_DIR", spec["superlu-dist"].prefix)
            )

        # DeePMD: variable-driven (DEFINED DeePMD_DIR enables it; no option).
        if "+deepmd" in spec:
            args.append(self.define("DeePMD_DIR", spec["deepmdkit"].prefix))

        # --- version-branched options (core architecture) ---
        if spec.satisfies("@3.10"):
            # LTS old build system
            args.append(self.define_from_variant("ENABLE_DEEPKS", "deepks"))
            # LTS still has ENABLE_PAW; force OFF (PAW removed @3.9.0.10).
            args.append(self.define("ENABLE_PAW", False))
            if "+deepks" in spec:
                self._add_torch_args(args, spec)
                args.append(
                    self.define(
                        "libnpy_INCLUDE_DIR", spec["libnpy"].prefix.include
                    )
                )

        elif spec.satisfies("@3.9.0.10:"):
            # develop new build system
            args.append(self.define_from_variant("ENABLE_MLALGO", "mlalgo"))
            # USE_SW exists @3.9.0.10: but x86 doesn't need Sunway.
            args.append(self.define("USE_SW", False))
            # ENABLE_PAW was removed @3.9.0.10: do not pass it.

            if "+mlalgo" in spec:
                self._add_torch_args(args, spec)
                args.append(
                    self.define(
                        "libnpy_INCLUDE_DIR", spec["libnpy"].prefix.include
                    )
                )

            # develop sub-branches (continuous version ranges within @3.9.0.10:)
            if spec.satisfies("@3.9.0.27:") and "+nep" in spec:
                args.append(self.define("NEP_DIR", spec["nep-cpu"].prefix))
            if spec.satisfies("@3.11.0-beta.3:"):
                args.append(self.define_from_variant("USE_KML", "kml"))
            if spec.satisfies("@3.11.0-beta.4:"):
                args.append(self.define_from_variant("ENABLE_DFTD4", "dftd4"))

        return args

    def _add_torch_args(self, args, spec):
        """Locate TorchConfig.cmake under py-torch.

        py-torch buries TorchConfig.cmake in its python site-packages tree
        (confirmed empirically with py-torch@2.12.0 and corroborated by cp2k's
        cmake_cp2k.sh: "PyTorch's TorchConfig.cmake is buried in the Python
        site-packages directory"). The python version in the path is dynamic,
        so the directory is glob-discovered rather than hard-coded.
        """
        torch = spec["py-torch"]
        pattern = join_path(
            str(torch.prefix),
            "lib",
            "python*",
            "site-packages",
            "torch",
            "share",
            "cmake",
            "Torch",
        )
        matches = glob.glob(pattern)
        if not matches:
            raise InstallError(
                "TorchConfig.cmake not found under py-torch prefix. "
                "Expected pattern: {0}".format(pattern)
            )
        args.append(self.define("Torch_DIR", matches[0]))
