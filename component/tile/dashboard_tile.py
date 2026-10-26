import ipyvuetify as v
import pysepal.sepalwidgets as sw

import component.parameter.module_parameter as param
import component.scripts as cs
from component.message import cm
from component.scripts.dashboard_data import calculate_a_dashboard, calculate_b_dashboard
from component.scripts.plots import (
    get_lc_class_map,
    get_nodes_and_links,
    get_sankey_chart,
    get_transition_matrix_chart,
)
from component.widget.base_dialog import BaseDialog
from component.widget.mgci_dashboard import (
    BeltSelector,
    DashboardRequestSelector,
    MgciDashboard,
)


def _freeze_input(value):
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), _freeze_input(item)) for key, item in value.items())
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_input(item) for item in value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return repr(value)


class ResultsDialog(BaseDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_width = 1180

        self.card_content = sw.CardText(
            class_="flex-grow-1",
            style_="min-height: 0; overflow-y: auto;",
            children=[
                "This is the results dialog. It will display the results of the calculations."
            ],
        )

        self.children = [
            sw.Card(
                class_="pa-2 d-flex flex-column",
                style_=(
                    "height: min(1180px, calc(100vh - 64px)); "
                    "height: min(1180px, calc(100dvh - 64px));"
                ),
                children=[
                    sw.CardTitle(children=["Results"]),
                    self.card_content,
                ],
            ),
        ]


class DashView(sw.Layout):
    def __init__(
        self, indicator, model, gee_interface=None, scale_selector=None, *args, **kwargs
    ):
        self.indicator = indicator
        self.class_ = "d-block pa-2"

        self.model = model
        self.gee_interface = gee_interface
        self.scale_selector = scale_selector

        super().__init__(*args, **kwargs)

    def clear(self):
        """Check if there is a previously displayed dashboard and clear it, and
        reset the module summary"""

        if self.get_children(id_=f"render_{self.indicator}"):
            self.children = [
                chld
                for chld in self.children
                if chld.attributes.get("id") != f"render_{self.indicator}"
            ]

    def render_dashboard(self, *args):
        """Validate shared dashboard prerequisites."""
        if not self.model.aoi_model.feature_collection:
            raise Exception(cm.error.no_aoi)

    def chart_scale(self):
        if self.scale_selector is None or self.scale_selector.disabled:
            return None
        return self.scale_selector.v_model

    def cache_context(self, *inputs):
        aoi = getattr(getattr(self.model, "aoi_model", None), "feature_collection", None)
        return (
            id(aoi),
            getattr(getattr(self.model, "aoi_model", None), "name", None),
            self.chart_scale(),
            _freeze_input(getattr(self.model, "rsa", None)),
            _freeze_input(getattr(self.model, "dem", None)),
            _freeze_input(getattr(self.model, "transition_matrix", None)),
            *(_freeze_input(value) for value in inputs),
        )


class DashViewA(DashView):
    def __init__(
        self,
        model,
        alert: sw.Alert = None,
        gee_interface=None,
        scale_selector=None,
        *args,
        **kwargs,
    ):
        self.attributes = {"id": f"dashboard_view_sub_a"}

        super().__init__(
            indicator="sub_a",
            model=model,
            gee_interface=gee_interface,
            scale_selector=scale_selector,
            *args,
            **kwargs,
        )

        self.alert = alert or sw.Alert()
        self.results_dialog = ResultsDialog(
            title="Results",
            action_text="Close",
            content=[self.alert],
            v_model=False,
        )

        self.btn = sw.Btn("Show dashboard", small=True, block=True)
        self.year_selector = DashboardRequestSelector(on_request=self._start_year_task)
        self.available_years = []
        self.current_year = None
        self._latest_chart_request = 0
        self._active_chart_task = None
        self._chart_cache = {}

        self.children = [
            sw.Flex(
                class_="d-block mt-2",
                style_="width: 100%;",
                children=[self.btn, self.results_dialog],
            ),
        ]

        self.model.observe(self.set_years, f"reporting_years_sub_a")
        self.btn.on_event("click", lambda *_: self._start_year_task(self._default_year()))
        self.set_years({"new": self.model.reporting_years_sub_a})

    def set_years(self, change):
        self.available_years = sorted(change["new"], key=int)
        self.year_selector.set_choices(
            [(year, str(year), year) for year in self.available_years]
        )
        self.year_selector.mark_selected(self.current_year)
        self.btn.disabled = not bool(self.available_years)

    def _default_year(self):
        return (
            self.current_year
            if self.current_year in self.available_years
            else self.available_years[-1] if self.available_years else None
        )

    def _start_year_task(self, year):
        if year is None:
            return
        signature = self._chart_signature()
        cached = self._chart_cache.get(year)
        if cached and cached[0] == signature:
            if self.current_year != year or not self.results_dialog.v_model:
                self.render_dashboard(cached[1])
            return
        self.year_selector.set_loading(year, True)
        self.btn.loading = True
        self.btn.disabled = True
        self._create_chart_task(year, signature).start()

    def _chart_signature(self):
        return self.cache_context(
            getattr(self.model, "reporting_years_sub_a", None),
            getattr(self.model, "matrix_sub_a", None),
            getattr(self.model, "lulc_classes_sub_a", None),
        )

    def _create_chart_task(self, year=None, signature=None):
        year = year if year is not None else self._default_year()
        signature = signature if signature is not None else self._chart_signature()
        self._latest_chart_request += 1
        request = self._latest_chart_request
        if self._active_chart_task and getattr(
            self._active_chart_task, "is_running", False
        ):
            self._active_chart_task.cancel()
        task = self.gee_interface.create_task(
            func=lambda: self._calculate_chart(year),
            key=f"dashboard_a_{id(self)}",
            on_done=lambda result: self._receive_chart(year, signature, request, result),
            on_error=lambda error: self.alert.add_msg(str(error), type_="error"),
            on_finally=lambda: self._finish_chart(year, request),
        )
        self._active_chart_task = task
        return task

    def _receive_chart(self, year, signature, request, result):
        if request == self._latest_chart_request and signature == self._chart_signature():
            self._chart_cache[year] = (signature, result)
            self.render_dashboard(result)

    def _finish_chart(self, year, request):
        self.year_selector.set_loading(year, False)
        if request == self._latest_chart_request:
            self.btn.loading = False
            self.btn.disabled = not bool(self.available_years)

    async def _calculate_chart(self, year):
        DashView.render_dashboard(self)
        if year is None:
            raise ValueError("Add a target year in Indicator Settings.")
        return year, await calculate_a_dashboard(
            self.model, year, self.gee_interface, scale=self.chart_scale()
        )

    def render_dashboard(self, result):
        """Display the requested year's freshly calculated data."""

        year, df = result
        self.current_year = year
        self.year_selector.mark_selected(year)

        # Create title at render time when AOI is available
        title = sw.Html(
            tag="h3",
            class_="mb-3",
            children=[f"Sub-indicator A Dashboard · {self.model.get_geo_area_name()}"],
        )

        previous = getattr(self, "mgci_dashboard", None)
        previous_belt = previous.selected_belt if previous else "Total"
        self.mgci_dashboard = MgciDashboard(df, self.model)
        if previous_belt in self.mgci_dashboard.selector.buttons:
            self.mgci_dashboard.select_belt(previous_belt)

        statistics = sw.Layout(
            attributes={"id": "render_sub_a"},
            class_="d-block",
            children=[
                title,
                sw.Html(
                    tag="div", class_="text-caption text-center", children=["Year"]
                ),
                self.year_selector,
                self.mgci_dashboard,
            ],
        )

        self.results_dialog.set_content([statistics])
        if previous and previous.chart:
            previous.chart.close()
        self.results_dialog.open_dialog()


class DashViewB(DashView):
    def __init__(
        self,
        model,
        alert: sw.Alert = None,
        gee_interface=None,
        scale_selector=None,
        *args,
        **kwargs,
    ):
        """Dashboard view for sub_b indicator"""

        self.alert = alert or sw.Alert()

        self.attributes = {"id": "dashboard_view_sub_b"}

        super().__init__(
            indicator="sub_b",
            model=model,
            gee_interface=gee_interface,
            scale_selector=scale_selector,
            *args,
            **kwargs,
        )

        self.results_dialog = ResultsDialog(
            title="Results",
            action_text="Close",
            content=[self.alert],
            v_model=False,
        )

        self.btn = sw.Btn("Show dashboard", small=True, block=True)

        self.sankey_data = None
        self.chart = None
        self.chart_host = sw.Layout(class_="d-block", style_="width: 100%;")
        self.selected_view = "flow"
        self.period_selector = DashboardRequestSelector(
            on_request=self._start_period_task
        )
        self.period_buttons = {}
        self.available_periods = []
        self.current_selection = None
        self._latest_chart_request = 0
        self._active_chart_task = None
        self._chart_cache = {}
        self.flow_button = v.Btn(
            small=True, color="primary", class_="text-none mx-1", children=["Flow"]
        )
        self.matrix_button = v.Btn(
            small=True,
            color="primary",
            outlined=True,
            class_="text-none mx-1",
            children=["Matrix"],
        )
        self.flow_button.on_event("click", lambda *_: self.select_view("flow"))
        self.matrix_button.on_event("click", lambda *_: self.select_view("matrix"))
        self.view_selector = sw.Flex(
            class_="d-flex justify-center mt-2 mb-2",
            children=[self.flow_button, self.matrix_button],
        )
        self.class_key = None
        self.matrix_hint = v.Html(
            tag="div",
            class_="text-caption text-center",
            children=["From class ↓  ·  To class →  ·  Area (km²) on hover"],
        )
        impact_items = [
            (param.DECODE[code]["label"], param.DECODE[code]["color"])
            for code in (1, 2, 3)
        ]
        impact_items.append(("No observed area", "rgba(128, 138, 142, 0.18)"))
        self.impact_legend = sw.Flex(
            class_="d-flex flex-wrap justify-center text-caption mt-1 mb-2",
            children=[
                v.Html(
                    tag="span",
                    class_="d-inline-flex align-center mx-1 my-1",
                    style_="width:145px; height:30px;",
                    children=[
                        v.Html(
                            tag="span",
                            style_=(
                                "display:inline-block; width:12px; height:12px; "
                                "border-radius:2px; border:1px solid var(--v-primary-base); "
                                f"background:{color};"
                            ),
                        ),
                        v.Html(tag="span", class_="ml-1", children=[label]),
                    ],
                )
                for label, color in impact_items
            ],
        )

        self.children = [
            sw.Flex(
                class_="d-block mt-2",
                style_="width: 100%;",
                children=[self.btn, self.results_dialog],
            ),
        ]

        self.model.observe(self.set_years, "reporting_years_sub_b")
        self.btn.on_event("click", lambda *_: self._start_period_task(self._default_selection()))

        self.set_years({"new": self.model.reporting_years_sub_b})

    def set_years(self, change):
        """Set the available transition periods:

        Args:
            change["new]: List of years in the form:
                [[start_base_y, end_base_y], rep_y2, rep_y2, ...]
        """

        items = cs.get_sub_b_items(change["new"]) if change["new"] else []
        items.sort(key=lambda item: int(next(iter(item["value"].values()))[1]))
        self.available_periods = [item["value"] for item in items]
        self.period_selector.set_choices(
            [
                (
                    tuple(next(iter(item["value"].values()))),
                    item["text"].replace(" -> ", " → "),
                    item["value"],
                )
                for item in items
            ]
        )
        self.period_buttons = self.period_selector.buttons
        if self.current_selection in self.available_periods:
            self.period_selector.mark_selected(
                tuple(next(iter(self.current_selection.values())))
            )
        self.btn.disabled = not bool(self.available_periods)

    def _default_selection(self):
        return (
            self.current_selection
            if self.current_selection in self.available_periods
            else self.available_periods[-1] if self.available_periods else None
        )

    def _start_period_task(self, selection):
        if not selection:
            return
        period = tuple(next(iter(selection.values())))
        cache_key = (next(iter(selection)), period)
        signature = self._chart_signature()
        cached = self._chart_cache.get(cache_key)
        if cached and cached[0] == signature:
            if self.current_selection != selection or not self.results_dialog.v_model:
                self.render_dashboard(cached[1])
            return
        self.period_selector.set_loading(period, True)
        self.btn.loading = True
        self.btn.disabled = True
        self._create_chart_task(selection, signature).start()

    def _chart_signature(self):
        return self.cache_context(
            getattr(self.model, "sub_b_year", None),
            getattr(self.model, "reporting_years_sub_b", None),
            getattr(self.model, "matrix_sub_b", None),
            getattr(self.model, "lulc_classes_sub_b", None),
        )

    def _create_chart_task(self, selection=None, signature=None):
        selection = selection or self._default_selection()
        signature = signature if signature is not None else self._chart_signature()
        period = tuple(next(iter(selection.values()))) if selection else None
        self._latest_chart_request += 1
        request = self._latest_chart_request
        if self._active_chart_task and getattr(
            self._active_chart_task, "is_running", False
        ):
            self._active_chart_task.cancel()
        task = self.gee_interface.create_task(
            func=lambda: self._calculate_chart(selection),
            key=f"dashboard_b_{id(self)}",
            on_done=lambda result: self._receive_chart(period, signature, request, result),
            on_error=lambda error: self.alert.add_msg(str(error), type_="error"),
            on_finally=lambda: self._finish_chart(period, request),
        )
        self._active_chart_task = task
        return task

    def _receive_chart(self, period, signature, request, result):
        if request == self._latest_chart_request and signature == self._chart_signature():
            selection = result[0] if isinstance(result, tuple) else None
            if selection:
                self._chart_cache[(next(iter(selection)), period)] = (signature, result)
            self.render_dashboard(result)

    def _finish_chart(self, period, request):
        self.period_selector.set_loading(period, False)
        if request == self._latest_chart_request:
            self.btn.loading = False
            self.btn.disabled = not bool(self.available_periods)

    async def _calculate_chart(self, selection):
        if not self.model.aoi_model.feature_collection:
            raise ValueError(cm.error.no_aoi)
        if not selection:
            raise ValueError("Select a transition period.")
        df = await calculate_b_dashboard(
            self.model, selection, self.gee_interface, scale=self.chart_scale()
        )
        return selection, df

    def render_dashboard(self, result):
        """Display the requested period's freshly calculated data."""

        selection, chart_data = result
        self.current_selection = selection
        selected_period = tuple(next(iter(selection.values())))
        self.period_selector.mark_selected(selected_period)
        self.chart_data = chart_data
        look_up_years = selected_period
        self.look_up_years = look_up_years
        self.lc_classes = (
            getattr(self.model, "lulc_classes_sub_b", None) or param.LC_CLASSES
        )
        class_labels = get_lc_class_map(self.lc_classes)
        class_codes = sorted(
            set(class_labels) | set(chart_data.from_lc) | set(chart_data.to_lc)
        )
        self.class_key = sw.Flex(
            class_="d-flex flex-wrap justify-center text-caption mb-2",
            children=[
                v.Html(
                    tag="span",
                    class_="mx-2 my-1",
                    children=[
                        f"{code} · {class_labels.get(code, {}).get('desc', 'Class ' + str(code))}"
                    ],
                )
                for code in class_codes
            ],
        )
        self.nodes_and_links = get_nodes_and_links(
            chart_data, self.lc_classes, look_up_years
        )
        belts = sorted(
            (belt for belt in self.nodes_and_links if belt != "Total"), key=int
        )
        self.belt_selector = BeltSelector(["Total", *belts], on_select=self.select_belt)
        self.belt_title = sw.Html(tag="h4", class_="mb-2")
        self.belt_selector.select(
            getattr(self, "selected_belt", "Total")
            if getattr(self, "selected_belt", "Total") in self.nodes_and_links
            else "Total"
        )

        # Create title at render time when AOI is available
        title = sw.Html(
            tag="h3",
            class_="mb-3",
            children=[f"Sub-indicator B Dashboard - {self.model.get_geo_area_name()}"],
        )

        # Create the sankey chart layout with proper width
        sankey_layout = sw.Layout(
            attributes={"id": "render_sub_b"},
            class_="d-block",
            style_="width: 100%;",
            children=[
                title,
                sw.Html(
                    tag="div", class_="text-caption text-center", children=["Period"]
                ),
                self.period_selector,
                self.belt_selector,
                self.view_selector,
                self.belt_title,
                self.chart_host,
            ],
        )

        self.results_dialog.set_content([sankey_layout])
        self.results_dialog.open_dialog()

    def select_belt(self, belt):
        self.selected_belt = belt
        name = "Overall" if belt == "Total" else param.BIOBELT_LEGEND[belt][0]
        self.belt_title.children = [f"Land-cover transitions · {name}"]
        self._update_chart()

    def select_view(self, view):
        self.selected_view = view
        self.flow_button.outlined = view != "flow"
        self.matrix_button.outlined = view != "matrix"
        if hasattr(self, "chart_data"):
            self._update_chart()

    def _update_chart(self):
        belt_data = self.nodes_and_links[self.selected_belt]
        values = (
            self.chart_data
            if self.selected_belt == "Total"
            else self.chart_data[self.chart_data.belt_class == self.selected_belt]
        )
        if self.selected_view == "matrix":
            chart = get_transition_matrix_chart(
                values,
                self.lc_classes,
                transition_matrix=getattr(self.model, "transition_matrix", None),
            )
            self.chart_host.children = [
                self.matrix_hint,
                chart,
                self.impact_legend,
                self.class_key,
            ]
            self.sankey_data = None
        else:
            series, chart = get_sankey_chart()
            series.nodes = belt_data["nodes"]
            series.links = belt_data["links"]
            self.sankey_data = series
            self.flow_years = sw.Flex(
                class_="d-flex justify-space-between text-overline px-4 mt-2",
                children=[
                    v.Html(tag="span", children=[f"From · {self.look_up_years[0]}"]),
                    v.Html(tag="span", children=[f"To · {self.look_up_years[1]}"]),
                ],
            )
            labels = get_lc_class_map(self.lc_classes)
            codes = sorted(set(values.from_lc) | set(values.to_lc))
            self.flow_legend = sw.Flex(
                class_="mt-1 mb-2 px-3",
                style_=(
                    "display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); "
                    "gap:4px 10px; width:100%;"
                ),
                children=[
                    v.Html(
                        tag="span",
                        class_="d-inline-flex align-center text-caption",
                        style_="height:32px; min-width:0;",
                        attributes={
                            "title": labels.get(code, {}).get("desc", f"Class {code}")
                        },
                        children=[
                            v.Html(
                                tag="span",
                                style_=(
                                    "display:inline-block; flex:0 0 11px; height:11px; "
                                    "border-radius:2px; border:1px solid var(--v-primary-base); "
                                    f"background:{labels.get(code, {}).get('color', '#888888')};"
                                ),
                            ),
                            v.Html(
                                tag="span",
                                class_="ml-2",
                                style_="min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;",
                                children=[
                                    f"{code} · "
                                    + (
                                        "Aquatic/flooded vegetation"
                                        if code == 6
                                        and labels.get(code, {}).get("desc")
                                        == "Shrubs and/or herbaceous vegetation, aquatic or regularly flooded"
                                        else labels.get(code, {}).get("desc", f"Class {code}")
                                    )
                                ],
                            ),
                        ],
                    )
                    for code in codes
                ],
            )
            self.chart_host.children = [self.flow_years, chart, self.flow_legend]
        previous_chart = self.chart
        self.chart = chart
        if previous_chart is not None:
            previous_chart.close()
