# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from abc import abstractmethod, ABC

import sys
import warnings
from typing import List, Optional, Union, cast, TYPE_CHECKING

if sys.version_info >= (3, 9):
    from collections.abc import Callable
else:
    from typing import Callable


from ..node import Node
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
from .engine import QueryEngine
from .errors import BadNumberNaryQueryArgs, InvalidQueryPath

if TYPE_CHECKING:
    from ..graphframe import GraphFrame


# QueryEngine object for running the legacy "apply" methods
COMPATABILITY_ENGINE: QueryEngine = QueryEngine()


class AbstractQuery(ABC):
    """Base class for all 'old-style' queries."""

    @abstractmethod
    def apply(self, gf: "GraphFrame") -> List[Node]:
        pass

    def __and__(self, other: "AbstractQuery") -> "AndQuery":
        """Create a new AndQuery using this query and another.

        Arguments:
            other (AbstractQuery): the other query to use in constructing the AndQuery

        Returns:
            (AndQuery): a new AndQuery that performs the AND of the results of both queries
        """
        return AndQuery(self, other)

    def __or__(self, other: "AbstractQuery") -> "OrQuery":
        """Create a new OrQuery using this query and another.

        Arguments:
            other (AbstractQuery): the other query to use in constructing the OrQuery

        Returns:
            (OrQuery): a new OrQuery that performs the OR of the results of both queries
        """
        return OrQuery(self, other)

    def __xor__(self, other: "AbstractQuery") -> "XorQuery":
        """Create a new XorQuery using this query and another.

        Arguments:
            other (AbstractQuery): the other query to use in constructing the XorQuery

        Returns:
            (XorQuery): a new XorQuery that performs the XOR of the results of both queries
        """
        return XorQuery(self, other)

    def __invert__(self) -> "NotQuery":
        """Create a new NotQuery using this query.

        Returns:
            (NotQuery): a new NotQuery that inverts the results of this query
        """
        return NotQuery(self)

    @abstractmethod
    def _get_new_query(self) -> Union[Query, CompoundQuery]:
        pass


class NaryQuery(AbstractQuery):
    """Base class for all compound queries that act on
    and merged N separate subqueries."""

    def __init__(self, *args) -> None:
        """Create a new NaryQuery object.

        Arguments:
            *args (AbstractQuery, str, or list): the subqueries to be performed
        """
        self.compat_subqueries: List[
            Union[QueryMatcher, CypherQuery, AbstractQuery, Query, CompoundQuery]
        ] = []
        if isinstance(args[0], tuple) and len(args) == 1:
            args = args[0]
        for query in args:
            if isinstance(query, list):
                self.compat_subqueries.append(QueryMatcher(query))
            elif isinstance(query, str):
                self.compat_subqueries.append(CypherQuery(query))
            elif issubclass(type(query), AbstractQuery):
                self.compat_subqueries.append(query)
            elif issubclass(type(query), Query) or issubclass(
                type(query), CompoundQuery
            ):
                self.compat_subqueries.append(query)
            else:
                raise TypeError(
                    "Subqueries for NaryQuery must be either a\
                     high-level query or a subclass of AbstractQuery"
                )

    def apply(self, gf: "GraphFrame") -> List[Node]:
        """Applies the query to the specified GraphFrame.

        Arguments:
            gf (GraphFrame): the GraphFramme on which to apply the query

        Results:
            (list): A list of nodes representing the result of the query
        """
        true_query = self._get_new_query()
        return COMPATABILITY_ENGINE.apply(true_query, gf.graph, gf.dataframe)

    def _get_new_query(self) -> Union[Query, CompoundQuery]:
        """Gets all the underlying 'new-style' queries in this object.

        Returns:
            (List[Union[Query, CompoundQuery]]): a list of all the underlying 'new-style' queries in this object
        """
        true_subqueries = []
        for subq in self.compat_subqueries:
            if issubclass(type(subq), AbstractQuery):
                true_subq = cast(AbstractQuery, subq)._get_new_query()
            else:
                true_subq = cast(Union[Query, CompoundQuery], subq)
            true_subqueries.append(true_subq)
        return self._convert_to_new_query(true_subqueries)

    @abstractmethod
    def _convert_to_new_query(
        self, subqueries: List[Union[Query, CompoundQuery]]
    ) -> CompoundQuery:
        pass


class AndQuery(NaryQuery):
    """Compound query that returns the intersection of the results
    of the subqueries."""

    def __init__(self, *args) -> None:
        """Create a new AndQuery object.

        Arguments:
            *args (AbstractQuery, str, or list): the subqueries to be performed
        """
        warnings.warn(
            "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries (e.g., hatchet.query.ConjunctionQuery) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if sys.version_info[0] == 2:
            super(AndQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 2:
            raise BadNumberNaryQueryArgs("AndQuery requires 2 or more subqueries")

    def _convert_to_new_query(
        self, subqueries: List[Union[Query, CompoundQuery]]
    ) -> CompoundQuery:
        return ConjunctionQuery(*subqueries)


"""Alias of AndQuery"""
IntersectionQuery = AndQuery


class OrQuery(NaryQuery):
    """Compound query that returns the union of the results
    of the subqueries"""

    def __init__(self, *args) -> None:
        """Create a new OrQuery object.

        Arguments:
            *args (AbstractQuery, str, or list): the subqueries to be performed
        """
        warnings.warn(
            "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries (e.g., hatchet.query.DisjunctionQuery) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if sys.version_info[0] == 2:
            super(OrQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 2:
            raise BadNumberNaryQueryArgs("OrQuery requires 2 or more subqueries")

    def _convert_to_new_query(
        self, subqueries: List[Union[Query, CompoundQuery]]
    ) -> CompoundQuery:
        return DisjunctionQuery(*subqueries)


"""Alias of OrQuery"""
UnionQuery = OrQuery


class XorQuery(NaryQuery):
    """Compound query that returns the symmetric difference
    (i.e., set-based XOR) of the results of the subqueries"""

    def __init__(self, *args) -> None:
        """Create a new XorQuery object.

        Arguments:
            *args (AbstractQuery, str, or list): the subqueries to be performed
        """
        warnings.warn(
            "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries (e.g., hatchet.query.ExclusiveDisjunctionQuery) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if sys.version_info[0] == 2:
            super(XorQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 2:
            raise BadNumberNaryQueryArgs("XorQuery requires 2 or more subqueries")

    def _convert_to_new_query(
        self, subqueries: List[Union[Query, CompoundQuery]]
    ) -> CompoundQuery:
        return ExclusiveDisjunctionQuery(*subqueries)


"""Alias of XorQuery"""
SymDifferenceQuery = XorQuery


class NotQuery(NaryQuery):
    """Compound query that returns all nodes in the GraphFrame that
    are not returned from the subquery."""

    def __init__(self, *args) -> None:
        """Create a new NotQuery object.

        Arguments:
            *args (AbstractQuery, str, or list): the subquery to be performed
        """
        warnings.warn(
            "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries (e.g., hatchet.query.NegationQuery) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if sys.version_info[0] == 2:
            super(NotQuery, self).__init__(*args)
        else:
            super().__init__(*args)
        if len(self.compat_subqueries) < 1:
            raise BadNumberNaryQueryArgs("NotQuery requires exactly 1 subquery")

    def _convert_to_new_query(
        self, subqueries: List[Union[Query, CompoundQuery]]
    ) -> CompoundQuery:
        return NegationQuery(*subqueries)


class QueryMatcher(AbstractQuery):
    """Processes and applies base syntax queries and Object-based queries to GraphFrames."""

    def __init__(self, query: Optional[Union[List, Query]] = None) -> None:
        """Create a new QueryMatcher object.

        Arguments:
            query (list, optional): if provided, convert the Object-based query
                                    into its internal representation
        """
        warnings.warn(
            "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries instead. For QueryMatcher, the equivalent new-style queries are hatchet.query.Query for base-syntax queries and hatchet.query.ObjectQuery for the object-dialect.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.true_query: Optional[Union[Query, CompoundQuery]] = None
        if query is None:
            self.true_query = Query()
        elif isinstance(query, list):
            self.true_query = ObjectQuery(query)
        else:
            raise InvalidQueryPath("Provided query is not a valid object dialect query")

    def match(
        self,
        wildcard_spec: Union[str, int] = ".",
        filter_func: Callable = lambda row: True,
    ) -> "QueryMatcher":
        """Start a query with a root node described by the arguments.

        Arguments:
            wildcard_spec (str, optional): the wildcard status of the node
            filter_func (Callable, optional): a callable acceepting only a row from a pandas DataFrame
                                              that is used to filter this node in the query

        Returns:
            (QueryMatcher): the instance of the class that called this function
        """
        assert isinstance(self.true_query, Query)
        self.true_query.match(wildcard_spec, filter_func)
        return self

    def rel(
        self,
        wildcard_spec: Union[str, int] = ".",
        filter_func: Callable = lambda row: True,
    ) -> "QueryMatcher":
        """Add another edge and node to the query.

        Arguments:
            wildcard_spec (str, optional): the wildcard status of the node
            filter_func (Callable, optional): a callable acceepting only a row from a pandas DataFrame
                                              that is used to filter this node in the query

        Returns:
            (QueryMatcher): the instance of the class that called this function
        """
        assert isinstance(self.true_query, Query)
        self.true_query.rel(wildcard_spec, filter_func)
        return self

    def apply(self, gf: "GraphFrame") -> List[Node]:
        """Apply the query to a GraphFrame.

        Arguments:
            gf (GraphFrame): the GraphFrame on which to apply the query

        Returns:
            (list): A list representing the set of nodes from paths that match this query
        """
        return COMPATABILITY_ENGINE.apply(self.true_query, gf.graph, gf.dataframe)

    def _get_new_query(self) -> Union[Query, CompoundQuery]:
        """Get all the underlying 'new-style' query in this object.

        Returns:
            (Query or ObjectQuery): the underlying 'new-style' query in this object
        """
        return self.true_query


class CypherQuery(QueryMatcher):
    """Processes and applies Strinb-based queries to GraphFrames."""

    def __init__(self, cypher_query: str) -> None:
        """Create a new Cypher object.

        Arguments:
            cypher_query (str): the String-based query
        """
        warnings.warn(
            "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries instead. For CypherQuery, the equivalent new-style query is hatchet.query.StringQuery.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.true_query = parse_string_dialect(cypher_query)

    def _get_new_query(self) -> Union[Query, CompoundQuery]:
        """Gets all the underlying 'new-style' queries in this object.

        Returns:
            (List[Union[Query, CompoundQuery]]): a list of all the underlying 'new-style' queries in this object
        """
        return self.true_query


def parse_cypher_query(cypher_query: str) -> CypherQuery:
    """Parse all types of String-based queries, including multi-queries that
    leverage the curly brace delimiters.

    Arguments:
        cypher_query (str): the String-based query to be parsed

    Returns:
        (CypherQuery): a Hatchet query for this String-based query
    """
    warnings.warn(
        "Old-style queries are deprecated as of Hatchet 2023.1.0 and will be removed in the future. Please use new-style queries (e.g., hatchet.query.parse_string_dialect) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return CypherQuery(cypher_query)
