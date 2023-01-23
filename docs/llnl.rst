.. Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
   Hatchet Project Developers. See the top-level LICENSE file for details.

   SPDX-License-Identifier: MIT

*****************************
Using Hatchet on LLNL Systems
*****************************

Hatchet installations are available on both Intel and IBM systems at Lawrence
Livermore National Laboratory.

To use one of these global installations, add the following to your Python
script or Jupyter notebook. This code allows you to use hatchet and its
dependencies.

.. code-block:: python
  :caption: Starter commands to find hatchet and its dependencies

  import sys
  import platform
  import datetime as dt
  from IPython.display import HTML, display

  input_deploy_dir_str = "/usr/gapps/spot/live/"
  machine = platform.uname().machine

  sys.path.append(input_deploy_dir_str + "/hatchet-venv/" + machine + "/lib/python3.7/site-packages")
  sys.path.append(input_deploy_dir_str + "/hatchet/" + machine)
  sys.path.append(input_deploy_dir_str + "/spotdb")

  import hatchet
  import spotdb


The following Python script loads a single SPOT/cali file into hatchet using
Hatchet's ``from_spotdb()``. This returns a list of hatchet ``GraphFrames``,
and we use ``pop()`` to access the single ``GraphFrame`` in the list.

.. code-block:: python
  :caption: Python script to load a single SPOT file into hatchet

  import sys
  import platform
  import datetime as dt
  from IPython.display import HTML, display

  input_deploy_dir_str = "/usr/gapps/spot/live/"
  machine = platform.uname().machine

  sys.path.append(input_deploy_dir_str + "/hatchet-venv/" + machine + "/lib/python3.7/site-packages")
  sys.path.append(input_deploy_dir_str + "/hatchet/" + machine)
  sys.path.append(input_deploy_dir_str + "/spotdb")

  import hatchet
  import spotdb

  input_db_uri_str = "./mpi"
  input_run_ids_str = "c5UcO9xwAUKNVVFg1_0.cali"

  db = spotdb.connect(input_db_uri_str)
  runs = input_run_ids_str.split(',')

  gfs = hatchet.GraphFrame.from_spotdb(db, runs)
  gf = gfs.pop()

  launchdate = dt.datetime.fromtimestamp(int(gf.metadata["launchdate"]))
  jobsize = int(gf.metadata.get("jobsize", 1))

  print("launchdate: {}, jobsize: {}".format(launchdate, jobsize))
  print(gf.tree())
  display(HTML(gf.dataframe.to_html()))


The following Python script loads multiple SPOT/cali files (most likely
contained in the same directory) into hatchet using Hatchet's
``from_spotdb()``. The files are specified as a single string, and commas
delineate each file. The result is a list of hatchet ``GraphFrames``, one for
each file.

.. code-block:: python
  :caption: Python script to load multiple SPOT files into hatchet

  import sys
  import platform
  import datetime as dt
  from IPython.display import HTML, display

  input_deploy_dir_str = "/usr/gapps/spot/live/"
  machine = platform.uname().machine

  sys.path.append(input_deploy_dir_str + "/hatchet-venv/" + machine + "/lib/python3.7/site-packages")
  sys.path.append(input_deploy_dir_str + "/hatchet/" + machine)
  sys.path.append(input_deploy_dir_str + "/spotdb")

  import hatchet
  import spotdb

  input_db_uri_str = "./mpi"
  input_run_ids_str = "./mpi/cQ-CGJlYj-uFT2yv-_0.cali,./mpi/cQ-CGJlYj-uFT2yv-_1.cali,./mpi/cQ-CGJlYj-uFT2yv-_2.cali"

  db = spotdb.connect(input_db_uri_str)
  runs = input_run_ids_str.split(',')

  gfs = hatchet.GraphFrame.from_spotdb(db, runs)

  for idx, gf in enumerate(gfs):
      launchdate = dt.datetime.fromtimestamp(int(gf.metadata["launchdate"]))
      jobsize = int(gf.metadata.get("jobsize", 1))
      print("launchdate: {}, jobsize: {}".format(launchdate, jobsize))
      print(gf.tree())
      display(HTML(gf.dataframe.to_html()))
