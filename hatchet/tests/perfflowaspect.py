# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np

from hatchet import GraphFrame


def test_laghos_graphframe(laghos_perfflowaspect_array):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_perfflowaspect(str(laghos_perfflowaspect_array))

    assert len(gf.dataframe.groupby("name")) == 4

    for col in gf.dataframe.columns:
        if col in ("ts", "dur"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("pid", "tid"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "ph"):
            assert gf.dataframe[col].dtype == object

    # TODO: add tests to confirm values in dataframe


def test_foobar_graphframe(foobar_perfflowaspect_array):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_perfflowaspect(str(foobar_perfflowaspect_array))

    assert len(gf.dataframe.groupby("name")) == 3

    for col in gf.dataframe.columns:
        if col in ("ts", "dur"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("pid", "tid"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "ph"):
            assert gf.dataframe[col].dtype == object

    # TODO: add tests to confirm values in dataframe


def test_ams_mpi_graphframe(ams_mpi_perfflowaspect_array):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_perfflowaspect(str(ams_mpi_perfflowaspect_array))

    assert len(gf.dataframe.groupby("name")) == 34

    for col in gf.dataframe.columns:
        if col in ("ts", "dur"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("pid", "tid"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "ph"):
            assert gf.dataframe[col].dtype == object

    # TODO: add tests to confirm values in dataframe
