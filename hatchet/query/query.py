# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import sys
from typing import List, Tuple, Union

if sys.version_info >= (3, 9):
    from collections.abc import Callable, Iterator
else:
    from typing import Callable, Iterator

from .errors import InvalidQueryPath


class Query(object):
    """Class for representing and building Hatchet Call Path Queries"""

    def __init__(self) -> None:
        """Create new Query"""
        self.query_pattern: List[Tuple[Union[str, int], Callable]] = []

    def match(
        self, quantifier: Union[str, int] = ".", predicate: Callable = lambda row: True
    ) -> "Query":
        """Start a query with a root node described by the arguments.

        Arguments:
            quantifier (".", "*", "+", or int, optional): the quantifier for this node (tells how many graph nodes to match)
            predicate (Callable, optional): the predicate for this node (used to determine whether a graph node matches this query node)

        Returns:
            (Query): returns self so that this method can be chained with subsequent calls to "rel"/"relation"
        """
        if len(self.query_pattern) != 0:
            self.query_pattern = []
        self._add_node(quantifier, predicate)
        return self

    def rel(
        self, quantifier: Union[str, int] = ".", predicate: Callable = lambda row: True
    ) -> "Query":
        """Add a new node to the end of the query.

        Arguments:
            quantifier (".", "*", "+", or int, optional): the quantifier for this node (tells how many graph nodes to match)
            predicate (Callable, optional): the predicate for this node (used to determine whether a graph node matches this query node)

        Returns:
            (Query): returns self so that this method can be chained with subsequent calls to "rel"/"relation"
        """
        if len(self.query_pattern) == 0:
            raise InvalidQueryPath(
                "Queries in the base Query Language must start with a call to 'match'"
            )
        self._add_node(quantifier, predicate)
        return self

    def relation(
        self, quantifer: Union[str, int] = ".", predicate: Callable = lambda row: True
    ) -> "Query":
        """Alias to Query.rel. Add a new node to the end of the query.

        Arguments:
            quantifier (".", "*", "+", or int, optional): the quantifier for this node (tells how many graph nodes to match)
            predicate (Callable, optional): the predicate for this node (used to determine whether a graph node matches this query node)

        Returns:
            (Query): returns self so that this method can be chained with subsequent calls to "rel"/"relation"
        """
        return self.rel(quantifer, predicate)

    def __len__(self) -> int:
        """Returns the length of the query."""
        return len(self.query_pattern)

    def __iter__(self) -> Iterator[Tuple[Union[str, int], Callable]]:
        """Allows users to iterate over the Query like a list."""
        return iter(self.query_pattern)

    def _add_node(
        self, quantifer: Union[str, int] = ".", predicate: Callable = lambda row: True
    ) -> None:
        """Add a node to the query.

        Arguments:
            quantifier (".", "*", "+", or int, optional): the quantifier for this node (tells how many graph nodes to match)
            predicate (Callable, optional): the predicate for this node (used to determine whether a graph node matches this query node)
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
