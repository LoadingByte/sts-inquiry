import math
from urllib.parse import urlencode

import numpy as np
from flask import request, url_for, abort, redirect, render_template

from sts_inquiry import app, cache
from sts_inquiry.forms import create_search_form
from sts_inquiry.search import search

METRIC_COL_LABELS = {
    "intra_handovers": "#C\U0001F517",
    "nghbr_handovers": "#N\U0001F517",
    "n_neighbors": "#N",
    "mean_difficulty": "\u2300\U0001F92F",
    "mean_entertainment": "\u2300\U0001F3A2",
    "mean_difent": "\u2300\u2300\U0001F92F\U0001F3A2",
    "min_difficulty": "\u25BD\U0001F92F",
    "min_entertainment": "\u25BD\U0001F3A2",
    "min_difent": "\u25BD\u2300\U0001F92F\U0001F3A2",
    "nghbr_occupants": "#N\U0001F464",
    "region_occupants": "#R\U0001F464"
}

_ROWS_PER_PAGE = app.config["ROWS_PER_PAGE"]

_LEGACY_PARAM_KEYS = {
    "name": "nameincl"
}

_HARDCODED_STW_COORDS = {
    2: [(0, 50), (100, 50)],
    3: [(0, 0), (100, 0), (50, 100)],
    4: [(0, 0), (100, 0), (100, 100), (0, 100)],
    5: [(0, 20), (70, 0), (100, 50), (70, 100), (0, 80)],
    6: [(25, 0), (75, 0), (100, 50), (75, 100), (25, 100), (0, 50)]
}


@app.errorhandler(503)
def error(_):
    return render_template("503.html"), 503


@app.route("/")
def index():
    if not cache.ready:
        abort(503)

    form = create_search_form(request.args,
                              max_cluster_size=len(cache.dfs), superregions=cache.world.superregions,
                              sortable_cols=list(METRIC_COL_LABELS.items()))

    # Add used=True or used=False to each field depending on whether it contains a value that is not the default.
    form.mark_used_fields()

    # If the URL query string contains values for any non-used fields, page = 1,
    # or both a page and a highlight cluster, remove redundant values by redirecting.
    # Also, if the regions field is split up into multiple params, join them.
    # This leads to nice an concise URLs that only contain relevant information.
    query_cleansing_necessary, search_params, other_params = _process_params(form)
    if query_cleansing_necessary:
        return redirect(url_for("index") + "?" + urlencode(search_params + other_params), 302)

    try:
        page = int(request.args["page"])
    except (KeyError, TypeError):
        page = 1

    try:
        highlight_cluster_aids = {int(aid) for aid in request.args["cluster"].split("-")}
    except (KeyError, TypeError):
        highlight_cluster_aids = None

    cluster_size, page, highlight_row_idx, n_total_rows, rows = search(form, page, highlight_cluster_aids)

    # Detect too high page numbers or highlight clusters that cannot be found; then, redirect.
    if (not rows and page != 1) or (highlight_cluster_aids and highlight_row_idx is None):
        return redirect(url_for("index") + "?" + urlencode(search_params), 302)

    prev_pages = list(range(1, page))
    next_pages = list(range(page + 1, math.ceil(n_total_rows / _ROWS_PER_PAGE) + 1))

    # Calculate the coordinates where the stws in each cluster should be placed.
    if cluster_size in _HARDCODED_STW_COORDS:
        stw_coords = _HARDCODED_STW_COORDS[cluster_size]
    else:
        stw_coords = [(_coordfun(v + 0.5), _coordfun(v + 0.25))
                      for v in np.linspace(0, 1, cluster_size, endpoint=False)]

    return render_template("index.html",
                           form=form,
                           metric_col_labels=METRIC_COL_LABELS, cluster_size=cluster_size, stw_coords=stw_coords,
                           instance=form.instance.data if form.instance.used else None,
                           rows=rows, n_total_rows=n_total_rows,
                           highlight_row_idx=highlight_row_idx,
                           search_params=search_params, cur_page=page, prev_pages=prev_pages, next_pages=next_pages)


def _process_params(form):
    search_params = []
    region_values = []

    nav_params = {}
    legacy_params = []
    query_cleansing_necessary = False

    # Read all params sequentially.
    field_names = {field.name for field in form}
    for key, value in request.args.items(multi=True):
        if key == "regions" and form.regions.used:
            region_values.append(value)
        elif key in field_names and getattr(form, key).used:
            search_params.append((key, value))
        elif key == "page" and value != "1":
            nav_params["page"] = value
        elif key == "cluster":
            nav_params["cluster"] = value
        else:
            query_cleansing_necessary = True
            if key in _LEGACY_PARAM_KEYS:
                legacy_params.append((_LEGACY_PARAM_KEYS[key], value))

    if len(region_values) >= 2:
        query_cleansing_necessary = True
        search_params += [("regions", "-".join(region_values))]
    elif len(region_values) == 1:
        search_params += [("regions", region_values[0])]

    if "page" in nav_params and "cluster" in nav_params:
        del nav_params["page"]
        query_cleansing_necessary = True

    other_params = list(nav_params.items()) + legacy_params

    return query_cleansing_necessary, search_params, other_params


def _coordfun(v: float) -> int:
    return int(np.clip(abs((v % 1) * 4 - 1.5) - 0.5, 0, 1) * 100)
