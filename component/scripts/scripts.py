from typing import TYPE_CHECKING
import random
import re
from pathlib import Path
from typing import Dict, List, Literal, Tuple, Union

import ipyvuetify as v
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from sepal_ui.aoi.aoi_model import AoiModel

import component.parameter.directory as DIR
import component.parameter.module_parameter as param
import component.scripts as cs
from component.scripts import mountain_area as mntn
from component.scripts import sub_a as sub_a
from component.scripts import sub_b as sub_b

if TYPE_CHECKING:
    from component.model.model import MgciModel


__all__ = [
    "human_format",
    "get_random_color",
    "get_mgci_color",
    "get_report_folder",
    "get_geoarea",
    "create_avatar",
    "get_years",
    "read_from_csv",
    "export_reports",
    "get_sub_a_break_points",
    "years_from_dict",
    "get_result_from_year",
    "get_sub_b_break_points",
    "get_sub_b_years_labels",
    "parse_result",
]


def create_avatar(mgci: float) -> v.Avatar:
    """Creates a circular avatar containing the MGCI value"""
    color = cs.get_mgci_color(mgci)

    overall_mgci_html = v.Html(
        tag="h1", children=["MGCI", v.Html(tag="br"), str(mgci) + "%"]
    )
    return v.Avatar(color=color, size="150", children=[overall_mgci_html])


def human_format(num: float, round_to: int = 2) -> str:
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return "{:.{}f}{}".format(
        round(num, round_to), round_to, ["", "K", "M", "G", "T", "P"][magnitude]
    )


def get_random_color() -> str:
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def get_mgci_color(mgci: float) -> str:
    """Return color based on a given MGCI scale"""

    thresholds = sorted(param.UPPER_THRESHOLDS, reverse=True)

    for threshold in thresholds:
        if mgci >= threshold:
            break
    return param.UPPER_THRESHOLDS[threshold]


def get_report_folder(mgci_model: "MgciModel") -> Path:
    """Get output report folder path"""

    # Create a folder to store multiple year reports from the same area
    report_folder = DIR.REPORTS_DIR / f"MGCI_{mgci_model.aoi_model.name}"
    report_folder.mkdir(parents=True, exist_ok=True)
    return report_folder


def get_geoarea(aoi_model: AoiModel) -> Tuple[str, str]:
    """Create the geo area name to the excel report"""

    if aoi_model.method in ["ADMIN0", "ADMIN1", "ADMIN2"]:
        split_name = aoi_model.name.split("_")

        iso31661 = split_name[0]

        m49_df = pd.read_csv(param.M49_FILE, sep=";")

        gaul_row = m49_df[m49_df.iso31661 == iso31661]

        geoarea_name = gaul_row["country"].values[0]
        m49_code = gaul_row["m49"].values[0]

        if len(split_name) > 1:
            geoarea_name = f"{geoarea_name}_" + "_".join(split_name[1:])
        return geoarea_name, m49_code
    else:
        return aoi_model.name, ""


def remove_duplicated_years(
    breakpoints: List[List[Dict[str, Union[int, float]]]]
) -> List[List[Dict[str, Union[int, float]]]]:
    """Remove duplicated years from a list of years"""

    # remove duplicates knowing that years are dictionaries
    converted_list = [
        frozenset(frozenset(d.items()) for d in sublist) for sublist in breakpoints
    ]

    # Remove duplicates by using a set comprehension and then convert back to a list
    # of lists of dictionaries. Sort them by year.
    # return [
    #     sorted(list(dict(d) for d in fs), key=lambda d: d.get("year"))
    #     for fs in set(converted_list)
    # ]

    return [
        sorted(
            list(dict(sorted(d, key=lambda x: x[0])) for d in fs),
            key=lambda d: d.get("year"),
        )
        for fs in set(converted_list)
    ]


def years_from_dict(year_dict: dict) -> str:
    """Extract years from a get_years dictionary.

    It will be used to label and display the progress in the alerts.

    Args:
        year_dict (dict): dictionary with years coming from get_years function
    """

    return "_".join([str(year.get("year")) for year in year_dict])


def get_interpolation_years(
    breaking_points: Dict[str, List[Dict[str, str]]]
) -> List[List[Dict[str, str]]]:
    """Get interpolation years (assets) from the breaking points.

    Based on the breaking points, it will return a list of years (assets)
    that will be used to interpolate the sub indicator.

    There are three posible cases:

     1. a reporting period has 4 years, in that case we need to calculate
        the reduction with first and second year, and second and third year.

     2. a reporting period has 3 years, this case is special because we
        have two options: calculate the reduction with first and second year,
        or second and third year. The option selected will be the one that
        has the reporting period at the end or beginning of the asset list.
        for example, if the reporting period is 2010-2015, and the asset list
        is [2009, 2011, 2015], then we will calculate the reduction with
        2009-2011, while if the asset list is [2010, 2013, 2016], then we will
        calculate the reduction with 2013-2016.

     3. a reporting period has 2 years, in that case we need to calculate
        the reduction with first and second year.
    """
    # create a list of years to calculate the reduction
    years_to_calculate: list[list[dict[str, str]]] = []
    for period, year in breaking_points.items():
        if len(year) == 4:
            years_to_calculate.append(year[:2])
            years_to_calculate.append(year[1:])
        elif len(year) == 3:
            if year[0].get("year") in period:
                years_to_calculate.append([year[0]])
                years_to_calculate.append(year[1:])
            elif year[-1].get("year") in period:
                years_to_calculate.append(year[:2])
                years_to_calculate.append([year[-1]])
            else:
                raise ValueError("Invalid reporting period.")
        elif len(year) == 2:
            years_to_calculate.append(year)
        else:
            raise ValueError("Invalid year format")

    # remove duplicated years
    years_to_calculate = remove_duplicated_years(years_to_calculate)

    return sorted(
        [
            sorted(segment, key=lambda x: x.get("year"))
            for segment in years_to_calculate
        ],
        key=lambda x: [y.get("year") for y in x],
    )


def get_years(
    sub_a_year: dict,
    sub_b_year: dict,
    matrix_a: str,
    matrix_b: str,
    which: Literal["both", "sub_a", "sub_b"],
) -> List[List[int]]:
    """Returns a nested list of years (asset) based on the input start and end years.

    In order to minimize the number of calculations, assets that are present
    in both models are only calculated once (using reduction with both years)
    (example 1) as long as matrix_a and matrix_b are the same. If they are
    different, then the assets are calculated reparately (example 2).

    Args:
        sub_a_year (dict): model dictionary containing sub A dialog v_model
        sub_b_year (dict): model dictionary containing sub B dialog v_model
        matrix_a (dict): reclassification matrix from model A
        matrix_b (dict): reclassification matrix from model B
        which (str): which sub indicator is being calculated


    Returns:
        list: A list with individual years (for indicator A) and nested list
            of years [[start, end], ...,[start, end]] (for indicator B)

    Example:
        sub_a_year = {
            1: {'asset': 'asset_x/2020',year': '2020'},
            2: {'asset': 'asset_x/2015',year': '2015'},
        }

        sub_b_year = {
            1: {'asset': 'asset_y/2020',year': '2020'},
            2: {'asset': 'asset_y/2015',year': '2015'},
        }
        returns: [[asset_x/2015], [asset_x/2020] [asset_y/2020', asset_y/2015]]

    """

    years_to_calculate = get_sub_b_break_points(sub_b_year)

    if which == "sub_b":
        return years_to_calculate

    years_a = get_sub_a_break_points(sub_a_year)

    if which == "sub_a":
        years_to_calculate = []
        for breakp_years in years_a.values():
            # flatten years_a list
            for year in breakp_years:
                years_to_calculate.append([year])
        return years_to_calculate

    if matrix_a == matrix_b:
        # Add years from years_a that are not present in years_b
        for breakp_years in years_a.values():
            # flatten years_a list
            for year in breakp_years:
                if year not in [
                    item for sublist in years_to_calculate for item in sublist
                ]:
                    years_to_calculate.append([year])

        return years_to_calculate

    else:
        # Add all years from years_a individually
        return years_to_calculate + [
            [year]
            for sublist in remove_duplicated_years(years_a.values())
            for year in sublist
        ]


def get_result_from_year(
    model: "MgciModel", year: int, indicator: str
) -> Union[pd.DataFrame, None]:
    """Return the results for the given year.

    It will use the results dictionary to get the results for the requested
    year.

    If indicator sub a es required, it will first try to search it within the individual
    years, and if it is not found, it will search it within the double years (if
    same_asset_matrix == True). If there's
    not a match, it will try to interpolate the results.

    Args:
        results (dict): dictionary with results coming from model
        year (int): year to get the results from
        indicator (str): indicator to get the results from
        same_asset_matrix (bool): if matrix and asset are the same
    """
    results = model.results
    same_asset_matrix = model.same_asset_matrix
    reporting_years_sub_a = model.reporting_years_sub_a

    str_year = str(year)

    individual_yrs = [y for y in results.keys() if len(y.split("_")) == 1]
    double_years = [y for y in results.keys() if len(y.split("_")) == 2]

    # Check that indicator is sub_a and year is in individual years
    if indicator == "sub_a" and any([str_year in yr for yr in individual_yrs]):
        return parse_result(results[str_year]["groups"], single=True)

    # Otherwise, check that year is in double years
    in_double = [str_year in yr for yr in double_years]

    if any(in_double):
        # There is no way that there are more than 2 years in double_years
        assert sum(in_double) == 1, "More than 2 years in double_years"
        idx = in_double.index(True)

        # We can only try to get year from double years if indicator same_asset_matrix
        if indicator == "sub_a" and same_asset_matrix:
            # If we are in sub_a, we need to extract target year from double years
            parsed_df = parse_result(results[double_years[idx]]["groups"])

            # Get the name of the column that contains the target year
            target_lc = ["from_lc", "to_lc"][
                double_years[idx].split("_").index(str_year)
            ]

            cols = ["belt_class", target_lc]
            parsed_df = parsed_df.groupby(cols, as_index=False).sum()[cols + ["sum"]]
            parsed_df = parsed_df.rename(columns={target_lc: "lc_class"})

            return parsed_df

        elif indicator == "sub_b":
            return parse_result(results[double_years[idx]]["groups"])

    # If we're here, it means that we didn't find the year in individual or double years
    if indicator == "sub_a":
        assert (
            int(year) in reporting_years_sub_a
        ), "You're not suppose to be asking for this year"

        # Try to get the year by interpolating between two years only if we are in sub_a
        year1 = model.reporting_years_sub_a[int(year)][0]["year"]
        year2 = model.reporting_years_sub_a[int(year)][1]["year"]

        return interpolate_sub_a_data(model, year1, year2, year)

    raise Exception(
        f"{str_year} not found in results, are you sure indicator is correct?"
    )


def interpolate_sub_a_data(
    model: "MgciModel", year1: int, year2: int, target_year: int
) -> pd.DataFrame:  # type: ignore
    """Interpolate sub A data between two years.

    Args:
        mode (MgciModel): MGCI model containing results from calculation
        year1 (int): first year
        year2 (int): second year
        target_year (int): target year
    """

    if not year2 > year1:
        raise Exception("year2 has to be higher than year 1")

    if not (year1 < target_year < year2):
        raise Exception("target year has to be in between year1 and year 2")
    df1 = get_result_from_year(model, year1, "sub_a")
    df2 = get_result_from_year(model, year2, "sub_a")

    # Ensure both dataframes have the same structure
    if not (df1.columns == df2.columns).all():
        raise Exception("Dataframes must have the same columns")

    # Merge dataframes on belt_class and lc_class
    # This will ensure that the dataframes have the same structure
    merged_df = df1.merge(df2, on=["belt_class", "lc_class"])

    # Perform linear interpolation between y1 and y2
    # I've used this function because later we can change the interpolation
    # method without having to change the rest of the code

    interp_func = interp1d(
        [year1, year2], np.vstack([merged_df["sum_x"], merged_df["sum_y"]]), axis=0
    )

    # Get the interpolated data for the requested year
    interpolated_data = interp_func(target_year)

    # Create a new DataFrame with the interpolated data
    df_interpolated = merged_df[["belt_class", "lc_class"]].copy()
    df_interpolated["sum"] = interpolated_data

    return df_interpolated


def parse_result(result: dict, single: bool = False) -> pd.DataFrame:
    """
    This function parses the nest result to create a exploded dataframe.
    The input format should be of type:

    {'belt': [
        {'from_lc':[
            {'to_lc': [
                {'sum': <value>}
            ]}
        ]}
    ]}

    Parameters
    ----------

    result : dict
        The input dictionary with nested groups
    single : bool (default=False).
        The flag to indicate whether single level or double level nesting exists

    Returns
    -------
    df : pandas.DataFrame
        The resulting dataframe with the corresponding columns and their values.

    """

    # Define the dataframe depending whether if single or double level nested
    df = (
        pd.DataFrame(columns=["belt_class", "lc_class", "sum"])
        if single
        else pd.DataFrame(columns=["belt_class", "from_lc", "to_lc", "sum"])
    )

    s = 0
    for belt in result:
        for lc_class in belt["groups"]:
            if single:
                df.loc[s] = [belt["group"], lc_class["group"], lc_class["sum"]]
                s += 1
            else:
                for lc_to_class in lc_class["groups"]:
                    df.loc[s] = [
                        belt["group"],
                        lc_class["group"],
                        lc_to_class["group"],
                        lc_to_class["sum"],
                    ]
                    s += 1
    return df


def read_from_csv(task_file, process_id) -> dict:
    """read csv format from feature collection exportation in gee

    Args:
        task_file(path): full path of downloaded task
        process_id (str): process id, normally are the year(s) of the result
    """

    result_df = pd.read_csv(task_file)

    line = (
        re.sub(r"([a-zA-Z]+)", r"'\1'", result_df.groups.iloc[0])
        .replace("=", ":")
        .replace("'E'", "E")
        .replace("<'FeatureCollection'>,", "")
    )

    return eval(line)


def get_sub_b_break_points(
    user_input_years: Dict[str, Dict[str, Dict[str, int]]]
) -> List[List[int]]:
    """Extract years from user input.

    This functions extracts all the assets in the form of
    [{asset:xx, year:xx}, ...] from the user input, to easier manipulataion.

    """

    # extract tuple of years from user input
    reporting_years: List[List[int]] = []
    for user_year in user_input_years.values():
        for user_tuple in user_year.values():
            reporting_years.append([user_tuple.get("base"), user_tuple.get("report")])

    return reporting_years


def get_sub_b_years_labels(sub_b_year: Dict) -> Dict:
    """Returns string label for sub_b indicator.

    It gets the input user years for indicator sub b and parses the
    years for each reporting period as the same way as it is set in
    model.results dictionary.

    If user is reporting year 2015, with 2009 and 2014, and 2018 with 2014 and 2017,
    the function will return a dictionary with the following structure:

    .. code-block:: python

        {
            2015: "2009_2014",
            2018: "2014_2017"
        }

    This fucntion will be used in the dashboard to display the results from the user
    selection.

    """

    yrs = {}
    for date in sub_b_year.values():
        for period in date.values():
            report_year = next(iter(list(date.keys())))

            if "base" not in period or "report" not in period:
                raise Exception(
                    f"You have not provided a base and report period for {report_year}"
                )

            if "year" not in period.get("base") or "year" not in period.get("report"):
                raise Exception(
                    f"You have not provided an actual year for {report_year}"
                )

            yr_tuple = [
                str(period.get("base").get("year")),
                str(period.get("report").get("year")),
            ]

            label_yrs = "_".join(yr_tuple)

            yrs[report_year] = label_yrs

    return yrs


def get_sub_a_break_points(user_input_years: list) -> dict:
    """Get the break points for Sub-A.

    It will get the years that can be reported using the user input years. In case
    the user input years are not in the reporting years, it will get the closest from
    below and above, it will use this breakpoints to interpolate the values.

    Args:
        user_input_years: A list of user input years.

    Returns:
        A dictionary of break points.
    """
    # get a list of the years from the user input
    user_years = [val.get("year") for val in user_input_years.values()]

    # filter report intervals that are relevant given the user input years
    reporting_years = [
        report_year
        for report_year in param.REPORT_INTERVALS
        if report_year >= min(user_years) and report_year <= max(user_years)
    ]

    break_points = {}

    for report_year in reporting_years:
        # if the report year is in the list of user input years
        if report_year in user_years:
            # save the year to the break points
            break_points[report_year] = [
                year
                for year in user_input_years.values()
                if year.get("year") == report_year
            ]

        else:
            # get years that will be used to interpolate
            # get minimum year that is larger than the report year
            after_report_year = min(
                [
                    year
                    for year in user_input_years.values()
                    if year.get("year") > report_year
                ],
                key=lambda x: x.get("year"),
                default=None,
            )

            # get maximum year that is smaller than the report year
            before_report_year = max(
                [
                    year
                    for year in user_input_years.values()
                    if year.get("year") < report_year
                ],
                key=lambda x: x.get("year"),
                default=None,
            )

            # if both years exist
            if before_report_year and after_report_year:
                # save the years to the break points
                break_points[report_year] = [before_report_year, after_report_year]

            else:
                break_points[report_year] = None

    return break_points


def export_reports(model: "MgciModel", output_folder) -> None:
    """
    This function exports the reports of the model's results (calculation).
    It separates the reports into two categories: sub_a_reports and sub_b_reports.
    For each group in the results, it performs the following steps:
        - Splits the group name by "_" to get the year(s)
        - If there is only one year, it parses the result and appends the sub_a_report
            to the sub_a_reports list
        - If there are multiple years, it parses the result and for each year:
            - Groups the parsed dataframe by belt_class and target_lc
            - Renames the target_lc column to lc_class
            - Appends the sub_a_report to the sub_a_reports list
        - Appends the sub_b_report to the sub_b_reports list

    :param model: The model object containing the results to be exported
    :type model: object
    :return: A tuple containing two lists, the first one is sub_a_reports and the second
        one is sub_b_reports
    :rtype: tuple
    """

    mtn_reports = []
    sub_a_reports = []
    sub_b_reports = []

    # Instead of looping over all "results" in the model, we
    # only loop over the ones that are of our interest.
    # use model.reporting_years_sub_b and model.reporting_years_sub_a

    sub_a_years = list(model.reporting_years_sub_a.keys())
    sub_b_years = model.reporting_years_sub_b

    for year in sub_a_years:
        print(f"Reporting {year} for sub_a")
        parsed_df = cs.get_result_from_year(model, year, "sub_a")
        sub_a_reports.append(sub_a.get_reports(parsed_df, year, model))
        print(f"Reporting {year} for mtn")
        mtn_reports.append(mntn.get_report(parsed_df, year, model))

    for year in sub_b_years:
        print(f"Reporting {year} for sub_b")
        # Get year label for the report
        year_lbl = cs.get_sub_b_years_labels(model.sub_b_year)[year]
        print(year_lbl)
        parsed_df = cs.get_result_from_year(model, year_lbl, "sub_b")
        sub_b_reports.append(sub_b.get_reports(parsed_df, year_lbl, model))

    for reports in sub_a_reports:
        [
            report[0].to_excel(
                str(Path(output_folder, name.format(report[1]))),
                sheet_name=name.format(report[1]),
                index=False,
            )
            for report, name in zip(
                reports,
                ["Table3_1542a_MGCI_{}.xlsx", "Table2_1542a_LandCoverType_{}.xlsx"],
            )
        ]

    for reports in sub_b_reports:
        [
            report[0].to_excel(
                str(Path(output_folder, name.format(report[1]))),
                sheet_name=name.format(report[1]),
                index=False,
            )
            for report, name in zip(
                reports,
                ["Table5_1542b_pdma_pt_{}.xlsx", "Table4_1542b_pdma_area_{}.xlsx"],
            )
        ]

    for reports in mtn_reports:
        [
            report.to_excel(
                str(Path(output_folder, name.format(name))),
                sheet_name=name.format(name),
                index=False,
            )
            for report, name in zip(reports, ["Table1_MountainArea_{}.xlsx"])
        ]

    return True
