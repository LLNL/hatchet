# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from codecs import open
from os import path

from setuptools import Extension, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Get the version in a safe way which does not refrence hatchet `__init__` file
# per python docs: https://packaging.python.org/guides/single-sourcing-package-version/
version = {}
with open("./hatchet/version.py") as fp:
    exec(fp.read(), version)


cmd_class = {}
ext_modules = []
should_cythonize = False
mod_import_path = "hatchet.cython_modules.libs"
mod_file_path = "hatchet/cython_modules"
mod_names = [
    "reader_modules",
    "graphframe_modules",
]


for mname in mod_names:
    c_file = path.join(mod_file_path, "{}.c".format(mname))
    pyx_file = path.join(mod_file_path, "{}.pyx".format(mname))
    if not path.isfile(pyx_file):
        raise FileNotFoundError(
            "Requested Cython extension not found: {}".format(pyx_file)
        )
    if path.isfile(c_file):
        should_cythonize = False
        ext_modules.append(
            Extension(
                "{}.{}".format(mod_import_path, mname),
                [c_file],
            )
        )
    else:
        should_cythonize = True
        ext_modules.append(
            Extension(
                "{}.{}".format(mod_import_path, mname),
                [pyx_file],
            )
        )

if should_cythonize:
    from Cython.Build import build_ext, cythonize

    ext_modules = cythonize(ext_modules)
    cmd_class.update({"build_ext": build_ext})


ext_modules = [
    Extension(
        "hatchet.cython_modules.libs.reader_modules",
        ["hatchet/cython_modules/reader_modules.pyx"],
    ),
    Extension(
        "hatchet.cython_modules.libs.graphframe_modules",
        ["hatchet/cython_modules/graphframe_modules.pyx"],
    ),
]


setup(
    name="llnl-hatchet",
    version=version["__version__"],
    license="MIT",
    description="A Python library for analyzing hierarchical performance data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/llnl/hatchet",
    project_urls={
        "Source Code": "https://github.com/llnl/hatchet",
        "Documentation": "https://llnl-hatchet.readthedocs.io/en/latest/",
    },
    author="Stephanie Brink",
    author_email="brink2@llnl.gov",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="",
    python_requires=">=3.5",
    packages=[
        "hatchet",
        "hatchet.readers",
        "hatchet.writers",
        "hatchet.query",
        "hatchet.vis",
        "hatchet.util",
        "hatchet.external",
        "hatchet.tests",
        "hatchet.cython_modules.libs",
    ],
    include_package_data=True,
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
    ext_modules=ext_modules,
    cmdclass=cmd_class,
)
