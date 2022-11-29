# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from hatchet.query import IntersectionQuery, SymDifferenceQuery, UnionQuery

try:
    from abc import ABC
except ImportError:
    from abc import ABCMeta

    ABC = ABCMeta("ABC", (object,), {"__slots__": ()})
import sys

from .query import (
    Query,
    CompoundQuery,
    ConjunctionQuery,
    DisjunctionQuery,
    ExclusiveDisjunctionQuery,
    NegationQuery
)
from .object_dialect import ObjectQuery
from .string_dialect import parse_string_dialect
from .engine import QueryEngine
from .errors import (
    BadNumberNaryQueryArgs,
    InvalidQueryPath
)


COMPATABILITY_ENGINE = QueryEngine()


class AbstractQuery(ABC):

    @abstractmethod
    def apply(self, gf):
        pass

    def __and__(self, other):
        return AndQuery(self, other)

    def __or__(self, other):
        return OrQuery(self, other)

    def __xor__(self, other):
        return XorQuery(self, other)

    def __invert__(self):
        return NotQuery(self)

    @abstractmethod
    def _get_subqueries(self):
        pass

class NaryQuery(AbstractQuery):

    def __init__(self, *args):
        self.compat_subqueries = []
        if isinstance(args[0], tuple) and len(args) == 1:
            args = args[0]
        for query in args:
            if isinstance(query, list):
                self.compat_subqueries.append(QueryMatcher(query))
            elif isinstance(query, str):
                self.compat_subqueries.append(CypherQuery(query))
            elif issubclass(type(query), AbstractQuery):
                self.compat_subqueries.append(query)
            elif issubclass(type(query), Query) or issubclass(type(query), CompoundQuery):
                self.compat_subqueries.append(query)
            else:
                raise TypeError(
                    "Subqueries for NaryQuery must be either a \
                                high-level query or a subclass of AbstractQuery"
                )

    @abstractmethod
    def apply(self, gf):
        pass

    def _get_subqueries(self):
        true_subqueries = []
        for subq in self.compat_subqueries:
            if issubclass(type(subq), Query) or issubclass(type(subq), CompoundQuery):
                true_subqueries.append(subq)
            else:
                true_subqueries.extend(subq._get_subqueries())
        return true_subqueries


class AndQuery(NaryQuery):

    def __init__(self, *args):
        if sys.version_info[0] == 2:
            super(AndQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 2:
            raise BadNumberNaryQueryArgs("AndQuery requires 2 or more subqueries")

    def apply(self, gf):
        subqueries = self._get_subqueries()
        true_query = ConjunctionQuery(*subqueries)
        return COMPATABILITY_ENGINE.apply(true_query, gf.graph, gf.dataframe)


IntersectionQuery = AndQuery


class OrQuery(NaryQuery):

    def __init__(self, *args):
        if sys.version_info[0] == 2:
            super(OrQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 2:
            raise BadNumberNaryQueryArgs("OrQuery requires 2 or more subqueries")

    def apply(self, gf):
        subqueries = self._get_subqueries()
        true_query = DisjunctionQuery(*subqueries)
        return COMPATABILITY_ENGINE.apply(true_query, gf.graph, gf.dataframe)


UnionQuery = OrQuery


class XorQuery(NaryQuery):

    def __init__(self, *args):
        if sys.version_info[0] == 2:
            super(XorQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 2:
            raise BadNumberNaryQueryArgs("XorQuery requires 2 or more subqueries")

    def apply(self, gf):
        subqueries = self._get_subqueries()
        true_query = ExclusiveDisjunctionQuery(*subqueries)
        return COMPATABILITY_ENGINE.apply(true_query, gf.graph, gf.dataframe)


SymDifferenceQuery = XorQuery


class NotQuery(NaryQuery):

    def __init__(self, *args):
        if sys.version_info[0] == 2:
            super(NotQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 1:
            raise BadNumberNaryQueryArgs("NotQuery requires exactly 1 subquery")

    def apply(self, gf):
        subqueries = self._get_subqueries()
        true_query = NegationQuery(*subqueries)
        return COMPATABILITY_ENGINE.apply(true_query, gf.graph, gf.dataframe)


class QueryMatcher(AbstractQuery):

    def __init__(self, query=None):
        self.true_query = None
        if query is None:
            self.true_query = Query()
        elif isinstance(query, list):
            self.true_query = ObjectQuery(query)
        else:
            raise InvalidQueryPath("Provided query is not a valid object dialect query")

    def match(self, wildcard_spec=".", filter_func=lambda row: True):
        self.true_query.match(wildcard_spec, filter_func)

    def rel(self, wildcard_spec=".", filter_func=lambda row: True):
        self.true_query.rel(wildcard_spec, filter_func)

    def _apply_impl(self, query, gf):
        return COMPATABILITY_ENGINE.apply(query, gf.graph, gf.dataframe)

    def apply(self, gf):
        return self._apply_impl(self.true_query, gf)


class CypherQuery(QueryMatcher):

    def __init__(self, cypher_query):
        self.true_query = parse_string_dialect(cypher_query)

    def apply(self, gf):
        return self._apply_impl(self.true_query, gf)
