"""Reduce land use/land cover image to bioclimatic belts regions using planimetric or real surface area"""

from typing import Literal, Optional, Union
import ee
import component.parameter.module_parameter as param
from component.scripts.surface_area import get_real_surface_area

ee.Initialize()


def reduce_regions(
    aoi: ee.FeatureCollection,
    matrix: dict,
    rsa: bool,
    dem: str,
    indicator: Literal["sub_a", "sub_b"],
    lc_start: str,
    lc_end=Union[str, None],
) -> ee.Dictionary:
    """Reduce land use/land cover image to bioclimatic belts regions using planimetric
    or real surface area

    Attributes:
        indicator (str): either 'sub_a' or 'sub_b'
        lc_start (string): first year (asset id) of the report or baseline.
        lc_end (string): last year (asset id) of the report.
        aoi (ee.FeatureCollection, ee.Geometry): Region to reduce image

    Return:
        GEE Dicionary process (is not yet executed), with land cover class area
        per land cover (when both dates are input) and biobelts
    """

    def no_remap(image):
        """return remapped or raw image if there's a matrix"""

        if matrix:
            from_, to_ = list(zip(*matrix.items()))
            return image.remap(from_, to_, 0)

        return image

    # Define two ways of calculation, with only one date and with both
    ee_lc_start_band = ee.Image(lc_start).bandNames().get(0)
    ee_lc_start = ee.Image(lc_start).select([ee_lc_start_band])
    ee_lc_start = no_remap(ee_lc_start)

    aoi = aoi.geometry()
    clip_biobelt = ee.Image(param.BIOBELT).clip(aoi)

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

    if indicator == "sub_b":
        ee_lc_end_band = ee.Image(lc_end).bandNames().get(0)
        ee_lc_end = ee.Image(lc_end).select([ee_lc_end_band])
        ee_lc_end = no_remap(ee_lc_end)

        return (
            image_area.divide(param.UNITS["sqkm"][0])
            .updateMask(clip_biobelt.mask())
            .addBands(ee_lc_end)
            .addBands(ee_lc_start)
            .addBands(clip_biobelt)
            .reduceRegion(
                **{
                    "reducer": ee.Reducer.sum().group(1).group(2).group(3),
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
