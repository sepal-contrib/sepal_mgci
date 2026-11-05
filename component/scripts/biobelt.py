# isort: skip_file
import json

import ee
import pandas as pd

from component.message import msg
from component.parameter.module_parameter import BIOBELT_LEGEND
from component.scripts.aoi_geometry import aoi_bbox
from pysepal.solara import get_current_gee_interface


def unnest(group):
    d_group = ee.Dictionary(group)
    return ee.List([[ee.String(d_group.get("group"))], [d_group.get("sum")]]).flatten()


async def get_belt_area(aoi, biobelt, gee_interface=None) -> tuple:
    """returns legend-dict for the belt areas over the AOI feature collection."""

    gee_interface = gee_interface or get_current_gee_interface()

    try:
        area = await gee_interface.get_info_async(
            ee.List(
                ee.Image.pixelArea()
                .divide(1e6)  # To display in square kilometers
                .addBands(biobelt)
                .clip(aoi)
                .reduceRegion(
                    **{
                        "reducer": ee.Reducer.sum().group(1),
                        "geometry": aoi_bbox(aoi),
                        "scale": biobelt.projection().nominalScale(),
                        "maxPixels": 1e13,
                        "bestEffort": True,
                    }
                )
                .get("groups")
            ).map(unnest)
        )

        df = pd.DataFrame(area, columns=["class", "area"])

        # Cast class to int
        df["class"] = df["class"].astype(float).astype(int)

        total_area = df.sum().iloc[1]

        df_area = pd.DataFrame({"class": ["total"], "area": [total_area]})
        df = pd.concat([df, df_area], ignore_index=True)
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
                "color": msg('aoi.legend.color'),
                "desc": msg('aoi.legend.desc'),
                "area": msg('aoi.legend.area'),
                "perc": msg('aoi.legend.perc'),
            }
        )

        if len(df) == 1:
            df.iloc[0] = ["#24221f", msg('aoi.legend.no_mountain'), "-", "-"]

    except ZeroDivisionError:
        # If a division by zero error happens, return meaningful values
        df_fallback = pd.DataFrame(
            {
                msg('aoi.legend.color'): ["gray"],
                msg('aoi.legend.desc'): ["No mountain"],
                msg('aoi.legend.area'): ["0"],
                msg('aoi.legend.perc'): ["0"],
            }
        )

        # Return the same tuple format, but with fallback values
        return json.loads(df_fallback.to_json(orient="index")), df_fallback

    return json.loads(df.to_json(orient="index")), df
