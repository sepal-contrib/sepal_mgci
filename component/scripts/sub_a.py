from typing import Optional

import pandas as pd

import component.parameter.module_parameter as param
import component.scripts as cs

# isort: off
from component.parameter.index_parameters import sub_a_cols, sub_a_landtype_cols

lc_map_matrix = pd.read_csv(param.LC_MAP_MATRIX)
belt_table = pd.read_csv(param.BIOBELTS_DESC)
lulc_table = pd.read_csv(param.LC_CLASSES)


def get_belt_desc(row):
    """return bioclimatic belt description"""

    desc = belt_table[belt_table.code == row["belt_class"]]["desc"]
    return desc.values[0] if len(desc) else "Total"


def get_lc_desc(row):
    """return landcover description"""
    desc = lulc_table[lulc_table.code == row["lc_class"]]["desc"]

    return desc.values[0] if len(desc) else "All"


def get_mgci_landtype(parsed_df):
    """
    This function takes in a parsed DataFrame as an input and returns a concatenated
    DataFrame that includes the calculation of belt area and grouping by
    land cover class (lc_class) and belt class.
    """

    df = parsed_df.copy()

    # Calculate belt area
    belt_area_df = df.groupby(["belt_class"]).sum().reset_index()[["belt_class", "sum"]]
    belt_area_df["lc_class"] = "All"

    land_type_df = pd.concat([df, belt_area_df])

    by_lc_df = df.groupby(["lc_class"]).sum().reset_index()[["lc_class", "sum"]]
    by_lc_df["belt_class"] = "Total"

    return pd.concat([land_type_df, by_lc_df])


def get_mgci(parsed_df: pd.DataFrame) -> pd.DataFrame:
    """
    This function takes a dataframe as input and calculates the MGCI (Mountain Green
    Cover Index) for each belt class. It groups the data by "belt_class" and "is_green",
    adds a column "is_green" to the dataframe based on the lc_map_matrix, calculates the
    green and non-green areas, and calculates the mgci value. The function then returns
    a new dataframe with the belts and their respective mgci values.
    """

    df = parsed_df.copy()

    # Adds is_green column to the dataframe based on lc_class.
    df["is_green"] = df.apply(
        lambda row: lc_map_matrix.loc[lc_map_matrix.target_code == row["lc_class"]][
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
        report_df = get_mgci_landtype(parsed_df)
        report_df["Value"] = report_df["sum"]
        report_df["Units"] = "SQKM_PA"
        report_df["Land Type"] = report_df.apply(get_lc_desc, axis=1)
        output_cols = sub_a_landtype_cols
    else:
        report_df = get_mgci(parsed_df)
        report_df["Value"] = report_df.mgci
        report_df["Units"] = "PERCENT"
        output_cols = sub_a_cols

    # The following cols are equal for both tables
    report_df["SeriesID"] = 1
    report_df["SeriesDescription"] = "Mountain Green Cover Index"
    report_df["GeoAreaName"] = cs.get_geoarea(model.aoi_model)[0]
    report_df["GeoAreaCode"] = cs.get_geoarea(model.aoi_model)[1]
    report_df["TimePeriod"] = year
    report_df["Time_Detail"] = year
    report_df["Source"] = "Food and Agriculture Organisation of United Nations (FAO)"
    report_df["FootNote"] = "FAO estimate"
    report_df["Nature"] = "G"
    report_df["Reporting Type"] = "G"
    report_df["Observation Status"] = "A"
    report_df["Bioclimatic Belt"] = report_df.apply(get_belt_desc, axis=1)
    report_df["ISOalpha3"] = "nan"
    report_df["Type"] = "Region"
    report_df["SeriesCode"] = "ER_MTN_GRNCVI"

    return report_df[output_cols], year
