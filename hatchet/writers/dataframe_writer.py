# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from hatchet.node import Node
from hatchet.graphframe import GraphFrame
import pandas as pd

from abc import abstractmethod, ABC


def _get_node_from_df_iloc(df: pd.DataFrame, ind: int) -> Node:
    node = None
    if isinstance(df.iloc[ind].name, tuple):
        node = df.iloc[ind].name[0]
    elif isinstance(df.iloc[ind].name, Node):
        node = df.iloc[ind].name
    else:
        raise InvalidDataFrameIndex(
            "DataFrame index elements must be either a tuple or a Node"
        )
    return node


def _fill_children_and_parents(dump_df: pd.DataFrame) -> pd.DataFrame:
    dump_df["children"] = [[] for _ in range(len(dump_df))]
    dump_df["parents"] = [[] for _ in range(len(dump_df))]
    for i in range(len(dump_df)):
        node = _get_node_from_df_iloc(dump_df, i)
        dump_df.iat[i, dump_df.columns.get_loc("children")] = [
            c._hatchet_nid for c in node.children
        ]
        node.children = []
        dump_df.iat[i, dump_df.columns.get_loc("parents")] = [
            p._hatchet_nid for p in node.parents
        ]
        node.parents = []
    return dump_df


class DataframeWriter(ABC):
    def __init__(self, filename: str) -> None:
        self.filename = filename

    @abstractmethod
    def _write_dataframe_to_file(self, df: pd.DataFrame, **kwargs) -> None:
        pass

    def write(self, gf: GraphFrame, **kwargs) -> None:
        gf_cpy = gf.deepcopy()
        dump_df = _fill_children_and_parents(gf_cpy.dataframe)
        dump_df["exc_metrics"] = None
        dump_df.iat[0, dump_df.columns.get_loc("exc_metrics")] = gf_cpy.exc_metrics
        dump_df["inc_metrics"] = None
        dump_df.iat[0, dump_df.columns.get_loc("inc_metrics")] = gf_cpy.inc_metrics
        dump_df["default_metric"] = None
        dump_df.iat[0, dump_df.columns.get_loc("default_metric")] = (
            gf_cpy.default_metric
        )
        self._write_dataframe_to_file(dump_df, **kwargs)


class InvalidDataFrameIndex(Exception):
    """Raised when the DataFrame index is of an invalid type."""
