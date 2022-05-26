# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import numpy as np
import pandas as pd
from scipy import stats
import hatchet as ht


class BoxPlot:
    def __init__(
        self,
        multi_index_gf,
        drop_index_levels=[],
        metrics=[],
    ):
        """
        Boxplot class computes the runtime distributions of a multi-indexed GraphFrame.


        Arguments:
            multi_index_gf: (ht.GraphFrame) Target GraphFrame.
            drop_index_levels (Optional): (list) List of columns to aggregate the boxplot
            computation.
            metrics (Optional): (list) List of metrics to compute.

        Return: None
        """
        assert isinstance(multi_index_gf, ht.GraphFrame)
        assert isinstance(drop_index_levels, list)
        assert isinstance(metrics, list)

        # Reset the indexes in the dataframe.
        self.multi_index_gf = multi_index_gf.copy()
        self.multi_index_gf.dataframe = self.multi_index_gf.dataframe.reset_index()
        self.multi_index_gf.dataframe["_hatchet_nid"] = self.multi_index_gf.dataframe[
            "node"
        ].apply(lambda _: _._hatchet_nid)

        self.drop_indexes, self.output_indexes = BoxPlot.validate_drop_index_level(
            multi_index_gf, drop_index_levels
        )
        self.metrics = BoxPlot.validate_metrics(multi_index_gf, metrics)

        self.agg_columns = ["_hatchet_nid"] + self.output_indexes
        self.output_columns = list(
            set(self.multi_index_gf.dataframe.columns)
            .difference(set(self.agg_columns))
            .difference(set(self.metrics))
        )

        # Compute the boxplot dictionary keyed by "index" and valued as a dataframe.
        self.boxplot_df_dict = BoxPlot.compute(
            multi_index_df=self.multi_index_gf.dataframe,
            groupby=self.agg_columns,
            cols=self.output_columns,
            metrics=self.metrics,
        )

        # Convert it to a GraphFrame.
        self.gf = self.to_gf()

    @staticmethod
    def validate_drop_index_level(
        multi_index_gf: ht.GraphFrame, drop_index_levels: list
    ):
        df_index_levels = list(multi_index_gf.dataframe.index.names)

        # Validate primary index is 'node'.
        if "node" not in df_index_levels:
            raise Exception(
                "ht.util.BoxPlot expects the primary index of `multi_index_gf` to be `ht.Graph.Node`."
            )

        # Validate drop_index in the dataframe, if provided.
        if len(drop_index_levels) > 0:
            for _index in drop_index_levels:
                if _index not in df_index_levels:
                    raise Exception(
                        f"'drop_index_level: {_index}' is not a valid index of 'multi_index_gf'."
                    )
        elif len(drop_index_levels) == 0:
            # Validate if only 2 indexes are provided. Else, warn the user to pass `drop_column`.
            if len(df_index_levels) > 2:
                raise Exception(
                    f"multi_index_gf contains {len(df_index_levels)} indexes = {df_index_levels}. ht.util.BoxPlot is limited to processing GraphFrames with 2 indexes. Please specify the `drop_index` by which BoxPlot API will compute the distribution to avoid ambiguity."
                )
            elif len(df_index_levels) == 2:
                drop_index_levels = [multi_index_gf.dataframe.index.names[1]]

        # Drop the 'node' and `drop_index_levels` from the
        # ht.GraphFrame.DataFrame's indexes.
        df_index_levels.remove("node")
        for index in drop_index_levels:
            df_index_levels.remove(index)

        return drop_index_levels, df_index_levels

    @staticmethod
    def validate_metrics(multi_index_gf: ht.GraphFrame, metrics: list):
        # Validate metrics are columns in the dataframe, if provided.
        if len(metrics) > 0:
            for metric in metrics:
                if metric not in multi_index_gf.dataframe.columns:
                    raise Exception(f"{metric} not found in the gf.dataframe.")

        if len(metrics) == 0:
            return multi_index_gf.inc_metrics + multi_index_gf.exc_metrics
        return metrics

    @staticmethod
    def df_groupby(df, groupby, cols):
        """
        Group the dataframe by groupby column.

        Arguments:
            df (graphframe): self's graphframe
            groupby: groupby columns on dataframe
            cols: columns from the dataframe

        Return:
            (dict): A dictionary of dataframes (columns) keyed by groups.
        """
        _df = df.set_index(groupby)
        _levels = _df.index.unique().tolist()
        return {_df.xs(_)["nid"].unique().tolist()[0]: _df.xs(_)[cols] for _ in _levels}

    @staticmethod
    def outliers(data, scale=1.5, side="both"):
        """
        Calculate outliers from the data.

        Arguments:
            data (np.ndarray or pd.Series): Array of values.
            scale (float): IQR range for outliers.
            side (str): directions for calculating the outliers, i.e., left,
            right, both.

        Return:
            outliers (np.ndarray): Array of outlier values.
        """
        assert isinstance(data, (pd.Series, np.ndarray))
        assert len(data.shape) == 1
        assert isinstance(scale, float)
        assert side in ["gt", "lt", "both"]

        d_q13 = np.percentile(data, [25.0, 75.0])
        iqr_distance = np.multiply(stats.iqr(data), scale)

        if side in ["gt", "both"]:
            upper_range = d_q13[1] + iqr_distance
            upper_outlier = np.greater(data - upper_range.reshape(1), 0)

        if side in ["lt", "both"]:
            lower_range = d_q13[0] - iqr_distance
            lower_outlier = np.less(data - lower_range.reshape(1), 0)

        if side == "gt":
            return upper_outlier
        if side == "lt":
            return lower_outlier
        if side == "both":
            return np.logical_or(upper_outlier, lower_outlier)

    @staticmethod
    def compute(multi_index_df, groupby, metrics, cols):
        """
        Compute boxplot quartiles and statistics.

        Arguments:
            multi_index_df: Dataframe to calculate the boxplot information.
            groupby: Columns to aggregate the data.
            cols: Columns to retain in the output dataframe.

        Return:
            ret (dict): {
                "metric1": {
                    "q": (array) quartiles (i.e., [q0, q1, q2, q3, q4]),
                    "ometric": (array) outlier from metric,
                    "ocat": (array) outlier from cat_column,
                    "d": (array) metric values,
                    "rng": (tuple) (min, max),
                    "uv": (tuple) (mean, variance),
                    "imb": (number) imbalance,
                    "ks": (tuple) (kurtosis, skewness)
                }
            }
        """
        group_df_dict = BoxPlot.df_groupby(
            df=multi_index_df,
            groupby=groupby,
            cols=cols + metrics,
        )

        boxplot_dict_df = {_: {} for _ in group_df_dict.keys()}
        for callsite, callsite_df in group_df_dict.items():
            ret = {_: {} for _ in metrics}
            for tk, tv in zip(metrics, metrics):
                q = np.percentile(callsite_df[tv], [0.0, 25.0, 50.0, 75.0, 100.0])
                mask = BoxPlot.outliers(callsite_df[tv])
                mask = np.where(mask)[0]

                _data = callsite_df[tv].to_numpy()
                _min, _mean, _max = _data.min(), _data.mean(), _data.max()
                _var = _data.var() if _data.shape[0] > 0 else 0.0
                _imb = (_max - _mean) / _mean if not np.isclose(_mean, 0.0) else _max
                _skew = stats.skew(_data)
                _kurt = stats.kurtosis(_data)

                # TODO: Outliers and their corresponding rank member is not being
                # fetched accurately.
                # _outliers = df[tv].to_numpy()[mask]

                ret[tk] = {
                    "q": q,
                    # "ometric": _outliers,
                    # "ocat": df.index[1] if len(_outliers) > 0 else -1, # not being used in the vis yet.
                    "d": _data,
                    "rng": (_min, _max),
                    "uv": (_mean, _var),
                    "imb": _imb,
                    "ks": (_kurt, _skew),
                }

                for _column in cols:
                    ret[tk][_column] = callsite_df[_column].iloc[0]

            boxplot_dict_df[callsite] = ret

        return boxplot_dict_df

    def to_json(self):
        """
        Unpack the boxplot data into JSON format.

        Arguments:

        Return:
            result (dict): {
                "callsite1": {
                    "tgt": self._unpack_callsite,
                    "bkg": self._unpack_callsite
                },
            }
        """
        return {
            callsite: self._unpack_callsite(callsite)
            for callsite in self.boxplot_df_dict.keys()
        }

    def _unpack_callsite(self, callsite):
        """
        Helper function to unpack the data by callsite.

        Arguments:
            callsite: Callsite's name
            with_htnode: (bool) An option to add hatchet.Node to the dict.

        Return:
            ret (dict): {
                "metric": {
                    "q": (array) quartiles (i.e., [q0, q1, q2, q3, q4]),
                    "ocat": (array) outlier from cat_column, (TODO)
                    "ometric": (array) outlier from metri, (TODO)
                    "min": (number) minimum,
                    "max": (number) maximum,
                    "mean": (number) mean,
                    "var": (number) variance,
                    "imb": (number) imbalance,
                    "kurt": (number) kurtosis,
                    "skew": (number) skewness,
                }
            }
        """
        ret = {}
        for metric in self.metrics:
            box = self.boxplot_df_dict[callsite][metric]
            ret[metric] = {
                "q": box["q"].tolist(),
                # "ocat": box["ocat"], # TODO
                # "ometric": box["ometric"].tolist(), # TODO
                "min": box["rng"][0],
                "max": box["rng"][1],
                "mean": box["uv"][0],
                "var": box["uv"][1],
                "imb": box["imb"],
                "kurt": box["ks"][0],
                "skew": box["ks"][1],
            }

            for _column in self.output_columns:
                ret[metric][_column] = box[_column]

        return ret

    def _to_gf_by_metric(self, gf, metric):
        """
        Wrapper function to unpack the boxplot data into Hatchet.GraphFrame by
        respective metric.

        Argument:
            gf: (hatchet.GraphFrame) GraphFrame
            metric: (string) Metric

        Return:
            hatchet.GraphFrame with boxplot information as columns.

        """
        _dtype = {
            "name": str,
            "q": object,
            # "ocat": object, # TODO
            # "ometric": object, # TODO
            "min": np.float64,
            "max": np.float64,
            "mean": np.float64,
            "var": np.float64,
            "imb": np.float64,
            "kurt": np.float64,
            "skew": np.float64,
        }
        _dict = {
            callsite: self._unpack_callsite(callsite)[metric]
            for callsite in self.boxplot_df_dict.keys()
        }
        tmp_df = pd.DataFrame.from_dict(data=_dict).T
        tmp_df = tmp_df.astype(_dtype)
        tmp_df.index.names = self.agg_columns
        tmp_df.reset_index(inplace=True)

        tmp_df = tmp_df.drop(columns=self.drop_indexes + ["_hatchet_nid"])
        tmp_df.set_index(["node"] + self.output_indexes, inplace=True)

        # TODO: Would we need to squash the graph. (Check in the to_gf() method.)
        # Call into the gf.groupby_aggregate() (in PR) before returning the gf.
        return ht.GraphFrame(gf.graph, tmp_df, gf.exc_metrics, gf.inc_metrics)

    def to_gf(self):
        """
        Unpack the boxplot data into GraphFrame object.

        Note: In this case, only the hatchet.dataframe will be updated, with
        hatchet.Graph being the same as the input gf.

        Arguments:

        Return:
            (dict) : {
                "metric": hatchet.GraphFrame, ...
            }
        """
        return {
            metric: self._to_gf_by_metric(self.multi_index_gf, metric)
            for metric in self.metrics
        }
