# Copyright 2017-2021 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from .dataframe_writer import DataframeWriter

import pandas as pd
import pickle

import sys


def pickle_series_elems(pd_series):
    pickled_elems = [pickle.dumps(e) for e in pd_series]
    return pd.Series(pickled_elems)


class CSVWriter(DataframeWriter):
    def __init__(self, filename):
        if sys.version_info[0] == 2:
            super(CSVWriter, self).__init__(filename)
        else:
            super().__init__(filename)

    def _write_dataframe_to_file(self, df, **kwargs):
        df.reset_index(inplace=True)
        df["node"] = pickle_series_elems(df["node"])
        df["children"] = df["children"].apply(str, convert_dtype=True)
        df["parents"] = df["parents"].apply(str, convert_dtype=True)
        df.to_csv(self.filename, **kwargs)
