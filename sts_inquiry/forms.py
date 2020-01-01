from typing import Iterable

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField, SelectMultipleField, SubmitField

from sts_inquiry.structs import Region

_SORT_ORDERS = [("asc", "\u2B08 aufsteigend"), ("desc", "\u2B0A absteigend")]


class SearchForm(FlaskForm):
    clustersize = SelectField("Clustergröße", coerce=int, default=1)

    name = StringField("Stellwerkname")
    regions = SelectMultipleField("Regionen", coerce=int)
    free = BooleanField("Stellwerke unbesetzt")

    sortby1 = SelectField("1. Stufe")
    sortby2 = SelectField("2. Stufe")
    sortby3 = SelectField("3. Stufe")

    submit = SubmitField("\U0001F50D\u00A0\u00A0Suchen")

    def mark_used_fields(self):
        self.clustersize.used = True
        self.name.used = self.name.validate(self) and self.name.data.strip() != ""
        self.regions.used = self.regions.validate(self) and -1 not in self.regions.data
        self.free.used = self.free.validate(self) and self.free.data
        self.sortby1.used = self.sortby1.validate(self) and self.sortby1.data and self.sortby1.data != "none"
        self.sortby2.used = self.sortby2.validate(self) and self.sortby2.data and self.sortby2.data != "none"
        self.sortby3.used = self.sortby3.validate(self) and self.sortby3.data and self.sortby3.data != "none"
        self.submit.used = False


def create_search_form(args,
                       max_cluster_size: int, regions: Iterable[Region], sortable_cols: Iterable[str]) -> SearchForm:
    form = SearchForm(args)

    cluster_sizes = range(1, max_cluster_size + 1)
    form.clustersize.choices = list(zip(cluster_sizes, cluster_sizes))

    form.regions.choices = [(-1, "-- Alle --")] + \
                           [(region.rid, region.name) for region in regions]
    # Hacky way to set the default region ("all"); necessary because wtforms does wtf and defaults don't work here.
    if not form.regions.data:
        form.regions.data = [-1]

    sort_choices = [("none", "-- Keine --")] + \
                   [(f"{col_id}-{ord_id}", f"{col_lbl} ({ord_lbl})")
                    for col_id, col_lbl in sortable_cols for ord_id, ord_lbl in _SORT_ORDERS]
    form.sortby1.choices = sort_choices
    form.sortby2.choices = sort_choices
    form.sortby3.choices = sort_choices

    return form
