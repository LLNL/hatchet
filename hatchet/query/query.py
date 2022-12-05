# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from .errors import InvalidQueryPath


class Query:

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
