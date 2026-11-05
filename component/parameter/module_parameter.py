from pathlib import Path

import pandas as pd

from component.message import msg

# Create a range of years from 2000 to present year
# and sort them in descending order
YEARS = pd.date_range(
    start="2000-01-01", end=pd.Timestamp.now(), freq="YS"
).year.tolist()
YEARS.sort(reverse=True)
"list: list of years used in calculation dialogs to match asset selection"

# Get current year
current_year = pd.Timestamp.now().year

REPORT_INTERVALS = [2000, 2005, 2010, 2015] + list(range(2018, current_year + 1, 3))
"list: list of years used in the report to match asset selection"


BIOBELT_LEGEND = {
    1: ["Nival", "#ff0000"],
    2: ["Alpine", "#ffd500"],
    3: ["Montane", "#bbff00"],
    4: ["Remaining mountain area", "#034502"],
    "total": [msg('aoi.legend.total'), "#24221f"],
}


# Kapos layer visualization for map
BIOBELT_VIS = {
    "palette": [val[1] for val in BIOBELT_LEGEND.values()][:-1],
    "min": 1,
    "max": 4,
}


BIOBELT = "users/xavidelamo/SDG1542_Mntn_BioclimaticBelts"
LULC_DEFAULT = "users/amitghosh/sdg_module/esa/cci_landcover"
DEM_DEFAULT = "CGIAR/SRTM90_V4"

# Define the translation matrix between ESA and MGCI LC classes
LC_MAP_MATRIX = Path(__file__).parent / "lc_map_matrix.csv"

# Define the default classes that will be loaded as target in the reclassify tile
LC_CLASSES = Path(__file__).parent / "lc_classification.csv"

# Define the default classes that will be loaded as target in the reclassify tile
TRANSITION_MATRIX_FILE = Path(__file__).parent / "transition_matrix.csv"

TRANSITION_DEGRADATION_MATRIX_FILE = (
    Path(__file__).parent / "transition_degradation_matrix.csv"
)

# Description of bioclimatic belts codes
BIOBELTS_DESC = Path(__file__).parent / "biobelts_label.csv"

UNITS = {
    # acronym: [factor, name]
    "ha": [10000, "hectares"],
    "sqkm": [1000000, "square kilometers"],
}


transition_degradation_matrix = pd.read_csv(TRANSITION_DEGRADATION_MATRIX_FILE)


DECODE = {
    3: {
        "abrv": "I",
        "label": "Improvement",
        "color": "#008000",
    },
    2: {
        "abrv": "S",
        "label": "Stable",
        "color": "#FFFACD",
    },
    1: {
        "abrv": "D",
        "label": "Degradation",
        "color": "#DC143C",
    },
}
"dict: dictionary containing the displayed labels for transition classes"


TBD = ""
