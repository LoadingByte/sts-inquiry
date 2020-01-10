from typing import Any, Tuple, List, Dict

from sts_inquiry import app, cache
from sts_inquiry.forms import SearchForm

_ROWS_PER_PAGE = app.config["ROWS_PER_PAGE"]
_PER_INST_COL_NAMES = ["instance", "nghbr_occupants", "region_occupants"]


def search(form: SearchForm, page: int):
    with cache.LOCK:
        # Get the appropriate df for the selected cluster size.
        cluster_size = form.clustersize.data
        df = cache.dfs[cluster_size - 1]

        # Filter and sort the df according to the user inputs.
        df = _filter(df, form)
        df, sort_cols = _sort(df, cluster_size, form)

        # For now, just remove the duplicates created by each cluster having multiple rows, one for each instance.
        # Note that we keep the first one, i.e., the winner of the sorting.
        df_out = df.drop_duplicates("cid")

        # Add a meaningful rank number (= index).
        df_out = df_out.reset_index()

        n_total_rows = df_out.shape[0]

        # Limit the amount of results to the current page.
        start_row = (page - 1) * _ROWS_PER_PAGE
        df_out = df_out.iloc[start_row:start_row + _ROWS_PER_PAGE]

        # Retroactively merge rows that contain the same cluster for different instances,
        # if they share the same sorting col values.
        df_out = _merge_instances(df, df_out, sort_cols)

        # Get the result away from Pandas so that we can release the lock.
        rows = list(df_out.itertuples())

        return cluster_size, n_total_rows, rows


def _filter(df, form):
    if form.instance.used:
        df = df[df["instance"] == form.instance.data]

    if form.free.used:
        df = df[df["free"]]

    if form.name.used:
        df = df[df["concat_names"].str.contains(form.name.data, case=False, regex=False)]

    if form.regions.used:
        region_filter = set(form.regions.data)  # hopefully, computing this first is better for performance.
        df = df[[bool(regions_ids.intersection(region_filter)) for regions_ids in df["rids"]]]

    return df


def _sort(df, cluster_size: int, form):
    sort_cols, sort_orders = [], []
    for sortby_field in [form.sortby1, form.sortby2, form.sortby3]:
        if sortby_field.used:
            sort_col, sort_order = sortby_field.data.split("-")
            sort_cols.append(sort_col)
            sort_orders.append(sort_order == "asc")

    # Also sort the results by name if we're searching for individual stws
    if cluster_size == 1:
        sort_cols.append("concat_names")
        sort_orders.append("asc")

    if sort_cols:
        # We use mergesort because that is stable and the instance merging later on
        # requires stability for the instances to be in proper order.
        df = df.sort_values(sort_cols, ascending=sort_orders, kind="mergesort")

    return df, sort_cols


def _merge_instances(df, df_out, sort_cols: List[str]):
    seen_cids: Dict[int, Tuple[Any, int]] = {}

    new_cols = {col_name: [] for col_name in _PER_INST_COL_NAMES}
    new_idx_ctr = 0

    for idx, row in enumerate(df[df["cid"].isin(df_out["cid"])].itertuples()):
        if row.cid not in seen_cids:
            seen_cids[row.cid] = (row, new_idx_ctr)
            new_idx_ctr += 1

            for col_name in _PER_INST_COL_NAMES:
                new_cols[col_name].append(str(getattr(row, col_name)))
        else:
            seen_row, seen_new_idx = seen_cids[row.cid]
            if all(getattr(row, sc) == getattr(seen_row, sc) for sc in sort_cols):
                for col_name in _PER_INST_COL_NAMES:
                    new_cols[col_name][seen_new_idx] += "|" + str(getattr(row, col_name))

    return df_out.assign(**new_cols)
