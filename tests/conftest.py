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
def test_biobelt() -> ee.Image:
    return ee.Image("users/xavidelamo/SDG1542_Mntn_BioclimaticBelts")


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
