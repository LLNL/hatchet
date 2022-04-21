from IPython.display import Javascript, HTML, display
from IPython import get_ipython
from bs4 import BeautifulSoup

import io
import tokenize
import json
import inspect
import os
import sys


def _default_converter(data):
    """
    The default converter from an active python datatype to
    a string encoding for transfer to JavaScript.

    :param data: The python varaible/object we are encoding.
    :returns: A string representation of the variable/object which was passed.

    TODO: Raise error if unconvertable.
    """

    if data is None:
        return "{}"
    elif type(data) in [type(""), type(0), type(0.0)]:
        return str(data)
    elif type(data) in [type({}), type([])]:
        return json.dumps(data)
    elif "DataFrame" in str(type(data)) or "Series" in str(type(data)):
        return data.to_json()
    return data


def _default_from_converter(data):
    """
    The default converter from a string representation of JavaScript data.
    Does not do any conversion right now but is required for the javascript code.

    :param data: The string representation of the JavaScript object/data we are decoding.
    :returns: The string representation of the JavaScript object/data passed in.

    """
    return data


class RoundTrip:
    """
    Core Roundtrip class.

    Instantiated as a singleton object "Roundtrip", inside of this file.

    Calls all necessary ipython functions required to load javascript and
    web files. Additionally, it keeps track of python-code specific watched cells
    in the jupyter notebook.

    Most implementation details of automatic running and data binding are deferred
    to the roundtrip object in roundtrip.js.
    """

    def __init__(self, ipy_shell=get_ipython(), test=False):
        """
        Initialize our singelton roundtrip instance.

        :param ipy_shell: The current Jupyter shell.

        TODO: Throw an error if attempting to run outside of a Jupyter notebook.
        """

        if sys.version_info[0] < 3:
            print(
                "Warning: Your Roundtrip visualizations may not load properly. Roundtrip only supports Python v3.x.x. You are using Python v{}.{}.{}".format(
                    sys.version_info[0], sys.version_info[1], sys.version_info[2]
                )
            )

        self.shell = ipy_shell
        self.tags = {
            "script": "<script src='{src}'></script>",
            "style": "<link rel='stylesheet' href='{src}'>",
        }
        self.line = "{tags}\n"
        self.bridges = {}
        self.last_id = None
        self.watched = {}
        self.scrid = 0
        self.relative_html_caches = {}
        self.istest = test

        js_directory = os.path.dirname(os.path.realpath(__file__))

        # Load the javascript roundtrip object upon creation of the python object
        with open(os.path.join(js_directory, "roundtrip.js"), "r") as f:
            script = f.read()

        if test is not True:
            display(Javascript(script))
        else:
            self.rt_js = Javascript(script)
            display(self.rt_js)

    script_map = {"csv": "text/csv", "json": "text/json"}

    def _get_file_type(self, file):
        """
        Get the file extenstion from the filename by retireving the string after the last '.'

        :param file: A string of the format <filename>.<ext>
        """
        return file.split(".")[-1]

    def _file_formatter(self, file):
        ft = self._get_file_type(file)
        if ft in self.script_map.keys():
            tag = self.tags["script"].format(src=file, type=self.script_map[ft])
            return self.line.format(tags=tag)
        if ft == "css":
            tag = self.tags["style"].format(src=file)
            return self.line.format(tags=tag)
        elif ft == "html":
            return open(file).read()

    def load_webpack(self, file, cache=True):
        """
        The primary interface for loading visualizations.

        :param file: A html file containg refrences to all the required javascript required for a visualization to run.
            This html file should be constructed using the HTMLWebpackPlugin with a "public path" defined in the webpack.config.js,
            to simplify the difficulty of routing to find/load local files relative to the location of the visualization extension code.
            See the example_webpack.config.js provided in the roundtrip directory.
        """
        output_html = ""

        # use generic javascript loading for these now
        if cache is False or file not in self.relative_html_caches:
            output_html += self._file_formatter(file)
            html = BeautifulSoup(output_html, "html.parser")
            for tag in html.select("script"):
                # TODO: Add option for server based loading with this
                # So JS can be dynamically loaded
                # tag['src'] = os.path.relpath(tag['src'], self.shell.user_ns['_dh'][0])
                t = tag.extract()
                with open(t["src"]) as f:
                    src = f.read()
                    scrpt = html.new_tag("script")
                    scrpt.string = src
                    html.select("head")[0].append(scrpt)

            output_html = str(html)
            self.relative_html_caches[file] = {"html": output_html}
        else:
            output_html = self.relative_html_caches[file]["html"]

        # This line is needed to expose the current `element` to the webpack bundled scripts as though
        # the scripts were run using display(Javascript()).
        scope_var = """
                    <script id="script-{id}">
                        var element = document.getElementById("script-{id}").parentNode;
                    </script>""".format(
            id=self.scrid
        )
        output_html = scope_var + output_html

        bdg = Bridge(output_html, ipy_shell=self.shell, test=self.istest)

        self.scrid += 1

        self.bridges[bdg.id] = bdg
        self.last_id = bdg.id

        return id

    def load_web_files(self, files):
        """
        The secondary interface for loading visualizations, included for simple visualizations and
        legacy support.

        :param file: A list of filepaths to be loaded into the visualization. These files load
            in-order. So be sure to manage dependencies between scripts correctly by specifying
            dependant scripts after their dependencies.

        """
        output_html = ""

        # this initial string is where variable bindings go
        scripts = [""]

        scope_tag = """
                    <div id="locator-{id}">
                    </div>
            """.format(
            id=self.scrid
        )

        locator_script = (
            'var element = document.getElementById("locator-{id}").parentNode;'.format(
                id=self.scrid
            )
        )

        output_html += scope_tag
        scripts.append(locator_script)

        # load files based on their individual properties
        for file in files:
            ft = self._get_file_type(file)
            if ft == "js":
                scripts.append(open(file).read())
            else:
                output_html += self._file_formatter(file)

        bdg = Bridge(output_html, scripts, self.shell, self.istest)
        self.bridges[bdg.id] = bdg
        self.last_id = bdg.id

        return id

    # Passing to JS is working now
    def data_to_js(
        self,
        data,
        js_variable,
        to_js_converter=_default_converter,
        from_js_converter=_default_from_converter,
    ):
        """
        Pass python data, one-way, into the Javascript Roundtrip oject for retireval in
        loaded visualization/gui code. Intended primarily for passing down data initalized
        within the local scope of a visualization loader.

        :param data: The data to be passed down, can be a variable or literal.
        :param js_variable: String of the key where the data can be found on the window.Roundtrip object in the javascript code.
        :param to_js_converter: Function which defines how to convert the data in 'data' into a serilaizable string format like JSON.
            This function takes one argument "data" and returns a string.
        :param from_js_converter: Function which defines how to convert a string in an specific encoding to an active Python object
            This function takes one argument "data", a string and returns either a python object or the string itself.
        """
        self.bridges[self.last_id].pass_to_js(
            js_variable,
            data,
            py_to_js_converter=to_js_converter,
            js_to_py_converter=from_js_converter,
        )

    # consider seperating watchable and reloadable?
    def var_to_js(
        self,
        jup_var,
        js_variable,
        watch=False,
        to_js_converter=_default_converter,
        from_js_converter=_default_from_converter,
    ):
        """
        Bind a variable in the Jupyter notebook scope to a member of the Roundtrip JS object.

        If 'watch' is True, this binding will propogate data changes to the variable in the Jupyter Notebook
        to the JavaScript code and will also propogate changes to the associated member of the JS Roundtrip object back up to
        the notebook. Changes made under this watch will also cause all cells associated with 'jup_var' and
        annotated with a '?' operator to be automically refreshed and re-run.

        Otherwise it will pass the data in jup_var down one-way like data_to_jS.

        :param jup_var: A string containing the name of a variable in the Jupyter Notebook namespace.
        :param js_variable: String of the key where the data can be found on the window.Roundtrip object in the javascript code.
        :param watch: A boolean which specifies if the two-way binding of the data in jup_var and auto-updating of this cell should be turned on or not.
        :param to_js_converter: Function which defines how to convert the data in 'data' into a serilaizable string format like JSON.
            This function takes one argument "data" and returns a string.
        :param from_js_converter: Function which defines how to convert a string in an specific encoding to an active Python object
            This function takes one argument "data", a string and returns either a python object or the string itself.
        """
        if jup_var[0] == "?":
            if watch is False:
                print(
                    """WARNING:
                        This magic function does not support automatic reloading.
                        Please remove the '?' character in front of '{0}'.
                        """.format(
                        jup_var[1:]
                    )
                )
                watch = "false"
            else:
                watch = "true"

            jup_var = jup_var[1:]

            if (
                jup_var in self.watched.keys()
                and js_variable not in self.watched[jup_var]["js_var"]
            ):
                self.watched[jup_var]["js_var"].append(js_variable)
            else:
                self.watched[jup_var] = {
                    "converter": to_js_converter,
                    "js_var": [js_variable],
                }
        else:
            watch = "false"

        if jup_var not in self.shell.user_ns:
            self.shell.user_ns[jup_var] = None

        data = self.shell.user_ns[jup_var]

        self.bridges[self.last_id].pass_to_js(
            js_variable,
            data,
            two_way=watch,
            python_var=jup_var,
            py_to_js_converter=to_js_converter,
            js_to_py_converter=from_js_converter,
        )

    def manage_jupter_change(self):
        """
        Callback function which runs after a cell is executed.

        Checks to see if a watched variable in a visualization is upaded in the regular python notebook code. Triggers the re-running of all cells
        which have the "?" before the updated variable as an argument to a roundtrip magic function. Also, propogates the data change to the JavaScript code.

        """

        tokens = [
            token
            for token in tokenize.tokenize(
                io.BytesIO(self.shell.user_ns["_ih"][-1].encode("utf-8")).readline
            )
        ]
        assignment_tokens = [
            "=",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "//=",
            "**=",
            "&=",
            "|=",
            "^=",
            ">>=",
            "<<=",
        ]
        update_flags = {}
        update_hook = """\n (function(){{
                                window.Roundtrip[\'{js_var}\'] = {{
                                    \'data\': \'{data}\',
                                    \'python_var\': \'{var}\',
                                    \'origin\': \'PYASSIGN\'
                                }};
                            }})();\n"""
        code = ""

        for var in self.watched.keys():
            for i, token in enumerate(tokens):
                if token.string == var:
                    lookahead = i
                    while (
                        lookahead < len(tokens)
                        and tokenize.tok_name[tokens[lookahead].type] != "NEWLINE"
                    ):
                        if tokens[lookahead].string in assignment_tokens:
                            update_flags[var] = True
                            break
                        else:
                            lookahead += 1

                    if var in update_flags.keys():
                        break

        for flag in update_flags:
            new_data = self.watched[flag]["converter"](self.shell.user_ns[flag])
            for var in self.watched[flag]["js_var"]:
                code += update_hook.format(js_var=var, data=new_data, var=flag)
        if code != "":
            display(Javascript(code))

    def fetch_data(self, js_var, ipy_var, converter=_default_from_converter):
        """
        Retrieves data from the javascript Roundtrip object.

        :param js_var: String containing the key in the Javascript roundtrip object where the desired data can be found
        :param ipy_var: A String containing the name of a variable in the Jupyter notebook namespace where the retrieved data can be stored
        """
        self.bridges[self.last_id].retrieve_from_js(js_var, ipy_var, converter)

    def initialize(self):
        """
        Function which manages the running and loading of specificed visualization files, data, and variable bindings. Should be called last in
        a visualization magic function.
        """
        self.bridges[self.last_id].run()


class Bridge:
    def __init__(self, html, js=None, ipy_shell=get_ipython(), test=False):
        self.html = html
        self.scripts = js
        self.shell = ipy_shell
        self.display = display(HTML(""), display_id=True)
        self.id = self.display.display_id
        self.converter = _default_converter
        self.istest = test

        if self.istest:
            self.active_scripts = []
            self.active_html = None

    def _extract_simple_dt(self, dt_str):
        return dt_str.split("'")[1]

    def run(self):
        if not self.istest:
            display(HTML(self.html))
        else:
            new_HTML = HTML(self.html)
            self.active_html = new_HTML
            self.display.update(new_HTML)

        if self.scripts is not None:
            js_exe = ""
            for script in self.scripts:
                js_exe += script

            if not self.istest:
                display(Javascript(js_exe))
            else:
                new_Javascript = Javascript(js_exe)
                self.active_scripts.append(new_Javascript)
                display(new_Javascript)

    def add_javascript(self, code):
        if not self.istest:
            display(Javascript(code))
        else:
            new_Javascript = Javascript(code)
            self.active_scripts.append(new_Javascript)
            display(new_Javascript)

    # put down explicit write notification (maybe)
    # watch errors with user documentation
    # run some stress tests on this
    # with weird waits for java script
    # watch gives us an explicit way to link views
    def pass_to_js(
        self,
        js_variable,
        data,
        two_way="false",
        python_var="",
        datatype=None,
        py_to_js_converter=None,
        js_to_py_converter=None,
    ):
        # This may have a race condition; keep an eye on that.
        pass_hook = """\n (function(){{
            window.Roundtrip[\'{js_var}\'] = {{
                \'origin\': \'INIT\',
                \'two_way\': {binding},
                \'python_var\':\'{py_var}\',
                \'type\':\'{type}\',
                \'data\':\'{data}\',
                \'converter\':{converter},
            }};
        }})();\n"""

        if datatype is None:
            datatype = type(data)
            datatype = self._extract_simple_dt(str(datatype))

        try:
            # some default conversion
            # we may want to push this off to the application
            # developer
            if py_to_js_converter is None:
                data = self._default_converter(data)
            else:
                data = py_to_js_converter(data)
                self.converter = py_to_js_converter
        except Exception:
            pass

        # Patch: Ensure all ' and " are escaped
        data = data.replace('"', '\\"').replace("'", "\\'")

        conv_spec = None

        if js_to_py_converter is not None:
            conv_spec = {
                "name": js_to_py_converter.__name__,
                "code": inspect.getsource(js_to_py_converter),
            }

        self.add_javascript(
            pass_hook.format(
                js_var=js_variable,
                binding=two_way,
                py_var=python_var,
                type=datatype,
                data=data,
                converter=json.dumps(conv_spec),
            )
        )

    def retrieve_from_js(self, js_variable, notebook_var, converter):
        # TODO: add validator(s)

        hook_template = """
            (function(){{
                    var holder = Roundtrip['{src}'];
                    holder = `\'${{holder}}\'`;
                    var code = {converter_code};
                    code += `\n{dest} = {converter_name}(${{holder}})`;
                    IPython.notebook.kernel.execute(code, {{
                                                            shell:{{
                                                                reply: function(r){{
                                                                    //consider putting this in a reserved jupyter variable
                                                                    if(r.content.status == \'error\'){{
                                                                        console.error(`${{r.content.ename}} in JS->Python coversion: \n ${{r.content.evalue}}`);
                                                                    }}
                                                                }}
                                                            }}
                                                        }}
                                                    );
                    }})()
               """
        hook = hook_template.format(
            src=str(js_variable),
            dest=str(notebook_var),
            converter_code=json.dumps(inspect.getsource(converter)),
            converter_name=converter.__name__,
        )

        if not self.istest:
            display(Javascript(hook))
        else:
            new_Javascript = Javascript(hook)
            self.active_scripts.append(new_Javascript)
            display(new_Javascript)
        # self.add_javascript(hook)


# Singelton declaration of the roundtrip object.
Roundtrip = RoundTrip()
if Roundtrip.shell is not None:
    Roundtrip.shell.events.register("post_run_cell", Roundtrip.manage_jupter_change)
