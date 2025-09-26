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
        dialog.open_dialog()

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
        # self.scrollable = True
        # self.style_ = "overflow-x: hidden;"

        super().__init__(persistent=True, max_width=750)

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
        close_btn.on_event("click", lambda *x: super().close_dialog(*x))
        clean_btn.on_event("click", self.reset_event)

    def validate_and_close(self, *args):
        """validate the dialog and close if no errors are found"""

        if self.custom_list.errors:
            return

        super().close_dialog(*args)

    def reset_event(self, *args):
        """search within the content and trigger reset method"""

        log.debug("About to reset content")

        self.custom_list.reset()
