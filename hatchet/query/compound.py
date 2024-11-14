# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import sys
import re
from typing import List, Optional, Set, Union, cast

from ..node import Node
from ..graph import Graph
from .query import Query
from .string_dialect import StringQuery
from .object_dialect import ObjectQuery
from .errors import BadNumberNaryQueryArgs


class CompoundQuery(object):
    """Base class for all types of compound queries."""

    def __init__(self, *queries) -> None:
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
    def _apply_op_to_results(
        self, subquery_results: List[List[Node]], graph: Graph
    ) -> List[Node]:
        """Combines/Modifies the results of the subqueries based on the operation the subclass
        represents.
        """
        pass


class ConjunctionQuery(CompoundQuery):
    """A compound query that combines the results of its subqueries
    using set conjunction.
    """

    def __init__(self, *queries) -> None:
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

    def _apply_op_to_results(
        self, subquery_results: List[List[Node]], graph: Graph
    ) -> List[Node]:
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

    def __init__(self, *queries) -> None:
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

    def _apply_op_to_results(
        self, subquery_results: List[List[Node]], graph: Graph
    ) -> List[Node]:
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

    def __init__(self, *queries) -> None:
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

    def _apply_op_to_results(
        self, subquery_results: List[List[Node]], graph: Graph
    ) -> List[Node]:
        """Combines the results of the subqueries using exclusive set disjunction.

        Arguments:
            subquery_results (list): a list containing the results of each subquery
            graph (hatchet.Graph): the graph associated with the data being queried

        Returns:
            (list): A list containing all the nodes satisfying the exclusive disjunction of the subqueries' results
        """
        xor_set: Set[Node] = set()
        for res in subquery_results:
            xor_set = xor_set.symmetric_difference(set(res))
        return list(xor_set)


class NegationQuery(CompoundQuery):
    """A compound query that inverts/negates the result of
    its single subquery.
    """

    def __init__(self, *queries) -> None:
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

    def _apply_op_to_results(
        self, subquery_results: List[List[Node]], graph: Graph
    ) -> List[Node]:
        """Inverts the results of the subquery so that all nodes not in the results are returned.

        Arguments:
            subquery_results (list): a list containing the results of each subquery
            graph (hatchet.Graph): the graph associated with the data being queried

        Returns:
            (list): A list containing all the nodes in the Graph not contained in the subquery's results
        """
        trav_nodes = set(graph.traverse())
        nodes = cast(Set[Node], trav_nodes)
        query_nodes = set(subquery_results[0])
        return list(nodes.difference(query_nodes))


def parse_string_dialect(
    query_str: str, multi_index_mode: str = "off"
) -> Union[StringQuery, CompoundQuery]:
    """Parse all types of String-based queries, including multi-queries that leverage
    the curly brace delimiters.

    Arguments:
        query_str (str): the String-based query to be parsed

    Returns:
        (Query or CompoundQuery): A Hatchet query object representing the String-based query
    """
    # TODO Check if there's a way to prevent curly braces in a string
    #      from being captured

    # Find the number of curly brace-delimited regions in the query
    query_str = query_str.strip()
    curly_brace_elems = re.findall(r"\{(.*?)\}", query_str)
    num_curly_brace_elems = len(curly_brace_elems)
    # If there are no curly brace-delimited regions, just pass the query
    # off to the CypherQuery constructor
    if num_curly_brace_elems == 0:
        if sys.version_info[0] == 2:
            query_str = query_str.decode("utf-8")
        return StringQuery(query_str, multi_index_mode)
    # Create an iterator over the curly brace-delimited regions
    curly_brace_iter = re.finditer(r"\{(.*?)\}", query_str)
    # Will store curly brace-delimited regions in the WHERE clause
    condition_list = None
    # Will store curly brace-delimited regions that contain entire
    # mid-level queries (MATCH clause and WHERE clause)
    query_list = None
    # If entire queries are in brace-delimited regions, store the indexes
    # of the regions here so we don't consider brace-delimited regions
    # within the already-captured region.
    query_idxes = None
    # Store which compound queries to apply to the curly brace-delimited regions
    compound_ops = []
    for i, match in enumerate(curly_brace_iter):
        # Get the substring within curly braces
        substr = query_str[match.start() + 1 : match.end() - 1]
        substr = substr.strip()
        # If an entire query (MATCH + WHERE) is within curly braces,
        # add the query to "query_list", and add the indexes corresponding
        # to the query to "query_idxes"
        if substr.startswith("MATCH"):
            if query_list is None:
                query_list = []
            if query_idxes is None:
                query_idxes = []
            query_list.append(substr)
            query_idxes.append((match.start(), match.end()))
        # If the curly brace-delimited region contains only parts of a
        # WHERE clause, first, check if the region is within another
        # curly brace delimited region. If it is, do nothing (it will
        # be handled later). Otherwise, add the region to "condition_list"
        elif re.match(r"[a-zA-Z0-9_]+\..*", substr) is not None:
            is_encapsulated_region = False
            if query_idxes is not None:
                for s, e in query_idxes:
                    if match.start() >= s or match.end() <= e:
                        is_encapsulated_region = True
                        break
            if is_encapsulated_region:
                continue
            if condition_list is None:
                condition_list = []
            condition_list.append(substr)
        # If the curly brace-delimited region is neither a whole query
        # or part of a WHERE clause, raise an error
        else:
            raise ValueError("Invalid grouping (with curly braces) within the query")
        # If there is a compound operator directly after the curly brace-delimited region,
        # capture the type of operator, and store the type in "compound_ops"
        if i + 1 < num_curly_brace_elems:
            rest_substr = query_str[match.end() :]
            rest_substr = rest_substr.strip()
            if rest_substr.startswith("AND"):
                compound_ops.append("AND")
            elif rest_substr.startswith("OR"):
                compound_ops.append("OR")
            elif rest_substr.startswith("XOR"):
                compound_ops.append("XOR")
            else:
                raise ValueError("Invalid compound operator type found!")
    # Each call to this function should only consider one of the full query or
    # WHERE clause versions at a time. If both types were captured, raise an error
    # because some type of internal logic issue occured.
    if condition_list is not None and query_list is not None:
        raise ValueError(
            "Curly braces must be around either a full mid-level query or a set of conditions in a single mid-level query"
        )
    # This branch is for the WHERE clause version
    if condition_list is not None:
        # Make sure you correctly gathered curly brace-delimited regions and
        # compound operators
        if len(condition_list) != len(compound_ops) + 1:
            raise ValueError(
                "Incompatible number of curly brace elements and compound operators"
            )
        # Get the MATCH clause that will be shared across the subqueries
        match_comp_obj = re.search(r"MATCH\s+(?P<match_field>.*)\s+WHERE", query_str)
        match_comp = match_comp_obj.group("match_field")
        # Iterate over the compound operators
        full_query: Optional[Union[StringQuery, CompoundQuery]] = None
        for i, op in enumerate(compound_ops):
            # If in the first iteration, set the initial query as a CypherQuery where
            # the MATCH clause is the shared match clause and the WHERE clause is the
            # first curly brace-delimited region
            if i == 0:
                query1 = "MATCH {} WHERE {}".format(match_comp, condition_list[i])
                if sys.version_info[0] == 2:
                    query1 = query1.decode("utf-8")
                full_query = StringQuery(query1, multi_index_mode)
            # Get the next query as a CypherQuery where
            # the MATCH clause is the shared match clause and the WHERE clause is the
            # next curly brace-delimited region
            next_query = "MATCH {} WHERE {}".format(match_comp, condition_list[i + 1])
            if sys.version_info[0] == 2:
                next_query = next_query.decode("utf-8")
            next_string_query: Union[StringQuery, CompoundQuery] = StringQuery(
                next_query, multi_index_mode
            )
            # Add the next query to the full query using the compound operator
            # currently being considered
            if op == "AND":
                assert full_query is not None
                full_query = ConjunctionQuery(full_query, next_string_query)
            elif op == "OR":
                assert full_query is not None
                full_query = DisjunctionQuery(full_query, next_string_query)
            else:
                assert full_query is not None
                full_query = ExclusiveDisjunctionQuery(full_query, next_string_query)
        return full_query
    # This branch is for the full query version
    else:
        # Make sure you correctly gathered curly brace-delimited regions and
        # compound operators
        if len(query_list) != len(compound_ops) + 1:
            raise ValueError(
                "Incompatible number of curly brace elements and compound operators"
            )
        # Iterate over the compound operators
        full_query = None
        for i, op in enumerate(compound_ops):
            # If in the first iteration, set the initial query as the result
            # of recursively calling this function on the first curly brace-delimited region
            if i == 0:
                full_query = parse_string_dialect(query_list[i])
            # Get the next query by recursively calling this function
            # on the next curly brace-delimited region
            next_string_query = parse_string_dialect(query_list[i + 1])
            # Add the next query to the full query using the compound operator
            # currently being considered
            if op == "AND":
                assert full_query is not None
                full_query = ConjunctionQuery(full_query, next_string_query)
            elif op == "OR":
                assert full_query is not None
                full_query = DisjunctionQuery(full_query, next_string_query)
            else:
                assert full_query is not None
                full_query = ExclusiveDisjunctionQuery(full_query, next_string_query)
        return full_query
