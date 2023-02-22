# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import sys

from .query import Query
from .string_dialect import parse_string_dialect
from .object_dialect import ObjectQuery
from .errors import BadNumberNaryQueryArgs


class CompoundQuery(object):

    """Base class for all types of compound queries."""

    def __init__(self, *queries):
        """Collect the provided queries into a list, constructing ObjectQuery and StringQuery objects as needed.

        Arguments:
            *queries (Query, CompoundQuery, list, or str): the subqueries of the compound query
        """
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
        """Combines/Modifies the results of the subqueries based on the operation the subclass
        represents.
        """
        pass


class ConjunctionQuery(CompoundQuery):

    """A compound query that combines the results of its subqueries
    using set conjunction.
    """

    def __init__(self, *queries):
        """Create the ConjunctionQuery.

        Arguments:
            *queries (Query, CompoundQuery, list, or str): the subqueries of the compound query
        """
        if sys.version_info[0] == 2:
            super(ConjunctionQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) < 2:
            raise BadNumberNaryQueryArgs(
                "ConjunctionQuery requires 2 or more subqueries"
            )

    def _apply_op_to_results(self, subquery_results, graph):
        """Combines the results of the subqueries using set conjunction.

        Arguments:
            subquery_results (list): a list containing the results of each subquery
            graph (hatchet.Graph): the graph associated with the data being queried

        Returns:
            (list): A list containing all the nodes satisfying the conjunction of the subqueries' results
        """
        intersection_set = set(subquery_results[0]).intersection(*subquery_results[1:])
        return list(intersection_set)


class DisjunctionQuery(CompoundQuery):

    """A compound query that combines the results of its subqueries
    using set disjunction.
    """

    def __init__(self, *queries):
        """Create the DisjunctionQuery.

        Arguments:
            *queries (Query, CompoundQuery, list, or str): the subqueries of the compound query
        """
        if sys.version_info[0] == 2:
            super(DisjunctionQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) < 2:
            raise BadNumberNaryQueryArgs(
                "DisjunctionQuery requires 2 or more subqueries"
            )

    def _apply_op_to_results(self, subquery_results, graph):
        """Combines the results of the subqueries using set disjunction.

        Arguments:
            subquery_results (list): a list containing the results of each subquery
            graph (hatchet.Graph): the graph associated with the data being queried

        Returns:
            (list): A list containing all the nodes satisfying the disjunction of the subqueries' results
        """
        union_set = set().union(*subquery_results)
        return list(union_set)


class ExclusiveDisjunctionQuery(CompoundQuery):

    """A compound query that combines the results of its subqueries
    using exclusive set disjunction.
    """

    def __init__(self, *queries):
        """Create the ExclusiveDisjunctionQuery.

        Arguments:
            *queries (Query, CompoundQuery, list, or str): the subqueries of the compound query
        """
        if sys.version_info[0] == 2:
            super(ExclusiveDisjunctionQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) < 2:
            raise BadNumberNaryQueryArgs("XorQuery requires 2 or more subqueries")

    def _apply_op_to_results(self, subquery_results, graph):
        """Combines the results of the subqueries using exclusive set disjunction.

        Arguments:
            subquery_results (list): a list containing the results of each subquery
            graph (hatchet.Graph): the graph associated with the data being queried

        Returns:
            (list): A list containing all the nodes satisfying the exclusive disjunction of the subqueries' results
        """
        xor_set = set()
        for res in subquery_results:
            xor_set = xor_set.symmetric_difference(set(res))
        return list(xor_set)


class NegationQuery(CompoundQuery):

    """A compound query that inverts/negates the result of
    its single subquery.
    """

    def __init__(self, *queries):
        """Create the NegationQuery.

        Arguments:
            *queries (Query, CompoundQuery, list, or str): the subqueries of the compound query. There must be eactly one subquery provided.
        """
        if sys.version_info[0] == 2:
            super(NegationQuery, self).__init__(*queries)
        else:
            super().__init__(*queries)
        if len(self.subqueries) != 1:
            raise BadNumberNaryQueryArgs("NotQuery requires exactly 1 subquery")

    def _apply_op_to_results(self, subquery_results, graph):
        """Inverts the results of the subquery so that all nodes not in the results are returned.

        Arguments:
            subquery_results (list): a list containing the results of each subquery
            graph (hatchet.Graph): the graph associated with the data being queried

        Returns:
            (list): A list containing all the nodes in the Graph not contained in the subquery's results
        """
        nodes = set(graph.traverse())
        query_nodes = set(subquery_results[0])
        return list(nodes.difference(query_nodes))
