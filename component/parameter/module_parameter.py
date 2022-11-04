from pathlib import Path

from sepal_ui import color

from component.message import cm

__all__ = [
    "UPPER_THRESHOLDS",
    "GREEN_CLASSES",
    "DISPLAY_CLASSES",
    "M49",
    "CUSTOM_AOI_ITEMS",
    "LULC_DEFAULT",
    "ESA_IPCC_MATRIX",
    "UNITS",
    "M49_FILE",
    "DEM_DEFAULT",
    "LEGEND_NAMES",
]

# SET SOME PARAMETERS
UPPER_THRESHOLDS = {98: "green", 95: "orange", 90: "red"}

# Specify which are the IPCC green classes
# Forest, grassland, cropland, wetland
GREEN_CLASSES = [1, 2, 3, 4]

# LULC Classes that will be displayed in the dashboard
DISPLAY_CLASSES = [1, 2, 3, 4, 5, 6]

BIOBELT_LEGEND = {
    1: ["Nival", "#ff0000"],
    2: ["Alpine", "#ffd500"],
    3: ["Montane", "#bbff00"],
    4: ["Remaining mountain area", "#034502"],
    "total": [cm.aoi.legend.total, color.main],
}

LEGEND_NAMES = {
    "color": cm.aoi.legend.color,
    "desc": cm.aoi.legend.desc,
    "area": cm.aoi.legend.area,
    "perc": cm.aoi.legend.perc,
    "total": cm.aoi.legend.total,
}

# Kapos layer visualization for map
BIOBELT_VIS = {
    "palette": [val[1] for val in BIOBELT_LEGEND.values()][:-1],
    "min": 1,
    "max": 4,
}

M49 = Path(__file__).parent / "m49_iso31661.csv"
M49_FILE = Path(__file__).parent / "m49_countries.csv"


CUSTOM_AOI_ITEMS = [
    {"header": "Administrative definitions"},
    {"text": "Country", "value": "ADMIN0"},
    {"text": "Sub-national level 1", "value": "ADMIN1"},
    {"text": "Sub-national level 2", "value": "ADMIN2"},
    {"header": "Custom geometries"},
    {"text": "Vector file", "value": "SHAPE"},
    {"text": "GEE Asset name", "value": "ASSET"},
]


BIOBELT = "users/xavidelamo/SDG1542_Mntn_BioclimaticBelts"
LULC_DEFAULT = "users/amitghosh/sdg_module/esa_cci_lc_1992_2019"
DEM_DEFAULT = "CGIAR/SRTM90_V4"


# dem = ee.Image("USGS/SRTMGL1_003") # srtm_1
# dem = ee.Image("USGS/GTOPO30")


# Define the translation matrix between ESA and IPCC classes
ESA_IPCC_MATRIX = Path(__file__).parent / "esa_ipcc_matrix.csv"

UNITS = {
    # acronym: [factor, name]
    "ha": [10000, "hectares"],
    "sqkm": [1000000, "square kilometers"],
}
