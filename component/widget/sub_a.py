import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Dict, Int

import component.parameter as param
from component.tile.aoi_view import AoiView
from component.widget.legend_control import LegendControl

__all__ = ["AoiTile"]


class CustomList(sw.List):

    counter = Int(1).tag(syc=True)
    max_ = Int(4 - 1).tag(syc=True)
    v_model = Dict({}).tag(syc=True)

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

        w_basep = v.Select(label="Baseline period year", items=list(range(10)))
        w_reportp = v.Select(label="Reporting period", items=list(range(10)))

        w_basep.on_event(
            "change", lambda *args: self.update_model(*args, id_=id_, pos="base")
        )
        w_reportp.on_event(
            "change", lambda *args: self.update_model(*args, id_=id_, pos="report")
        )

        item = [
            v.ListItem(
                attributes={"id": id_},
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


class SubB(sw.Card):
    def __init__(self):

        super().__init__()

        title = v.CardTitle(children=["Sub indicator B"])
        self.custom_list = CustomList()

        self.children = [title, self.custom_list]


class SubA(sw.Card):
    def __init__(self):

        super().__init__()

        title = v.CardTitle(children=["Sub indicator A"])

        self.children = [title, v.Select()]


class Calculation(sw.Layout):
    def __init__(self):

        super().__init__()

        w_sub_a = SubA()
        w_sub_b = SubB()

        self.children = [
            v.Flex(xs6=True, children=[w_sub_a]),
            v.Flex(xs6=True, children=[w_sub_b]),
        ]
