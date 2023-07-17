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
    
    def read(self):
        roots = []
        node_mapping = {} # Dictionary to keep track of the nodes

        for item in self.spec_dict:
            name = item['name']
            ts = item['ts']
            dur = item['dur']

            # Create a Frame and Node for the function
            # Frame stores performance data related to each function
            # Node represents a node in the hierarchical graph structure 
            node = Node(Frame({"name": name, "ts": ts, "dur": dur}))
        
            # Connect nodes based on parent-child relationships
            parent_node = None
            # print(node_mapping.values())
            for existing_node in node_mapping.values():
                if existing_node.frame['ts'] < ts < (existing_node.frame['ts'] + existing_node.frame['dur']):
                    parent_node = existing_node
                    break

            if parent_node:
                parent_node.add_child(node)
                node.add_parent(parent_node)
            else:
                roots.append(node)

            # Store the Node object with its name for future reference
            node_mapping[name] = node

        # Create the Graph object from the root nodes
        graph = Graph(roots)

        # Create the DataFrame
        dataframe = pd.DataFrame(self.spec_dict)

        return hatchet.graphframe.GraphFrame(graph, dataframe)

if __name__ == "__main__":
    filename = "perfflow.quartz1532.3570764.pfw"

    # Create an instance of the PerfReader class
    perf_reader = PerfReader(filename)

    # Call the read() method to create a GraphFrame object
    graph_frame = perf_reader.read()
    print(graph_frame.dataframe)
