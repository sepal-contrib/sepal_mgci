import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Dict, Int, List

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


class SubA(sw.Card):

    active = Bool(True).tag(sync=True)

    def __init__(self):

        super().__init__()

        self.class_ = "px-4 mr-2"
        w_active = v.Switch(v_model=True)
        title = v.CardTitle(children=[cm.calculation.sub_a, v.Spacer(), w_active])

        self.children = [
            title,
            sw.Card(
                class_="ma-0 pa-0",
                flat=True,
                children=[v.Select(label=cm.calculation.y_report)],
            ),
        ]

        w_active.observe(self.toggle, "v_model")

    def toggle(self, change):
        """toggle card disabled status"""

        self.active = not change["new"]
        self.children[-1].disabled = not change["new"]


class SubB(sw.Card):

    active = Bool(True).tag(sync=True)

    def __init__(self):

        self.class_ = "px-4"
        self.tile = True

        super().__init__()

        w_active = v.Switch(v_model=True)
        title = v.CardTitle(children=[cm.calculation.sub_b, v.Spacer(), w_active])

        self.custom_list = CustomList()

        self.children = [
            title,
            sw.Card(class_="ma-0 pa-0", flat=True, children=[self.custom_list]),
        ]

        w_active.observe(self.toggle, "v_model")

    def toggle(self, change):
        """toggle card disabled status"""

        self.active = not change["new"]
        self.children[-1].disabled = not change["new"]


class Calculation(sw.Layout):
    def __init__(self):

        super().__init__()

        w_sub_a = SubA()
        w_sub_b = SubB()

        self.children = [
            v.Flex(xs12=True, sm6=True, children=[w_sub_a]),
            v.Flex(xs12=True, sm6=True, children=[w_sub_b]),
        ]
