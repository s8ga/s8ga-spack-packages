# Copyright Spack Project Developers. See COPYRIGHT file for details.
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.generic import Package

from spack.package import *


class Cppflow(Package):
    """cppflow: header-only C++17 wrapper around the TensorFlow 2.x C API for
    running SavedModel inference without Bazel or the TensorFlow C++ build
    system.

    Packages the ACEworksGmbH fork recommended by VASP for VASPml GRACE
    machine-learned force fields (backward-compatible with serizba/cppflow
    while adding session option and signature inspection helpers).
    """

    homepage = "https://github.com/ACEworksGmbH/cppflow"
    git = "https://github.com/ACEworksGmbH/cppflow.git"

    license("MIT")

    version(
        "2.0.4aw",
        tag="v2.0.4aw",
        commit="83f89ea661f42d9bdb615da3d2d7ca252bd7cbb6",
        preferred=True,
    )
    version(
        "2.0.0",
        tag="v2.0.0",
        commit="99e04d7045af79ef8fe9f906cf0d9bd5559dd935",
    )

    depends_on("cxx", type="build")

    sanity_check_is_file = [
        join_path("include", "cppflow", "cppflow.h"),
        join_path("include", "cppflow", "model.h"),
    ]

    def install(self, spec, prefix):
        install_tree("include", prefix.include)
