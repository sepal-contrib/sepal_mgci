import re

import ee
import pytest

import component.parameter.module_parameter as param
from component.message import cm
from component.scripts.setup_check import SetupError
from component.tile.dashboard_tile import DashView
from component.widget.scale_selector import (
    MAX_SCALE,
    MIN_SCALE,
    NATIVE,
    SCALE_PRESETS,
    ScaleSelector,
)


def _selected(selector):
    return [
        key for key, button in selector.buttons.items() if button.color == "secondary"
    ]


def test_native_scale_is_the_default():
    selector = ScaleSelector()

    assert selector.scale is None
    assert selector.custom.v_model == ""
    assert _selected(selector) == [NATIVE]


def test_a_preset_sets_the_scale_and_shows_it_in_the_custom_field():
    selector = ScaleSelector()
    selector.toggle.v_model = 500

    assert selector.scale == 500
    assert selector.custom.v_model == "500"
    assert _selected(selector) == [500]


def test_a_custom_scale_clears_the_preset_selection():
    selector = ScaleSelector()
    selector.custom.v_model = "750"

    assert selector.scale == 750
    assert selector.toggle.v_model is None
    assert _selected(selector) == []


def test_a_custom_value_that_matches_a_preset_selects_it():
    selector = ScaleSelector()
    selector.custom.v_model = "300"

    assert selector.toggle.v_model == 300
    assert _selected(selector) == [300]


def scale_range_message():
    return cm.setup.scale_range.format(
        min=MIN_SCALE, max=MAX_SCALE, step=cm.app.drawer_item.calculation
    )


@pytest.mark.parametrize("text", ["5", str(MAX_SCALE + 1), "abc"])
def test_an_invalid_custom_value_is_shown_and_refused(text):
    selector = ScaleSelector()
    selector.toggle.v_model = 300
    selector.custom.v_model = text

    assert selector.custom.error_messages
    assert _selected(selector) == []
    with pytest.raises(SetupError, match=re.escape(scale_range_message())):
        selector.checked_scale()


def test_a_value_typed_past_the_maximum_does_not_keep_a_partial_value():
    # Each keystroke is a new value: "2000" passes through "200", which is valid.
    selector = ScaleSelector()
    for text in ("2", "20", "200", "2000"):
        selector.custom.v_model = text

    with pytest.raises(SetupError):
        selector.checked_scale()


def test_a_valid_custom_value_clears_the_error():
    selector = ScaleSelector()
    selector.custom.v_model = str(MAX_SCALE + 1)
    selector.custom.v_model = "800"

    assert selector.checked_scale() == 800
    assert not selector.custom.error_messages


def test_a_preset_clears_an_invalid_custom_value():
    selector = ScaleSelector()
    selector.custom.v_model = str(MAX_SCALE + 1)
    selector.toggle.v_model = 100

    assert selector.checked_scale() == 100
    assert not selector.custom.error_messages
    assert _selected(selector) == [100]


def test_clicking_the_selected_preset_again_keeps_it():
    selector = ScaleSelector()
    selector.toggle.v_model = 500
    selector.toggle.v_model = None

    assert selector.toggle.v_model == 500
    assert selector.scale == 500


def test_an_empty_custom_field_means_native():
    selector = ScaleSelector()
    selector.custom.v_model = "750"
    selector.custom.v_model = ""

    assert selector.scale is None
    assert _selected(selector) == [NATIVE]


def test_dashboards_use_the_selected_scale():
    view = DashView.__new__(DashView)
    view.scale_selector = ScaleSelector()
    assert view.chart_scale() is None

    view.scale_selector.toggle.v_model = 300
    assert view.chart_scale() == 300


def test_presets_stay_within_the_maximum():
    assert max(SCALE_PRESETS) <= MAX_SCALE


def test_the_maximum_scale_keeps_belt_classes_whole():
    # The belt asset is averaged in coarser pyramid levels, which gives
    # fractional belt classes from about 1,800 m.
    andes = ee.Geometry.Rectangle([-72.5, -14.0, -71.0, -13.0])
    histogram = (
        ee.Image(param.BIOBELT)
        .reduceRegion(ee.Reducer.frequencyHistogram(), andes, MAX_SCALE)
        .get("b1")
        .getInfo()
    )

    assert {float(value) for value in histogram} <= {1.0, 2.0, 3.0, 4.0}


def test_the_custom_field_keeps_room_for_its_error():
    # An error that appears below the field must not push the buttons under it.
    assert ScaleSelector().custom.hide_details is False
