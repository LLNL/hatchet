import json
import pandas as pd

import hatchet.graphframe
from hatchet.node import Node
from hatchet.graph import Graph
from hatchet.frame import Frame

class PerfFlowAspectReader:
    """ Create a GraphFrame from a json string of the following format.

    Return:
        (GraphFrame): graphframe containing data from dictionaries
    """

    def __init__(self, filename):
        """Read from a json string specification of a graphframe

        json (string): Json specification of a graphframe.
        """
        with open(filename, 'r') as file:
            content = file.read()
            self.spec_dict = json.loads(content)
   
    def sort(self):
        # Sort the spec_dict based on the end time (ts + dur) of each function
        self.spec_dict = sorted(self.spec_dict, key=lambda item: item["ts"] + item["dur"])
 
    def read(self):
        roots = []
        node_mapping = {} # Dictionary to keep track of the nodes
        node_dicts = []

        for item in self.spec_dict:
            name = item["name"]
            ts = item["ts"]
            dur = item["dur"]

            # Create a Frame and Node for the function
            # Frame stores performance data related to each function
            # Node represents a node in the hierarchical graph structure
            frame = Frame({"name": name, "type": "function", "ts": ts, "dur": dur})
            node = Node(frame, parent=None, hnid=-1)

            # check the relationships between node and roots
            for root in reversed(roots):
                # if node is a parent of root node 
                if (ts < root.frame["ts"]) and (ts + dur > root.frame["ts"] + root.frame["dur"]):
                    node.add_child(root)
                    root.add_parent(node)
                    roots.pop()
            roots.append(node)
       
            
            node_dict = dict(
                {
                    "node": node,
                    "name": name,
                    "ts": ts,
                    "dur": dur,
                    "pid": item["pid"],
                    "tid": item["tid"],
                    "ph": item["ph"],
                }
            )
            node_dicts.append(node_dict)

            # Store the Node object with its name for future reference
            print("Add", name, "to node map")
            node_mapping[name] = node

        # Create the Graph object from the root nodes
        graph = Graph(roots)
        graph.enumerate_traverse()

        dataframe = pd.DataFrame(data=node_dicts)
        dataframe.set_index(["node"], inplace=True)
        dataframe.sort_index(inplace=True)

        exc_metrics = []
        inc_metrics = []
        for col in dataframe.columns:
            if "(inc)" in col:
                inc_metrics.append(col)
            else:
                exc_metrics.append(col)

        return hatchet.graphframe.GraphFrame(graph, dataframe)
