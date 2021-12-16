import os
import sys
from IPython.testing.globalipapp import start_ipython

from hatchet.external.roundtrip.roundtrip.manager import RoundTrip

no_rt = False
if sys.version_info[0] < 3:
    no_rt = True

local_dir = os.path.dirname(os.path.abspath(__file__))

ip = start_ipython()

if not no_rt:
    RT = RoundTrip(ipy_shell=ip, test=True)


def test_init_load_web_files():
    if not no_rt:
        # verify that the RT Javascript was loaded
        assert (
            open(os.path.join(local_dir, "../roundtrip.js"), "r").read()
            in RT.rt_js._repr_javascript_()
        )

        # test loading multiple files
        RT.load_web_files(
            [
                str(os.path.join(local_dir, "data/test.html")),
                str(os.path.join(local_dir, "data/test.js")),
            ]
        )

        assert len(RT.bridges) != 0

        RT.initialize()

        for b in RT.bridges:
            for s in RT.bridges[b].active_scripts:
                assert (
                    open(os.path.join(local_dir, "data/test.js"), "r").read()
                    in s._repr_javascript_()
                )


def test_data_transfer():
    if not no_rt:
        js_var_down = "data_from_py"
        js_var_up = "data_to_py"

        RT.data_to_js(5, js_variable=js_var_down)
        RT.fetch_data(js_var_up, "retrieved_from_js")

        down = False
        up = False

        for b in RT.bridges:
            for s in RT.bridges[b].active_scripts:
                if (
                    "window.Roundtrip['{}']".format(js_var_down)
                    in s._repr_javascript_()
                ):
                    down = True
                elif "Roundtrip['{}']".format(js_var_up) in s._repr_javascript_():
                    up = True

        assert down is True
        assert up is True


def test_var_transfer():
    if not no_rt:
        js_var_down = "var_from_py"
        js_var_up = "var_to_py"
        py_var = "var_test"

        down = False
        up = False

        # load a var in the user namespace
        ip.run_cell(raw_cell="{} = 1".format(py_var))

        RT.var_to_js(py_var, js_variable=js_var_down)
        RT.fetch_data(js_var_up, "retrieved_from_js")

        for b in RT.bridges:
            for s in RT.bridges[b].active_scripts:
                if (
                    "window.Roundtrip['{}']".format(js_var_down)
                    in s._repr_javascript_()
                    and py_var in s._repr_javascript_()
                ):
                    down = True
                elif "Roundtrip['{}']".format(js_var_up) in s._repr_javascript_():
                    up = True

        assert down is True
        assert up is True
