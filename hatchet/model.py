# Copyright 2017-2021 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from numpy.lib.function_base import append
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import extrap.entities as xte
import extrap.entities.experiment
from extrap.fileio import io_helper
from extrap.modelers.model_generator import ModelGenerator


class ModelWrapper:
    def __init__(self, mdl, param_name):
        self.mdl = mdl
        self.param_name = param_name

    def __str__(self):
        return str(self.mdl.hypothesis.function)

    def eval(self, val):
        return self.mdl.hypothesis.function.evaluate(val)

    def display(self):
        vals = [ms.value(True) for ms in self.mdl.measurements]
        params = [ms.coordinate[0] for ms in self.mdl.measurements]
        x_vals = np.arange(params[0], 1.5*params[-1], (params[-1] - params[0]) / 100.0)
        y_vals = [self.mdl.hypothesis.function.evaluate(x) for x in x_vals]

        fig = plt.figure()
        plt.plot(x_vals, y_vals, label=self.mdl.hypothesis.function)
        plt.plot(params, vals, 'ro', label=self.mdl.callpath)
        plt.xlabel(self.param_name)
        plt.ylabel(self.mdl.metric)
        plt.text(x_vals[0], max(y_vals + vals), 'AR2 = {0}'.format(self.mdl.hypothesis.AR2))
        plt.legend()

        plt.show()


class Modeling:
    """Produce models for all the metrics across the given graph frames.

    Adds a model column for each metric for each common frame across all the graph frames.
    The given list of params contains the parameters to build the models. For example, MPI
    ranks, input sizes, and so on. Assume that gfs[i] represents the measured call graph and
    values for params[i]. In case there were a number of repetitions for each benchmarking run,
    i.e., for each value of params[i], these all graph frames need to be reduced into one gfs[i]
    before this function is called.

    Arguments:
        gfs: a list of graph frames (assume index levels were dropped)
        params: parameters list
        all_met: all the metrics
    """

    def __init__(self, gfs, params, param_name, all_met=None, depth=10000):
        # Assume params are sorted
        assert(len(gfs) == len(params))

        self.gfs = [gf.copy() for gf in gfs]
        self.params = params
        self.param_name = param_name
        if not all_met:
            self.all_met = self.gfs[0].exc_metrics + self.gfs[0].inc_metrics
        self.models_df = None
        self.max_depth = depth

        # Unify all graphs
        for i in range(1, len(self.gfs)):
            self.gfs[0].unify(self.gfs[i])
    
        for i in range(1, len(self.gfs)):
            self.gfs[i].unify(self.gfs[0])

    def model_all(self):
        self.models_df = pd.DataFrame(index=pd.Index([], name='node'))
        self._traverse_sync([gf.graph for gf in self.gfs], roots = True)

    def _produce_extrap_models(self, nodes):
        # Prepare for adding new row to the models df
        curr_ind = list(self.models_df.index)
        curr_ind.append(nodes[0])
        # self.models_df = self.models_df.reindex(curr_ind, fill_value=object())
        self.models_df = self.models_df.reindex(curr_ind, fill_value=None)

        ex = xte.experiment.Experiment()
        ex.add_parameter(xte.parameter.Parameter(self.param_name))
        # If we're modeling MPI functions timing over increasing core count, then
        # we need to skip serial code (core count equals 1)
        skip_idx = -1

        for i, p in enumerate(self.params):
            if self.param_name == 'cores' and p == 1:
                skip_idx = i
                continue
            ex.coordinates.append(xte.coordinate.Coordinate(float(p)))

        for m in self.all_met:
            vals = []
            for i, n in enumerate(nodes):
                if i == skip_idx:
                    continue
                v = self.gfs[i].dataframe.loc[n, m]
                if not np.isnan(v):
                    vals.append(v)
            if len(vals) < len(ex.coordinates):
                if nodes[0] in self.models_df.index:
                    self.models_df = self.models_df.drop(nodes[0])
                continue
            xm = xte.metric.Metric(m)
            ex.add_metric(xte.metric.Metric(m))
            # Assume name column is called 'name':
            node_name = self.gfs[0].dataframe.loc[nodes[0], 'name']
            cpath = xte.callpath.Callpath(node_name)
            ex.add_callpath(cpath)
            ex.call_tree = io_helper.create_call_tree(ex.callpaths)
            for coord, v in zip(ex.coordinates, vals):
                msr = xte.measurement.Measurement(coord, cpath, xm, v)
                ex.add_measurement(msr)
            io_helper.validate_experiment(ex)
            model_gen = ModelGenerator(ex)
            model_gen.model_all()
            mkey = (cpath, xm)
            self.models_df.at[nodes[0], m + '_model'] = \
                ModelWrapper(model_gen.models[mkey], self.param_name)

    def _traverse_sync(self, nodes, roots = False, visited_l = None):
        if not visited_l:
            visited_l = [None for n in nodes]
        for i in range(len(visited_l)):
            if not visited_l[i]:
                visited_l[i] = set()
        cdicts = []
        for i, n in enumerate(nodes):
            if not roots:
                visited_l[i].add(n._hatchet_nid)
            arr = []
            if roots:
                arr = n.roots
            else:
                arr = n.children
            dc = {child.frame: child for child in arr}
            cdicts.append(dc)

        if roots:
            arr = nodes[0].roots
        else:
            arr = nodes[0].children
        for child in arr:
            if child._depth >= self.max_depth:
                break
            child_nodes = []
            child_nodes.append(child)
            for j in range(1, len(cdicts)):
                if child.frame in cdicts[j]:
                    child_nodes.append(cdicts[j][child.frame])

            if any([child in vs for child, vs in zip(child_nodes, visited_l)]):
                continue

            # recursive call
            self._produce_extrap_models(child_nodes)
            self._traverse_sync(child_nodes, False, visited_l)
