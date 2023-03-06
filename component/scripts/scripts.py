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


def get_years(start_year, end_year):
    """
    Returns a nested list of years based on the input start and end years.

    Args:
        start_year (list): A list of strings representing the start years.
        end_year (dict): A dictionary containing the end years, where the
            keys are a consecutive number and the values are dictionaries
            with 'base' and 'report' keys.

    Returns:
        list: A nested list of years.

    Example:
        start_year = ['1992', '1993', '1994']
        end_year = {
            1: {'base': '1993', 'report': '1993'},
            2: {'base': '1995', 'report': '1996'}
        }
        get_years(start_year, end_year)

        returns: [['1993', '1993'], ['1995', '1996'], ['1992'], ['1994']]
    """

    subb_years = [list(sub.values()) for sub in end_year.values()]

    flatten_subb_years = [year for sub_year in subb_years for year in sub_year]

    for year in start_year:
        if year not in flatten_subb_years:
            subb_years += [[year]]
    return subb_years


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
        - If there is only one year, it parses the result and appends the sub_a_report to the sub_a_reports list
        - If there are multiple years, it parses the result and for each year:
            - Groups the parsed dataframe by belt_class and target_lc
            - Renames the target_lc column to lc_class
            - Appends the sub_a_report to the sub_a_reports list
        - Appends the sub_b_report to the sub_b_reports list

    :param model: The model object containing the results to be exported
    :type model: object
    :return: A tuple containing two lists, the first one is sub_a_reports and the second one is sub_b_reports
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
