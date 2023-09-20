import pytest
import pandas as pd

from sepal_ui.aoi.aoi_model import AoiModel
from component.model.model import MgciModel
from component.tile.vegetation_tile import VegetationTile
import component.parameter.directory as dir_
import component.parameter.module_parameter as param


@pytest.fixture
def mgci_model():
    aoi_model = AoiModel(admin="959")
    return MgciModel(aoi_model)


@pytest.fixture
def default_target_classes():
    dst_class_file = dir_.LOCAL_LC_CLASSES
    return {
        row.lc_class: (row.desc, row.color)
        for _, row in pd.read_csv(dst_class_file).iterrows()
    }


def test_default(mgci_model):
    """Test that links between view and model are correct"""

    vegetation_tile = VegetationTile(mgci_model)

    default_asset = "users/amitghosh/sdg_module/esa/cci_landcover"

    # The default values of the model should be the default asset

    assert (
        vegetation_tile.vegetation_view.reclassify_tile_a.w_reclass.w_ic_select.v_model
        == "users/amitghosh/sdg_module/esa/cci_landcover"
    )
    assert (
        vegetation_tile.vegetation_view.reclassify_tile_b.w_reclass.w_ic_select.v_model
        == "users/amitghosh/sdg_module/esa/cci_landcover"
    )

    # Check Mgci Model contains both assets

    assert mgci_model.lc_asset_sub_a == default_asset
    assert mgci_model.lc_asset_sub_b == default_asset


def test_on_change(mgci_model):
    """Test that links will change when the user changes values from view"""

    vegetation_tile = VegetationTile(mgci_model)

    # Change the asset on reclassify_A
    new_asset = "projects/planet-afk/assets/afk_treecount"

    vegetation_tile.vegetation_view.reclassify_tile_a.w_reclass.w_ic_select.v_model = (
        new_asset
    )

    assert (
        vegetation_tile.vegetation_view.reclassify_tile_a.w_reclass.w_ic_select.v_model
        == new_asset
    )
    assert (
        vegetation_tile.vegetation_view.reclassify_tile_b.w_reclass.w_ic_select.v_model
        == new_asset
    )

    # Check Mgci Model contains both assets

    assert mgci_model.lc_asset_sub_a == new_asset
    assert mgci_model.lc_asset_sub_b == new_asset


def test_default_matrix(mgci_model, default_target_classes):
    """Test default values from mapping land cover matrix"""

    vegetation_tile = VegetationTile(mgci_model)

    default_map_matrix = dict(
        list(
            zip(
                *list(
                    pd.read_csv(param.LC_MAP_MATRIX)[["from_code", "target_code"]]
                    .to_dict("list")
                    .values()
                )
            )
        )
    )

    # Vegetation tile has to start with the default land cover mapping matrices in both models

    assert mgci_model.matrix_sub_a == default_map_matrix
    assert mgci_model.matrix_sub_b == default_map_matrix

    # If user wants to use a custom land cover, the default matrices have to be empty
    vegetation_tile.vegetation_view.w_questionnaire.ans_custom_lulc = True

    assert mgci_model.matrix_sub_a == {}
    assert mgci_model.matrix_sub_b == {}


def test_target_classes(mgci_model, default_target_classes):
    vegetation_tile = VegetationTile(mgci_model)

    # Check the target classes are the default ones
    assert mgci_model.lulc_classes_sub_a == default_target_classes
    assert mgci_model.lulc_classes_sub_b == default_target_classes

    # Now we have to test that if we change the dst_class_file from reclassify_model, using the
    # import_target_matrix dialog, the parameter lulc_classes will be updated as well

    # Create a custom classification file using csv and save it
    custom_target_classes = {
        1: ("Artificial surfaces", "#515151"),
        2: ("Croplands", "#F18701"),
        3: ("Grassland", "#92B4A7"),
    }
    path_to_file = dir_.CLASS_DIR / "test_custom_target.csv"
    df = pd.DataFrame.from_dict(custom_target_classes).T
    df.reset_index(inplace=True)
    df.columns = ["lc_class", "desc", "color"]
    df.to_csv(path_to_file, index=False)

    # Select the custom classification file from the import_target_matrix dialog
    vegetation_tile.vegetation_view.reclassify_tile_b.w_reclass.target_dialog.w_dst_class_file.select_file(
        path_to_file
    )

    # use the validation method to update the target classes in the model
    vegetation_tile.vegetation_view.reclassify_tile_b.w_reclass.target_dialog.action_btn.fire_event(
        "click", {}
    )

    assert mgci_model.lulc_classes_sub_b == custom_target_classes

    # TODO: Now we have to test if we use the default ones again, the parameter lulc_classes will default
    # OR NOT? I'm not sure if it worth it to do
