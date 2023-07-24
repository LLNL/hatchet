# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np
import re

from hatchet import GraphFrame


def test_graphframe(hatchet_cycle_pstats):
    gf = GraphFrame.from_cprofile(str(hatchet_cycle_pstats))

    assert len(gf.dataframe.groupby("file")) == 4
    assert len(gf.dataframe.groupby("name")) == 9

    gf.dataframe.reset_index(inplace=True)

    for col in gf.dataframe.columns:
        if col in ("time (inc)", "time"):
            assert gf.dataframe[col].dtype == np.float64
        elif col in ("line", "numcalls", "nativecalls"):
            assert gf.dataframe[col].dtype == np.int64
        elif col in ("name", "type", "file", "module", "node"):
            assert gf.dataframe[col].dtype == object


def test_tree(monkeypatch, hatchet_cycle_pstats):
    monkeypatch.setattr("sys.stdout.isatty", (lambda: False))
    gf = GraphFrame.from_cprofile(str(hatchet_cycle_pstats))

    output = gf.tree(metric_column="time")

    assert "g pstats_reader_test.py" in output
    assert "<method 'disable' ...Profiler' objects> ~" in output

    output = gf.tree(metric_column="time (inc)")

    assert "f pstats_reader_test.py" in output
    assert re.match("(.|\n)*recursive(.|\n)*recursive", output)
