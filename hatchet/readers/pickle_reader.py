# Copyright 2017-2021 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import pandas as pd
from .dataframe_reader import DataframeReader

import sys


class PickleReader(DataframeReader):
    def __init__(self, filename):
        if sys.version_info[0] == 2:
            super(PickleReader, self).__init__(filename)
        else:
            super().__init__(filename)

    def _read_dataframe_from_file(self, **kwargs):
        return pd.read_pickle(self.filename, **kwargs)
