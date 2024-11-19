# Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import os
    
HATCHET_PERF_ENV_VAR = "HATCHET_PERF_PLUGIN"
    
_HATCHET_PERF_PLUGIN = "none"
_HATCHET_PERF_ENABLED = False
if HATCHET_PERF_ENV_VAR in os.environ:
    if os.environ[HATCHET_PERF_ENV_VAR].lower() == "caliper":
        try:
            from pycaliper import annotate_function
            from pycaliper.instrumentation import begin_region, end_region
            
            _HATCHET_PERF_PLUGIN = "caliper"
            _HATCHET_PERF_ENABLED = True
        except Exception:
            print("User requested Caliper annotations, but could not import Caliper")
    elif os.environ[HATCHET_PERF_ENV_VAR].lower() == "perfflowaspect":
        try:
            import perfflowaspect.aspect
            
            _HATCHET_PERF_PLUGIN = "perfflowaspect"
            _HATCHET_PERF_ENABLED = True
        except Exception:
            print("User requested PerfFlow Aspect annotations, but could not import Caliper")
    else:
        print("'{}' is an invalid value for {}. Not enabling performance annotations".format(os.environ[HATCHET_PERF_ENV_VAR], HATCHET_PERF_ENV_VAR))


def annotate(name=None, fmt=None):
    def inner_decorator(func):
        if not _HATCHET_PERF_ENABLED:
            return func
        else:
            real_name = name
            if name is None or name == "":
                real_name = func.__name__
            if fmt is not None and fmt != "":
                real_name = fmt.format(real_name)
            if _HATCHET_PERF_PLUGIN == "caliper":
                return annotate_function(name=real_name)(func)
            elif _HATCHET_PERF_PLUGIN == "perfflowaspect":
                return perfflowaspect.aspect.critical_path(pointcut="around")(func)
            else:
                return func

    return inner_decorator


def begin_code_region(name):
    if _HATCHET_PERF_ENABLED:
        if _HATCHET_PERF_PLUGIN == "caliper":
            begin_region(name)
            return


def end_code_region(name):
    if _HATCHET_PERF_ENABLED:
        if _HATCHET_PERF_PLUGIN == "caliper":
            end_region(name)
            return
