import ee

import component.parameter.module_parameter as param
from component.tile.dashboard_tile import DashView
from component.widget.scale_selector import SCALE_PRESETS, ScaleSelector


def test_native_scale_is_the_default():
    assert ScaleSelector().scale is None


def test_a_preset_sets_the_scale():
    selector = ScaleSelector()
    selector.toggle.v_model = 500

    assert selector.scale == 500


def test_dashboards_use_the_selected_scale():
    view = DashView.__new__(DashView)
    view.scale_selector = ScaleSelector()
    assert view.chart_scale() is None

    view.scale_selector.toggle.v_model = 300
    assert view.chart_scale() == 300


def test_the_largest_preset_keeps_belt_classes_whole():
    # The belt asset is averaged in coarser pyramid levels, which gives
    # fractional belt classes from about 2,000 m.
    andes = ee.Geometry.Rectangle([-72.5, -14.0, -71.0, -13.0])
    histogram = (
        ee.Image(param.BIOBELT)
        .reduceRegion(ee.Reducer.frequencyHistogram(), andes, max(SCALE_PRESETS))
        .get("b1")
        .getInfo()
    )

    assert {float(value) for value in histogram} <= {1.0, 2.0, 3.0, 4.0}
