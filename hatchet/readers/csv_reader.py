# Copyright 2017-2021 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT
from __future__ import unicode_literals

from ast import literal_eval
import pandas as pd
from .dataframe_reader import DataframeReader

import pickle
import sys


def _unpickle_series_elems(pd_series):
    # unpickled_elems = [pickle.loads(e.encode("utf-8")) for e in pd_series]
    unpickled_elems = []
    for e in pd_series:
        e_bytes = e
        print(sys.version_info)
        print(sys.version_info >= (3,))
        if sys.version_info >= (3,):
            e_bytes = literal_eval(e)
        unpickled_elems.append(pickle.loads(e_bytes))
    return pd.Series(unpickled_elems)


def _correct_children_and_parent_col_types(df):
    new_children_col = []
    for c in df["children"]:
        if not isinstance(c, list):
            new_val = literal_eval(c)
            new_children_col.append(new_val)
        else:
            new_children_col.append(c)
    df["children"] = pd.Series(new_children_col)
    new_parent_col = []
    for p in df["parents"]:
        if not isinstance(p, list):
            new_val = literal_eval(p)
            new_parent_col.append(new_val)
        else:
            new_parent_col.append(p)
    df["parents"] = pd.Series(new_parent_col)
    return df


class CSVReader(DataframeReader):
    def __init__(self, filename):
        if sys.version_info[0] == 2:
            super(CSVReader, self).__init__(filename)
        else:
            super().__init__(filename)

    def _read_dataframe_from_file(self, **kwargs):
        index_col = None
        if "index_col" in kwargs:
            index_col = kwargs["index_col"]
            del kwargs["index_col"]
        csv_df = pd.read_csv(self.filename, index_col=0, **kwargs)
        csv_df["node"] = _unpickle_series_elems(csv_df["node"])
        csv_df = _correct_children_and_parent_col_types(csv_df)
        if index_col is not None:
            return csv_df.reset_index(drop=True).set_index(index_col)
        multindex_cols = ["node", "rank", "thread"]
        while len(multindex_cols) > 0:
            if set(multindex_cols).issubset(csv_df.columns):
                return csv_df.reset_index(drop=True).set_index(multindex_cols)
            multindex_cols.pop()
        # TODO Replace with a custom error
        raise RuntimeError("Could not generate a valid Index or MultiIndex")
