# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import pandas as pd

import hatchet as ht
from hatchet.util.boxplot import BoxPlot

bp_columns = [
    "name",
    "q",
    "ocat",
    "ometric",
    "min",
    "max",
    "mean",
    "var",
    "imb",
    "kurt",
    "skew",
]


def test_gf_format(calc_pi_hpct_db):
    gf = ht.GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    bp = BoxPlot(multi_index_gf=gf)

    metrics = gf.inc_metrics + gf.exc_metrics

    # Check if the format of target is correct.
    assert all(metric in list(bp.gf.keys()) for metric in metrics)
    assert all(isinstance(bp.gf[metric], ht.GraphFrame) for metric in metrics)
    assert all(isinstance(bp.gf[metric].dataframe, pd.DataFrame) for metric in metrics)
    assert all(isinstance(bp.gf[metric].graph, ht.graph.Graph) for metric in metrics)

    # Check if the required columns are present.
    columns = [
        "name",
        "q",
        "ocat",
        "ometric",
        "min",
        "max",
        "mean",
        "var",
        "imb",
        "kurt",
        "skew",
    ]
    assert all(
        bp.gf[metric].dataframe.columns.tolist().sort() == columns.sort()
        for metric in metrics
    )

    assert all(
        len(list(bp.gf[metric].dataframe.index.names)) == 1 for metric in metrics
    )
    assert all(
        list(bp.gf[metric].dataframe.index.names) == ["node"] for metric in metrics
    )


def test_output_dtypes(calc_pi_hpct_db):
    gf = ht.GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    metrics = ["time"]
    bp = BoxPlot(multi_index_gf=gf, drop_index_levels=["rank"], metrics=metrics)

    object_dtype = ["name", "nid", "q"]
    float_dtype = ["min", "max", "mean", "var", "imb", "kurt", "skew"]

    assert all(bp.gf["time"].dataframe.dtypes[col] == "object" for col in object_dtype)
    assert all(bp.gf["time"].dataframe.dtypes[col] == "float64" for col in float_dtype)


def test_callsite_count(calc_pi_hpct_db):
    gf = ht.GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    metrics = ["time"]
    bp = BoxPlot(multi_index_gf=gf, drop_index_levels=["rank"], metrics=metrics)

    assert len(bp.gf["time"].graph) == len(
        bp.gf["time"].dataframe.index.values.tolist()
    )


def test_multiple_metrics(calc_pi_hpct_db):
    gf = ht.GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    metrics = ["time", "time (inc)"]
    bp = BoxPlot(multi_index_gf=gf, drop_index_levels=["rank"], metrics=metrics)

    assert all(metric in bp.gf for metric in metrics)


def test_to_json(calc_pi_hpct_db):
    gf = ht.GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    bp = BoxPlot(multi_index_gf=gf, drop_index_levels=["rank"], metrics=["time"])
    json = bp.to_json()
    assert all((nid in json.keys()) for nid in gf.dataframe["nid"].unique().tolist())
