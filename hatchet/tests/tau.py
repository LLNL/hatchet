# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np

from hatchet import GraphFrame


def test_graphframe(tau_profile_dir):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_tau(str(tau_profile_dir))

    for col in gf.dataframe.columns:
        if col in ("time (inc)", "time"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("line"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "node"):
            assert gf.dataframe[col].dtype == object

    # TODO: add tests to confirm values in dataframe


def test_tree(monkeypatch, tau_profile_dir):
    """Sanity test a GraphFrame object with known data."""
    monkeypatch.setattr("sys.stdout.isatty", (lambda: False))
    gf = GraphFrame.from_tau(str(tau_profile_dir))

    # check the tree for rank 0
    output = gf.tree(metric_column="time", rank=0)

    assert "449.000 .TAU application" in output
    assert "4458.000 MPI_Finalize()" in output
    assert "218.000 MPI_Bcast()" in output

    # check the tree for rank 1
    output = gf.tree(metric_column="time", rank=1)

    assert "419.000 .TAU application" in output
    assert "4894.000 MPI_Finalize()" in output
    assert "333.000 MPI_Bcast()" in output


def test_children(tau_profile_dir):
    gf = GraphFrame.from_tau(str(tau_profile_dir))
    root = gf.graph.roots
    root_children = [
        "MPI_Init()",
        "MPI_Comm_size()",
        "MPI_Comm_rank()",
        "MPI_Get_processor_name()",
        "MPI_Bcast()",
        "MPI_Reduce()",
        "MPI_Finalize()",
    ]

    # check if only one root node is created
    assert len(root) == 1

    # check if root has right children #TODO: can be improved
    for child in root[0].children:
        assert child.frame["name"] in root_children


def test_graphframe_to_literal(tau_profile_dir):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_tau(str(tau_profile_dir))
    graph_literal = gf.to_literal()

    gf_literal = GraphFrame.from_literal(graph_literal)

    assert len(gf.graph) == len(gf_literal.graph)
