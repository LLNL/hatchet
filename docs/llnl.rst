.. Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
   Hatchet Project Developers. See the top-level LICENSE file for details.

   SPDX-License-Identifier: MIT

*****************************
Using Hatchet on LLNL Systems
*****************************

Hatchet installations are available on both Intel and IBM systems at Lawrence
Livermore National Laboratory.

To use one of these global installations, please add the following to your
Python script or Jupyter notebook. This code allows you to use hatchet and its
dependencies.

.. code-block:: python
  :caption: Starter commands to find hatchet and its dependencies

  import sys
  import platform
  from IPython.display import HTML, display

  machine = platform.uname().machine

  sys.path.append(input_deploy_dir_str + "/hatchet-venv/" + machine + "/lib/python3.7/site-packages")
  sys.path.append(input_deploy_dir_str + "/hatchet/" + machine)
  sys.path.append(input_deploy_dir_str + "/spotdb")

  import datetime as dt
  import hatchet
  import spotdb


.. code-block:: python
  :caption: Load single SPOT file into hatchet

  import sys
  import platform
  from IPython.display import HTML, display

  machine = platform.uname().machine

  sys.path.append(input_deploy_dir_str + "/hatchet-venv/" + machine + "/lib/python3.7/site-packages")
  sys.path.append(input_deploy_dir_str + "/hatchet/" + machine)
  sys.path.append(input_deploy_dir_str + "/spotdb")

  import datetime as dt
  import hatchet
  import spotdb

  input_deploy_dir_str = "/usr/gapps/spot/live/"
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


.. code-block:: python
  :caption: Load multiple SPOT files into hatchet

  import sys
  import platform
  from IPython.display import HTML, display

  machine = platform.uname().machine

  sys.path.append(input_deploy_dir_str + "/hatchet-venv/" + machine + "/lib/python3.7/site-packages")
  sys.path.append(input_deploy_dir_str + "/hatchet/" + machine)
  sys.path.append(input_deploy_dir_str + "/spotdb")

  import datetime as dt
  import hatchet
  import spotdb

  input_deploy_dir_str = "/usr/gapps/spot/live/"
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
