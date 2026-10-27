import asyncio
import json
import pandas as pd
from types import SimpleNamespace

import component.parameter.module_parameter as param
from component.scripts.plots import (
    get_land_cover_bar_chart,
    get_nodes_and_links,
    get_sankey_chart,
    get_transition_matrix_chart,
)
from component.widget.mgci_dashboard import BeltSelector, MgciDashboard
from component.tile.dashboard_tile import DashViewA, DashViewB
from pysepal.solara.theme import ThemeState
from tests.setup_model import complete_model


def test_land_cover_chart_ranks_classes_and_labels_values_directly():
    values = pd.DataFrame({"lc_class": [1, 2], "sum": [25.0, 75.0]})
    classes = {1: ["Forest", "#123456"], 2: ["Cropland", "#abcdef"]}

    chart = get_land_cover_bar_chart(values, classes)
    series = chart.option.series[0]

    assert list(chart.option.yAxis.data) == ["Cropland", "Forest"]
    assert [item["value"] for item in series.data] == [75.0, 25.0]
    assert [item["itemStyle"]["color"] for item in series.data] == [
        "#abcdef",
        "#123456",
    ]
    assert chart.style["height"] == "150px"
    assert "75.0%" in series.data[0]["tooltip"]["formatter"]
    assert "75.0 km²" in series.data[0]["tooltip"]["formatter"]


def test_selecting_belt_updates_the_single_chart():
    values = pd.DataFrame(
        {
            "belt_class": [1, 1, 2, 2],
            "lc_class": [1, 2, 1, 2],
            "sum": [40.0, 60.0, 70.0, 30.0],
        }
    )
    model = SimpleNamespace(
        lulc_classes_sub_a={
            1: ["Artificial", "#123456"],
            2: ["Cropland", "#abcdef"],
        }
    )

    dashboard = MgciDashboard(values, model)
    dashboard.select_belt(2)

    assert dashboard.selected_belt == 2
    assert dashboard.chart_title.children == ["Land-cover composition · Alpine"]
    assert dashboard.chart.option.yAxis.data == ["Artificial", "Cropland"]
    assert dashboard.overall_button.disabled is False

    dashboard.select_belt("Total")
    assert dashboard.selected_belt == "Total"
    assert dashboard.overall_button.disabled is False
    assert dashboard.overall_button.color == "primary"
    assert dashboard.overall_button.outlined is False
    assert dashboard.belt_buttons[2].height <= 60
    assert "justify-center" in dashboard.children[1].class_
    assert dashboard.belt_buttons[2].children[0].children[0].children[0].children == [
        "mdi-image-filter-hdr"
    ]


def test_belt_selector_can_be_reused_for_sankey_without_percentages():
    selected = []
    selector = BeltSelector(["Total", 1, 2], on_select=selected.append)

    selector.select(2)

    assert selected == [2]
    assert selector.buttons[2].outlined is False
    assert selector.buttons["Total"].outlined is True
    assert selector.buttons[2].width == 128


def test_sankey_overall_combines_matching_transitions_across_belts():
    values = pd.DataFrame(
        {
            "belt_class": [1, 1, 2],
            "from_lc": [1, 1, 1],
            "to_lc": [2, 2, 2],
            "sum": [10.0, 5.0, 20.0],
        }
    )

    data = get_nodes_and_links(values, param.LC_CLASSES, (2000, 2015))

    assert data["Total"]["links"][0]["value"] == 35.0
    assert len(data[1]["links"]) == 1
    assert data[1]["links"][0]["value"] == 15.0
    assert data[2]["links"][0]["value"] == 20.0
    assert {node["name"] for node in data[1]["nodes"]} == {
        "1 · Artificial surfaces · 2000",
        "2 · Croplands · 2015",
    }
    assert "15.0 km²" in data[1]["links"][0]["tooltip"]["formatter"]


def test_sankey_follows_dark_theme_changes():
    state = ThemeState(mode="dark")
    _, chart = get_sankey_chart(theme_state=state)

    assert chart.theme == "dark"
    state.set_mode("light")
    assert chart.theme == "light"
    chart.close()


def test_sankey_shows_completed_layout_without_animation():
    _, chart = get_sankey_chart()

    assert chart.option.animation is False
    chart.close()


def test_themed_charts_can_be_closed_twice():
    state = ThemeState(mode="dark")
    _, flow = get_sankey_chart(theme_state=state)
    matrix = get_transition_matrix_chart(
        pd.DataFrame({"from_lc": [1], "to_lc": [2], "sum": [4.0]}),
        theme_state=state,
    )

    for chart in (flow, matrix):
        chart.close()
        chart.close()

    state.set_mode("light")
    assert flow.theme == "dark"
    assert matrix.theme == "dark"


def test_transition_matrix_aggregates_pairs_for_selected_belt():
    values = pd.DataFrame(
        {
            "belt_class": [2, 2, 3],
            "from_lc": [1, 1, 1],
            "to_lc": [2, 2, 2],
            "sum": [10.0, 5.0, 30.0],
        }
    )

    chart = get_transition_matrix_chart(values[values.belt_class == 2])
    cells = chart.option["series"][0]["data"]

    cell = next(cell for cell in cells if cell["value"][:2] == [1, 0])
    assert cell["value"] == [1, 0, 15.0]
    assert "15.0 km²" in cell["tooltip"]["formatter"]
    assert "Artificial surfaces" in cell["tooltip"]["formatter"]
    assert len(chart.option["xAxis"]["data"]) == 10
    assert "visualMap" not in chart.get_state()["option"]
    assert "IPY_MODEL_" not in json.dumps(chart.get_state()["option"])
    chart.close()


def test_transition_matrix_colors_observed_pairs_by_selected_impact():
    values = pd.DataFrame(
        {
            "from_lc": [1, 2, 3],
            "to_lc": [2, 1, 3],
            "sum": [10.0, 5.0, 2.0],
        }
    )
    classes = {
        1: ["Forest", "#123456"],
        2: ["Cropland", "#abcdef"],
        3: ["Grassland", "#fedcba"],
    }
    matrix = pd.DataFrame(
        {
            "from_code": [1, 2, 3],
            "to_code": [2, 1, 3],
            "impact_code": [1, 3, 2],
        }
    )

    chart = get_transition_matrix_chart(values, classes, transition_matrix=matrix)
    cells = {
        tuple(cell["value"][:2]): cell for cell in chart.option["series"][0]["data"]
    }

    assert cells[(1, 0)]["itemStyle"]["color"] == param.DECODE[1]["color"]
    assert cells[(0, 1)]["itemStyle"]["color"] == param.DECODE[3]["color"]
    assert cells[(2, 2)]["itemStyle"]["color"] == param.DECODE[2]["color"]
    assert cells[(0, 0)]["itemStyle"]["color"] not in {
        item["color"] for item in param.DECODE.values()
    }
    assert "Degradation" in cells[(1, 0)]["tooltip"]["formatter"]
    assert "10.0 km²" in cells[(1, 0)]["tooltip"]["formatter"]
    chart.close()


def test_transition_matrix_uses_custom_class_labels():
    values = pd.DataFrame(
        {"from_lc": [20], "to_lc": [30], "sum": [4.0]}
    )
    classes = {20: ["Forest", "#123456"], 30: ["Pasture", "#abcdef"]}

    chart = get_transition_matrix_chart(values, classes)
    cell = next(cell for cell in chart.option["series"][0]["data"] if cell["value"][2] == 4)

    assert cell["value"] == [1, 0, 4.0]
    assert "Forest → Pasture" in cell["tooltip"]["formatter"]
    assert chart.option["xAxis"]["data"] == ["20", "30"]
    chart.close()


def test_transition_matrix_tracks_dark_theme():
    state = ThemeState(mode="dark")
    values = pd.DataFrame({"from_lc": [1], "to_lc": [2], "sum": [4.0]})

    chart = get_transition_matrix_chart(values, theme_state=state)
    assert chart.theme == "dark"
    assert chart.option["series"][0]["itemStyle"]["borderColor"] == "#252a2d"

    state.set_mode("light")
    assert chart.theme == "light"
    assert chart.option["series"][0]["itemStyle"]["borderColor"] == "#fff"
    chart.close()


def test_b_dashboard_buttons_select_overall_and_belts():
    model = SimpleNamespace(
        reporting_years_sub_b=[(2000, 2015), 2021],
        observe=lambda *args: None,
        get_geo_area_name=lambda: "Test area",
    )
    view = DashViewB(model)
    selection = {"report": [2015, 2021]}
    values = pd.DataFrame(
        {
            "belt_class": [1, 2],
            "from_lc": [1, 1],
            "to_lc": [2, 2],
            "sum": [10.0, 20.0],
        }
    )

    view.render_dashboard((selection, values))
    assert view.selected_belt == "Total"
    assert view.sankey_data.links[0]["value"] == 30.0
    overall_chart = view.chart

    view.belt_selector.select(2)
    assert view.selected_belt == 2
    assert view.sankey_data.links[0]["value"] == 20.0
    assert view.chart is not overall_chart
    assert view.belt_selector.buttons[2].outlined is False
    assert set(view.period_selector.buttons) == {(2000, 2015), (2015, 2021)}
    assert view.period_selector.buttons[(2015, 2021)].color == "primary"
    assert view.period_selector.buttons[(2015, 2021)].outlined is False
    assert view.period_selector.buttons[(2000, 2015)].outlined is True
    view.select_view("matrix")
    assert view.selected_view == "matrix"
    assert view.chart_host.children[2] is view.impact_legend
    assert {
        item.children[1].children[0] for item in view.impact_legend.children
    } == {"Degradation", "Stable", "Improvement", "No observed area"}
    cell = next(
        cell for cell in view.chart.option["series"][0]["data"]
        if cell["value"][:2] == [1, 0]
    )
    assert cell["value"] == [1, 0, 20.0]
    assert view.matrix_button.outlined is False
    view.chart.close()


def test_b_dashboard_matrix_uses_active_transition_file(monkeypatch):
    requested = []

    def fake_read_file(path):
        requested.append(path)
        return pd.DataFrame({"from_code": [1], "to_code": [2], "impact_code": [1]})

    monkeypatch.setattr("component.scripts.plots.read_file", fake_read_file)
    model = SimpleNamespace(
        reporting_years_sub_b=[(2000, 2015), 2021],
        transition_matrix="custom_transition.csv",
        observe=lambda *args: None,
        get_geo_area_name=lambda: "Test area",
    )
    view = DashViewB(model)
    values = pd.DataFrame(
        {"belt_class": [1], "from_lc": [1], "to_lc": [2], "sum": [10.0]}
    )

    view.render_dashboard(({"report": [2015, 2021]}, values))
    view.select_view("matrix")

    assert requested == ["custom_transition.csv"]
    cell = next(
        cell for cell in view.chart.option["series"][0]["data"]
        if cell["value"][:2] == [1, 0]
    )
    assert cell["itemStyle"]["color"] == param.DECODE[1]["color"]
    view.chart.close()


def test_flow_legend_uses_equal_single_line_items_with_full_names_on_hover():
    model = SimpleNamespace(
        reporting_years_sub_b=[(2000, 2015), 2021],
        observe=lambda *args: None,
        get_geo_area_name=lambda: "Test area",
    )
    view = DashViewB(model)
    values = pd.DataFrame(
        {
            "belt_class": [1, 1],
            "from_lc": [1, 6],
            "to_lc": [6, 1],
            "sum": [10.0, 20.0],
        }
    )

    view.render_dashboard(({"report": [2015, 2021]}, values))

    assert "display:grid" in view.flow_legend.style_
    assert {item.style_ for item in view.flow_legend.children} == {
        "height:32px; min-width:0;"
    }
    aquatic = next(
        item for item in view.flow_legend.children
        if item.children[1].children[0].startswith("6 ·")
    )
    assert "Aquatic/flooded vegetation" in aquatic.children[1].children[0]
    assert "Shrubs and/or herbaceous vegetation" in aquatic.attributes["title"]
    assert "white-space:nowrap" in aquatic.children[1].style_
    view.chart.close()


def test_dashboard_side_panels_have_compact_actions_and_no_year_select():
    model = SimpleNamespace(
        reporting_years_sub_a={2020: [], 2022: []},
        reporting_years_sub_b=[(2000, 2015), 2021],
        observe=lambda *args: None,
    )
    view_a = DashViewA(model)
    view_b = DashViewB(model)

    assert view_a.btn.children[-1] == "Show dashboard"
    assert view_b.btn.children[-1] == "Show dashboard"
    assert view_a.children[0].children[0] is view_a.btn
    assert view_b.children[0].children[0] is view_b.btn
    assert view_a.available_years[-1] == 2022
    assert view_b.available_periods[-1] == {"report": [2015, 2021]}
    assert view_a._default_selection() == 2022
    assert view_b._default_selection() == {"report": [2015, 2021]}
    assert view_b.results_dialog.max_width == 1180
    assert "min(1180px, calc(90dvh - 16px))" in view_b.results_dialog.children[0].style_


def test_b_dashboard_period_button_requests_its_own_period(monkeypatch):
    requested = []

    class FakeGee:
        def create_task(self, **kwargs):
            class FakeTask:
                is_running = False

                def start(self):
                    asyncio.run(kwargs["func"]())
                    kwargs["on_finally"]()

            return FakeTask()

    async def fake_calculate(model, selection, gee_interface, scale=None):
        requested.append(selection)
        return pd.DataFrame()

    monkeypatch.setattr(
        "component.tile.dashboard_tile.calculate_b_dashboard", fake_calculate
    )
    model = complete_model(
        reporting_years_sub_b=[(2000, 2015), 2021],
        aoi_model=SimpleNamespace(feature_collection="aoi"),
        observe=lambda *args: None,
    )
    view = DashViewB(model, gee_interface=FakeGee())

    view.period_selector.buttons[(2015, 2021)].click()

    assert requested == [{"report": [2015, 2021]}]


def test_a_dashboard_year_button_requests_its_own_year(monkeypatch):
    requested = []

    class FakeGee:
        def create_task(self, **kwargs):
            class FakeTask:
                is_running = False

                def start(self):
                    asyncio.run(kwargs["func"]())
                    kwargs["on_finally"]()

            return FakeTask()

    async def fake_calculate(model, year, gee_interface, scale=None):
        requested.append(year)
        return pd.DataFrame()

    monkeypatch.setattr(
        "component.tile.dashboard_tile.calculate_a_dashboard", fake_calculate
    )
    model = complete_model(
        reporting_years_sub_a={2020: [], 2022: []},
        aoi_model=SimpleNamespace(feature_collection="aoi"),
        observe=lambda *args: None,
    )
    view = DashViewA(model, gee_interface=FakeGee())

    view.year_selector.buttons[2020].click()

    assert requested == [2020]


def test_b_dashboard_ignores_stale_period_results():
    callbacks = []

    class FakeGee:
        def create_task(self, **kwargs):
            callbacks.append(kwargs["on_done"])
            return SimpleNamespace(is_running=False)

    model = SimpleNamespace(
        reporting_years_sub_b=[(2000, 2015), 2021],
        observe=lambda *args: None,
    )
    view = DashViewB(model, gee_interface=FakeGee())
    shown = []
    view.render_dashboard = shown.append

    view._create_chart_task({"baseline": [2000, 2015]})
    view._create_chart_task({"report": [2015, 2021]})
    callbacks[0]("older")
    callbacks[1]("newer")

    assert shown == ["newer"]


def test_a_dashboard_reuses_year_until_inputs_change(monkeypatch):
    calls = []

    class FakeGee:
        def create_task(self, **kwargs):
            class FakeTask:
                is_running = False

                def start(self):
                    result = asyncio.run(kwargs["func"]())
                    kwargs["on_done"](result)
                    kwargs["on_finally"]()

            return FakeTask()

    async def fake_calculate(model, year, gee_interface, scale=None):
        calls.append(year)
        return pd.DataFrame({"year": [year]})

    monkeypatch.setattr(
        "component.tile.dashboard_tile.calculate_a_dashboard", fake_calculate
    )
    model = complete_model(
        reporting_years_sub_a={2020: [{"year": 2020}], 2022: [{"year": 2022}]},
        matrix_sub_a={1: 1},
        aoi_model=SimpleNamespace(feature_collection=object()),
        observe=lambda *args: None,
    )
    view = DashViewA(model, gee_interface=FakeGee())
    view.render_dashboard = lambda result: setattr(view, "current_selection", result[0])

    view._start_task(2020)
    view._start_task(2022)
    view._start_task(2020)
    assert calls == [2020, 2022]

    model.matrix_sub_a = {1: 2}
    view._start_task(2020)
    assert calls == [2020, 2022, 2020]


def test_b_dashboard_reuses_period_until_aoi_changes(monkeypatch):
    calls = []

    class FakeGee:
        def create_task(self, **kwargs):
            class FakeTask:
                is_running = False

                def start(self):
                    result = asyncio.run(kwargs["func"]())
                    kwargs["on_done"](result)
                    kwargs["on_finally"]()

            return FakeTask()

    async def fake_calculate(model, selection, gee_interface, scale=None):
        calls.append(selection)
        return pd.DataFrame()

    monkeypatch.setattr(
        "component.tile.dashboard_tile.calculate_b_dashboard", fake_calculate
    )
    model = complete_model(
        reporting_years_sub_b=[(2000, 2015), 2021],
        aoi_model=SimpleNamespace(feature_collection=object()),
        observe=lambda *args: None,
    )
    view = DashViewB(model, gee_interface=FakeGee())
    view.render_dashboard = lambda result: setattr(view, "current_selection", result[0])
    selection = {"report": [2015, 2021]}

    view._start_task(selection)
    view._start_task(selection)
    assert calls == [selection]

    model.aoi_model.feature_collection = object()
    view._start_task(selection)
    assert calls == [selection, selection]


def test_land_cover_chart_follows_dark_theme_changes():
    state = ThemeState(mode="light")
    values = pd.DataFrame({"lc_class": [1], "sum": [25.0]})

    chart = get_land_cover_bar_chart(
        values, {1: ["Forest", "#123456"]}, theme_state=state
    )

    assert chart.theme == "light"
    state.set_mode("dark")
    assert chart.theme == "dark"
    assert chart.option.series[0].backgroundStyle["color"] == "#353b40"
    chart.close()


def test_a_dashboard_refetches_when_inputs_change_during_request(monkeypatch):
    calls = []
    shown = []

    class FakeGee:
        def create_task(self, **kwargs):
            class FakeTask:
                is_running = False

                def start(self):
                    result = asyncio.run(kwargs["func"]())
                    kwargs["on_done"](result)
                    kwargs["on_finally"]()

            return FakeTask()

    model = complete_model(
        reporting_years_sub_a={2020: [{"year": 2020}]},
        matrix_sub_a={1: 1},
        aoi_model=SimpleNamespace(feature_collection=object()),
        observe=lambda *args: None,
    )

    async def fake_calculate(model, year, gee_interface, scale=None):
        calls.append(dict(model.matrix_sub_a))
        if len(calls) == 1:
            model.matrix_sub_a = {1: 2}
        return pd.DataFrame({"year": [year]})

    monkeypatch.setattr(
        "component.tile.dashboard_tile.calculate_a_dashboard", fake_calculate
    )
    view = DashViewA(model, gee_interface=FakeGee())
    view.render_dashboard = shown.append

    view._start_task(2020)

    assert calls == [{1: 1}, {1: 2}]
    assert len(shown) == 1
    assert view.btn.loading is False
    assert view.year_selector.loading_key is None


def test_dashboards_explain_when_an_area_is_too_large_to_chart():
    errors = []

    class FakeGee:
        def create_task(self, **kwargs):
            errors.append(kwargs["on_error"])
            return SimpleNamespace(is_running=False)

    messages = []
    import pysepal.sepalwidgets as sw

    alert = sw.Alert()
    alert.add_msg = lambda msg, type_: messages.append((msg, type_))
    model_a = SimpleNamespace(reporting_years_sub_a={2020: []}, observe=lambda *a: None)
    model_b = SimpleNamespace(
        reporting_years_sub_b=[(2000, 2015), 2021], observe=lambda *a: None
    )
    DashViewA(model_a, alert=alert, gee_interface=FakeGee())._create_chart_task(2020)
    DashViewB(model_b, alert=alert, gee_interface=FakeGee())._create_chart_task(
        {"report": [2015, 2021]}
    )

    errors[0](Exception("Computation timed out."))
    errors[1](Exception("User memory limit exceeded."))
    errors[0](Exception("Asset not found."))

    for msg, type_ in messages[:2]:
        assert "too large" in msg
        assert "process scale" in msg
        assert type_ == "error"
    assert messages[2] == ("Asset not found.", "error")
