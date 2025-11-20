# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from hatchet import GraphFrame
from hatchet.node import Node


def test_import_entire_db(data_dir: str) -> None:
    graphframe = GraphFrame.from_hpctoolkit_latest(
        f"{data_dir}/hpctoolkit-gamess",
        metric_names=["time", "gpuop", "gker", "gxcopy", "gxcopy:count"],
        label_function_nodes=False,
    )

    assert len(graphframe.graph.roots) == 1
    assert graphframe.graph.roots[0]._hatchet_nid == 1195
    assert graphframe.graph.roots[0]._depth == 0
    assert graphframe.graph.roots[0].frame["name"] == "entry"
    assert graphframe.graph.roots[0].frame["type"] == "entry"

    assert len(graphframe.dataframe) == 11292
    assert "name" in graphframe.dataframe.columns
    assert "time (inc)" in graphframe.dataframe.columns
    assert "time" in graphframe.dataframe.columns
    assert "gpuop (inc)" in graphframe.dataframe.columns
    assert "gker (inc)" in graphframe.dataframe.columns
    assert "gxcopy (inc)" in graphframe.dataframe.columns
    assert "gxcopy:count (inc)" in graphframe.dataframe.columns

    measurements = graphframe.dataframe.loc[Node(None, hnid=1195)]
    assert measurements["name"] == "entry"
    assert round(measurements["time (inc)"], 2) == 1608.49
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    measurements = graphframe.dataframe.loc[Node(None, hnid=1197)]
    assert measurements["name"] == "gamess_"
    assert round(measurements["time (inc)"], 2) == 1608.49
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    measurements = graphframe.dataframe.loc[Node(None, hnid=1004)]
    assert measurements["name"] == "loop [libsci_cray.so.5.0]:0"
    assert round(measurements["time (inc)"], 2) == 0.08
    assert round(measurements["time"], 2) == 0.08

    measurements = graphframe.dataframe.loc[Node(None, hnid=1003)]
    assert measurements["name"] == "line [libsci_cray.so.5.0]:0"
    assert round(measurements["time (inc)"], 2) == 0.08
    assert round(measurements["time"], 2) == 0.08


def test_filter_by_max_depth(data_dir: str) -> None:
    graphframe = GraphFrame.from_hpctoolkit_latest(
        f"{data_dir}/hpctoolkit-gamess",
        max_depth=10,
        metric_names=["time", "gpuop", "gker", "gxcopy", "gxcopy:count"],
        label_function_nodes=False,
    )

    assert len(graphframe.graph.roots) == 1
    assert graphframe.graph.roots[0]._hatchet_nid == 1195
    assert graphframe.graph.roots[0]._depth == 0
    assert graphframe.graph.roots[0].frame["name"] == "entry"
    assert graphframe.graph.roots[0].frame["type"] == "entry"

    assert len(graphframe.dataframe) == 133
    assert "name" in graphframe.dataframe.columns
    assert "time (inc)" in graphframe.dataframe.columns
    assert "time" in graphframe.dataframe.columns
    assert "gpuop (inc)" in graphframe.dataframe.columns
    assert "gker (inc)" in graphframe.dataframe.columns
    assert "gxcopy (inc)" in graphframe.dataframe.columns
    assert "gxcopy:count (inc)" in graphframe.dataframe.columns

    measurements = graphframe.dataframe.loc[Node(None, hnid=1195)]
    assert measurements["name"] == "entry"
    assert round(measurements["time (inc)"], 2) == 1608.49
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    measurements = graphframe.dataframe.loc[Node(None, hnid=1197)]
    assert measurements["name"] == "gamess_"
    assert round(measurements["time (inc)"], 2) == 1608.49
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    measurements = graphframe.dataframe.loc[Node(None, hnid=9846)]
    assert measurements["name"] == "wfn_"
    assert round(measurements["time (inc)"], 2) == 786.09
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    measurements = graphframe.dataframe.loc[Node(None, hnid=9845)]
    assert measurements["name"] == "loop [gamess.00.x]:0"
    assert round(measurements["time (inc)"], 2) == 786.09
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    for node in graphframe.graph.traverse():
        assert node._depth <= 10


def test_filter_by_min_percentage_of_application_time(data_dir: str) -> None:
    graphframe = GraphFrame.from_hpctoolkit_latest(
        f"{data_dir}/hpctoolkit-gamess",
        min_percentage_of_application_time=1,
        metric_names=["time", "gpuop", "gker", "gxcopy", "gxcopy:count"],
        label_function_nodes=False,
    )

    assert len(graphframe.graph.roots) == 1
    assert graphframe.graph.roots[0]._hatchet_nid == 1195
    assert graphframe.graph.roots[0]._depth == 0
    assert graphframe.graph.roots[0].frame["name"] == "entry"
    assert graphframe.graph.roots[0].frame["type"] == "entry"

    assert len(graphframe.dataframe) == 164
    assert "name" in graphframe.dataframe.columns
    assert "time (inc)" in graphframe.dataframe.columns
    assert "time" in graphframe.dataframe.columns
    assert "gpuop (inc)" in graphframe.dataframe.columns
    assert "gker (inc)" in graphframe.dataframe.columns
    assert "gxcopy (inc)" in graphframe.dataframe.columns
    assert "gxcopy:count (inc)" in graphframe.dataframe.columns

    measurements = graphframe.dataframe.loc[Node(None, hnid=1195)]
    assert measurements["name"] == "entry"
    assert round(measurements["time (inc)"], 2) == 1608.49
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688
    application_time = measurements["time (inc)"]

    measurements = graphframe.dataframe.loc[Node(None, hnid=1197)]
    assert measurements["name"] == "gamess_"
    assert round(measurements["time (inc)"], 2) == 1608.49
    assert round(measurements["gpuop (inc)"], 2) == 608.09
    assert round(measurements["gker (inc)"], 2) == 608.00
    assert round(measurements["gxcopy (inc)"], 2) == 0.09
    assert measurements["gxcopy:count (inc)"] == 9688

    measurements = graphframe.dataframe.loc[Node(None, hnid=2856)]
    assert measurements["name"] == "__GI___sched_yield"
    assert round(measurements["time (inc)"], 3) == 159.238
    assert round(measurements["time"], 3) == 159.238

    measurements = graphframe.dataframe.loc[Node(None, hnid=251)]
    assert measurements["name"] == "line [libc-2.31.so]:0"
    assert round(measurements["time (inc)"], 3) == 159.238
    assert round(measurements["time"], 3) == 159.238

    for node in graphframe.graph.traverse():
        node_time = graphframe.dataframe.loc[node]["time (inc)"]
        assert node_time / application_time >= 0.01
