#!/bin/bash

python3 -m pip install meson[ninja] meson-python Cython

python3 -m pip install --no-build-isolation -e .