# Copyright Spack Project Developers. See COPYRIGHT file for details.
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import shutil
import stat
import zipfile

from spack_repo.builtin.build_systems.generic import Package

from spack.package import *


class LibtensorflowCc(Package):
    """Prebuilt TensorFlow 2.x CPU C/C++ shared libraries and headers
    (``libtensorflow_cc.so.2``, ``libtensorflow_framework.so.2``, and
    ``include/``) extracted from official PyPI ``tensorflow-cpu`` manylinux
    wheels.

    Provides the exact C/C++ libraries and headers needed by ``cppflow`` and
    VASPml ``+grace`` without pulling Bazel, OpenJDK, LLVM/libclang, or the
    Python TensorFlow runtime dependency graph into Spack CPU builds.
    """

    homepage = "https://www.tensorflow.org"

    license("Apache-2.0")

    # Official Google PyPI tensorflow-cpu wheels (Linux x86_64).
    # Only the Python-independent C/C++ libraries and headers are extracted;
    # 2.20.0 is preferred as the latest manylinux_2_17 (glibc >= 2.17) release.
    version(
        "2.21.0",
        sha256="dcc8afd32930e42d5296b6ee19078b773706830af4ea97fbe503b9f5e0f820cb",
        url="https://files.pythonhosted.org/packages/6f/07/a691049cb74276164d8449de9e25c4f51ad3111a3eba86358395d2552fc3/tensorflow_cpu-2.21.0-cp312-cp312-manylinux_2_27_x86_64.whl",
        expand=False,
    )
    version(
        "2.20.0",
        sha256="c7a9224185818094ed95c4e114d3efe77241db35fbf0b75251fb2bf6222dd6a7",
        url="https://files.pythonhosted.org/packages/62/62/acf40b822414f1e2b6cae8495d6ba0aeed66ac9ffcc2e43a9b82d7688da9/tensorflow_cpu-2.20.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        expand=False,
        preferred=True,
    )
    version(
        "2.19.1",
        sha256="2cb4b20fa86b04c166db1616fd466d09ec850cc3b47607cf12225469e750c476",
        url="https://files.pythonhosted.org/packages/28/65/a6896d25bf34e5ff211b352cb505f2492f279fad31fdd1e36e3a782c19c7/tensorflow_cpu-2.19.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        expand=False,
    )
    version(
        "2.18.1",
        sha256="8e0f27dbd92c6d380ae0ccfe73c7343f65c127b0aa98467c30c2e71eda7c76a4",
        url="https://files.pythonhosted.org/packages/12/cb/5d428ab3861782f2f50b59813d105cbe6da6f452f7f1a03341cb8d12a9cc/tensorflow_cpu-2.18.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        expand=False,
    )

    for _constraint in (
        "platform=darwin",
        "platform=windows",
        "platform=freebsd",
        "target=aarch64:",
        "target=ppc64:",
        "target=ppc64le:",
        "target=riscv64:",
    ):
        conflicts(
            _constraint,
            msg="libtensorflow-cc prebuilt wheels are only available for Linux x86_64",
        )

    # Precompiled shared libraries reference host/toolchain glibc and libstdc++
    # without Spack compiler-wrapper RPATHs (same pattern as openjdk / oneapi).
    unresolved_libraries = ["*"]

    sanity_check_is_file = [
        join_path("include", "tensorflow", "c", "c_api.h"),
        join_path("lib", "libtensorflow_cc.so"),
        join_path("lib", "libtensorflow_cc.so.2"),
        join_path("lib", "libtensorflow_framework.so"),
        join_path("lib", "libtensorflow_framework.so.2"),
    ]

    @property
    def libs(self):
        return find_libraries(
            ["libtensorflow_cc", "libtensorflow_framework"],
            root=self.prefix.lib,
            shared=True,
            recursive=False,
        )

    @property
    def headers(self):
        return find_headers("c_api", root=self.prefix.include, recursive=True)

    def install(self, spec, prefix):
        inc_prefix = "tensorflow/include/"
        so_names = {
            "tensorflow/libtensorflow_cc.so.2": "libtensorflow_cc.so",
            "tensorflow/libtensorflow_framework.so.2": "libtensorflow_framework.so",
        }

        mkdirp(prefix.include)
        mkdirp(prefix.lib)
        lic_dir = join_path(prefix.share, "licenses", "libtensorflow-cc")
        mkdirp(lic_dir)

        with zipfile.ZipFile(self.stage.archive_file, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename

                if name in so_names:
                    soname_file = os.path.basename(name)
                    dst = join_path(prefix.lib, soname_file)
                    with zf.open(info, "r") as src_f, open(dst, "wb") as dst_f:
                        shutil.copyfileobj(src_f, dst_f, length=8 * 1024 * 1024)
                    os.chmod(dst, 0o755)
                elif name.startswith(inc_prefix):
                    rel = os.path.normpath(name[len(inc_prefix) :])
                    if rel.startswith("..") or rel == ".":
                        continue
                    dst = join_path(prefix.include, rel)
                    mkdirp(os.path.dirname(dst))
                    mode = info.external_attr >> 16
                    if stat.S_ISLNK(mode):
                        link_target = zf.read(info).decode("utf-8")
                        symlink(link_target, dst)
                    else:
                        with zf.open(info, "r") as src_f, open(dst, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f)
                        os.chmod(dst, 0o644)
                elif name.endswith(".dist-info/LICENSE"):
                    dst = join_path(lic_dir, "LICENSE")
                    with zf.open(info, "r") as src_f, open(dst, "wb") as dst_f:
                        shutil.copyfileobj(src_f, dst_f)
                    os.chmod(dst, 0o644)

        for ver_path, unversioned_name in so_names.items():
            soname_file = os.path.basename(ver_path)
            link_path = join_path(prefix.lib, unversioned_name)
            if not os.path.lexists(link_path):
                symlink(soname_file, link_path)
