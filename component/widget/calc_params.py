import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import Bool, directional_link

import component.scripts.scripts as cs
from component.message import cm
from component.widget.custom_list import CustomListA, CustomListB
import logging

log = logging.getLogger("MGCI.widget.calc_params")


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

        directional_link((self, "ready"), (self.model, "dash_ready"))

        self.ready = True

    def reset_event(self, change, indicator):
        """search within the content and trigger reset method"""

        widget = self.w_content_a if indicator == "sub_a" else self.w_content_b
        widget.reset()

        self.get_children(id_=f"desc_{indicator}")[0].children = (
            [cm.calculation[indicator].desc_disabled]
            if not change["new"]
            else [cm.calculation[indicator].desc_active]
        )

        self.get_children(id_=f"pen_{indicator}")[0].disabled = not change["new"]

    def populate_years(self, change, indicator):
        """function to trigger and send population methods from a and b content based
        on model ic_items change"""

        log.debug(
            f">>>>>>>>>>>>>> populate_years for {indicator} Received change: {change['new']}"
        )

        widgets = {"sub_a": self.w_content_a, "sub_b": self.w_content_b}

        if self.ready and change["new"]:
            log.debug(f">>>>>>>>>>>>>> populate_years Setting items")
            w_content = widgets[indicator]
            items = [{"value": item, "text": item} for item in change["new"]]
            log.debug("About to populate content with items")
            w_content.populate(items)
            w_content.set_default()  # It will set only if it is the default dataset
            w_content.validate()

    def get_item(self, indicator):
        """returns the specific structure required to display the bands(years) that will
        be used to calculate each of the specific subindicator"""

        alert = sw.Alert(attributes={"id": f"alert_{indicator}"}).hide()
        switch = sw.Switch(attributes={"id": f"switch_{indicator}"}, v_model=True)
        switch.observe(
            lambda change: self.reset_event(change, indicator=indicator), "v_model"
        )
        class_ = "pl-0"

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
            class_=class_,
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
                            ],
                        )
                    ]
                ),
                # v.ListItemAction(children=[pencil]),
            ],
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
        log.debug(f">>>>>>>>>>>>>> get_chips Received change: {change['new']}")
        # Get the space where the elements will be inserted
        span = self.get_children(id_=f"span_{indicator}")[0]
        alert = self.get_children(id_=f"alert_{indicator}")[0]

        empty_sub_a_year = {1: {"asset": None, "year": None}}
        empty_sub_b_year = (
            {
                "baseline": {
                    "base": {"asset": None, "year": None},
                    "report": {"asset": None, "year": None},
                },
                2: {"asset": None, "year": None},
            },
        )

        if not change.get("new", None):
            alert.reset()
            span.children = [""]
            self.model.reporting_years_sub_b = []
            self.model.reporting_years_sub_a = {}
            return

        if change.get("new", None) == empty_sub_a_year:
            span.children = [""]
            alert.add_msg(
                (f"Please provide valid asset and year information for all inputs."),
                type_="warning",
            )
            self.model.reporting_years_sub_a = {}
            return

        data = change["new"]

        if indicator == "sub_b":
            baseline = data.get("baseline", {}).values()
            report = {k: v for k, v in data.items() if k != "baseline"}.values()
            if not all(
                [
                    all(val.get("asset") for val in baseline) if baseline else False,
                    all(val.get("year") for val in baseline) if baseline else False,
                    all(val.get("asset") for val in report) if report else False,
                    all(val.get("year") for val in report) if report else False,
                ]
            ):
                self.model.reporting_years_sub_b = []
                span.children = [""]
                alert.add_msg(
                    (
                        f"Please provide valid asset and year information for all selected reporting years."
                    ),
                    type_="warning",
                )
                return

            alert.hide()
            reporting_years_sub_b = cs.get_reporting_years(data, "sub_b")
            baseline_chip = [
                v.Chip(
                    color="success",
                    small=True,
                    children=["-".join([str(y) for y in reporting_years_sub_b[0]])],
                )
            ]
            report_chip = [
                v.Chip(
                    color="success",
                    small=True,
                    children=[str(yr)],
                )
                for yr in reporting_years_sub_b[1:]
            ]
            span.children = (
                ["Baseline: "] + baseline_chip + ["\nReport: "] + report_chip
            )

            self.model.reporting_years_sub_b = cs.get_reporting_years(data, "sub_b")
            return

        base_years = [str(val.get("year", "...")) for val in data.values()]

        reporting_years = cs.get_reporting_years(data, "sub_a")

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
        self.max_width = 750
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
                max_width=750,
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

        log.debug("About to reset content")

        self.custom_list.reset()


# class CustomList(sw.List):
#     counter = Int(1).tag(syc=True)
#     "int: control number to check how many subb pairs are loaded"
#     max_ = Int(10 - 1).tag(syc=True)
#     "int: maximun number of sub indicator pairs to be displayed in UI"
#     v_model = Dict({}, allow_none=True).tag(syc=True)
#     "dict: where key is the consecutive number of pairs, and values are the baseline and reporting period"
#     items = List([]).tag(sync=True)
#     "list: image collection items to be loaded in each select pair"
#     indicator = None
#     "str: indicator name. sub_a or sub_b. The widget will render the corresponding subindicator"
#     ids = List([]).tag(sync=True)
#     "list: list of ids of the elements that are currently loaded in the list"
#     errors = List([]).tag(sync=True)
#     "list: list of errors that are currently displayed in each of the list elements"

#     def __init__(
#         self, indicator: Literal["sub_a", "sub_b"], items: list = [], label: str = ""
#     ) -> sw.List:
#         self.label = label
#         self.items = items
#         self.indicator = indicator
#         self.attributes = {"id": f"content_{indicator}"}
#         self.reporty_title = sw.CardTitle(children=["Reporting years"])

#         log.debug(f"<<<<<<<<<<<<<<<<<<< Received items: {items}")

#         super().__init__()

#         self.add_btn = v.Btn(children=[v.Icon(children=["mdi-plus"])], icon=True)
#         self.add_btn.on_event("click", self.add_element)

#     def remove_element(self, *args, id_):
#         """Removes element from the current list"""

#         # remove id from self.ids
#         self.ids = [val for val in self.ids if val != id_]

#         self.children = [
#             chld for chld in self.children if chld not in self.get_children(id_=id_)
#         ]

#         tmp_vmodel = deepcopy(self.v_model)
#         tmp_vmodel.pop(id_, None)

#         self.v_model = tmp_vmodel

#         self.counter -= 1
#         self.get_errors(None)

#     def add_element(self, *args):
#         """Creates a new element and append to the current list"""

#         if self.counter <= self.max_:
#             self.counter += 1
#             self.children = self.children + self.get_element()

#         [ch.validate_inputs() for ch in self.get_children(id_="custom_list_sub_b")]

#     def update_model(self, data, id_, target=None):
#         """update v_model content based on select changes.

#         Args:
#             data (dict): data from the select change event (change)
#             id_ (int): id of the element that triggered the change
#             target (str): either asset or year.
#             type_ (str, optional): baseline or reporting. Defaults to None.
#         """

#         if not data["new"]:
#             return

#         tmp_vmodel = deepcopy(self.v_model)

#         # if self.indicator == "sub_a":
#         value = str(data["new"]) if target == "asset" else int(data["new"])
#         # set a default value for the key if it doesn't exist
#         # do this for each level of the dict
#         # so we can set the value for the target
#         # key
#         tmp_vmodel.setdefault(id_, {})[target] = value

#         # else:
#         #     tmp_vmodel[id_] = data["new"]

#         self.v_model = tmp_vmodel

#     def get_errors(self, change):
#         """Get errors from the select change event"""

#         # Get all custom List items
#         items = self.get_children(id_="custom_list_sub_b")

#         # Get all errors that are there
#         errors = [item.errors for item in items]

#         # flatten list
#         self.errors = [val for sublist in errors for val in sublist]

#     def populate(self, items):
#         """receive v.select items, save in object (to be reused by new elements) and
#         fill the current one ones in the view"""

#         log.debug(f"Polulate function called")

#         self.items = items

#         select_wgts = self.get_children(id_="selects")

#         for select in select_wgts:
#             log.debug(f"Setting items for select")
#             select.items = items

#     def get_actions(self):
#         """get the actions to be displayed in the list elements"""

#         id_ = self.counter

#         self.ids.append(id_)

#         sub_btn = v.Btn(children=[v.Icon(children=["mdi-minus"])], icon=True)
#         sub_btn.on_event("click", lambda *args: self.remove_element(*args, id_=id_))

#         actions = [sub_btn]

#         if self.counter == 1:
#             actions = [self.add_btn]

#         return actions, id_

#     def get_element(self):
#         """creates a double select widget with add and remove buttons. To allow user
#         calculate subindicator B and also perform multiple calculations at once"""

#         actions, id_ = self.get_actions()

#         w_basep = v.Select(
#             style_="max-width: 550px;",
#             class_="mr-2",
#             v_model=False,
#             attributes={"id": "selects", "unique_id": f"report_asset_{id_}"},
#             label=cm.calculation.year,
#             items=self.items,
#         )

#         w_base_yref = SelectYear(
#             label=cm.calculation.match_year,
#             attributes={"unique_id": f"report_ref_{id_}", "id_": "ref_select"},
#         )

#         sub_a_content = sw.Flex(
#             class_="d-flex flex-row", children=[w_basep, w_base_yref] + actions
#         )

#         w_basep.observe(
#             lambda chg: self.update_model(chg, id_=id_, target="asset"),
#             "v_model",
#         )
#         w_base_yref.observe(
#             lambda chg: self.update_model(chg, id_=id_, target="year"),
#             "v_model",
#         )

#         return [
#             v.ListItem(
#                 attributes={"id": id_},
#                 class_="ma-0 pa-0",
#                 children=[
#                     v.ListItemContent(children=[sub_a_content]),
#                 ],
#             ),
#             v.Divider(
#                 attributes={"id": id_},
#             ),
#         ]


# class CustomListA(CustomList):
#     def __init__(self, items):
#         super().__init__("sub_a", items=items)
#         self.children = [self.reporty_title] + self.get_element()

#     def set_default(self):
#         # Default values for sub_a
#         self.get_children(attr="unique_id", value="report_asset_1")[0].v_model = (
#             param.DEFAULT_ASSETS["sub_a"][1]["asset_id"]
#         )

#         self.get_children(attr="unique_id", value="report_ref_1")[0].v_model = (
#             param.DEFAULT_ASSETS["sub_a"][1]["year"]
#         )

#     def reset(self):
#         """remove all selected values form selection widgets"""

#         select_wgts = self.get_children(id_="selects")
#         ref_wgts = self.get_children(attr="id_", value="ref_select")

#         [self.remove_element(id_=id) for id in self.ids if id != 1]

#         [setattr(select, "v_model", None) for select in (select_wgts + ref_wgts)]

#         log.debug("Resetting v_model to empty dictionary")

#         # And also reset the v_model
#         self.v_model = {}


# class CustomListB(CustomList):
#     def __init__(self, items):
#         super().__init__("sub_b", items=items)

#         self.reporty_title = sw.Flex(
#             children=[
#                 sw.CardTitle(children=[cm.calculation.reporting_title]),
#                 sw.CardSubtitle(children=[cm.calculation.reporting_subtitle]),
#             ]
#         )

#         # Create baseline widget
#         actions, _ = self.get_actions()
#         self.w_baseline = BaselineItem(items=self.items, actions=actions)

#         self.children = [self.w_baseline]

#         self.get_children(id_="custom_list_sub_b")[0].validate_inputs()

#         self.w_baseline.observe(self.update_baseline_model, "v_model")

#         # Add at leas one report year
#         self.add_element()

#     def remove_element(self, *args, id_):
#         """Inherit from CustomList and remove title if there's only one element left"""

#         if self.counter > 2:
#             super().remove_element(*args, id_=id_)

#     def get_element(self):
#         """Inherit from CustomList and overwrite get_element method to add
#         a title only to the first element"""

#         if self.counter == 2:
#             elements = (
#                 [self.reporty_title] + super().get_element()
#                 if not self.reporty_title in self.children
#                 else super().get_element()
#             )
#             return elements

#         return super().get_element()

#     def update_baseline_model(self, change):
#         """inherith from CustomList and overwrite update_model method to add the baseline"""

#         if not change["new"]:
#             return

#         tmp_vmodel = deepcopy(self.v_model)

#         # combine the baseline and the default current v_model
#         tmp_vmodel.update(change["new"])

#         self.v_model = tmp_vmodel

#     def set_default(self):
#         """Set default values"""

#         baseline = param.DEFAULT_ASSETS["sub_b"]["baseline"]
#         report = param.DEFAULT_ASSETS["sub_b"]["report"]

#         self.w_baseline.w_basep.v_model = baseline["start_year"]["asset_id"]
#         self.w_baseline.w_base_yref.v_model = baseline["start_year"]["year"]

#         self.w_baseline.w_reportp.v_model = baseline["end_year"]["asset_id"]
#         self.w_baseline.w_report_yref.v_model = baseline["end_year"]["year"]

#         self.get_children(attr="unique_id", value="report_asset_2")[0].v_model = report[
#             "asset_id"
#         ]
#         self.get_children(attr="unique_id", value="report_ref_2")[0].v_model = report[
#             "year"
#         ]

#     def reset(self):
#         """remove all selected values form selection widgets"""

#         select_wgts = self.get_children(id_="selects")
#         ref_wgts = self.get_children(attr="id_", value="ref_select")

#         [self.remove_element(id_=id) for id in self.ids if id not in [1, 2]]

#         [setattr(select, "v_model", None) for select in (select_wgts + ref_wgts)]

#         # And also reset the v_model
#         log.debug("SubB - Resetting v_model to empty dictionary")
#         self.v_model = {}


# class BaselineItem(sw.ListItemContent):
#     """Widget to allow the selection of the baseline period for the subindicator B.
#     It will be composed of two selects, one for the initial year and another for the final year.
#     """

#     v_model = Dict(allow_none=True).tag(sync=True)

#     errors = List([]).tag(sync=True)
#     "list: List of errors found in the widget"

#     def __init__(self, items, actions, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.errors = []
#         self.items = items

#         self.attributes = {"id": "custom_list_sub_b"}

#         self.w_basep = v.Select(
#             style_="max-width: 485px;",
#             class_="mr-2",
#             v_model=False,
#             attributes={
#                 "id": "selects",
#                 "type": "base",
#                 "target": "asset",
#                 "clean": True,
#             },
#             label=cm.calculation.y_start,
#             items=sorted(self.items, reverse=False),
#         )

#         self.w_base_yref = SelectYear(
#             attributes={
#                 "unique_id": "ref_select_base",
#                 "id_": "ref_select",
#                 "type": "base",
#                 "target": "year",
#                 "clean": True,
#             },
#             reverse=False,
#         )

#         w_basep_container = sw.Flex(
#             class_="d-flex flex-row", children=[self.w_basep, self.w_base_yref]
#         )

#         self.w_reportp = v.Select(
#             style_="max-width: 485px;",
#             class_="mr-3 ",
#             v_model=False,
#             attributes={
#                 "id": "selects",
#                 "type": "report",
#                 "target": "asset",
#                 "clean": True,
#             },
#             label=cm.calculation.y_end,
#             items=sorted(self.items, reverse=True),
#         )

#         self.w_report_yref = SelectYear(
#             attributes={
#                 "unique_id": "ref_select_report",
#                 "id_": "ref_select",
#                 "type": "report",
#                 "target": "year",
#                 "clean": True,
#             },
#             reverse=True,
#         )

#         w_reportp_container = sw.Flex(
#             class_="d-flex flex-row", children=[self.w_reportp, self.w_report_yref]
#         )

#         span_base = v.Html(
#             tag="span", class_="mr-2", children=["2000"], attributes={"id": "span_base"}
#         )
#         span_report = v.Html(
#             tag="span",
#             class_="mr-2",
#             children=["2015"],
#             attributes={"id": "span_report"},
#         )

#         self.children = [
#             sw.Card(
#                 children=[
#                     sw.CardTitle(children=[cm.calculation.baseline_title]),
#                     sw.CardText(
#                         children=[
#                             sw.Flex(
#                                 class_="d-flex align-center",
#                                 children=[span_base, w_basep_container],
#                             ),
#                             sw.Flex(
#                                 class_="d-flex align-center",
#                                 children=[span_report, w_reportp_container],
#                             ),
#                         ]
#                     ),
#                     sw.CardActions(children=[v.Spacer()] + actions),
#                 ]
#             )
#         ]

#         _ = [
#             setattr(chld, "label", cm.calculation.y_actual)
#             for chld in self.get_children(id_="ref_select")
#         ]

#         self.w_basep.observe(self.set_v_model, "v_model")
#         self.w_base_yref.observe(self.set_v_model, "v_model")

#         self.w_reportp.observe(self.set_v_model, "v_model")
#         self.w_report_yref.observe(self.set_v_model, "v_model")

#     def validate_inputs(self):
#         """Validate the inputs"""
#         # Default errors
#         self.errors = []

#         selects = self.get_children(id_="selects") + self.get_children(id_="ref_select")

#         for select in selects:
#             if not select.v_model:
#                 select.error_messages = ["This field is required"]
#                 self.errors = self.errors + [select.label]
#             else:
#                 select.error_messages = []
#                 self.errors = [err for err in self.errors if err != select.label]

#         # Validate reference year inputs
#         base_year = self.get_children(attr="unique_id", value="ref_select_base")[0]
#         report_year = self.get_children(attr="unique_id", value="ref_select_report")[0]

#         if all([base_year.v_model, report_year.v_model]):
#             if base_year.v_model >= report_year.v_model:
#                 base_year.error_messages = ["Base year must be less than report year"]
#                 report_year.error_messages = ["Base year must be less than report year"]
#                 self.errors = self.errors + ["year_error"]
#             else:
#                 base_year.error_messages = []
#                 report_year.error_messages = []
#                 self.errors = [err for err in self.errors if err != "year_error"]

#     def set_v_model(self, change):
#         """set the v_model of the w_reportp"""

#         tmp_vmodel = deepcopy(self.v_model)
#         type_ = change["owner"].attributes.get("type")
#         target = change["owner"].attributes.get("target")
#         value = change["owner"].v_model

#         tmp_vmodel.setdefault("baseline", {}).setdefault(type_, {})[target] = value

#         self.validate_inputs()
#         self.v_model = tmp_vmodel


# class SelectYear(v.Select):
#     """Select widget to select a year, it will be always the same"""

#     def __init__(
#         self,
#         label=cm.calculation.match_year,
#         attributes={},
#         reverse=False,
#         *args,
#         **kwargs,
#     ):
#         super().__init__(*args, **kwargs)

#         self.v_model = None
#         self.style_ = "min-width: 125px; max-width: 125px"
#         self.label = label
#         self.items = sorted(param.YEARS, reverse=reverse)
#         self.attributes = attributes
