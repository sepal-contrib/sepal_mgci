from sepal_ui.scripts.utils import init_ee
import ee
import pytest

from component.model.model import MgciModel
from sepal_ui.aoi.aoi_model import AoiModel
import component.parameter.directory as dir_
import pandas as pd

init_ee()


@pytest.fixture()
def test_aoi() -> ee.FeatureCollection:
    """returns aoi"""

    return ee.FeatureCollection("projects/ee-cheprotich22/assets/Argentina_Bounds")


@pytest.fixture()
def test_land_cover() -> ee.ImageCollection:
    """returns land cover collection"""

    return ee.ImageCollection("projects/ee-cheprotich22/assets/Argentina_Landcover")


@pytest.fixture
def mgci_model() -> MgciModel:
    aoi_model = AoiModel(admin="959")
    return MgciModel(aoi_model)


@pytest.fixture
def default_target_classes() -> dict:
    dst_class_file = dir_.LOCAL_LC_CLASSES
    return {
        row.lc_class: (row.desc, row.color)
        for _, row in pd.read_csv(dst_class_file).iterrows()
    }


def argentina_model() -> MgciModel:

    aoi_model = AoiModel(asset="projects/ee-cheprotich22/assets/Argentina_Bounds")

    mgci_model = MgciModel(aoi_model)

    return mgci_model
