from sqlite3 import DataError
from IPython.core.magic import Magics, magics_class, line_magic
from hatchet.external import Roundtrip as RT
from hatchet import GraphFrame
from os import path
from os.path import dirname

import json

vis_dir = dirname(path.abspath(__file__))


def _gf_to_json(data):
    try:
        if type(data) is type(GraphFrame):
            return json.dumps(data.to_literal())
        else:
            return json.dumps(data)
    except DataError:
        raise "Input data is not of type graphframe or json serializable."


def _query_to_dict(json_query):
    import json

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
