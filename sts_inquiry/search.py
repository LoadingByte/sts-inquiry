from typing import Any, Optional, Tuple, List, Set, Dict

from sts_inquiry import app, cache
from sts_inquiry.forms import SearchForm

_ROWS_PER_PAGE = app.config["ROWS_PER_PAGE"]
_PER_INST_COL_NAMES = ["instance", "nghbr_occupants", "region_occupants"]


def search(form: SearchForm, page: int, highlight_cluster_aids: Optional[Set[int]]):
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

        # If the user wants to view a specific cluster, find that cluster and go to the page its on.
        highlight_row_idx = None
        if highlight_cluster_aids:
            try:
                highlight_row_idx = df_out.index[df_out["aids"] == highlight_cluster_aids][0]
                page = highlight_row_idx // _ROWS_PER_PAGE + 1
            except IndexError:
                # In this case, highlight row idx will remain None.
                pass

        # Limit the amount of results to the current page.
        start_row = (page - 1) * _ROWS_PER_PAGE
        df_out = df_out.iloc[start_row:start_row + _ROWS_PER_PAGE]

        # Retroactively merge rows that contain the same cluster for different instances,
        # if they share the same sorting col values.
        df_out = _merge_instances(df, df_out, sort_cols)

        # Get the result away from Pandas so that we can release the lock.
        rows = list(df_out.itertuples())

        return cluster_size, page, highlight_row_idx, n_total_rows, rows


def _filter(df, form):
    if form.instance.used:
        df = df[df["instance"] == form.instance.data]

    if form.free.used:
        df = df[df["free"]]

    if form.nameincl.used:
        df = df[df["concat_names"].str.contains(form.nameincl.data, case=False, regex=True)]
    if form.nameexcl.used:
        df = df[~df["concat_names"].str.contains(form.nameexcl.data, case=False, regex=True)]

    if form.regions.used and not form.regions.data.all:
        filter_urids = set(form.regions.data.urids)
        filter_rids = set(form.regions.data.rids)
        if filter_urids and filter_rids:
            mask = [not filter_urids.isdisjoint(urids) or not filter_rids.isdisjoint(rids)
                    for urids, rids in zip(df["urids"], df["rids"])]
        elif filter_urids:
            mask = [not filter_urids.isdisjoint(urids) for urids in df["urids"]]
        else:
            mask = [not filter_rids.isdisjoint(rids) for rids in df["rids"]]
        df = df[mask]

    return df


def _sort(df, cluster_size: int, form):
    sort_cols, sort_orders = [], []
    for sortby_field in (form.sortby1, form.sortby2, form.sortby3, form.sortby4):
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
