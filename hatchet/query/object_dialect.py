# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from numbers import Real
import numpy as np
import pandas as pd
import re

from .errors import InvalidQueryPath, InvalidQueryFilter
from .query import Query


def _process_predicate(attr_filter):
    """Converts high-level API attribute filter to a lambda"""
    compops = ("<", ">", "==", ">=", "<=", "<>", "!=")  # ,
    # Currently not supported
    #           "is", "is not", "in", "not in")

    # This is a dict to work around Python's non-local variable
    # assignment rules.
    #
    # TODO: Replace this with the use of the "nonlocal" keyword
    #       once Python 2.7 support is dropped.
    first_no_drop_indices = {"val": True}

    def filter_series(df_row):
        def filter_single_series(df_row, key, single_value):
            if key == "depth":
                node = df_row.name
                if isinstance(single_value, str) and single_value.lower().startswith(
                    compops
                ):
                    return eval("{} {}".format(node._depth, single_value))
                if isinstance(single_value, Real):
                    # If the value for "depth" is -1, check if the node is a leaf
                    if single_value == -1:
                        return len(node.children) == 0
                    return node._depth == single_value
                raise InvalidQueryFilter(
                    "Attribute {} has a numeric type. Valid filters for this attribute are a string starting with a comparison operator or a real number.".format(
                        key
                    )
                )
            if key == "node_id":
                node = df_row.name
                if isinstance(single_value, str) and single_value.lower().startswith(
                    compops
                ):
                    return eval("{} {}".format(node._hatchet_nid, single_value))
                if isinstance(single_value, Real):
                    return node._hatchet_nid == single_value
                raise InvalidQueryFilter(
                    "Attribute {} has a numeric type. Valid filters for this attribute are a string starting with a comparison operator or a real number.".format(
                        key
                    )
                )
            if key not in df_row.keys():
                return False
            if isinstance(df_row[key], str):
                if not isinstance(single_value, str):
                    raise InvalidQueryFilter(
                        "Value for attribute {} must be a string.".format(key)
                    )
                return re.match(single_value + r"\Z", df_row[key]) is not None
            if isinstance(df_row[key], Real):
                if isinstance(single_value, str) and single_value.lower().startswith(
                    compops
                ):
                    # compare nan metric value to numeric query
                    # (e.g. np.nan > 5)
                    if pd.isnull(df_row[key]):
                        nan_str = "np.nan"
                        # compare nan metric value to nan query
                        # (e.g., np.nan == np.nan)
                        if nan_str in single_value:
                            return eval("pd.isnull({}) == True".format(nan_str))
                        return eval("{} {}".format(nan_str, single_value))
                    elif np.isinf(df_row[key]):
                        inf_str = "np.inf"
                        # compare inf metric value to inf query
                        # (e.g., np.inf == np.inf)
                        if inf_str in single_value:
                            return eval("np.isinf({}) == True".format(inf_str))
                        return eval("{} {}".format(inf_str, single_value))
                    else:
                        return eval("{} {}".format(df_row[key], single_value))

                if isinstance(single_value, Real):
                    return df_row[key] == single_value
                raise InvalidQueryFilter(
                    "Attribute {} has a numeric type. Valid filters for this attribute are a string starting with a comparison operator or a real number.".format(
                        key
                    )
                )
            raise InvalidQueryFilter(
                "Filter must be one of the following:\n  * A regex string for a String attribute\n  * A string starting with a comparison operator for a Numeric attribute\n  * A number for a Numeric attribute\n"
            )

        matches = True
        for k, v in attr_filter.items():
            try:
                _ = iter(v)
                # Manually raise TypeError if v is a string so that
                # the string is processed as a non-iterable
                if isinstance(v, str):
                    raise TypeError
            # Runs if v is not iterable (e.g., list, tuple, etc.)
            except TypeError:
                matches = matches and filter_single_series(df_row, k, v)
            else:
                for single_value in v:
                    matches = matches and filter_single_series(df_row, k, single_value)
        return matches

    def filter_dframe(df_row):
        if first_no_drop_indices["val"]:
            print("===================================================================")
            print("WARNING: You are performing a query without dropping index levels.")
            print("         This is a valid operation, but it will significantly")
            print("         increase the time it takes for this operation to complete.")
            print("         If you don't want the operation to take so long, call")
            print("         GraphFrame.drop_index_levels() before calling")
            print("         GraphFrame.filter()")
            print(
                "===================================================================\n"
            )
            first_no_drop_indices["val"] = False

        def filter_single_dframe(node, df_row, key, single_value):
            if key == "depth":
                if isinstance(single_value, str) and single_value.lower().startswith(
                    compops
                ):
                    return eval("{} {}".format(node._depth, single_value))
                if isinstance(single_value, Real):
                    return node._depth == single_value
                raise InvalidQueryFilter(
                    "Attribute {} has a numeric type. Valid filters for this attribute are a string starting with a comparison operator or a real number.".format(
                        key
                    )
                )
            if key == "node_id":
                if isinstance(single_value, str) and single_value.lower().startswith(
                    compops
                ):
                    return eval("{} {}".format(node._hatchet_nid, single_value))
                if isinstance(single_value, Real):
                    return node._hatchet_nid == single_value
                raise InvalidQueryFilter(
                    "Attribute {} has a numeric type. Valid filters for this attribute are a string starting with a comparison operator or a real number.".format(
                        key
                    )
                )
            if key not in df_row.columns:
                return False
            if df_row[key].apply(type).eq(str).all():
                if not isinstance(single_value, str):
                    raise InvalidQueryFilter(
                        "Value for attribute {} must be a string.".format(key)
                    )
                return (
                    df_row[key]
                    .apply(lambda x: re.match(single_value + r"\Z", x) is not None)
                    .any()
                )
            if df_row[key].apply(type).eq(Real).all():
                if isinstance(single_value, str) and single_value.lower().startswith(
                    compops
                ):
                    return (
                        df_row[key]
                        .apply(lambda x: eval("{} {}".format(x, single_value)))
                        .any()
                    )
                if isinstance(single_value, Real):
                    return df_row[key].apply(lambda x: x == single_value).any()
                raise InvalidQueryFilter(
                    "Attribute {} has a numeric type. Valid filters for this attribute are a string starting with a comparison operator or a real number.".format(
                        key
                    )
                )
            raise InvalidQueryFilter(
                "Filter must be one of the following:\n  * A regex string for a String attribute\n  * A string starting with a comparison operator for a Numeric attribute\n  * A number for a Numeric attribute\n"
            )

        matches = True
        node = df_row.name.to_frame().index[0][0]
        for k, v in attr_filter.items():
            try:
                _ = iter(v)
                if isinstance(v, str):
                    raise TypeError
            except TypeError:
                matches = matches and filter_single_dframe(node, df_row, k, v)
            else:
                for single_value in v:
                    matches = matches and filter_single_dframe(
                        node, df_row, k, single_value
                    )
        return matches

    def filter_choice(df_row):
        if isinstance(df_row, pd.DataFrame):
            return filter_dframe(df_row)
        return filter_series(df_row)

    return filter_choice if attr_filter != {} else lambda row: True


class ObjectQuery(Query):

    """Class for representing and parsing queries using the Object-based dialect."""

    def __init__(self, query):
        """Builds a new ObjectQuery from an instance of the Object-based dialect syntax.

        Arguments:
            query (list): the Object-based dialect query to parse and store
        """
        super().__init__()
        assert isinstance(query, list)
        for qnode in query:
            if isinstance(qnode, dict):
                self._add_node(predicate=_process_predicate(qnode))
            elif isinstance(qnode, str) or isinstance(qnode, int):
                self._add_node(quantifer=qnode)
            elif isinstance(qnode, tuple):
                assert isinstance(qnode[1], dict)
                if isinstance(qnode[0], str) or isinstance(qnode[0], int):
                    self._add_node(qnode[0], _process_predicate(qnode[1]))
                else:
                    raise InvalidQueryPath(
                        "The first value of a tuple entry in a path must be either a string or integer."
                    )
            else:
                raise InvalidQueryPath(
                    "A query path must be a list containing String, Integer, Dict, or Tuple elements"
                )
