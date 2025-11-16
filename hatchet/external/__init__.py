# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT


class VersionError(Exception):
    """
    Define a version error class with the same features of the base exception class.
    Allows us to catch the very specific ipython version error and throw a warning.
    """

    pass


try:
    import IPython

    # Testing IPython version
    if int(IPython.__version__.split(".")[0]) > 7:
        raise VersionError()

    from .roundtrip.roundtrip.manager import Roundtrip

    # Refrencing Roundtrip here to resolve scope issues with import
    Roundtrip

except ImportError:
    pass

except VersionError:
    if IPython.get_ipython() is not None:
        print(
            "Warning: Roundtrip module could not be loaded. Requires jupyter notebook version <= 7.x."
        )
