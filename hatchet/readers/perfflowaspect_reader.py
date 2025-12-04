import json
import pandas as pd

import hatchet.graphframe
from hatchet.node import Node
from hatchet.graph import Graph
from hatchet.frame import Frame


class PerfFlowAspectReader:
    """Create a GraphFrame from PerfFlowAspect trace files.

    Return:
        (GraphFrame): graphframe containing data from dictionaries
    """

    def __init__(self, filename, scan_memory=False, scan_cpu=False):
        """
        filename (str): A path to a PerfFlowAspect trace file.
        scan_memory (bool): Whether or not to include memory usage statistics
        scan_cpu (bool): Whether or not to include CPU usage statistics
        """
        self.scan_memory = scan_memory
        self.scan_cpu = scan_cpu
        with open(filename, "r+") as file:
            raw = file.read()
            
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                fixed = self._repair_array_json(raw)
                try:
                    data = json.loads(fixed)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Trace file could not be parsed or repaired: {e}")
            
            if isinstance(data, dict) and "traceEvents" in data and isinstance(data["traceEvents"], list):
                obj = data
                self.displayTimeUnit = obj.get("displayTimeUnit")
                self.metadata = obj.get("otherData", {})
                self.spec_dict = obj["traceEvents"]
            elif isinstance(data, list):
                self.displayTimeUnit = None
                self.metadata = {}
                self.spec_dict = data
            else:
                raise ValueError("Trace must be either object or array format")

        # Change verbose output to compact output
        if self.spec_dict and self.spec_dict[0].get("ph") == "B":
            stack = []
            final = []
            for event in self.spec_dict:
                ph = event.get("ph")

                if ph == "B":
                    stack.append(event.copy())
                elif ph == "E":
                    if not stack:
                        continue
                    start = stack.pop()
                    merged = start
                    merged["dur"] = event["ts"] - start["ts"]
                    merged["ph"] = "X"
                    final.append(merged)
            self.spec_dict = final

    def _repair_array_json(self, text):
        text = text.rstrip()
        text = text.replace(",\n]", "\n]")
        if not text.endswith("]"):
            text += "]"
        if not text.lstrip().startswith("["):
            text = "[" + text
        return text

    def sort(self):
        # Sort the spec_dict based on the end time (ts + dur) of each function
        self.spec_dict = sorted(
            self.spec_dict, key=lambda item: item["ts"] + item["dur"]
        )

    def read(self):
        roots = []
        node_mapping = {}  # Dictionary to keep track of the nodes
        node_dicts = []
        usage_pairings = {}  # usage_pairings[ts] = (memory, cpu)

        # Error if attempt is made to retrieve statistics,
        # but no statistics exist.
        if all("C" not in item["ph"] for item in self.spec_dict) and (
            self.scan_cpu or self.scan_memory
        ):
            raise ValueError("No statistics in the provided file!")

        for item in self.spec_dict:
            # the following values always appear in a PerfFlowAspect log
            name = item["name"]
            ts = item["ts"] * 1e-6 # convert to seconds
            ph = item["ph"]

            # these items may or may not appear.
            dur = None
            memory = 0
            cpu = 0

            # If statistic event, get the statistics and match with
            # the timestamp.
            if ph == "C":
                valid_statistic = False
                if self.scan_memory:
                    if item["args"]["memory_usage"] != 0:
                        memory = item["args"]["memory_usage"]
                        valid_statistic = True
                if self.scan_cpu:
                    if item["args"]["cpu_usage"] != 0.0:
                        cpu = item["args"]["cpu_usage"]
                        valid_statistic = True
                if valid_statistic:
                    usage_pairings[ts] = (memory, cpu)
                continue

            dur = item["dur"] * 1e-6

            # A Frame always consists of these values
            frame_values = {"name": name, "type": "function", "ts": ts, "dur": dur}

            # Optionally, if logging statistics, insert memory and cpu usage
            # into the Frame
            if self.scan_memory:
                memory = usage_pairings[ts][0]
                frame_values["usage_memory"] = memory
            if self.scan_cpu:
                cpu = usage_pairings[ts][1]
                frame_values["usage_cpu"] = cpu

            # Create a Frame and Node for the function
            # Frame stores information about the node
            # Node represents a node in the hierarchical graph structure
            frame = Frame(frame_values)
            node = Node(frame, parent=None, hnid=-1)

            # check the relationships between node and roots
            for root in reversed(roots):
                # if node is a parent of root node
                if (ts < root.frame["ts"]) and (
                    ts + dur > root.frame["ts"] + root.frame["dur"]
                ):
                    node.add_child(root)
                    root.add_parent(node)
                    roots.pop()
            roots.append(node)

            node_dict_vals = {
                "node": node,
                "name": name,
                "ts": ts,
                "dur": dur,
                "pid": item["pid"],
                "tid": item["tid"],
                "ph": item["ph"],
            }
            if self.scan_memory:
                node_dict_vals["usage_memory"] = memory
            if self.scan_cpu:
                node_dict_vals["usage_cpu"] = cpu

            node_dict = dict(node_dict_vals)
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

        return hatchet.graphframe.GraphFrame(graph, dataframe, metadata=self.metadata)
