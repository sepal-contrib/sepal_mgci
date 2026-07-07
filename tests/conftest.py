import component.parameter.module_parameter as param


from sepal_ui.scripts.utils import init_ee
import ee
import pytest

from component.model.model import MgciModel
from sepal_ui.aoi.aoi_model import AoiModel
import component.parameter.directory as dir_
import pandas as pd

from component.scripts.scripts import map_matrix_to_dict


def _bridge_eeclient_credentials() -> None:
    """Derive eeclient's ``sepal_credentials`` from the active EE credentials.

    Widgets authenticate GEE through eeclient (``get_current_gee_interface``),
    whose file mode expects a SEPAL-format ``GoogleTokens`` file. That is a
    different filename and schema from the legacy ``credentials`` file that
    ``EARTHENGINE_TOKEN`` / ``init_ee()`` produces, so widget-constructing tests
    fail to authenticate in CI. Mint an access token from the same credentials
    and write it where eeclient looks, so one ``EARTHENGINE_TOKEN`` serves both.
    """
    import json
    import os
    import time
    import warnings
    from pathlib import Path

    from google.auth.transport.requests import Request

    ee_dir = Path.home() / ".config" / "earthengine"
    legacy = ee_dir / "credentials"
    # eeclient selects the filename by home dir name (SepalCredentialMixin).
    target = ee_dir / (
        "credentials" if "sepal-user" in Path.home().name else "sepal_credentials"
    )
    # Never clobber the legacy credentials file (sepal-user env manages its own).
    if target == legacy:
        return

    try:
        # Raw EE credentials: EARTHENGINE_TOKEN (CI may not leave a file on disk if
        # EE was initialized before init_ee ran) or the legacy credentials file.
        raw = os.environ.get("EARTHENGINE_TOKEN") or (
            legacy.read_text() if legacy.exists() else ""
        )
        data = json.loads(raw) if raw else {}
        project = data.get("project") or data.get("project_id")
        if not project:
            warnings.warn("eeclient credential bridge skipped: no project id found")
            return

        # Mint a fresh access token. Service-account tokens have no OAuth refresh
        # token, so get_persistent_credentials() can't refresh them — build the
        # credentials from the key directly. Personal OAuth uses the persistent file.
        if data.get("type") == "service_account":
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_info(
                data,
                scopes=[
                    "https://www.googleapis.com/auth/earthengine",
                    "https://www.googleapis.com/auth/cloud-platform",
                ],
            )
        else:
            creds = ee.data.get_persistent_credentials()
        creds.refresh(Request())

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "accessToken": creds.token,
                    # ms; file mode can't self-refresh, so keep it comfortably ahead
                    "accessTokenExpiryDate": int((time.time() + 3300) * 1000),
                    "projectId": project,
                }
            )
        )
    except Exception as e:  # pragma: no cover - best effort, don't break collection
        warnings.warn(f"eeclient credential bridge failed: {type(e).__name__}: {e}")


init_ee()
_bridge_eeclient_credentials()


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

    return ee.ImageCollection("projects/ee-cheprotich22/assets/aoi_Argentina_Landcover")


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
def mgci_model() -> MgciModel:
    # MgciModel takes an AoiView and reads aoi_view.model, matching solara_app.py.
    # (AoiModel has no .model attribute.)
    from sepal_ui import mapping as sm

    from component.tile.aoi_tile import AoiView

    aoi_view = AoiView(map_=sm.SepalMap())
    return MgciModel(aoi_view)


@pytest.fixture
def default_target_classes() -> dict:
    # Default LC classes; directory.py copies this to class_dir as the local default.
    dst_class_file = param.LC_CLASSES
    return {
        row.lc_class: (row.desc, row.color)
        for _, row in pd.read_csv(dst_class_file).iterrows()
    }


def argentina_model() -> MgciModel:

    aoi_model = AoiModel(asset="projects/ee-cheprotich22/assets/aoi_Argentina_Bounds")

    mgci_model = MgciModel(aoi_model)

    return mgci_model
