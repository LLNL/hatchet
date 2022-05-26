# Copyright 2017-2022 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
from io import StringIO


class Timer(object):
    """Simple phase timer with a context manager."""

    def __init__(self):
        self._phase = None
        self._start_time = None
        self._times = OrderedDict()

    def start_phase(self, phase):
        now = datetime.now()
        delta = None

        if self._phase:
            delta = now - self._start_time
            self._times[self._phase] = delta

        self._phase = phase
        self._start_time = now
        return delta

    def end_phase(self):
        assert self._phase and self._start_time

        now = datetime.now()
        delta = now - self._start_time
        if self._times.get(self._phase):
            self._times[self._phase] = self._times.get(self._phase) + delta
        else:
            self._times[self._phase] = delta

        self._phase = None
        self._start_time = None

    def __str__(self):
        out = StringIO()
        out.write("Times:\n")
        for phase, delta in self._times.items():
            out.write("    %-20s %.2fs\n" % (phase + ":", delta.total_seconds()))
        return out.getvalue()

    @contextmanager
    def phase(self, name):
        self.start_phase(name)
        yield
        self.end_phase()
