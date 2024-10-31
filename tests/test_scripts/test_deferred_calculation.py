import json
from pathlib import Path
import ee
import pytest
from component.scripts.deferred_calculation import task_process, perform_calculation
import component.scripts as cs
from tests.utils import compare_nested_dicts
from component.types import ResultsDict


@pytest.fixture()
def years(test_sub_a_year, test_sub_b_year) -> list:
    which = "both"

    sub_a_years = cs.get_a_years(test_sub_a_year)
    sub_b_years = cs.get_b_years(test_sub_b_year)

    # Define a dictionary to map 'which' values to 'years' values
    which_to_years = {
        "both": sub_a_years + sub_b_years,
        "sub_a": sub_a_years,
        "sub_b": sub_b_years,
    }

    # Get the 'years' value for the given 'which' value
    return which_to_years.get(which)


def test_perform_calculation_on_the_fly(
    test_antioquia_aoi,
    years,
    default_dem_asset_id,
    default_remap_matrix_a,
    default_remap_matrix_b,
    default_transition_matrix,
) -> None:

    antioquia_default_result: ResultsDict = json.loads(
        Path("tests/test_output_result/result_antioquia.json").read_text()
    )

    calculation_parms = {
        "aoi": test_antioquia_aoi,
        "rsa": False,
        "dem": default_dem_asset_id,
        "remap_matrix_a": default_remap_matrix_a,
        "remap_matrix_b": default_remap_matrix_b,
        "transition_matrix": default_transition_matrix,
        "years": years,
        "logger": None,
        "background": False,
        "scale": 1000,
    }

    result = perform_calculation(**calculation_parms)

    assert isinstance(result, dict)
    assert compare_nested_dicts(result, antioquia_default_result)


def test_perform_calculation_on_the_background(
    test_antioquia_aoi,
    years,
    default_dem_asset_id,
    default_remap_matrix_a,
    default_remap_matrix_b,
    default_transition_matrix,
) -> None:
    antioquia_default_result: ResultsDict = json.loads(
        Path("tests/test_output_result/result_antioquia_on_background.json").read_text()
    )
    calculation_parms = {
        "aoi": test_antioquia_aoi,
        "rsa": False,
        "dem": default_dem_asset_id,
        "remap_matrix_a": default_remap_matrix_a,
        "remap_matrix_b": default_remap_matrix_b,
        "transition_matrix": default_transition_matrix,
        "years": years,
        "logger": None,
        "background": True,
        "scale": 1000,
    }

    result = perform_calculation(**calculation_parms)
    assert isinstance(result, ee.featurecollection.FeatureCollection)

    result = result.getInfo()
    assert compare_nested_dicts(result, antioquia_default_result)


def test_perform_calculation_timed_out(
    test_antioquia_aoi,
    years,
    default_dem_asset_id,
    default_remap_matrix_a,
    default_remap_matrix_b,
    default_transition_matrix,
) -> None:

    calculation_parms = {
        "aoi": test_antioquia_aoi,
        "rsa": False,
        "dem": default_dem_asset_id,
        "remap_matrix_a": default_remap_matrix_a,
        "remap_matrix_b": default_remap_matrix_b,
        "transition_matrix": default_transition_matrix,
        "years": years,
        "logger": None,
        "background": True,
        "scale": 1000,
        "test_time_out": True,
    }

    with pytest.raises(Exception) as e:

        result = perform_calculation(**calculation_parms)
        assert "Computation timed out." in str(e)
        assert result is None


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s", "-vv"])
