from typing import Optional

import pandas as pd

import component.parameter.module_parameter as param
import component.scripts as cs

# isort: off
from component.parameter.index_parameters import sub_b_landtype_cols, sub_b_perc_cols

from component.scripts.report_scripts import (
    get_impact,
    get_impact_desc,
    get_belt_desc,
    fill_parsed_df,
)


def get_pdma(parsed_df, model):
    """Get the MGCI report table for the given period

    Args:
        df (DataFrame): grouped dataframe from raw data
        model MGCIModel: Model containing transition_matrix dataframe (custom or default)

    Table5_1542b_pdma_pt

    """
    df = fill_parsed_df(parsed_df.copy())
    df["impact"] = df.apply(lambda x: get_impact(x, model=model), axis=1)

    # Prepare df
    # Get the rest of the proportion (stable+increase aka 0,1)
    stable_recover = (
        df[df.impact.isin([0, 1])]
        .groupby(["belt_class"])
        .sum()
        .reset_index()[["belt_class", "sum"]]
    )

    # Get degraded area (-1 class is degraded)
    degraded = df[df.impact == -1][["belt_class", "sum"]]

    # If there nothing degraded
    if not len(degraded):
        degraded = stable_recover.copy(deep=True)
        degraded["sum"] = 0

    # Get the degradation rate by belt
    pdma_df = pd.merge(stable_recover, degraded, on=["belt_class"], how="outer")

    pdma_df.rename(
        columns={"sum_x": "sum_stable_recover", "sum_y": "sum_degraded"}, inplace=True
    )
    pdma_df["pdma"] = (
        pdma_df["sum_degraded"]
        / (pdma_df["sum_stable_recover"] + pdma_df["sum_degraded"])
        * 100
    )

    # Return a dataframe with all the columns
    total_pdma = pd.DataFrame(
        [
            [
                "Total",
                pdma_df["sum_degraded"].sum()
                / pdma_df[["sum_stable_recover", "sum_degraded"]].sum().sum()
                * 100,
            ]
        ],
        columns=["belt_class", "pdma"],
    ).fillna(0)

    return pd.concat([pdma_df, total_pdma])


def get_pdma_landtype(parsed_df, model):
    """
    Get the MGCI report table for the given iso_code and year

    Args:
        df (DataFrame): grouped dataframe from raw data
        model MGCIModel: Model containing transition_matrix dataframe (custom or default)

    Table4_1542b_pdma_area
    """

    # Prepare df
    df = parsed_df.copy()
    df["impact"] = df.apply(lambda x: get_impact(x, model=model), axis=1)

    # Summary area by belt
    by_belt = df.groupby(["belt_class"]).sum().reset_index()[["belt_class", "sum"]]
    by_belt["impact"] = "All"

    # Summary area by impact
    by_impact = df.groupby(["impact"]).sum().reset_index()[["impact", "sum"]]

    by_impact["belt_class"] = "Total"

    result = pd.concat([df, by_belt, by_impact])

    return result


def get_report(
    parsed_df: pd.DataFrame, years: list, model, land_type: Optional[bool] = False
) -> pd.DataFrame:
    if land_type:
        report_df = get_pdma_landtype(parsed_df, model)
        report_df["OBS_VALUE"] = report_df["sum"]
        report_df["OBS_VALUE_NET"] = "TBD"
        report_df[
            "OBS_VALUE_RSA"
        ] = "TBD"  # TODO: determine if we're going to use RSA or not
        report_df[
            "OBS_VALUE_RSA_NET"
        ] = "TBD"  # TODO: determine if we're going to use RSA or not
        report_df["UNIT_MEASURE"] = "KM2"
        report_df["IMPACT_TYPE"] = report_df.apply(get_impact_desc, axis=1)
        output_cols = sub_b_landtype_cols
    else:
        report_df = get_pdma(parsed_df, model)
        report_df["OBS_VALUE"] = report_df.pdma
        report_df["OBS_VALUE_NET"] = "TBD"
        report_df["UNIT_MEASURE"] = "PT"
        output_cols = sub_b_perc_cols

    report_df["Indicator"] = "15.4.2"
    report_df["SeriesID"] = "TBD"
    report_df["SERIES"] = "TBD"
    report_df["SeriesDesc"] = "TBD"
    report_df["REF_AREA"] = cs.get_geoarea(model.aoi_model)[1]
    report_df["GeoAreaName"] = cs.get_geoarea(model.aoi_model)[0]
    report_df["TIME_PERIOD"] = years  # TODO: CHANGE THIS
    report_df["TIME_DETAIL"] = f"{years[0]}-{years[1]}"  # TODO: CHANGE THIS
    report_df[
        "SOURCE_DETAIL"
    ] = "Food and Agriculture Organisation of United Nations (FAO)"  # TODO: Capture from user's input
    report_df["COMMENT_OBS"] = "FAO estimate"
    report_df["NATURE"] = ""  # TODO: CREATE cs.get_nature()
    report_df["OBS_STATUS"] = ""  # TODO: CREATE cs.get_obs_status()
    report_df["BIOCLIMATIC_BELT"] = report_df.apply(get_belt_desc, axis=1)

    return report_df[output_cols], f"{years[0]}_{years[1]}"
