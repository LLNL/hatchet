# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from setuptools import setup
from setuptools import Extension
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Get the version in a safe way which does not refrence hatchet `__init__` file
# per python docs: https://packaging.python.org/guides/single-sourcing-package-version/
version = {}
with open("./hatchet/version.py") as fp:
    exec(fp.read(), version)


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
        "hatchet.cython_modules.libs",
    ],
    install_requires=[
        "pydot",
        "PyYAML",
        "matplotlib",
        "numpy",
        "pandas",
        "textX",
        "multiprocess",
        "caliper-reader",
    ],
    ext_modules=[
        Extension(
            "hatchet.cython_modules.libs.reader_modules",
            ["hatchet/cython_modules/reader_modules.c"],
        ),
        Extension(
            "hatchet.cython_modules.libs.graphframe_modules",
            ["hatchet/cython_modules/graphframe_modules.c"],
        ),
    ],
)
