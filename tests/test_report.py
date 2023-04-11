from sepal_ui.aoi.aoi_model import AoiModel

import component.parameter.module_parameter as param
import component.scripts as cs
import component.scripts.sub_a as sub_a
import component.scripts.sub_b as sub_b
import tests.test_result as test
from component.parameter.index_parameters import sub_a_landtype_cols

aoi_model = AoiModel(admin="959")


class Model:
    results = test.results
    same_asset_matrix = True
    data = test.sub_a_year
    reporting_years_sub_a = cs.get_sub_a_break_points(data)
    aoi_model = aoi_model
    transition_matrix = str(param.TRANSITION_MATRIX_FILE)
    source = "Food and Agriculture Organisation of United Nations (FAO)"


model = Model()


def test_get_result_from_year():
    """Test get_result_from_year"""
    result = cs.get_result_from_year(model, 2015, "sub_a")
    assert len(result) == 17


def test_fill_parsed_df():
    """Test fill_parsed_df"""

    parsed_df = cs.get_result_from_year(model, 2015, "sub_a")
    filled_df = sub_a.fill_parsed_df(parsed_df)

    # We expect to have 4 cols: belt_class, lc_class, sum, and key
    # and also 40 rows, one for each combination of belt_class and lc_class

    assert filled_df.shape == (40, 4)


def test_get_report_sub_a_landtype():
    parsed_df = cs.get_result_from_year(model, 2015, "sub_a")

    report = sub_a.get_report(parsed_df, 2008, model=model, land_type=True)[0]

    # We always will expect to have 55 columns to each country report
    # Also, we expect to have 18 columns for each land type

    assert len(sub_a_landtype_cols) == 18
    assert report.shape == (55, 18)


def test_get_report_sub_a_mgci():
    parsed_df = cs.get_result_from_year(model, 2015, "sub_a")

    report = sub_a.get_report(parsed_df, 2008, model=model, land_type=False)[0]

    # We always will expect to have 55 columns to each country report
    # Also, we expect to have 17 columns for each land type
    assert report["BIOCLIMATIC_BELT"].unique() == [
        "Alpine",
        "Montane",
        "Nival",
        "Remaining mountain area",
        "Total",
    ]
    assert len(sub_a_landtype_cols) == 17
    assert report.shape == (55, 17)


def test_get_report_pdma_area():
    years = "2004_2011"
    parsed_df = cs.get_result_from_year(model, years, "sub_b")
    report = sub_b.get_report(parsed_df, years, model=model, area=True)[0]

    assert report.shape == (5, 17)


def test_get_report_pdma_pt():
    years = "2004_2011"
    parsed_df = cs.get_result_from_year(model, years, "sub_b")
    report = sub_b.get_report(parsed_df, years, model=model, area=False)[0]

    assert report.shape == (5, 19)
