import pandas as pd
import ipyvuetify as v
import pysepal.sepalwidgets as sw
from ipywidgets import Widget

import component.parameter.module_parameter as param
from component.message import cm
from component.scripts.plots import get_land_cover_bar_chart
from component.scripts.sub_a import get_mgci


def close_tree(widget, keep=()):
    """Close ``widget`` and every widget under its ``children``.

    Widgets in ``keep`` are reused, so they and their children stay open. Only
    ``children`` is followed: other traits of ipyvue widgets hold shared models
    (``_jupyter_vue``) that must stay open.
    """
    kept = {id(item) for item in keep}

    def close(item):
        if not isinstance(item, Widget) or id(item) in kept:
            return
        for child in getattr(item, "children", None) or []:
            close(child)
        item.close()

    close(widget)


class DashboardRequestSelector(sw.Flex):
    """Compact year or period buttons for requesting dashboard data."""

    def __init__(self, on_request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_ = "d-flex flex-wrap justify-center"
        self.on_request = on_request
        self.buttons = {}
        self.loading_key = None

    def set_choices(self, choices):
        previous = list(self.buttons.values())
        self.buttons = {}
        for key, label, value in choices:
            button = v.Btn(
                small=True,
                color="primary",
                outlined=True,
                class_="text-none ma-1 px-3",
                children=[label],
            )
            button.on_event("click", lambda *_, selected=value: self.on_request(selected))
            self.buttons[key] = button
        self.children = list(self.buttons.values())
        for button in previous:
            button.close()

    def mark_selected(self, selected):
        for key, button in self.buttons.items():
            button.outlined = key != selected

    def set_loading(self, key, loading):
        if loading:
            self.loading_key = key
        elif self.loading_key != key:
            return
        else:
            self.loading_key = None
        for button_key, button in self.buttons.items():
            button.loading = self.loading_key == button_key
            button.disabled = self.loading_key is not None


class BeltSelector(sw.Flex):
    """Compact mountain belt buttons shared by both indicator charts."""

    def __init__(self, belts, on_select, details=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_ = "d-flex flex-wrap justify-center"
        self.on_select = on_select
        self.buttons = {}
        details = details or {}

        for belt in belts:
            name = "Overall" if belt == "Total" else param.BIOBELT_LEGEND[belt][0]
            content = [
                v.Html(
                    tag="div",
                    class_="d-flex align-center text-caption",
                    children=[
                        v.Icon(
                            children=["mdi-image-filter-hdr"],
                            small=True,
                            class_="mr-1",
                        ),
                        v.Html(
                            tag="span",
                            style_="display: inline-block; max-width: 90px; text-align: center; line-height: 1.05; white-space: normal;",
                            attributes={"title": name},
                            children=[name],
                        ),
                    ],
                )
            ]
            if belt in details:
                content.append(
                    v.Html(
                        tag="div",
                        class_="text-subtitle-1 font-weight-bold",
                        children=[details[belt]],
                    )
                )
            button = v.Btn(
                outlined=True,
                disabled=False,
                height=60,
                width=128,
                color="primary",
                class_="text-none ma-1 px-2",
                children=[
                    v.Flex(
                        class_="d-flex flex-column align-center justify-center",
                        children=content,
                    )
                ],
            )
            button.on_event("click", lambda *_, selected=belt: self.select(selected))
            self.buttons[belt] = button

        self.children = list(self.buttons.values())

    def select(self, belt):
        for code, button in self.buttons.items():
            button.outlined = bool(code != belt)
            button.style_ = (
                "border-color: var(--v-primary-base);"
                if code == belt
                else "border-color: var(--v-primary-base); opacity: .76;"
            )
        self.on_select(belt)


class MgciDashboard(sw.Layout):
    """Compare belt percentages and inspect one land-cover chart at a time."""

    def __init__(self, df, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_ = "d-block"
        self.df = df
        self.model = model
        self.selected_belt = "Total"
        self.chart = None
        mgci_rows = get_mgci(df)
        self.mgci = mgci_rows[mgci_rows.lc_class == "MGCI"].set_index("belt_class")[
            "mgci"
        ]

        summary = v.Card(
            elevation=0,
            class_="pa-4 mb-4",
            style_="border-left: 4px solid var(--v-primary-base);",
            children=[
                v.Html(
                    tag="div",
                    class_="text-overline",
                    children=[cm.dashboard.global_.title],
                ),
                v.Html(
                    tag="div",
                    style_="font-size: 3rem; line-height: 1.1; font-weight: 650;",
                    children=[self._percent("Total")],
                ),
                v.Html(
                    tag="div",
                    class_="text-body-2 mt-2",
                    children=[cm.dashboard.global_.desc.format(param.UNITS["sqkm"][1])],
                ),
            ],
        )

        belts = [belt for belt in df["belt_class"].unique() if belt in param.BIOBELT_LEGEND]
        self.selector = BeltSelector(
            ["Total", *sorted(belts, key=int)],
            on_select=self._show_belt,
            details={belt: self._percent(belt) for belt in ["Total", *belts]},
        )
        self.overall_button = self.selector.buttons["Total"]
        self.belt_buttons = {
            belt: button
            for belt, button in self.selector.buttons.items()
            if belt != "Total"
        }

        self.chart_title = v.Html(tag="h3", class_="ma-0", children=[])
        self.chart_description = v.Html(
            tag="p", class_="text-body-2 mb-2", children=[]
        )
        self.chart_host = sw.Layout(class_="d-block")
        breakdown = v.Card(
            elevation=0,
            class_="pa-4 mt-3",
            children=[
                self.chart_title,
                self.chart_description,
                self.chart_host,
            ],
        )
        self.children = [
            summary,
            self.selector,
            breakdown,
        ]
        self.select_belt("Total")

    def _percent(self, belt):
        value = self.mgci.get(belt)
        return f"{value:.1f}%" if value is not None and pd.notna(value) else "—"

    def select_belt(self, belt):
        self.selector.select(belt)

    def _show_belt(self, belt):
        self.selected_belt = belt
        name = "Overall" if belt == "Total" else param.BIOBELT_LEGEND[belt][0]
        self.chart_title.children = [f"Land-cover composition · {name}"]
        self.chart_description.children = (
            []
            if belt == "Total"
            else [getattr(cm.dashboard.individual.desc, f"belt_{int(belt)}")]
        )
        values = self.df if belt == "Total" else self.df[self.df.belt_class == belt]
        chart = get_land_cover_bar_chart(values, self.model.lulc_classes_sub_a or {})
        self.chart_host.children = [chart]
        if self.chart is not None:
            self.chart.close()
        self.chart = chart
