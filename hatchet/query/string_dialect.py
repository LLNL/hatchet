# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from numbers import Real
import re
import sys
import pandas as pd  # noqa: F401
from pandas.api.types import is_numeric_dtype, is_string_dtype  # noqa: F401
import numpy as np  # noqa: F401
from textx import metamodel_from_str
from textx.exceptions import TextXError
import warnings

from .errors import InvalidQueryPath, InvalidQueryFilter, RedundantQueryFilterWarning
from .query import Query


# PEG grammar for the String-based dialect
CYPHER_GRAMMAR = u"""
FullQuery: path_expr=MatchExpr(cond_expr=WhereExpr)?;
MatchExpr: 'MATCH' path=PathQuery;
PathQuery: '(' nodes=NodeExpr ')'('->' '(' nodes=NodeExpr ')')*;
NodeExpr: ((wcard=INT | wcard=STRING) ',' name=ID) | (wcard=INT | wcard=STRING) |  name=ID;
WhereExpr: 'WHERE' ConditionExpr;
ConditionExpr: conditions+=CompoundCond;
CompoundCond: UnaryCond | BinaryCond;
BinaryCond: AndCond | OrCond;
AndCond: 'AND' subcond=UnaryCond;
OrCond: 'OR' subcond=UnaryCond;
UnaryCond: NotCond | SingleCond;
NotCond: 'NOT' subcond=SingleCond;
SingleCond: StringCond | NumberCond | NoneCond | NotNoneCond | LeafCond | NotLeafCond;
NoneCond: name=ID '.' prop=STRING 'IS NONE';
NotNoneCond: name=ID '.' prop=STRING 'IS NOT NONE';
LeafCond: name=ID 'IS LEAF';
NotLeafCond: name=ID 'IS NOT LEAF';
StringCond: StringEq | StringStartsWith | StringEndsWith | StringContains | StringMatch;
StringEq: name=ID '.' prop=STRING '=' val=STRING;
StringStartsWith: name=ID '.' prop=STRING 'STARTS WITH' val=STRING;
StringEndsWith: name=ID '.' prop=STRING 'ENDS WITH' val=STRING;
StringContains: name=ID '.' prop=STRING 'CONTAINS' val=STRING;
StringMatch: name=ID '.' prop=STRING '=~' val=STRING;
NumberCond: NumEq | NumLt | NumGt | NumLte | NumGte | NumNan | NumNotNan | NumInf | NumNotInf;
NumEq: name=ID '.' prop=STRING '=' val=NUMBER;
NumLt: name=ID '.' prop=STRING '<' val=NUMBER;
NumGt: name=ID '.' prop=STRING '>' val=NUMBER;
NumLte: name=ID '.' prop=STRING '<=' val=NUMBER;
NumGte: name=ID '.' prop=STRING '>=' val=NUMBER;
NumNan: name=ID '.' prop=STRING 'IS NAN';
NumNotNan: name=ID '.' prop=STRING 'IS NOT NAN';
NumInf: name=ID '.' prop=STRING 'IS INF';
NumNotInf: name=ID '.' prop=STRING 'IS NOT INF';
"""

# TextX metamodel for the String-based dialect
cypher_query_mm = metamodel_from_str(CYPHER_GRAMMAR)


def cname(obj):
    """Utility function to get the name of the rule represented by the input"""
    return obj.__class__.__name__


def filter_check_types(type_check, df_row, filt_lambda):
    """Utility function used in String-based predicates
       to make sure the node data used in the actual boolean predicate
       is of the correct type.

    Arguments:
        type_check (str): a string containing a boolean Python expression used to validate node data typing
        df_row (pandas.Series or pandas.DataFrame): the row (or sub-DataFrame) representing the data for the current node being tested
        filt_lambda (Callable): the lambda used to actually confirm whether the node satisfies the predicate

    Returns:
        (bool): True if the node satisfies the predicate. False otherwise
    """
    try:
        if type_check == "" or eval(type_check):
            return filt_lambda(df_row)
        else:
            raise InvalidQueryFilter("Type mismatch in filter")
    except KeyError:
        return False


class StringQuery(Query):

    """Class for representing and parsing queries using the String-based dialect."""

    def __init__(self, cypher_query, multi_index_mode="off"):
        """Builds a new StringQuery object representing a query in the String-based dialect.

        Arguments:
            cypher_query (str): a query in the String-based dialect
        """
        if sys.version_info[0] == 2:
            super(StringQuery, self).__init__()
        else:
            super().__init__()
        assert multi_index_mode in ["off", "all", "any"]
        self.multi_index_mode = multi_index_mode
        model = None
        try:
            model = cypher_query_mm.model_from_str(cypher_query)
        except TextXError as e:
            # TODO Change to a "raise-from" expression when Python 2.7 support is dropped
            raise InvalidQueryPath(
                "Invalid String Dialect Query Detected. Parser Error Message: {}".format(
                    e.message
                )
            )
        self.wcards = []
        self.wcard_pos = {}
        self._parse_path(model.path_expr)
        self.filters = [[] for _ in self.wcards]
        self._parse_conditions(model.cond_expr)
        self.lambda_filters = [None for _ in self.wcards]
        self._build_lambdas()
        self._build_query()

    def _build_query(self):
        """Builds the entire query using 'match' and 'rel' using
        the pre-parsed quantifiers and predicates.
        """
        for i in range(0, len(self.wcards)):
            wcard = self.wcards[i][0]
            # TODO Remove this when Python 2.7 support is dropped.
            if sys.version_info[0] == 2 and not isinstance(wcard, Real):
                wcard = wcard.encode("ascii", "ignore")
            filt_str = self.lambda_filters[i]
            if filt_str is None:
                if i == 0:
                    self.match(quantifier=wcard)
                else:
                    self.rel(quantifier=wcard)
            else:
                if i == 0:
                    self.match(quantifier=wcard, predicate=eval(filt_str))
                else:
                    self.rel(quantifier=wcard, predicate=eval(filt_str))

    def _build_lambdas(self):
        """Constructs the final predicate lambdas from the pre-parsed
        predicate information.
        """
        for i in range(0, len(self.wcards)):
            n = self.wcards[i]
            if n[1] != "":
                bool_expr = ""
                type_check = ""
                for j, cond in enumerate(self.filters[i]):
                    if cond[0] is not None:
                        bool_expr += " {}".format(cond[0])
                    bool_expr += " {}".format(cond[1])
                    if cond[2] is not None:
                        if j == 0:
                            type_check += " {}".format(cond[2])
                        else:
                            type_check += " and {}".format(cond[2])
                bool_expr = "lambda df_row: {}".format(bool_expr)
                bool_expr = (
                    'lambda df_row: filter_check_types("{}", df_row, {})'.format(
                        type_check, bool_expr
                    )
                )
                self.lambda_filters[i] = bool_expr

    def _parse_path(self, path_obj):
        """Parses the MATCH statement of a String-based query."""
        nodes = path_obj.path.nodes
        idx = len(self.wcards)
        for n in nodes:
            new_node = [n.wcard, n.name]
            if n.wcard is None or n.wcard == "" or n.wcard == 0:
                new_node[0] = "."
            self.wcards.append(new_node)
            if n.name != "":
                self.wcard_pos[n.name] = idx
            idx += 1

    def _parse_conditions(self, cond_expr):
        """Top level function for parsing the WHERE statement of
        a String-based query.
        """
        conditions = cond_expr.conditions
        for cond in conditions:
            converted_condition = None
            if self._is_unary_cond(cond):
                converted_condition = self._parse_unary_cond(cond)
            elif self._is_binary_cond(cond):
                converted_condition = self._parse_binary_cond(cond)
            else:
                raise RuntimeError("Bad Condition")
            self.filters[self.wcard_pos[converted_condition[1]]].append(
                [converted_condition[0], converted_condition[2], converted_condition[3]]
            )
        for i in range(0, len(self.filters)):
            if len(self.filters[i]) > 0:
                if self.filters[i][0][0] != "not":
                    self.filters[i][0][0] = None

    def _is_unary_cond(self, obj):
        """Detect whether a predicate is unary or not."""
        if (
            cname(obj) == "NotCond"
            or self._is_str_cond(obj)
            or self._is_num_cond(obj)
            or cname(obj) in ["NoneCond", "NotNoneCond", "LeafCond", "NotLeafCond"]
        ):
            return True
        return False

    def _is_binary_cond(self, obj):
        """Detect whether a predicate is binary or not."""
        if cname(obj) in ["AndCond", "OrCond"]:
            return True
        return False

    def _parse_binary_cond(self, obj):
        """Top level function for parsing binary predicates."""
        if cname(obj) == "AndCond":
            return self._parse_and_cond(obj)
        if cname(obj) == "OrCond":
            return self._parse_or_cond(obj)
        raise RuntimeError("Bad Binary Condition")

    def _parse_or_cond(self, obj):
        """Top level function for parsing predicates combined with logical OR."""
        converted_subcond = self._parse_unary_cond(obj.subcond)
        converted_subcond[0] = "or"
        return converted_subcond

    def _parse_and_cond(self, obj):
        """Top level function for parsing predicates combined with logical AND."""
        converted_subcond = self._parse_unary_cond(obj.subcond)
        converted_subcond[0] = "and"
        return converted_subcond

    def _parse_unary_cond(self, obj):
        """Top level function for parsing unary predicates."""
        if cname(obj) == "NotCond":
            return self._parse_not_cond(obj)
        return self._parse_single_cond(obj)

    def _parse_not_cond(self, obj):
        """Parse predicates containing the logical NOT operator."""
        converted_subcond = self._parse_single_cond(obj.subcond)
        converted_subcond[2] = "not {}".format(converted_subcond[2])
        return converted_subcond

    def _run_method_based_on_multi_idx_mode(self, method_name, obj):
        real_method_name = method_name
        if self.multi_index_mode != "off":
            real_method_name = method_name + "_multi_idx"
        method = eval("StringQuery.{}".format(real_method_name))
        return method(self, obj)

    def _parse_single_cond(self, obj):
        """Top level function for parsing individual numeric or string predicates."""
        if self._is_str_cond(obj):
            return self._parse_str(obj)
        if self._is_num_cond(obj):
            return self._parse_num(obj)
        if cname(obj) == "NoneCond":
            return self._run_method_based_on_multi_idx_mode("_parse_none", obj)
        if cname(obj) == "NotNoneCond":
            return self._run_method_based_on_multi_idx_mode("_parse_not_none", obj)
        if cname(obj) == "LeafCond":
            return self._run_method_based_on_multi_idx_mode("_parse_leaf", obj)
        if cname(obj) == "NotLeafCond":
            return self._run_method_based_on_multi_idx_mode("_parse_not_leaf", obj)
        raise RuntimeError("Bad Single Condition")

    def _parse_none(self, obj):
        """Parses 'property IS NONE'."""
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "df_row.name._depth is None",
                None,
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid is None",
                None,
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] is None'.format(obj.prop),
            None,
        ]

    def _add_aggregation_call_to_multi_idx_predicate(self, predicate):
        if self.multi_index_mode == "any":
            return predicate + ".any()"
        return predicate + ".all()"

    def _parse_none_multi_idx(self, obj):
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth is None",
                None,
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid is None",
                None,
            ]
        if self.multi_index_mode == "any":
            return [
                None,
                obj.name,
                "df_row['{}'].apply(lambda elem: elem is None).any()".format(obj.prop),
                None,
            ]
        # if self.multi_index_mode == "all":
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                "df_row['{}'].apply(lambda elem: elem is None)".format(obj.prop)
            ),
            None,
        ]

    def _parse_not_none(self, obj):
        """Parses 'property IS NOT NONE'."""
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "df_row.name._depth is not None",
                None,
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid is not None",
                None,
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] is not None'.format(obj.prop),
            None,
        ]

    def _parse_not_none_multi_idx(self, obj):
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth is not None",
                None,
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid is not None",
                None,
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                "df_row['{}'].apply(lambda elem: elem is not None)".format(obj.prop)
            ),
            None,
        ]

    def _parse_leaf(self, obj):
        """Parses 'node IS LEAF'."""
        return [
            None,
            obj.name,
            "len(df_row.name.children) == 0",
            None,
        ]

    def _parse_leaf_multi_idx(self, obj):
        return [
            None,
            obj.name,
            "len(df_row.index.get_level_values('node')[0].children) == 0",
            None,
        ]

    def _parse_not_leaf(self, obj):
        """Parses 'node IS NOT LEAF'."""
        return [
            None,
            obj.name,
            "len(df_row.name.children) > 0",
            None,
        ]

    def _parse_not_leaf_multi_idx(self, obj):
        return [
            None,
            obj.name,
            "len(df_row.index.get_level_values('node')[0].children) > 0",
            None,
        ]

    def _is_str_cond(self, obj):
        """Determines whether a predicate is for string data."""
        if cname(obj) in [
            "StringEq",
            "StringStartsWith",
            "StringEndsWith",
            "StringContains",
            "StringMatch",
        ]:
            return True
        return False

    def _is_num_cond(self, obj):
        """Determines whether a predicate is for numeric data."""
        if cname(obj) in [
            "NumEq",
            "NumLt",
            "NumGt",
            "NumLte",
            "NumGte",
            "NumNan",
            "NumNotNan",
            "NumInf",
            "NumNotInf",
        ]:
            return True
        return False

    def _parse_str(self, obj):
        """Function that redirects processing of string predicates
        to the correct function.
        """
        if cname(obj) == "StringEq":
            return self._run_method_based_on_multi_idx_mode("_parse_str_eq", obj)
        if cname(obj) == "StringStartsWith":
            return self._run_method_based_on_multi_idx_mode(
                "_parse_str_starts_with", obj
            )
        if cname(obj) == "StringEndsWith":
            return self._run_method_based_on_multi_idx_mode("_parse_str_ends_with", obj)
        if cname(obj) == "StringContains":
            return self._run_method_based_on_multi_idx_mode("_parse_str_contains", obj)
        if cname(obj) == "StringMatch":
            return self._run_method_based_on_multi_idx_mode("_parse_str_match", obj)
        raise RuntimeError("Bad String Op Class")

    def _parse_str_eq(self, obj):
        """Processes string equivalence predicates."""
        return [
            None,
            obj.name,
            'df_row["{}"] == "{}"'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], str)".format(obj.prop),
        ]

    def _parse_str_eq_multi_idx(self, obj):
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem == "{}")'.format(
                    obj.prop, obj.val
                )
            ),
            "is_string_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_str_starts_with(self, obj):
        """Processes string 'startswith' predicates."""
        return [
            None,
            obj.name,
            'df_row["{}"].startswith("{}")'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], str)".format(obj.prop),
        ]

    def _parse_str_starts_with_multi_idx(self, obj):
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem.startswith("{}"))'.format(
                    obj.prop, obj.val
                )
            ),
            "is_string_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_str_ends_with(self, obj):
        """Processes string 'endswith' predicates."""
        return [
            None,
            obj.name,
            'df_row["{}"].endswith("{}")'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], str)".format(obj.prop),
        ]

    def _parse_str_ends_with_multi_idx(self, obj):
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem.endswith("{}"))'.format(
                    obj.prop, obj.val
                )
            ),
            "is_string_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_str_contains(self, obj):
        """Processes string 'contains' predicates."""
        return [
            None,
            obj.name,
            '"{}" in df_row["{}"]'.format(obj.val, obj.prop),
            "isinstance(df_row['{}'], str)".format(obj.prop),
        ]

    def _parse_str_contains_multi_idx(self, obj):
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: "{}" in elem)'.format(
                    obj.prop, obj.val
                )
            ),
            "is_string_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_str_match(self, obj):
        """Processes string regex match predicates."""
        return [
            None,
            obj.name,
            're.match("{}", df_row["{}"]) is not None'.format(obj.val, obj.prop),
            "isinstance(df_row['{}'], str)".format(obj.prop),
        ]

    def _parse_str_match_multi_idx(self, obj):
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: re.match("{}", elem) is not None)'.format(
                    obj.prop, obj.val
                )
            ),
            "is_string_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num(self, obj):
        """Function that redirects processing of numeric predicates
        to the correct function.
        """
        if cname(obj) == "NumEq":
            return self._run_method_based_on_multi_idx_mode("_parse_num_eq", obj)
        if cname(obj) == "NumLt":
            return self._run_method_based_on_multi_idx_mode("_parse_num_lt", obj)
        if cname(obj) == "NumGt":
            return self._run_method_based_on_multi_idx_mode("_parse_num_gt", obj)
        if cname(obj) == "NumLte":
            return self._run_method_based_on_multi_idx_mode("_parse_num_lte", obj)
        if cname(obj) == "NumGte":
            return self._run_method_based_on_multi_idx_mode("_parse_num_gte", obj)
        if cname(obj) == "NumNan":
            return self._run_method_based_on_multi_idx_mode("_parse_num_nan", obj)
        if cname(obj) == "NumNotNan":
            return self._run_method_based_on_multi_idx_mode("_parse_num_not_nan", obj)
        if cname(obj) == "NumInf":
            return self._run_method_based_on_multi_idx_mode("_parse_num_inf", obj)
        if cname(obj) == "NumNotInf":
            return self._run_method_based_on_multi_idx_mode("_parse_num_not_inf", obj)
        raise RuntimeError("Bad Number Op Class")

    def _parse_num_eq(self, obj):
        """Processes numeric equivalence predicates."""
        if obj.prop == "depth":
            if obj.val == -1:
                return [
                    None,
                    obj.name,
                    "len(df_row.name.children) == 0",
                    None,
                ]
            elif obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.name._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._depth == {}".format(obj.val),
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.name._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid == {}".format(obj.val),
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] == {}'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_eq_multi_idx(self, obj):
        if obj.prop == "depth":
            if obj.val == -1:
                return [
                    None,
                    obj.name,
                    "len(df_row.index.get_level_values('node')[0].children) == 0",
                    None,
                ]
            elif obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth == {}".format(obj.val),
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid == {}".format(
                    obj.val
                ),
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem == {})'.format(obj.prop, obj.val)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_lt(self, obj):
        """Processes numeric less-than predicates."""
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.name._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._depth < {}".format(obj.val),
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.name._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid < {}".format(obj.val),
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] < {}'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_lt_multi_idx(self, obj):
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth < {}".format(obj.val),
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid < {}".format(
                    obj.val
                ),
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem < {})'.format(obj.prop, obj.val)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_gt(self, obj):
        """Processes numeric greater-than predicates."""
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.name._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._depth > {}".format(obj.val),
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.name._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid > {}".format(obj.val),
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] > {}'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_gt_multi_idx(self, obj):
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth > {}".format(obj.val),
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid > {}".format(
                    obj.val
                ),
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem > {})'.format(obj.prop, obj.val)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_lte(self, obj):
        """Processes numeric less-than-or-equal-to predicates."""
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.name._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._depth <= {}".format(obj.val),
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.name._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid <= {}".format(obj.val),
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] <= {}'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_lte_multi_idx(self, obj):
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth <= {}".format(obj.val),
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be false.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "False",
                    "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid <= {}".format(
                    obj.val
                ),
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem <= {})'.format(obj.prop, obj.val)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_gte(self, obj):
        """Processes numeric greater-than-or-equal-to predicates."""
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.name._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._depth >= {}".format(obj.val),
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.name._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.name._hatchet_nid >= {}".format(obj.val),
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'df_row["{}"] >= {}'.format(obj.prop, obj.val),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_gte_multi_idx(self, obj):
        if obj.prop == "depth":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'depth' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._depth >= {}".format(obj.val),
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            if obj.val < 0:
                warnings.warn(
                    """
                    The 'node_id' property of a Node is strictly non-negative.
                    This condition will always be true.
                    The statement that triggered this warning is:
                    {}
                    """.format(
                        obj
                    ),
                    RedundantQueryFilterWarning,
                )
                return [
                    None,
                    obj.name,
                    "True",
                    "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
                ]
            return [
                None,
                obj.name,
                "df_row.index.get_level_values('node')[0]._hatchet_nid >= {}".format(
                    obj.val
                ),
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'df_row["{}"].apply(lambda elem: elem >= {})'.format(obj.prop, obj.val)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_nan(self, obj):
        """Processes predicates that check for NaN."""
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "pd.isna(df_row.name._depth)",
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "pd.isna(df_row.name._hatchet_nid)",
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'pd.isna(df_row["{}"])'.format(obj.prop),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_nan_multi_idx(self, obj):
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "pd.isna(df_row.index.get_level_values('node')[0]._depth)",
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "pd.isna(df_row.index.get_level_values('node')[0]._hatchet_nid)",
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'pd.isna(df_row["{}"])'.format(obj.prop)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_not_nan(self, obj):
        """Processes predicates that check for NaN."""
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "not pd.isna(df_row.name._depth)",
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "not pd.isna(df_row.name._hatchet_nid)",
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'not pd.isna(df_row["{}"])'.format(obj.prop),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_not_nan_multi_idx(self, obj):
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "not pd.isna(df_row.index.get_level_values('node')[0]._depth)",
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "not pd.isna(df_row.index.get_level_values('node')[0]._hatchet_nid)",
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'not pd.isna(df_row["{}"])'.format(obj.prop)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_inf(self, obj):
        """Processes predicates that check for Infinity."""
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "np.isinf(df_row.name._depth)",
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "np.isinf(df_row.name._hatchet_nid)",
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'np.isinf(df_row["{}"])'.format(obj.prop),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_inf_multi_idx(self, obj):
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "np.isinf(df_row.index.get_level_values('node')[0]._depth)",
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "np.isinf(df_row.index.get_level_values('node')[0]._hatchet_nid)",
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'np.isinf(df_row["{}"])'.format(obj.prop)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]

    def _parse_num_not_inf(self, obj):
        """Processes predicates that check for not-Infinity."""
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "not np.isinf(df_row.name._depth)",
                "isinstance(df_row.name._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "not np.isinf(df_row.name._hatchet_nid)",
                "isinstance(df_row.name._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            'not np.isinf(df_row["{}"])'.format(obj.prop),
            "isinstance(df_row['{}'], Real)".format(obj.prop),
        ]

    def _parse_num_not_inf_multi_idx(self, obj):
        if obj.prop == "depth":
            return [
                None,
                obj.name,
                "not np.isinf(df_row.index.get_level_values('node')[0]._depth)",
                "isinstance(df_row.index.get_level_values('node')[0]._depth, Real)",
            ]
        if obj.prop == "node_id":
            return [
                None,
                obj.name,
                "not np.isinf(df_row.index.get_level_values('node')[0]._hatchet_nid)",
                "isinstance(df_row.index.get_level_values('node')[0]._hatchet_nid, Real)",
            ]
        return [
            None,
            obj.name,
            self._add_aggregation_call_to_multi_idx_predicate(
                'not np.isinf(df_row["{}"])'.format(obj.prop)
            ),
            "is_numeric_dtype(df_row['{}'])".format(obj.prop),
        ]


def parse_string_dialect(query_str, multi_index_mode="off"):
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
        full_query = None
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
            next_query = StringQuery(next_query, multi_index_mode)
            # Add the next query to the full query using the compound operator
            # currently being considered
            if op == "AND":
                full_query = full_query & next_query
            elif op == "OR":
                full_query = full_query | next_query
            else:
                full_query = full_query ^ next_query
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
            next_query = parse_string_dialect(query_list[i + 1])
            # Add the next query to the full query using the compound operator
            # currently being considered
            if op == "AND":
                full_query = full_query & next_query
            elif op == "OR":
                full_query = full_query | next_query
            else:
                full_query = full_query ^ next_query
        return full_query
