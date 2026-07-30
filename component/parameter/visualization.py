from component.parameter.module_parameter import LC_CLASSES
import pandas as pd

from component.message import cm
from pysepal.solara.components.legend import DiscreteEntry, LegendData

df = pd.read_csv(LC_CLASSES, header=0)


degradation = {
    "palette": ["#8B0000", "#B0C4DE", "#008000"],
    "max": 3,
    "min": 1,
}

degrad_label = {
    "degraded": "Degraded",
    "stable": "Stable",
    "improved": "Improved",
}

degradation_legend = {
    label: color for label, color in zip(degrad_label.values(), degradation["palette"])
}

land_cover = {"max": len(df), "min": 1, "palette": list(df.color.tolist())}
land_cover_legend = {
    label: color for label, color in zip(df.desc.tolist(), df.color.tolist())
}


VIS_PARAMS = {
    "land_cover": land_cover,
    "degradation": degradation,
}

LEGENDS = {
    "land_cover": land_cover_legend,
    "degradation": degradation_legend,
}


def land_cover_legend_data() -> LegendData:
    """Discrete chips for the land-cover classes."""
    return LegendData(
        items=[
            DiscreteEntry(label=label, color=color)
            for label, color in LEGENDS["land_cover"].items()
        ]
    )


def degradation_legend_data() -> LegendData:
    """Discrete chips for the degradation classes."""
    return LegendData(
        items=[
            DiscreteEntry(label=label, color=color)
            for label, color in LEGENDS["degradation"].items()
        ]
    )


def biobelt_legend_data(df) -> LegendData:
    """Build the biobelt legend from the area DataFrame returned by get_belt_area.

    ``df`` columns are the renamed ``cm.aoi.legend.*`` labels
    (Color / Description / Area (sqkm) / %). The "Total" row is rendered without
    a color chip; rows with no real area (the no-mountain fallback) carry no
    detail text.
    """
    total_label = cm.aoi.legend.total
    items = []
    for _, row in df.iterrows():
        label = row[cm.aoi.legend.desc]
        area = row[cm.aoi.legend.area]
        perc = row[cm.aoi.legend.perc]
        detail = "" if area in ("-", "0") else f"{area} km² · {perc}%"
        color = "" if label == total_label else row[cm.aoi.legend.color]
        items.append(DiscreteEntry(label=label, color=color, detail=detail))
    return LegendData(items=items)
