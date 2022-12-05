# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import sys

from .query import Query
from .string_dialect import parse_string_dialect
from .object_dialect import ObjectQuery
from .errors import BadNumberNaryQueryArgs

class CompoundQuery:

    def __init__(self, *queries):
        self.subqueries = []
        if isinstance(queries[0], tuple) and len(queries) == 1:
            queries = queries[0]
        for query in queries:
            if issubclass(type(query), Query) or issubclass(type(query), CompoundQuery):
                self.subqueries.append(query)
            elif isinstance(query, list):
                self.subqueries.append(ObjectQuery(query))
            elif isinstance(query, str):
                self.subqueries.append(parse_string_dialect(query))
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
