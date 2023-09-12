import pandas as pd

import component.parameter.module_parameter as param
import component.scripts as cs

# isort: off
from component.parameter.index_parameters import mountain_area_cols
from component.scripts.report_scripts import (
    fill_parsed_df,
    get_belt_desc,
    get_nature,
    get_obs_status,
)

LC_MAP_MATRIX = pd.read_csv(param.LC_MAP_MATRIX)
"pd.DataFrame: land cover map matrix. Contains the mapping values between old and new classes for each land cover type. If user selects custom land cover, users will have to reclassify their classes into the fixed lulc_table classes."

BELT_TABLE = pd.read_csv(param.BIOBELTS_DESC)
"pd.Dataframe: bioclimatic belts classes and description"

LC_CLASSES = pd.read_csv(param.LC_CLASSES)
"pd.Dataframe: fixed land cover classes, description and colors"


def get_mountain_area(parsed_df):
    """Takes in a parsed DataFrame as an input and returns a DataFrame that
    gets the area for each belt class and a total area for all belt classes.

    Table1_MountainArea
    """

    # Fill dataframe with missing values
    df = fill_parsed_df(parsed_df.copy())

    # Calculate belt area
    belt_area_df = df.groupby(["belt_class"]).sum().reset_index()

    # Add total area for all belt_classes

    total_green = pd.DataFrame(columns=["belt_class", "sum"])
    total_green.loc[0] = ["Total", belt_area_df["sum"].sum()]

    return pd.concat([belt_area_df, total_green])


def get_report(parsed_df: pd.DataFrame, year: int, model) -> pd.DataFrame:
    """Create a report for Table1_MountainArea.

    Args:
        parsed_df (pd.DataFrame): it comes from cs.cs.get_result_from_year() since it gets the year from model.results and parses the result.
    """

    report_df = get_mountain_area(parsed_df)
    report_df["OBS_VALUE"] = report_df["sum"]
    report_df["OBS_VALUE_RSA"] = "TBD"  # TODO: check if we can report RSA
    report_df["UNIT_MEASURE"] = "KM2"
    report_df["UNIT_MULT"] = "TBD"

    # The following cols are equal for both tables
    report_df["Indicator"] = "15.4.2"
    report_df["SeriesID"] = "TBD"
    report_df["SERIES"] = "TBD"
    report_df["SeriesDesc"] = "TBD"
    report_df["GeoAreaName"] = cs.get_geoarea(model.aoi_model)[0]
    report_df["REF_AREA"] = cs.get_geoarea(model.aoi_model)[1]
    report_df["TIME_PERIOD"] = year
    report_df["TIME_DETAIL"] = year
    report_df["SOURCE_DETAIL"] = model.source
    report_df["COMMENT_OBS"] = "FAO estimate"
    report_df["BIOCLIMATIC_BELT"] = report_df.apply(get_belt_desc, axis=1)

    # fill NaN values with "N/A"
    report_df.fillna("NA", inplace=True)

    # fill zeros with "N/A"
    report_df.replace(0, "NA", inplace=True)

    report_df["NATURE"] = report_df.apply(get_nature, axis=1)
    report_df["OBS_STATUS"] = report_df.apply(get_obs_status, axis=1)

    return report_df[mountain_area_cols].reset_index(drop=True), year
