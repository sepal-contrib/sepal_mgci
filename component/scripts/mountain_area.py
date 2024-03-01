from typing import List, Tuple
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


def get_report(
    parsed_df: pd.DataFrame, year: int, model=None, **details
) -> Tuple[pd.DataFrame, int]:
    """Create a report for Table1_MountainArea.

    Args:
        parsed_df (pd.DataFrame): it comes from cs.cs.parse_to_year_a() since it gets the year from model.results and parses the result.

    **extra_args:
        Extra parameters used when model = None and function is executed from
        outside the ui
        - geo_area_name
        - ref_area
        - source_detail
    """

    if details:
        # This is useful when function is called from outside the
        geo_area_name = details.get("geo_area_name")
        ref_area = details.get("ref_area")
        source_detail = details.get("source_detail")

    report_df = get_mountain_area(parsed_df)
    report_df["OBS_VALUE"] = report_df["sum"]
    report_df["OBS_VALUE_RSA"] = param.TBD  # TODO: check if we can report RSA
    report_df["UNIT_MEASURE"] = "KM2"
    report_df["UNIT_MULT"] = param.TBD

    # The following cols are equal for both tables
    report_df["Indicator"] = "15.4.2"
    report_df["SeriesID"] = param.TBD
    report_df["SERIES"] = param.TBD
    report_df["SeriesDesc"] = param.TBD
    report_df["GeoAreaName"] = geo_area_name or cs.get_geoarea(model.aoi_model)[0]
    report_df["REF_AREA"] = ref_area or cs.get_geoarea(model.aoi_model)[1]
    report_df["TIME_PERIOD"] = year
    report_df["TIME_DETAIL"] = year
    report_df["SOURCE_DETAIL"] = source_detail or model.source
    report_df["COMMENT_OBS"] = "FAO estimate"
    report_df["BIOCLIMATIC_BELT"] = report_df.apply(get_belt_desc, axis=1)

    # round obs_value
    report_df["OBS_VALUE"] = report_df["OBS_VALUE"].round(4)
    report_df["OBS_VALUE_RSA"] = report_df["OBS_VALUE"].round(4)

    # Convert DataFrame to object type
    report_df = report_df.astype(object)

    # fill NaN values with "N/A"
    report_df.fillna("NA", inplace=True)

    # fill zeros with "N/A"
    report_df.replace(0, "NA", inplace=True)

    report_df["NATURE"] = report_df.apply(get_nature, axis=1)
    report_df["OBS_STATUS"] = report_df.apply(get_obs_status, axis=1)

    return report_df[mountain_area_cols].reset_index(drop=True)
