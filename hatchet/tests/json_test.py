# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from hatchet import GraphFrame


def test_read_json(json_graphframe_specification):
    jgs = ""
    with open(json_graphframe_specification, "r") as f:
        jgs = f.read()
    gf = GraphFrame.from_json(jgs)

    assert len(gf.dataframe) == 24
    assert len(gf.graph) == 24
    assert gf.graph.roots[0].frame["name"] == "foo"


def test_write_json(json_graphframe_specification):
    jgs = ""
    with open(json_graphframe_specification, "r") as f:
        jgs = f.read()
    gf = GraphFrame.from_json(jgs)
    json_out = gf.to_json()

    assert "".join(sorted("".join(sorted(jgs.split())))) == "".join(
        sorted("".join(json_out.split()))
    )
