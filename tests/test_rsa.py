import pytest
import ee

from component.model import MgciModel
from component.scripts.surface_area import get_real_surface_area


def test_rsa_values(test_realsurfacearea_aoi, default_dem_asset_id):
    """Test real surface area values. It will use a random dataset of 10 points
    and will assert that the given values are the same as the expected by using
    the workflow proposed to calculate Real Surface Area, Jenness(2004)
    https://www.fs.fed.us/rm/pubs_other/rmrs_2004_jenness_j001.pdf

    """

    test_dem_id = "CGIAR/SRTM90_V4"

    # Arrange

    fixed_points = ee.FeatureCollection(
        "users/dfgm2006/FAO/MGCI/random_points_to_test_rsa"
    ).toList(10)

    expected_values = [
        8963.217294093089,
        10119.663928409078,
        9354.773351832117,
        12597.586934741064,
        9396.973753435605,
        8868.871154058705,
        9554.478042850124,
        9527.284588883378,
        9023.03040048494,
        10026.499187631303,
    ]

    # Act

    rsa = get_real_surface_area(test_dem_id, test_realsurfacearea_aoi)
    cellsize = rsa.projection().nominalScale().getInfo()

    def extract_values(point):
        """Extracts values from raster using a point"""
        feature = ee.Feature(point).geometry()
        return ee.Number(
            rsa.reduceRegion(ee.Reducer.first(), feature, cellsize).get("sum")
        )

    process_values = fixed_points.map(extract_values).getInfo()

    # Assert

    assert process_values == expected_values


# 0.1 deg boxes over flat ground at four latitudes
FLAT_SITES = {
    "amazon": [-64.10, -2.05, -64.00, -1.95],
    "sahara": [25.00, 24.95, 25.10, 25.05],
    "great_plains": [-100.10, 39.95, -100.00, 40.05],
    "melipilla": [-71.30, -33.75, -71.20, -33.65],
}

REDUCE_ARGS = dict(bestEffort=True, maxPixels=int(1e13), tileScale=8)


@pytest.mark.parametrize("box", FLAT_SITES.values(), ids=list(FLAT_SITES))
def test_rsa_equals_planimetric_on_flat_terrain(box):
    """A flat DEM has no surface excess, so the real surface area must equal the
    planimetric pixel area at any latitude. Assuming a square DEM cell inflated it
    by ~1/cos(lat), i.e. 28% at 40 degrees."""

    dem = ee.Image("CGIAR/SRTM90_V4")
    flat_dem = dem.multiply(0)
    scale = dem.projection().nominalScale()

    # clip wider than the reduced box so cells on the clip edge stay out of the ratio
    inner = ee.Geometry.Rectangle(box)
    outer = inner.buffer(1000, 1)
    reduce = dict(reducer=ee.Reducer.sum(), geometry=inner, scale=scale, **REDUCE_ARGS)

    rsa = get_real_surface_area(flat_dem, outer).reduceRegion(**reduce).get("sum")
    planimetric = ee.Image.pixelArea().reduceRegion(**reduce).get("area")

    assert ee.Number(rsa).divide(planimetric).getInfo() == pytest.approx(1, abs=5e-3)


def test_rsa_edge_cells_are_complete():
    """Cells on the clip boundary must read their neighbours from outside the AOI,
    otherwise every edge cell sums a partial set of triangles (-1.7% on a 0.1 deg box).
    """

    dem = ee.Image("CGIAR/SRTM90_V4")
    flat_dem = dem.multiply(0)
    scale = dem.projection().nominalScale()

    box = ee.Geometry.Rectangle(FLAT_SITES["melipilla"])
    reduce = dict(reducer=ee.Reducer.sum(), geometry=box, scale=scale, **REDUCE_ARGS)

    rsa = get_real_surface_area(flat_dem, box).reduceRegion(**reduce).get("sum")
    planimetric = ee.Image.pixelArea().reduceRegion(**reduce).get("area")

    assert ee.Number(rsa).divide(planimetric).getInfo() == pytest.approx(1, abs=1e-3)
