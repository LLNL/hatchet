# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import sys

from .errors import (
    BadNumberNaryQueryArgs,
    InvalidQueryPath
)

class QueryOps:

    def __init__(self):
        pass

    def __and__(self, other):
        return ConjunctionQuery(self, other)

    def __or__(self, other):
        return DisjunctionQuery(self, other)

    def __xor__(self, other):
       return ExclusiveDisjunctionQuery(self, other)

    def __invert__(self):
        return NegationQuery(self)


class Query(QueryOps):

    def __init__(self):
        self.query_pattern = []

    def match(self, quantifier=".", predicate=lambda row: True):
        """Start a query with a root node described by the arguments.

        Arguments:
            wildcard_spec (str, optional, ".", "*", or "+"): the wildcard status of the node (follows standard Regex syntax)
            filter_func (callable, optional): a callable accepting only a row from a Pandas DataFrame that is used to filter this node in the query

        Returns:
            (QueryMatcher): The instance of the class that called this function (enables fluent design).
        """
        if len(self.query_pattern) != 0:
            self.query_pattern = []
        self._add_node(quantifier, predicate)
        return self

    def rel(self, quantifier=".", predicate=lambda row: True):
        """Add another edge and node to the query.

        Arguments:
            wildcard_spec (str, optional, ".", "*", or "+"): the wildcard status of the node (follows standard Regex syntax)
            filter_func (callable, optional): a callable accepting only a row from a Pandas DataFrame that is used to filter this node in the query

        Returns:
            (QueryMatcher): The instance of the class that called this function (enables fluent design).
        """
        if len(self.query_pattern) == 0:
            raise InvalidQueryPath(
                "Queries in the base Query Language must start with a call to 'match'"
            )
        self._add_node(quantifier, predicate)
        return self

    def relation(self, quantifer=".", predicate=lambda row: True):
        return self.rel(quantifer, predicate)

    def __len__(self):
        return len(self.query_pattern)

    def __iter__(self):
        return iter(self.query_pattern)

    def _add_node(self, quantifer=".", predicate=lambda row: True):
        """Add a node to the query.
        Arguments:
            wildcard_spec (str, optional, ".", "*", or "+"): the wildcard status of the node (follows standard Regex syntax)
            filter_func (callable, optional): a callable accepting only a row from a Pandas DataFrame that is used to filter this node in the query
        """
        assert isinstance(quantifer, int) or isinstance(quantifer, str)
        assert callable(predicate)
        if isinstance(quantifer, int):
            for _ in range(quantifer):
                self.query_pattern.append((".", predicate))
        elif quantifer == "+":
            self.query_pattern.append((".", predicate))
            self.query_pattern.append(("*", predicate))
        else:
            assert quantifer == "." or quantifer == "*"
            self.query_pattern.append((quantifer, predicate))


class CompoundQuery(QueryOps):

    def __init__(self, *queries):
        self.subqueries = []
        if isinstance(queries[0], tuple) and len(queries) == 1:
            queries = queries[0]
        for query in queries:
            if (issubclass(type(query), Query) or issubclass(type(query), CompoundQuery) or
                isinstance(query, list) or isinstance(query, str)):
                self.subqueries.append(query)
            else:
                raise TypeError(
                    "Subqueries for NaryQuery must be either a \
                                high-level query or a subclass of AbstractQuery"
                )

    @abstractmethod
    def _apply_op_to_results(self, subquery_results):
        pass


class ConjunctionQuery(CompoundQuery):

    def __init__(self, *queries):
        if sys.version_info[0] == 2:
            super(ConjunctionQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) < 2:
            raise BadNumberNaryQueryArgs("ConjunctionQuery requires 2 or more subqueries")

    def _apply_op_to_results(self, subquery_results, graph):
        intersection_set = set(subquery_results[0]).intersection(*subquery_results[1:])
        return list(intersection_set)


class DisjunctionQuery(CompoundQuery):

    def __init__(self, *queries):
        if sys.version_info[0] == 2:
            super(DisjunctionQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) < 2:
            raise BadNumberNaryQueryArgs("DisjunctionQuery requires 2 or more subqueries")

    def _apply_op_to_results(self, subquery_results, graph):
        union_set = set().union(*subquery_results)
        return list(union_set)


class ExclusiveDisjunctionQuery(CompoundQuery):

    def __init__(self, *queries):
        if sys.version_info[0] == 2:
            super(ExclusiveDisjunctionQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) < 2:
            raise BadNumberNaryQueryArgs("XorQuery requires 2 or more subqueries")

    def _apply_op_to_results(self, subquery_results, graph):
        xor_set = set()
        for res in subquery_results:
            xor_set = xor_set.symmetric_difference(set(res))
        return list(xor_set)


class NegationQuery(CompoundQuery):

    def __init__(self, *queries):
        if sys.version_info[0] == 2:
            super(NegationQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) != 1:
            raise BadNumberNaryQueryArgs("NotQuery requires exactly 1 subquery")

    def _apply_op_to_results(self, subquery_results, graph):
        nodes = set(graph.traverse())
        query_nodes = set(subquery_results[0])
        return list(nodes.difference(query_nodes))
