"""Request flow and rendering shared by the sub-indicator dashboard views."""

import asyncio
from types import SimpleNamespace

import pandas as pd
import pysepal.sepalwidgets as sw
import pytest

from component.message import cm
from component.tile.dashboard_tile import DashViewA, DashViewB
from tests.setup_model import complete_model


class FakeTask:
    """A GEE task the test finishes by hand, with GEETask's callback order."""

    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.is_running = False
        self.cancelled = False

    def start(self):
        self.is_running = True

    def cancel(self):
        self.cancelled = True

    def complete(self):
        self.is_running = False
        try:
            result = asyncio.run(self.callbacks["func"]())
        except Exception as error:
            self.callbacks["on_error"](error)
        else:
            self.callbacks["on_done"](result)
        self.callbacks["on_finally"]()


class FakeGee:
    def __init__(self):
        self.tasks = []

    def create_task(self, **callbacks):
        task = FakeTask(callbacks)
        self.tasks.append(task)
        return task


A_DATA = pd.DataFrame(
    {
        "belt_class": [1, 1, 2, 2],
        "lc_class": [1, 2, 1, 2],
        "sum": [40.0, 60.0, 70.0, 30.0],
    }
)
B_DATA = pd.DataFrame(
    {
        "belt_class": [1, 2],
        "from_lc": [1, 1],
        "to_lc": [2, 2],
        "sum": [10.0, 20.0],
    }
)


def make_case(kind, monkeypatch):
    """Build a dashboard view with a fake GEE interface and recorded output."""
    case = SimpleNamespace(kind=kind, calls=[], shown=[], messages=[], error=None)

    async def fake_calculate(model, selection, gee_interface, scale=None):
        case.calls.append(selection)
        if case.error is not None:
            raise case.error
        return case.data.copy()

    model = complete_model(
        observe=lambda *args: None,
        get_geo_area_name=lambda: "Test area",
    )
    if kind == "a":
        monkeypatch.setattr(
            "component.tile.dashboard_tile.calculate_a_dashboard", fake_calculate
        )
        model.reporting_years_sub_a = {2020: [{"year": 2020}], 2022: [{"year": 2022}]}
        model.matrix_sub_a = {1: 1}
        model.lulc_classes_sub_a = {
            1: ["Forest", "#123456"],
            2: ["Cropland", "#abcdef"],
        }
        view_class, case.data, case.prefix = DashViewA, A_DATA, "dashboard_a"
        case.selections = [2020, 2022]
        case.keys = [2020, 2022]
        case.change_inputs = lambda: setattr(model, "matrix_sub_a", {1: 2})
    else:
        monkeypatch.setattr(
            "component.tile.dashboard_tile.calculate_b_dashboard", fake_calculate
        )
        model.reporting_years_sub_b = [(2000, 2015), 2021]
        model.matrix_sub_b = {1: 1}
        view_class, case.data, case.prefix = DashViewB, B_DATA, "dashboard_b"
        case.selections = [{"baseline": (2000, 2015)}, {"report": [2015, 2021]}]
        case.keys = [(2000, 2015), (2015, 2021)]
        case.change_inputs = lambda: setattr(model, "matrix_sub_b", {1: 2})

    alert = sw.Alert()
    alert.add_msg = lambda msg, type_: case.messages.append((msg, type_))
    case.model = model
    case.gee = FakeGee()
    case.view = view = view_class(model, alert=alert, gee_interface=case.gee)
    case.selector = view.year_selector if kind == "a" else view.period_selector

    render = view.render_dashboard

    def record(result):
        case.shown.append(result[0])
        render(result)

    view.render_dashboard = record
    return case


@pytest.fixture(params=["a", "b"])
def case(request, monkeypatch):
    return make_case(request.param, monkeypatch)


def request_choice(case, index):
    case.selector.buttons[case.keys[index]].click()


def assert_idle(case):
    assert case.view.btn.loading is False
    assert case.view.btn.disabled is False
    assert case.selector.loading_key is None
    assert not any(
        button.loading or button.disabled for button in case.selector.buttons.values()
    )


# --- request flow shared by both views ---------------------------------------


def test_request_marks_loading_then_shows_the_selection(case):
    request_choice(case, 1)

    assert case.gee.tasks[0].callbacks["key"] == f"{case.prefix}_{id(case.view)}"
    assert case.view.btn.loading is True
    assert case.view.btn.disabled is True
    assert case.selector.loading_key == case.keys[1]
    assert case.selector.buttons[case.keys[1]].loading is True
    assert all(button.disabled for button in case.selector.buttons.values())

    case.gee.tasks[0].complete()

    assert case.calls == [case.selections[1]]
    assert case.shown == [case.selections[1]]
    assert_idle(case)
    assert case.selector.buttons[case.keys[1]].outlined is False
    assert case.selector.buttons[case.keys[0]].outlined is True
    assert case.view.results_dialog.show is True


def test_show_dashboard_requests_the_current_or_latest_choice(case):
    case.view.btn.click()
    case.gee.tasks[0].complete()
    assert case.calls == [case.selections[-1]]

    request_choice(case, 0)
    case.gee.tasks[1].complete()
    case.view.btn.click()

    assert len(case.gee.tasks) == 2
    assert case.shown == [case.selections[-1], case.selections[0], case.selections[0]]


def test_cached_selection_renders_without_a_new_request(case):
    first, second = case.selections
    request_choice(case, 0)
    case.gee.tasks[-1].complete()
    request_choice(case, 1)
    case.gee.tasks[-1].complete()

    request_choice(case, 0)

    assert len(case.gee.tasks) == 2
    assert case.calls == [first, second]
    assert case.shown == [first, second, first]
    assert_idle(case)


def test_cache_rerenders_only_for_a_new_selection_or_a_closed_dialog(case):
    first, second = case.selections
    request_choice(case, 0)
    case.gee.tasks[-1].complete()
    request_choice(case, 1)
    case.gee.tasks[-1].complete()

    case.view.results_dialog.v_model = True
    request_choice(case, 1)
    assert case.shown == [first, second]

    request_choice(case, 0)
    assert case.shown == [first, second, first]

    case.view.results_dialog.v_model = False
    request_choice(case, 0)
    assert case.shown == [first, second, first, first]
    assert len(case.gee.tasks) == 2


def test_changed_inputs_request_the_cached_selection_again(case):
    first = case.selections[0]
    request_choice(case, 0)
    case.gee.tasks[0].complete()

    case.change_inputs()
    request_choice(case, 0)

    assert len(case.gee.tasks) == 2
    case.gee.tasks[1].complete()
    assert case.calls == [first, first]
    assert case.shown == [first, first]


def test_new_request_cancels_only_a_running_one(case):
    request_choice(case, 0)
    case.gee.tasks[0].complete()
    case.change_inputs()
    request_choice(case, 0)
    request_choice(case, 1)

    assert case.gee.tasks[0].cancelled is False
    assert case.gee.tasks[1].cancelled is True
    assert case.gee.tasks[2].cancelled is False


def test_stale_result_neither_renders_nor_resets_loading(case):
    request_choice(case, 0)
    request_choice(case, 1)

    case.gee.tasks[0].complete()

    assert case.shown == []
    assert case.view.btn.loading is True
    assert case.selector.loading_key == case.keys[1]

    case.gee.tasks[1].complete()

    assert case.shown == [case.selections[1]]
    assert_idle(case)


def test_inputs_changed_while_loading_request_again_with_the_current_ones(case):
    first = case.selections[0]
    request_choice(case, 0)
    case.change_inputs()

    case.gee.tasks[0].complete()

    assert case.shown == []
    assert len(case.gee.tasks) == 2
    assert case.view.btn.loading is True
    assert case.selector.loading_key == case.keys[0]

    case.gee.tasks[1].complete()

    assert case.calls == [first, first]
    assert case.shown == [first]
    assert_idle(case)
    request_choice(case, 0)
    assert len(case.gee.tasks) == 2


def test_errors_go_to_the_alert_and_reset_loading(case):
    case.error = Exception("Computation timed out.")
    request_choice(case, 0)

    case.gee.tasks[0].complete()

    ((message, type_),) = case.messages
    assert "too large" in message
    assert type_ == "error"
    assert case.shown == []
    assert_idle(case)

    case.error = None
    request_choice(case, 0)
    assert len(case.gee.tasks) == 2


def test_missing_aoi_is_reported_without_calculating(case):
    case.model.aoi_model.feature_collection = None
    request_choice(case, 0)

    no_aoi = cm.setup.no_aoi.format(step=cm.app.drawer_item.aoi)
    assert case.messages == [(no_aoi, "error")]
    assert case.gee.tasks == []
    assert case.calls == []
    assert not case.view.btn.loading
    assert case.selector.loading_key is None


# --- rendering ---------------------------------------------------------------


def test_a_rerender_updates_the_title_and_keeps_the_belt(monkeypatch):
    case = make_case("a", monkeypatch)
    view = case.view
    view.render_dashboard((2020, case.data))
    view.mgci_dashboard.select_belt(2)
    case.model.get_geo_area_name = lambda: "Other area"

    view.render_dashboard((2022, case.data))

    (layout,) = view.results_dialog.card_content.children
    assert layout.attributes["id"] == "render_sub_a"
    title, caption, selector, dashboard = layout.children
    assert title.children == ["Sub-indicator A Dashboard · Other area"]
    assert caption.children == ["Year"]
    assert selector is view.year_selector
    assert dashboard is view.mgci_dashboard
    assert dashboard.selected_belt == 2
    assert view.year_selector.buttons[2022].outlined is False


def test_b_rerender_updates_the_title_and_keeps_belt_and_view(monkeypatch):
    case = make_case("b", monkeypatch)
    view = case.view
    first, second = case.selections
    view.render_dashboard((second, case.data))
    view.belt_selector.select(2)
    view.select_view("matrix")
    case.model.get_geo_area_name = lambda: "Other area"

    view.render_dashboard((first, case.data))

    (layout,) = view.results_dialog.card_content.children
    assert layout.attributes["id"] == "render_sub_b"
    title, caption, periods, belts, views, belt_title, host = layout.children
    assert title.children == ["Sub-indicator B Dashboard - Other area"]
    assert caption.children == ["Period"]
    assert periods is view.period_selector
    assert belts is view.belt_selector
    assert views is view.view_selector
    assert belt_title is view.belt_title
    assert host is view.chart_host
    assert view.selected_belt == 2
    assert view.belt_selector.buttons[2].outlined is False
    assert belt_title.children == ["Land-cover transitions · Alpine"]
    assert host.children == [
        view.matrix_hint,
        view.chart,
        view.impact_legend,
        view.class_key,
    ]
    assert view.look_up_years == (2000, 2015)
    assert view.period_selector.buttons[(2000, 2015)].outlined is False
