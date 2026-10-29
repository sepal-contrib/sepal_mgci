"""Every window of the app closes with the same "Close" button as the step windows."""

import ipyvuetify as v
import pysepal.sepalwidgets as sw
import pytest

from component.message import cm
from component.tile.dashboard_tile import ResultsDialog
from component.tile.vegetation_tile import VegetationDialog
from component.widget.calc_params import EditionDialog
from component.widget.custom_list import CustomListA


def contains(widget, target):
    if widget is target:
        return True
    children = getattr(widget, "children", None) or []
    return any(
        contains(child, target) for child in children if not isinstance(child, str)
    )


def results_window():
    return ResultsDialog(title="Results", action_text="Close", content=[])


def years_window():
    return EditionDialog(CustomListA(items=[]), "sub_a")


def land_cover_window():
    return VegetationDialog(v.Html(tag="div"), sw.Alert())


@pytest.mark.parametrize(
    "make",
    [results_window, years_window, land_cover_window],
    ids=["results", "years", "land-cover"],
)
def test_each_window_closes_with_the_step_window_close_button(make):
    window = make()
    window.open_dialog()

    assert contains(window, window.btn_close)
    assert window.btn_close.msg == cm.app.step_action.close
    assert window.btn_close.text is True
    assert window.btn_close.outlined is True

    window.btn_close.fire_event("click", None)
    assert window.show is False
