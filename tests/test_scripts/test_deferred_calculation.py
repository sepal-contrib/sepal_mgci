import asyncio
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
    gee_interface,
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
        "gee_interface": gee_interface,
        "aoi": test_antioquia_aoi,
        "rsa": False,
        "dem": default_dem_asset_id,
        "remap_matrix_a": default_remap_matrix_a,
        "remap_matrix_b": default_remap_matrix_b,
        "transition_matrix": default_transition_matrix,
        "years": years,
        "logger": None,
        "background": False,
        "scale": None,
    }

    result = asyncio.run(perform_calculation(**calculation_parms))

    assert isinstance(result, dict)
    assert compare_nested_dicts(result, antioquia_default_result)


def test_perform_calculation_on_the_background(
    gee_interface,
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
        "gee_interface": gee_interface,
        "aoi": test_antioquia_aoi,
        "rsa": False,
        "dem": default_dem_asset_id,
        "remap_matrix_a": default_remap_matrix_a,
        "remap_matrix_b": default_remap_matrix_b,
        "transition_matrix": default_transition_matrix,
        "years": years,
        "logger": None,
        "background": True,
        "scale": None,
    }

    result = asyncio.run(perform_calculation(**calculation_parms))
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
        assert ee.featurecollection.FeatureCollection == ee.FeatureCollection
        assert isinstance(result, ee.FeatureCollection)
        assert "Computation timed out." in str(e)
        assert result is None


SUB_A_2015 = [{"asset": "lc/2015", "year": 2015}]
SUB_A_2020 = [{"asset": "lc/2020", "year": 2020}]
SUB_B_2000_2021 = [
    {"asset": "lc/2000", "year": 2000},
    {"asset": "lc/2015", "year": 2015},
    {"asset": "lc/2021", "year": 2021},
]


@pytest.mark.parametrize("mode", ["on_the_fly", "background", "timeout_fallback"])
@pytest.mark.parametrize(
    "years",
    [
        [SUB_A_2015, SUB_A_2020, SUB_B_2000_2021],
        [SUB_A_2015, SUB_A_2020],
        [SUB_B_2000_2021],
    ],
    ids=["both", "sub_a_only", "single_sub_b_period"],
)
def test_each_sub_indicator_uses_its_own_remap_matrix(monkeypatch, mode, years):
    """Sub-indicator A years use matrix A and B periods use matrix B."""
    import component.scripts.deferred_calculation as deferred_calculation

    used = {}

    def fake_reduce(aoi, matrix, rsa, dem, year, transition_matrix, scale):
        used[cs.years_from_dict(year)] = matrix
        return ee.Dictionary({})

    class FakeGee:
        async def get_info_async(self, process, tag=None):
            if mode == "timeout_fallback":
                raise Exception("Computation timed out.")
            return {}

    monkeypatch.setattr(deferred_calculation, "reduce_regions", fake_reduce)
    matrix_a, matrix_b = {1: 1}, {1: 2}

    asyncio.run(
        perform_calculation(
            gee_interface=FakeGee(),
            aoi="aoi",
            rsa=False,
            dem="dem",
            remap_matrix_a=matrix_a,
            remap_matrix_b=matrix_b,
            transition_matrix="matrix",
            years=years,
            background=mode == "background",
        )
    )

    expected = {
        cs.years_from_dict(year): matrix_a if len(year) == 1 else matrix_b
        for year in years
    }
    assert used == expected


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s", "-vv"])
