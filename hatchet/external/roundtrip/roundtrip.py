from __future__ import print_function
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.display import HTML, Javascript, display
import os
import jsonschema

"""
   File: roundtrip.py
   Purpose: Pass data between Jupyter Python cells and
   Javascript variables.
   Hatchet-specific.
"""


@magics_class
class Roundtrip(Magics):

    # Note to self: Custom magic classes MUST call parent's constructor
    def __init__(self, shell):
        super(Roundtrip, self).__init__(shell)
        global VIS_TO_FILE, VIS_TO_VALIDATION, VIS_TO_DATA

        VIS_TO_FILE = {"literal_tree": "roundtripTree.js", "boxplot": "boxplot.js"}
        VIS_TO_VALIDATION = {
            "literal_tree": self._validate_literal_tree,
            "boxplot": self._validate_boxplot,
        }
        VIS_TO_DATA = {"literal_tree": "jsNodeSelected", "boxplot": "variance_df"}

        self.id_number = 0
        # Clean up namespace function
        display(
            HTML(
                "<script>function cleanUp() { argList =[]; element = null; cell_idx = -1}</script>"
            )
        )

    inputType = {
        "js": "text/javascript",
        "csv": "text/csv",
        "html": "text/html",
        "json": "text/json",
        "css": "text/css",
    }

    codeMap = {}

    def cleanLineArgument(self, arg):
        if '"' in arg:
            return arg.replace('"', "")
        elif "'" in arg:
            return arg.replace("'", "")
        else:
            # Path is a variable from the nb namespace
            return self.shell.user_ns[arg]

    @line_magic
    def loadVisualization(self, line):
        # Get command line args for loading the vis.
        args = line.split(" ")
        # Clean up the input arguments.
        path = self.cleanLineArgument(args[0])
        visType = self.cleanLineArgument(args[1])
        data = self.shell.user_ns[args[2]]

        if visType not in VIS_TO_FILE.keys():
            assert f"Invalid visualization type provided. Valid types include {''.join(VIS_TO_FILE.keys())}"

        # Set a name to visualization cell.
        name = "roundtripTreeVis" + str(self.id_number)

        # Read the appropriate JS file.
        fileAndPath = os.path.join(path, VIS_TO_FILE[visType])
        javascriptFile = open(fileAndPath).read()

        # Source input files
        # Set up the object to map input files to what javascript expects
        argList = "<script> var argList = []; var elementTop = null; var cell_idx = -1;</script>"

        displayObj = display(HTML(argList), display_id=True)

        displayObj.update(Javascript('argList.push("' + str(path) + '")'))
        displayObj.update(Javascript('argList.push("' + str(visType) + '")'))
        displayObj.update(Javascript('argList.push("' + str(data) + '")'))

        VIS_TO_VALIDATION[visType](data)

        # Get curent cell id.
        self.codeMap[name] = javascriptFile

        preRun = """
        // Grab current context
        elementTop = element.get(0);"""
        displayObj.update(Javascript(preRun))

        self.runVis(name, javascriptFile, visType)
        self.id_number += 1

    def _validate_literal_tree(self, data):
        # Check that users provided a tree literal
        if not isinstance(data, list):
            print(
                """The argument is not a tree literal or it is not a valid Python list. Please check that you have provided a list of nodes and nested children of the following form to loadVisualization:
                    literal_tree = [{
                        "frame": {"name": "foo", "type": "function"},
                        "metrics": {"time (inc)": 130.0, "time": 0.0},
                        "children":[ . . . ]
                    },
                    {
                        "frame": {"name": "bar", "type": "function"},
                        "metrics": {"time (inc)": 30.0, "time": 0.0},
                        "children":[ . . . ]
                    }]
            """
            )
            raise Exception("Bad argument")

    def _validate_boxplot(self, data):
        STATS_SCHEMA = {
            "type": "object",
            "properties": {
                "min": {"type": "number"},
                "max": {"type": "number"},
                "mean": {"type": "number"},
                "imb": {"type": "number"},
                "var": {"type": "number"},
                "kurt": {"type": "number"},
                "skew": {"type": "number"},
                "q": {"type": "array"},
                "ocat": {"type": "array"},
                "ometric": {"type": "array"},
                "nid": {"type": "string"},
                "node": {"type": "object"},
            },
        }

        if isinstance(data, dict):
            callsites = data.keys()
            for cs in callsites:
                if isinstance(data[cs], dict):
                    boxplotTypes = data[cs].keys()
                    for boxplotType in boxplotTypes:
                        if boxplotType in ["tgt", "bgk"]:
                            for metric in data[cs][boxplotType]:
                                jsonschema.validate(
                                    instance=data[cs][boxplotType][metric],
                                    schema=STATS_SCHEMA,
                                )
                        else:
                            self._print_exception_boxplot()
                            raise Exception(
                                "Incorrect boxplot type key provided. Use 'tgt' or 'bgk'."
                            )
                else:
                    self._print_exception_boxplot()
                    raise Exception("Bad argument.")
        else:
            self._print_exception_boxplot()
            raise Exception("Bad argument.")

    def _print_exception_boxplot(self):
        print(
            """The argument is not a valid boxplot dictionary. Please check that
            you have provided the data in the following form to
            loadVisualization:
            boxplot = {
                "tgt" : {
                    "metric1": {
                        "min": number,
                        "max": number,
                        "mean": number,
                        "imb": number,
                        "kurt": number,
                        "skew": number,
                        "q": [q0, q1, q2, q3, q4],
                        "outliers: {
                            "values": array,
                            "keys": array
                        }
                    },
                    "metric2": {
                        ...
                    }
                },
                "bkg": {
                    // Refer "tgt" key.
                }
            }
        """
        )

    def runVis(self, name, javascriptFile, visType):
        name = "roundtripTreeVis" + str(self.id_number)

        javascriptExport = """
            <div id=\"{0}\">
            </div>
            <script>
                var jsNodeSelected = "";
                elementTop.appendChild(document.getElementById('{1}'));
                var element = document.getElementById('{1}');
                {2}
            </script>
        """.format(
            name, str(name), javascriptFile
        )
        display(HTML(javascriptExport))

    @line_magic
    def fetchData(self, line):
        # added eval() to 'execute' the JS list-as-string as a Python list

        # Get command line args for loading the vis.
        args = line.split(" ")
        visType = self.cleanLineArgument(args[0])
        dest = args[1]

        hook = (
            """
                var holder = """
            + VIS_TO_DATA[visType]
            + """;
                holder = '"' + holder + '"';
                console.debug('"""
            + str(dest)
            + """ = '+ holder);
                IPython.notebook.kernel.execute('"""
            + str(dest)
            + """ = '+ eval(holder));
            """
        )

        display(Javascript(hook))

        return display(Javascript(hook))


# Function to make module loading possible
def load_ipython_extension(ipython):
    ipython.register_magics(Roundtrip)
