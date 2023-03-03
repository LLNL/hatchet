#include <stdlib.h>
#include <stdbool.h>

#define INDEX(array, num_cols, row_idx, col_idx) array[row_idx*num_cols + col_idx]

#ifdef __cplusplus
extern "C" {
#endif

void insert_one_for_self_nodes (const long snio_len,
        short* self_missing_node, const long* snio_indices)
{
    for (long i = 0; i < snio_len; i++)
        self_missing_node[snio_indices[i]] = 1;
}

static int compare_vals (const void* key, const void* arr_mem)
{
    return (*(unsigned long long*) key - *(unsigned long long*) arr_mem);
}

void fast_not_isin (const unsigned long long* arr1,
        const unsigned long long* arr2, const long arr1_rlen,
        const long arr1_clen, const long arr2_rlen,
        const long arr2_clen, bool* result)
{
    unsigned long long* bsearch_out = NULL;
    unsigned long long prior = -1;
    long i = 0;
    unsigned long long arr2_0[arr2_rlen];
    for (long j = 0; j < arr2_rlen; j++)
        arr2_0[j] = INDEX(arr2, arr2_clen, j, 0);
    for (i = 0; i < arr1_rlen; i++) {
        if (prior == INDEX(arr1, arr1_clen, i, 0)) {
            result[INDEX(arr1, arr1_clen, i, 1)] = result[INDEX(arr1, arr1_clen, (i-1), 1)];
        } else {
            bsearch_out = (unsigned long long*) bsearch (
                (void*)&INDEX(arr1, arr1_clen, i, 0),
                (const void*) arr2_0,
                (size_t) arr2_rlen,
                sizeof(unsigned long long),
                compare_vals
            );
            result[INDEX(arr1, arr1_clen, i, 1)] = (bsearch_out == NULL);
        }
    }
    prior = INDEX(arr1, arr1_clen, i, 0);
}

#ifdef __cplusplus
}
#endif
