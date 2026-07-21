import component.parameter.module_parameter as param


from pysepal.scripts.utils import init_ee
import ee
import pytest

from component.model.model import MgciModel
from component.tile.aoi_tile import AoiView
from pysepal.mapping import SepalMap
from pysepal.scripts.gee_interface import GEEInterface
import pandas as pd

from component.scripts.scripts import map_matrix_to_dict
import pysepal.solara.utils as solara_utils

init_ee()

# Outside a SEPAL session, sepal_ui's get_current_gee_interface() falls back to a
# GEEInterface backed by an eeclient EESession, which needs SEPAL credentials that
# don't exist in a test/CI environment. Seed the fallback with a sessionless
# GEEInterface so internal calls use the local Earth Engine credentials instead.
solara_utils._fallback_gee_interface = GEEInterface()


@pytest.fixture()
def default_remap_matrix_a() -> dict:
    """returns the default remap matrix for subindicator A"""
    return map_matrix_to_dict(param.LC_MAP_MATRIX)


@pytest.fixture()
def default_remap_matrix_b() -> dict:
    """returns the default remap matrix for subindicator B"""
    return map_matrix_to_dict(param.LC_MAP_MATRIX)


@pytest.fixture()
def default_transition_matrix() -> str:
    return str(param.TRANSITION_MATRIX_FILE)


@pytest.fixture()
def default_dem_asset_id() -> str:
    """returns dem asset id"""

    return "USGS/SRTMGL1_003"


@pytest.fixture()
def default_dem_asset(default_dem_asset_id) -> ee.Image:
    """returns dem asset"""

    return ee.Image(default_dem_asset_id)


@pytest.fixture()
def test_aoi() -> ee.FeatureCollection:
    """returns aoi"""

    return ee.FeatureCollection("projects/ee-cheprotich22/assets/aoi_Argentina_Bounds")


@pytest.fixture()
def test_antioquia_aoi() -> ee.FeatureCollection:
    """returns a regional aoi (for quick testing)"""

    fc = ee.FeatureCollection("FAO/GAUL/2015/level1")
    return fc.filter(ee.Filter.eq("ADM1_CODE", 935))


@pytest.fixture()
def test_realsurfacearea_aoi() -> ee.FeatureCollection:
    """returns a an aoi for real surface area calculation"""

    return ee.FeatureCollection("users/dfgm2006/FAO/MGCI/AOI_RSA")


@pytest.fixture()
def test_sub_a_year():
    return {
        1: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2000", "year": 2000}
    }


@pytest.fixture()
def test_sub_b_year():
    return {
        "baseline": {
            "base": {
                "asset": "users/amitghosh/sdg_module/esa/cci_landcover/2000",
                "year": 2000,
            },
            "report": {
                "asset": "users/amitghosh/sdg_module/esa/cci_landcover/2015",
                "year": 2015,
            },
        },
        2: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2018", "year": 2018},
        3: {"asset": "users/amitghosh/sdg_module/esa/cci_landcover/2021", "year": 2021},
    }


@pytest.fixture()
def test_biobelt() -> ee.Image:
    return ee.Image("users/xavidelamo/SDG1542_Mntn_BioclimaticBelts")


@pytest.fixture()
def test_land_cover() -> ee.ImageCollection:
    """returns land cover collection"""

    return ee.ImageCollection("projects/ee-cheprotich22/assets/Argentina_Landcover")


@pytest.fixture()
def test_multipolygon_aoi() -> ee.FeatureCollection:
    """returns aoi"""

    return ee.FeatureCollection(
        [
            ee.Feature(
                ee.Geometry.Polygon(
                    [
                        [
                            [5.262516683862475, 46.39655013792998],
                            [5.262516683862475, 45.63360136660453],
                            [6.580876058862475, 45.63360136660453],
                            [6.580876058862475, 46.39655013792998],
                        ]
                    ],
                    None,
                    False,
                ),
                {"system:index": "0"},
            ),
            ee.Feature(
                ee.Geometry.Polygon(
                    [
                        [
                            [9.569157308862474, 47.74335902540055],
                            [9.569157308862474, 46.99933410813134],
                            [10.931461996362474, 46.99933410813134],
                            [10.931461996362474, 47.74335902540055],
                        ]
                    ],
                    None,
                    False,
                ),
                {"system:index": "1"},
            ),
            ee.Feature(
                ee.Geometry.Polygon(
                    [
                        [
                            [13.084782308862474, 46.6082900232144],
                            [13.084782308862474, 45.87889028991833],
                            [14.315251058862474, 45.87889028991833],
                            [14.315251058862474, 46.6082900232144],
                        ]
                    ],
                    None,
                    False,
                ),
                {"system:index": "2"},
            ),
        ]
    )


@pytest.fixture
def gee_interface() -> GEEInterface:
    # Sessionless: uses the local Earth Engine credentials (asyncio.to_thread on
    # ee.getInfo) rather than the SEPAL eeclient session path.
    return GEEInterface()


@pytest.fixture
def mgci_model() -> MgciModel:
    # MgciModel derives its AoiModel from an AoiView (aoi_view.model), the way
    # solara_app.Page builds it. A sessionless GEEInterface uses the local Earth
    # Engine credentials rather than the SEPAL eeclient path.
    aoi_view = AoiView(map_=SepalMap(gee_interface=GEEInterface()))
    return MgciModel(aoi_view)


@pytest.fixture
def default_target_classes() -> dict:
    return {
        row.lc_class: (row.desc, row.color)
        for _, row in pd.read_csv(param.LC_CLASSES).iterrows()
    }


def argentina_model() -> MgciModel:
    # NOTE: unused helper kept for parity with the other model fixtures.
    aoi_view = AoiView(map_=SepalMap(gee_interface=GEEInterface()))

    return MgciModel(aoi_view)
