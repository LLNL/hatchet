import json
import pandas as pd

import hatchet.graphframe
from hatchet.node import Node
from hatchet.graph import Graph
from hatchet.frame import Frame

class PerfReader :
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
        node_mapping = {}
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
                if (ts < root.frame['ts']) and (ts + dur > root.frame['ts'] + root.frame['dur']):
                    node.add_child(root)
                    root.add_parent(node)
                    roots.pop()
            roots.append(node)
       
        print(roots) 
        # Create the Graph object from the root nodes
        graph = Graph(roots)

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
       
        return hatchet.graphframe.GraphFrame(graph, dataframe)

if __name__ == "__main__":
    # filename = "perfflow.quartz1532.3570764.pfw"
    filename = "perf_mod.pfw"
    # Create an instance of the PerfReader class
    perf_reader = PerfReader(filename)

    perf_reader.sort()
    graph_frame = perf_reader.read()
    # print(graph_frame.dataframe)

    # print(graph_frame.tree())

