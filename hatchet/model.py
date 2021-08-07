# Copyright 2017-2021 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import extrap.entities as xte
import extrap.entities.experiment
from extrap.fileio import io_helper
from extrap.modelers.model_generator import ModelGenerator


# class StubModel:
#     def __init__(self, l):
#         self._vals = l
    
#     def __str__(self):
#         return str(self._vals)

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

    def __init__(self, gfs, params, param_name, all_met):
        # Assume params are sorted
        assert(len(gfs) == len(params))

        self.gfs = gfs
        self.params = params
        self.param_name = param_name
        self.all_met = all_met

    def model_all(self):
        for gf in self.gfs:
            for m in self.all_met:
                gf.dataframe[m + '_model'] = [object] * len(gf.dataframe.index)

        self._traverse_sync([gf.graph for gf in self.gfs], roots = True)

    def evaluate_value(self, model, val):
        return model.hypothesis.function.evaluate(val)

    def display_model(self, model):
        vals = [ms.value(True) for ms in model.measurements]
        x_vals = np.arange(self.params[0], 1.5*self.params[-1], (self.params[-1] - self.params[0]) / 100.0)
        y_vals = [model.hypothesis.function.evaluate(x) for x in x_vals]

        fig = plt.figure()
        plt.plot(x_vals, y_vals, label=model.hypothesis.function)
        plt.plot(self.params, vals, 'ro', label=model.callpath)
        plt.xlabel(self.param_name)
        plt.ylabel(model.metric)
        plt.text(x_vals[0], max(y_vals + vals), 'AR2 = {0}'.format(model.hypothesis.AR2))
        plt.legend()

        plt.show()

    # def _produce_models(self, nodes):
    #     for m in self.all_met:
    #         vals = [self.gfs[i].dataframe.loc[n, m] for i, n in enumerate(nodes)]
    #         for i, n in enumerate(nodes):
    #             self.gfs[i].dataframe.at[n, m + '_model'] = StubModel(vals)

    def _produce_extrap_models(self, nodes):
        ex = xte.experiment.Experiment()
        ex.add_parameter(xte.parameter.Parameter(self.param_name))
        ex.coordinates.extend([xte.coordinate.Coordinate(float(p)) for p in self.params])
        for m in self.all_met:
            vals = [self.gfs[i].dataframe.loc[n, m] for i, n in enumerate(nodes)]
            xm = xte.metric.Metric(m)
            ex.add_metric(xte.metric.Metric(m))
            cpath = xte.callpath.Callpath(nodes[0].frame.attrs['name'])
            ex.add_callpath(cpath)
            ex.call_tree = io_helper.create_call_tree(ex.callpaths)
            for coord, v in zip(ex.coordinates, vals):
                msr = xte.measurement.Measurement(coord, cpath, xm, v)
                ex.add_measurement(msr)
            io_helper.validate_experiment(ex)
            model_gen = ModelGenerator(ex)
            model_gen.model_all()
            mkey = (cpath, xm)
            # func_arr = []
            for i, n in enumerate(nodes):
                self.gfs[i].dataframe.at[n, m + '_model'] = model_gen.models[mkey] #.hypothesis.function

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
            dc = {}
            arr = []
            if roots:
                arr = n.roots
            else:
                arr = n.children
            for child in arr:
                dc[child.frame] = child
            cdicts.append(dc)
        
        arr = []
        if roots:
            arr = nodes[0].roots
        else:
            arr = nodes[0].children
        for child in arr:
            child_nodes = []
            child_nodes.append(child)
            for i in range(1, len(cdicts)):
                if child.frame in cdicts[i]:
                    child_nodes.append(cdicts[i][child.frame])
                else:
                    break
            if len(child_nodes) == len(nodes):
                if any([child in vs for child, vs in zip(child_nodes, visited_l)]):
                    continue
                # recursive call
                # self._produce_models(child_nodes)
                self._produce_extrap_models(child_nodes)
                self._traverse_sync(child_nodes, False, visited_l)

