from typing import Dict, Optional, Tuple, TYPE_CHECKING

import pandas as pd

import component.parameter.module_parameter as param
import component.scripts as cs

# isort: off
from component.parameter.index_parameters import sub_b_landtype_cols, sub_b_perc_cols

from component.scripts.report_scripts import (
    get_impact,
    get_nature,
    get_belt_desc,
    get_obs_status,
)

if TYPE_CHECKING:
    from component.model.model import MgciModel

BELT_TABLE = pd.read_csv(param.BIOBELTS_DESC)
"pd.Dataframe: bioclimatic belts classes and description"


def get_degraded_area(parsed_df: pd.DataFrame, model: "MgciModel"):
    """Return net and gross area of degraded land per belt class"""

    # Prepare df
    df = parsed_df.copy()
    df["impact"] = df.apply(lambda x: get_impact(x, model=model), axis=1)

    # get the degraded area
    degraded = (
        df[df.impact == 1]
        .groupby(["belt_class"])
        .sum(numeric_only=True)
        .reset_index()[["belt_class", "sum"]]
    )
    degraded.rename(columns={"sum": "degraded"}, inplace=True)

    # Get net degraded area per belt class as the sum of improved minus the sum of degraded

    improved = (
        df[df.impact == 3]
        .groupby(["belt_class"])
        .sum(numeric_only=True)
        .reset_index()[["belt_class", "sum"]]
    )
    improved.rename(columns={"sum": "improved"}, inplace=True)

    net_degraded = degraded.merge(improved, on="belt_class", how="outer")
    net_degraded["net_degraded"] = net_degraded.degraded - net_degraded.improved

    # we must be sure that all belt classes are present.
    # if not, we must add them with 0 values
    net_degraded = net_degraded.merge(
        BELT_TABLE[["belt_class"]],
        left_on="belt_class",
        right_on="belt_class",
        how="outer",
    )

    return net_degraded


def get_pdma_area(parsed_df, model):
    """Return net and gross area of degraded land per belt class"""

    degraded = get_degraded_area(parsed_df, model=model)

    # Add new row for total
    total_row = pd.DataFrame(
        [
            [
                "Total",
                degraded.degraded.sum(),
                degraded.degraded.sum() - degraded.improved.sum(),
            ]
        ],
        columns=["belt_class", "degraded", "net_degraded"],
    )

    return pd.concat([degraded, total_row])


def get_pdma_pt(parsed_df, model):
    """Return net and gross area (as percentage) of degraded land per belt class"""

    pt_degraded = get_degraded_area(parsed_df, model=model)

    # get total area of each belt class
    belt_area = parsed_df.groupby("belt_class").sum(numeric_only=True).reset_index()
    # Merge pdma_area and belt_area

    pt_degraded = pd.merge(
        pt_degraded, belt_area[["belt_class", "sum"]], how="left", on="belt_class"
    )

    pt_degraded["pt_degraded"] = pt_degraded["degraded"] / pt_degraded["sum"]
    pt_degraded["pt_net_degraded"] = (
        pt_degraded["net_degraded"] / pt_degraded["sum"] * 100
    )

    # Add new row for total
    total_row = pd.DataFrame(
        [
            [
                "Total",
                pt_degraded.degraded.sum() / pt_degraded["sum"].sum() * 100,
                (pt_degraded.degraded.sum() - pt_degraded.improved.sum())
                / pt_degraded["sum"].sum()
                * 100,
            ]
        ],
        columns=["belt_class", "pt_degraded", "pt_net_degraded"],
    )

    return pd.concat([pt_degraded, total_row])


def get_report(
    parsed_df: pd.DataFrame,
    years: Dict[str, Tuple[int, int]],
    model: "MgciModel",
    area: Optional[bool] = False,
) -> pd.DataFrame:
    parsed_df = parsed_df.copy()

    years = list(years.values())[0]

    if area:
        report_df = get_pdma_area(parsed_df, model)
        report_df["OBS_VALUE"] = report_df["degraded"]
        report_df["OBS_VALUE_NET"] = report_df["net_degraded"]
        report_df[
            "OBS_VALUE_RSA"
        ] = "TBD"  # TODO: determine if we're going to use RSA or not
        report_df[
            "OBS_VALUE_RSA_NET"
        ] = "TBD"  # TODO: determine if we're going to use RSA or not
        report_df["UNIT_MEASURE"] = "KM2"
        report_df["UNIT_MULT"] = "TBD"
        output_cols = sub_b_landtype_cols
    else:
        report_df = get_pdma_pt(parsed_df, model)
        report_df["OBS_VALUE"] = report_df["pt_degraded"]
        report_df["OBS_VALUE_NET"] = report_df["pt_net_degraded"]
        report_df["UNIT_MEASURE"] = "PT"
        report_df["UNIT_MULT"] = "TBD"

        output_cols = sub_b_perc_cols

    report_df["Indicator"] = "15.4.2"
    report_df["SeriesID"] = "TBD"
    report_df["SERIES"] = "TBD"
    report_df["SeriesDesc"] = "TBD"
    report_df["REF_AREA"] = cs.get_geoarea(model.aoi_model)[1]
    report_df["GeoAreaName"] = cs.get_geoarea(model.aoi_model)[0]
    report_df["TIME_PERIOD"] = f"{years[1]}"
    report_df["TIME_DETAIL"] = f"{years[0]}-{years[1]}"
    report_df["SOURCE_DETAIL"] = model.source
    report_df["COMMENT_OBS"] = "FAO estimate"

    report_df["BIOCLIMATIC_BELT"] = report_df.apply(get_belt_desc, axis=1)

    # round obs_value
    report_df["OBS_VALUE"] = report_df["OBS_VALUE"].round(4)
    report_df["OBS_VALUE_NET"] = report_df["OBS_VALUE"].round(4)

    # Convert DataFrame to object type
    report_df = report_df.astype(object)

    # Now fill NaN values with "NA"
    report_df.fillna("NA", inplace=True)

    # fill zeros with "N/A"
    report_df.replace(0, "NA", inplace=True)

    report_df["NATURE"] = report_df.apply(get_nature, axis=1)
    report_df["OBS_STATUS"] = report_df.apply(get_obs_status, axis=1)

    return report_df[output_cols]


def get_reports(
    parsed_df: pd.DataFrame, year_s: Dict[str, Tuple[int, int]], model: "MgciModel"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    SubIndB_pdma
    SubIndB_pdma_TransitionType

    Args:
        year_s: either {"baseline": (2000, 2015)} or {"report": (2015, 2018)"

    """

    pdma_perc_report = get_report(parsed_df, year_s, model)
    pdma_land_type_report = get_report(parsed_df, year_s, model, area=True)

    return pdma_perc_report, pdma_land_type_report
