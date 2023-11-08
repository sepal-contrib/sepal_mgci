from copy import deepcopy
from typing import Literal

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Bool, CInt, Dict, Int, List, directional_link, link

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

        self.w_content_a = CustomListA(items=self.model.ic_items_sub_a)
        self.w_content_b = CustomListB(items=self.model.ic_items_sub_b)

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
        to the bands(years) selected for each of subindicator.


        Args:
            change["new"]: It's the v_model from CustomList component, it will contain the user selection for each of the subindicators.
        """

        # Get the space where the elements will be inserted
        span = self.get_children(id_=f"span_{indicator}")[0]
        alert = self.get_children(id_=f"alert_{indicator}")[0]

        if not change.get("new", None):
            alert.reset()
            span.children = [""]
            self.model.reporting_years_sub_b = []
            self.model.reporting_years_sub_a = {}
            return

        data = change["new"]

        if indicator == "sub_b":
            self.model.reporting_years_sub_b = [
                next(iter(list(y.keys()))) for y in list(data.values())
            ]
            return

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
        self.model.reporting_years_sub_a = reporting_years


class EditionDialog(sw.Dialog):
    def __init__(self, custom_list, indicator):
        self.v_model = False
        self.scrollable = True
        self.max_width = 650
        self.style_ = "overflow-x: hidden;"
        self.persistent = True

        super().__init__()

        self.attributes = {"id": f"dialog_{indicator}"}
        self.custom_list = custom_list

        ok_btn = sw.Btn("OK", small=True)
        close_btn = sw.Btn("CANCEL", small=True)

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
                    v.CardActions(children=[v.Spacer(), close_btn, ok_btn]),
                ],
            ),
        ]

        ok_btn.on_event("click", self.validate_and_close)
        close_btn.on_event("click", lambda *x: setattr(self, "v_model", False))
        clean_btn.on_event("click", self.reset_event)

    def validate_and_close(self, *args):
        """validate the dialog and close if no errors are found"""

        if self.custom_list.errors:
            return

        setattr(self, "v_model", False)

    def reset_event(self, *args):
        """search within the content and trigger reset method"""

        self.custom_list.reset()


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
    errors = List([]).tag(sync=True)
    "list: list of errors that are currently displayed in each of the list elements"

    def __init__(
        self, indicator: Literal["sub_a", "sub_b"], items: list = [], label: str = ""
    ) -> sw.List:
        self.label = label
        self.items = items
        self.indicator = indicator
        self.attributes = {"id": f"content_{indicator}"}

        self.reporty_title = sw.CardTitle(children=["Reporting years"])

        super().__init__()

        self.add_btn = v.Btn(children=[v.Icon(children=["mdi-plus"])], icon=True)
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
        self.get_errors(None)

    def add_element(self, *args):
        """Creates a new element and append to the current list"""

        if self.counter <= self.max_:
            self.counter += 1
            self.children = self.children + self.get_element()

        [ch.validate_inputs() for ch in self.get_children(id_="custom_list_sub_b")]

    def update_model(self, data, id_, target=None):
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

        # if self.indicator == "sub_a":
        value = str(data["new"]) if target == "asset" else int(data["new"])
        # set a default value for the key if it doesn't exist
        # do this for each level of the dict
        # so we can set the value for the target
        # key
        tmp_vmodel.setdefault(id_, {})[target] = value

        # else:
        #     tmp_vmodel[id_] = data["new"]

        self.v_model = tmp_vmodel

    def get_errors(self, change):
        """Get errors from the select change event"""

        # Get all custom List items
        items = self.get_children(id_="custom_list_sub_b")

        # Get all errors that are there
        errors = [item.errors for item in items]

        # flatten list
        self.errors = [val for sublist in errors for val in sublist]

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

    def get_actions(self):
        """get the actions to be displayed in the list elements"""

        id_ = self.counter

        self.ids.append(id_)

        sub_btn = v.Btn(children=[v.Icon(children=["mdi-minus"])], icon=True)
        sub_btn.on_event("click", lambda *args: self.remove_element(*args, id_=id_))

        actions = [sub_btn]

        if self.counter == 1:
            actions = [self.add_btn]

        return actions, id_

    def get_element(self):
        """creates a double select widget with add and remove buttons. To allow user
        calculate subindicator B and also perform multiple calculations at once"""

        actions, id_ = self.get_actions()

        w_basep = v.Select(
            class_="mr-2 max-width-200",
            v_model=False,
            attributes={"id": "selects"},
            label=cm.calculation.year,
            items=self.items,
        )

        w_base_yref = SelectYear(label=cm.calculation.match_year)
        sub_a_content = sw.Flex(
            class_="d-flex flex-row", children=[w_basep, w_base_yref] + actions
        )

        w_basep.observe(
            lambda chg: self.update_model(chg, id_=id_, target="asset"),
            "v_model",
        )
        w_base_yref.observe(
            lambda chg: self.update_model(chg, id_=id_, target="year"),
            "v_model",
        )

        return [
            v.ListItem(
                attributes={"id": id_},
                class_="ma-0 pa-0",
                children=[
                    v.ListItemContent(children=[sub_a_content]),
                ],
            ),
            v.Divider(
                attributes={"id": id_},
            ),
        ]


class CustomListA(CustomList):
    def __init__(self, items):
        super().__init__("sub_a", items=items)
        self.children = [self.reporty_title] + self.get_element()


class CustomListB(CustomList):
    def __init__(self, items):
        super().__init__("sub_b", items=items)

        self.reporty_title = sw.Flex(
            children=[
                sw.CardTitle(children=[cm.calculation.reporting_title]),
                sw.CardSubtitle(children=[cm.calculation.reporting_subtitle]),
            ]
        )

        # Create baseline widget
        actions, _ = self.get_actions()
        self.w_baseline = BaselineItem(items=self.items, actions=actions)

        self.children = [self.w_baseline]

        self.get_children(id_="custom_list_sub_b")[0].validate_inputs()

        self.w_baseline.observe(self.update_baseline_model, "v_model")

    def remove_element(self, *args, id_):
        """Inherit from CustomList and remove title if there's only one element left"""

        super().remove_element(*args, id_=id_)

        if self.counter == 1:
            self.children = [self.w_baseline]

    def get_element(self):
        """Inherit from CustomList and overwrite get_element method to add
        a title only to the first element"""

        if self.counter == 2:
            elements = (
                [self.reporty_title] + super().get_element()
                if not self.reporty_title in self.children
                else super().get_element()
            )
            return elements

        return super().get_element()

    def update_baseline_model(self, change):
        """inherith from CustomList and overwrite update_model method to add the baseline"""

        if not change["new"]:
            return

        tmp_vmodel = deepcopy(self.v_model)

        # combine the baseline and the default current v_model
        tmp_vmodel.update(change["new"])

        self.v_model = tmp_vmodel


class BaselineItem(sw.ListItemContent):
    """Widget to allow the selection of the baseline period for the subindicator B.
    It will be composed of two selects, one for the initial year and another for the final year.
    """

    v_model = Dict(allow_none=True).tag(sync=True)

    errors = List([]).tag(sync=True)
    "list: List of errors found in the widget"

    def __init__(self, items, actions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors = []
        self.items = items

        self.attributes = {"id": "custom_list_sub_b"}

        w_basep = v.Select(
            class_="mr-2 max-width-200",
            v_model=False,
            attributes={
                "id": "selects",
                "type": "base",
                "target": "asset",
                "clean": True,
            },
            label=cm.calculation.y_start,
            items=sorted(self.items, reverse=False),
        )

        w_base_yref = SelectYear(
            attributes={
                "unique_id": "ref_select_base",
                "id": "ref_select",
                "type": "base",
                "target": "year",
                "clean": True,
            },
            reverse=False,
        )

        w_basep_container = sw.Flex(
            class_="d-flex flex-row", children=[w_basep, w_base_yref]
        )

        w_reportp = v.Select(
            class_="mr-3 ",
            v_model=False,
            attributes={
                "id": "selects",
                "type": "report",
                "target": "asset",
                "clean": True,
            },
            label=cm.calculation.y_end,
            items=sorted(self.items, reverse=True),
        )

        w_report_yref = SelectYear(
            attributes={
                "unique_id": "ref_select_report",
                "id": "ref_select",
                "type": "report",
                "target": "year",
                "clean": True,
            },
            reverse=True,
        )

        w_reportp_container = sw.Flex(
            class_="d-flex flex-row", children=[w_reportp, w_report_yref]
        )

        span_base = v.Html(
            tag="span", class_="mr-2", children=["2000"], attributes={"id": "span_base"}
        )
        span_report = v.Html(
            tag="span",
            class_="mr-2",
            children=["2015"],
            attributes={"id": "span_report"},
        )

        self.children = [
            sw.Card(
                children=[
                    sw.CardTitle(children=[cm.calculation.baseline_title]),
                    sw.CardText(
                        children=[
                            sw.Flex(
                                class_="d-flex align-center",
                                children=[span_base, w_basep_container],
                            ),
                            sw.Flex(
                                class_="d-flex align-center",
                                children=[span_report, w_reportp_container],
                            ),
                        ]
                    ),
                    sw.CardActions(children=[v.Spacer()] + actions),
                ]
            )
        ]

        _ = [
            setattr(chld, "label", cm.calculation.y_actual)
            for chld in self.get_children(id_="ref_select")
        ]

        w_basep.observe(self.set_v_model, "v_model")
        w_base_yref.observe(self.set_v_model, "v_model")

        w_reportp.observe(self.set_v_model, "v_model")
        w_report_yref.observe(self.set_v_model, "v_model")

    def validate_inputs(self):
        """Validate the inputs"""
        # Default errors
        self.errors = []

        selects = self.get_children(id_="selects") + self.get_children(id_="ref_select")

        for select in selects:
            if not select.v_model:
                select.error_messages = ["This field is required"]
                self.errors = self.errors + [select.label]
            else:
                select.error_messages = []
                self.errors = [err for err in self.errors if err != select.label]

        # Validate reference year inputs
        base_year = self.get_children(attr="unique_id", value="ref_select_base")[0]
        report_year = self.get_children(attr="unique_id", value="ref_select_report")[0]

        if all([base_year.v_model, report_year.v_model]):
            if base_year.v_model >= report_year.v_model:
                base_year.error_messages = ["Base year must be less than report year"]
                report_year.error_messages = ["Base year must be less than report year"]
                self.errors = self.errors + ["year_error"]
            else:
                base_year.error_messages = []
                report_year.error_messages = []
                self.errors = [err for err in self.errors if err != "year_error"]

    def set_v_model(self, change):
        """set the v_model of the w_reportp"""

        tmp_vmodel = deepcopy(self.v_model)
        type_ = change["owner"].attributes.get("type")
        target = change["owner"].attributes.get("target")
        value = change["owner"].v_model

        tmp_vmodel.setdefault("baseline", {}).setdefault(type_, {})[target] = value

        self.validate_inputs()
        self.v_model = tmp_vmodel


class SelectYear(v.Select):
    """Select widget to select a year, it will be always the same"""

    def __init__(
        self,
        label=cm.calculation.match_year,
        attributes={},
        reverse=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.v_model = False
        self.style_ = "min-width: 125px; max-width: 125px"
        self.label = label
        self.items = sorted(param.YEARS, reverse=reverse)
        self.attributes = attributes or {"id": "ref_select"}
