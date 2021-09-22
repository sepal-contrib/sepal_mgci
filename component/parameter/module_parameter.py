from pathlib import Path
from component.message import cm

__all__ = [
    "UPPER_THRESHOLDS",
    "GREEN_CLASSES",
    "DISPLAY_CLASSES",
    "KAPOS_PALETTE",
    "KAPOS_LEGEND",
    "KAPOS_VIS",
    "M49",
    "CUSTOM_AOI_ITEMS",
    "LULC_DEFAULT",
    "ESA_IPCC_MATRIX",
]

# SET SOME PARAMETERS
UPPER_THRESHOLDS = {98: "green", 95: "orange", 90: "red"}

# Specify which are the IPCC green classes
# Forest, grassland, cropland, wetland
GREEN_CLASSES = [1, 2, 3, 4]


# Classes that will be displayed in the dashboard
DISPLAY_CLASSES = [1, 2, 3, 4, 5, 6]

KAPOS_PALETTE = ["#ff0000", "#ff6f00", "#ffd500", "#bbff00", "#04ff00", "#034502"]

KAPOS_LEGEND = {
    name: color
    for name, color in zip([f"Kapos {i+1}" for i in range(6)], KAPOS_PALETTE)
}

# Kapos layer visualization for map
KAPOS_VIS = {"palette": KAPOS_PALETTE, "min": 1, "max": 6}

M49 = Path(__file__).parent / "m49_iso31661.csv"


CUSTOM_AOI_ITEMS = [
    {"header": "Administrative definitions"},
    {"text": "Country", "value": "ADMIN0"},
    {"text": "Sub-national level 1", "value": "ADMIN1"},
    {"text": "Sub-national level 2", "value": "ADMIN2"},
    {"header": "Custom geometries"},
    {"text": "Vector file", "value": "SHAPE"},
    {"text": "GEE Asset name", "value": "ASSET"},
]


LULC_DEFAULT = "users/geflanddegradation/toolbox_datasets/lcov_esacc_1992_2018"

# Define the translation matrix between ESA and IPCC classes
ESA_IPCC_MATRIX = Path(__file__).parent / "esa_ipcc_matrix.csv"
