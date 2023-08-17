# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np

from hatchet import GraphFrame

import pytest

timemory_avail = True
try:
    import timemory
except ImportError:
    timemory_avail = False


@pytest.mark.skipif(not timemory_avail, reason="timemory package not available")
def test_graphframe(timemory_json_data):
    """Sanity test a GraphFrame object with known data."""
    from timemory.component import WallClock

    wc_s = WallClock.id()  # string identifier
    wc_v = WallClock.index()  # enumeration id
    gf = GraphFrame.from_timemory(timemory_json_data, [wc_s])

    assert len(gf.dataframe) == timemory.size([wc_v])[wc_v]

    for col in gf.dataframe.columns:
        if col in ("sum.wall_clock.inc", "sum.wall_clock"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("nid", "rank"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "node"):
            assert gf.dataframe[col].dtype == object


@pytest.mark.skipif(not timemory_avail, reason="timemory package not available")
def test_tree(monkeypatch, timemory_json_data):
    """Sanity test a GraphFrame object with known data."""
    monkeypatch.setattr("sys.stdout.isatty", (lambda: False))
    gf = GraphFrame.from_timemory(timemory_json_data)

    output = gf.tree(metric_column="sum.wall_clock")
    print(output)


@pytest.mark.skipif(not timemory_avail, reason="timemory package not available")
def test_graphframe_to_literal(timemory_json_data):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_timemory(timemory_json_data)
    graph_literal = gf.to_literal()

    assert len(graph_literal) == len(gf.graph.roots)


@pytest.mark.skipif(not timemory_avail, reason="timemory package not available")
def test_default_metric(timemory_json_data):
    """Validation test for GraphFrame object using default metric field"""
    gf = GraphFrame.from_timemory(timemory_json_data)

    for func in ["tree", "to_dot", "to_flamegraph"]:
        lhs = "{}".format(getattr(gf, func)(gf.default_metric))
        rhs = "{}".format(getattr(gf, func)())
        assert lhs == rhs
