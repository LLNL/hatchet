# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# Make flake8 ignore unused names in this file
# flake8: noqa: F401

from typing import Any, Union, List

from .query import Query
from .compound import (
    CompoundQuery,
    ConjunctionQuery,
    DisjunctionQuery,
    ExclusiveDisjunctionQuery,
    NegationQuery,
    parse_string_dialect,
)
from .object_dialect import ObjectQuery
from .string_dialect import StringQuery
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

BaseQueryType = Union[Query, ObjectQuery, StringQuery, str, List]
CompoundQueryType = Union[
    CompoundQuery,
    ConjunctionQuery,
    DisjunctionQuery,
    ExclusiveDisjunctionQuery,
    NegationQuery,
]
LegacyQueryType = Union[
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
]


def combine_via_conjunction(
    query0: Union[BaseQueryType, CompoundQueryType],
    query1: Union[BaseQueryType, CompoundQueryType],
) -> ConjunctionQuery:
    return ConjunctionQuery(query0, query1)


def combine_via_disjunction(
    query0: Union[BaseQueryType, CompoundQueryType],
    query1: Union[BaseQueryType, CompoundQueryType],
) -> DisjunctionQuery:
    return DisjunctionQuery(query0, query1)


def combine_via_exclusive_disjunction(
    query0: Union[BaseQueryType, CompoundQueryType],
    query1: Union[BaseQueryType, CompoundQueryType],
) -> ExclusiveDisjunctionQuery:
    return ExclusiveDisjunctionQuery(query0, query1)


def negate_query(query: Union[BaseQueryType, CompoundQueryType]) -> NegationQuery:
    return NegationQuery(query)


# Note: skipping mypy checks here because we're monkey
#       patching these operators. Per mypy Issue #2427,
#       mypy doesn't like this
Query.__and__ = combine_via_conjunction  # type: ignore
Query.__or__ = combine_via_disjunction  # type: ignore
Query.__xor__ = combine_via_exclusive_disjunction  # type: ignore
Query.__not__ = negate_query  # type: ignore


CompoundQuery.__and__ = combine_via_conjunction  # type: ignore
CompoundQuery.__or__ = combine_via_disjunction  # type: ignore
CompoundQuery.__xor__ = combine_via_exclusive_disjunction  # type: ignore
CompoundQuery.__not__ = negate_query  # type: ignore


def is_hatchet_query(query_obj: Any) -> bool:
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
