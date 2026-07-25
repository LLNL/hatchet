# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT


import json
import pandas as pd
import re

import hatchet.graphframe
from hatchet.node import Node
from hatchet.graph import Graph
from hatchet.frame import Frame


class PerfFlowAspectReader:
    """Create a GraphFrame from PerfFlowAspect trace files.

    Return:
        (GraphFrame): graphframe containing data from dictionaries
    """

    def __init__(self, filename, scan_cpu_mem=False):
        """
        filename (str): A path to a PerfFlowAspect trace file.
        scan_cpu_mem (bool): Whether or not to include CPU/Memory usage statistics
        """
        self.scan_cpu_mem = scan_cpu_mem
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
                elif ph == "C":
                    final.append(event)
            self.spec_dict = final

    def _repair_array_json(self, text):
        text = text.rstrip()
        text = re.sub(r",\s*$", "", text)

        stripped = text.lstrip()

        if stripped.startswith("{"):
            # Object format
            if not text.endswith("]"):
                text += "]"
            if not text.endswith("}"):
                text += "}"
            return text

        # Bare array format: [ {...}, {...}, ... ]
        if not text.endswith("]"):
            text += "]"
        if not stripped.startswith("["):
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
        if all("C" not in item["ph"] for item in self.spec_dict) and self.scan_cpu_mem:
            raise ValueError("No statistics in the provided file!")
        
        if self.scan_cpu_mem:
            for item in self.spec_dict:
                if item["ph"] != "C":
                    continue
                ts = item["ts"] * 1e-6
                memory, cpu, valid = 0, 0, False
                if item["args"]["memory_usage"] != 0:
                    memory = item["args"]["memory_usage"]
                    valid = True
                if item["args"]["cpu_usage"] != 0.0:
                    cpu = item["args"]["cpu_usage"]
                    valid = True
                if valid:
                    usage_pairings[ts] = (memory, cpu)

        for item in self.spec_dict:
            name = item["name"]
            ts = item["ts"] * 1e-6
            ph = item["ph"]

            if ph == "C":
                continue

            dur = item["dur"] * 1e-6

            # A Frame always consists of these values
            frame_values = {"name": name, "type": "function", "ts": ts, "dur": dur}

            # Optionally, if logging statistics, insert memory and cpu usage
            # into the Frame
            if self.scan_cpu_mem:
                memory = usage_pairings.get(ts, (0, 0))[0]
                frame_values["usage_memory"] = memory
                cpu = usage_pairings.get(ts, (0, 0))[1]
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
            if self.scan_cpu_mem:
                node_dict_vals["usage_memory"] = memory
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
                
        return hatchet.graphframe.GraphFrame(
            graph, dataframe, exc_metrics=exc_metrics, inc_metrics=inc_metrics, metadata=self.metadata
        )
