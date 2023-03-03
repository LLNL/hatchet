#ifdef __cplusplus
extern "C" {
#endif

void subtract_exclusive_metric_vals (const long nid, const long parent_nid,
        const long num_stmt_nodes, const long stride, double* metrics)
{
    long ref_nid = nid;
    long ref_pnid = parent_nid;
    for (long i = 0; i < num_stmt_nodes; i++) {
        metrics[ref_pnid-1] -= metrics[ref_nid-1];
        ref_nid += stride;
        ref_pnid += stride;
    }
}

#ifdef __cplusplus
}
#endif
