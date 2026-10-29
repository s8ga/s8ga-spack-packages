# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.cmake import CMakePackage
from spack.package import *


class Libmbd(CMakePackage):
    """libMBD: A general-purpose package for scalable quantum many-body
    dispersion (MBD) calculations. Fortran reference implementation with
    analytical gradients and optional distributed parallelism via
    ScaLAPACK/MPI."""

    homepage = "https://github.com/libmbd/libmbd"
    url = "https://github.com/libmbd/libmbd/releases/download/0.15.0/libmbd-0.15.0.tar.gz"
    list_url = "https://github.com/libmbd/libmbd/releases"

    # cmake-only build system (upstream has no makefile/autotools)
    build_system("cmake", default="cmake")

    version("master", branch="master")
    version(
        "0.15.0",
        sha256="f309447547f5203c179a9c8344dbf55fd4781852d9e7f248b1c6b5da69e533c8",
    )
    version(
        "0.14.1",
        sha256="8e0b49fd7e1fef6a77897ce54fc17218e4022d799e5a41f855af03a9404177f2",
    )
    version(
        "0.14.0",
        sha256="e08033d2baa8c42dcc12fb1bec4748cd9b507e6d4095cce00f643c16a4406fed",
    )
    version(
        "0.12.8",
        sha256="c50a61068d7aeb1ff76c32dcbf6aae848e47972bdbcfe609bd6050e853f76b1e",
    )

    variant("shared", default=True, description="Build shared library")
    variant("static", default=False, description="Build static library")
    variant(
        "mpi",
        default=False,
        description="Enable ScaLAPACK/MPI distributed parallelism",
    )

    depends_on("c", type="build")
    depends_on("fortran", type="build")
    depends_on("blas")
    depends_on("lapack")
    depends_on("mpi", when="+mpi")
    depends_on("scalapack", when="+mpi")

    conflicts("+shared", when="+static", msg="Use either +shared or +static, not both")

    def cmake_args(self):
        spec = self.spec
        args = [
            self.define_from_variant("ENABLE_SCALAPACK_MPI", "mpi"),
        ]
        if spec.satisfies("+static"):
            args.append(self.define("BUILD_SHARED_LIBS", False))
        elif spec.satisfies("+shared"):
            args.append(self.define("BUILD_SHARED_LIBS", True))
        return args
