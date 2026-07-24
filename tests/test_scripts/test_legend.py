"""Tests for legend-data builders and the per-session legend registry."""

import pandas as pd

from component.message import cm
from component.parameter.visualization import (
    biobelt_legend_data,
    degradation_legend_data,
    land_cover_legend_data,
)
from pysepal.solara.components.legend import LegendData


def _biobelt_df():
    return pd.DataFrame(
        {
            cm.aoi.legend.color: ["#ff0000", "#034502", "#24221f"],
            cm.aoi.legend.desc: [
                "Nival",
                "Remaining mountain area",
                cm.aoi.legend.total,
            ],
            cm.aoi.legend.area: ["1,234", "5,000", "6,234"],
            cm.aoi.legend.perc: ["19.8", "80.2", "100.0"],
        }
    )


def test_land_cover_legend_data_has_ten_items_without_detail():
    data = land_cover_legend_data()
    assert isinstance(data, LegendData)
    assert len(data.items) == 10
    assert data.items[0].detail == ""


def test_degradation_legend_data_labels():
    data = degradation_legend_data()
    assert [i.label for i in data.items] == ["Degraded", "Stable", "Improved"]


def test_biobelt_legend_data_detail_and_chipless_total():
    data = biobelt_legend_data(_biobelt_df())
    nival = data.items[0]
    assert nival.color == "#ff0000"
    assert nival.detail == "1,234 km² · 19.8%"
    total = data.items[-1]
    assert total.label == cm.aoi.legend.total
    assert total.color == ""
    assert total.detail == "6,234 km² · 100.0%"


def test_biobelt_legend_data_no_mountain_has_no_detail():
    df = pd.DataFrame(
        {
            cm.aoi.legend.color: ["gray"],
            cm.aoi.legend.desc: ["No mountain"],
            cm.aoi.legend.area: ["0"],
            cm.aoi.legend.perc: ["0"],
        }
    )
    assert biobelt_legend_data(df).items[0].detail == ""


from component.scripts.legend import (
    BIOBELT_KEY,
    LegendEntry,
    LegendRegistry,
    resolve_legend_view,
)


def test_register_appends_and_auto_selects():
    reg = LegendRegistry()
    reg.register("land_cover_2020", "Land cover 2020", LegendData())
    assert list(reg.entries.value) == ["land_cover_2020"]
    assert reg.selected.value == "land_cover_2020"


def test_register_same_key_dedupes_and_keeps_order():
    reg = LegendRegistry()
    reg.register("a", "A", LegendData())
    reg.register("b", "B", LegendData())
    reg.register("a", "A2", LegendData())
    assert list(reg.entries.value) == ["a", "b"]
    assert reg.entries.value["a"].title == "A2"
    assert reg.selected.value == "a"


def test_clear_empties_everything():
    reg = LegendRegistry()
    reg.register("a", "A", LegendData())
    reg.clear()
    assert reg.entries.value == {}
    assert reg.selected.value is None


def test_clear_thematic_keeps_biobelt():
    reg = LegendRegistry()
    reg.register(BIOBELT_KEY, "Bioclimatic belts", LegendData())
    reg.register("land_cover_2020", "Land cover 2020", LegendData())
    reg.clear_thematic()
    assert list(reg.entries.value) == [BIOBELT_KEY]
    assert reg.selected.value == BIOBELT_KEY


def test_unregister_updates_selection():
    reg = LegendRegistry()
    reg.register("a", "A", LegendData())
    reg.register("b", "B", LegendData())
    reg.unregister("b")
    assert list(reg.entries.value) == ["a"]
    assert reg.selected.value == "a"


def test_resolve_empty_returns_none():
    assert resolve_legend_view({}, None) == (None, [], None)


def test_resolve_builds_options_and_effective():
    entries = {
        "a": LegendEntry("A", LegendData()),
        "b": LegendEntry("B", LegendData()),
    }
    data, options, effective = resolve_legend_view(entries, "b")
    assert options == [
        {"value": "a", "text": "A"},
        {"value": "b", "text": "B"},
    ]
    assert effective == "b"
    assert data is entries["b"].data


def test_resolve_falls_back_when_selected_missing():
    entries = {"a": LegendEntry("A", LegendData())}
    _, _, effective = resolve_legend_view(entries, "gone")
    assert effective == "a"
