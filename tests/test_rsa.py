import pytest
import ee

from component.model import MgciModel
from component.scripts.surface_area import get_real_surface_area


@pytest.fixture
def aoi():
    return ee.FeatureCollection("users/dfgm2006/FAO/MGCI/AOI_RSA").geometry()


@pytest.fixture
def dem():
    return ee.Image("CGIAR/SRTM90_V4")


@pytest.fixture
def mgci_model(dem):

    # Arrange

    # Create a fake aoi_model with a test AOI
    class AoiModel:
        pass

    aoi_model = AoiModel()

    aoi_model.feature_collection = ee.FeatureCollection(
        "users/dfgm2006/FAO/MGCI/AOI_RSA"
    )

    # Create the mgci model with known input parameters
    model = MgciModel(aoi_model)
    model.dem = dem
    model.kapos_image = ee.Image("users/dfgm2006/FAO/MGCI/kapos_1_6")
    model.vegetation_image = ee.Image(
        ee.Image(
            "users/geflanddegradation/toolbox_datasets/lcov_esacc_1992_2018"
        ).select("y2018")
    )

    return model


def test_rsa_values(aoi, dem):
    """Test real surface area values. It will use a random dataset of 10 points
    and will assert that the given values are the same as the expected by using
    the workflow proposed to calculate Real Surface Area, Jenness(2004)
    https://www.fs.fed.us/rm/pubs_other/rmrs_2004_jenness_j001.pdf

    """

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

    rsa = get_real_surface_area(dem, aoi)
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


def test_planimetric_reduce(mgci_model):
    """
    Test to verify that the planimetric area that is calculated in the model
    is the same as the expected area.

    """
    # Arrange

    mgci_model.rsa = False

    # Define the expected result
    kapos_class_area = {
        2: 44.33550363758039,
        3: 296.75708955092773,
        4: 198.07427361031571,
        5: 2.7006134453431354,
    }

    # Act

    # Reduce regions
    mgci_model.reduce_to_regions("sqkm")

    model_result = {
        k: v
        for k, v in mgci_model.summary_df["krange_area"].to_dict().items()
        if v != 0
    }

    # Assert

    # The model has to return the same area as the  expected result
    assert kapos_class_area == model_result


def test_rsa_reduce(mgci_model):
    """
    Test to verify that the real surface area that is calculated in the model
    is the same as the expected area.
    """
    # Arrange

    mgci_model.rsa = True

    # Define the expected result
    kapos_class_area = {
        2: 48.03719012708352,
        3: 320.0903554828036,
        4: 213.6195623073718,
        5: 2.829834635697798,
    }

    # Act

    # Reduce regions
    mgci_model.reduce_to_regions("sqkm")

    model_result = {
        k: v
        for k, v in mgci_model.summary_df["krange_area"].to_dict().items()
        if v != 0
    }

    # Assert

    # The model has to return the same area as the  expected result
    assert kapos_class_area == model_result
