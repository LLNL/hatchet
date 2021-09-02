from ..graphframe import GraphFrame

from itertools import groupby
import pandas as pd

def unify_ensemble(gf_list):

    # Taken from the Python Itertools Recipes page:
    # https://docs.python.org/3/library/itertools.html#itertools-recipes
    def all_equal(iterable):
        "Returns True if all the elements are equal to each other"
        g = groupby(iterable)
        return next(g, True) and not next(g, False)

    if not all_equal([gf.graph for gf in gf_list]):
        raise ValueError("\"unify_ensemble\" requires all graphs to be equal")
    unify_df = pd.DataFrame()
    for i, gf in enumerate(gf_list):
        curr_df = gf.dataframe.copy()
        if gf.dataset is not None:
            curr_df["dataset"] = gf.dataset
        else:
            curr_df["dataset"] = "gframe_{}".format(i)
        unify_df = pd.concat([curr_df, unify_df], sort=True)
    unify_gf = GraphFrame(graph=gf_list[0].graph, dataframe=unify_df)
    return unify_gf
