import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Bool, Dict, Int, List

import component.parameter as param
from component.message import cm
from component.tile.aoi_view import AoiView
from component.widget.legend_control import LegendControl

__all__ = ["AoiTile"]


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

        self.v_model.pop(id_, None)

        self.counter -= 1

    def add_element(self, *args):
        """Creates a new element and append to the current list"""

        if self.counter <= self.max_:
            self.counter += 1
            self.children = self.children + self.get_element()

    def update_model(self, *args, id_, pos):
        """update v_model content based on select changes"""

        if not id_ in self.v_model:
            self.v_model[id_] = {}

        self.v_model[id_][pos] = args[-1]

    def get_element(self, single=False):

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

        w_basep = v.Select(label=cm.calculation.y_base, items=list(range(10)))
        w_reportp = v.Select(label=cm.calculation.y_report, items=list(range(10)))

        w_basep.on_event(
            "change", lambda *args: self.update_model(*args, id_=id_, pos="base")
        )
        w_reportp.on_event(
            "change", lambda *args: self.update_model(*args, id_=id_, pos="report")
        )

        item = [
            v.ListItem(
                attributes={"id": id_},
                class_="ma-0 pa-0",
                children=[
                    v.ListItemContent(children=[w_basep, w_reportp]),
                ]
                + actions,
            ),
            v.Divider(
                attributes={"id": id_},
            ),
        ]

        return item


class EditionDialog(sw.Dialog):
    def __init__(self, content, indicator):

        self.v_model = False
        self.scrollable = True
        self.max_width = 650
        self.style_ = "overflow-x: hidden;"

        super().__init__()

        self.attributes = {"id": f"dialg_{indicator}"}

        close_btn = sw.Btn("OK", small=True)

        self.children = [
            sw.Card(
                max_width=650,
                min_height=420,
                class_="pa-4",
                children=[
                    v.CardTitle(children=[cm.calculation[indicator], v.Spacer()]),
                    content,
                    v.CardActions(children=[v.Spacer(), close_btn]),
                ],
            ),
        ]

        close_btn.on_event("click", lambda *args: setattr(self, "v_model", False))


class Calculation(sw.List):
    """Card to display and/or edit the bands(years) that will be used to calculate the
    statistics for each indicator. It is composed of two cards for subA y subB each
    with an editing icon that will display the corresponding editing dialogs"""

    indicators = ["sub_a", "sub_b"]

    def __init__(self):

        super().__init__()

        self.w_content_a = v.Select()
        self.w_content_b = CustomList()

        self.dialog_a = EditionDialog(self.w_content_a, "sub_a")
        self.dialog_b = EditionDialog(self.w_content_b, "sub_b")

        self.children = [self.get_item(indicator) for indicator in self.indicators] + [
            self.dialog_a,
            self.dialog_b,
        ]

    def get_item(self, indicator):
        """returns the specific structure required to display the bands(years) that will
        be used to calculate each of the specific subindicator"""

        switch = sw.Switch(attributes={"id": f"swit_{indicator}"}, v_model=True)
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
                                        cm.calculation[indicator],
                                        v.Spacer(),
                                        switch,
                                    ]
                                ),
                                v.CardText(
                                    children=[
                                        "You are about to calculate the MGCI witht the layer",
                                        v.Spacer(),
                                        self.get_chips(indicator),
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

    def get_chips(self, indicator):
        """get chips that will be inserted in the list elements and corresponds
        to the bands(years) selected for each of subindicator"""

        # If subindicator A : return simple chips
        # else: return pair-wise chips
        return ""
