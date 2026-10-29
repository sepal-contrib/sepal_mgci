import ipyvuetify as v
import pysepal.sepalwidgets as sw

import component.parameter.module_parameter as param
import component.scripts as cs
from component.message import cm
from component.scripts.dashboard_data import (
    calculate_a_dashboard,
    calculate_b_dashboard,
    freeze_input as _freeze_input,
)
from component.scripts.setup_check import SetupError, check_setup
from component.widget.buttons import CloseBtn
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
    close_tree,
)


GEE_LIMIT_ERRORS = ("Computation timed out", "User memory limit exceeded")


def dashboard_error_message(error):
    """Explain Earth Engine limits in user terms; pass other errors through."""
    text = str(error)
    if not any(limit in text for limit in GEE_LIMIT_ERRORS):
        return text
    settings = cm.app.drawer_item.calculation
    return cm.error.chart_too_large.format(
        text.rstrip("."),
        cm.dashboard.label.scale.lower(),
        settings,
        settings,
        cm.app.drawer_item.task,
    )


class ResultsDialog(BaseDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_width = 1180
        self.btn_close = CloseBtn()

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
                    "box-sizing: border-box; "
                    "height: min(1180px, calc(90vh - 16px)); "
                    "height: min(1180px, calc(90dvh - 16px));"
                ),
                children=[
                    sw.CardTitle(children=["Results"]),
                    self.card_content,
                    sw.CardActions(children=[v.Spacer(), self.btn_close]),
                ],
            ),
        ]
        self.btn_close.on_event("click", self.close_dialog)


class DashView(sw.Layout):
    """Request, cache and show one sub-indicator's dashboard.

    Subclasses provide the request selector, the available choices, how a
    selection maps to a selector key and a cache key, the chart signature, the
    calculation, the rendering and the task key prefix.
    """

    task_prefix = None

    def __init__(
        self,
        indicator,
        model,
        gee_interface=None,
        scale_selector=None,
        alert=None,
        *args,
        **kwargs,
    ):
        self.indicator = indicator
        self.class_ = "d-block pa-2"

        self.model = model
        self.gee_interface = gee_interface
        self.scale_selector = scale_selector

        super().__init__(*args, **kwargs)

        self.alert = alert or sw.Alert()
        self.results_dialog = ResultsDialog(
            title="Results",
            action_text="Close",
            content=[self.alert],
            v_model=False,
        )
        self.btn = sw.Btn("Show dashboard", small=True, block=True)
        self.current_selection = None
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
        self.btn.on_event(
            "click", lambda *_: self._start_task(self._default_selection())
        )

    @property
    def request_selector(self):
        """The DashboardRequestSelector whose buttons request a selection."""
        raise NotImplementedError

    def _choices(self):
        """The selections that can be requested, latest last."""
        raise NotImplementedError

    def _selector_key(self, selection):
        """The request selector key of ``selection``."""
        raise NotImplementedError

    def _cache_key(self, selection):
        """The chart cache key of ``selection``."""
        raise NotImplementedError

    def _chart_signature(self):
        """The inputs a cached chart depends on."""
        raise NotImplementedError

    async def _calculate_chart(self, selection):
        """Return ``(selection, data)`` for ``render_dashboard``."""
        raise NotImplementedError

    def render_dashboard(self, result):
        """Show the ``(selection, data)`` result."""
        raise NotImplementedError

    def clear(self):
        """Check if there is a previously displayed dashboard and clear it, and
        reset the module summary"""

        if self.get_children(id_=f"render_{self.indicator}"):
            self.children = [
                chld
                for chld in self.children
                if chld.attributes.get("id") != f"render_{self.indicator}"
            ]

    def validate(self):
        """Raise if the setup of this sub-indicator or the process scale is not valid."""
        check_setup(self.model, self.indicator)
        if self.scale_selector is not None:
            self.scale_selector.checked_scale()

    def chart_scale(self):
        return self.scale_selector.scale if self.scale_selector is not None else None

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

    def _default_selection(self):
        choices = self._choices()
        if self.current_selection in choices:
            return self.current_selection
        return choices[-1] if choices else None

    def _start_task(self, selection):
        if not selection:
            return
        # Also before a cached chart: the setup can change after it was made.
        try:
            self.validate()
        except SetupError as error:
            self.alert.add_msg(str(error), type_="error")
            return
        signature = self._chart_signature()
        cached = self._chart_cache.get(self._cache_key(selection))
        if cached and cached[0] == signature:
            if self.current_selection != selection or not self.results_dialog.v_model:
                self.render_dashboard(cached[1])
            return
        self.request_selector.set_loading(self._selector_key(selection), True)
        self.btn.loading = True
        self.btn.disabled = True
        self._create_chart_task(selection, signature).start()

    def _create_chart_task(self, selection=None, signature=None):
        selection = selection or self._default_selection()
        signature = signature if signature is not None else self._chart_signature()
        selector_key = self._selector_key(selection) if selection else None
        self._latest_chart_request += 1
        request = self._latest_chart_request
        if self._active_chart_task and getattr(
            self._active_chart_task, "is_running", False
        ):
            self._active_chart_task.cancel()
        task = self.gee_interface.create_task(
            func=lambda: self._calculate_chart(selection),
            key=f"{self.task_prefix}_{id(self)}",
            on_done=lambda result: self._receive_chart(
                selection, signature, request, result
            ),
            on_error=lambda error: self.alert.add_msg(
                dashboard_error_message(error), type_="error"
            ),
            on_finally=lambda: self._finish_chart(selector_key, request),
        )
        self._active_chart_task = task
        return task

    def _receive_chart(self, selection, signature, request, result):
        if request != self._latest_chart_request:
            return
        if signature != self._chart_signature():
            # Inputs changed while loading; fetch again with the current ones.
            self._start_task(selection)
            return
        self._chart_cache[self._cache_key(selection)] = (signature, result)
        self.render_dashboard(result)

    def _finish_chart(self, selector_key, request):
        # A newer request owns the loading state.
        if request != self._latest_chart_request:
            return
        self.request_selector.set_loading(selector_key, False)
        self.btn.loading = False
        self.btn.disabled = not bool(self._choices())


class DashViewA(DashView):
    task_prefix = "dashboard_a"

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
            alert=alert,
            *args,
            **kwargs,
        )

        self.year_selector = DashboardRequestSelector(on_request=self._start_task)
        self.available_years = []
        self.mgci_dashboard = None
        self.title = sw.Html(tag="h3", class_="mb-3")
        self.year_label = sw.Html(
            tag="div", class_="text-caption text-center", children=["Year"]
        )
        self.statistics = sw.Layout(attributes={"id": "render_sub_a"}, class_="d-block")

        self.model.observe(self.set_years, f"reporting_years_sub_a")
        self.set_years({"new": self.model.reporting_years_sub_a})

    @property
    def request_selector(self):
        return self.year_selector

    def set_years(self, change):
        self.available_years = sorted(change["new"], key=int)
        self.year_selector.set_choices(
            [(year, str(year), year) for year in self.available_years]
        )
        self.year_selector.mark_selected(self.current_selection)
        self.btn.disabled = not bool(self.available_years)

    def _choices(self):
        return self.available_years

    def _selector_key(self, year):
        return year

    def _cache_key(self, year):
        return year

    def _chart_signature(self):
        return self.cache_context(
            getattr(self.model, "reporting_years_sub_a", None),
            getattr(self.model, "matrix_sub_a", None),
            getattr(self.model, "lulc_classes_sub_a", None),
        )

    async def _calculate_chart(self, year):
        self.validate()
        if year is None:
            raise ValueError("Add a target year in Indicator Settings.")
        return year, await calculate_a_dashboard(
            self.model, year, self.gee_interface, scale=self.chart_scale()
        )

    def render_dashboard(self, result):
        """Display the requested year's freshly calculated data."""

        year, df = result
        self.current_selection = year
        self.year_selector.mark_selected(year)

        title = cm.dashboard.window_title.format(
            indicator="A", area=self.model.get_geo_area_name()
        )

        previous = self.mgci_dashboard
        previous_belt = previous.selected_belt if previous else "Total"
        self.mgci_dashboard = MgciDashboard(df, self.model)
        if previous_belt in self.mgci_dashboard.selector.buttons:
            self.mgci_dashboard.select_belt(previous_belt)

        self.title.children = [title]
        self.statistics.children = [
            self.title,
            self.year_label,
            self.year_selector,
            self.mgci_dashboard,
        ]

        self.results_dialog.set_content([self.statistics])
        if previous is not None:
            close_tree(previous)
        self.results_dialog.open_dialog()


class DashViewB(DashView):
    task_prefix = "dashboard_b"

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

        self.attributes = {"id": "dashboard_view_sub_b"}

        super().__init__(
            indicator="sub_b",
            model=model,
            gee_interface=gee_interface,
            scale_selector=scale_selector,
            alert=alert,
            *args,
            **kwargs,
        )

        self.sankey_data = None
        self.chart = None
        self.chart_host = sw.Layout(class_="d-block", style_="width: 100%;")
        self.selected_view = "flow"
        self.period_selector = DashboardRequestSelector(on_request=self._start_task)
        self.available_periods = []
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
        self.belt_selector = None
        self.belt_title = sw.Html(tag="h4", class_="mb-2")
        self.title = sw.Html(tag="h3", class_="mb-3")
        self.period_label = sw.Html(
            tag="div", class_="text-caption text-center", children=["Period"]
        )
        self.sankey_layout = sw.Layout(
            attributes={"id": "render_sub_b"},
            class_="d-block",
            style_="width: 100%;",
        )

        self.model.observe(self.set_years, "reporting_years_sub_b")
        self.set_years({"new": self.model.reporting_years_sub_b})

    @property
    def request_selector(self):
        return self.period_selector

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
                    self._selector_key(item["value"]),
                    item["text"].replace(" -> ", " → "),
                    item["value"],
                )
                for item in items
            ]
        )
        if self.current_selection in self.available_periods:
            self.period_selector.mark_selected(
                self._selector_key(self.current_selection)
            )
        self.btn.disabled = not bool(self.available_periods)

    def _choices(self):
        return self.available_periods

    def _selector_key(self, selection):
        return tuple(next(iter(selection.values())))

    def _cache_key(self, selection):
        return next(iter(selection)), self._selector_key(selection)

    def _chart_signature(self):
        return self.cache_context(
            getattr(self.model, "sub_b_year", None),
            getattr(self.model, "reporting_years_sub_b", None),
            getattr(self.model, "matrix_sub_b", None),
            getattr(self.model, "lulc_classes_sub_b", None),
        )

    async def _calculate_chart(self, selection):
        self.validate()
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
        selected_period = self._selector_key(selection)
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
        replaced = [self.belt_selector, self.class_key]
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
        self.belt_selector.select(
            getattr(self, "selected_belt", "Total")
            if getattr(self, "selected_belt", "Total") in self.nodes_and_links
            else "Total"
        )

        title = cm.dashboard.window_title.format(
            indicator="B", area=self.model.get_geo_area_name()
        )
        self.title.children = [title]
        self.sankey_layout.children = [
            self.title,
            self.period_label,
            self.period_selector,
            self.belt_selector,
            self.view_selector,
            self.belt_title,
            self.chart_host,
        ]

        self.results_dialog.set_content([self.sankey_layout])
        for widget in replaced:
            if widget is not None:
                close_tree(widget)
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
        previous = list(self.chart_host.children)
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
        self.chart = chart
        # The class key is shown again when the view returns to the matrix;
        # render_dashboard closes it when it replaces it.
        keep = (self.matrix_hint, self.impact_legend, self.class_key)
        for widget in previous:
            close_tree(widget, keep=keep)
