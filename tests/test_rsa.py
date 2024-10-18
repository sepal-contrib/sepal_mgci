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
        9026.699751147127,
        10184.337086968659,
        9412.543831521269,
        12644.78916494911,
        9461.432453993664,
        8928.90164645962,
        9616.467382050774,
        9582.613353337636,
        9082.907170284572,
        10097.300124120764,
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
