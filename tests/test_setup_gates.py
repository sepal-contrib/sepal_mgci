"""Every step that computes results refuses the same incomplete setup, with the same message."""

import asyncio
from types import SimpleNamespace

import pysepal.sepalwidgets as sw
import pytest

from component.message import cm
from component.scripts.setup_check import SetupError
from component.tile.calculation_tile import CalculationView
from component.tile.dashboard_tile import DashViewA, DashViewB
from component.tile.vegetation_tile import VegetationView
from component.widget.scale_selector import MAX_SCALE, ScaleSelector
from tests.setup_model import complete_model, custom_model

def not_reclassified(**overrides):
    """A custom map that needs a reclassification the user did not do."""
    return custom_model(**{"matrix_sub_a": {}, "matrix_sub_b": {}, **overrides})


def no_matrix(letter):
    return cm.setup.no_matrix.format(indicator=letter, step=cm.app.drawer_item.vegetation)


def vegetation_view(model):
    view = VegetationView.__new__(VegetationView)
    view.w_questionnaire = SimpleNamespace(
        ans_custom_lulc=model.answer_custom_lulc,
        ans_reclassify_custom_lulc=model.answer_need_reclassify,
        ans_transition_matrix=False,
    )
    view.model = model
    return view


def validate_and_close(model):
    with pytest.raises(SetupError) as error:
        vegetation_view(model).validate()
    return str(error.value)


def calculate(model, scale_selector=None):
    view = CalculationView.__new__(CalculationView)
    view.model = model
    view.w_use_rsa = SimpleNamespace(v_model=False)
    view.w_scale = scale_selector or ScaleSelector()
    with pytest.raises(SetupError) as error:
        asyncio.run(view.async_perform_calculation())
    return str(error.value)


class NoTasks:
    def create_task(self, **_):
        raise AssertionError("an incomplete setup must not start a request")


def dashboard(view_class, selection):
    def run(model, scale_selector=None):
        model.observe = lambda *args: None
        model.reporting_years_sub_a = {2000: [{"year": 2000}]}
        model.reporting_years_sub_b = []
        messages = []
        alert = sw.Alert()
        alert.add_msg = lambda msg, type_: messages.append((msg, type_))
        view = view_class(
            model, alert=alert, gee_interface=NoTasks(), scale_selector=scale_selector
        )
        view._start_task(selection)
        [(message, type_)] = messages
        assert type_ == "error"
        return message

    return run


def no_reclassification():
    return cm.setup.no_matrix_any.format(step=cm.app.drawer_item.vegetation)


@pytest.mark.parametrize(
    "gate, expected",
    [
        (validate_and_close, no_reclassification()),
        (calculate, no_matrix("A")),
        (dashboard(DashViewA, 2000), no_matrix("A")),
        (dashboard(DashViewB, {"report": [2015, 2018]}), no_matrix("B")),
    ],
    ids=["validate-and-close", "calculate", "dashboard-a", "dashboard-b"],
)
def test_a_map_that_was_not_reclassified_is_refused_everywhere(gate, expected):
    assert gate(not_reclassified()) == expected


def test_the_land_cover_step_closes_with_only_sub_indicator_a_and_warns_about_b():
    model = not_reclassified(matrix_sub_a={10: 1, 20: 2})

    warnings = vegetation_view(model).validate()

    assert warnings == [cm.setup.partial.format(reason=no_matrix("B"), ready="A")]


def test_only_the_sub_indicator_that_was_reclassified_can_be_used():
    model = not_reclassified(matrix_sub_a={10: 1, 20: 2})
    model.observe = lambda *args: None
    model.reporting_years_sub_a = {2000: [{"year": 2000}]}
    DashViewA(model, alert=sw.Alert(), gee_interface=NoTasks()).validate()

    assert calculate(model) == no_matrix("B")
    assert dashboard(DashViewB, {"report": [2015, 2018]})(model) == no_matrix("B")


@pytest.mark.parametrize(
    "gate",
    [calculate, dashboard(DashViewA, 2000), dashboard(DashViewB, {"report": [2015, 2018]})],
    ids=["calculate", "dashboard-a", "dashboard-b"],
)
def test_a_scale_out_of_range_is_refused(gate):
    selector = ScaleSelector()
    selector.custom.v_model = str(MAX_SCALE + 1)

    message = gate(complete_model(), selector)

    assert message == cm.setup.scale_range.format(
        min=10, max=MAX_SCALE, step=cm.app.drawer_item.calculation
    )


def test_dashboards_check_the_setup_before_using_a_cached_chart():
    model = complete_model()
    model.observe = lambda *args: None
    model.reporting_years_sub_a = {2000: [{"year": 2000}]}
    messages = []
    alert = sw.Alert()
    alert.add_msg = lambda msg, type_: messages.append(msg)
    view = DashViewA(model, alert=alert, gee_interface=NoTasks())
    view.render_dashboard = lambda result: pytest.fail("rendered a cached chart")

    model.matrix_sub_a = {}
    view._chart_cache[2000] = (view._chart_signature(), (2000, None))
    view._start_task(2000)

    assert messages == [no_matrix("A")]
