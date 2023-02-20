from copy import deepcopy

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Bool, Dict, Int, List, directional_link

import component.parameter.module_parameter as param
from component.message import cm


class Calculation(sw.List):
    """Card to display and/or edit the bands(years) that will be used to calculate thes statistics for each indicator. It is composed of two cards for subA y subB each
    with an editing icon that will display the corresponding editing dialogs"""

    indicators = ["sub_a", "sub_b"]
    ready = Bool(False).tag(sync=True)
    "bool: traitlet to alert model that this element has loaded."

    def __init__(self, model):
        super().__init__()

        self.model = model

        self.w_content_a = CustomList(
            label=cm.calculation.y_report, unique=True, items=self.model.ic_items
        )

        self.w_content_b = CustomList(items=self.model.ic_items)

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

        directional_link((self, "ready"), (self.model, "dash_ready"))
        directional_link((self.w_content_a, "v_model"), (self.model, "start_year"))
        directional_link((self.w_content_b, "v_model"), (self.model, "end_year"))

        # Link switches to the model
        directional_link(
            (self.get_children("switch_sub_a"), "v_model"),
            (self.model, "calc_a"),
        )

        directional_link(
            (self.get_children("switch_sub_b"), "v_model"),
            (self.model, "calc_b"),
        )

        self.ready = True

    def reset_event(self, data, indicator):
        """search within the content and trigger reset method"""

        if indicator in "dialg_sub_a":
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
            self.dialog_a.reset_event()
            self.dialog_b.reset_event()

            # Create a dictionary to store items with name as key and id as value
            self.model.ic_items_label = {
                item.split("/")[-1]: item for item in self.model.ic_items
            }

            items = [
                {"value": item.split("/")[-1], "text": item} for item in change["new"]
            ]

            self.w_content_a.populate(items)
            self.w_content_b.populate(items)

    def get_item(self, indicator):
        """returns the specific structure required to display the bands(years) that will
        be used to calculate each of the specific subindicator"""

        switch = sw.Switch(attributes={"id": f"switch_{indicator}"}, v_model=True)
        switch.observe(
            lambda chg: self.reset_event(chg["new"], indicator=indicator), "v_model"
        )

        pencil = v.Btn(
            children=[sw.Icon(children=["mdi-pencil"])],
            icon=True,
            attributes={"id": f"pen_{indicator}"},
        )

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

        # Get the space where the elements will be inserted
        span = self.get_children(f"span_{indicator}")

        if not change.get("new", None):
            span.children = [""]
            return

        data = change["new"]

        base_years = [val["base"].get("year", "...") for val in data.values()]

        if indicator == "sub_a":
            multichips = [
                # Set chip red color if the year is empty
                [
                    v.Chip(
                        color="secondary" if year != "..." else "error",
                        small=True,
                        children=[year],
                    ),
                    ", ",
                ]
                for year in base_years
            ]

        else:
            multichips = []
            for val in data.values():
                base_y = val.get("base", {}).get("year", "...") or "..."
                report_y = val.get("report", {}).get("year", "...") or "..."

                if not all([base_y != "...", base_y != "..."]):
                    continue

                multichips.append(
                    [
                        v.Chip(
                            color="error"
                            if any([base_y == "...", report_y == "..."])
                            else "secondary",
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


class CustomList(sw.List):
    counter = Int(1).tag(syc=True)
    "int: control number to check how many subb pairs are loaded"
    max_ = Int(4 - 1).tag(syc=True)
    "int: maximun number of sub indicator pairs to be displayed in UI"
    v_model = Dict({}).tag(syc=True)
    "dict: where key is the consecutive number of pairs, and values are the baseline and reporting period"
    items = List([]).tag(sync=True)
    "list: image collection items to be loaded in each select pair"
    unique = False
    "bool: if true, only the base period will be added to the list"

    def __init__(self, items=[], unique=False, label=""):
        self.label = label
        self.items = items
        self.unique = unique

        super().__init__()

        self.add_btn = v.Btn(children=[v.Icon(children=["mdi-plus"])], icon=True)
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

    def update_model(self, data, id_, pos, target):
        """update v_model content based on select changes"""

        tmp_vmodel = deepcopy(self.v_model)

        # set a default value for the key if it doesn't exist
        # do this for each level of the dict
        # so we can set the value for the target key
        tmp_vmodel.setdefault(id_, {}).setdefault(pos, {})[target] = str(data["new"])

        # if not id_ in tmp_vmodel:
        #     tmp_vmodel[id_] = {}

        # if not pos in tmp_vmodel[id_]:
        #     tmp_vmodel[id_][pos] = {}

        # tmp_vmodel[id_][pos][target] = data["new"]

        self.v_model = tmp_vmodel

    def get_element(self, single=False):
        """creates a double select widget with add and remove buttons. To allow user
        calculate subindicator B and also perform multiple calculations at once"""

        id_ = self.counter

        sub_btn = v.Btn(children=[v.Icon(children=["mdi-minus"])], icon=True)
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
            class_="mr-2",
            v_model=False,
            attributes={"id": "selects"},
            label=cm.calculation.y_base,
            items=self.items,
        )

        w_base_yref = SelectYear()
        w_basep_container = sw.Flex(
            class_="d-flex flex-row", children=[w_basep, w_base_yref]
        )

        w_basep.observe(
            lambda chg: self.update_model(chg, id_=id_, pos="base", target="asset"),
            "v_model",
        )
        w_base_yref.observe(
            lambda chg: self.update_model(chg, id_=id_, pos="base", target="year"),
            "v_model",
        )

        if not self.unique:
            # only display report widgets if unique is True
            w_reportp = v.Select(
                class_="mr-3",
                v_model=False,
                attributes={"id": "selects"},
                label=cm.calculation.y_report,
                items=self.items,
            )
            w_report_yref = SelectYear()

            w_reportp_container = sw.Flex(
                class_="d-flex flex-row", children=[w_reportp, w_report_yref]
            )

            w_reportp.observe(
                lambda chg: self.update_model(
                    chg, id_=id_, pos="report", target="asset"
                ),
                "v_model",
            )
            w_report_yref.observe(
                lambda chg: self.update_model(
                    chg, id_=id_, pos="report", target="year"
                ),
                "v_model",
            )

        item = [
            v.ListItem(
                attributes={"id": id_},
                class_="ma-0 pa-0",
                children=[
                    v.ListItemContent(children=[w_basep_container])
                    if self.unique
                    else v.ListItemContent(
                        children=[w_basep_container, w_reportp_container],
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
        """receive v.select items that are children of 'selects' id"""

        selects = self.get_children("selects")

        if not isinstance(selects, list):
            selects = [selects]

        return selects

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
    def __init__(self, custom_list, indicator):
        self.v_model = False
        self.scrollable = True
        self.max_width = 650
        self.style_ = "overflow-x: hidden;"

        super().__init__()

        self.attributes = {"id": f"dialg_{indicator}"}
        self.custom_list = custom_list

        close_btn = sw.Btn("OK", small=True)
        clean_btn = v.Btn(children=[v.Icon(children=["mdi-broom"])], icon=True)

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
                    self.custom_list,
                    v.CardActions(children=[v.Spacer(), close_btn]),
                ],
            ),
        ]

        close_btn.on_event("click", lambda *args: setattr(self, "v_model", False))
        clean_btn.on_event("click", self.reset_event)

    def reset_event(self, *args):
        """search within the content and trigger reset method"""

        self.custom_list.reset()


class SelectYear(v.Select):
    """Select widget to select a year, it will be always the same"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.v_model = False
        self.style_ = "min-width: 175px; max-width: 175px"
        self.label = cm.calculation.match_year
        self.items = param.YEARS
