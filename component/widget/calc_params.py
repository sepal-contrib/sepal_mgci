from copy import deepcopy
from typing import Literal

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Bool, Dict, Int, List, directional_link

import component.frontend
import component.parameter.module_parameter as param
import component.scripts.scripts as cs
from component.message import cm


class Calculation(sw.List):
    """Card to display and/or edit the bands(years) that will be used to calculate thes statistics for each indicator.
    It is composed of two cards for subA y subB each
    with an editing icon that will display the corresponding editing dialogs"""

    indicators = ["sub_a", "sub_b"]
    ready = Bool(False).tag(sync=True)
    "bool: traitlet to alert model that this element has loaded."

    def __init__(self, model):
        super().__init__()

        self.model = model
        self.ready = False

        self.w_content_a = CustomList(
            indicator="sub_a",
            label=cm.calculation.y_report,
            items=self.model.ic_items_sub_a,
        )

        self.w_content_b = CustomList(
            indicator="sub_b", items=self.model.ic_items_sub_b
        )

        self.dialog_a = EditionDialog(self.w_content_a, "sub_a")
        self.dialog_b = EditionDialog(self.w_content_b, "sub_b")

        self.children = (
            v.Flex(
                class_="d-flex",
                children=[self.get_item(indicator) for indicator in self.indicators],
            ),
            self.dialog_a,
            self.dialog_b,
        )

        self.model.observe(
            lambda chg: self.populate_years(chg, indicator="sub_a"),
            "ic_items_sub_a",
        )
        self.model.observe(
            lambda chg: self.populate_years(chg, indicator="sub_b"),
            "ic_items_sub_b",
        )

        self.w_content_a.observe(
            lambda change: self.get_chips(change, "sub_a"), "v_model"
        )
        self.w_content_b.observe(
            lambda change: self.get_chips(change, "sub_b"), "v_model"
        )

        directional_link((self, "ready"), (self.model, "dash_ready"))
        directional_link((self.w_content_a, "v_model"), (self.model, "sub_a_year"))
        directional_link((self.w_content_b, "v_model"), (self.model, "sub_b_year"))

        # Link switches to the model
        directional_link(
            (self.get_children(id_="switch_sub_a")[0], "v_model"),
            (self.model, "calc_a"),
        )

        directional_link(
            (self.get_children(id_="switch_sub_b")[0], "v_model"),
            (self.model, "calc_b"),
        )
        self.ready = True

    def reset_event(self, change, indicator):
        """search within the content and trigger reset method"""

        # get widget and reset it
        widget = self.get_children(id_=f"dialog_{indicator}")[0]
        widget.reset_event()

        self.get_children(id_=f"desc_{indicator}")[0].children = (
            [cm.calculation[indicator].desc_disabled]
            if not change["new"]
            else [cm.calculation[indicator].desc_active]
        )

        self.get_children(id_=f"pen_{indicator}")[0].disabled = not change["new"]

    def populate_years(self, change, indicator):
        """function to trigger and send population methods from a and b content based
        on model ic_items change"""

        if self.ready and change["new"]:

            dialog = self.get_children(id_=f"dialog_{indicator}")[0]
            w_content = self.get_children(id_=f"content_{indicator}")[0]
            dialog.reset_event()
            items = [{"value": item, "text": item} for item in change["new"]]

            w_content.populate(items)

    def get_item(self, indicator):
        """returns the specific structure required to display the bands(years) that will
        be used to calculate each of the specific subindicator"""

        alert = sw.Alert(attributes={"id": f"alert_{indicator}"}).hide()
        switch = sw.Switch(attributes={"id": f"switch_{indicator}"}, v_model=True)
        switch.observe(
            lambda change: self.reset_event(change, indicator=indicator), "v_model"
        )

        pencil = v.Btn(
            children=[sw.Icon(children=["mdi-layers-plus"])],
            icon=True,
            attributes={"id": f"pen_{indicator}"},
            class_="mr-2",
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
                                        pencil,
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
                                        v.Spacer(class_="my-2"),
                                        v.Html(
                                            class_="mt-2",
                                            tag="span",
                                            attributes={"id": f"span_{indicator}"},
                                        ),
                                        alert,
                                    ]
                                ),
                            ]
                        )
                    ]
                ),
                # v.ListItemAction(children=[pencil]),
            ]
        )

    def deactivate_indicator(self, change, indicator):
        """toggle indicator item disabled status"""

        self.active = not change["new"]
        self.children[-1].disabled = not change["new"]

    def open_dialog(self, *args, indicator):
        """Change the v_model value of subindicators edition dialogs to display them"""

        dialog = self.get_children(id_=f"dialog_{indicator}")[0]
        dialog.v_model = True

    def get_chips(self, change, indicator):
        """get chips that will be inserted in the list elements and corresponds
        to the bands(years) selected for each of subindicator"""

        if indicator == "sub_b":
            return

        # Get the space where the elements will be inserted
        span = self.get_children(id_=f"span_{indicator}")[0]
        alert = self.get_children(id_=f"alert_{indicator}")[0]

        if not change.get("new", None):
            alert.reset()
            span.children = [""]
            return

        data = change["new"]

        base_years = [str(val.get("year", "...")) for val in data.values()]

        reporting_years = cs.get_sub_a_break_points(data)

        if base_years and not reporting_years:
            str_base_y = ", ".join(base_years)
            alert.add_msg(
                (
                    f"With {str_base_y} you cannot report any year. Please provide"
                    " years that are at least 5 years apart."
                ),
                type_="warning",
            )
        else:
            alert.hide()

        multichips = []

        for reporting_y in reporting_years.keys():

            multichips.append(
                [
                    v.Chip(
                        color="success",
                        small=True,
                        draggable=True,
                        children=[
                            str(reporting_y),
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

        span.children = ["Reporting years: "] + chips

        # Send reporting years to the model so it can be listened by dashboard
        self.model.reporting_a_years = reporting_years.keys()


class CustomList(sw.List):

    counter = Int(1).tag(syc=True)
    "int: control number to check how many subb pairs are loaded"
    max_ = Int(10 - 1).tag(syc=True)
    "int: maximun number of sub indicator pairs to be displayed in UI"
    v_model = Dict({}, allow_none=True).tag(syc=True)
    "dict: where key is the consecutive number of pairs, and values are the baseline and reporting period"
    items = List([]).tag(sync=True)
    "list: image collection items to be loaded in each select pair"
    indicator = None
    "str: indicator name. sub_a or sub_b. The widget will render the corresponding subindicator"
    ids = List([]).tag(sync=True)
    "list: list of ids of the elements that are currently loaded in the list"

    def __init__(
        self, indicator: Literal["sub_a", "sub_b"], items: list = [], label: str = ""
    ) -> sw.List:

        self.label = label
        self.items = items
        self.indicator = indicator
        self.attributes = {"id": f"content_{indicator}"}

        super().__init__()

        self.add_btn = v.Btn(children=[v.Icon(children=["mdi-plus"])], icon=True)
        self.children = self.get_element(single=True)
        self.add_btn.on_event("click", self.add_element)

    def remove_element(self, *args, id_):
        """Removes element from the current list"""

        # remove id from self.ids
        self.ids = [val for val in self.ids if val != id_]

        self.children = [
            chld for chld in self.children if chld not in self.get_children(id_=id_)
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

    def update_model(self, data, id_, target, type_=None):
        """update v_model content based on select changes.

        Args:
            data (dict): data from the select change event (change)
            id_ (int): id of the element that triggered the change
            target (str): either asset or year.
            type_ (str, optional): baseline or reporting. Defaults to None.
        """

        if not data["new"]:
            return

        tmp_vmodel = deepcopy(self.v_model)
        value = str(data["new"]) if target == "asset" else int(data["new"])

        if self.indicator == "sub_a":
            # set a default value for the key if it doesn't exist
            # do this for each level of the dict
            # so we can set the value for the target key
            tmp_vmodel.setdefault(id_, {})[target] = value

        else:
            tmp_vmodel.setdefault(id_, {}).setdefault(type_, {})[target] = value

        self.v_model = tmp_vmodel

    def get_element(self, single=False):
        """creates a double select widget with add and remove buttons. To allow user
        calculate subindicator B and also perform multiple calculations at once"""

        id_ = self.counter

        self.ids.append(id_)

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
            class_="mr-2 max-width-200",
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
            lambda chg: self.update_model(chg, id_=id_, target="asset", type_="base"),
            "v_model",
        )
        w_base_yref.observe(
            lambda chg: self.update_model(chg, id_=id_, target="year", type_="base"),
            "v_model",
        )

        # I will skip double select for sub_b
        if self.indicator == "sub_b":
            # only display report widgets when using sub_b

            sub_b_content = CustomListB(w_basep_container, items=self.items)

            sub_b_content.w_reportp.observe(
                lambda chg: self.update_model(
                    chg, id_=id_, target="asset", type_="report"
                ),
                "v_model",
            )
            sub_b_content.w_report_yref.observe(
                lambda chg: self.update_model(
                    chg, id_=id_, target="year", type_="report"
                ),
                "v_model",
            )

        item = [
            v.ListItem(
                attributes={"id": id_},
                class_="ma-0 pa-0",
                children=[
                    sub_b_content
                    if self.indicator == "sub_b"
                    else v.ListItemContent(children=[w_basep_container]),
                ]
                + actions,
            ),
            v.Divider(
                attributes={"id": id_},
            ),
        ]

        return item

    def populate(self, items):
        """receive v.select items, save in object (to be reused by new elements) and
        fill the current one ones in the view"""

        self.items = items

        select_wgts = self.get_children(id_="selects")

        [setattr(select, "items", items) for select in select_wgts]

    def reset(self):
        """remove all selected values form selection widgets"""

        select_wgts = self.get_children(id_="selects")
        ref_wgts = self.get_children(id_="ref_select")

        [self.remove_element(id_=id) for id in self.ids if id != 1]

        [setattr(select, "v_model", None) for select in (select_wgts + ref_wgts)]

        # And also reset the v_model
        self.v_model = {}


class EditionDialog(sw.Dialog):
    def __init__(self, custom_list, indicator):
        self.v_model = False
        self.scrollable = True
        self.max_width = 650
        self.style_ = "overflow-x: hidden;"

        super().__init__()

        self.attributes = {"id": f"dialog_{indicator}"}
        self.custom_list = custom_list

        close_btn = sw.Btn("OK", small=True)
        clean_btn = sw.Btn(gliph="mdi-broom", icon=True).set_tooltip(
            "Reset all values", bottom=True
        )

        self.children = [
            sw.Card(
                max_width=650,
                min_height=420,
                style_="height: 100%;",
                class_="pa-4",
                children=[
                    v.CardTitle(
                        children=[
                            cm.calculation[indicator].title,
                            v.Spacer(),
                            clean_btn.with_tooltip,
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

    def __init__(self, label=cm.calculation.match_year, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.v_model = False
        self.style_ = "min-width: 125px; max-width: 125px"
        self.label = label
        self.items = param.YEARS
        self.attributes = {"id": "ref_select"}


class CustomListB(sw.ListItemContent):
    def __init__(self, w_basep_container, items, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.items = items

        self.w_basep_container = w_basep_container

        self.w_report_yr = sw.Select(
            label=cm.calculation.y_report,
            style_="min-width: 200px; max-width: 2005px",
            attributes={"id": "selects"},
            items=param.REPORT_INTERVALS[2:],
            v_model=False,
        )

        self.w_reportp = v.Select(
            class_="mr-3 ",
            v_model=False,
            attributes={"id": "selects"},
            label=cm.calculation.y_report,
            items=self.items,
        )

        self.w_report_yref = SelectYear()

        self.w_reportp_container = sw.Flex(
            class_="d-flex flex-row", children=[self.w_reportp, self.w_report_yref]
        )

        span_base = v.Html(
            tag="span", class_="mr-2", children=["...."], attributes={"id": "span_base"}
        )
        span_report = v.Html(
            tag="span",
            class_="mr-2",
            children=["...."],
            attributes={"id": "span_report"},
        )

        self.children = [
            sw.Card(
                children=[
                    sw.CardTitle(children=[sw.Spacer(), self.w_report_yr]),
                    sw.CardText(
                        children=[
                            sw.Flex(
                                class_="d-flex align-center",
                                children=[span_base, self.w_basep_container],
                            ),
                            sw.Flex(
                                class_="d-flex align-center",
                                children=[span_report, self.w_reportp_container],
                            ),
                        ]
                    ),
                ]
            )
        ]

        _ = [
            setattr(chld, "label", cm.calculation.y_actual)
            for chld in self.get_children(id_="ref_select")
        ]

        self.w_report_yr.observe(self.fill_span_values, "v_model")

    def fill_span_values(self, change):
        """set the values of the span elements.

        They will change according with the w_report_yr selected.

        """

        val = change["new"]

        if val:

            span_base = self.get_children(id_="span_base")[0]
            span_report = self.get_children(id_="span_report")[0]

            # from REPORT_INTERVALS, get the index of the selected value and
            # substract 1 to get the previous value

            current = param.REPORT_INTERVALS.index(val)
            previous = param.REPORT_INTERVALS[max(0, current - 1)]

            span_report.children = [f"{val}:"]
            span_base.children = [f"{previous}:"]
