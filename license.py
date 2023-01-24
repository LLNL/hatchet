# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT

from __future__ import print_function

import os
import re
from collections import defaultdict
import sys

#: SPDX license id must appear in the first <license_lines> lines of a file
license_lines = 7

#: Hatchet's license identifier
mit_spdx = "MIT"

#: regular expressions for licensed files.
licensed_files = [
    # hatchet docs
    r"^docs\/[^\/]*\.rst$",
    r"^docs/conf.py$",
    r"^docs/Makefile$",
    r"^docs\/examples\/.*\.py$",
    # hatchet source
    r"^pytest.ini",
    r"^hatchet\/[^\/]*\.py$",
    r"^hatchet/cython_modules/.*\.pyx$",
    r"^hatchet/cython_modules/.*\.py$",
    # hatchet external
    r"^hatchet/external/__init__.py",
    # hatchet readers and writers
    r"^hatchet/readers/.*\.py$",
    r"^hatchet/writers/.*\.py$",
    # hatchet tests
    r"^hatchet/tests/.*\.py$",
    # hatchet utils
    r"^hatchet/util/.*\.py$",
    # hatchet vis
    r"^hatchet/vis/.*\.py$",
]


def _all_hatchet_files(root="."):
    """Generates root-relative paths of all files in the hatchet repository."""
    visited = set()
    for cur_root, folders, files in os.walk(root):
        for filename in files:
            path = os.path.realpath(os.path.join(cur_root, filename))

            if path not in visited:
                yield os.path.relpath(path, root)
                visited.add(path)


def _licensed_files(root):
    for relpath in _all_hatchet_files(root):
        if any(regex.match(relpath) for regex in licensed_files):
            yield relpath


def list_files(root):
    """list files in hatchet that should have license headers"""
    for relpath in sorted(_licensed_files(root)):
        print(os.path.join(".", relpath))


# Error codes for license verification. All values are chosen such that
# bool(value) evaluates to True
OLD_LICENSE, SPDX_MISMATCH, GENERAL_MISMATCH = range(1, 4)

#: Latest year that copyright applies. UPDATE THIS when bumping copyright.
latest_year = 2023
strict_date = r"Copyright 2017-%s" % latest_year

#: regexes for valid license lines at tops of files
license_line_regexes = [
    r"Copyright 2017-(%d|%d) Lawrence Livermore National Security, LLC and other"
    % (latest_year - 1, latest_year),  # allow a little leeway: current or last year
    r"Hatchet Project Developers\. See the top-level LICENSE file for details.",
    r"SPDX-License-Identifier: MIT",
]


class LicenseError(object):
    def __init__(self):
        self.error_counts = defaultdict(int)

    def add_error(self, error):
        self.error_counts[error] += 1

    def has_errors(self):
        return sum(self.error_counts.values()) > 0

    def error_messages(self):
        total = sum(self.error_counts.values())
        missing = self.error_counts[GENERAL_MISMATCH]
        spdx_mismatch = self.error_counts[SPDX_MISMATCH]
        return (
            "%d improperly licensed files\n" % (total),
            "files with wrong SPDX-License-Identifier:   %d\n" % spdx_mismatch,
            "files not containing expected license:      %d\n" % missing,
        )


def _check_license(lines, path):

    found = []

    for line in lines:
        line = re.sub(r"^[\s#\%\.]*", "", line)
        line = line.rstrip()
        for i, line_regex in enumerate(license_line_regexes):
            if re.match(line_regex, line):
                # The first line of the license contains the copyright date.
                # We allow it to be out of date but print a warning if it is
                # out of date.
                if i == 0:
                    if not re.search(strict_date, line):
                        print("{}: copyright date mismatch".format(path))
                found.append(i)

    if len(found) == len(license_line_regexes) and found == list(sorted(found)):
        return

    def old_license(line, path):
        if re.search("This program is free software", line):
            print("{0}: has old LGPL license header".format(path))
            return OLD_LICENSE

    # If the SPDX identifier is present, then there is a mismatch (since it
    # did not match the above regex)
    def wrong_spdx_identifier(line, path):
        m = re.search(r"SPDX-License-Identifier: [^\n]*", line)
        if m and m.group(1) != mit_spdx:
            print(
                "{0}: SPDX license identifier mismatch"
                "(expecting {1}, found {2})".format(path, mit_spdx, m.group(1))
            )
            return SPDX_MISMATCH
        else:
            print("{0}: SPDX license identifier missing".format(path))
            return GENERAL_MISMATCH

    checks = [old_license, wrong_spdx_identifier]

    for line in lines:
        for check in checks:
            error = check(line, path)
            if error:
                return error

    print(
        "{0}: the license header at the top of the file does not match the"
        " expected format".format(path)
    )
    return GENERAL_MISMATCH


def verify(root):
    """verify that files in hatchet have the right license header"""

    license_errors = LicenseError()

    for relpath in _licensed_files(root):
        path = os.path.join(root, relpath)
        with open(path) as f:
            lines = [line for line in f][:license_lines]

        error = _check_license(lines, path)
        if error:
            license_errors.add_error(error)

    if license_errors.has_errors():
        print(*license_errors.error_messages())
        sys.exit(1)
    else:
        print("No license issues found.")
        return


if __name__ == "__main__":
    valid_options = ["list-files", "verify"]

    if len(sys.argv) != 2:
        print("Please specify a valid option: {}".format(valid_options))
        sys.exit()

    cmd = sys.argv[1]
    if cmd not in valid_options:
        print("Invalid argument. Valid options are {}".format(valid_options))
        sys.exit()

    licensed_files[:] = [re.compile(regex) for regex in licensed_files]
    root = os.path.dirname(os.path.abspath(__file__))

    if cmd == "list-files":
        list_files(root)
    elif cmd == "verify":
        verify(root)
