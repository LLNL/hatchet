# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# This code comes from the equivalent file in Thicket:
# https://github.com/LLNL/thicket
import os
import sys
import subprocess

_filenotfound_errmsg = """
Cannot find NPM!
This is required to use hatchet.vis!
Please install NPM and try again to import hatchet.vis!
"""


def check_npm():
    if sys.version_info[0] == 2:
        from distutils.spawn import find_executable

        return find_executable("npm") is not None
    from shutil import which

    return which("npm") is not None


def npm_build(vis_directory):
    print("Building hatchet.vis using NPM!")
    subprocess.check_output(["npm", "install", "-y"], cwd=vis_directory)
    subprocess.check_output(["npm", "run", "build"], cwd=vis_directory)


# Get the absolute path to this __init__.py file
# Store in curr_dir to minimize the number of variables
curr_dir = os.path.realpath(os.path.expanduser(__file__))
# Get the hatchet/vis directory from the path to this __init__.py file
curr_dir = os.path.abspath(os.path.join(curr_dir, os.pardir))
# Get the path to hatchet/vis/package-lock.json
pkg_lock_file = os.path.abspath(os.path.join(curr_dir, "package-lock.json"))

if not os.path.isfile(pkg_lock_file):
    if not check_npm():
        raise FileNotFoundError(_filenotfound_errmsg)
    else:
        npm_build(curr_dir)
