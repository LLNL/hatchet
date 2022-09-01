# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import json

import pandas as pd

import hatchet.graphframe
from hatchet.node import Node
from hatchet.graph import Graph
from hatchet.frame import Frame


class JsonReader:
    """Create a GraphFrame from a json string of the following format.

    Return:
        (GraphFrame): graphframe containing data from dictionaries
    """

    def __init__(self, json_spec):
        """Read from a json string specification of a graphframe

        json (string): Json specification of a graphframe.
        """
        self.spec_dict = json.loads(json_spec)

    def read(self):
        roots = []
        for graph_spec in self.spec_dict["graph"]:
            # turn frames into nodes
            for nid, value in graph_spec.items():
                graph_spec[nid]["data"] = Node(Frame(value["data"]), hnid=int(nid))

            # connect nodes
            for nid, value in graph_spec.items():
                for child in value["children"]:
                    child = str(child)
                    value["data"].add_child(graph_spec[child]["data"])
                    graph_spec[child]["data"].add_parent(value["data"])

            for nid, value in graph_spec.items():
                if len(value["data"].parents) == 0:
                    roots.append(value["data"])

        grph = Graph(roots)

        # make the dataframes
        dataframe = pd.DataFrame(self.spec_dict["dataframe"])
        for graph_spec in self.spec_dict["graph"]:
            dataframe["node"] = dataframe["node"].map(
                lambda n: graph_spec[str(n)]["data"] if (str(n) in graph_spec) else n
            )
        dataframe.set_index(self.spec_dict["dataframe_indices"], inplace=True)

        return hatchet.graphframe.GraphFrame(
            grph,
            dataframe,
            self.spec_dict["exclusive_metrics"],
            self.spec_dict["inclusive_metrics"],
        )
