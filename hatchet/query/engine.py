# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from itertools import groupby
import pandas as pd

from .errors import InvalidQueryFilter
from ..node import Node, traversal_order
from .query import Query
from .compound import CompoundQuery
from .object_dialect import ObjectQuery
from .string_dialect import parse_string_dialect


class QueryEngine:
    """Class for applying queries to GraphFrames."""

    def __init__(self):
        """Creates the QueryEngine."""
        self.search_cache = {}

    def reset_cache(self):
        """Resets the cache in the QueryEngine."""
        self.search_cache = {}

    def apply(self, query, graph, dframe):
        """Apply the query to a GraphFrame.

        Arguments:
            query (Query or CompoundQuery): the query being applied
            graph (Graph): the Graph to which the query is being applied
            dframe (pandas.DataFrame): the DataFrame associated with the graph

        Returns:
            (list): A list representing the set of nodes from paths that match the query
        """
        if issubclass(type(query), Query):
            self.reset_cache()
            matches = []
            visited = set()
            for root in sorted(graph.roots, key=traversal_order):
                self._apply_impl(query, dframe, root, visited, matches)
            assert len(visited) == len(graph)
            matched_node_set = list(set().union(*matches))
            # return matches
            return matched_node_set
        elif issubclass(type(query), CompoundQuery):
            results = []
            for subq in query.subqueries:
                subq_obj = subq
                if isinstance(subq, list):
                    subq_obj = ObjectQuery(subq)
                elif isinstance(subq, str):
                    subq_obj = parse_string_dialect(subq)
                results.append(self.apply(subq_obj, graph, dframe))
            return query._apply_op_to_results(results, graph)
        else:
            raise TypeError("Invalid query data type ({})".format(str(type(query))))

    def _cache_node(self, node, query, dframe):
        """Cache (Memoize) the parts of the query that the node matches.

        Arguments:
            node (Node): the Node to be cached
            query (Query): the query being applied
            dframe (pandas.DataFrame): the DataFrame containing node metrics and other data
        """
        assert isinstance(node, Node)
        matches = []
        # Applies each filtering function to the node to cache which
        # query nodes the current node matches.
        for i, node_query in enumerate(query):
            _, filter_func = node_query
            row = None
            if isinstance(dframe.index, pd.MultiIndex):
                row = dframe.xs(node, level="node", drop_level=False)
            else:
                row = dframe.loc[node]
            if filter_func(row):
                matches.append(i)
        self.search_cache[node._hatchet_nid] = matches

    def _match_0_or_more(self, query, dframe, node, wcard_idx):
        """Process a "*" predicate in the query on a subgraph.

        Arguments:
            query (Query): the query being applied
            dframe (pandas.DataFrame): the DataFrame containing the metrics for the queried GraphFrame
            node (Node): the node being queried against the "*" predicate
            wcard_idx (int): the index into the query associated with the "*" predicate

        Returns:
            (list): a list of lists representing the paths rooted at "node" that match the "*" predicate
                    and/or the next query node. Will return None if there is no match for the "*"
                    predicate or the next query node.
        """
        # Cache the node if it's not already cached
        if node._hatchet_nid not in self.search_cache:
            self._cache_node(node, query, dframe)
        # If the node matches with the next non-wildcard query node,
        # end the recursion and return the node.
        if wcard_idx + 1 in self.search_cache[node._hatchet_nid]:
            return [[]]
        # If the node matches the "*" wildcard query, recursively
        # apply this function to the current node's children. Then,
        # collect their returned matches, and prepend the current node.
        elif wcard_idx in self.search_cache[node._hatchet_nid]:
            matches = []
            if len(node.children) == 0:
                if wcard_idx == len(query) - 1:
                    return [[node]]
                return None
            for child in sorted(node.children, key=traversal_order):
                sub_match = self._match_0_or_more(query, dframe, child, wcard_idx)
                if sub_match is not None:
                    matches.extend(sub_match)
            if len(matches) == 0:
                return None
            tmp = set(tuple(m) for m in matches)
            matches = [list(t) for t in tmp]
            return [[node] + m for m in matches]
        # If the current node doesn't match the current "*" wildcard or
        # the next non-wildcard query node, return None.
        else:
            if wcard_idx == len(query) - 1:
                return [[]]
            return None

    def _match_1(self, query, dframe, node, idx):
        """Process a "." predicate in the query on a subgraph.

        Arguments:
            query (Query): the query being applied
            dframe (pandas.DataFrame): the DataFrame containing the metrics for the queried GraphFrame
            node (Node): the node being queried against the "." predicate
            idx (int): the index into the query associated with the "." predicate

        Returns:
            (list): A list of lists representing the children of "node" that match the "." predicate being considered.
                    Will return None if there are no matches for the "." predicate.
        """
        if node._hatchet_nid not in self.search_cache:
            self._cache_node(node, query, dframe)
        matches = []
        for child in sorted(node.children, key=traversal_order):
            # Cache the node if it's not already cached
            if child._hatchet_nid not in self.search_cache:
                self._cache_node(child, query, dframe)
            if idx in self.search_cache[child._hatchet_nid]:
                matches.append([child])
        # To be consistent with the other matching functions, return
        # None instead of an empty list.
        if len(matches) == 0:
            return None
        return matches

    def _match_pattern(self, query, dframe, pattern_root, match_idx):
        """Try to match the query pattern starting at the provided root node.

        Arguments:
            query (Query): the query being applied
            dframe (pandas.DataFrame): the DataFrame containing the metrics for the queried GraphFrame
            pattern_root (Node): the current node considered in the query
            match_idx (int): the current index into the query

        Returns:
            (list): A list of lists representing the paths rooted at "pattern_root" that match the query
        """
        assert isinstance(pattern_root, Node)
        # Starting query node
        pattern_idx = match_idx + 1
        if query.query_pattern[match_idx][0] == "*":
            pattern_idx = 0
        # Starting matching pattern
        matches = [[pattern_root]]
        while pattern_idx < len(query):
            # Get the wildcard type
            wcard, _ = query.query_pattern[pattern_idx]
            new_matches = []
            # Consider each existing match individually so that more
            # nodes can be added to them.
            for m in matches:
                sub_match = []
                # Get the portion of the subgraph that matches the next
                # part of the query.
                if wcard == ".":
                    s = self._match_1(query, dframe, m[-1], pattern_idx)
                    if s is None:
                        sub_match.append(s)
                    else:
                        sub_match.extend(s)
                elif wcard == "*":
                    if len(m[-1].children) == 0:
                        sub_match.append([])
                    else:
                        for child in sorted(m[-1].children, key=traversal_order):
                            s = self._match_0_or_more(query, dframe, child, pattern_idx)
                            if s is None:
                                sub_match.append(s)
                            else:
                                sub_match.extend(s)
                else:
                    raise InvalidQueryFilter(
                        'Query wildcards must (internally) be one of "." or "*"'
                    )
                # Merge the next part of the match path with the
                # existing part.
                for s in sub_match:
                    if s is not None:
                        new_matches.append(m + s)
                new_matches = [uniq_match for uniq_match, _ in groupby(new_matches)]
            # Overwrite the old matches with the updated matches
            matches = new_matches
            # If all the existing partial matches were not able to be
            # expanded into full matches, return None.
            if len(matches) == 0:
                return None
            # Update the query node
            pattern_idx += 1
        return matches

    def _apply_impl(self, query, dframe, node, visited, matches):
        """Traverse the subgraph with the specified root, and collect all paths that match the query.

        Arguments:
            query (Query): the query being applied
            dframe (pandas.DataFrame): the DataFrame containing the metrics for the queried GraphFrame
            node (Node): the root node of the subgraph that is being queried
            visited (set): a set that keeps track of what nodes have been visited in the traversal to minimize the amount of work that is repeated
            matches (list): the list in which the final set of matches are stored
        """
        # If the node has already been visited (or is None for some
        # reason), skip it.
        if node is None or node._hatchet_nid in visited:
            return
        # Cache the node if it's not already cached
        if node._hatchet_nid not in self.search_cache:
            self._cache_node(node, query, dframe)
        # If the node matches the starting/root node of the query,
        # try to get all query matches in the subgraph rooted at
        # this node.
        if query.query_pattern[0][0] == "*":
            if 1 in self.search_cache[node._hatchet_nid]:
                sub_match = self._match_pattern(query, dframe, node, 1)
                if sub_match is not None:
                    matches.extend(sub_match)
        if 0 in self.search_cache[node._hatchet_nid]:
            sub_match = self._match_pattern(query, dframe, node, 0)
            if sub_match is not None:
                matches.extend(sub_match)
        # Note that the node is now visited.
        visited.add(node._hatchet_nid)
        # Continue the Depth First Search.
        for child in sorted(node.children, key=traversal_order):
            self._apply_impl(query, dframe, child, visited, matches)
