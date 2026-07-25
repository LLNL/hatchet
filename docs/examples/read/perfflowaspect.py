#!/usr/bin/env python
#
# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import hatchet as ht


if __name__ == "__main__":
    # pfa_file = "../../../hatchet/tests/data/perfflowaspect-smoketests/array_compact.pfw"
    # pfa_file = "../../../hatchet/tests/data/perfflowaspect-smoketests/array_verbose.pfw"
    # pfa_file = "../../../hatchet/tests/data/perfflowaspect-smoketests/object_compact_adiak.pfw"
    pfa_file = (
        "../../../hatchet/tests/data/perfflowaspect-smoketests/object_verbose_adiak.pfw"
    )

    gf = ht.GraphFrame.from_perfflowaspect(pfa_file)

    # Printout the DataFrame component of the GraphFrame.
    print(gf.dataframe)
    print(gf.metadata)

    print(len(gf.graph.roots))

    for i, node in enumerate(gf.graph.traverse()):
        print(node._hatchet_nid, node, list(node.parents), list(node.children))

    # Printout the graph component of the GraphFrame.
    # Use "ts" as the metric column to be displayed
    print(gf.tree(metric_column=["dur"]))
    # print(gf.tree(metric_column="ts"))
