# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from bs4 import BeautifulSoup
from os import walk, path

static_filepath = path.abspath("static/")

for (pt, dirs, files) in walk(static_filepath):
    for file in files:
        if ".html" in file:
            with open(path.join(static_filepath, file), "r") as f:
                html = f.read()
                soup = BeautifulSoup(html)
                soup.script["src"] = path.join(static_filepath, file[0:-5] + ".js")
                with open(path.join(static_filepath, file), "w") as writer:
                    writer.write(soup.prettify())
