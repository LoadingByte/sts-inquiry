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
    "difficulty": "\u2300\U0001F92F",
    "entertainment": "\u2300\U0001F3A2",
    "difent": "\u2300\u2300\U0001F92F\U0001F3A2",
    "mode_playing_time": "\u2300\u23F3",
    "nghbr_occupants": "#N\U0001F464",
    "region_occupants": "#R\U0001F464"
}

_ROWS_PER_PAGE = app.config["ROWS_PER_PAGE"]


@app.errorhandler(503)
def error(_):
    return render_template("503.html"), 503


@app.route("/")
def index():
    if not cache.ready:
        abort(503)

    form = create_search_form(request.args,
                              max_cluster_size=len(cache.dfs), regions=cache.world.regions,
                              sortable_cols=list(METRIC_COL_LABELS.items()))

    # Add used=True or used=False to each field depending on whether it contains a value that is not the default.
    form.mark_used_fields()

    # If the URL query string contains values for any non-used fields or page=1, remove those by redirecting.
    # This leads to nice an concise URLs that only contain relevant information.
    form_fields = {field.name: field for field in form}
    search_params = []
    page_param = []
    query_cleansing_necessary = False
    for key, value in request.args.items(multi=True):
        if key in form_fields and form_fields[key].used:
            search_params.append((key, value))
        elif key == "page" and value != "1":
            page_param = [("page", value)]
        else:
            query_cleansing_necessary = True
    if query_cleansing_necessary:
        return redirect(url_for("index") + "?" + urlencode(search_params + page_param), 302)

    try:
        page = int(request.args["page"])
    except (KeyError, TypeError):
        page = 1

    cluster_size, n_total_rows, rows = search(form, page)

    # Catch too high page numbers.
    if not rows and page != 1:
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
                           search_params=search_params, cur_page=page, prev_pages=prev_pages, next_pages=next_pages)


_HARDCODED_STW_COORDS = {
    2: [(0, 0), (100, 100)],
    3: [(0, 0), (100, 0), (50, 100)],
    4: [(0, 0), (100, 0), (100, 100), (0, 100)],
    5: [(30, 0), (90, 30), (90, 70), (30, 100), (0, 50)]
}


def _coordfun(v: float) -> int:
    return int(np.clip(abs((v % 1) * 4 - 1.5) - 0.5, 0, 1) * 100)
