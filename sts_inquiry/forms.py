from dataclasses import dataclass, field as dfield
from typing import List

from flask_wtf import FlaskForm
from wtforms import Field, BooleanField, StringField, SelectField, SubmitField
from wtforms.widgets import HTMLString, html_params

from sts_inquiry.consts import INSTANCES
from sts_inquiry.structs import SuperRegion

_SORT_ORDERS = [("asc", "\u2B08 aufsteigend"), ("desc", "\u2B0A absteigend")]


class RegionField(Field):
    @dataclass
    class Data:
        all: bool = dfield(default=True)
        urids: List[int] = dfield(default_factory=list)
        rids: List[int] = dfield(default_factory=list)

    @staticmethod
    def widget(field, **kwargs):
        def checkbox(value, label, checked):
            id_ = f"{field.id}-{value}"
            return f"<input {html_params(type='checkbox', id=id_, name=field.name, value=value, checked=checked)}>" \
                   f"<label {html_params(for_=id_)}>{label}</label>"

        kwargs.setdefault("id", field.id)
        html = []
        html.append(f"<ul {html_params(**kwargs)}><li>")
        html.append(checkbox("all", "Alle", field.data.all))
        html.append("<ul>")
        for superregion in sorted(field.superregions, key=lambda s: s.name.lower()):
            html.append("<li>")
            html.append(checkbox(f"s{superregion.urid}", superregion.name, superregion.urid in field.data.urids))
            html.append("<ul>")
            for region in sorted(superregion.regions, key=lambda r: r.name.lower()):
                html.append("<li>")
                html.append(checkbox(f"r{region.rid}", region.name, region.rid in field.data.rids))
                html.append("</li>")
            html.append("</ul></li>")
        html.append("</ul></li></ul>")
        return HTMLString("".join(html))

    superregions: List[SuperRegion]
    data: Data

    def process_formdata(self, valuelist):
        if len(valuelist) == 0:
            self.data = self.Data()
            return

        if len(valuelist) == 1:
            valuelist = valuelist[0].split("-")

        try:
            self.data = self.Data(all=False)
            for value in valuelist:
                if value == "all":
                    self.data.all = True
                elif value.startswith("s"):
                    self.data.urids.append(int(value[1:]))
                elif value.startswith("r"):
                    self.data.rids.append(int(value[1:]))
                else:
                    # For legacy URLs
                    self.data.rids.append(int(value))
        except ValueError:
            # In case of invalid user input, just use default data.
            self.data = self.Data()
            return


class SearchForm(FlaskForm):
    clustersize = SelectField("Clustergröße", coerce=int, default=1)

    name = StringField("Stellwerkname")
    regions = RegionField("Regionen")
    instance = SelectField("Instanz", coerce=int, default=-1,
                           choices=[(-1, "-- Alle -- ")] + [(inst, str(inst)) for inst in INSTANCES])
    free = BooleanField("Stellwerke unbesetzt")

    sortby1 = SelectField("1. Stufe")
    sortby2 = SelectField("2. Stufe")
    sortby3 = SelectField("3. Stufe")

    submit = SubmitField("\U0001F50D\u00A0\u00A0Suchen")

    def mark_used_fields(self):
        self.clustersize.used = self.clustersize.validate(self) and self.clustersize.data != 1
        self.instance.used = self.instance.validate(self) and self.instance.data != -1
        self.name.used = self.name.validate(self) and self.name.data.strip() != ""
        self.regions.used = self.regions.validate(self) and (self.regions.data.urids or self.regions.data.rids)
        self.free.used = self.free.validate(self) and self.free.data
        self.sortby1.used = self.sortby1.validate(self) and self.sortby1.data and self.sortby1.data != "none"
        self.sortby2.used = self.sortby2.validate(self) and self.sortby2.data and self.sortby2.data != "none"
        self.sortby3.used = self.sortby3.validate(self) and self.sortby3.data and self.sortby3.data != "none"
        self.submit.used = False


def create_search_form(args,
                       max_cluster_size: int, superregions: List[SuperRegion],
                       sortable_cols: List[str]) -> SearchForm:
    form = SearchForm(args)

    cluster_sizes = range(1, max_cluster_size + 1)
    form.clustersize.choices = [(sz, str(sz)) for sz in cluster_sizes]

    form.regions.superregions = superregions

    sort_choices = [("none", "-- Keine --")] + \
                   [(f"{col_id}-{ord_id}", f"{col_lbl} ({ord_lbl})")
                    for col_id, col_lbl in sortable_cols for ord_id, ord_lbl in _SORT_ORDERS]
    form.sortby1.choices = sort_choices
    form.sortby2.choices = sort_choices
    form.sortby3.choices = sort_choices

    return form
