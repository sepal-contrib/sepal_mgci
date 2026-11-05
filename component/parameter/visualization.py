from component.message import msg
from pysepal.solara.components.legend import DiscreteEntry, LegendData


def biobelt_legend_data(df) -> LegendData:
    """Build the biobelt legend from the area DataFrame returned by get_belt_area.

    ``df`` columns are the renamed ``aoi.legend.*`` labels
    (Color / Description / Area (sqkm) / %). The "Total" row is rendered without
    a color chip; rows with no real area (the no-mountain fallback) carry no
    detail text.
    """
    total_label = msg('aoi.legend.total')
    items = []
    for _, row in df.iterrows():
        label = row[msg('aoi.legend.desc')]
        area = row[msg('aoi.legend.area')]
        perc = row[msg('aoi.legend.perc')]
        detail = "" if area in ("-", "0") else f"{area} km² · {perc}%"
        color = "" if label == total_label else row[msg('aoi.legend.color')]
        items.append(DiscreteEntry(label=label, color=color, detail=detail))
    return LegendData(items=items)
