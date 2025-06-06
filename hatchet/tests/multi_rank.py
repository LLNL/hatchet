# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from hatchet import GraphFrame


def test_multi_rank(caliper_multi_rank):
    gf = GraphFrame.from_caliperreader(caliper_multi_rank)

    node = [
        n
        for n in gf.dataframe.index.get_level_values("node")
        if n.frame["name"] == "CalculateMoments"
    ][0]

    node_df = gf.dataframe.loc[node]

    # same number of rows as ranks
    assert node_df.shape[0] == gf.metadata["mpi.world.size"]
    # same check in different way
    assert (
        len(gf.dataframe.index.get_level_values("rank").unique())
        == gf.metadata["mpi.world.size"]
    )
