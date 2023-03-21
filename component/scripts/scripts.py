import random
import re
from pathlib import Path

import ipyvuetify as v
import pandas as pd

import component.parameter.directory as DIR
import component.parameter.module_parameter as param
import component.scripts as cs
from component.scripts import sub_a, sub_b

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
    "calculate_breakpoints",
    "years_from_dict",
]


def create_avatar(mgci):
    """Creates a circular avatar containing the MGCI value"""
    color = cs.get_mgci_color(mgci)

    overall_mgci_html = v.Html(
        tag="h1", children=["MGCI", v.Html(tag="br"), str(mgci) + "%"]
    )
    return v.Avatar(color=color, size="150", children=[overall_mgci_html])


def human_format(num, round_to=2):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return "{:.{}f}{}".format(
        round(num, round_to), round_to, ["", "K", "M", "G", "T", "P"][magnitude]
    )


def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def get_mgci_color(mgci):
    """Return color based on a given MGCI scale"""

    thresholds = sorted(param.UPPER_THRESHOLDS, reverse=True)

    for threshold in thresholds:
        if mgci >= threshold:
            break
    return param.UPPER_THRESHOLDS[threshold]


def get_report_folder(mgci_model):
    """Get output report folder path"""

    # Create a folder to store multiple year reports from the same area
    report_folder = DIR.REPORTS_DIR / f"MGCI_{mgci_model.aoi_model.name}"
    report_folder.mkdir(parents=True, exist_ok=True)
    return report_folder


def get_geoarea(aoi_model):
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


def remove_duplicated_years(breakpoints):
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


def years_from_dict(year_dict):
    """Extract years from a get_years dictionary.

    It will be used to label and display the progress in the alerts.

    Args:
        year_dict (dict): dictionary with years coming from get_years function
    """

    return "_".join([str(year.get("year")) for year in year_dict])


def get_interpolation_years(breaking_points):
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
    years_to_calculate = []
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


def get_years(sub_a_year, sub_b_year, matrix_a, matrix_b):
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

    years_a = calculate_breakpoints(sub_a_year)
    years_b = calculate_breakpoints(sub_b_year)

    # Only get interpolation years from subindicator B
    years_to_calculate = get_interpolation_years(years_b)

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


def parse_result(result, single=False):
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


def read_from_csv(task_file, process_id):
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


def calculate_breakpoints(user_input_years):
    """Calculate the breakpoints for the user input years.

    The objective is to get a dictionary with reporting year as key and
    all the years that are relevant for the reporting year as value.

    """

    breakpoints = {}

    if not user_input_years:
        return breakpoints

    report_intervals = [2000, 2005, 2010, 2015] + list(range(2018, 2050, 3))

    user_years = [val.get("year") for val in user_input_years.values()]

    # filter report intervals that are relevant for the user input
    report_intervals = [
        interval
        for interval in report_intervals
        if interval >= min(user_years) and interval <= max(user_years)
    ]

    # Create a list of tuples with the lower and upper bound of the interval
    intervals = list(zip(report_intervals[:-1], report_intervals[1:]))

    for interval in intervals:

        lower, upper = interval

        # get all years that falls in the interval
        years_in_interval = [
            year
            for year in user_input_years.values()
            if year.get("year") == lower or year.get("year") == upper
        ]

        only_years = [year.get("year") for year in years_in_interval]

        # If lower bound is not in the interval, find the maximum
        # year that is smaller than the lower bound
        if lower not in only_years:
            # get the maximum year that is smaller than the lower bound
            before_lower = max(
                [
                    year
                    for year in user_input_years.values()
                    if year.get("year") < lower
                ],
                key=lambda x: x.get("year"),
                default=None,
            )
            after_lower = min(
                [
                    year
                    for year in user_input_years.values()
                    if year.get("year") > lower
                ],
                key=lambda x: x.get("year"),
                default=None,
            )
            years_in_interval.extend([before_lower, after_lower])

        # If upper bound is not in the interval, find the minimum
        # year that is larger than the upper bound
        if upper not in only_years:
            # get the minimum year that is larger than the upper bound
            after_higher = min(
                [
                    year
                    for year in user_input_years.values()
                    if year.get("year") > upper
                ],
                key=lambda x: x.get("year"),
                default=None,
            )
            before_higher = max(
                [
                    year
                    for year in user_input_years.values()
                    if year.get("year") < upper
                ],
                key=lambda x: x.get("year"),
                default=None,
            )
            years_in_interval.extend([before_higher, after_higher])

        # Add the interval and the years that are relevant for the interval
        # skip None and remove duplicates
        unique_values = []
        for value in years_in_interval:
            if value not in unique_values and value:
                unique_values.append(value)

        breakpoints[interval] = unique_values

    return breakpoints


def get_sub_a_reports(parsed_df, year_s, model):
    """
    SubIndA_MGCI
    SubIndA_LandType
    """

    mgci_report = sub_a.get_report(parsed_df, year_s, model)
    mgci_land_type_report = sub_a.get_report(parsed_df, year_s, model, land_type=True)

    return mgci_report, mgci_land_type_report


def get_sub_b_reports(parsed_df, year_s, model):
    """
    SubIndB_pdma
    SubIndB_pdma_TransitionType
    """

    pdma_perc_report = sub_b.get_report(parsed_df, year_s, model)
    pdma_land_type_report = sub_b.get_report(parsed_df, year_s, model, land_type=True)

    return pdma_perc_report, pdma_land_type_report


def export_reports(model, output_folder):
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

    sub_a_reports = []
    sub_b_reports = []

    for group_name, result in model.results.items():
        # Split the group name by "_" to get the year(s)
        year_s = group_name.split("_")

        if len(year_s) == 1:
            # Only process requested years
            parsed_df = parse_result(result, single=True)
            sub_a_reports.append(get_sub_a_reports(parsed_df, year_s[0], model))
        else:
            parsed_df = parse_result(result)

            for year in year_s:
                target_lc = ["from_lc", "to_lc"][year_s.index(year)]
                parsed_df_year = (
                    parsed_df.groupby(["belt_class", target_lc], as_index=False)
                    .sum()
                    .copy()
                )
                parsed_df_year.rename(columns={target_lc: "lc_class"}, inplace=True)

                sub_a_reports.append(get_sub_a_reports(parsed_df_year, year, model))
            sub_b_reports.append(get_sub_b_reports(parsed_df, year_s, model))

    for reports in sub_a_reports:
        [
            report[0].to_excel(
                str(Path(output_folder, name.format(report[1]))),
                sheet_name=name.format(report[1]),
                index=False,
            )
            for report, name in zip(
                reports, ["SubIndA_MGCI_{}.xlsx", "SubIndA_LandType_{}.xlsx"]
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
                reports, ["SubIndB_pdma_{}.xlsx", "SubIndB_pdma_TransitionType_{}.xlsx"]
            )
        ]

    return True
