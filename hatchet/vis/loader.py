# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from IPython.core.magic import Magics, magics_class, line_magic
from hatchet.external import Roundtrip as RT
from hatchet import GraphFrame
from os import path
from os.path import dirname


vis_dir = dirname(path.abspath(__file__))


def _gf_to_json(data):
    import json
    from pandas import Series

    def serialize(obj):
        if isinstance(obj, Series):
            return obj.to_json
        return obj.__dict__

    try:
        if isinstance(data, GraphFrame):
            return json.dumps(data.to_literal(), default=serialize)
        else:
            with open("check", "w") as f:
                f.write(json.dumps(data, default=serialize))
            return json.dumps(data, default=serialize)
    except ValueError:
        raise "Input data is not of type graphframe or json serializable."

def _pass_through(json_query):
    return json_query

def _query_to_dict(json_query):
    import json
    return json.loads(json_query)

def _to_js(data):
    if data is None:
        return "{}"
    return data.to_json()

def _selection_to_js(data):
    if data is None:
        return "{}"
    return data['selection']

def _from_js(data):
    import json
    import pandas as pd
    data = json.loads(data)
    return pd.DataFrame(data)


@magics_class
class CCT(Magics):
    def __init__(self, shell):
        super(CCT, self).__init__(shell)
        self.vis_dist = path.join(vis_dir, "static")

    @line_magic
    def cct(self, line):
        args = line.split(" ")

        RT.load_webpack(path.join(self.vis_dist, "cct_bundle.html"), cache=False)
        RT.var_to_js(
            args[0], "hatchet_tree_def", watch=True, to_js_converter=_gf_to_json
        )

        if(len(args) > 1):
            RT.var_to_js(
                args[1], "node_query", watch=True, from_js_converter=_query_to_dict
            )
        
        #secret configuration var
        RT.var_to_js(
            "?vis_state", "visualization_state", watch=True, from_js_converter=_query_to_dict
        )

        RT.initialize()

    @line_magic
    def table(self, line):
        args = line.split(" ")

        RT.load_webpack(path.join(self.vis_dist, "table_bundle.html"), cache=False)

        self.shell.user_ns[args[0][1:]].drop_index_levels()
        if(len(args) > 1 and self.shell.user_ns[args[1][1:]]):
            self.shell.user_ns['df'] = self.shell.user_ns[args[0][1:]].filter(self.shell.user_ns[args[1][1:]]['selection']).dataframe
        elif(len(args) == 1):
            self.shell.user_ns['df'] = self.shell.user_ns[args[0][1:]].dataframe


        RT.var_to_js(
            'df',
            "table_src",
            watch=True,
            to_js_converter=_to_js
        )

        RT.var_to_js(
            args[0],
            "reload_watcher",
            watch=True,
            to_js_converter=_gf_to_json
        )

        RT.var_to_js(
            args[1],
            "query_watcher",
            watch=True,
            to_js_converter=_selection_to_js
        )

        RT.initialize()

    @line_magic
    def cct_fetch_query(self, line):
        args = line.split(" ")

        RT.fetch_data("jsNodeSelected", args[0], converter=_pass_through)


def load_ipython_extension(ipython):
    ipython.register_magics(CCT)
