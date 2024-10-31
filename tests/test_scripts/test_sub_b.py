import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(".").resolve()))

from component.scripts import sub_b
from component.types import ResultsDict
import component.scripts as cs
import pytest

antioquia_default_result: ResultsDict = json.loads(
    Path("tests/test_output_result/result_antioquia.json").read_text()
)

report_years = {"report": [2015, 2018]}
baseline_years = {"baseline": [2000, 2015]}


def test_sub_b_report_df_area(default_transition_matrix):

    years = {"report": [2015, 2018]}
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)

    details = {"geo_area_name": "", "ref_area": "", "source_detail": ""}

    report = sub_b.get_report(
        parsed_df,
        years,
        transition_matrix=default_transition_matrix,
        **details,
        area=True,
    )
    assert report.TIME_DETAIL.values.tolist() == [
        "2000-2018",
        "2000-2018",
        "2000-2018",
        "2000-2018",
        "2000-2018",
    ]
    assert report.TIME_PERIOD.values.tolist() == [
        "2018",
        "2018",
        "2018",
        "2018",
        "2018",
    ]
    assert report.UNIT_MEASURE.values.tolist() == ["KM2", "KM2", "KM2", "KM2", "KM2"]
    assert report.BIOCLIMATIC_BELT.values.tolist() == [
        "Nival",
        "Alpine",
        "Montane",
        "Remaining mountain area",
        "Total",
    ]
    assert report.OBS_VALUE.values.tolist() == [
        "NA",
        "NA",
        27.1817,
        1545.648,
        1572.8297,
    ]
    assert report.OBS_VALUE_NET.values.tolist() == [
        "NA",
        "NA",
        22.8422,
        1495.4244,
        1518.2666,
    ]

    # Test with baseline years
    years = {"baseline": [2000, 2015]}
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)

    report = sub_b.get_report(
        parsed_df,
        years,
        transition_matrix=default_transition_matrix,
        **details,
        area=True,
    )
    assert report.TIME_DETAIL.values.tolist() == [
        "2000-2015",
        "2000-2015",
        "2000-2015",
        "2000-2015",
        "2000-2015",
    ]
    assert report.TIME_PERIOD.values.tolist() == [
        "2015",
        "2015",
        "2015",
        "2015",
        "2015",
    ]


def test_sub_b_report_df_percentage(default_transition_matrix):

    years = {"report": [2015, 2018]}
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)
    details = {"geo_area_name": "", "ref_area": "", "source_detail": ""}

    report = sub_b.get_report(
        parsed_df,
        years,
        transition_matrix=default_transition_matrix,
        area=False,
        **details,
    )

    assert report.TIME_DETAIL.values.tolist() == [
        "2000-2018",
        "2000-2018",
        "2000-2018",
        "2000-2018",
        "2000-2018",
    ]
    assert report.TIME_PERIOD.values.tolist() == [
        "2018",
        "2018",
        "2018",
        "2018",
        "2018",
    ]
    assert report.UNIT_MEASURE.values.tolist() == ["PT", "PT", "PT", "PT", "PT"]
    assert report.BIOCLIMATIC_BELT.values.tolist() == [
        "Nival",
        "Alpine",
        "Montane",
        "Remaining mountain area",
        "Total",
    ]
    assert report.OBS_VALUE.values.tolist() == [
        "NA",
        "NA",
        0.723,
        4.1866,
        3.8645,
    ]
    assert report.OBS_VALUE_NET.values.tolist() == [
        "NA",
        "NA",
        0.6076,
        4.0506,
        3.7304,
    ]


def test_get_degraded_area(default_transition_matrix):

    years = report_years
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)
    degraded = sub_b.get_degraded_area(
        parsed_df, transition_matrix=default_transition_matrix
    )

    expected_result = {
        "belt_class": {0: 1, 1: 2, 2: 3, 3: 4},
        "degraded": {0: np.nan, 1: np.nan, 2: 27.1817221796875, 3: 1545.648000734526},
        "stable": {
            0: np.nan,
            1: 21.238068515625017,
            2: 3728.0393291830255,
            3: 35322.996898,
        },
        "improved": {0: np.nan, 1: np.nan, 2: 4.3395719843750005, 3: 50.2235961177696},
        "net_degraded": {
            0: np.nan,
            1: np.nan,
            2: 22.8421501953125,
            3: 1495.4244046167564,
        },
    }

    assert degraded.equals(pd.DataFrame(expected_result))

    # Test with the baseline year
    years = baseline_years
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)
    degraded = sub_b.get_degraded_area(
        parsed_df, transition_matrix=default_transition_matrix
    )

    expected_result = {
        "belt_class": {0: 1, 1: 2, 2: 3, 3: 4},
        "degraded": {0: np.nan, 1: np.nan, 2: 20.665385171875, 3: 1135.925068948468},
        "stable": {
            0: np.nan,
            1: 21.238068515625,
            2: 3648.120780730509,
            3: 34925.06165119144,
        },
        "improved": {0: np.nan, 1: np.nan, 2: 90.77445744469973, 3: 857.8817747122545},
        "net_degraded": {
            0: np.nan,
            1: np.nan,
            2: -70.10907227282473,
            3: 278.04329423621346,
        },
    }

    assert degraded.equals(pd.DataFrame(expected_result))


def get_pdma_area(default_transition_matrix):

    years = report_years
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)

    pdma_area = sub_b.get_pdma_area(parsed_df, default_transition_matrix)

    expected_result = {
        "belt_class": {0: "Total", 1: 2, 2: 3, 3: 4},
        "degraded": {
            0: 1572.8297229142136,
            1: np.nan,
            2: 27.1817221796875,
            3: 1545.648000734526,
        },
        "stable": {
            0: 39072.27429569865,
            1: 21.238068515625017,
            2: 3728.0393291830255,
            3: 35322.996898,
        },
        "improved": {
            0: 54.563168102144594,
            1: np.nan,
            2: 4.3395719843750005,
            3: 50.223596117769596,
        },
        "net_degraded": {
            0: 1518.266554812069,
            1: np.nan,
            2: 22.8421501953125,
            3: 1495.4244046167564,
        },
    }

    pdma_area[pdma_area.belt_class == "Total"].equals(pd.DataFrame(expected_result))

    # Test with the baseline
    years = baseline_years
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)

    pdma_area = sub_b.get_pdma_area(parsed_df, default_transition_matrix)

    # We are just adding a new row with the sum of all the columns

    expected_result = {
        "belt_class": {0: "Total", 1: 2, 2: 3, 3: 4},
        "degraded": {
            0: 1156.5904541203429,
            1: np.nan,
            2: 20.665385171875,
            3: 1135.925068948468,
        },
        "stable": {
            0: 38594.42050043758,
            1: 21.238068515625,
            2: 3648.1207807305086,
            3: 34925.06165119145,
        },
        "improved": {
            0: 948.6562321569543,
            1: np.nan,
            2: 90.77445744469975,
            3: 857.8817747122546,
        },
        "net_degraded": {
            0: 207.9342219633886,
            1: np.nan,
            2: -70.10907227282475,
            3: 278.04329423621334,
        },
    }

    pdma_area[pdma_area.belt_class == "Total"].equals(pd.DataFrame(expected_result))


def test_get_pdma_percentage(default_transition_matrix):

    years = report_years
    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)

    pdma_pt = sub_b.get_pdma_pt(parsed_df, default_transition_matrix)

    expected_result = {
        "index": {0: 0, 1: 1, 2: 2, 3: 3, 4: 0},
        "belt_class": {0: 1, 1: 2, 2: 3, 3: 4, 4: "Total"},
        "degraded": {
            0: np.nan,
            1: np.nan,
            2: 27.1817221796875,
            3: 1545.648000734526,
            4: 1572.8297229142136,
        },
        "stable": {
            0: np.nan,
            1: 21.238068515625017,
            2: 3728.0393291830255,
            3: 35322.996898,
            4: 39072.27429569865,
        },
        "improved": {
            0: np.nan,
            1: np.nan,
            2: 4.3395719843750005,
            3: 50.223596117769596,
            4: 54.563168102144594,
        },
        "net_degraded": {
            0: np.nan,
            1: np.nan,
            2: 22.8421501953125,
            3: 1495.4244046167564,
            4: 1518.266554812069,
        },
        "belt_area": {
            0: 0.0,
            1: 21.238068515625017,
            2: 3759.560623347088,
            3: 36918.86849485229,
            4: 40699.66718671501,
        },
        "pt_degraded": {
            0: np.nan,
            1: np.nan,
            2: 0.7230026299054054,
            3: 4.1866071842099934,
            4: 3.8644780943752024,
        },
        "pt_net_degraded": {
            0: np.nan,
            1: np.nan,
            2: 0.6075749930314045,
            3: 4.050569439378317,
            4: 3.730415160022867,
        },
    }

    pdma_pt.equals(pd.DataFrame(expected_result))

    # And with the baseline
    years = baseline_years

    parsed_df = cs.parse_sub_b_year(antioquia_default_result, years)

    expected_result = {
        "index": {0: 0, 1: 1, 2: 2, 3: 3, 4: 0},
        "belt_class": {0: 1, 1: 2, 2: 3, 3: 4, 4: "Total"},
        "degraded": {
            0: np.nan,
            1: np.nan,
            2: 20.665385171875,
            3: 1135.925068948468,
            4: 1156.5904541203429,
        },
        "stable": {
            0: np.nan,
            1: 21.238068515625,
            2: 3648.1207807305086,
            3: 34925.06165119145,
            4: 38594.42050043758,
        },
        "improved": {
            0: np.nan,
            1: np.nan,
            2: 90.77445744469975,
            3: 857.8817747122546,
            4: 948.6562321569543,
        },
        "net_degraded": {
            0: np.nan,
            1: np.nan,
            2: -70.10907227282475,
            3: 278.04329423621334,
            4: 207.9342219633886,
        },
        "belt_area": {
            0: 0.0,
            1: 21.238068515625,
            2: 3759.5606233470835,
            3: 36918.86849485217,
            4: 40699.667186714876,
        },
        "pt_degraded": {
            0: np.nan,
            1: np.nan,
            2: 0.5496755403687812,
            3: 3.07681441836945,
            4: 2.841768825318246,
        },
        "pt_net_degraded": {
            0: np.nan,
            1: np.nan,
            2: -1.8648209005446927,
            3: 0.7531197611730237,
            4: 0.5108990719984614,
        },
    }

    pdma_pt = sub_b.get_pdma_pt(parsed_df, default_transition_matrix)

    pdma_pt.equals(pd.DataFrame(expected_result))


if __name__ == "__main__":
    # Run pytest with the current file
    pytest.main([__file__, "-s", "-vv"])
