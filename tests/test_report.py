import json
from pathlib import Path
import pytest
from sepal_ui.aoi.aoi_model import AoiModel

import component.parameter.module_parameter as param
import component.scripts as cs
import component.scripts.sub_a as sub_a
import component.scripts.sub_b as sub_b
import tests.test_result as test
from component.parameter.index_parameters import (
    sub_a_landtype_cols,
    sub_a_cols,
    sub_b_landtype_cols,
    sub_b_perc_cols,
)

aoi_model = AoiModel(admin="959")
details = {"geo_area_name": "", "ref_area": "", "source_detail": ""}
reporting_years_sub_a = cs.get_sub_a_break_points(test.sub_a_year)
transition_matrix = str(param.TRANSITION_MATRIX_FILE)


@pytest.fixture()
def results() -> dict:
    return json.loads(
        Path("tests/test_output_result/result_antioquia.json").read_text()
    )


@pytest.fixture()
def model(antioquia_default_result):
    class Model:
        data = test.sub_a_year
        reporting_years_sub_a = cs.get_sub_a_break_points(data)
        aoi_model = aoi_model
        transition_matrix = str(param.TRANSITION_MATRIX_FILE)
        source = "Food and Agriculture Organisation of United Nations (FAO)"

    return Model()


def test_parse_to_year_a(results):
    """Test get_result_from_year"""
    result = cs.parse_to_year_a(results, reporting_years_sub_a, 2000)
    assert len(result) == 18


def test_fill_parsed_df(results):
    """Test fill_parsed_df"""

    parsed_df = cs.parse_to_year_a(results, reporting_years_sub_a, 2000)
    filled_df = sub_a.fill_parsed_df(parsed_df)

    # We expect to have 4 cols: belt_class, lc_class, sum, and key
    # and also 40 rows, one for each combination of belt_class and lc_class

    assert filled_df.shape == (40, 4)


def test_get_report_sub_a_landtype(results):

    parsed_df = cs.parse_to_year_a(results, reporting_years_sub_a, 2000)
    report = sub_a.get_report(parsed_df, 2000, **details, land_type=True)

    # We always will expect to have 55 rows to each country report
    # Also, we expect to have 18 columns for each land type

    assert len(sub_a_landtype_cols) == 18
    assert report.shape == (55, len(sub_a_landtype_cols))


def test_get_report_sub_a_mgci(results):

    parsed_df = cs.parse_to_year_a(results, reporting_years_sub_a, 2000)
    report = sub_a.get_report(parsed_df, 2000, **details, land_type=False)

    # We always will expect to have 55 columns to each country report
    # Also, we expect to have 17 columns for each land type
    assert set(report["BIOCLIMATIC_BELT"].unique()) == {
        "Alpine",
        "Montane",
        "Nival",
        "Remaining mountain area",
        "Total",
    }
    assert len(sub_a_cols) == 17
    assert report.shape == (55, len(sub_a_cols))


def test_get_report_pdma_area(results):
    years = {"baseline": [2000, 2015]}
    parsed_df = cs.parse_sub_b_year(results, years)

    report = sub_b.get_report(
        parsed_df, years, transition_matrix=transition_matrix, **details, area=True
    )

    assert len(sub_b_landtype_cols) == 19
    assert report.shape == (5, len(sub_b_landtype_cols))


def test_get_report_pdma_pt(results):
    years = {"baseline": [2000, 2015]}
    parsed_df = cs.parse_sub_b_year(results, years)
    report = sub_b.get_report(
        parsed_df, years, transition_matrix=transition_matrix, **details, area=False
    )
    assert len(sub_b_perc_cols) == 17
    assert report.shape == (5, len(sub_b_perc_cols))
