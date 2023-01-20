# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT


class InvalidQueryPath(Exception):
    """Raised when a query does not have the correct syntax"""


class InvalidQueryFilter(Exception):
    """Raised when a query filter does not have a valid syntax"""


class RedundantQueryFilterWarning(Warning):
    """Warned when a query filter does nothing or is redundant"""


class BadNumberNaryQueryArgs(Exception):
    """Raised when a query filter does not have a valid syntax"""
