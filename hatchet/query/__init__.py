# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# Make flake8 ignore unused names in this file
# flake8: noqa: F401

from .query import Query
from .compound import (
    CompoundQuery,
    ConjunctionQuery,
    DisjunctionQuery,
    ExclusiveDisjunctionQuery,
    NegationQuery,
)
from .object_dialect import ObjectQuery
from .string_dialect import StringQuery, parse_string_dialect
from .engine import QueryEngine
from .errors import (
    InvalidQueryPath,
    InvalidQueryFilter,
    RedundantQueryFilterWarning,
    BadNumberNaryQueryArgs,
)

from .compat import (
    AbstractQuery,
    NaryQuery,
    AndQuery,
    IntersectionQuery,
    OrQuery,
    UnionQuery,
    XorQuery,
    SymDifferenceQuery,
    NotQuery,
    QueryMatcher,
    CypherQuery,
    parse_cypher_query,
)


def combine_via_conjunction(query0, query1):
    return ConjunctionQuery(query0, query1)


def combine_via_disjunction(query0, query1):
    return DisjunctionQuery(query0, query1)


def combine_via_exclusive_disjunction(query0, query1):
    return ExclusiveDisjunctionQuery(query0, query1)


def negate_query(query):
    return NegationQuery(query)


Query.__and__ = combine_via_conjunction
Query.__or__ = combine_via_disjunction
Query.__xor__ = combine_via_exclusive_disjunction
Query.__not__ = negate_query


CompoundQuery.__and__ = combine_via_conjunction
CompoundQuery.__or__ = combine_via_disjunction
CompoundQuery.__xor__ = combine_via_exclusive_disjunction
CompoundQuery.__not__ = negate_query


def is_hatchet_query(query_obj):
    return (
        issubclass(type(query_obj), Query)
        or issubclass(type(query_obj), CompoundQuery)
        or issubclass(type(query_obj), AbstractQuery)
    )


# Uncomment when accessing old-style queries using
# 'from hatchet.query import *' is removed
#
# __all__ = [
#     "Query",
#     "CompoundQuery",
#     "ConjunctionQuery",
#     "DisjunctionQuery",
#     "ExclusiveDisjunctionQuery",
#     "NegationQuery",
#     "ObjectQuery",
#     "StringQuery",
#     "parse_string_dialect",
#     "InvalidQueryFilter",
#     "InvalidQueryPath",
#     "RedundantQueryFilterWarning",
#     "BadNumberNaryQueryArgs",
# ]
