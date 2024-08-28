from sepal_ui.scripts.utils import init_ee
import ee
import pytest

init_ee()


@pytest.fixture()
def test_aoi() -> ee.FeatureCollection:
    """returns aoi"""

    return ee.FeatureCollection("projects/ee-cheprotich22/assets/Argentina_Bounds")


@pytest.fixture()
def test_land_cover() -> ee.ImageCollection:
    """returns land cover collection"""

    return ee.ImageCollection("projects/ee-cheprotich22/assets/Argentina_Landcover")
