#!/usr/bin/env python
#
# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import hatchet as ht


if __name__ == "__main__":
    pfa_file = "../../../hatchet/tests/data/perfflow.quartz1532.3570764.pfw"

    gf = ht.GraphFrame.from_perfflowaspect(pfa_file)

    # Printout the DataFrame component of the GraphFrame.
    print(gf.dataframe)

    print(len(gf.graph.roots))

    for i, node in enumerate(gf.graph.traverse()):
        print(node._hatchet_nid, node, list(node.parents), list(node.children))

#    # Printout the graph component of the GraphFrame.
#    # Use "time (inc)" as the metric column to be displayed
#    print(gf.tree(metric_column="ts"))
