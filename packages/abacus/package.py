# Copyright Spack Project Developers. See COPYRIGHT file for details.
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack.package import *


class Abacus(CMakePackage):
    """ABACUS (Atomic-orbital Based Ab-initial Computation at UStc) is an
    open-source package for first-principles electronic structure calculations.

    This package targets the LTS (Long-Term Support) releases, providing
    stable CPU-only builds for x86_64 Linux.
    """

    homepage = "https://abacus.deepmodeling.com/"
    url = (
        "https://github.com/deepmodeling/abacus-develop/"
        "archive/refs/tags/v3.10.1.tar.gz"
    )
    list_url = "https://github.com/deepmodeling/abacus-develop/releases"

    license("LGPL-3.0-or-later")

    # newest first. LTS releases carry a "-lts" suffix in the Spack version
    # string to distinguish them from regular releases; the suffix is not part
    # of the GitHub tag, so each version needs an explicit url.
    version(
        "3.10.1-lts",
        sha256="06873eba8a4e0bc085177a6580455b28e4b62ea8a18f8afe71a02105756d91a0",
        url="https://github.com/deepmodeling/abacus-develop/"
        "archive/refs/tags/v3.10.1.tar.gz",
    )
    version(
        "3.10.0-lts",
        sha256="332ed08bb18489f50dcaacdcca8f6ee7ff68e485d49585a2eb9797547898021b",
        url="https://github.com/deepmodeling/abacus-develop/"
        "archive/refs/tags/LTSv3.10.0.tar.gz",
    )

    # ------------------------------------------------------------------ #
    #  Variants                                                           #
    # ------------------------------------------------------------------ #

    # Core build options
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
    variant(
        "deepks",
        default=False,
        when="+mpi",
        description="Enable DeePKS functionality (requires MPI; uses libtorch "
        "via py-torch)",
    )

    # Optional scientific libraries
    variant("libri", default=False, description="Enable EXX with LibRI")
    variant("libxc", default=False, description="Enable LibXC functionality")
    variant("rapidjson", default=False, description="Enable RapidJSON usage")

    # ------------------------------------------------------------------ #
    #  Dependencies                                                       #
    # ------------------------------------------------------------------ #

    # Language and build tools.
    # ABACUS declares `project(... LANGUAGES CXX)`, but the source tree ships
    # one .c file (source_base/mcd.c); keep `c` for safety and parity with
    # other DFT packages (e.g. cp2k).
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
    depends_on("py-torch", when="+deepks")
    depends_on("rapidjson", when="+rapidjson")

    # OpenMP propagation: ensure threaded BLAS/FFTW/MKL providers are chosen
    with when("+openmp"):
        depends_on("fftw+openmp", when="^[virtuals=fftw-api] fftw")
        depends_on(
            "openblas threads=openmp", when="^[virtuals=blas,lapack] openblas"
        )
        depends_on(
            "intel-oneapi-mkl threads=openmp",
            when="^[virtuals=blas,lapack,scalapack,fftw-api] intel-oneapi-mkl",
        )

    # ------------------------------------------------------------------ #
    #  Conflicts                                                          #
    # ------------------------------------------------------------------ #

    # LTS FindMKL only locates Intel Fortran interfaces; linking with gcc fails.
    conflicts(
        "%gcc ^intel-oneapi-mkl",
        msg="ABACUS LTS MKL backend only provides Intel Fortran interfaces. "
        "Use %intel-oneapi-compilers with intel-oneapi-mkl, or pick a "
        "non-MKL BLAS/FFTW provider (e.g. openblas + fftw).",
    )

    # ------------------------------------------------------------------ #
    #  CMake arguments                                                    #
    # ------------------------------------------------------------------ #

    def cmake_args(self):
        spec = self.spec
        args = [
            # --- variant -> option mapping ---
            self.define_from_variant("ENABLE_MPI", "mpi"),
            self.define_from_variant("USE_OPENMP", "openmp"),
            self.define_from_variant("ENABLE_LCAO", "lcao"),
            self.define_from_variant("USE_ELPA", "elpa"),
            self.define_from_variant("ENABLE_LIBRI", "libri"),
            self.define_from_variant("ENABLE_LIBXC", "libxc"),
            self.define_from_variant("ENABLE_DEEPKS", "deepks"),
            self.define_from_variant("ENABLE_PEXSI", "pexsi"),
            self.define_from_variant("ENABLE_RAPIDJSON", "rapidjson"),
            self.define_from_variant("ENABLE_FLOAT_FFTW", "float-fftw"),
            self.define_from_variant(
                "ENABLE_NATIVE_OPTIMIZATION", "native-optimization"
            ),
            self.define_from_variant("DEBUG_INFO", "debug"),
            # --- force-disabled (LTS: CPU-only x86_64) ---
            self.define("USE_CUDA", False),
            self.define("USE_ROCM", False),
            self.define("USE_DSP", False),
            self.define("USE_CUDA_ON_DCU", False),
            self.define("ENABLE_CUSOLVERMP", False),
            self.define("ENABLE_PAW", False),
            # --- disable git/network (release tarball has no .git) ---
            self.define("GIT_SUBMODULE", False),
            self.define("COMMIT_INFO", False),
        ]

        # FFT backend: MKL (MKLROOT) vs FFTW3 (FFTW3_DIR).
        # LTS FindMKL.cmake reads the *CMake variable* ${MKLROOT} (not the env
        # var), so it must be passed explicitly. intel-oneapi-mkl ships MKL
        # under <prefix>/mkl/<version>/{include,lib}; the `latest` symlink
        # points at the active version and is stable across MKL releases.
        if "^intel-oneapi-mkl" in spec:
            mkl = spec["intel-oneapi-mkl"]
            args.append(
                self.define("MKLROOT", join_path(mkl.prefix, "mkl", "latest"))
            )
        else:
            args.append(self.define("FFTW3_DIR", spec["fftw-api"].prefix))

        # Cereal: FindCereal expects CEREAL_INCLUDE_DIR = include dir itself
        # (not the prefix), because it searches for cereal/cereal.hpp.
        if "+lcao" in spec:
            args.append(
                self.define("CEREAL_INCLUDE_DIR", spec["cereal"].prefix.include)
            )

        # ELPA: FindELPA uses ELPA_DIR (prefix), searches include/elpa*
        if "+lcao+elpa" in spec:
            args.append(self.define("ELPA_DIR", spec["elpa"].prefix))

        # LibRI / LibComm: ENABLE_LIBRI auto-enables ENABLE_LIBCOMM in CMake
        # (L548-565); we pass ENABLE_LIBCOMM explicitly for clarity and both
        # _DIR prefixes so the Find*.cmake modules locate our headers.
        if "+libri" in spec:
            args.append(self.define("ENABLE_LIBCOMM", True))
            args.append(self.define("LIBRI_DIR", spec["libri"].prefix))
            args.append(self.define("LIBCOMM_DIR", spec["libcomm"].prefix))

        # LibXC: FindLibxc uses Libxc_DIR (prefix) or pkg-config
        if "+libxc" in spec:
            args.append(self.define("Libxc_DIR", spec["libxc"].prefix))

        # PEXSI: FindPEXSI uses PEXSI_DIR (prefix)
        if "+pexsi" in spec:
            args.append(self.define("PEXSI_DIR", spec["pexsi"].prefix))

        # DeePKS: libtorch CMake config exported by py-torch under
        # <prefix>/libtorch/share/cmake/Torch
        if "+deepks" in spec:
            torch = spec["py-torch"]
            args.append(
                self.define(
                    "Torch_DIR",
                    join_path(
                        torch.prefix, "libtorch", "share", "cmake", "Torch"
                    ),
                )
            )

        return args
