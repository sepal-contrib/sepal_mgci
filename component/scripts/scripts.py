import pandas as pd
import random
import component.parameter as param
import component.scripts as cs
import ipyvuetify as v

__all__ = [
    "human_format",
    "get_random_color",
    "get_mgci_color",
    "get_report_folder",
    "get_geoarea",
    "create_avatar",
    "read_from_task",
]


def read_from_task(results_file):
    """Read a tasks file and extract its structure"""

    result = {}
    group = "group"
    groups = "groups"
    sum = "sum"

    result["groups"] = eval(pd.read_csv(results_file)["groups"][0].replace("=", ":"))

    return result


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
    report_folder = param.REPORTS_DIR / f"MGCI_{mgci_model.aoi_model.name}"
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
