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


def _query_to_dict(json_query):
    import json

    return json_query

    return json.loads(json_query)


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
            args[0], "hatchet_tree_def", watch=False, to_js_converter=_gf_to_json
        )

        RT.initialize()

    @line_magic
    def cct_fetch_query(self, line):
        args = line.split(" ")

        RT.fetch_data("jsNodeSelected", args[0], converter=_query_to_dict)


def load_ipython_extension(ipython):
    ipython.register_magics(CCT)
