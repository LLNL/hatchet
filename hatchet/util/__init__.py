# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import sys

import numpy as np


def _validate_numpy_version_for_hdf():
    is_py_lt_3_10 = sys.version_info < (3, 10)
    is_np_ge_2 = tuple(map(int, (np.__version__.split(".")))) >= (2, 0)
    return is_py_lt_3_10 and is_np_ge_2
