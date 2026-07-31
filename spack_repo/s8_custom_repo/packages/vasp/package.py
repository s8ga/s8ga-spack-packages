# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import shutil
import re
import glob

from spack_repo.builtin.build_systems import cmake, makefile
from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack_repo.builtin.build_systems.cuda import CudaPackage
from spack_repo.builtin.build_systems.makefile import MakefilePackage

from spack.package import *


class Vasp(MakefilePackage, CMakePackage, CudaPackage):
    """
    The Vienna Ab initio Simulation Package (VASP)
    is a computer program for atomic scale materials modelling,
    e.g. electronic structure calculations
    and quantum-mechanical molecular dynamics, from first principles.
    """

    homepage = "https://vasp.at"
    url = "file://{0}/vasp.5.4.4.pl2.tgz".format(os.getcwd())
    maintainers("snehring")
    manual_download = True

    # ------------------------------------------------------------------
    # Versions
    # ------------------------------------------------------------------
    version("6.6.0", sha256="9566f59b0ae2fc60f670a91153655d09dba13fe6cc6c54e9ca6bd03bbcd86384")
    version("6.5.1", sha256="a53fd9dd2a66472a4aa30074dbda44634fc663ea2628377fc01d870e37136f61")
    version("6.5.0", sha256="7836f0fd2387a6768be578f1177e795dc625f36f19015e31cab0e81154a24196")
    version("6.4.3", sha256="fe30e773f2a3e909b5e0baa9654032dfbdeff7ec157bc348cee7681a7b6c24f4")
    version("6.4.2", sha256="b704637f7384673f91adfbc803edc5cc7fe736d9623453461f7cdc29b123410e")
    version("6.3.2", sha256="f7595221b0f9236a324ea8afe170637a578cdd5a837cc7679e7f7812f6edf25a")
    version("6.3.1", sha256="113db53c4346287c89982f52887a65d12d246e38de7ccd024e44499c4774dc66")
    version("6.3.0", sha256="adcf83bdfd98061016baae31616b54329563aa2739573f069dd9df19c2071ad3")

    # ------------------------------------------------------------------
    # Build system selection (cmake preferred for 6.6.0+)
    # ------------------------------------------------------------------
    build_system(
        conditional("cmake", when="@6.6.0:"),
        conditional("makefile"),
        default="cmake",
    )

    # ------------------------------------------------------------------
    # Variants
    # ------------------------------------------------------------------
    variant("openmp", default=False, description="Enable openmp build")

    variant("cuda", default=False, description="Enables running on Nvidia GPUs")
    variant("fftlib", default=True, when="+openmp", description="Enables fftlib build")

    variant("shmem", default=True, description="Enable use_shmem build flag")
    variant("hdf5", default=False, description="Enabled HDF5 support")
    variant("libbeef", default=False, description="Enable Libbeef support")
    variant("libxc", default=False, description="Enable Libxc support")
    variant("wannier90", default=False, description="Enable wannier90 support")

    variant("vtst", default=False, description="Enable VTST modified code")
    resource(
        name="vtst_src",
        url="https://github.com/henkelmangroup/vtstcode/archive/2596bccc6ef684965cd528841ea617334fa50e13.tar.gz",
        sha256="4275937fd7e19155ae8c87b51c7e7b4b07e18645e84f3287098976d02c810f79",
        placement="vtst_src",
        when="+vtst",
    )

    variant("vaspsol", default=False, description="Enable VASPsol solvation model")

    variant("dftd4", default=False, description="Enable DFT-D4 van der Waals correction")
    variant("sdftd3", default=False, description="Enable simple-DFT-D3 van der Waals correction")

    variant("elpa", default=False, description="Enable ELPA eigenvalue solver")

    variant("libmbd", default=False, description="Enable libMBD many-body dispersion")

    # ------------------------------------------------------------------
    # vasp-cmake resource (for build_system=cmake)
    # ------------------------------------------------------------------
    resource(
        name="vasp_cmake",
        git="https://github.com/s8ga/vasp-cmake.git",
        branch="6.6.x",
        placement="cmake",
        when="build_system=cmake",
    )

    # ------------------------------------------------------------------
    # Patches
    # ------------------------------------------------------------------
    patch("WANNIER90_WIN_MAXLEN_fix.patch", when="@6.2.0: +wannier90")
    patch("pot_electrostat_fix.patch", when="@6.6.0")

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------
    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("fortran", type="build")

    depends_on("rsync", type="build")
    depends_on("blas")
    depends_on("lapack")
    depends_on("fftw-api")
    depends_on("fftw+openmp", when="+openmp ^[virtuals=fftw-api] fftw")
    depends_on("amdfftw+openmp", when="+openmp ^[virtuals=fftw-api] amdfftw")
    depends_on("amdblis threads=openmp", when="+openmp ^[virtuals=blas] amdblis")
    depends_on("openblas threads=openmp", when="+openmp ^[virtuals=blas] openblas")
    depends_on("mpi", type=("build", "link", "run"))
    # fortran oddness requires the below
    depends_on("openmpi%aocc", when="%aocc ^[virtuals=mpi] openmpi")
    depends_on("openmpi%gcc", when="%gcc ^[virtuals=mpi] openmpi")
    depends_on("scalapack")
    depends_on("nccl", when="+cuda")
    depends_on("hdf5+fortran+mpi", when="+hdf5")
    depends_on("libbeef", when="+libbeef")
    depends_on("libxc~fhc+fortran", when="+libxc")
    depends_on("wannier90", when="+wannier90")

    # DFTD4 / SDFTD3: cmake build needs cmake-config installed
    depends_on("dftd4", when="+dftd4")
    depends_on("simple-dftd3", when="+sdftd3")
    with when("build_system=cmake"):
        depends_on("dftd4 build_system=cmake", when="+dftd4")
        depends_on("simple-dftd3 build_system=cmake", when="+sdftd3")

    # ELPA
    depends_on("elpa+openmp", when="+elpa+openmp")
    depends_on("elpa~openmp", when="+elpa~openmp")

    # libMBD: require static + no MPI (VASP NEB correctness)
    depends_on("libmbd~mpi+static build_system=cmake", when="+libmbd")
    conflicts(
        "^libmbd+mpi",
        when="+libmbd",
        msg="VASP requires libMBD without ScaLAPACK/MPI for correct NEB results",
    )

    # cmake build needs pkg-config and cmake itself
    depends_on("pkgconfig", type="build", when="build_system=cmake")
    depends_on("cmake@3.24:", type="build", when="build_system=cmake")

    # at the very least the nvhpc mpi seems required
    requires("^nvhpc+mpi+lapack+blas", when="%nvhpc")

    # ------------------------------------------------------------------
    # Conflicts
    # ------------------------------------------------------------------
    conflicts(
        "%gcc@:8", msg="GFortran before 9.x does not support all features needed to build VASP"
    )
    requires("%nvhpc", when="+cuda", msg="vasp requires nvhpc to build the openacc build")
    # intel mkl/mpi conflicts with ilp64, which is a default behaviour
    requires("^intel-oneapi-mkl~ilp64", when="^intel-oneapi-mkl")
    requires("^intel-oneapi-mpi~ilp64", when="^intel-oneapi-mpi")
    # the mpi compiler wrappers in nvhpc assume nvhpc is the underlying compiler, seemingly
    conflicts("^[virtuals=mpi] nvhpc", when="%gcc", msg="nvhpc mpi requires nvhpc compiler")
    conflicts("^[virtuals=mpi] nvhpc", when="%aocc", msg="nvhpc mpi requires nvhpc compiler")
    conflicts("cuda_arch=none", when="+cuda", msg="CUDA arch required when building openacc port")

    # ------------------------------------------------------------------
    # Shared patch logic (runs for both build systems)
    # ------------------------------------------------------------------
    def patch(self):
        # --- VTST source injection ---
        if "+vtst" in self.spec:
            v_src = join_path(self.stage.source_path, "src")
            vt_src = join_path(self.stage.source_path, "vtst_src", "vtstcode6.6.0")

            for f in os.listdir(vt_src):
                if f.endswith((".F", ".f90")) and os.path.isfile(join_path(vt_src, f)):
                    shutil.copyfile(join_path(vt_src, f), join_path(v_src, f))

            pyamff_src = join_path(vt_src, "pyamff_fortran")
            pyamff_dst = join_path(v_src, "pyamff_fortran")
            if os.path.exists(pyamff_src):
                if os.path.exists(pyamff_dst):
                    shutil.rmtree(pyamff_dst)
                shutil.copytree(pyamff_src, pyamff_dst)

            m_file = join_path(v_src, "makefile")
            filter_file(r"LIB\s*=\s*lib\s+parser", "LIB = lib parser pyamff_fortran", m_file)
            filter_file(
                r"dependencies:\s*sources", "dependencies: sources libs", m_file
            )

            objs_list = (
                "bfgs.o dynmat.o instanton.o lbfgs.o sd.o cg.o dimer.o bbm.o fire.o "
                "lanczos.o neb.o qm.o pyamff_fortran/*.o ml_pyamff.o opt.o".split()
            )
            objs = "".join(f"\t{x} \\\n" for x in objs_list)
            filter_file(
                r"^(\s*)(chain\.o)",
                lambda m: f"{m.group(1)}{objs}chain.o",
                join_path(v_src, ".objects"),
            )

            m_path = join_path(v_src, "main.F")
            with open(m_path, "r", encoding="utf-8") as f:
                txt = f.read()

            txt = re.sub(
                r"IF\s*\(\s*LCHAIN\s*\)\s*CALL\s+chain_init\s*\(\s*T_INFO\s*,\s*IO\s*\)",
                "CALL chain_init( T_INFO, IO)",
                txt,
            )
            txt = re.sub(
                r"(CALL\s+CHAIN_FORCE\([^&]+&\s*\r?\n\s*)(LATT_CUR%A,)",
                r"\1TSIF,\2",
                txt,
            )

            with open(m_path, "w", encoding="utf-8") as f:
                f.write(txt)

        # --- VASPsol source injection ---
        if "+vaspsol" in self.spec:
            tty.msg("Overwriting solvation.F with local vaspsol_solvation.F...")
            v_src = join_path(self.stage.source_path, "src")

            sol_src = join_path(self.package_dir, "vaspsol_solvation.F")
            sol_dst = join_path(v_src, "solvation.F")

            if os.path.exists(sol_src):
                shutil.copyfile(sol_src, sol_dst)

            patch_file = join_path(self.package_dir, "vaspsol_660.patch")
            if os.path.exists(patch_file):
                patch_bin = which("patch")
                with working_dir(self.stage.source_path):
                    patch_bin("-p0", "-i", patch_file)
                tty.msg("Successfully applied local VASPsol 6.6.0 patch!")

        # --- cmake build: run setup.sh to create CMakeLists symlinks ---
        if self.spec.satisfies("build_system=cmake"):
            setup_sh = join_path(self.stage.source_path, "cmake", "setup.sh")
            if os.path.exists(setup_sh):
                bash = which("bash")
                with working_dir(self.stage.source_path):
                    bash("cmake/setup.sh")
                tty.msg("vasp-cmake: CMakeLists.txt symlinks created via setup.sh")
            else:
                tty.warn("build_system=cmake but cmake/setup.sh not found!")

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------
    def setup_build_environment(self, env):
        if self.spec.satisfies("+cuda %nvhpc"):
            env.set("NVHPC_CUDA_HOME", self.spec["cuda"].prefix)

        # vasp-cmake ships custom Find*.cmake modules that don't always search
        # CMAKE_PREFIX_PATH.  Map each spack dependency to the *_ROOT env var
        # the corresponding find module expects.
        _ROOT_MAP = {
            "scalapack": "SCALAPACK_ROOT",
            "fftw-api": "FFTW_ROOT",
            "libxc": "LibXC_ROOT",
            "wannier90": "WANNIER90_ROOT",
            "hdf5": "HDF5_ROOT",
            "dftd4": "DFTD4_ROOT",
            "libbeef": "LIBBEEF_ROOT",
            "elpa": "ELPA_ROOT",
            "libmbd": "LIBMBD_ROOT",
        }
        for dep, var in _ROOT_MAP.items():
            if dep in self.spec:
                env.set(var, self.spec[dep].prefix)


# ==========================================================================
# MakefileBuilder (legacy makefile-based build, fully preserved from HPC ver)
# ==========================================================================
class MakefileBuilder(makefile.MakefileBuilder):
    def edit(self, pkg, spec, prefix):
        cpp_options = [
            "-DMPI",
            "-DMPI_BLOCK=8000",
            "-Duse_collective",
            "-DCACHE_SIZE=4000",
            "-Davoidalloc",
            "-Duse_bse_te",
            "-Dtbdyn",
            "-Dfock_dblbuf",
            "-Dvasp6",
        ]

        if spec.satisfies("+vaspsol"):
            cpp_options.append("-Dsol_compat")

        objects_lib = ["linpack_double.o"]
        llibs = list(self.compiler.stdcxx_libs)
        cflags = ["-fPIC", "-DAAD_"]
        fflags = ["-w", "-ffpe-summary=none"]

        fftw_api = spec["fftw-api"]
        incs = [fftw_api.headers.include_flags]
        if fftw_api.name == "intel-oneapi-mkl":
            incs.append(f"-I{join_path(fftw_api.headers.directories[0], 'fftw')}")

        if spec["blas"].name == "intel-oneapi-mkl":
            llibs.append("-Wl,--no-as-needed")

        llibs.extend([spec["blas"].libs.ld_flags, spec["lapack"].libs.ld_flags])

        fc = [spec["mpi"].mpifc]
        fcl = [spec["mpi"].mpifc]

        omp_flag = "-fopenmp"

        if spec.satisfies("+shmem"):
            cpp_options.extend(["-Duse_shmem", "-Dshmem_bcast_buffer", "-Dshmem_rproj"])
            objects_lib.append("getshmem.o")

        include_string = "makefile.include."

        # gcc
        if spec.satisfies("%gcc"):
            include_string += "gnu"
            if spec.satisfies("+openmp"):
                include_string += "_omp"
            make_include = join_path("arch", include_string)
        # oneapi
        elif spec.satisfies("%oneapi"):
            include_string += "oneapi"
            if spec.satisfies("+openmp"):
                include_string += "_omp"
            make_include = join_path("arch", include_string)
            filter_file(r"^CC_LIB[ ]{0,}=.*$", f"CC_LIB={spack_cc}", make_include)
            filter_file(r"^CXX_PARS[ ]{0,}=.*$", f"CXX_PARS={spack_cxx}", make_include)
        # nvhpc
        elif spec.satisfies("%nvhpc"):
            qd_root = join_path(
                spec["nvhpc"].prefix,
                f"Linux_{spec['nvhpc'].target.family.name}",
                str(spec["nvhpc"].version.dotted),
                "compilers",
                "extras",
                "qd",
            )
            nvroot = join_path(
                spec["nvhpc"].prefix, f"Linux_{spec['nvhpc'].target.family.name}"
            )
            cpp_options.extend(['-DHOST=\\"LinuxNV\\"', "-Dqd_emulate"])

            fflags.extend(["-Mnoupcase", "-Mbackslash", "-Mlarge_arrays"])
            incs.append(f"-I{join_path(qd_root, 'include', 'qd')}")
            llibs.extend([f"-L{join_path(qd_root, 'lib')}", "-lqdmod", "-lqd"])

            include_string += "nvhpc"
            if spec.satisfies("+openmp"):
                include_string += "_omp"
            if spec.satisfies("+cuda"):
                include_string += "_acc"
            make_include = join_path("arch", include_string)
            omp_flag = "-mp"
            filter_file(r"^QD[ \t]*\??=.*$", f"QD = {qd_root}", make_include)
            filter_file("NVROOT[ \t]*=.*$", f"NVROOT = {nvroot}", make_include)
        # aocc
        elif spec.satisfies("%aocc"):
            cpp_options.extend(['-DHOST=\\"LinuxAMD\\"', "-Dshmem_bcast_buffer", "-DNGZhalf"])
            fflags.extend(["-fno-fortran-main", "-Mbackslash", "-ffunc-args-alias"])
            if spec.satisfies("^amdfftw@4.0:"):
                cpp_options.extend(["-Dfftw_cache_plans", "-Duse_fftw_plan_effort"])
            if spec.satisfies("+openmp"):
                if spec.satisfies("@6.3.2:"):
                    include_string += "aocc_ompi_aocl_omp"
                elif spec.satisfies("@=6.3.0"):
                    include_string += "gnu_ompi_aocl_omp"
                else:
                    include_string += "gnu_omp"
            else:
                if spec.satisfies("@6.3.2:"):
                    include_string += "aocc_ompi_aocl"
                elif spec.satisfies("@=6.3.0"):
                    include_string += "gnu_ompi_aocl"
                else:
                    include_string += "gnu"
            make_include = join_path("arch", include_string)
            filter_file(r"^CC_LIB[ ]{0,}=.*$", f"CC_LIB={spack_cc}", make_include)
            if spec.satisfies("@6:6.3.0"):
                filter_file("gcc", f"{spack_fc} -Mfree", make_include, string=True)
                filter_file(
                    "-fallow-argument-mismatch",
                    " -fno-fortran-main",
                    make_include,
                    string=True,
                )
        # fj
        elif spec.satisfies("@6.4.3: target=a64fx %fj"):
            include_string += "fujitsu_a64fx"
            omp_flag = "-Kopenmp"
            fc.extend(["simd_nouse_multiple_structures", "-X03"])
            fcl.append("simd_nouse_multiple_structures")
            cpp_options.append('-DHOST=\\"FJ-A64FX\\"')
            fflags.append("-Koptmsg=2")
            llibs.extend(["-SSL2BLAMP", "-SCALAPACK"])
            if spec.satisfies("+openmp"):
                include_string += "_omp"
            make_include = join_path("arch", include_string)

        else:
            if spec.satisfies("+openmp"):
                make_include = join_path(
                    "arch", f"{include_string}{spec.compiler.name}_omp"
                )
                if not os.path.exists(make_include):
                    make_include = join_path("arch", f"{include_string}gnu_omp")
            else:
                make_include = join_path("arch", include_string + spec.compiler.name)
                if not os.path.exists(make_include):
                    make_include = join_path("arch", f"{include_string}gnu")
            cpp_options.append('-DHOST=\\"LinuxGNU\\"')

        if spec.satisfies("+openmp"):
            cpp_options.extend(["-D_OPENMP"])
            llibs.extend(["-ldl", spec["fftw-api:openmp"].libs.ld_flags])
            fc.append(omp_flag)
            fcl.append(omp_flag)
        else:
            llibs.append(spec["fftw-api"].libs.ld_flags)

        if spec.satisfies("^scalapack"):
            cpp_options.append("-DscaLAPACK")
            if spec.satisfies("%nvhpc"):
                llibs.append("-Mscalapack")
            else:
                llibs.append(spec["scalapack"].libs.ld_flags)

        if spec.satisfies("+cuda"):
            # openacc
            if spec.satisfies("@6.5.0:"):
                cpp_options.extend(["-DACC_OFFLOAD", "-DNVCUDA", "-DUSENCCL"])
            else:
                cpp_options.extend(["-D_OPENACC", "-DUSENCCL"])
            llibs.extend(["-cudalib=cublas,cusolver,cufft,nccl", "-cuda"])
            fc.append("-acc")
            fcl.append("-acc")
            cuda_flags = [
                f"cuda{str(spec['cuda'].version.dotted[0:2])}", "rdc"
            ]
            for f in spec.variants["cuda_arch"].value:
                cuda_flags.append(f"cc{f}")
            fc.append(f"-gpu={','.join(cuda_flags)}")
            fcl.append(f"-gpu={','.join(cuda_flags)}")
            fcl.extend(list(self.compiler.stdcxx_libs))
            cc = [spec["mpi"].mpicc, "-acc"]
            if spec.satisfies("+openmp"):
                cc.append(omp_flag)
            filter_file(r"^CC[ \t]*=.*$", f"CC = {' '.join(cc)}", make_include)

        if spec.satisfies("+hdf5"):
            cpp_options.append("-DVASP_HDF5")
            llibs.append(spec["hdf5:fortran"].libs.ld_flags)
            incs.append(spec["hdf5"].headers.include_flags)

        if spec.satisfies("+libbeef"):
            cpp_options.append("-Dlibbeef")
            llibs.append(spec["libbeef"].libs.ld_flags)

        if spec.satisfies("+libxc"):
            cpp_options.append("-DUSELIBXC")
            llibs.append(spec["libxc:fortran"].libs.ld_flags)
            incs.append(spec["libxc"].headers.include_flags)

        if spec.satisfies("+wannier90"):
            cpp_options.append("-DVASP2WANNIER90")
            llibs.append(spec["wannier90"].libs.ld_flags)

        if spec.satisfies("%gcc@10:"):
            fflags.append("-fallow-argument-mismatch")

        filter_file(r"^VASP_TARGET_CPU[ ]{0,}\?=.*", "", make_include)

        if spec.satisfies("+fftlib"):
            cxxftlib = (
                f"CXX_FFTLIB = {spack_cxx} {omp_flag}"
                f" -DFFTLIB_THREADSAFE {' '.join(list(self.compiler.stdcxx_libs))}"
            )
            filter_file("^#FCL[ ]{0,}=fftlib.o", "FCL += fftlib/fftlib.o", make_include)
            filter_file("^#CXX_FFTLIB.*$", cxxftlib, make_include)

            fftw = spec["fftw-api"]
            fftw_inc_flags = fftw.headers.include_flags
            if fftw.name == "intel-oneapi-mkl":
                fftw_inc_flags += f" -I{join_path(fftw.headers.directories[0], 'fftw')}"

            filter_file(
                "^#INCS_FFTLIB.*$",
                f"INCS_FFTLIB = -I./include {fftw_inc_flags}",
                make_include,
            )
            filter_file(r"#LIBS[ \t]*\+=.*$", "LIBS = fftlib", make_include)
            llibs.append("-ldl")
            fcl.append(join_path("fftlib", "fftlib.o"))

        if spec.satisfies("+elpa"):
            cpp_options.append("-DELPA")

            elpa_prefix = spec["elpa"].prefix
            elpa_lib = (
                elpa_prefix.lib64
                if os.path.exists(elpa_prefix.lib64)
                else elpa_prefix.lib
            )

            lib_name = "elpa_openmp" if spec.satisfies("+openmp") else "elpa"
            llibs.extend([f"-L{elpa_lib}", f"-l{lib_name}"])

            incs.append(f"-I{elpa_prefix.include}")

            elpa_mod_dir = elpa_prefix.join(
                f"include/{lib_name}-{spec['elpa'].version}/modules"
            )

            if os.path.exists(elpa_mod_dir):
                incs.append(f"-I{elpa_mod_dir}")
            else:
                elpa_fallback_dir = elpa_prefix.join(
                    f"include/{lib_name}-{spec['elpa'].version}"
                )
                if os.path.exists(elpa_fallback_dir):
                    incs.append(f"-I{elpa_fallback_dir}")

        comp_vendor = "GNU" if self.compiler.name == "gcc" else self.compiler.name.upper()

        if spec.satisfies("+dftd4") or spec.satisfies("+sdftd3"):
            llibs.append("-Wl,--start-group")
            mctc_prefix = spec["mctc-lib"].prefix
            mctc_lib = (
                mctc_prefix.lib64
                if os.path.exists(mctc_prefix.lib64)
                else mctc_prefix.lib
            )
            llibs.extend([f"-L{mctc_lib}", "-lmctc-lib"])

            incs.append(f"-I{mctc_prefix.include}")

            mctc_mod_dir = mctc_prefix.join("include/mctc-lib/modules")
            if os.path.exists(mctc_mod_dir):
                incs.append(f"-I{mctc_mod_dir}")

        if spec.satisfies("+dftd4"):
            cpp_options.append("-DDFTD4")
            if spec.satisfies("^dftd4@:3.7.0"):
                cpp_options.append("-DDFTD4_API_V3")

            d4_prefix = spec["dftd4"].prefix
            d4_lib = (
                d4_prefix.lib64 if os.path.exists(d4_prefix.lib64) else d4_prefix.lib
            )
            llibs.extend([f"-L{d4_lib}", "-ldftd4", "-lmulticharge"])

            incs.append(f"-I{d4_prefix.include}")

            d4_mod_dir = d4_prefix.join(
                f"include/dftd4/{comp_vendor}-{self.compiler.version}"
            )
            if os.path.exists(d4_mod_dir):
                incs.append(f"-I{d4_mod_dir}")

        if spec.satisfies("+sdftd3"):
            cpp_options.append("-DSDFTD3")
            d3_prefix = spec["simple-dftd3"].prefix
            d3_lib = (
                d3_prefix.lib64 if os.path.exists(d3_prefix.lib64) else d3_prefix.lib
            )
            llibs.extend([f"-L{d3_lib}", "-ls-dftd3"])

            incs.append(f"-I{d3_prefix.include}")

            d3_mod_dir = d3_prefix.join(
                f"include/s-dftd3/{comp_vendor}-{self.compiler.version}"
            )
            if os.path.exists(d3_mod_dir):
                incs.append(f"-I{d3_mod_dir}")

        if spec.satisfies("+dftd4") or spec.satisfies("+sdftd3"):
            llibs.append("-Wl,--end-group")

        # clean multiline CPP options at begining of file
        filter_file(r"^[ \t]+(-D[a-zA-Z0-9_=]+[ ]*)+[ ]*\\*$", "", make_include)
        # replace relevant variables in the makefile.include
        filter_file("^FFLAGS[ \t]*=.*$", f"FFLAGS = {' '.join(fflags)}", make_include)
        filter_file(r"^FFLAGS[ \t]*\+=.*$", "", make_include)
        filter_file(
            "^CPP_OPTIONS[ \t]*=.*$",
            f"CPP_OPTIONS = {' '.join(cpp_options)}",
            make_include,
        )
        filter_file(r"^INCS[ \t]*\+?=.*$", f"INCS = {' '.join(incs)}", make_include)
        filter_file(r"^LLIBS[ \t]*\+?=.*$", f"LLIBS = {' '.join(llibs)}", make_include)
        filter_file(r"^LLIBS[ \t]*\+=[ ]*-.*$", "", make_include)
        filter_file("^CFLAGS[ \t]*=.*$", f"CFLAGS = {' '.join(cflags)}", make_include)
        filter_file(
            "^OBJECTS_LIB[ \t]*=.*$",
            f"OBJECTS_LIB = {' '.join(objects_lib)}",
            make_include,
        )
        filter_file("^FC[ \t]*=.*$", f"FC = {' '.join(fc)}", make_include)
        filter_file("^FCL[ \t]*=.*$", f"FCL = {' '.join(fcl)}", make_include)

        os.rename(make_include, "makefile.include")

    def build(self, pkg, spec, prefix):
        make("DEPS=1, all")

    def install(self, pkg, spec, prefix):
        install_tree("bin/", prefix.bin)


# ==========================================================================
# CMakeBuilder (new cmake-based build using s8ga/vasp-cmake)
# ==========================================================================
class CMakeBuilder(cmake.CMakeBuilder):
    def cmake_args(self):
        spec = self.spec
        args = [
            # Core feature toggles
            self.define_from_variant("VASP_OPENMP", "openmp"),
            self.define_from_variant("VASP_HDF5", "hdf5"),
            self.define_from_variant("VASP_LIBXC", "libxc"),
            self.define_from_variant("VASP_WANNIER90", "wannier90"),
            self.define_from_variant("VASP_LIBBEEF", "libbeef"),
            self.define_from_variant("VASP_DFTD4", "dftd4"),
            self.define_from_variant("VASP_SDFTD3", "sdftd3"),
            self.define_from_variant("VASP_ELPA", "elpa"),
            self.define_from_variant("VASP_FFTLIB", "fftlib"),
            self.define_from_variant("VASP_VASPSOL", "vaspsol"),
            self.define_from_variant("VASP_VTST", "vtst"),
            self.define_from_variant("VASP_LIBMBD", "libmbd"),
            self.define("VASP_SCALAPACK", True),
            self.define("VASP_TESTSUITE", False),
        ]

        # Shmem variants
        if spec.satisfies("+shmem"):
            args.append(self.define("VASP_SHMEM", True))
            args.append(self.define("VASP_SHMEM_BCAST", True))
            args.append(self.define("VASP_SHMEM_RPROJ", True))

        # CUDA (NVHPC OpenACC)
        if spec.satisfies("+cuda"):
            if spec.satisfies("cuda_arch=none"):
                raise InstallError(
                    "CUDA arch required for VASP OpenACC build. "
                    "Set cuda_arch=<values>."
                )
            args.append(self.define("VASP_CUDA", True))
            archs = ";".join(spec.variants["cuda_arch"].value)
            args.append(self.define("CMAKE_CUDA_ARCHITECTURES", archs))

        # DFTD4 API version: spack knows the exact version
        if spec.satisfies("+dftd4"):
            if spec.satisfies("^dftd4@:3.7.0"):
                args.append(self.define("VASP_DFTD4_API", "V3"))
            else:
                args.append(self.define("VASP_DFTD4_API", "V4"))

        # Force VASP_TARGET_CPU to match spack's resolved target, preventing
        # vasp-cmake from appending -march=native (or -tp=host for NVHPC) via
        # target_compile_options — that flag comes AFTER spack's wrapper-injected
        # -march and wins, breaking target portability (e.g. force_avx512 on
        # mixed-ISA clusters where build host != run host).
        try:
            opt_flags = spec.target.optimization_flags(
                spec.compiler.name, str(spec.compiler.version)
            )
        except Exception:
            opt_flags = None
        if opt_flags:
            m = re.search(r"-march=(\S+)", opt_flags)
            if m:
                args.append(self.define("VASP_TARGET_CPU", m.group(1)))
            elif spec.satisfies("%nvhpc"):
                # NVHPC uses -tp <name> instead of -march=<name>
                m = re.search(r"-tp\s+(\S+)", opt_flags)
                if m:
                    args.append(self.define("VASP_TARGET_CPU", m.group(1)))

        # Custom find modules in vasp-cmake don't search CMAKE_PREFIX_PATH;
        # pass explicit ROOT for each spack-managed dependency.
        _ROOT_MAP = {
            "scalapack": "SCALAPACK_ROOT",
            "fftw-api": "FFTW_ROOT",
            "libxc": "LibXC_ROOT",
            "wannier90": "WANNIER90_ROOT",
            "hdf5": "HDF5_ROOT",
            "dftd4": "DFTD4_ROOT",
            "libbeef": "LIBBEEF_ROOT",
            "elpa": "ELPA_ROOT",
            "libmbd": "LIBMBD_ROOT",
        }
        for dep, var in _ROOT_MAP.items():
            if dep in spec:
                args.append(self.define(var, spec[dep].prefix))

        return args

    @property
    def build_targets(self):
        return ["all"]

    def install(self, pkg, spec, prefix):
        mkdirp(prefix.bin)
        for exe in ("vasp_std", "vasp_gam", "vasp_ncl"):
            src = join_path(self.build_directory, "bin", exe)
            if os.path.exists(src):
                install(src, join_path(prefix.bin, exe))
