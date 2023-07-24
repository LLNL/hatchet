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
            node = Node(Frame({"name": name, "ts": ts, "dur": dur}))
            # check the relationships between node and roots
            for root in reversed(roots):
                # if node is a parent of root node 
                if (ts < root.frame["ts"]) and (ts + dur > root.frame["ts"] + root.frame["dur"]):
                    node.add_child(root)
                    root.add_parent(node)
                    roots.pop()
            roots.append(node)
       
        print(roots) 

            # Create a Frame and Node for the function
            # Frame stores performance data related to each function
            # Node represents a node in the hierarchical graph structure
            frame = Frame({"name": name, "type": "function", "ts": ts, "dur": dur})
            node = Node(frame, parent=None, hnid=-1)

            # Connect nodes based on parent-child relationships
            parent_node = None
            # print(node_mapping.values())
            for existing_node in node_mapping.values():
                if existing_node.frame["ts"] < ts < (existing_node.frame["ts"] + existing_node.frame["dur"]):
                    parent_node = existing_node
                    break

            if parent_node:
                parent_node.add_child(node)
                node.add_parent(parent_node)
            else:
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

        # Create the DataFrame
        dataframe = pd.DataFrame(self.spec_dict)
        #print(dataframe['name'])
        print(dataframe.columns)

        #print("Unique values in 'name' column:", dataframe["name"].unique())
        #print("Keys in node_mapping dictionary:", node_mapping.keys())

        dataframe.rename(columns={'name':'node'}, inplace=True)
        dataframe['node'] = dataframe['node'].map(

            lambda n: node_mapping[n] if n in node_mapping else n
        )
       
        dataframe.set_index('node', inplace=True)  # Set 'name' column as the index
       
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
