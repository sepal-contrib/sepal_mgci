from typing import Optional

import pandas as pd

import component.parameter.module_parameter as param
import component.scripts as cs

# isort: off
from component.parameter.index_parameters import sub_b_landtype_cols, sub_b_perc_cols

transition_table = pd.read_csv(param.TRANSITION_MATRIX_FILE)
belt_table = pd.read_csv(param.BIOBELTS_DESC)


def get_impact(row):
    """Return the type of the impact based on the initial and last class"""

    # Check that both
    if not all([row["from_lc"], row["to_lc"]]):
        return 0

    return transition_table[
        (transition_table.from_code == row["from_lc"])
        & (transition_table.to_code == row["to_lc"])
    ]["impact_code"].values[0]


def get_impact_desc(row):
    """Return impact description based on its code"""
    desc = transition_table[transition_table.impact_code == row["impact"]]["impact"]

    return desc.values[0] if len(desc) else "All"


def get_belt_desc(row):
    """return bioclimatic belt description"""

    desc = belt_table[belt_table.code == row["belt_class"]]["desc"]

    return desc.values[0] if len(desc) else "Total"


def get_pdma(parsed_df):
    """
    Get the MGCI report table for the given period

    df (DataFrame): grouped dataframe from raw data
    """

    df = parsed_df.copy()
    df["impact"] = df.apply(get_impact, axis=1)

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


def get_pdma_landtype(parsed_df):
    """
    Get the MGCI report table for the given iso_code and year

    df (DataFrame): grouped dataframe from raw data
    iso_code (str): country iso code

    """

    # Prepare df
    df = parsed_df.copy()
    df["impact"] = df.apply(get_impact, axis=1)

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
        report_df = get_pdma_landtype(parsed_df)
        report_df["Value"] = report_df["sum"]
        report_df["Units"] = "KM2_PA"
        report_df["Impact Type"] = report_df.apply(get_impact_desc, axis=1)
        output_cols = sub_b_landtype_cols
    else:
        report_df = get_pdma(parsed_df)
        report_df["Value"] = report_df.pdma
        report_df["Units"] = "PERCENT"
        output_cols = sub_b_perc_cols

    report_df["SeriesID"] = 1

    report_df["SeriesDescription"] = "Proportion of degraded mountain land"
    report_df["GeoAreaName"] = cs.get_geoarea(model.aoi_model)[0]
    report_df["GeoAreaCode"] = cs.get_geoarea(model.aoi_model)[1]
    report_df["TimePeriod"] = years[1]
    report_df["Time_Detail"] = f"{years[0]}-{years[1]}"
    report_df["Source"] = "Food and Agriculture Organisation of United Nations (FAO)"
    report_df["FootNote"] = "FAO estimate"
    report_df["Nature"] = "G"
    report_df["Reporting Type"] = "G"
    report_df["Observation Status"] = "A"
    report_df["Bioclimatic Belt"] = report_df.apply(get_belt_desc, axis=1)
    report_df["ISOalpha3"] = "np.nan"
    report_df["Type"] = "Region"
    report_df["SeriesCode"] = "XXXX"

    return report_df[output_cols], f"{years[0]}_{years[1]}"
