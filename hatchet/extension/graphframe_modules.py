import ctypes
import numpy as np
import numpy.ctypeslib as npct

array_1d_short = npct.ndpointer(
    dtype=np.short,
    ndim=1,
    flags="CONTIGUOUS"
)
array_1d_long = npct.ndpointer(
    dtype=np.int_,
    ndim=1,
    flags="CONTIGUOUS"
)
array_2d_ulonglong = npct.ndpointer(
    dtype=np.ulonglong,
    ndim=2,
    flags="CONTIGUOUS"
)
array_1d_bool = npct.ndpointer(
    dtype=np.bool_,
    ndim=1,
    flags="CONTIGUOUS"
)

libgf_mods = npct.load_library(
    "libgraphframe_modules",
    "."
)

libgf_mods.insert_one_for_self_nodes.restype = None
libgf_mods.insert_one_for_self_nodes.argtypes = [
    ctypes.c_long,  # snio_len
    array_1d_short, # self_missing_node
    array_1d_long,  # snio_indices
]

libgf_mods.fast_not_isin.restype = None
libgf_mods.fast_not_isin.argtypes = [
    array_2d_ulonglong,  # arr1
    array_2d_ulonglong,  # arr2
    ctypes.c_long,       # arr1_rlen
    ctypes.c_long,       # arr1_clen
    ctypes.c_long,       # arr2_rlen
    ctypes.c_long,       # arr2_clen
    array_1d_bool,       # result
]

def insert_one_for_self_nodes(snio_len, self_missing_node, snio_indices):
    return libgf_mods.insert_one_for_self_nodes(
        snio_len,
        self_missing_node,
        snio_indices,
    )


def fast_not_isin(arr1, arr2):
    result = np.zeros(len(arr1), dtype=np.bool_)
    libgf_mods.fast_not_isin(
        arr1,
        arr2,
        arr1.shape[0],
        arr1.shape[1],
        arr2.shape[0],
        arr2.shape[1],
        result,
    )
    return result
