from typing import Optional

import pandas as pd

import component.parameter.module_parameter as param
import component.scripts as cs

# isort: off
from component.parameter.index_parameters import sub_a_cols, sub_a_landtype_cols

from component.scripts.report_scripts import (
    fill_parsed_df,
    get_belt_desc,
    get_lc_desc,
    LC_MAP_MATRIX,
)


def get_mgci_landtype(parsed_df):
    """Takes in a parsed DataFrame as an input and returns a concatenated
    DataFrame that includes the calculation of belt area and group them by
    land cover class (lc_class) and belt_class.

    Table2_1542a_LandCoverType
    """

    df = fill_parsed_df(parsed_df.copy())

    # Add is_green column to the dataframe based on lc_class.
    df["is_green"] = df.apply(
        lambda row: LC_MAP_MATRIX.loc[LC_MAP_MATRIX.target_code == row["lc_class"]][
            "green"
        ].iloc[0],
        axis=1,
    )

    # Get area of "green" classes and group them by belt_class
    green_cover = (
        df[df.is_green == 1]
        .groupby(["belt_class"])
        .sum()
        .reset_index()[["belt_class", "sum"]]
    )

    # Add total area of green cover for all belt_classes
    total_green = pd.DataFrame(columns=["belt_class", "sum"])
    total_green.loc[0] = ["Total", green_cover["sum"].sum()]

    green_cover = pd.concat([green_cover, total_green])

    # Add lc_class
    green_cover["lc_class"] = "Green Cover"

    # with latest changes, we don't need to calculate belt area

    # Calculate belt area
    # belt_area_df = df.groupby(["belt_class"]).sum().reset_index()[["belt_class", "sum"]]
    # belt_area_df["lc_class"] = "All"

    # land_type_df = pd.concat([df, belt_area_df])

    by_lc_df = df.groupby(["lc_class"]).sum().reset_index()[["lc_class", "sum"]]
    by_lc_df["belt_class"] = "Total"

    return pd.concat([df, by_lc_df, green_cover])


def get_mgci(parsed_df: pd.DataFrame) -> pd.DataFrame:
    """
    This function takes a dataframe as input and calculates the MGCI (Mountain Green
    Cover Index) for each belt class. It groups the data by "belt_class" and "is_green",
    adds a column "is_green" to the dataframe based on the lc_map_matrix, calculates the
    green and non-green areas, and calculates the mgci value. The function then returns
    a new dataframe with the belts and their respective mgci values.

    Table3_1542a_MGCI
    """

    df = fill_parsed_df(parsed_df.copy())

    # Adds is_green column to the dataframe based on lc_class.
    df["is_green"] = df.apply(
        lambda row: LC_MAP_MATRIX.loc[LC_MAP_MATRIX.target_code == row["lc_class"]][
            "green"
        ].iloc[0],
        axis=1,
    )

    # Get the green and non green total area for each belt
    tmp_df = df.groupby(["belt_class", "is_green"], as_index=False).sum()

    # Split by green and non-green
    green_df = tmp_df[tmp_df.is_green == 1]
    non_green_df = tmp_df[tmp_df.is_green == 0]

    # Merge and calculate mgci
    green_non_green = pd.merge(
        green_df,
        non_green_df,
        on=["belt_class"],
        suffixes=["green", "non_green"],
        how="outer",
    )
    green_non_green = green_non_green.fillna(0)

    green_non_green["mgci"] = (
        green_non_green["sumgreen"]
        / (green_non_green["sumgreen"] + green_non_green["sumnon_green"])
        * 100
    )
    green_non_green = green_non_green[
        ["belt_class", "sumgreen", "sumnon_green", "mgci"]
    ]

    # Return a dataframe with all the columns
    total_mgci = pd.DataFrame(
        [
            [
                "Total",
                green_non_green.sum()["sumgreen"]
                / (
                    green_non_green.sum()["sumgreen"]
                    + green_non_green.sum()["sumnon_green"]
                )
                * 100,
            ]
        ],
        columns=["belt_class", "mgci"],
    ).fillna(0)

    return pd.concat([green_non_green, total_mgci])


def get_report(
    parsed_df: pd.DataFrame, year: int, model, land_type: Optional[bool] = False
) -> pd.DataFrame:
    """
    This function takes in a parsed DataFrame, a year, and an optional land_type
    parameter.
    Based on the land_type parameter, it either generates a report on mountain
    green cover index (MGCI) or MGCI by land cover class and belt class.

    The function then adds several additional columns to the resulting DataFrame
    such as 'Value', 'Units', 'SeriesID', 'SeriesDescription', 'GeoAreaName',
    'GeoAreaCode', 'TimePeriod', 'Time_Detail', 'Source', 'FootNote', 'Nature',
    'Reporting Type', 'Observation Status', 'Bioclimatic Belt', 'ISOalpha3',
    'Type', and 'SeriesCode'.
    """

    if land_type:
        # Table2_1542a_LandCoverType
        report_df = get_mgci_landtype(parsed_df)
        report_df["OBS_VALUE"] = report_df["sum"]
        report_df["OBS_VALUE_RSA"] = "TBD"  # TODO: check if we can report RSA
        report_df["UNIT_MEASURE"] = "KM2"
        report_df["UNIT_MULT"] = "TBD"
        report_df["LAND_COVER"] = report_df.apply(get_lc_desc, axis=1)
        output_cols = sub_a_landtype_cols
    else:
        # Table3_1542a_MGCI
        report_df = get_mgci(parsed_df)
        report_df["OBS_VALUE"] = report_df.mgci
        report_df["OBS_VALUE_RSA"] = "TBD"  # TODO: check if we can report RSA
        report_df["UNIT_MEASURE"] = "PT"
        report_df["UNIT_MULT"] = "TBD"
        output_cols = sub_a_cols

    # The following cols are equal for both tables
    report_df["Indicator"] = "15.4.2"
    report_df["SeriesID"] = "TBD"
    report_df["SERIES"] = "TBD"
    report_df["SeriesDesc"] = "TBD"
    report_df["GeoAreaName"] = cs.get_geoarea(model.aoi_model)[0]
    report_df["REF_AREA"] = cs.get_geoarea(model.aoi_model)[1]
    report_df["TIME_PERIOD"] = year  # TODO: CHANGE THIS
    report_df["TIME_DETAIL"] = year  # TODO: CHANGE THIS
    report_df[
        "SOURCE_DETAIL"
    ] = "Food and Agriculture Organisation of United Nations (FAO)"  # TODO: Capture from user's input
    report_df["COMMENT_OBS"] = "FAO estimate"
    report_df["NATURE"] = ""  # TODO: CREATE cs.get_nature()
    report_df["OBS_STATUS"] = ""  # TODO: CREATE cs.get_obs_status()
    report_df["BIOCLIMATIC_BELT"] = report_df.apply(get_belt_desc, axis=1)

    # fill NaN values with 0
    report_df.fillna(0, inplace=True)

    if land_type:
        assert len(report_df) == 55, "Report should have 55 rows"

    return report_df[output_cols].reset_index(drop=True), year
