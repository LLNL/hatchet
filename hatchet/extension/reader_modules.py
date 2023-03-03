import ctypes
import numpy as np
import numpy.ctypeslib as npct

array_1d_double = npct.ndpointer(
    dtype=np.double,
    ndim=1,
    flags="CONTIGUOUS"
)

libreader_mods = npct.load_library(
    "libreader_modules",
    "."
)

libreader_mods.subtract_exclusive_metric_vals.restype = None
libreader_mods.subtract_exclusive_metric_vals.argtypes = [
    ctypes.c_long,   # nid
    ctypes.c_long,   # parent_nid
    ctypes.c_long,   # num_stmt_nodes
    ctypes.c_long,   # stride
    array_1d_double, # metrics
]


def subtract_exclusive_metric_vals(nid, parent_nid,
                                   metrics, num_stmt_nodes, stride):
    return libreader_mods.subtract_exclusive_metric_vals(
        nid,
        parent_nid,
        num_stmt_nodes,
        stride,
        metrics,
    )
