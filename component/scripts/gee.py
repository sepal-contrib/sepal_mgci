"""Reduce land use/land cover image to bioclimatic belts regions using planimetric or real surface area"""

from typing import Dict, List, Optional, Tuple
import ee
import pandas as pd
from pathlib import Path

from component.scripts.file_handler import read_file
from sepal_ui.scripts.gee_interface import GEEInterface

import component.parameter.module_parameter as param
from component.scripts.surface_area import get_real_surface_area
from component.parameter.module_parameter import transition_degradation_matrix
from component.scripts.gee_parse_reduce_regions import filter_groups, reduceGroups

NO_DATA_VALUE = 0
"""Union[int, None]: No data value for the remap process"""


def no_remap(image: ee.Image, remap_matrix: Optional[dict] = None):
    """return remapped or raw image if there's a matrix"""

    if remap_matrix:
        from_, to_ = list(zip(*remap_matrix.items()))
        return image.remap(from_, to_, NO_DATA_VALUE).selfMask()

    return image


def reduce_by_regions(
    image_area: ee.Image,
    biobelt: ee.Image,
    image: ee.Image,
    aoi: ee.FeatureCollection,
    scale: int,
):
    """Reduce image to bioclimatic belts regions using planimetric or real surface area"""

    # This is the reducer that will be used to calculate the area of each class
    reducer = ee.Reducer.sum().group(1, "lc").group(2, "biobelt")
    group_keys = ["lc", "biobelt"]

    feature_collection = (
        image_area.divide(param.UNITS["sqkm"][0])
        .updateMask(biobelt.mask())
        .addBands(image)
        .addBands(biobelt)
        .reduceRegions(
            **{
                "collection": ee.FeatureCollection(aoi),
                "reducer": reducer,
                "scale": scale,
                "tileScale": 8,
            }
        )
    )

    return reduceGroups(ee.Reducer.sum(), feature_collection, group_keys)


def reduce_by_region(
    image_area: ee.Image,
    biobelt: ee.Image,
    image: ee.Image,
    aoi: ee.FeatureCollection,
    scale: int,
):
    """Reduce image to bioclimatic belts regions using planimetric or real surface area"""

    # This is the reducer that will be used to calculate the area of each class
    reducer = ee.Reducer.sum().group(1, "lc").group(2, "biobelt")

    feature_collection = (
        image_area.divide(param.UNITS["sqkm"][0])
        .updateMask(biobelt.mask())
        .addBands(image)
        .addBands(biobelt)
        .reduceRegion(
            **{
                "reducer": reducer,
                "geometry": ee.FeatureCollection(aoi).geometry(),
                "scale": scale,
                "bestEffort": True,
                "maxPixels": 1e13,
                "tileScale": 8,
            }
        )
    )
    # Remove the empty groups (biobelts without any land cover class)
    # I have to do like this because I want to reuse the filter_groups function
    return (
        ee.FeatureCollection([ee.Feature(None, feature_collection)])
        .map(filter_groups)
        .first()
        .toDictionary()
        .get("groups")
    )


def reduce_regions(
    aoi: ee.FeatureCollection,
    remap_matrix: dict,
    rsa: bool,
    dem: str,
    lc_years: List[Tuple[Dict]],
    transition_matrix: str,
    scale: Optional[int] = None,
) -> ee.Dictionary:
    """Reduce land use/land cover image to bioclimatic belts regions using planimetric
    or real surface area

    Attributes:
        matrix (dict): dictionary with the land cover classes to remap
        indicator (str): either 'sub_a' or 'sub_b'
        aoi (ee.FeatureCollection, ee.Geometry): Region to reduce image
        lc_years (list of strings): list of years (gee asset id) of the land cover
        transition_matrix (pathlike): transition matrix file path
        scale (int): scale of the reduce process

    Return:
        GEE Dicionary process (is not yet executed), with land cover class area
        per land cover (when both dates are input) and biobelts
    """

    aoi = aoi.geometry()

    # extract years from lc_years
    lc_years = [year["asset"] for year in lc_years]

    # Define two ways of calculation, with only one date and with both
    ee_lc_start = ee.Image(lc_years[0]).select(0)

    clip_biobelt = ee.Image(param.BIOBELT)

    if rsa:
        # When using rsa, we need to use the dem scale, otherwise
        # we will end with wrong results.
        image_area = get_real_surface_area(dem, aoi)
        scale = scale or ee_lc_start.projection().nominalScale()
    else:
        # Otherwise, we will use the coarse scale to the output.
        image_area = ee.Image.pixelArea()
        scale = scale or (
            ee_lc_start.projection()
            .nominalScale()
            .max(ee_lc_start.projection().nominalScale())
        )

    if len(lc_years) == 3:
        # We are in subindicator B, so we need to calculate the transition
        ee_end_base = ee.Image(lc_years[1]).select(0)
        ee_report = ee.Image(lc_years[2]).select(0)

        final_degradation = get_transition(
            ee_lc_start, ee_end_base, ee_report, aoi, transition_matrix, remap_matrix
        )

        return (
            ee.Dictionary(
                {
                    "baseline_degradation": reduce_by_regions(
                        image_area,
                        clip_biobelt,
                        final_degradation.select("baseline_degradation"),
                        aoi,
                        scale,
                    )
                }
            )
            .combine(
                {
                    "final_degradation": reduce_by_regions(
                        image_area,
                        clip_biobelt,
                        final_degradation.select("final_degradation"),
                        aoi,
                        scale,
                    )
                }
            )
            .combine(
                {
                    "baseline_transition": reduce_by_regions(
                        image_area,
                        clip_biobelt,
                        final_degradation.select("baseline_transition"),
                        aoi,
                        scale,
                    )
                }
            )
            .combine(
                {
                    "report_transition": reduce_by_regions(
                        image_area,
                        clip_biobelt,
                        final_degradation.select("report_transition"),
                        aoi,
                        scale,
                    )
                }
            )
        )

    reduced_collection = reduce_by_regions(
        image_area, clip_biobelt, no_remap(ee_lc_start, remap_matrix), aoi, scale
    )

    return ee.Dictionary({"sub_a": reduced_collection})


def get_transition(
    ee_start_base: ee.Image,
    ee_end_base: ee.Image,
    ee_report: ee.Image,
    aoi: ee.Geometry,
    transition_matrix: str,
    remap_matrix: Optional[Dict] = None,
):
    """Returns a transition image from two land cover images


    Args:
        ee_start_base (ee.Image): baseline initial land cover image
        ee_end_base (ee.Image): baseline end land cover image
        ee_report (ee.Image): reporting land cover image
        aoi (ee.Geometry): Area of interest
        transition_matrix (str): Path to transition matrix, has to contain from_code, to_code and impact_code columns
        remap_matrix (Optional[Dict], optional): Remap matrix (from_code, to_code). Defaults to None.
    """

    # Remap images
    ee_start_base = no_remap(ee_start_base, remap_matrix).rename("land_cover_start")
    ee_end_base = no_remap(ee_end_base, remap_matrix).rename("land_cover_end")
    ee_report = no_remap(ee_report, remap_matrix).rename("land_cover_report")
    transition_matrix = read_file(transition_matrix)

    # Compute transition between baseline images
    baseline_transition = (
        ee_start_base.multiply(100).add(ee_end_base).rename("baseline_transition")
    )

    # Between the last year of the baseline and the year of the report
    report_transition = (
        ee_end_base.multiply(100).add(ee_report).rename("report_transition")
    )

    # Remap transitions according to the transition matrix
    baseline_degradation = baseline_transition.remap(
        transition_matrix["transition"].tolist(),
        transition_matrix["impact_code"].tolist(),
        NO_DATA_VALUE,
    ).rename("baseline_degradation")

    report_degradation = report_transition.remap(
        transition_matrix["transition"].tolist(),
        transition_matrix["impact_code"].tolist(),
        NO_DATA_VALUE,
    ).rename("report_degradation")

    # Create transition between degradation images
    degraded_transition = (
        baseline_degradation.multiply(100)
        .add(report_degradation)
        .rename("degraded_transition")
    )

    final_degradation = degraded_transition.remap(
        transition_degradation_matrix["transition"].tolist(),
        transition_degradation_matrix["impact_code"].tolist(),
        NO_DATA_VALUE,
    ).rename("final_degradation")

    return (
        baseline_transition.addBands(report_transition)
        .addBands(baseline_degradation)
        .addBands(report_degradation)
        .addBands(degraded_transition)
        .addBands(final_degradation)
        .addBands(ee_start_base)
        .addBands(ee_end_base)
        .addBands(ee_report)
        .clip(aoi)
    )


def read_asset(asset_id: str) -> ee.Image:
    """Converts an asset id to an ee.Image"""
    return ee.Image(asset_id)


def get_gee_recipe_folder(recipe_name: str, gee_interface: GEEInterface) -> Path:
    """Create a folder for the recipe in GEE"""

    recipe_folder = Path("sepal_sdg15.4.2") / recipe_name
    return Path(gee_interface.create_folder(recipe_folder))
