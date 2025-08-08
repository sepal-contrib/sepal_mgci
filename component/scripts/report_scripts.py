import pandas as pd

import component.parameter.module_parameter as param
from component.scripts.file_handler import read_file

BELT_TABLE = pd.read_csv(param.BIOBELTS_DESC)
"pd.Dataframe: bioclimatic belts classes and description"

LC_CLASSES = pd.read_csv(param.LC_CLASSES)
"pd.Dataframe: fixed land cover classes, description and colors"


def get_nature(row):
    """return nature column based on OBS_VALUE"""

    return "N" if row["OBS_VALUE"] == "NA" else "C"


def get_obs_status(row):
    """Information on the quality of a value or an unusual or missing value. For what regards to the values produced by countries using the tools only two possible values are allowed: A (Official figure) for data values and M (Missing) when a given bioclimatc belt does not occur in a given country. When Nature = N then OBS_STATUS=M and  OBS_VALUE = NA."""

    if row["NATURE"] == "N":
        return "M"

    elif row["NATURE"] == "C":
        return "A"


def get_belt_desc(row):
    """return bioclimatic belt description"""

    if not row["belt_class"] in set(BELT_TABLE.belt_class.unique()):
        return row["belt_class"]

    desc = BELT_TABLE[BELT_TABLE.belt_class == row["belt_class"]]["desc"]

    return desc.values[0]


def get_lc_desc(row):
    """return landcover description"""

    if not row["lc_class"] in set(LC_CLASSES.lc_class.unique()):
        return row["lc_class"]

    desc = LC_CLASSES[LC_CLASSES.lc_class == row["lc_class"]]["desc"]

    return desc.values[0]


def fill_parsed_df(parsed_df):
    """Fill parsed_df with missing values.

    Parsed dataframe has to contain all the belt_classes, even if they are not present in the data
    """

    # create a cartesian product of belt_classes and lc_classes
    BELT_TABLE["key"] = 1
    LC_CLASSES["key"] = 1

    all_belts_classes = pd.merge(
        BELT_TABLE[["belt_class", "key"]], LC_CLASSES[["lc_class", "key"]], on="key"
    )

    # expand parsed_df to include all belt_classes
    filled_df = pd.merge(
        parsed_df, all_belts_classes, how="outer", on=["belt_class", "lc_class"]
    )

    # fill NaN values with 0
    filled_df.fillna(0, inplace=True)

    return filled_df


def get_impact(row, transition_matrix: str):
    """Return the type of the impact based on the initial and last class

    Args:
        row (pd.Series): row of the dataframe
        transition_matrix: transition_matrix dataframe (custom or default)
    """

    # Read the transition matrix safely with pandas
    transition_table = read_file(transition_matrix)

    # Check that both
    if not all([row["from_lc"], row["to_lc"]]):
        return 0

    return transition_table[
        (transition_table.from_code == row["from_lc"])
        & (transition_table.to_code == row["to_lc"])
    ]["impact_code"].values[0]
