# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import os
import re
import struct
from datetime import datetime
from typing import Dict, List, Tuple, Union

import pandas as pd

from hatchet.frame import Frame
from hatchet.graph import Graph
from hatchet.graphframe import GraphFrame
from hatchet.node import Node


def binary_search(
    format: str, data: bytes, low: int, high: int, target: int
) -> Union[int, Tuple[int, int, Union[int, float]]]:

    if high >= low:

        mid = (low + high) // 2
        (id, idValue) = safe_unpack(format, data, 0, mid)

        if id == target:
            return (mid, id, idValue)

        elif id > target:
            return binary_search(format, data, low, mid - 1, target)

        else:
            return binary_search(format, data, mid + 1, high, target)

    else:
        return -1


def safe_unpack(
    format: str, data: bytes, offset: int, index: int = None, index_length: int = None
) -> tuple:
    length = struct.calcsize(format)
    if index:
        offset += index * (length if index_length is None else index_length)
    return struct.unpack(format, data[offset : offset + length])


def read_string(data: bytes, offset: int) -> str:
    result = ""
    while True:
        (letter,) = struct.unpack("<c", data[offset : offset + 1])
        letter = letter.decode("ascii")
        if letter == "\x00":
            return result
        result += letter
        offset += 1


NODE_TYPE_MAPPING = {0: "function", 1: "loop", 2: "line", 3: "instruction"}

METRIC_SCOPE_MAPPING = {
    "execution": "i",
    "function": "e",
    "point": "p",
    "lex_aware": "c",
}

SUMMARY_METRIC_MAPPING = {
    0: "sum",
    1: "min",
    2: "max",
}

FILE_HEADER_OFFSET = 16


class HPCToolkitReaderLatest:

    def __init__(
        self,
        dir_path: str,
        directory_mapping: Dict[str, str] = None,
        parallel_profiles_mode: bool = False,
        max_depth: int = None,
        min_application_percentage_time: int = None,
        exclude_mpi_function_details: bool = False,
        exclude_openmp_function_details: bool = False,
        exclude_cuda_function_details: bool = False,
        exclude_system_libraries_source_code: bool = False,
        exclude_function_call_lines: bool = False,
        exclude_no_source_code_instructions: bool = False,
        exclude_instructions: bool = False,
        exclude_non_function_nodes: bool = False,
        label_function_nodes: bool = True,
        metric_names: List[str] = ["time"],
        metric_scopes: List[str] = ["i", "e"],
        summary_metrics: List[str] = ["sum", "min", "max"],
        profile_ranks: List[int] = None,
    ) -> None:
        self._dir_path = dir_path
        self._directory_mapping = directory_mapping or {}
        self._parallel_profiles_mode = parallel_profiles_mode
        self._max_depth = max_depth
        self._min_application_percentage_time = min_application_percentage_time

        self._exclude_mpi_function_details = exclude_mpi_function_details
        self._exclude_openmp_function_details = exclude_openmp_function_details
        self._exclude_cuda_function_details = exclude_cuda_function_details
        self._exclude_system_libraries_source_code = (
            exclude_system_libraries_source_code
        )
        self._exclude_function_call_lines = exclude_function_call_lines
        self._exclude_no_source_code_instructions = exclude_no_source_code_instructions
        self._exclude_instructions = exclude_instructions
        self._exclude_non_function_nodes = exclude_non_function_nodes

        self._metric_names = metric_names or ["time"]
        self._metric_scopes = metric_scopes or ["i", "e"]
        self._summary_metrics = summary_metrics or ["sum", "min", "max"]
        self._profile_ranks = profile_ranks or []

        self._meta_file = None
        self._profile_file = None
        self._cct_file = None

        self._functions = {}
        self._source_files = {}
        self._load_modules = {}
        self._graph_roots = []
        self._profiles_data = []
        self._summary_profile = {}

        self._label_function_nodes = label_function_nodes
        self._profile_ids = []
        self._metric_ids = []
        self._metric_descriptions = {}
        self._time_metric = None
        self._total_execution_time = 0
        self._profiles_metadata: pd.DataFrame = None

        for file_path in os.listdir(self._dir_path):
            if file_path.split(".")[-1] == "db":
                file_path = os.path.join(self._dir_path, file_path)
                with open(file_path, "rb") as file:
                    file.seek(10)
                    db = file.read(4)
                try:
                    format = db.decode("ascii")
                    if format == "meta":
                        self._meta_file = file_path
                    elif format == "prof":
                        self._profile_file = file_path
                    elif format == "ctxt":
                        self._cct_file = file_path

                except Exception:
                    pass

        if self._meta_file is None:
            raise ValueError("ERROR: meta.db not found.")

        if self._profile_file is None:
            raise ValueError("ERROR: profile.db not found.")

        if self._cct_file is None:
            raise ValueError("ERROR: cct.db not found.")

    def _parse_source_file(self, meta_db: bytes, pFile: int) -> Dict[str, str]:
        if pFile not in self._source_files:
            (pPath,) = safe_unpack(
                "<Q",
                meta_db,
                pFile + struct.calcsize("<Q"),
            )

            file_path = read_string(meta_db, pPath)

            if file_path.startswith("src"):
                file_path = file_path[3:]

            for item in self._directory_mapping:
                new_item = item
                if not item.startswith("/"):
                    new_item = f"/{item}"
                if not item.endswith("/"):
                    new_item = f"{new_item}/"
                if file_path.startswith(new_item):
                    file_path = (
                        f"{self._directory_mapping[item]}/{file_path[len(new_item):]}"
                    )
                    break

            self._source_files[pFile] = {"id": pFile, "file_path": file_path}

        return self._source_files[pFile]

    def _parse_load_module(self, meta_db: bytes, pModule: int) -> Dict[str, str]:
        if pModule not in self._load_modules:
            (pPath,) = safe_unpack(
                "<Q",
                meta_db,
                pModule + struct.calcsize("<Q"),
            )
            self._load_modules[pModule] = {
                "id": pModule,
                "module_path": read_string(meta_db, pPath),
            }

        return self._load_modules[pModule]

    def _parse_function(
        self, meta_db: bytes, pFunction: int
    ) -> Dict[str, Union[str, int]]:
        if pFunction not in self._functions:
            (pName, pModule, offset, pFile, line) = safe_unpack(
                "<QQQQL", meta_db, pFunction
            )

            name = read_string(meta_db, pName)

            if re.fullmatch(
                "P?MPI_.+",
                name,
            ):
                name = name[: re.match("^P?MPI_[a-zA-Z_]+", name).end()]

            for item in [" [", ".", "@", "(", "<"]:
                if item in name and not name.startswith(item):
                    name = name[: name.index(item)]

            self._functions[pFunction] = {
                "id": pFunction,
                "name": name,
                "line": line,
                "offset": offset,
            }
            if pFile:
                self._functions[pFunction]["file_id"] = self._parse_source_file(
                    meta_db, pFile
                )["id"]
            if pModule:
                self._functions[pFunction]["module_id"] = self._parse_load_module(
                    meta_db, pModule
                )["id"]

        return self._functions[pFunction]

    def _parse_context(
        self,
        current_offset: int,
        total_size: int,
        parent: Node,
        meta_db: bytes,
    ) -> None:
        final_offset = current_offset + total_size

        while current_offset < final_offset:
            (szChildren, pChildren, ctxId, _, lexicalType, nFlexWords) = safe_unpack(
                "<QQLHBB", meta_db, current_offset
            )

            flex_offset = current_offset + 32
            current_offset += 32 + nFlexWords * 8

            my_time = (
                self._summary_profile[ctxId][self._time_metric]
                if ctxId in self._summary_profile
                and self._time_metric in self._summary_profile[ctxId]
                else None
            )

            if self._min_application_percentage_time is not None and (
                my_time is None
                or my_time / self._total_execution_time * 100
                < self._min_application_percentage_time
            ):
                continue

            node_type = NODE_TYPE_MAPPING[lexicalType]
            frame = {"type": node_type}

            include_node = True and not (
                self._exclude_non_function_nodes and node_type != "function"
            )
            include_subtree = True

            if include_node and nFlexWords:
                if node_type == "function":
                    (pFunction,) = safe_unpack("<Q", meta_db, flex_offset)
                    function_data = self._parse_function(meta_db, pFunction)
                    frame["name"] = function_data["name"]

                    if self._exclude_mpi_function_details and (
                        frame["name"].startswith("MPI_")
                        or frame["name"].startswith("PMPI_")
                    ):
                        include_subtree = False

                    if "file_id" in function_data:
                        file_data = self._source_files[function_data["file_id"]]

                        if (
                            self._exclude_openmp_function_details
                            and "/openmp/" in file_data["file_path"]
                        ):
                            include_subtree = False
                            frame["name"] = f"<omp> {frame['name']}"

                        if self._exclude_cuda_function_details:
                            for item in [
                                "libcuda.so",
                                "libcudart.so",
                                "libcusparse.so",
                                "libcublas.so",
                                "libcurand.so",
                                "libcusolver.so",
                                "libcufft.so",
                                "/cuda/",
                            ]:
                                if item in file_data["file_path"]:
                                    include_subtree = False

                    if self._label_function_nodes:
                        frame["name"] = f"function: {frame['name']}"

                elif node_type == "instruction":
                    (pModule, offset) = safe_unpack("<QQ", meta_db, flex_offset)
                    frame["name"] = (
                        f"{self._parse_load_module(meta_db, pModule)['module_path']}:{offset}"
                    )

                    if self._exclude_instructions:
                        include_node = False

                else:
                    (pFile, line) = safe_unpack("<QL", meta_db, flex_offset)
                    file_data = self._parse_source_file(meta_db, pFile)
                    frame["name"] = f"{frame['type']} {file_data['file_path']}:{line}"

                    if self._exclude_system_libraries_source_code:
                        for item in ["/usr/src/debug", "/usr/tce"]:
                            if file_data["file_path"].startswith(item):
                                include_node = False

                    if self._exclude_no_source_code_instructions and line == 0:
                        include_node = False

                    if (
                        self._exclude_function_call_lines
                        and frame["type"] == "line"
                        and szChildren > 0
                    ):
                        include_node = False

            if not include_node:
                node = parent

            else:
                node = self._store_cct_node(
                    ctxId,
                    frame,
                    parent,
                )

            if include_subtree and (
                self._max_depth is None or node._depth < self._max_depth
            ):
                self._parse_context(
                    pChildren,
                    szChildren,
                    node,
                    meta_db,
                )

    def _store_cct_node(
        self,
        ctxId: int,
        frame: dict,
        parent: Node = None,
    ) -> Node:
        node = Node(
            Frame(frame),
            parent=parent,
            hnid=ctxId,
            depth=0 if parent is None else parent._depth + 1,
        )

        if not self._parallel_profiles_mode:
            record = self._summary_profile.get(ctxId, {})
            record["node"] = node
            record["name"] = node.frame["name"]
            record["profile"] = 0
            self._profiles_data.append(record)

        else:
            metric_ids = self._metric_ids[:]
            # TODO: what if metric list is empty?

            with open(self._cct_file, "rb") as file:
                file.seek(FILE_HEADER_OFFSET)
                formatCtxInfos = "<QQ"
                cct_db = file.read(struct.calcsize(formatCtxInfos))
                (szCtxInfos, pCtxInfos) = safe_unpack(formatCtxInfos, cct_db, 0)

                file.seek(pCtxInfos)
                cct_db = file.read(szCtxInfos)
                (pCtxs, nCtxs, szCtx) = safe_unpack("<QLB", cct_db, 0)

                file.seek(pCtxs + ctxId * szCtx)
                cct_db = file.read(szCtx)
                (nValues, pValues, nMetrics, _, _, pMetricIndices) = safe_unpack(
                    "<QQHHLQ", cct_db, 0
                )

                file.seek(pMetricIndices)
                formatMetrics = "<HQ"
                metrics_sub_db = file.read(nMetrics * struct.calcsize(formatMetrics))

                file.seek(pValues)
                formatValues = "<Ld"
                values_sub_db = file.read(nValues * struct.calcsize(formatValues))

                records = {}

                low = 0
                high = nMetrics

                while len(metric_ids):
                    metric_id = metric_ids.pop()
                    profile_ids = self._profile_ids[:]

                    result = binary_search(
                        formatMetrics, metrics_sub_db, low, high, metric_id
                    )

                    if result != -1:
                        (mid, metricId, startIndex) = result
                        high = mid

                        if mid == nMetrics - 1:
                            end_index = nValues
                        else:
                            (_, end_index) = safe_unpack(
                                formatMetrics, metrics_sub_db, 0, mid + 1
                            )

                        if len(profile_ids):

                            while len(profile_ids):

                                profile_id = profile_ids.pop()
                                result_2 = binary_search(
                                    formatValues,
                                    values_sub_db,
                                    startIndex,
                                    end_index,
                                    profile_id,
                                )

                                if result_2 != -1:
                                    (mid, profIndex, value) = result_2

                                    if profIndex not in records:
                                        records[profIndex] = {
                                            "node": node,
                                            "profile": profIndex,
                                            "name": node.frame["name"],
                                        }

                                    records[profIndex][
                                        self._metric_descriptions[metricId]
                                    ] = value

                                    end_index = mid

                        else:
                            for j in range(startIndex, end_index):
                                (profIndex, value) = safe_unpack(
                                    formatValues, values_sub_db, 0, j
                                )

                                if profIndex not in records:
                                    records[profIndex] = {
                                        "node": node,
                                        "profile": profIndex,
                                        "name": node.frame["name"],
                                    }

                                records[profIndex][
                                    self._metric_descriptions[metricId]
                                ] = value

                self._profiles_data.extend(records.values())

        if parent is None:
            self._graph_roots.append(node)
        else:
            parent.add_child(node)

        return node

    def _read_metric_descriptions(self) -> None:
        with open(self._meta_file, "rb") as file:
            file.seek(FILE_HEADER_OFFSET + 4 * 8)
            formatMetrics = "<QQ"
            meta_db = file.read(struct.calcsize(formatMetrics))
            (
                szMetrics,
                pMetrics,
            ) = safe_unpack(formatMetrics, meta_db, 0)

            file.seek(pMetrics)
            meta_db = file.read(szMetrics)

        pMetrics_old = pMetrics
        (pMetrics, nMetrics, szMetric, szScopeInst, szSummary) = safe_unpack(
            "<QLBBB", meta_db, 0
        )

        for i in range(nMetrics):
            (pName, pScopeInsts, pSummaries, nScopeInsts, nSummaries) = safe_unpack(
                "<QQQHH", meta_db, pMetrics - pMetrics_old, i, szMetric
            )

            name = read_string(meta_db, pName - pMetrics_old).lower().strip()
            # unit = None
            if name.endswith(")"):
                name = name[:-1]
                # unit = name.split("(")[1].lower().strip()
                name = name.split("(")[0].lower().strip()

            if name in ["cputime", "realtime", "cycles"]:
                name = "time"

            if name not in self._metric_names:
                continue

            def store_metric(
                metricName: str, metricId: int, pScope: int, store: bool = True
            ) -> None:
                (pScopeName,) = safe_unpack("<Q", meta_db, pScope - pMetrics_old)
                scope_name = METRIC_SCOPE_MAPPING[
                    read_string(meta_db, pScopeName - pMetrics_old).lower().strip()
                ]

                if scope_name in self._metric_scopes:
                    metric_full_name = (
                        f"{metricName} (inc)" if scope_name == "i" else metricName
                    )

                    if metric_full_name == "time (inc)":
                        self._time_metric = metric_full_name
                        # TODO: is the logic correct to use this metric for verifying min application percentage time filter?

                    if store:
                        self._metric_descriptions[metricId] = metric_full_name

            if self._parallel_profiles_mode:
                for j in range(nScopeInsts):
                    (pScope, propMetricId) = safe_unpack(
                        "<QH", meta_db, pScopeInsts - pMetrics_old, j, szScopeInst
                    )
                    store_metric(name, propMetricId, pScope)

            else:
                for j in range(nSummaries):
                    (pScope, _, combine, _, statMetricId) = safe_unpack(
                        "<QQBBH", meta_db, pSummaries - pMetrics_old, j, szSummary
                    )
                    summary_name = SUMMARY_METRIC_MAPPING[combine]
                    if summary_name in self._summary_metrics or (
                        self._min_application_percentage_time is not None
                        and summary_name == "sum"
                    ):
                        store_metric(
                            f"{name}:{summary_name}" if summary_name != "sum" else name,
                            statMetricId,
                            pScope,
                            store=summary_name in self._summary_metrics,
                        )

        self._metric_ids = list(self._metric_descriptions.keys())
        self._metric_ids.sort()

    def _read_profiles_metadata(self) -> None:
        identifiers = {}

        with open(self._meta_file, "rb") as file:
            file.seek(FILE_HEADER_OFFSET + 2 * 8)
            formatIdNames = "<QQ"
            meta_db = file.read(struct.calcsize(formatIdNames))
            (szIdNames, pIdNames) = safe_unpack(formatIdNames, meta_db, 0)

            file.seek(pIdNames)
            meta_db = file.read(szIdNames)
            (ppNames, nKinds) = safe_unpack("<QB", meta_db, 0)

            for i in range(nKinds):
                (pName,) = safe_unpack("<Q", meta_db, ppNames - pIdNames, i)
                identifiers[i] = read_string(meta_db, pName - pIdNames).lower().strip()

        profiles = []

        with open(self._profile_file, "rb") as file:
            file.seek(FILE_HEADER_OFFSET + 2 * 8)
            formatProfileInfosIdTuples = "<QQ"
            profile_db = file.read(struct.calcsize(formatProfileInfosIdTuples))
            (szIdTuples, pIdTuples) = safe_unpack(
                formatProfileInfosIdTuples, profile_db, 0
            )

            file.seek(pIdTuples)
            profile_db = file.read(szIdTuples)

            current_offset = 0
            current_index = 1

            while current_offset < szIdTuples:
                row = {"profile": current_index}
                profiles.append(row)

                (nIds,) = safe_unpack("<H", profile_db, current_offset)
                current_offset += 8

                for i in range(nIds):
                    formatIds = "<BBHLQ"
                    (kind, _, _, logicalId, physicalId) = safe_unpack(
                        formatIds, profile_db, current_offset
                    )
                    row[identifiers[kind]] = physicalId if kind in [1, 7] else logicalId
                    current_offset += struct.calcsize(formatIds)

                current_index += 1

        self._profiles_metadata = pd.DataFrame(profiles).set_index("profile")

        if len(self._profile_ranks):
            temp = self._profiles_metadata[
                self._profiles_metadata["rank"].isin(self._profile_ranks)
            ]
            self._profile_ids = temp.index.unique().tolist()
            self._profile_ids.sort()
            # TODO: what if there are no ranks in profiles?

    def _read_cct(
        self,
    ) -> None:
        with open(self._meta_file, "rb") as file:
            meta_db = file.read()

        (pContext,) = safe_unpack("<Q", meta_db, FILE_HEADER_OFFSET + 7 * 8)
        (pEntryPoints, nEntryPoints, szEntryPoint) = safe_unpack(
            "<QHB", meta_db, pContext
        )

        for i in range(nEntryPoints):
            (szChildren, pChildren, ctxId, entryPoint) = safe_unpack(
                "<QQLH",
                meta_db,
                pEntryPoints,
                i,
                szEntryPoint,
            )

            if entryPoint == 1:
                if (
                    not self._parallel_profiles_mode
                    or self._min_application_percentage_time is not None
                ):
                    self._total_execution_time = self._summary_profile[ctxId][
                        self._time_metric
                    ]

                node = self._store_cct_node(
                    ctxId,
                    {"type": "entry", "name": "entry"},
                )
                self._parse_context(
                    pChildren,
                    szChildren,
                    node,
                    meta_db,
                )
                break

        dataframe = pd.DataFrame(self._profiles_data).set_index(["node", "profile"])

        if self._parallel_profiles_mode:
            metadata = self._profiles_metadata.loc[
                dataframe.index.get_level_values(1).unique().tolist()
            ]

        else:
            try:
                nodes = int(self._dir_path.split("/")[-1].split("_")[-1])
            except Exception:
                nodes = 0
            metadata = {
                "date": datetime.utcfromtimestamp(
                    os.path.getmtime(self._dir_path)
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "file_path": self._dir_path,
                "nodes": nodes,
            }
            dataframe = dataframe.droplevel(level=1)

        inc_metrics = list(
            filter(lambda x: x.endswith("(inc)"), dataframe.columns.tolist())
        )

        exc_metrics = list(
            filter(lambda x: not x.endswith("(inc)"), dataframe.columns.tolist())
        )

        return GraphFrame(
            Graph(self._graph_roots),
            dataframe,
            inc_metrics=inc_metrics,
            exc_metrics=exc_metrics,
            default_metric=self._time_metric,
            metadata=metadata,
        )

    def _read_summary_profile(
        self,
    ) -> None:

        with open(self._profile_file, "rb") as file:
            file.seek(FILE_HEADER_OFFSET)
            formatProfileInfos = "<QQ"
            profile_db = file.read(struct.calcsize(formatProfileInfos))
            (szProfileInfos, pProfileInfos) = safe_unpack(
                formatProfileInfos, profile_db, 0
            )

            file.seek(pProfileInfos)
            profile_db = file.read(szProfileInfos)
            (pProfiles,) = safe_unpack("<Q", profile_db, 0)

            (nValues, pValues, nCtxs, _, pCtxIndices) = safe_unpack(
                "<QQLLQ", profile_db, pProfiles - pProfileInfos
            )

            file.seek(pCtxIndices)
            formatCtxs = "<LQ"
            cct_sub_db = file.read(nCtxs * struct.calcsize(formatCtxs))

            file.seek(pValues)
            formatValues = "<Hd"
            values_sub_db = file.read(nValues * struct.calcsize(formatValues))

            for i in range(nCtxs):
                (ctxId, startIndex) = safe_unpack("<LQ", cct_sub_db, 0, i)
                cct_id = ctxId

                if i == nCtxs - 1:
                    end_index = nValues
                else:
                    (_, end_index) = safe_unpack(formatCtxs, cct_sub_db, 0, i + 1)

                self._summary_profile[cct_id] = {}

                for j in range(startIndex, end_index):
                    (metricId, value) = safe_unpack("<Hd", values_sub_db, 0, j)

                    if metricId in self._metric_descriptions:
                        self._summary_profile[cct_id][
                            self._metric_descriptions[metricId]
                        ] = value

    def read(self) -> GraphFrame:
        self._read_metric_descriptions()
        if (
            not self._parallel_profiles_mode
            or self._min_application_percentage_time is not None
        ):
            self._read_summary_profile()

        if self._parallel_profiles_mode:
            self._read_profiles_metadata()

        return self._read_cct()
