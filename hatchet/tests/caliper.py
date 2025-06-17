# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import subprocess
import numpy as np

import pytest
import sys

from hatchet import GraphFrame
from hatchet.readers.caliper_reader import CaliperReader
from hatchet.util.executable import which

caliperreader_avail = True
try:
    import caliperreader
except ImportError:
    caliperreader_avail = False

annotations = [
    "main",
    "LagrangeLeapFrog",
    "LagrangeElements",
    "ApplyMaterialPropertiesForElems",
    "EvalEOSForElems",
    "CalcEnergyForElems",
    "CalcPressureForElems",
    "CalcSoundSpeedForElems",
    "UpdateVolumesForElems",
    "CalcTimeConstraintsForElems",
    "CalcCourantConstraintForElems",
    "CalcHydroConstraintForElems",
    "TimeIncrement",
    "LagrangeNodal",
    "CalcForceForNodes",
    "CalcVolumeForceForElems",
    "IntegrateStressForElems",
    "CalcHourglassControlForElems",
    "CalcFBHourglassForceForElems",
    "CalcLagrangeElements",
    "CalcKinematicsForElems",
    "CalcQForElems",
    "CalcMonotonicQGradientsForElems",
    "CalcMonotonicQRegionForElems",
]


def test_graphframe(lulesh_caliper_json):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_caliper(str(lulesh_caliper_json))

    assert len(gf.dataframe.groupby("name")) == 24

    for col in gf.dataframe.columns:
        if col in ("time (inc)", "time"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("nid", "rank"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "node"):
            assert gf.dataframe[col].dtype == object

    # TODO: add tests to confirm values in dataframe


def test_read_lulesh_json(lulesh_caliper_json):
    """Sanity check the Caliper reader by examining a known input."""
    reader = CaliperReader(str(lulesh_caliper_json))
    reader.read_json_sections()

    assert len(reader.json_data) == 192
    assert len(reader.json_cols) == 4
    assert len(reader.json_cols_mdata) == 4
    assert len(reader.json_nodes) == 24

    reader.create_graph()
    assert all(an in reader.idx_to_label.values() for an in annotations)


def test_calc_pi_json(calc_pi_caliper_json):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_caliper(str(calc_pi_caliper_json))

    assert len(gf.dataframe.groupby("name")) == 100


@pytest.mark.skipif(not which("cali-query"), reason="needs cali-query to be in path")
def test_lulesh_cali(lulesh_caliper_cali):
    """Sanity check the Caliper reader ingesting a .cali file."""
    grouping_attribute = "function"
    default_metric = "sum(sum#time.duration),inclusive_sum(sum#time.duration)"
    query = "select function,%s group by %s format json-split" % (
        default_metric,
        grouping_attribute,
    )

    gf = GraphFrame.from_caliper(str(lulesh_caliper_cali), query)

    assert len(gf.dataframe.groupby("name")) == 18


@pytest.mark.skipif(not which("cali-query"), reason="needs cali-query to be in path")
def test_lulesh_json_stream(lulesh_caliper_cali):
    """Sanity check the Caliper reader ingesting a JSON string literal."""
    cali_query = which("cali-query")
    grouping_attribute = "function"
    default_metric = "sum(sum#time.duration),inclusive_sum(sum#time.duration)"
    query = "select function,%s group by %s format json-split" % (
        default_metric,
        grouping_attribute,
    )

    cali_json = subprocess.Popen(
        [cali_query, "-q", query, lulesh_caliper_cali], stdout=subprocess.PIPE
    )

    gf = GraphFrame.from_caliper(cali_json.stdout)

    assert len(gf.dataframe.groupby("name")) == 18


@pytest.mark.skipif(sys.version_info > (3, 8), reason="Temporarily allow this to fail.")
def test_filter_squash_unify_caliper_data(lulesh_caliper_json):
    """Sanity test a GraphFrame object with known data."""
    gf1 = GraphFrame.from_caliper(str(lulesh_caliper_json))
    gf2 = GraphFrame.from_caliper(str(lulesh_caliper_json))

    assert gf1.graph is not gf2.graph

    gf1_index_names = gf1.dataframe.index.names
    gf2_index_names = gf2.dataframe.index.names

    gf1.dataframe.reset_index(inplace=True)
    gf2.dataframe.reset_index(inplace=True)

    # indexes are the same since we are reading in the same dataset
    assert all(gf1.dataframe["node"] == gf2.dataframe["node"])

    gf1.dataframe.set_index(gf1_index_names, inplace=True)
    gf2.dataframe.set_index(gf2_index_names, inplace=True)

    squash_gf1 = gf1.filter(lambda x: x["name"].startswith("Calc"))
    squash_gf2 = gf2.filter(lambda x: x["name"].startswith("Calc"))

    squash_gf1.unify(squash_gf2)

    assert squash_gf1.graph is squash_gf2.graph

    squash_gf1.dataframe.reset_index(inplace=True)
    squash_gf2.dataframe.reset_index(inplace=True)

    # Indexes should still be the same after unify. Sort indexes before comparing.
    assert all(squash_gf1.dataframe["node"] == squash_gf2.dataframe["node"])

    squash_gf1.dataframe.set_index(gf1_index_names, inplace=True)
    squash_gf2.dataframe.set_index(gf2_index_names, inplace=True)


def test_tree(monkeypatch, lulesh_caliper_json):
    """Sanity test a GraphFrame object with known data."""
    monkeypatch.setattr("sys.stdout.isatty", (lambda: False))
    gf = GraphFrame.from_caliper(str(lulesh_caliper_json))
    output = gf.tree(metric_column="time")

    assert "121489.000 main" in output
    assert "663.000 LagrangeElements" in output
    assert "21493.000 CalcTimeConstraintsForElems" in output

    output = gf.tree(metric_column="time (inc)")

    assert "662712.000 EvalEOSForElems" in output
    assert "2895319.000 LagrangeNodal" in output


def test_graphframe_to_literal(lulesh_caliper_json):
    """Sanity test a GraphFrame object with known data."""
    gf = GraphFrame.from_caliper(str(lulesh_caliper_json))
    graph_literal = gf.to_literal()

    gf2 = GraphFrame.from_literal(graph_literal)

    assert len(gf.graph) == len(gf2.graph)


def test_graphframe_native_lulesh_from_file(lulesh_caliper_cali):
    """Sanity check the native Caliper reader by examining a known input."""

    gf = GraphFrame.from_caliperreader(str(lulesh_caliper_cali))

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()

    for col in gf.dataframe.columns:
        if col in ("time (inc)", "time"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("nid", "rank"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("name", "node"):
            assert gf.dataframe[col].dtype == object

    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str


@pytest.mark.skipif(
    not caliperreader_avail, reason="needs caliper-reader package to be loaded"
)
def test_graphframe_native_lulesh_from_caliperreader(lulesh_caliper_cali):
    """Sanity check the native Caliper reader by examining a known input."""
    r = caliperreader.CaliperReader()
    r.read(lulesh_caliper_cali)

    gf = GraphFrame.from_caliperreader(r)

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.caliper.version"]) == str

    for col in gf.dataframe.columns:
        if col in ("time (inc)", "time"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("nid", "rank"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("name", "node"):
            assert gf.dataframe[col].dtype == object


def test_graphframe_native_lulesh_from_file_node_order(caliper_ordered_cali):
    """Check the order of output from the native Caliper reader by examining a known input with node order column."""

    gf = GraphFrame.from_caliperreader(str(caliper_ordered_cali))

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "lulesh.cycle",
        "TimeIncrement",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
    ]

    expected_data_order = [
        1.250952,
        1.229935,
        0.000085,
        1.229702,
        0.604766,
        0.566399,
        0.561237,
        0.161196,
        0.395344,
        0.239849,
        0.614079,
        0.175102,
        0.168127,
        0.136318,
        0.038575,
        0.299062,
        0.293046,
        0.190395,
        0.010707,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_data = gf.dataframe.iloc[i]["Total time"]
        assert node_data == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


@pytest.mark.skipif(
    not caliperreader_avail, reason="needs caliper-reader package to be loaded"
)
def test_graphframe_native_lulesh_from_caliperreader_node_order(caliper_ordered_cali):
    """Check the order of output from the native Caliper reader by examining a known input with node order column."""
    r = caliperreader.CaliperReader()
    r.read(caliper_ordered_cali)

    gf = GraphFrame.from_caliperreader(r)

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "lulesh.cycle",
        "TimeIncrement",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
    ]

    expected_data_order = [
        1.250952,
        1.229935,
        0.000085,
        1.229702,
        0.604766,
        0.566399,
        0.561237,
        0.161196,
        0.395344,
        0.239849,
        0.614079,
        0.175102,
        0.168127,
        0.136318,
        0.038575,
        0.299062,
        0.293046,
        0.190395,
        0.010707,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_data = gf.dataframe.iloc[i]["Total time"]
        assert node_data == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


def test_graphframe_lulesh_from_json_node_order(caliper_ordered_json):
    """Check the order of output from the Caliper reader by examining a known json with node order column."""

    gf = GraphFrame.from_caliper(str(caliper_ordered_json))

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "lulesh.cycle",
        "TimeIncrement",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
    ]

    # check the total time metric to make sure the values are synced with the correct node
    expected_data_order = [
        0.018887,
        0.000154,
        0.000100,
        0.000159,
        0.038220,
        0.005107,
        0.004684,
        0.161500,
        0.163350,
        0.239820,
        0.003603,
        0.007004,
        0.168298,
        0.097482,
        0.038570,
        0.006099,
        0.102499,
        0.190896,
        0.010730,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_time = gf.dataframe.iloc[i]["time"]
        assert node_time == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


def test_graphframe_native_lulesh_from_duplicate_node_order(caliper_ordered_dup):
    """Check the order of output from the native Caliper reader by examining a known input with node order column."""

    gf = GraphFrame.from_caliperreader(str(caliper_ordered_dup))

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "lulesh.cycle",
        "TimeIncrement",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
    ]

    expected_data_order = [
        1.250952,
        1.229935,
        0.000085,
        1.229702,
        0.604766,
        0.566399,
        0.561237,
        0.161196,
        0.395344,
        0.239849,
        0.614079,
        0.175102,
        0.168127,
        0.136318,
        0.038575,
        0.299062,
        0.293046,
        0.190395,
        0.010707,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_data = gf.dataframe.iloc[i]["Total time"]
        assert node_data == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


def test_graphframe_lulesh_from_duplicate_json_node_order(caliper_ordered_json_dup):
    """Check the order of output from the Caliper reader by examining a known json with node order column."""

    gf = GraphFrame.from_caliper(str(caliper_ordered_json_dup))

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "lulesh.cycle",
        "TimeIncrement",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
    ]

    # check the total time metric to make sure the values are synced with the correct node
    expected_data_order = [
        0.018887,
        0.000154,
        0.000100,
        0.000159,
        0.038220,
        0.005107,
        0.004684,
        0.161500,
        0.163350,
        0.239820,
        0.003603,
        0.007004,
        0.168298,
        0.097482,
        0.038570,
        0.006099,
        0.102499,
        0.190896,
        0.010730,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_time = gf.dataframe.iloc[i]["time"]
        assert node_time == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


def test_graphframe_native_lulesh_from_file_node_order_mpi(caliper_ordered_cali_mpi):
    """Check the order of output from the native Caliper reader by examining a known input with node order column."""

    gf = GraphFrame.from_caliperreader(str(caliper_ordered_cali_mpi))

    assert len(gf.dataframe.groupby("name")) == 26
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "MPI_Barrier",
        "lulesh.cycle",
        "TimeIncrement",
        "MPI_Allreduce",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
        "MPI_Reduce",
        "MPI_Finalize",
        "MPI_Initialized",
        "MPI_Finalized",
        "MPI_Comm_dup",
    ]

    expected_data_order = [
        1.264876,
        0.000025,
        1.245757,
        0.000170,
        0.000087,
        1.245438,
        0.607194,
        0.568202,
        0.563011,
        0.161496,
        0.396797,
        0.240649,
        0.627072,
        0.175473,
        0.168321,
        0.136137,
        0.039200,
        0.311724,
        0.305564,
        0.199211,
        0.011015,
        0.000029,
        0.000024,
        0.000007,
        0.000005,
        0.000017,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_data = gf.dataframe.iloc[i]["Total time"]
        assert node_data == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


@pytest.mark.skipif(
    not caliperreader_avail, reason="needs caliper-reader package to be loaded"
)
def test_graphframe_native_lulesh_from_caliperreader_node_order_mpi(
    caliper_ordered_cali_mpi,
):
    """Check the order of output from the native Caliper reader by examining a known input with node order column."""
    r = caliperreader.CaliperReader()
    r.read(caliper_ordered_cali_mpi)

    gf = GraphFrame.from_caliperreader(r)

    assert len(gf.dataframe.groupby("name")) == 26
    assert "cali.caliper.version" in gf.metadata.keys()
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert "Node order" not in gf.dataframe.columns

    expected_order = [
        "main",
        "MPI_Barrier",
        "lulesh.cycle",
        "TimeIncrement",
        "MPI_Allreduce",
        "LagrangeLeapFrog",
        "LagrangeNodal",
        "CalcForceForNodes",
        "CalcVolumeForceForElems",
        "IntegrateStressForElems",
        "CalcHourglassControlForElems",
        "CalcFBHourglassForceForElems",
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
        "MPI_Reduce",
        "MPI_Finalize",
        "MPI_Initialized",
        "MPI_Finalized",
        "MPI_Comm_dup",
    ]

    # check the total time metric to make sure the values are synced with the correct node
    expected_data_order = [
        1.264876,
        0.000025,
        1.245757,
        0.000170,
        0.000087,
        1.245438,
        0.607194,
        0.568202,
        0.563011,
        0.161496,
        0.396797,
        0.240649,
        0.627072,
        0.175473,
        0.168321,
        0.136137,
        0.039200,
        0.311724,
        0.305564,
        0.199211,
        0.011015,
        0.000029,
        0.000024,
        0.000007,
        0.000005,
        0.000017,
    ]

    for i in range(0, gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_data = gf.dataframe.iloc[i]["Total time"]
        assert node_data == expected_data_order[i]

    # check the tree ordering is correct as well
    gf.dataframe["hnid"] = [
        node._hatchet_nid for node in gf.graph.node_order_traverse()
    ]
    output = gf.tree(metric_column="hnid", render_header=False, precision=3)
    for i in gf.dataframe["hnid"].tolist():
        location = output.find(str(i) + ".000")
        assert location != -1
        output = output[location:]


def test_graphframe_squash_file_node_order(caliper_ordered_cali):
    """Check the order of output from the native Caliper reader by examining a known input with node order column."""

    gf = GraphFrame.from_caliperreader(str(caliper_ordered_cali))

    assert len(gf.dataframe.groupby("name")) == 19
    assert "Node order" not in gf.dataframe.columns

    filtered_gf = gf.filter(lambda x: x["nid"] > 10)
    assert len(filtered_gf.dataframe.groupby("name")) == 9

    expected_order = [
        "LagrangeElements",
        "CalcLagrangeElements",
        "CalcKinematicsForElems",
        "CalcQForElems",
        "CalcMonotonicQForElems",
        "ApplyMaterialPropertiesForElems",
        "EvalEOSForElems",
        "CalcEnergyForElems",
        "CalcTimeConstraintsForElems",
    ]

    expected_data_order = [
        0.614079,
        0.175102,
        0.168127,
        0.136318,
        0.038575,
        0.299062,
        0.293046,
        0.190395,
        0.010707,
    ]

    for i in range(0, filtered_gf.dataframe.shape[0]):
        # check if the rows are in the expected order
        node_name = filtered_gf.dataframe.iloc[i]["name"]
        assert node_name == expected_order[i]
        node_data = filtered_gf.dataframe.iloc[i]["Total time"]
        assert node_data == expected_data_order[i]

    # check the tree ordering is correct as well
    output = filtered_gf.tree(metric_column="nid")
    for i in range(10, 19):
        location = output.find(str(i))
        assert location != 0
        output = output[location:]


def test_inclusive_time_calculation(lulesh_caliper_json):
    """Validate update_inclusive_columns() on known dataset containing per-rank data."""
    gf = GraphFrame.from_caliper(str(lulesh_caliper_json))

    # save original time (inc) column for correctness check
    gf.dataframe["orig_inc_time"] = gf.dataframe["time (inc)"]

    # remove original time (inc) column since it will be generated by update_inclusive_columns()
    del gf.dataframe["time (inc)"]

    gf.update_inclusive_columns()
    assert all(
        gf.dataframe["time (inc)"].values == gf.dataframe["orig_inc_time"].values
    )


def test_sw4_cuda_from_caliperreader(sw4_caliper_cuda_activity_profile_cali):
    gf = GraphFrame.from_caliperreader(sw4_caliper_cuda_activity_profile_cali)

    assert len(gf.graph) == 549
    assert all(
        metric in gf.dataframe.columns for metric in gf.exc_metrics + gf.inc_metrics
    )

    for col in gf.dataframe.columns:
        if col in ("#scale#cupti.activity.duration", "#scale#sum#cupti.host.duration"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in "rank":
            assert gf.dataframe[col].dtype == np.int64
        elif col in "name":
            assert gf.dataframe[col].dtype == object

    for col in gf.exc_metrics + gf.inc_metrics:
        assert col in gf.dataframe.columns

    assert type(gf.metadata["mpi.world.size"]) == int
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert type(gf.metadata["cali.channel"]) == str


def test_sw4_cuda_summary_from_caliperreader(
    sw4_caliper_cuda_activity_profile_summary_cali,
):
    gf = GraphFrame.from_caliperreader(sw4_caliper_cuda_activity_profile_summary_cali)

    assert len(gf.graph) == 393
    assert all(
        metric in gf.dataframe.columns for metric in gf.exc_metrics + gf.inc_metrics
    )

    for col in gf.exc_metrics + gf.inc_metrics:
        assert col in gf.dataframe.columns

    assert type(gf.metadata["mpi.world.size"]) == int
    assert type(gf.metadata["cali.caliper.version"]) == str
    assert type(gf.metadata["cali.channel"]) == str


def test_graphframe_timeseries_lulesh_from_file(caliper_timeseries_cali):
    """Sanity check the timeseries Caliper reader by examining a known input."""

    gf_list = GraphFrame.from_timeseries(str(caliper_timeseries_cali))

    assert (type(gf_list)) == list
    gf = gf_list[0]
    gf2 = gf_list[2]

    assert len(gf.dataframe.groupby("name")) == 19
    assert "cali.caliper.version" in gf.metadata.keys()

    for col in gf.dataframe.columns:
        if col in ("time (inc)", "time"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("nid", "rank"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("name", "node"):
            assert gf.dataframe[col].dtype == object

    assert type(gf.metadata["cali.channel"]) == str
    assert type(gf.metadata["cali.caliper.version"]) == str

    # check for the expected timeseries and memory allocation columns
    timeseries_cols = [
        "timeseries.starttime",
        "timeseries.duration",
        "loop.start_iteration",
        "loop.iterations",
        "alloc.region.highwatermark",
    ]
    for tcol in timeseries_cols:
        assert tcol in gf.dataframe.columns

    # verify some values are as expected
    assert gf.dataframe["alloc.region.highwatermark"].iloc[0] == 25824351.0
    assert gf.dataframe["alloc.region.highwatermark"].iloc[1] == 63732320.0
    assert np.isnan(gf2.dataframe["loop.start_iteration"].iloc[0])
    assert np.isnan(gf2.dataframe["alloc.region.highwatermark"].iloc[0])
