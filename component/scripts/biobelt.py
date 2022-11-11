# isort: skip_file
import json
from copy import deepcopy

import ee
import pandas as pd
from sepal_ui import color

import component.parameter as param
from component.message import cm
from component.parameter.module_parameter import BIOBELT, BIOBELT_LEGEND, BIOBELT_VIS
from component.widget.legend_control import LegendControl

ee.Initialize()


def unnest(group):

    d_group = ee.Dictionary(group)
    return ee.List([[ee.String(d_group.get("group"))], [d_group.get("sum")]]).flatten()


def get_belt_area(aoi, biobelt):
    """returns legend-dict"""

    area = (
        ee.List(
            ee.Image.pixelArea()
            .divide(1e6)  # To display in square kilometers
            .addBands(biobelt)
            .reduceRegion(
                **{
                    "reducer": ee.Reducer.sum().group(1),
                    "geometry": aoi,
                    "scale": biobelt.projection().nominalScale(),
                }
            )
            .get("groups")
        )
        .map(unnest)
        .getInfo()
    )

    df = pd.DataFrame(area, columns=["class", "area"])

    total_area = df.sum()[1]
    df = df.append({"class": "total", "area": df.sum()[1]}, ignore_index=True)
    df["perc"] = df["area"] / total_area * 100
    df["area"] = df["area"].apply("{:,.0f}".format)

    # Parse legend code by display description
    df["desc"] = df["class"].apply(lambda x: BIOBELT_LEGEND[x][0])
    # Get the corresponding code to each class
    df["color"] = df["class"].apply(lambda x: BIOBELT_LEGEND[x][1])
    df = df.round(2)
    df = df[["color", "desc", "area", "perc"]]
    df = df.astype(str)
    df = df.rename(
        columns={
            "color": cm.aoi.legend.color,
            "desc": cm.aoi.legend.desc,
            "area": cm.aoi.legend.area,
            "perc": cm.aoi.legend.perc,
        }
    )

    if len(df) == 1:
        df.iloc[0] = [color.main, cm.legend.no_mountain, "-", "-"]

    return json.loads(df.to_json(orient="index"))


def add_belt_map(aoi_model, map_):
    """Create and display bioclimatic belt layer on a map."""

    aoi = aoi_model.feature_collection.geometry()
    biobelt = ee.Image(BIOBELT).clip(aoi)

    # Create legend
    legend_dict = get_belt_area(aoi, biobelt)

    # Add kapos mountain layer to map
    map_.zoom_ee_object(aoi_model.feature_collection.geometry())
    map_.addLayer(biobelt, BIOBELT_VIS, cm.aoi.legend.belts)

    if any([isinstance(c, LegendControl) for c in map_.controls]):
        map_.legend.legend_dict = deepcopy(legend_dict)
        return

    # Define as class member so it can be accessed from outside.
    map_.legend = LegendControl(
        legend_dict=legend_dict, title="", position="bottomright"
    )
    map_.add_control(map_.legend)