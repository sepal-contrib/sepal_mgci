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
