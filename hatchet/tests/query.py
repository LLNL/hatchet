# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import re

import numpy as np
import pytest

from hatchet import GraphFrame
from hatchet.node import traversal_order
from hatchet.query import (
    CompoundQuery,
    ConjunctionQuery,
    DisjunctionQuery,
    ExclusiveDisjunctionQuery,
    InvalidQueryFilter,
    InvalidQueryPath,
    NegationQuery,
    ObjectQuery,
    Query,
    QueryEngine,
    StringQuery,
    parse_string_dialect,
)
from hatchet.query.errors import MultiIndexModeMismatch


def test_construct_object_dialect():
    mock_node_mpi = {"name": "MPI_Bcast"}
    mock_node_ibv = {"name": "ibv_reg_mr"}
    mock_node_time_true = {"time (inc)": 0.1}
    mock_node_time_false = {"time (inc)": 0.001}
    path1 = [{"name": "MPI_[_a-zA-Z]*"}, "*", {"name": "ibv[_a-zA-Z]*"}]
    path2 = [{"name": "MPI_[_a-zA-Z]*"}, 2, {"name": "ibv[_a-zA-Z]*"}]
    path3 = [
        {"name": "MPI_[_a-zA-Z]*"},
        ("+", {"time (inc)": ">= 0.1"}),
        {"name": "ibv[_a-zA-Z]*"},
    ]
    path4 = [
        {"name": "MPI_[_a-zA-Z]*"},
        (3, {"time (inc)": 0.1}),
        {"name": "ibv[_a-zA-Z]*"},
    ]
    # Note: the comma's in the keys are necessary. In Python, creating a tuple
    #       from a single string results in a tuple containing every character of
    #       the string as a separate element. In other words,
    #       tuple("name") == ( "n", "a", "m", "e" ).
    #       The comma tells Python to create a tuple with a single element. In other words,
    #       ("name",) == tuple("name",) == ( "name" )
    path5 = [{("name",): "MPI_[_a-zA-Z]*"}, "*", {("name",): "ibv[_a-zA-Z]*"}]
    query1 = ObjectQuery(path1)
    query2 = ObjectQuery(path2)
    query3 = ObjectQuery(path3)
    query4 = ObjectQuery(path4)
    query5 = ObjectQuery(path5)

    assert query1.query_pattern[0][0] == "."
    assert query1.query_pattern[0][1](mock_node_mpi)
    assert not query1.query_pattern[0][1](mock_node_ibv)
    assert not query1.query_pattern[0][1](mock_node_time_true)
    assert query1.query_pattern[1][0] == "*"
    assert query1.query_pattern[1][1](mock_node_mpi)
    assert query1.query_pattern[1][1](mock_node_ibv)
    assert query1.query_pattern[1][1](mock_node_time_true)
    assert query1.query_pattern[1][1](mock_node_time_false)
    assert query1.query_pattern[2][0] == "."

    assert query2.query_pattern[0][0] == "."
    assert query2.query_pattern[1][0] == "."
    assert query2.query_pattern[1][1](mock_node_mpi)
    assert query2.query_pattern[1][1](mock_node_ibv)
    assert query2.query_pattern[1][1](mock_node_time_true)
    assert query2.query_pattern[1][1](mock_node_time_false)
    assert query2.query_pattern[2][0] == "."
    assert query2.query_pattern[2][1](mock_node_mpi)
    assert query2.query_pattern[2][1](mock_node_ibv)
    assert query2.query_pattern[2][1](mock_node_time_true)
    assert query2.query_pattern[2][1](mock_node_time_false)
    assert query2.query_pattern[3][0] == "."

    assert query3.query_pattern[0][0] == "."
    assert query3.query_pattern[1][0] == "."
    assert query3.query_pattern[2][0] == "*"
    assert not query3.query_pattern[1][1](mock_node_mpi)
    assert not query3.query_pattern[1][1](mock_node_ibv)
    assert query3.query_pattern[1][1](mock_node_time_true)
    assert not query3.query_pattern[1][1](mock_node_time_false)
    assert not query3.query_pattern[2][1](mock_node_mpi)
    assert not query3.query_pattern[2][1](mock_node_ibv)
    assert query3.query_pattern[2][1](mock_node_time_true)
    assert not query3.query_pattern[2][1](mock_node_time_false)
    assert query3.query_pattern[3][0] == "."

    assert query4.query_pattern[0][0] == "."
    assert query4.query_pattern[1][0] == "."
    assert not query4.query_pattern[1][1](mock_node_mpi)
    assert not query4.query_pattern[1][1](mock_node_ibv)
    assert query4.query_pattern[1][1](mock_node_time_true)
    assert not query4.query_pattern[1][1](mock_node_time_false)
    assert query4.query_pattern[2][0] == "."
    assert not query4.query_pattern[2][1](mock_node_mpi)
    assert not query4.query_pattern[2][1](mock_node_ibv)
    assert query4.query_pattern[2][1](mock_node_time_true)
    assert not query4.query_pattern[2][1](mock_node_time_false)
    assert query4.query_pattern[3][0] == "."
    assert not query4.query_pattern[3][1](mock_node_mpi)
    assert not query4.query_pattern[3][1](mock_node_ibv)
    assert query4.query_pattern[3][1](mock_node_time_true)
    assert not query4.query_pattern[3][1](mock_node_time_false)
    assert query4.query_pattern[4][0] == "."

    assert query5.query_pattern[0][0] == "."
    assert query5.query_pattern[0][1](mock_node_mpi)
    assert not query5.query_pattern[0][1](mock_node_ibv)
    assert not query5.query_pattern[0][1](mock_node_time_true)
    assert query5.query_pattern[1][0] == "*"
    assert query5.query_pattern[1][1](mock_node_mpi)
    assert query5.query_pattern[1][1](mock_node_ibv)
    assert query5.query_pattern[1][1](mock_node_time_true)
    assert query5.query_pattern[1][1](mock_node_time_false)
    assert query5.query_pattern[2][0] == "."

    invalid_path = [
        {"name": "MPI_[_a-zA-Z]*"},
        ({"bad": "wildcard"}, {"time (inc)": 0.1}),
        {"name": "ibv[_a-zA-Z]*"},
    ]
    with pytest.raises(InvalidQueryPath):
        _ = ObjectQuery(invalid_path)

    invalid_path = [["name", "MPI_[_a-zA-Z]*"], "*", {"name": "ibv[_a-zA-Z]*"}]
    with pytest.raises(InvalidQueryPath):
        _ = ObjectQuery(invalid_path)


def test_construct_base_query():
    mock_node_mpi = {"name": "MPI_Bcast"}
    mock_node_ibv = {"name": "ibv_reg_mr"}
    mock_node_time_true = {"time (inc)": 0.1}
    mock_node_time_false = {"time (inc)": 0.001}

    def mpi_filter(df_row):
        if "name" not in df_row:
            return False
        if re.match(r"MPI_[_a-zA-Z]*\Z", df_row["name"]) is not None:
            return True
        return False

    def ibv_filter(df_row):
        if "name" not in df_row:
            return False
        if re.match(r"ibv[_a-zA-Z]*\Z", df_row["name"]) is not None:
            return True
        return False

    def time_ge_filter(df_row):
        if "time (inc)" not in df_row:
            return False
        return df_row["time (inc)"] >= 0.1

    def time_eq_filter(df_row):
        if "time (inc)" not in df_row:
            return False
        return df_row["time (inc)"] == 0.1

    query = Query()

    query.match(predicate=mpi_filter).rel("*").rel(predicate=ibv_filter)
    assert query.query_pattern[0][0] == "."
    assert query.query_pattern[0][1](mock_node_mpi)
    assert not query.query_pattern[0][1](mock_node_ibv)
    assert not query.query_pattern[0][1](mock_node_time_true)
    assert query.query_pattern[1][0] == "*"
    assert query.query_pattern[1][1](mock_node_mpi)
    assert query.query_pattern[1][1](mock_node_ibv)
    assert query.query_pattern[1][1](mock_node_time_true)
    assert query.query_pattern[1][1](mock_node_time_false)
    assert query.query_pattern[2][0] == "."

    query.match(predicate=mpi_filter).rel(2).rel(predicate=ibv_filter)
    assert query.query_pattern[0][0] == "."
    assert query.query_pattern[1][0] == "."
    assert query.query_pattern[1][1](mock_node_mpi)
    assert query.query_pattern[1][1](mock_node_ibv)
    assert query.query_pattern[1][1](mock_node_time_true)
    assert query.query_pattern[1][1](mock_node_time_false)
    assert query.query_pattern[2][0] == "."
    assert query.query_pattern[2][1](mock_node_mpi)
    assert query.query_pattern[2][1](mock_node_ibv)
    assert query.query_pattern[2][1](mock_node_time_true)
    assert query.query_pattern[2][1](mock_node_time_false)
    assert query.query_pattern[3][0] == "."

    query.match(predicate=mpi_filter).rel("+", time_ge_filter).rel(predicate=ibv_filter)
    assert query.query_pattern[0][0] == "."
    assert query.query_pattern[1][0] == "."
    assert query.query_pattern[2][0] == "*"
    assert not query.query_pattern[1][1](mock_node_mpi)
    assert not query.query_pattern[1][1](mock_node_ibv)
    assert query.query_pattern[1][1](mock_node_time_true)
    assert not query.query_pattern[1][1](mock_node_time_false)
    assert not query.query_pattern[2][1](mock_node_mpi)
    assert not query.query_pattern[2][1](mock_node_ibv)
    assert query.query_pattern[2][1](mock_node_time_true)
    assert not query.query_pattern[2][1](mock_node_time_false)
    assert query.query_pattern[3][0] == "."

    query.match(predicate=mpi_filter).rel(3, time_eq_filter).rel(predicate=ibv_filter)
    assert query.query_pattern[0][0] == "."
    assert query.query_pattern[1][0] == "."
    assert not query.query_pattern[1][1](mock_node_mpi)
    assert not query.query_pattern[1][1](mock_node_ibv)
    assert query.query_pattern[1][1](mock_node_time_true)
    assert not query.query_pattern[1][1](mock_node_time_false)
    assert query.query_pattern[2][0] == "."
    assert not query.query_pattern[2][1](mock_node_mpi)
    assert not query.query_pattern[2][1](mock_node_ibv)
    assert query.query_pattern[2][1](mock_node_time_true)
    assert not query.query_pattern[2][1](mock_node_time_false)
    assert query.query_pattern[3][0] == "."
    assert not query.query_pattern[3][1](mock_node_mpi)
    assert not query.query_pattern[3][1](mock_node_ibv)
    assert query.query_pattern[3][1](mock_node_time_true)
    assert not query.query_pattern[3][1](mock_node_time_false)
    assert query.query_pattern[4][0] == "."

    with pytest.raises(InvalidQueryPath):
        _ = Query().rel(".", lambda row: True)


def test_node_caching(mock_graph_literal):
    path = [{"name": "fr[a-z]+"}, ("+", {"time (inc)": ">= 25.0"}), {"name": "baz"}]
    gf = GraphFrame.from_literal(mock_graph_literal)
    node = gf.graph.roots[0].children[2].children[0]

    query = ObjectQuery(path)
    engine = QueryEngine()
    engine._cache_node(node, query, gf.dataframe)

    assert 0 in engine.search_cache[node._hatchet_nid]
    assert 1 in engine.search_cache[node._hatchet_nid]
    assert 2 in engine.search_cache[node._hatchet_nid]
    assert 3 not in engine.search_cache[node._hatchet_nid]


def test_match_0_or_more_wildcard(mock_graph_literal):
    path = [
        {"name": "qux"},
        ("*", {"time (inc)": "> 10"}),
        {"name": "gr[a-z]+", "time (inc)": "<= 10"},
    ]
    gf = GraphFrame.from_literal(mock_graph_literal)
    node = gf.graph.roots[0].children[1]
    none_node = gf.graph.roots[0].children[2].children[0].children[1].children[0]

    correct_paths = [
        [
            node.children[0],
            node.children[0].children[0],
            node.children[0].children[0].children[0],
        ],
        [node.children[0], node.children[0].children[0]],
    ]

    query = ObjectQuery(path)
    engine = QueryEngine()
    matched_paths = []
    for child in sorted(node.children, key=traversal_order):
        match = engine._match_0_or_more(query, gf.dataframe, child, 1)
        if match is not None:
            matched_paths.extend(match)

    assert sorted(matched_paths, key=len) == sorted(correct_paths, key=len)
    assert engine._match_0_or_more(query, gf.dataframe, none_node, 1) is None


def test_match_1(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    path = [
        {"name": "qux"},
        ("*", {"time (inc)": "> 10"}),
        {"name": "gr[a-z]+", "time (inc)": "<= 10.0"},
    ]
    query = ObjectQuery(path)
    engine = QueryEngine()

    assert engine._match_1(query, gf.dataframe, gf.graph.roots[0].children[0], 2) == [
        [gf.graph.roots[0].children[0].children[1]]
    ]
    assert engine._match_1(query, gf.dataframe, gf.graph.roots[0], 2) is None


def test_match(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    root = gf.graph.roots[0].children[2]

    path0 = [
        {"name": "waldo"},
        "+",
        {"time (inc)": ">= 20.0"},
        "+",
        {"time (inc)": 5.0, "time": 5.0},
    ]
    match0 = [
        [
            root,
            root.children[0],
            root.children[0].children[1],
            root.children[0].children[1].children[0],
            root.children[0].children[1].children[0].children[0],
        ]
    ]
    query0 = ObjectQuery(path0)
    engine = QueryEngine()
    assert engine._match_pattern(query0, gf.dataframe, root, 0) == match0

    engine.reset_cache()

    path1 = [
        {"name": "waldo"},
        ("+", {}),
        {"time (inc)": ">= 20.0"},
        "+",
        {"time (inc)": 7.5, "time": 7.5},
    ]
    query1 = ObjectQuery(path1)
    assert engine._match_pattern(query1, gf.dataframe, root, 0) is None


def test_apply(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    path = [
        {"time (inc)": ">= 30.0"},
        (2, {"name": "[^b][a-z]+"}),
        ("*", {"name": "[^b][a-z]+"}),
        {"name": "gr[a-z]+"},
    ]
    root = gf.graph.roots[0]
    match = [
        root,
        root.children[1],
        root.children[1].children[0],
        root.children[1].children[0].children[0],
        root.children[1].children[0].children[0].children[1],
    ]
    query = ObjectQuery(path)
    engine = QueryEngine()

    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = [{"time (inc)": ">= 30.0"}, ".", {"name": "bar"}, "*"]
    match = [
        root.children[1].children[0],
        root.children[1].children[0].children[0],
        root.children[1].children[0].children[0].children[0],
        root.children[1].children[0].children[0].children[0].children[0],
        root.children[1].children[0].children[0].children[0].children[1],
    ]
    query = ObjectQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = [{"name": "foo"}, {"name": "bar"}, {"time": 5.0}]
    match = [root, root.children[0], root.children[0].children[0]]
    query = ObjectQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = [{"name": "foo"}, {"name": "qux"}, ("+", {"time (inc)": "> 15.0"})]
    match = [
        root,
        root.children[1],
        root.children[1].children[0],
        root.children[1].children[0].children[0],
        root.children[1].children[0].children[0].children[0],
    ]
    query = ObjectQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = [{"name": "this"}, ("*", {"name": "is"}), {"name": "nonsense"}]

    query = ObjectQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == []

    path = [{"name": 5}, "*", {"name": "whatever"}]
    query = ObjectQuery(path)
    with pytest.raises(InvalidQueryFilter):
        engine.apply(query, gf.graph, gf.dataframe)

    path = [{"time": "badstring"}, "*", {"name": "whatever"}]
    query = ObjectQuery(path)
    with pytest.raises(InvalidQueryFilter):
        engine.apply(query, gf.graph, gf.dataframe)

    class DummyType:
        def __init__(self):
            self.x = 5.0
            self.y = -1
            self.z = "hello"

    bad_field_test_dict = list(mock_graph_literal)
    bad_field_test_dict[0]["children"][0]["children"][0]["metrics"][
        "list"
    ] = DummyType()
    gf = GraphFrame.from_literal(bad_field_test_dict)
    path = [{"name": "foo"}, {"name": "bar"}, {"list": DummyType()}]
    query = ObjectQuery(path)
    with pytest.raises(InvalidQueryFilter):
        engine.apply(query, gf.graph, gf.dataframe)

    path = ["*", {"name": "bar"}, {"name": "grault"}, "*"]
    match = [
        [root, root.children[0], root.children[0].children[1]],
        [root.children[0], root.children[0].children[1]],
        [
            root,
            root.children[1],
            root.children[1].children[0],
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1],
            root.children[1].children[0],
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1].children[0],
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            gf.graph.roots[1],
            gf.graph.roots[1].children[0],
            gf.graph.roots[1].children[0].children[1],
        ],
        [gf.graph.roots[1].children[0], gf.graph.roots[1].children[0].children[1]],
    ]
    match = list(set().union(*match))
    query = ObjectQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = ["*", {"name": "bar"}, {"name": "grault"}, "+"]
    query = ObjectQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == []

    # Test a former edge case with the + quantifier/wildcard
    match = [
        [gf.graph.roots[0].children[0], gf.graph.roots[0].children[0].children[0]],
        [
            gf.graph.roots[0].children[1].children[0].children[0].children[0],
            gf.graph.roots[0]
            .children[1]
            .children[0]
            .children[0]
            .children[0]
            .children[0],
        ],
        [
            gf.graph.roots[1].children[0],
            gf.graph.roots[1].children[0].children[0],
        ],
        [
            gf.graph.roots[0]
            .children[2]
            .children[0]
            .children[1]
            .children[0]
            .children[0],
        ],
    ]
    match = list(set().union(*match))
    path = [("+", {"name": "ba.*"})]
    query = ObjectQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)


def test_apply_indices(calc_pi_hpct_db):
    gf = GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    main = gf.graph.roots[0].children[0]
    path = [
        {"name": "[0-9]*:?MPI_.*"},
        ("*", {"name": "^((?!MPID).)*"}),
        {"name": "[0-9]*:?MPID.*"},
    ]
    matches = [
        [
            main.children[0],
            main.children[0].children[0],
            main.children[0].children[0].children[0],
            main.children[0].children[0].children[0].children[0],
        ],
        [
            main.children[1],
            main.children[1].children[0],
            main.children[1].children[0].children[0],
        ],
    ]
    matches = list(set().union(*matches))
    query = ObjectQuery(path, multi_index_mode="all")
    engine = QueryEngine()
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)

    gf.drop_index_levels()
    assert engine.apply(query, gf.graph, gf.dataframe) == matches


def test_object_dialect_depth(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query = ObjectQuery([("*", {"depth": 1})])
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [c for r in roots for c in r.children]
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)

    query = ObjectQuery([("*", {"depth": "<= 2"})])
    matches = [
        [roots[0], roots[0].children[0], roots[0].children[0].children[0]],
        [roots[0].children[0], roots[0].children[0].children[0]],
        [roots[0].children[0].children[0]],
        [roots[0], roots[0].children[0], roots[0].children[0].children[1]],
        [roots[0].children[0], roots[0].children[0].children[1]],
        [roots[0].children[0].children[1]],
        [roots[0], roots[0].children[1], roots[0].children[1].children[0]],
        [roots[0].children[1], roots[0].children[1].children[0]],
        [roots[0].children[1].children[0]],
        [roots[0], roots[0].children[2], roots[0].children[2].children[0]],
        [roots[0].children[2], roots[0].children[2].children[0]],
        [roots[0].children[2].children[0]],
        [roots[0], roots[0].children[2], roots[0].children[2].children[1]],
        [roots[0].children[2], roots[0].children[2].children[1]],
        [roots[0].children[2].children[1]],
        [roots[1], roots[1].children[0], roots[1].children[0].children[0]],
        [roots[1].children[0], roots[1].children[0].children[0]],
        [roots[1].children[0].children[0]],
        [roots[1], roots[1].children[0], roots[1].children[0].children[1]],
        [roots[1].children[0], roots[1].children[0].children[1]],
        [roots[1].children[0].children[1]],
    ]
    matches = list(set().union(*matches))
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)

    with pytest.raises(InvalidQueryFilter):
        query = ObjectQuery([{"depth": "hello"}])
        engine.apply(query, gf.graph, gf.dataframe)


def test_object_dialect_hatchet_nid(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query = ObjectQuery([("*", {"node_id": ">= 20"})])
    engine = QueryEngine()
    root = gf.graph.roots[1]
    matches = [
        [root, root.children[0], root.children[0].children[0]],
        [root.children[0], root.children[0].children[0]],
        [root.children[0].children[0]],
        [root, root.children[0], root.children[0].children[1]],
        [root.children[0], root.children[0].children[1]],
        [root.children[0].children[1]],
    ]
    matches = list(set().union(*matches))
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)

    query = ObjectQuery([{"node_id": 0}])
    assert engine.apply(query, gf.graph, gf.dataframe) == [gf.graph.roots[0]]

    with pytest.raises(InvalidQueryFilter):
        query = ObjectQuery([{"node_id": "hello"}])
        engine.apply(query, gf.graph, gf.dataframe)


def test_object_dialect_depth_index_levels(calc_pi_hpct_db):
    gf = GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    root = gf.graph.roots[0]

    query = ObjectQuery([("*", {"depth": "<= 2"})], multi_index_mode="all")
    engine = QueryEngine()
    matches = [
        [root, root.children[0], root.children[0].children[0]],
        [root.children[0], root.children[0].children[0]],
        [root.children[0].children[0]],
        [root, root.children[0], root.children[0].children[1]],
        [root.children[0], root.children[0].children[1]],
        [root.children[0].children[1]],
    ]
    matches = list(set().union(*matches))
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)

    query = ObjectQuery([("*", {"depth": 0})], multi_index_mode="all")
    matches = [root]
    assert engine.apply(query, gf.graph, gf.dataframe) == matches

    with pytest.raises(InvalidQueryFilter):
        query = ObjectQuery([{"depth": "hello"}], multi_index_mode="all")
        engine.apply(query, gf.graph, gf.dataframe)


def test_object_dialect_node_id_index_levels(calc_pi_hpct_db):
    gf = GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    root = gf.graph.roots[0]

    query = ObjectQuery([("*", {"node_id": "<= 2"})], multi_index_mode="all")
    engine = QueryEngine()
    matches = [
        [root, root.children[0]],
        [root.children[0]],
        [root, root.children[0], root.children[0].children[0]],
        [root.children[0], root.children[0].children[0]],
        [root.children[0].children[0]],
    ]
    matches = list(set().union(*matches))
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)

    query = ObjectQuery([("*", {"node_id": 0})], multi_index_mode="all")
    matches = [root]
    assert engine.apply(query, gf.graph, gf.dataframe) == matches

    with pytest.raises(InvalidQueryFilter):
        query = ObjectQuery([{"node_id": "hello"}], multi_index_mode="all")
        engine.apply(query, gf.graph, gf.dataframe)


def test_object_dialect_multi_condition_one_attribute(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query = ObjectQuery([("*", {"time (inc)": [">= 20", "<= 60"]})])
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        [roots[0].children[0]],
        [
            roots[0].children[1],
            roots[0].children[1].children[0],
            roots[0].children[1].children[0].children[0],
            roots[0].children[1].children[0].children[0].children[0],
        ],
        [
            roots[0].children[1],
            roots[0].children[1].children[0],
            roots[0].children[1].children[0].children[0],
        ],
        [
            roots[0].children[1].children[0],
            roots[0].children[1].children[0].children[0],
            roots[0].children[1].children[0].children[0].children[0],
        ],
        [
            roots[0].children[1].children[0],
            roots[0].children[1].children[0].children[0],
        ],
        [
            roots[0].children[1].children[0].children[0],
            roots[0].children[1].children[0].children[0].children[0],
        ],
        [roots[0].children[1].children[0].children[0]],
        [roots[0].children[1].children[0].children[0].children[0]],
        [
            roots[0].children[2],
            roots[0].children[2].children[0],
            roots[0].children[2].children[0].children[1],
            roots[0].children[2].children[0].children[1].children[0],
        ],
        [roots[0].children[2], roots[0].children[2].children[0]],
        [roots[0].children[2]],
        [
            roots[0].children[2].children[0],
            roots[0].children[2].children[0].children[1],
            roots[0].children[2].children[0].children[1].children[0],
        ],
        [roots[0].children[2].children[0]],
        [
            roots[0].children[2].children[0].children[1],
            roots[0].children[2].children[0].children[1].children[0],
        ],
        [roots[0].children[2].children[0].children[1].children[0]],
        [roots[1], roots[1].children[0]],
        [roots[1].children[0]],
    ]
    matches = list(set().union(*matches))
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)


def test_obj_query_is_query():
    assert issubclass(ObjectQuery, Query)


def test_str_query_is_query():
    assert issubclass(StringQuery, Query)


def test_conj_query_is_compound_query():
    assert issubclass(ConjunctionQuery, CompoundQuery)


def test_disj_query_is_compound_query():
    assert issubclass(DisjunctionQuery, CompoundQuery)


def test_exc_disj_query_is_compound_query():
    assert issubclass(ExclusiveDisjunctionQuery, CompoundQuery)


def test_negation_query_is_compound_query():
    assert issubclass(NegationQuery, CompoundQuery)


def test_compound_query_object_dialect_construction(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 20", "<= 60"]})]
    query2 = [("*", {"time (inc)": ">= 60"})]
    q1_node = gf.graph.roots[0].children[1].children[0].children[0]
    q2_node = gf.graph.roots[0]
    compound_query = ConjunctionQuery(query1, query2)
    assert compound_query.subqueries[0].query_pattern[0][0] == "*"
    assert compound_query.subqueries[0].query_pattern[0][1](gf.dataframe.loc[q1_node])
    assert not compound_query.subqueries[0].query_pattern[0][1](
        gf.dataframe.loc[q2_node]
    )
    assert compound_query.subqueries[1].query_pattern[0][0] == "*"
    assert compound_query.subqueries[1].query_pattern[0][1](gf.dataframe.loc[q2_node])
    assert not compound_query.subqueries[1].query_pattern[0][1](
        gf.dataframe.loc[q1_node]
    )


def test_compound_query_base_query_construction(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = Query().match(
        "*", lambda x: x["time (inc)"] >= 20 and x["time (inc)"] <= 60
    )
    query2 = Query().match("*", lambda x: x["time (inc)"] >= 60)
    q1_node = gf.graph.roots[0].children[1].children[0].children[0]
    q2_node = gf.graph.roots[0]
    compound_query = ConjunctionQuery(query1, query2)
    assert compound_query.subqueries[0].query_pattern[0][0] == "*"
    assert compound_query.subqueries[0].query_pattern[0][1](gf.dataframe.loc[q1_node])
    assert not compound_query.subqueries[0].query_pattern[0][1](
        gf.dataframe.loc[q2_node]
    )
    assert compound_query.subqueries[1].query_pattern[0][0] == "*"
    assert compound_query.subqueries[1].query_pattern[0][1](gf.dataframe.loc[q2_node])
    assert not compound_query.subqueries[1].query_pattern[0][1](
        gf.dataframe.loc[q1_node]
    )


def test_compound_query_mixed_syntax_construction(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 20", "<= 60"]})]
    query2 = Query().match("*", lambda x: x["time (inc)"] >= 60)
    q1_node = gf.graph.roots[0].children[1].children[0].children[0]
    q2_node = gf.graph.roots[0]
    compound_query = ConjunctionQuery(query1, query2)
    assert compound_query.subqueries[0].query_pattern[0][0] == "*"
    assert compound_query.subqueries[0].query_pattern[0][1](gf.dataframe.loc[q1_node])
    assert not compound_query.subqueries[0].query_pattern[0][1](
        gf.dataframe.loc[q2_node]
    )
    assert compound_query.subqueries[1].query_pattern[0][0] == "*"
    assert compound_query.subqueries[1].query_pattern[0][1](gf.dataframe.loc[q2_node])
    assert not compound_query.subqueries[1].query_pattern[0][1](
        gf.dataframe.loc[q1_node]
    )


def test_conjunction_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 20", "<= 60"]})]
    query2 = [("*", {"time (inc)": ">= 60"})]
    compound_query = ConjunctionQuery(query1, query2)
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        roots[0].children[1],
        roots[0].children[1].children[0],
    ]
    assert sorted(engine.apply(compound_query, gf.graph, gf.dataframe)) == sorted(
        matches
    )


def test_disjunction_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": 5.0})]
    query2 = [("*", {"time (inc)": 10.0})]
    compound_query = DisjunctionQuery(query1, query2)
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[0].children[1],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[1],
        roots[0].children[1].children[0].children[0].children[1],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
        roots[1].children[0].children[1],
    ]
    assert sorted(engine.apply(compound_query, gf.graph, gf.dataframe)) == sorted(
        matches
    )


def test_exc_disjunction_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 5.0", "<= 10.0"]})]
    query2 = [("*", {"time (inc)": 10.0})]
    compound_query = ExclusiveDisjunctionQuery(query1, query2)
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
    ]
    assert sorted(engine.apply(compound_query, gf.graph, gf.dataframe)) == sorted(
        matches
    )


def test_construct_string_dialect():
    mock_node_mpi = {"name": "MPI_Bcast"}
    mock_node_ibv = {"name": "ibv_reg_mr"}
    mock_node_time_true = {"time (inc)": 0.1}
    mock_node_time_false = {"time (inc)": 0.001}
    path1 = """MATCH (p)->("*")->(q)
    WHERE p."name" STARTS WITH "MPI_" AND q."name" STARTS WITH "ibv"
    """
    path2 = """MATCH (p)->(2)->(q)
    WHERE p."name" STARTS WITH "MPI_" AND q."name" STARTS WITH "ibv"
    """
    path3 = """MATCH (p)->("+", a)->(q)
    WHERE p."name" STARTS WITH "MPI" AND a."time (inc)" >= 0.1 AND q."name" STARTS WITH "ibv"
    """
    path4 = """MATCH (p)->(3, a)->(q)
    WHERE p."name" STARTS WITH "MPI" AND a."time (inc)" = 0.1 AND q."name" STARTS WITH "ibv"
    """
    path5 = """MATCH (p)->("*")->(q)
    WHERE p.("name") STARTS WITH "MPI_" AND q.("name") STARTS WITH "ibv"
    """
    query1 = StringQuery(path1)
    query2 = StringQuery(path2)
    query3 = StringQuery(path3)
    query4 = StringQuery(path4)
    query5 = StringQuery(path5)

    assert query1.query_pattern[0][0] == "."
    assert query1.query_pattern[0][1](mock_node_mpi)
    assert not query1.query_pattern[0][1](mock_node_ibv)
    assert not query1.query_pattern[0][1](mock_node_time_true)
    assert query1.query_pattern[1][0] == "*"
    assert query1.query_pattern[1][1](mock_node_mpi)
    assert query1.query_pattern[1][1](mock_node_ibv)
    assert query1.query_pattern[1][1](mock_node_time_true)
    assert query1.query_pattern[1][1](mock_node_time_false)
    assert query1.query_pattern[2][0] == "."

    assert query2.query_pattern[0][0] == "."
    assert query2.query_pattern[1][0] == "."
    assert query2.query_pattern[1][1](mock_node_mpi)
    assert query2.query_pattern[1][1](mock_node_ibv)
    assert query2.query_pattern[1][1](mock_node_time_true)
    assert query2.query_pattern[1][1](mock_node_time_false)
    assert query2.query_pattern[2][0] == "."
    assert query2.query_pattern[2][1](mock_node_mpi)
    assert query2.query_pattern[2][1](mock_node_ibv)
    assert query2.query_pattern[2][1](mock_node_time_true)
    assert query2.query_pattern[2][1](mock_node_time_false)
    assert query2.query_pattern[3][0] == "."

    assert query3.query_pattern[0][0] == "."
    assert query3.query_pattern[1][0] == "."
    assert query3.query_pattern[2][0] == "*"
    assert not query3.query_pattern[1][1](mock_node_mpi)
    assert not query3.query_pattern[1][1](mock_node_ibv)
    assert query3.query_pattern[1][1](mock_node_time_true)
    assert not query3.query_pattern[1][1](mock_node_time_false)
    assert not query3.query_pattern[2][1](mock_node_mpi)
    assert not query3.query_pattern[2][1](mock_node_ibv)
    assert query3.query_pattern[2][1](mock_node_time_true)
    assert not query3.query_pattern[2][1](mock_node_time_false)
    assert query3.query_pattern[3][0] == "."

    assert query4.query_pattern[0][0] == "."
    assert query4.query_pattern[1][0] == "."
    assert not query4.query_pattern[1][1](mock_node_mpi)
    assert not query4.query_pattern[1][1](mock_node_ibv)
    assert query4.query_pattern[1][1](mock_node_time_true)
    assert not query4.query_pattern[1][1](mock_node_time_false)
    assert query4.query_pattern[2][0] == "."
    assert not query4.query_pattern[2][1](mock_node_mpi)
    assert not query4.query_pattern[2][1](mock_node_ibv)
    assert query4.query_pattern[2][1](mock_node_time_true)
    assert not query4.query_pattern[2][1](mock_node_time_false)
    assert query4.query_pattern[3][0] == "."
    assert not query4.query_pattern[3][1](mock_node_mpi)
    assert not query4.query_pattern[3][1](mock_node_ibv)
    assert query4.query_pattern[3][1](mock_node_time_true)
    assert not query4.query_pattern[3][1](mock_node_time_false)
    assert query4.query_pattern[4][0] == "."

    assert query5.query_pattern[0][0] == "."
    assert query5.query_pattern[0][1](mock_node_mpi)
    assert not query5.query_pattern[0][1](mock_node_ibv)
    assert not query5.query_pattern[0][1](mock_node_time_true)
    assert query5.query_pattern[1][0] == "*"
    assert query5.query_pattern[1][1](mock_node_mpi)
    assert query5.query_pattern[1][1](mock_node_ibv)
    assert query5.query_pattern[1][1](mock_node_time_true)
    assert query5.query_pattern[1][1](mock_node_time_false)
    assert query5.query_pattern[2][0] == "."

    invalid_path = """MATCH (p)->({"bad": "wildcard"}, a)->(q)
    WHERE p."name" STARTS WITH "MPI" AND a."time (inc)" = 0.1 AND
    q."name" STARTS WITH "ibv"
    """
    with pytest.raises(InvalidQueryPath):
        _ = StringQuery(invalid_path)


def test_apply_string_dialect(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    path = """MATCH (p)->(2, q)->("*", r)->(s)
    WHERE p."time (inc)" >= 30.0 AND NOT q."name" STARTS WITH "b"
    AND r."name" =~ "[^b][a-z]+" AND s."name" STARTS WITH "gr"
    """
    root = gf.graph.roots[0]
    match = [
        root,
        root.children[1],
        root.children[1].children[0],
        root.children[1].children[0].children[0],
        root.children[1].children[0].children[0].children[1],
    ]
    query = StringQuery(path)
    engine = QueryEngine()

    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = """MATCH (p)->(".")->(q)->("*")
    WHERE p."time (inc)" >= 30.0 AND q."name" = "bar"
    """
    match = [
        root.children[1].children[0],
        root.children[1].children[0].children[0],
        root.children[1].children[0].children[0].children[0],
        root.children[1].children[0].children[0].children[0].children[0],
        root.children[1].children[0].children[0].children[0].children[1],
    ]
    query = StringQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = """MATCH (p)->(q)->(r)
    WHERE p."name" = "foo" AND q."name" = "bar" AND r."time" = 5.0
    """
    match = [root, root.children[0], root.children[0].children[0]]
    query = StringQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = """MATCH (p)->(q)->("+", r)
    WHERE p."name" = "foo" AND q."name" = "qux" AND r."time (inc)" > 15.0
    """
    match = [
        root,
        root.children[1],
        root.children[1].children[0],
        root.children[1].children[0].children[0],
        root.children[1].children[0].children[0].children[0],
    ]
    query = StringQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = """MATCH (p)->(q)
    WHERE p."time (inc)" > 100 OR p."time (inc)" <= 30 AND q."time (inc)" = 20
    """
    roots = gf.graph.roots
    match = [
        roots[0],
        roots[0].children[0],
        roots[1],
        roots[1].children[0],
    ]
    query = StringQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = """MATCH (p)->("*", q)->(r)
    WHERE p."name" = "this" AND q."name" = "is" AND r."name" = "nonsense"
    """

    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == []

    path = """MATCH (p)->("*")->(q)
    WHERE p."name" = 5 AND q."name" = "whatever"
    """
    with pytest.raises(InvalidQueryFilter):
        query = StringQuery(path)
        engine.apply(query, gf.graph, gf.dataframe)

    path = """MATCH (p)->("*")->(q)
    WHERE p."time" = "badstring" AND q."name" = "whatever"
    """
    query = StringQuery(path)
    with pytest.raises(InvalidQueryFilter):
        engine.apply(query, gf.graph, gf.dataframe)

    class DummyType:
        def __init__(self):
            self.x = 5.0
            self.y = -1
            self.z = "hello"

    bad_field_test_dict = list(mock_graph_literal)
    bad_field_test_dict[0]["children"][0]["children"][0]["metrics"][
        "list"
    ] = DummyType()
    gf = GraphFrame.from_literal(bad_field_test_dict)
    path = """MATCH (p)->(q)->(r)
    WHERE p."name" = "foo" AND q."name" = "bar" AND p."list" = DummyType()
    """
    with pytest.raises(InvalidQueryPath):
        query = StringQuery(path)
        engine.apply(query, gf.graph, gf.dataframe)

    path = """MATCH ("*")->(p)->(q)->("*")
    WHERE p."name" = "bar" AND q."name" = "grault"
    """
    match = [
        [root, root.children[0], root.children[0].children[1]],
        [root.children[0], root.children[0].children[1]],
        [
            root,
            root.children[1],
            root.children[1].children[0],
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1],
            root.children[1].children[0],
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1].children[0],
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1].children[0].children[0],
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            root.children[1].children[0].children[0].children[0],
            root.children[1].children[0].children[0].children[0].children[1],
        ],
        [
            gf.graph.roots[1],
            gf.graph.roots[1].children[0],
            gf.graph.roots[1].children[0].children[1],
        ],
        [gf.graph.roots[1].children[0], gf.graph.roots[1].children[0].children[1]],
    ]
    match = list(set().union(*match))
    query = StringQuery(path)
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(match)

    path = """MATCH ("*")->(p)->(q)->("+")
    WHERE p."name" = "bar" AND q."name" = "grault"
    """
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == []

    gf.dataframe["time"] = np.nan
    gf.dataframe.at[gf.graph.roots[0], "time"] = 5.0
    path = """MATCH ("*", p)
    WHERE p."time" IS NOT NAN"""
    match = [gf.graph.roots[0]]
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == match

    gf.dataframe["time"] = 5.0
    gf.dataframe.at[gf.graph.roots[0], "time"] = np.nan
    path = """MATCH ("*", p)
    WHERE p."time" IS NAN"""
    match = [gf.graph.roots[0]]
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == match

    gf.dataframe["time"] = np.inf
    gf.dataframe.at[gf.graph.roots[0], "time"] = 5.0
    path = """MATCH ("*", p)
    WHERE p."time" IS NOT INF"""
    match = [gf.graph.roots[0]]
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == match

    gf.dataframe["time"] = 5.0
    gf.dataframe.at[gf.graph.roots[0], "time"] = np.inf
    path = """MATCH ("*", p)
    WHERE p."time" IS INF"""
    match = [gf.graph.roots[0]]
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == match

    names = gf.dataframe["name"].copy()
    gf.dataframe["name"] = None
    gf.dataframe.at[gf.graph.roots[0], "name"] = names.iloc[0]
    path = """MATCH ("*", p)
    WHERE p."name" IS NOT NONE"""
    match = [gf.graph.roots[0]]
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == match

    gf.dataframe["name"] = names
    gf.dataframe.at[gf.graph.roots[0], "name"] = None
    path = """MATCH ("*", p)
    WHERE p."name" IS NONE"""
    match = [gf.graph.roots[0]]
    query = StringQuery(path)
    assert engine.apply(query, gf.graph, gf.dataframe) == match


def test_string_conj_compound_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    compound_query1 = parse_string_dialect(
        """
        {MATCH ("*", p) WHERE p."time (inc)" >= 20 AND p."time (inc)" <= 60}
        AND {MATCH ("*", p) WHERE p."time (inc)" >= 60}
        """
    )
    compound_query2 = parse_string_dialect(
        """
        MATCH ("*", p)
        WHERE {p."time (inc)" >= 20 AND p."time (inc)" <= 60} AND {p."time (inc)" >= 60}
        """
    )
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        roots[0].children[1],
        roots[0].children[1].children[0],
    ]
    assert sorted(engine.apply(compound_query1, gf.graph, gf.dataframe)) == sorted(
        matches
    )
    assert sorted(engine.apply(compound_query2, gf.graph, gf.dataframe)) == sorted(
        matches
    )


def test_string_disj_compound_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    compound_query1 = parse_string_dialect(
        """
        {MATCH ("*", p) WHERE p."time (inc)" = 5.0}
        OR {MATCH ("*", p) WHERE p."time (inc)" = 10.0}
        """
    )
    compound_query2 = parse_string_dialect(
        """
        MATCH ("*", p)
        WHERE {p."time (inc)" = 5.0} OR {p."time (inc)" = 10.0}
        """
    )
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[0].children[1],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[1],
        roots[0].children[1].children[0].children[0].children[1],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
        roots[1].children[0].children[1],
    ]
    assert sorted(engine.apply(compound_query1, gf.graph, gf.dataframe)) == sorted(
        matches
    )
    assert sorted(engine.apply(compound_query2, gf.graph, gf.dataframe)) == sorted(
        matches
    )


def test_cypher_exc_disj_compound_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    compound_query1 = parse_string_dialect(
        """
        {MATCH ("*", p) WHERE p."time (inc)" >= 5.0 AND p."time (inc)" <= 10.0}
        XOR {MATCH ("*", p) WHERE p."time (inc)" = 10.0}
        """
    )
    compound_query2 = parse_string_dialect(
        """
        MATCH ("*", p)
        WHERE {p."time (inc)" >= 5.0 AND p."time (inc)" <= 10.0} XOR {p."time (inc)" = 10.0}
        """
    )
    engine = QueryEngine()
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
    ]
    assert sorted(engine.apply(compound_query1, gf.graph, gf.dataframe)) == sorted(
        matches
    )
    assert sorted(engine.apply(compound_query2, gf.graph, gf.dataframe)) == sorted(
        matches
    )


def test_leaf_query(small_mock2):
    gf = GraphFrame.from_literal(small_mock2)
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[0].children[1],
        roots[0].children[1].children[0],
        roots[0].children[1].children[1],
    ]
    nodes = set(gf.graph.traverse())
    nonleaves = list(nodes - set(matches))
    obj_query = ObjectQuery([{"depth": -1}])
    str_query_numeric = parse_string_dialect(
        """
        MATCH (p)
        WHERE p."depth" = -1
        """
    )
    str_query_is_leaf = parse_string_dialect(
        """
        MATCH (p)
        WHERE p IS LEAF
        """
    )
    str_query_is_not_leaf = parse_string_dialect(
        """
        MATCH (p)
        WHERE p IS NOT LEAF
        """
    )
    engine = QueryEngine()
    assert sorted(engine.apply(obj_query, gf.graph, gf.dataframe)) == sorted(matches)
    assert sorted(engine.apply(str_query_numeric, gf.graph, gf.dataframe)) == sorted(
        matches
    )
    assert sorted(engine.apply(str_query_is_leaf, gf.graph, gf.dataframe)) == sorted(
        matches
    )
    assert sorted(
        engine.apply(str_query_is_not_leaf, gf.graph, gf.dataframe)
    ) == sorted(nonleaves)


def test_object_dialect_all_mode(tau_profile_dir):
    gf = GraphFrame.from_tau(tau_profile_dir)
    engine = QueryEngine()
    query = ObjectQuery(
        [".", ("+", {"time (inc)": ">= 17983.0"})], multi_index_mode="all"
    )
    roots = gf.graph.roots
    matches = [
        roots[0],
        roots[0].children[6],
        roots[0].children[6].children[1],
        roots[0].children[0],
    ]
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)


def test_string_dialect_all_mode(tau_profile_dir):
    gf = GraphFrame.from_tau(tau_profile_dir)
    engine = QueryEngine()
    query = StringQuery(
        """MATCH (".")->("+", p)
        WHERE p."time (inc)" >= 17983.0
        """,
        multi_index_mode="all",
    )
    roots = gf.graph.roots
    matches = [
        roots[0],
        roots[0].children[6],
        roots[0].children[6].children[1],
        roots[0].children[0],
    ]
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)


def test_object_dialect_any_mode(tau_profile_dir):
    gf = GraphFrame.from_tau(tau_profile_dir)
    engine = QueryEngine()
    query = ObjectQuery([{"time": "< 24.0"}], multi_index_mode="any")
    roots = gf.graph.roots
    matches = [
        roots[0].children[2],
        roots[0].children[6].children[3],
    ]
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)


def test_string_dialect_any_mode(tau_profile_dir):
    gf = GraphFrame.from_tau(tau_profile_dir)
    engine = QueryEngine()
    query = StringQuery(
        """MATCH (".", p)
        WHERE p."time" < 24.0
        """,
        multi_index_mode="any",
    )
    roots = gf.graph.roots
    matches = [
        roots[0].children[2],
        roots[0].children[6].children[3],
    ]
    assert sorted(engine.apply(query, gf.graph, gf.dataframe)) == sorted(matches)


def test_multi_index_mode_assertion_error(tau_profile_dir):
    with pytest.raises(AssertionError):
        _ = ObjectQuery([".", ("*", {"name": "test"})], multi_index_mode="foo")
    with pytest.raises(AssertionError):
        _ = StringQuery(
            """ MATCH (".")->("*", p)
            WHERE p."name" = "test"
            """,
            multi_index_mode="foo",
        )
    gf = GraphFrame.from_tau(tau_profile_dir)
    query = ObjectQuery(
        [".", ("*", {"time (inc)": "> 17983.0"})], multi_index_mode="off"
    )
    engine = QueryEngine()
    with pytest.raises(MultiIndexModeMismatch):
        engine.apply(query, gf.graph, gf.dataframe)
