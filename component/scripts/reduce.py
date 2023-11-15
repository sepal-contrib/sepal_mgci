"""Reduce land use/land cover image to bioclimatic belts regions using planimetric or real surface area"""

from typing import Dict, List, Optional, Tuple
import ee
import pandas as pd
import component.parameter.module_parameter as param
from component.scripts.surface_area import get_real_surface_area
from component.parameter.module_parameter import TRANSITION_MATRIX
from component.parameter.module_parameter import transition_degradation_matrix

ee.Initialize()


def no_remap(image: ee.Image, remap_matrix: Optional[dict] = None):
    """return remapped or raw image if there's a matrix"""

    if remap_matrix:
        from_, to_ = list(zip(*remap_matrix.items()))
        return image.remap(from_, to_, 0)

    return image


def reduce_regions(
    aoi: ee.FeatureCollection,
    remap_matrix: dict,
    rsa: bool,
    dem: str,
    lc_years: List[Tuple[Dict]],
    transition_matrix: str,
) -> ee.Dictionary:
    """Reduce land use/land cover image to bioclimatic belts regions using planimetric
    or real surface area

    Attributes:
        matrix (dict): dictionary with the land cover classes to remap
        indicator (str): either 'sub_a' or 'sub_b'
        aoi (ee.FeatureCollection, ee.Geometry): Region to reduce image
        lc_years (list of strings): list of years (gee asset id) of the land cover
        transition_matrix (pathlike): transition matrix file path

    Return:
        GEE Dicionary process (is not yet executed), with land cover class area
        per land cover (when both dates are input) and biobelts
    """

    aoi = aoi.geometry()

    # extract years from lc_years
    lc_years = [year["asset"] for year in lc_years]

    # Define two ways of calculation, with only one date and with both
    ee_lc_start = no_remap(ee.Image(lc_years[0]).select(0), remap_matrix)

    clip_biobelt = ee.Image(param.BIOBELT)

    if rsa:
        # When using rsa, we need to use the dem scale, otherwise
        # we will end with wrong results.
        image_area = get_real_surface_area(dem, aoi)
        scale = ee_lc_start.projection().nominalScale().getInfo()
    else:
        # Otherwise, we will use the coarse scale to the output.
        image_area = ee.Image.pixelArea()
        scale = (
            ee_lc_start.projection()
            .nominalScale()
            .max(ee_lc_start.projection().nominalScale())
            .getInfo()
        )

    if len(lc_years) == 3:
        # We are in subindicator B, so we need to calculate the transition
        ee_end_base = ee.Image(lc_years[1]).select(0)
        ee_report = ee.Image(lc_years[2]).select(0)

        final_degradation = get_transition(
            ee_lc_start, ee_end_base, ee_report, aoi, transition_matrix, remap_matrix
        ).select("final_degradation")

        return (
            image_area.divide(param.UNITS["sqkm"][0])
            .updateMask(clip_biobelt.mask())
            .addBands(final_degradation)
            .addBands(clip_biobelt)
            .reduceRegion(
                **{
                    "reducer": ee.Reducer.sum().group(1).group(2),
                    "geometry": aoi,
                    "maxPixels": 1e19,
                    "scale": scale,
                    "bestEffort": True,
                    "tileScale": 4,
                }
            )
        )

    return (
        image_area.divide(param.UNITS["sqkm"][0])
        .updateMask(clip_biobelt.mask())
        .addBands(ee_lc_start)
        .addBands(clip_biobelt)
        .reduceRegion(
            **{
                "reducer": ee.Reducer.sum().group(1).group(2),
                "geometry": aoi,
                "maxPixels": 1e19,
                "scale": scale,
                "bestEffort": True,
                "tileScale": 4,
            }
        )
    )


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
    ee_start_base = no_remap(ee_start_base, remap_matrix).rename("start_base_year")
    ee_end_base = no_remap(ee_end_base, remap_matrix).rename("end_base_year")
    ee_report = no_remap(ee_report, remap_matrix).rename("report_year")
    transition_matrix = pd.read_csv(transition_matrix)

    # Define all possible transitions for the transition matrix
    transition_matrix.loc[:, "transition"] = (
        transition_matrix["from_code"] * 100 + transition_matrix["to_code"]
    )

    # Define all possible transitions for the transition degradation matrix
    transition_degradation_matrix.loc[:, "transition"] = (
        transition_degradation_matrix["from_code"] * 100
        + transition_degradation_matrix["to_code"]
    )

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
        0,
    ).rename("baseline_degradation")

    report_degradation = report_transition.remap(
        transition_matrix["transition"].tolist(),
        transition_matrix["impact_code"].tolist(),
        0,
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
        0,
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
