from copy import deepcopy

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Bool, Dict, Int, List

import component.parameter as param
from component.message import cm
from component.tile.aoi_view import AoiView
from component.widget.legend_control import LegendControl


class CustomList(sw.List):

    counter = Int(1).tag(syc=True)
    max_ = Int(4 - 1).tag(syc=True)
    v_model = Dict({}).tag(syc=True)
    items = List([]).tag(sync=True)

    def __init__(self):

        super().__init__()

        self.add_btn = v.Icon(children=["mdi-plus"])
        self.children = self.get_element(single=True)
        self.add_btn.on_event("click", self.add_element)

    def remove_element(self, *args, id_):
        """Removes element from the current list"""

        self.children = [
            chld for chld in self.children if chld not in self.get_children(id_)
        ]

        tmp_vmodel = deepcopy(self.v_model)

        tmp_vmodel.pop(id_, None)

        self.v_model = tmp_vmodel

        self.counter -= 1

    def add_element(self, *args):
        """Creates a new element and append to the current list"""

        if self.counter <= self.max_:
            self.counter += 1
            self.children = self.children + self.get_element()

    def update_model(self, data, id_, pos):
        """update v_model content based on select changes"""

        tmp_vmodel = deepcopy(self.v_model)

        if not id_ in tmp_vmodel:
            tmp_vmodel[id_] = {}
        tmp_vmodel[id_][pos] = data["new"]

        self.v_model = tmp_vmodel

    def get_element(self, single=False):
        """creates a double select widget with add and remove buttons. To allow user
        calculate subindicator B and also perform multiple calculations at once"""

        id_ = self.counter

        sub_btn = v.Icon(children=["mdi-minus"])
        sub_btn.on_event("click", lambda *args: self.remove_element(*args, id_=id_))

        actions = (
            [v.ListItemAction(children=[self.add_btn])]
            if single
            else [
                v.ListItemAction(
                    children=[self.add_btn],
                ),
                v.ListItemAction(
                    children=[sub_btn],
                ),
            ]
        )

        w_basep = v.Select(
            v_model=False,
            attributes={"id": f"base_{id_}"},
            label=cm.calculation.y_base,
            items=self.items,
        )
        w_reportp = v.Select(
            v_model=False,
            attributes={"id": f"report_{id_}"},
            label=cm.calculation.y_report,
            items=self.items,
        )

        w_basep.observe(
            lambda chg: self.update_model(chg, id_=id_, pos="base"), "v_model"
        )
        w_reportp.observe(
            lambda chg: self.update_model(chg, id_=id_, pos="report"), "v_model"
        )

        item = [
            v.ListItem(
                attributes={"id": id_},
                class_="ma-0 pa-0",
                children=[
                    v.ListItemContent(
                        attributes={"id": "selects"}, children=[w_basep, w_reportp]
                    ),
                ]
                + actions,
            ),
            v.Divider(
                attributes={"id": id_},
            ),
        ]

        return item

    def get_select_elements(self):
        """receive v.select items, save in object (to be reused by new elements) and
        fill the current one ones in the view"""

        item_content_chlds = self.get_children("selects")

        # Manage the special case when there is only one item.
        if not isinstance(item_content_chlds, list):
            item_content_chlds = [item_content_chlds]
        return [select for item in item_content_chlds for select in item.children]

    def populate(self, items):
        """receive v.select items, save in object (to be reused by new elements) and
        fill the current one ones in the view"""

        self.items = items

        select_wgts = self.get_select_elements()

        [setattr(select, "items", items) for select in select_wgts]

    def reset(self):
        """remove all selected values form selection widgets"""

        select_wgts = self.get_select_elements()

        [setattr(select, "v_model", False) for select in select_wgts]


class EditionDialog(sw.Dialog):
    def __init__(self, content, indicator):

        self.v_model = False
        self.scrollable = True
        self.max_width = 650
        self.style_ = "overflow-x: hidden;"

        super().__init__()

        self.attributes = {"id": f"dialg_{indicator}"}
        self.content = content

        close_btn = sw.Btn("OK", small=True)
        clean_btn = v.Icon(children=["mdi-broom"])

        self.children = [
            sw.Card(
                max_width=650,
                min_height=420,
                class_="pa-4",
                children=[
                    v.CardTitle(
                        children=[
                            cm.calculation[indicator].title,
                            v.Spacer(),
                            clean_btn,
                        ]
                    ),
                    self.content,
                    v.CardActions(children=[v.Spacer(), close_btn]),
                ],
            ),
        ]

        close_btn.on_event("click", lambda *args: setattr(self, "v_model", False))
        clean_btn.on_event("click", self.reset_event)

    def reset_event(self, *args):
        """search within the content and trigger reset method"""

        if self.attributes["id"] == "dialg_sub_a":
            self.content.v_model = []
        else:
            self.content.reset()


class Calculation(sw.List):
    """Card to display and/or edit the bands(years) that will be used to calculate the
    statistics for each indicator. It is composed of two cards for subA y subB each
    with an editing icon that will display the corresponding editing dialogs"""

    indicators = ["sub_a", "sub_b"]

    def __init__(self, model):

        super().__init__()

        self.model = model

        self.w_content_a = v.Select(
            label=cm.calculation.y_report, v_model=[], multiple=True
        )
        self.w_content_b = CustomList()

        self.dialog_a = EditionDialog(self.w_content_a, "sub_a")
        self.dialog_b = EditionDialog(self.w_content_b, "sub_b")

        self.children = [self.get_item(indicator) for indicator in self.indicators] + [
            self.dialog_a,
            self.dialog_b,
        ]

        self.model.observe(self.populate_years, "ic_items")
        self.w_content_a.observe(
            lambda change: self.get_chips(change, "sub_a"), "v_model"
        )
        self.w_content_b.observe(
            lambda change: self.get_chips(change, "sub_b"), "v_model"
        )

    def reset_event(self, data, indicator):
        """search within the content and trigger reset method"""

        if indicator in f"dialg_sub_a":
            self.w_content_a.v_model = []
        else:
            self.w_content_b.reset()

        self.get_children(f"desc_{indicator}").children = (
            [cm.calculation[indicator].desc_disabled]
            if not data
            else [cm.calculation[indicator].desc_active]
        )

        self.get_children(f"pen_{indicator}").disabled = not data

    def populate_years(self, change):
        """function to trigger and send population methods from a and b content based
        on model ic_items change"""

        if change["new"]:

            items = [
                {"value": item.split("/")[-1], "text": item} for item in change["new"]
            ]

            self.w_content_a.items = items
            self.w_content_b.populate(items)

    def get_item(self, indicator):
        """returns the specific structure required to display the bands(years) that will
        be used to calculate each of the specific subindicator"""

        switch = sw.Switch(attributes={"id": f"swit_{indicator}"}, v_model=True)
        switch.observe(
            lambda chg: self.reset_event(chg["new"], indicator=indicator), "v_model"
        )

        pencil = sw.Icon(children=["mdi-pencil"], attributes={"id": f"pen_{indicator}"})
        pencil.on_event(
            "click", lambda *args: self.open_dialog(indicator=f"{indicator}")
        )

        return v.ListItem(
            children=[
                v.ListItemContent(
                    children=[
                        v.Card(
                            children=[
                                v.CardTitle(
                                    children=[
                                        cm.calculation[indicator].title,
                                        v.Spacer(),
                                        switch,
                                    ]
                                ),
                                sw.CardText(
                                    children=[
                                        v.Html(
                                            tag="span",
                                            attributes={"id": f"desc_{indicator}"},
                                            children=[
                                                cm.calculation[indicator].desc_active
                                            ],
                                        ),
                                        v.Spacer(),
                                        v.Html(
                                            tag="span",
                                            attributes={"id": f"span_{indicator}"},
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ]
                ),
                v.ListItemAction(children=[pencil]),
            ]
        )

    def deactivate_indicator(self, change, indicator):
        """toggle indicator item disabled status"""

        self.active = not change["new"]
        self.children[-1].disabled = not change["new"]

    def open_dialog(self, *args, indicator):
        """Change the v_model value of subindicators edition dialogs to display them"""

        dialog = self.get_children(f"dialg_{indicator}")
        dialog.v_model = True

    def get_chips(self, change, indicator):
        """get chips that will be inserted in the list elements and corresponds
        to the bands(years) selected for each of subindicator"""

        span = self.get_children(f"span_{indicator}")

        if not change.get("new", None):
            span.children = [""]
            return

        data = change["new"]

        if indicator == "sub_a":
            multichips = [[v.Chip(small=True, children=[year]), ", "] for year in data]

        else:

            multichips = []
            for period, val in data.items():

                base_y = val.get("base", "...") or "..."
                report_y = val.get("report", "...") or "..."

                if not all([base_y != "...", base_y != "..."]):
                    continue

                multichips.append(
                    [
                        v.Chip(
                            small=True,
                            draggable=True,
                            children=[
                                base_y + " AND " + report_y,
                            ],
                        ),
                        ", ",
                    ]
                )

            if not multichips:
                span.children = [""]
                return

        # Flat list and always remove the last element (the comma)
        chips = [val for period in multichips for val in period][:-1]

        span.children = chips
