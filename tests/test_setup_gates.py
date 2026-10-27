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
from tests.setup_model import complete_model

CUSTOM = "users/someone/land_cover"
CUSTOM_IMAGES = [f"{CUSTOM}/2000", f"{CUSTOM}/2015", f"{CUSTOM}/2018"]


def not_reclassified():
    """A custom map that needs a reclassification the user did not do."""
    return complete_model(
        answer_custom_lulc=True,
        answer_need_reclassify=True,
        lc_asset_sub_a=CUSTOM,
        lc_asset_sub_b=CUSTOM,
        ic_items_sub_a=CUSTOM_IMAGES,
        ic_items_sub_b=CUSTOM_IMAGES,
        matrix_sub_a={},
        matrix_sub_b={},
        sub_a_year={1: {"asset": f"{CUSTOM}/2000", "year": 2000}},
        sub_b_year={
            "baseline": {
                "base": {"asset": f"{CUSTOM}/2000", "year": 2000},
                "report": {"asset": f"{CUSTOM}/2015", "year": 2015},
            },
            2: {"asset": f"{CUSTOM}/2018", "year": 2018},
        },
    )


def no_matrix(letter):
    return cm.setup.no_matrix.format(indicator=letter, step=cm.app.drawer_item.vegetation)


def validate_and_close(model):
    view = VegetationView.__new__(VegetationView)
    view.w_questionnaire = SimpleNamespace(
        ans_custom_lulc=model.answer_custom_lulc,
        ans_reclassify_custom_lulc=model.answer_need_reclassify,
        ans_transition_matrix=False,
    )
    view.model = model
    with pytest.raises(SetupError) as error:
        view.validate()
    return str(error.value)


def calculate(model):
    view = CalculationView.__new__(CalculationView)
    view.model = model
    view.w_use_rsa = SimpleNamespace(v_model=False)
    with pytest.raises(SetupError) as error:
        asyncio.run(view.async_perform_calculation())
    return str(error.value)


class NoTasks:
    def create_task(self, **_):
        raise AssertionError("an incomplete setup must not start a request")


def dashboard(view_class, selection):
    def run(model):
        model.observe = lambda *args: None
        model.reporting_years_sub_a = {2000: [{"year": 2000}]}
        model.reporting_years_sub_b = []
        messages = []
        alert = sw.Alert()
        alert.add_msg = lambda msg, type_: messages.append((msg, type_))
        view = view_class(model, alert=alert, gee_interface=NoTasks())
        view._start_task(selection)
        [(message, type_)] = messages
        assert type_ == "error"
        return message

    return run


@pytest.mark.parametrize(
    "gate, letter",
    [
        (validate_and_close, "A"),
        (calculate, "A"),
        (dashboard(DashViewA, 2000), "A"),
        (dashboard(DashViewB, {"report": [2015, 2018]}), "B"),
    ],
    ids=["validate-and-close", "calculate", "dashboard-a", "dashboard-b"],
)
def test_a_map_that_was_not_reclassified_is_refused_everywhere(gate, letter):
    assert gate(not_reclassified()) == no_matrix(letter)


def test_dashboards_check_the_setup_before_using_a_cached_chart():
    model = complete_model()
    model.observe = lambda *args: None
    model.reporting_years_sub_a = {2000: [{"year": 2000}]}
    messages = []
    alert = sw.Alert()
    alert.add_msg = lambda msg, type_: messages.append(msg)
    view = DashViewA(model, alert=alert, gee_interface=NoTasks())
    view._chart_cache[2000] = (view._chart_signature(), (2000, None))
    view.render_dashboard = lambda result: pytest.fail("rendered a cached chart")

    model.matrix_sub_a = {}
    view._chart_cache[2000] = (view._chart_signature(), (2000, None))
    view._start_task(2000)

    assert messages == [no_matrix("A")]
