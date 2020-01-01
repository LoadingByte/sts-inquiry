from threading import Lock
from typing import Optional, List
from urllib.parse import urlencode

import numpy as np
from flask import request, url_for, abort, redirect, render_template

from sts_inquiry import app, cache
from sts_inquiry.forms import create_search_form

METRIC_COL_LABELS = {
    "intra_handovers": "#C\U0001F517",
    "nghbr_handovers": "#N\U0001F517",
    "n_neighbors": "#N",
    "difficulty": "\u2300\U0001F92F",
    "entertainment": "\u2300\U0001F3A2",
    "difent": "\u2300\u2300\U0001F92F\U0001F3A2",
    "mode_playing_time": "\u2300\u23F3",
    "intra_occupied": "#C\U0001F464",
    "nghbr_occupied": "#N\U0001F464",
    "region_occupied": "#R\U0001F464"
}

MAX_OUTPUT_ROWS = 50

DFS_LOCK = Lock()


@app.route("/")
def index():
    if not cache.ready:
        abort(503)

    form = create_search_form(request.args,
                              max_cluster_size=len(cache.dfs), regions=cache.world.regions,
                              sortable_cols=list(METRIC_COL_LABELS.items()))

    # Add used=True or used=False to each field depending on whether it contains a value that is not the default.
    form.mark_used_fields()

    # If the URL query string contains values for any non-used fields, remove those by redirecting.
    # This leads to nice an concise URLs that only contain relevant information.
    for field in form:
        if field.name in request.args and not field.used:
            clean_query = urlencode([(field.name, value)
                                     for field in form if field.used
                                     for value in request.args.getlist(field.name)])
            return redirect(url_for("index") + "?" + clean_query, 302)

    # Because we cannot assume that operations on Pandas objects are thread-safe, we better make sure that
    # only one user request at the time can do stuff with the dfs.
    DFS_LOCK.acquire()

    # Get the appropriate df for the selected cluster size.
    cluster_size = form.clustersize.data
    df = cache.dfs[cluster_size - 1]

    # Filter and sort the df according to the user inputs.
    df = _filter(df,
                 form.name.data if form.name.used else None,
                 form.regions.data if form.regions.used else None,
                 form.free.data if form.free.used else None)
    df = _sort(df, [form.sortby1.data if form.sortby1.used else None,
                    form.sortby2.data if form.sortby2.used else None,
                    form.sortby3.data if form.sortby3.used else None])

    # Limit the amount of results.
    n_total_rows = df.shape[0]
    df = df.head(MAX_OUTPUT_ROWS)

    # Get the result away from Pandas so that we can release the lock.
    rows = list(df.itertuples())

    DFS_LOCK.release()

    if cluster_size in _HARDCODED_STW_COORDS:
        stw_coords = _HARDCODED_STW_COORDS[cluster_size]
    else:
        stw_coords = [(_coordfun(v + 0.5), _coordfun(v + 0.25))
                      for v in np.linspace(0, 1, cluster_size, endpoint=False)]

    return render_template("index.html", form=form, metric_col_labels=METRIC_COL_LABELS, stw_coords=stw_coords,
                           cluster_size=cluster_size, rows=rows, n_total_rows=n_total_rows)


def _filter(df, name_filter: Optional[str], region_filter: Optional[List[int]], free_filter: Optional[bool]):
    if free_filter:
        df = df[df["intra_occupied"] == 0]

    if region_filter:
        region_filter = set(region_filter)  # hopefully, computing this first is better for performance.
        df = df[[len({reg.rid for reg in regions}.intersection(region_filter)) > 0
                 for regions in df["regions"]]]

    if name_filter:
        df = df[df["concat_names"].str.contains(name_filter, case=False, regex=False)]

    return df


def _sort(df, sort_bys: Optional[List[str]]):
    sort_cols, sort_orders = [], []
    for sort_by in sort_bys:
        if sort_by:
            sort_col, sort_order = sort_by.split("-")
            if sort_col == "mode_playing_time":
                sort_col = "mode_playing_time_ordinal"
            sort_cols.append(sort_col)
            sort_orders.append(sort_order == "asc")

    if sort_cols:
        df = df.sort_values(sort_cols, ascending=sort_orders)
    return df


_HARDCODED_STW_COORDS = {
    2: [(0, 0), (100, 100)],
    3: [(0, 0), (100, 0), (50, 100)],
    4: [(0, 0), (100, 0), (100, 100), (0, 100)],
    5: [(30, 0), (90, 30), (90, 70), (30, 100), (0, 50)]
}


def _coordfun(v: float) -> int:
    return int(np.clip(abs((v % 1) * 4 - 1.5) - 0.5, 0, 1) * 100)
