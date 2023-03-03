# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from setuptools import setup
from setuptools import Extension
from setuptools.command.build_ext import build_ext as build_ext_orig
from codecs import open
from os import path
import sys

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Get the version in a safe way which does not refrence hatchet `__init__` file
# per python docs: https://packaging.python.org/guides/single-sourcing-package-version/
version = {}
with open("./hatchet/version.py") as fp:
    exec(fp.read(), version)


# Obtained from https://github.com/himbeles/ctypes-example/blob/master/setup.py
class CTypesExtension(Extension):
    pass


class build_ext(build_ext_orig):

    def __init__(self, *args, **kwargs):
        self._ctypes = False
        if sys.version_info[0] == 2:
            super(build_ext, self).__init__(*args, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    def build_extension(self, ext):
        self._ctypes = isinstance(ext, CTypesExtension)
        if sys.version_info[0] == 2:
            return super(build_ext, self).build_extension(ext)
        else:
            return super().build_extension(ext)

    def get_export_symbols(self, ext):
        if self._ctypes:
            return ext.export_symbols
        if sys.version_info[0] == 2:
            return super(build_ext, self).get_export_symbols(ext)
        return super().get_export_symbols(ext)

    def get_ext_filename(self, ext_name):
        if self._ctypes:
            return ext_name + ".so"
        if sys.version_info[0] == 2:
            return super(build_ext, self).get_ext_filename(ext_name)
        return super().get_ext_filename(ext_name)


setup(
    name="llnl-hatchet",
    version=version["__version__"],
    description="A Python library for analyzing hierarchical performance data",
    url="https://github.com/llnl/hatchet",
    author="Stephanie Brink",
    author_email="brink2@llnl.gov",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="",
    packages=[
        "hatchet",
        "hatchet.readers",
        "hatchet.writers",
        "hatchet.util",
        "hatchet.external",
        "hatchet.tests",
        "hatchet.extension",
    ],
    install_requires=[
        "pydot",
        "PyYAML",
        "matplotlib",
        "numpy",
        "pandas",
        "textX < 3.0.0; python_version < '3.6'",
        "textX >= 3.0.0; python_version >= '3.6'",
        "multiprocess",
        "caliper-reader",
    ],
    ext_modules=[
        CTypesExtension(
            "hatchet.extension.libreader_modules",
            [
                "hatchet/extension/reader_modules.c",
            ]
        ),
        CTypesExtension(
            "hatchet.extension.libgraphframe_modules",
            [
                "hatchet/extension/graphframe_modules.c",
            ],
        ),
    ],
    cmdclass={"build_ext": build_ext},
)
