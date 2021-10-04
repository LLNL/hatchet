from hatchet import GraphFrame

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
        raise ValueError('"unify_ensemble" requires all graphs to be equal')
    unify_df = pd.DataFrame()
    inc_metrics = []
    exc_metrics = []
    for i, gf in enumerate(gf_list):
        inc_metrics.extend(gf.inc_metrics)
        exc_metrics.extend(gf.exc_metrics)
        curr_df = gf.dataframe.copy()
        if gf.dataset is not None:
            curr_df["dataset"] = gf.dataset
        else:
            curr_df["dataset"] = "gframe_{}".format(i)
        unify_df = pd.concat([curr_df, unify_df], sort=True)
    index_names = list(unify_df.index.names)
    unify_df.reset_index(inplace=True)
    index_names.append("dataset")
    unify_df["hatchet_nid"] = unify_df["node"].apply(lambda x: x._hatchet_nid)
    unify_df.sort_values(by="hatchet_nid", inplace=True)
    unify_df.drop("hatchet_nid", axis=1)
    unify_df.set_index(index_names, inplace=True)
    inc_metrics = list(set(inc_metrics))
    exc_metrics = list(set(exc_metrics))
    unify_gf = GraphFrame(
        graph=gf_list[0].graph,
        dataframe=unify_df,
        inc_metrics=inc_metrics,
        exc_metrics=exc_metrics,
    )
    return unify_gf
