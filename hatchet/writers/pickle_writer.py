# Copyright 2017-2021 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from .dataframe_writer import DataframeWriter

import sys


class PickleWriter(DataframeWriter):
    def __init__(self, filename):
        if sys.version_info[0] == 2:
            super(PickleWriter, self).__init__(filename)
        else:
            super().__init__(filename)

    def _write_dataframe_to_file(self, df, **kwargs):
        df.to_pickle(self.filename, **kwargs)
