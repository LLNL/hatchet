# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT


import pandas as pd
import numpy as np
import os

import caliperreader as cr

import hatchet.graphframe
from hatchet.node import Node
from hatchet.graph import Graph
from hatchet.frame import Frame
from hatchet.util.timer import Timer


def __raise_cali_type_error(msg):
    raise ValueError(msg)


class CaliperNativeReader:
    """Read in a native `.cali` file using Caliper's python reader."""

    __cali_type_dict = {
        "inv": lambda dummy: __raise_cali_type_error(
            "Caliper type 'inv' is unsupported in Hatchet"
        ),
        "usr": lambda dummy: __raise_cali_type_error(
            "Custom Caliper types are unsupported in Hatchet"
        ),
        "int": np.int64,
        "uint": np.uint64,
        "string": str,
        "addr": np.uint64,
        "double": np.float64,
        "bool": bool,
        "type": lambda dummy: __raise_cali_type_error(
            "Caliper 'type' types are unsupported in Hatchet"
        ),
        "ptr": lambda dummy: __raise_cali_type_error(
            "Caliper 'ptr' types are for internal use only!"
        ),
    }

    def __init__(self, filename_or_caliperreader, native, string_attributes):
        """Read in a native cali using Caliper's python reader.

        Args:
            filename_or_caliperreader (str or CaliperReader): name of a `cali` file OR
                a CaliperReader object
            native (bool): use native metric names or user-readable metric names
            string_attributes (str or list): Adds existing string attributes from within the caliper file to the dataframe
        """
        self.filename_or_caliperreader = filename_or_caliperreader
        self.filename_ext = ""
        self.use_native_metric_names = native
        self.string_attributes = string_attributes

        self.df_nodes = {}
        self.metric_cols = []
        self.record_data_cols = []
        self.node_dicts = []
        self.callpath_to_node = {}
        self.idx_to_node = {}
        self.callpath_to_idx = {}
        self.global_nid = 0
        self.node_ordering = False
        self.gf_list = []
        self.timeseries_level = None

        self.default_metric = None

        self.timer = Timer()

        if isinstance(self.filename_or_caliperreader, str):
            _, self.filename_ext = os.path.splitext(filename_or_caliperreader)

        if isinstance(self.string_attributes, str):
            self.string_attributes = [self.string_attributes]

    def _create_metric_df(self, metrics):
        """Make a list of metric columns and create a dataframe, group by node"""
        for col in self.record_data_cols:
            if self.filename_or_caliperreader.attribute(col).is_value():
                self.metric_cols.append(col)
        df_metrics = pd.DataFrame.from_dict(data=metrics)
        df_new = df_metrics.groupby(df_metrics["nid"]).aggregate("first").reset_index()
        return df_new

    def _reset_metrics(self, metrics):
        """Since the initial functions (i.e. main) are only called once, this keeps a small subset
        of the timeseries data and resets the rest so future iterations will be filled with nans
        """
        new_mets = []
        cols_to_keep = [
            "nid",
            "loop.iterations",
            "loop.start_iteration",
            "timeseries.snapshot",
        ]
        for node_dict in metrics:
            if node_dict.get("timeseries.snapshot") == 0.0:
                new_mets.append({k: node_dict.get(k, np.nan) for k in cols_to_keep})
        return new_mets

    def read_metrics(self, ctx="path"):
        """append each metrics table to a list and return the list, split on timeseries_level if exists"""
        metric_dfs = []
        all_metrics = []
        next_timestep = 0
        cur_timestep = 0
        records = self.filename_or_caliperreader.records

        # read metadata from the caliper reader
        for record in records:
            # if we have a timeseries file we need to split the single cali file into multiple profiles
            if self.timeseries_level in record:
                next_timestep = int(record[self.timeseries_level])
                if cur_timestep != next_timestep:
                    # make a dataframe for the current profile before we continue reading metrics
                    df_new = self._create_metric_df(all_metrics)
                    metric_dfs.append(df_new)
                    # reset the metrics for the next df, and update the timestep
                    all_metrics = self._reset_metrics(all_metrics)
                    cur_timestep = next_timestep

            node_dict = {}
            if ctx in record:
                # only parse records that have spot.channel=regionprofile or no
                # spot.channel attribute
                if (
                    "spot.channel" in record
                    and record["spot.channel"] == "regionprofile"
                ) or "spot.channel" not in record:
                    # get the node label and callpath for the record
                    if isinstance(record[ctx], list):
                        # specify how to parse cupti records
                        if "cupti.activity.kind" in record:
                            if record["cupti.activity.kind"] == "kernel":
                                node_label = record["cupti.kernel.name"]
                                node_callpath = tuple(record[ctx] + [node_label])
                            elif record["cupti.activity.kind"] == "memcpy":
                                node_label = record["cupti.activity.kind"]
                                node_callpath = tuple(record[ctx] + [node_label])
                        else:
                            node_label = record[ctx][-1]
                            node_callpath = tuple(record[ctx])
                    else:
                        node_label = record[ctx]
                        node_callpath = tuple([record[ctx]])

                    if "spot.channel" in record:
                        node_dict["spot.channel"] = record["spot.channel"]

                    # get node nid based on callpath
                    node_dict["nid"] = self.callpath_to_idx.get(node_callpath)

                    for item in record.keys():
                        if item != ctx:
                            attr_type = self.filename_or_caliperreader.attribute(
                                item
                            ).attribute_type()
                            if attr_type in self.__cali_type_dict:
                                if (
                                    attr_type != "string"
                                    or item in self.string_attributes
                                ):
                                    try:
                                        node_dict[item] = self.__cali_type_dict[
                                            attr_type
                                        ](record[item])
                                        if item not in self.record_data_cols:
                                            self.record_data_cols.append(item)
                                    except ValueError as e:
                                        if attr_type not in ("ptr", "inv"):
                                            print(
                                                "Ignoring attribute {}:\n    {}".format(
                                                    item, str(e)
                                                )
                                            )
                                        else:
                                            raise e

                    all_metrics.append(node_dict)

        # create the dataframe, if a single profile (or last one if the timeseries)
        df_new = self._create_metric_df(all_metrics)
        metric_dfs.append(df_new)
        # will return a list with only one element unless it is a timeseries
        return metric_dfs

    def create_graph(self, ctx="path"):
        list_roots = []

        def _create_parent(child_node, parent_callpath):
            """We may encounter a parent node in the callpath before we see it
            as a child node. In this case, we need to create a hatchet node for
            the parent.

            This function recursively creates parent nodes in a callpath
            until it reaches the already existing parent in that callpath.
            """
            parent_node = self.callpath_to_node.get(parent_callpath)

            if parent_node:
                # return if arrives at the parent
                parent_node.add_child(child_node)
                child_node.add_parent(parent_node)
                return
            else:
                # else create the parent and add parent/child

                # if root node, end recursive call to create parent nodes
                if not parent_callpath:
                    list_roots.append(child_node)

                    node_dict = dict(
                        {
                            "name": child_node.frame["name"],
                            "node": child_node,
                            "nid": self.global_nid,
                        }
                    )

                    self.idx_to_node[self.global_nid] = node_dict
                    self.global_nid += 1
                else:
                    grandparent_callpath = parent_callpath[:-1]
                    parent_name = parent_callpath[-1]

                    parent_node = Node(
                        Frame({"type": "function", "name": parent_name}), None
                    )

                    self.callpath_to_node[parent_callpath] = parent_node
                    self.callpath_to_idx[parent_callpath] = self.global_nid

                    node_dict = dict(
                        {
                            "name": parent_name,
                            "node": parent_node,
                            "nid": self.global_nid,
                        },
                    )
                    self.idx_to_node[self.global_nid] = node_dict
                    self.global_nid += 1

                    parent_node.add_child(child_node)
                    child_node.add_parent(parent_node)
                    _create_parent(parent_node, grandparent_callpath)

        parent_hnode = None
        records = self.filename_or_caliperreader.records
        order = -1

        for record in records:
            node_label = ""
            if ctx in record:
                if (
                    "spot.channel" in record
                    and record["spot.channel"] == "regionprofile"
                ) or "spot.channel" not in record:
                    # if it's a list, then it's a callpath
                    if isinstance(record[ctx], list):
                        # specify how to parse cupti records
                        if "cupti.activity.kind" in record:
                            if record["cupti.activity.kind"] == "kernel":
                                node_label = record["cupti.kernel.name"]
                                node_callpath = tuple(record[ctx] + [node_label])
                                parent_callpath = node_callpath[:-1]
                                node_type = "kernel"
                            elif record["cupti.activity.kind"] == "memcpy":
                                node_label = record["cupti.activity.kind"]
                                node_callpath = tuple(record[ctx] + [node_label])
                                parent_callpath = node_callpath[:-1]
                                node_type = "memcpy"
                            else:
                                Exception("Haven't seen this activity kind yet")
                        else:
                            node_label = record[ctx][-1]
                            node_callpath = tuple(record[ctx])
                            parent_callpath = node_callpath[:-1]
                            node_type = "function"

                        hnode = self.callpath_to_node.get(node_callpath)

                        if not hnode:
                            # set the _hatchet_nid by the node order column if it exists, else -1
                            if "min#min#aggregate.slot" in record:
                                self.node_ordering = True
                                order = record["min#min#aggregate.slot"]
                            frame = Frame({"type": node_type, "name": node_label})
                            order = int(order)
                            hnode = Node(frame, hnid=order)
                            self.callpath_to_node[node_callpath] = hnode

                            # get parent from node callpath
                            parent_hnode = self.callpath_to_node.get(parent_callpath)

                            # create parent if it doesn't exist
                            # else if parent already exists, add child-parent
                            if not parent_hnode:
                                _create_parent(hnode, parent_callpath)
                            else:
                                parent_hnode.add_child(hnode)
                                hnode.add_parent(parent_hnode)

                            self.callpath_to_idx[node_callpath] = self.global_nid
                            node_dict = dict(
                                {
                                    "name": node_label,
                                    "node": hnode,
                                    "nid": self.global_nid,
                                },
                            )
                            self.idx_to_node[self.global_nid] = node_dict
                            self.global_nid += 1

                    # if it's a string, then it's a root
                    else:
                        root_label = record[ctx]
                        root_callpath = tuple([root_label])

                        if root_callpath not in self.callpath_to_node:
                            # create the root since it doesn't exist
                            frame = Frame({"type": "function", "name": root_label})
                            graph_root = Node(frame, None)

                            # store callpaths to identify the root
                            self.callpath_to_node[root_callpath] = graph_root
                            self.callpath_to_idx[root_callpath] = self.global_nid
                            list_roots.append(graph_root)

                            node_dict = dict(
                                {
                                    "name": root_label,
                                    "node": graph_root,
                                    "nid": self.global_nid,
                                }
                            )

                            self.idx_to_node[self.global_nid] = node_dict
                            self.global_nid += 1

        return list_roots

    def _parse_metadata(self, mdata):
        """Convert Caliper Metadata values into correct Python objects.

        Args:
            mdata (dict[str: str]): metadata to convert

        Return:
            (dict[str: str]): modified metadata
        """
        parsed_mdata = {}
        for k, v in mdata.items():
            # environment information service brings in different metadata types
            if isinstance(v, list):
                parsed_mdata[k] = v
                continue
            # If the value is an int, convert it to an int.
            try:
                parsed_mdata[k] = int(v)
            except ValueError:
                # If the value is a float, convert it to a float
                try:
                    parsed_mdata[k] = float(v)
                except ValueError:
                    # If the value is a list or tuple, convert it to a list or
                    # tuple
                    if v.startswith("[") and v.endswith("]"):
                        parsed_mdata[k] = [
                            elem.strip() for elem in v.strip("][").split(",")
                        ]
                    elif v.startswith("(") and v.endswith(")"):
                        parsed_mdata[k] = [
                            elem.strip() for elem in v.strip(")(").split(",")
                        ]
                    # If the value is a string, just save it as-is
                    else:
                        parsed_mdata[k] = v
        return parsed_mdata

    def read(self):
        """Read the caliper records to extract the calling context tree."""
        if isinstance(self.filename_or_caliperreader, str):
            if self.filename_ext != ".cali":
                raise ValueError("from_caliperreader() needs a .cali file")
            else:
                cali_file = self.filename_or_caliperreader
                self.filename_or_caliperreader = cr.CaliperReader()
                self.filename_or_caliperreader.read(cali_file)

        with self.timer.phase("graph construction"):
            list_roots = self.create_graph()
        self.df_nodes = pd.DataFrame(data=list(self.idx_to_node.values()))

        # create a graph object once all the nodes have been added
        graph = Graph(list_roots, node_ordering=self.node_ordering)
        graph.enumerate_traverse()

        metadata = self.filename_or_caliperreader.globals
        parsed_metadata = self._parse_metadata(metadata)

        # Get a list of metrics (split by timeseries level if it exists)
        with self.timer.phase("read metrics"):
            metrics_list = self.read_metrics()

        # If not a timeseries there will just be one element in the list
        for df_fixed_data in metrics_list:

            metrics = pd.DataFrame.from_dict(data=df_fixed_data)

            # add missing intermediate nodes to the df_fixed_data dataframe
            if "mpi.rank" in df_fixed_data.columns:
                num_ranks = metrics["mpi.rank"].max() + 1
                rank_list = range(0, num_ranks)

            # create a standard dict to be used for filling all missing rows
            default_metric_dict = {}
            for idx, col in enumerate(self.record_data_cols):
                if self.filename_or_caliperreader.attribute(col).is_value():
                    default_metric_dict[list(self.record_data_cols)[idx]] = 0
                else:
                    default_metric_dict[list(self.record_data_cols)[idx]] = None
            default_metric_dict["nid"] = np.nan

            # create a list of dicts, one dict for each missing row
            missing_nodes = []
            for iteridx, row in self.df_nodes.iterrows():
                # check if df_nodes row exists in df_fixed_data
                metric_rows = df_fixed_data.loc[metrics["nid"] == row["nid"]]
                if "mpi.rank" not in self.metric_cols:
                    if metric_rows.empty:
                        # add a single row
                        node_dict = dict(default_metric_dict)
                        missing_nodes.append(node_dict)
                else:
                    if metric_rows.empty:
                        # add a row per MPI rank
                        for rank in rank_list:
                            node_dict = dict(default_metric_dict)
                            node_dict["nid"] = row["nid"]
                            node_dict["mpi.rank"] = rank
                            missing_nodes.append(node_dict)
                    elif len(metric_rows) < num_ranks:
                        # add a row for each missing MPI rank
                        present_ranks = metric_rows["mpi.rank"].values
                        missing_ranks = [x for x in rank_list if x not in present_ranks]
                        for rank in missing_ranks:
                            node_dict = dict(default_metric_dict)
                            node_dict["nid"] = row["nid"]
                            node_dict["mpi.rank"] = rank
                            missing_nodes.append(node_dict)

            df_missing = pd.DataFrame.from_dict(data=missing_nodes)
            df_metrics = pd.concat([df_fixed_data, df_missing], sort=False)

            # rename columns to user-readable metric names (i.e., aliases)
            if not self.use_native_metric_names:
                for col in df_metrics.columns:
                    if col == "nid":
                        continue
                    alias = self.filename_or_caliperreader.attribute(col).get(
                        "attribute.alias"
                    )
                    if alias:
                        # update column name in metrics dataframe
                        df_metrics.rename(columns={col: alias}, inplace=True)

                        # also update list of metric columns
                        self.metric_cols = [
                            alias if item == col else item for item in self.metric_cols
                        ]

            # dict mapping old to new column names to make columns consistent with
            # other readers
            old_to_new = {
                "mpi.rank": "rank",
                "module#cali.sampler.pc": "module",
                "sum#time.duration": "time",
                "sum#avg#sum#time.duration": "time",
                "inclusive#sum#time.duration": "time (inc)",
                "sum#avg#inclusive#sum#time.duration": "time (inc)",
            }

            # change column names
            new_cols = []
            for col in df_metrics.columns:
                if col in old_to_new:
                    new_cols.append(old_to_new[col])
                else:
                    new_cols.append(col)
            df_metrics.columns = new_cols

            # create list of exclusive and inclusive metric columns
            ignore_columns = [
                "mpi.rank",
                "aggregate.slot",
                "Node order",
                "loop.start_iteration",
            ]
            exc_metrics = []
            inc_metrics = []
            for column in self.metric_cols:
                # ignore rank as an exc or inc metric
                if column in ignore_columns:
                    continue

                # add new column names to list of metrics if inc or inclusive in
                # old column names
                if "(inc)" in column or "inclusive" in column:
                    if column in old_to_new:
                        column = old_to_new[column]
                    inc_metrics.append(column)
                else:
                    if column in old_to_new:
                        column = old_to_new[column]
                    exc_metrics.append(column)

            with self.timer.phase("data frame"):
                # merge the metrics and node dataframes on the nid column
                dataframe = pd.merge(df_metrics, self.df_nodes, on="nid")
                dataframe["nid"] = dataframe["nid"].astype(
                    self.__cali_type_dict["double"]
                )

                # set the index to be a MultiIndex
                indices = ["node"]
                if "rank" in dataframe.columns:
                    indices.append("rank")
                dataframe.set_index(indices, inplace=True)
                dataframe.sort_index(inplace=True)

            # set the default metric
            if self.default_metric is None:
                if "time (inc)" in dataframe.columns:
                    self.default_metric = "time"
                elif "avg#inclusive#sum#time.duration" in dataframe.columns:
                    self.default_metric = "avg#inclusive#sum#time.duration"
                elif len(inc_metrics) > 0:
                    self.default_metric = inc_metrics[0]
                elif len(exc_metrics) > 0:
                    self.default_metric = exc_metrics[0]

            # remove the "Node order" (or unaliased "aggregate.slot")
            if "Node order" in dataframe.columns:
                dataframe = dataframe.drop(columns="Node order")
            if "aggregate.slot" in dataframe.columns:
                dataframe = dataframe.drop(columns="aggregate.slot")

            # add the gf to the list
            self.gf_list.append(
                hatchet.graphframe.GraphFrame(
                    graph,
                    dataframe,
                    exc_metrics,
                    inc_metrics,
                    self.default_metric,
                    metadata=parsed_metadata,
                )
            )

        # If not a timeseries this will return the single profile expected
        #  othewise we'll have populated the timeseries list of gfs attribute and can ignore the return value
        return self.gf_list[0]

    def read_timeseries(self, level="loop.start_iteration"):
        """Read in a timeseries Cali file. We need to intercept the read function
        so we can get a list of profiles for thicket

        Args:
            level (str): column name to split the Cali file on, default

        Return:
            (list[GraphFrame]): A list of graph frames to be loaded into thicket
        """
        self.timeseries_level = level
        # we don't need the return gf from read as we want the list that has been populated
        _ = self.read()
        # return the list of graph frames that has been split per timestep
        return self.gf_list
