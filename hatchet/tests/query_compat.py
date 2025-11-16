# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np
import pytest

from hatchet import GraphFrame
from hatchet.query import (
    AbstractQuery,
    AndQuery,
    CypherQuery,
    IntersectionQuery,
    InvalidQueryFilter,
    InvalidQueryPath,
    NaryQuery,
    OrQuery,
    QueryMatcher,
    SymDifferenceQuery,
    UnionQuery,
    XorQuery,
    parse_cypher_query,
)


def test_apply_indices(calc_pi_hpct_db):
    gf = GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    gf.drop_index_levels()
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
    query = QueryMatcher(path)
    assert sorted(query.apply(gf)) == sorted(matches)

    gf.drop_index_levels()
    assert query.apply(gf) == matches


def test_high_level_depth(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query = QueryMatcher([("*", {"depth": 1})])
    roots = gf.graph.roots
    matches = [c for r in roots for c in r.children]
    assert sorted(query.apply(gf)) == sorted(matches)

    query = QueryMatcher([("*", {"depth": "<= 2"})])
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
    assert sorted(query.apply(gf)) == sorted(matches)

    with pytest.raises(InvalidQueryFilter):
        query = QueryMatcher([{"depth": "hello"}])
        query.apply(gf)


def test_high_level_hatchet_nid(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query = QueryMatcher([("*", {"node_id": ">= 20"})])
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
    assert sorted(query.apply(gf)) == sorted(matches)

    query = QueryMatcher([{"node_id": 0}])
    assert query.apply(gf) == [gf.graph.roots[0]]

    with pytest.raises(InvalidQueryFilter):
        query = QueryMatcher([{"node_id": "hello"}])
        query.apply(gf)


def test_high_level_depth_index_levels(calc_pi_hpct_db):
    gf = GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    gf.drop_index_levels()
    root = gf.graph.roots[0]

    query = QueryMatcher([("*", {"depth": "<= 2"})])
    matches = [
        [root, root.children[0], root.children[0].children[0]],
        [root.children[0], root.children[0].children[0]],
        [root.children[0].children[0]],
        [root, root.children[0], root.children[0].children[1]],
        [root.children[0], root.children[0].children[1]],
        [root.children[0].children[1]],
    ]
    matches = list(set().union(*matches))
    assert sorted(query.apply(gf)) == sorted(matches)

    query = QueryMatcher([("*", {"depth": 0})])
    matches = [root]
    assert query.apply(gf) == matches

    with pytest.raises(InvalidQueryFilter):
        query = QueryMatcher([{"depth": "hello"}])
        query.apply(gf)


def test_high_level_node_id_index_levels(calc_pi_hpct_db):
    gf = GraphFrame.from_hpctoolkit(str(calc_pi_hpct_db))
    gf.drop_index_levels()
    root = gf.graph.roots[0]

    query = QueryMatcher([("*", {"node_id": "<= 2"})])
    matches = [
        [root, root.children[0]],
        [root.children[0]],
        [root, root.children[0], root.children[0].children[0]],
        [root.children[0], root.children[0].children[0]],
        [root.children[0].children[0]],
    ]
    matches = list(set().union(*matches))
    assert sorted(query.apply(gf)) == sorted(matches)

    query = QueryMatcher([("*", {"node_id": 0})])
    matches = [root]
    assert query.apply(gf) == matches

    with pytest.raises(InvalidQueryFilter):
        query = QueryMatcher([{"node_id": "hello"}])
        query.apply(gf)


def test_high_level_multi_condition_one_attribute(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query = QueryMatcher([("*", {"time (inc)": [">= 20", "<= 60"]})])
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
    assert sorted(query.apply(gf)) == sorted(matches)


def test_query_matcher_is_abstract_query():
    assert issubclass(QueryMatcher, AbstractQuery)


def test_nary_query_is_abstract_query():
    assert issubclass(NaryQuery, AbstractQuery)


def test_and_query_is_nary_query():
    assert issubclass(AndQuery, NaryQuery)


def test_or_query_is_nary_query():
    assert issubclass(OrQuery, NaryQuery)


def test_xor_query_is_nary_query():
    assert issubclass(XorQuery, NaryQuery)


def test_and_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 20", "<= 60"]})]
    query2 = [("*", {"time (inc)": ">= 60"})]
    compound_query = AndQuery(query1, query2)
    roots = gf.graph.roots
    matches = [
        roots[0].children[1],
        roots[0].children[1].children[0],
    ]
    assert sorted(compound_query.apply(gf)) == sorted(matches)


def test_intersection_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 20", "<= 60"]})]
    query2 = [("*", {"time (inc)": ">= 60"})]
    compound_query = IntersectionQuery(query1, query2)
    roots = gf.graph.roots
    matches = [
        roots[0].children[1],
        roots[0].children[1].children[0],
    ]
    assert sorted(compound_query.apply(gf)) == sorted(matches)


def test_or_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": 5.0})]
    query2 = [("*", {"time (inc)": 10.0})]
    compound_query = OrQuery(query1, query2)
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
    assert sorted(compound_query.apply(gf)) == sorted(matches)


def test_union_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": 5.0})]
    query2 = [("*", {"time (inc)": 10.0})]
    compound_query = UnionQuery(query1, query2)
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
    assert sorted(compound_query.apply(gf)) == sorted(matches)


def test_xor_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 5.0", "<= 10.0"]})]
    query2 = [("*", {"time (inc)": 10.0})]
    compound_query = XorQuery(query1, query2)
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
    ]
    assert sorted(compound_query.apply(gf)) == sorted(matches)


def test_sym_diff_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    query1 = [("*", {"time (inc)": [">= 5.0", "<= 10.0"]})]
    query2 = [("*", {"time (inc)": 10.0})]
    compound_query = SymDifferenceQuery(query1, query2)
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
    ]
    assert sorted(compound_query.apply(gf)) == sorted(matches)


def test_apply_cypher(mock_graph_literal):
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
    query = CypherQuery(path)

    assert sorted(query.apply(gf)) == sorted(match)

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
    query = CypherQuery(path)
    assert sorted(query.apply(gf)) == sorted(match)

    path = """MATCH (p)->(q)->(r)
    WHERE p."name" = "foo" AND q."name" = "bar" AND r."time" = 5.0
    """
    match = [root, root.children[0], root.children[0].children[0]]
    query = CypherQuery(path)
    assert sorted(query.apply(gf)) == sorted(match)

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
    query = CypherQuery(path)
    assert sorted(query.apply(gf)) == sorted(match)

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
    query = CypherQuery(path)
    assert sorted(query.apply(gf)) == sorted(match)

    path = """MATCH (p)->("*", q)->(r)
    WHERE p."name" = "this" AND q."name" = "is" AND r."name" = "nonsense"
    """

    query = CypherQuery(path)
    assert query.apply(gf) == []

    path = """MATCH (p)->("*")->(q)
    WHERE p."name" = 5 AND q."name" = "whatever"
    """
    with pytest.raises(InvalidQueryFilter):
        query = CypherQuery(path)
        query.apply(gf)

    path = """MATCH (p)->("*")->(q)
    WHERE p."time" = "badstring" AND q."name" = "whatever"
    """
    query = CypherQuery(path)
    with pytest.raises(InvalidQueryFilter):
        query.apply(gf)

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
        query = CypherQuery(path)
        query.apply(gf)

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
    query = CypherQuery(path)
    assert sorted(query.apply(gf)) == sorted(match)

    path = """MATCH ("*")->(p)->(q)->("+")
    WHERE p."name" = "bar" AND q."name" = "grault"
    """
    query = CypherQuery(path)
    assert query.apply(gf) == []

    gf.dataframe["time"] = np.nan
    gf.dataframe.at[gf.graph.roots[0], "time"] = 5.0
    path = """MATCH ("*", p)
    WHERE p."time" IS NOT NAN"""
    match = [gf.graph.roots[0]]
    query = CypherQuery(path)
    assert query.apply(gf) == match

    gf.dataframe["time"] = 5.0
    gf.dataframe.at[gf.graph.roots[0], "time"] = np.nan
    path = """MATCH ("*", p)
    WHERE p."time" IS NAN"""
    match = [gf.graph.roots[0]]
    query = CypherQuery(path)
    assert query.apply(gf) == match

    gf.dataframe["time"] = np.inf
    gf.dataframe.at[gf.graph.roots[0], "time"] = 5.0
    path = """MATCH ("*", p)
    WHERE p."time" IS NOT INF"""
    match = [gf.graph.roots[0]]
    query = CypherQuery(path)
    assert query.apply(gf) == match

    gf.dataframe["time"] = 5.0
    gf.dataframe.at[gf.graph.roots[0], "time"] = np.inf
    path = """MATCH ("*", p)
    WHERE p."time" IS INF"""
    match = [gf.graph.roots[0]]
    query = CypherQuery(path)
    assert query.apply(gf) == match

    names = gf.dataframe["name"].copy()
    gf.dataframe["name"] = None
    gf.dataframe.at[gf.graph.roots[0], "name"] = names.iloc[0]
    path = """MATCH ("*", p)
    WHERE p."name" IS NOT NONE"""
    match = [gf.graph.roots[0]]
    query = CypherQuery(path)
    assert query.apply(gf) == match

    gf.dataframe["name"] = names
    gf.dataframe.at[gf.graph.roots[0], "name"] = None
    path = """MATCH ("*", p)
    WHERE p."name" IS NONE"""
    match = [gf.graph.roots[0]]
    query = CypherQuery(path)
    assert query.apply(gf) == match


def test_cypher_and_compound_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    compound_query1 = parse_cypher_query(
        """
        {MATCH ("*", p) WHERE p."time (inc)" >= 20 AND p."time (inc)" <= 60}
        AND {MATCH ("*", p) WHERE p."time (inc)" >= 60}
        """
    )
    compound_query2 = parse_cypher_query(
        """
        MATCH ("*", p)
        WHERE {p."time (inc)" >= 20 AND p."time (inc)" <= 60} AND {p."time (inc)" >= 60}
        """
    )
    roots = gf.graph.roots
    matches = [
        roots[0].children[1],
        roots[0].children[1].children[0],
    ]
    assert sorted(compound_query1.apply(gf)) == sorted(matches)
    assert sorted(compound_query2.apply(gf)) == sorted(matches)


def test_cypher_or_compound_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    compound_query1 = parse_cypher_query(
        """
        {MATCH ("*", p) WHERE p."time (inc)" = 5.0}
        OR {MATCH ("*", p) WHERE p."time (inc)" = 10.0}
        """
    )
    compound_query2 = parse_cypher_query(
        """
        MATCH ("*", p)
        WHERE {p."time (inc)" = 5.0} OR {p."time (inc)" = 10.0}
        """
    )
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
    assert sorted(compound_query1.apply(gf)) == sorted(matches)
    assert sorted(compound_query2.apply(gf)) == sorted(matches)


def test_cypher_xor_compound_query(mock_graph_literal):
    gf = GraphFrame.from_literal(mock_graph_literal)
    compound_query1 = parse_cypher_query(
        """
        {MATCH ("*", p) WHERE p."time (inc)" >= 5.0 AND p."time (inc)" <= 10.0}
        XOR {MATCH ("*", p) WHERE p."time (inc)" = 10.0}
        """
    )
    compound_query2 = parse_cypher_query(
        """
        MATCH ("*", p)
        WHERE {p."time (inc)" >= 5.0 AND p."time (inc)" <= 10.0} XOR {p."time (inc)" = 10.0}
        """
    )
    roots = gf.graph.roots
    matches = [
        roots[0].children[0].children[0],
        roots[0].children[1].children[0].children[0].children[0].children[0],
        roots[0].children[2].children[0].children[0],
        roots[0].children[2].children[0].children[1].children[0].children[0],
        roots[1].children[0].children[0],
    ]
    assert sorted(compound_query1.apply(gf)) == sorted(matches)
    assert sorted(compound_query2.apply(gf)) == sorted(matches)


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
    obj_query = QueryMatcher([{"depth": -1}])
    str_query_numeric = parse_cypher_query(
        """
        MATCH (p)
        WHERE p."depth" = -1
        """
    )
    str_query_is_leaf = parse_cypher_query(
        """
        MATCH (p)
        WHERE p IS LEAF
        """
    )
    str_query_is_not_leaf = parse_cypher_query(
        """
        MATCH (p)
        WHERE p IS NOT LEAF
        """
    )
    assert sorted(obj_query.apply(gf)) == sorted(matches)
    assert sorted(str_query_numeric.apply(gf)) == sorted(matches)
    assert sorted(str_query_is_leaf.apply(gf)) == sorted(matches)
    assert sorted(str_query_is_not_leaf.apply(gf)) == sorted(nonleaves)
