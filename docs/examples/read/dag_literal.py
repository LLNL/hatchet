#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import hatchet as ht


if __name__ == "__main__":
    # Define a literal GraphFrame using a list of dicts.
    gf = ht.GraphFrame.from_literal(
        [
            {
                "frame": {"name": "foo"},
                "metrics": {"time (inc)": 130.0, "time": 0.0},
                "children": [
                    {
                        "frame": {"name": "bar"},
                        "metrics": {"time (inc)": 20.0, "time": 5.0},
                        "children": [
                            {
                                "frame": {"name": "baz"},
                                "metrics": {"time (inc)": 5.0, "time": 5.0},
                            },
                            {
                                "frame": {"name": "grault"},
                                "metrics": {"time (inc)": 10.0, "time": 10.0},
                            },
                        ],
                    },
                    {
                        "frame": {"name": "qux"},
                        "metrics": {"time (inc)": 60.0, "time": 0.0},
                        "children": [
                            {
                                "frame": {"name": "quux"},
                                "metrics": {"time (inc)": 60.0, "time": 5.0},
                                "children": [
                                    {
                                        "frame": {"name": "corge"},
                                        "metrics": {"time (inc)": 55.0, "time": 10.0},
                                        "children": [
                                            {
                                                "frame": {"name": "bar"},
                                                "metrics": {
                                                    "time (inc)": 20.0,
                                                    "time": 5.0,
                                                },
                                                "children": [
                                                    {
                                                        "frame": {"name": "baz"},
                                                        "metrics": {
                                                            "time (inc)": 5.0,
                                                            "time": 5.0,
                                                        },
                                                    },
                                                    {
                                                        "frame": {"name": "grault"},
                                                        "metrics": {
                                                            "time (inc)": 10.0,
                                                            "time": 10.0,
                                                        },
                                                    },
                                                ],
                                            },
                                            {
                                                "frame": {"name": "grault"},
                                                "metrics": {
                                                    "time (inc)": 10.0,
                                                    "time": 10.0,
                                                },
                                            },
                                            {
                                                "frame": {"name": "garply"},
                                                "metrics": {
                                                    "time (inc)": 15.0,
                                                    "time": 15.0,
                                                },
                                            },
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "frame": {"name": "waldo"},
                        "metrics": {"time (inc)": 50.0, "time": 0.0},
                        "children": [
                            {
                                "frame": {"name": "fred"},
                                "metrics": {"time (inc)": 35.0, "time": 5.0},
                                "children": [
                                    {
                                        "frame": {"name": "plugh"},
                                        "metrics": {"time (inc)": 5.0, "time": 5.0},
                                    },
                                    {
                                        "frame": {"name": "xyzzy"},
                                        "metrics": {"time (inc)": 25.0, "time": 5.0},
                                        "children": [
                                            {
                                                "frame": {"name": "thud"},
                                                "metrics": {
                                                    "time (inc)": 25.0,
                                                    "time": 5.0,
                                                },
                                                "children": [
                                                    {
                                                        "frame": {"name": "baz"},
                                                        "metrics": {
                                                            "time (inc)": 5.0,
                                                            "time": 5.0,
                                                        },
                                                    },
                                                    {
                                                        "frame": {"name": "garply"},
                                                        "metrics": {
                                                            "time (inc)": 15.0,
                                                            "time": 15.0,
                                                        },
                                                    },
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            },
                            {
                                "frame": {"name": "garply"},
                                "metrics": {"time (inc)": 15.0, "time": 15.0},
                            },
                        ],
                    },
                ],
            },
            {
                "frame": {"name": "?????? (hoge)"},
                "metrics": {"time (inc)": 30.0, "time": 0.0},
                "children": [
                    {
                        "frame": {"name": "(?????? (piyo)"},
                        "metrics": {"time (inc)": 15.0, "time": 5.0},
                        "children": [
                            {
                                "frame": {"name": "?????? (fuga)"},
                                "metrics": {"time (inc)": 5.0, "time": 5.0},
                            },
                            {
                                "frame": {"name": "????????? (hogera)"},
                                "metrics": {"time (inc)": 5.0, "time": 5.0},
                            },
                        ],
                    },
                    {
                        "frame": {"name": "???????????? (hogehoge)"},
                        "metrics": {"time (inc)": 15.0, "time": 15.0},
                    },
                ],
            },
        ]
    )

    # Printout the DataFrame component of the GraphFrame.
    print(gf.dataframe)

    # Printout the graph component of the GraphFrame.
    # Because no metric parameter is specified, ``time`` is used by default.
    print(gf.tree())
